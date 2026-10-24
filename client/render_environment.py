"""Small state transitions for the legacy environment renderer."""
import struct
from fractions import Fraction


def set_environment_activity(primary, secondary, *, primary_enabled=True):
    """Write the active flags at +0x3c of the two optional scene objects.

    This models the complete body of 0x478950. The global-to-object pointer
    selection remains the caller's responsibility.
    """
    for pointer in (primary, secondary):
        if type(pointer) is not int or pointer < 0:
            raise ValueError('environment object addresses must be nonnegative integers')
    return ((primary, int(bool(primary_enabled))) if primary else None,
            (secondary, 0) if secondary else None)


def release_environment_objects(objects):
    """Return non-null frees and zeroed globals for the 0x478980 cleanup."""
    if not isinstance(objects,(tuple,list)) or len(objects)!=4:
        raise ValueError('environment cleanup requires four object pointers')
    if any(type(pointer) is not int or not 0<=pointer<=0xffffffff
           for pointer in objects):
        raise ValueError('environment pointers must be unsigned words')
    return tuple(pointer for pointer in objects if pointer), (0,0,0,0)


def build_environment_mesh_no_projection(record, track_index, track_id,
                                          reverse, object_bytes, *,
                                          vertical_step, segment_step,
                                          span_scale):
    """Build the 11-row 0x478b20 object when projection checks all miss.

    `record` is the 0x54-byte track row. `object_bytes` supplies the prior
    allocation contents so fields the native routine leaves untouched remain
    untouched in the returned image.
    """
    if not isinstance(record,(bytes,bytearray)) or len(record)!=0x54:
        raise ValueError('track record must contain 0x54 bytes')
    if (not isinstance(object_bytes,(bytes,bytearray)) or len(object_bytes)!=0x3d0):
        raise ValueError('environment object image must contain 0x3d0 bytes')
    if type(track_index) is not int or not -(1<<31)<=track_index<(1<<31):
        raise ValueError('track index must be signed 32-bit')
    if type(track_id) is not int or not -(1<<31)<=track_id<(1<<31):
        raise ValueError('track identifier must be signed 32-bit')
    if type(reverse) is not bool:
        raise ValueError('reverse must be boolean')
    def f(offset): return struct.unpack_from('<f',record,offset)[0]
    def i(offset): return struct.unpack_from('<i',record,offset)[0]
    def f32(value): return struct.unpack('<f',struct.pack('<f',value))[0]
    vertical_step=f32(vertical_step)
    segment_step=f32(segment_step)
    span_scale=f32(span_scale)
    def ratio(value): return Fraction.from_float(float(value))
    def x87(value):
        value=Fraction(value)
        if not value: return value
        sign=-1 if value<0 else 1
        value=abs(value)
        exponent=value.numerator.bit_length()-value.denominator.bit_length()
        if exponent>=0:
            if value < (1<<exponent): exponent-=1
        elif value < Fraction(1,1<<(-exponent)):
            exponent-=1
        shift=63-exponent
        scaled=value*(1<<shift) if shift>=0 else value/Fraction(1<<(-shift))
        quotient,remainder=divmod(scaled.numerator,scaled.denominator)
        twice=remainder*2
        if twice>scaled.denominator or (twice==scaled.denominator and quotient&1):
            quotient+=1
        if quotient==(1<<64):
            quotient>>=1; exponent+=1
        return sign*Fraction(quotient,1<<shift) if shift>=0 else sign*Fraction(quotient*(1<<(-shift)),1)
    def f32_exact(value):
        value=Fraction(value)
        if not value: return 0.0
        sign=0x80000000 if value<0 else 0
        value=abs(value)
        exponent=value.numerator.bit_length()-value.denominator.bit_length()
        if exponent>=0:
            if value < (1<<exponent): exponent-=1
        elif value < Fraction(1,1<<(-exponent)):
            exponent-=1
        shift=23-exponent if exponent>=-126 else 149
        scaled=value*(1<<shift) if shift>=0 else value/Fraction(1<<(-shift))
        quotient,remainder=divmod(scaled.numerator,scaled.denominator)
        if remainder*2>scaled.denominator or (
            remainder*2==scaled.denominator and quotient&1):
            quotient+=1
        if exponent>=-126:
            if quotient==(1<<24): quotient>>=1; exponent+=1
            if exponent>127: bits=sign|0x7f800000
            else: bits=sign|((exponent+127)<<23)|(quotient-(1<<23))
        else:
            bits=sign|quotient
        return struct.unpack('<f',struct.pack('<I',bits))[0]
    result=bytearray(object_bytes)
    struct.pack_into('<ii',result,0,track_index,track_id)
    origin=[f(offset) for offset in (0,4,8)]
    direction=[f(offset) for offset in (0x24,0x28,0x2c)]
    half=[f32(f(offset)*3.0) for offset in (0x18,0x1c,0x20)]
    distance=f32(i(0x48)*f(0x3c))
    projected=[f32(direction[n]*distance) for n in range(3)]
    center=[f32(origin[n]+projected[n]) for n in range(3)]
    delta_scale=x87(x87(x87(i(0x44)*ratio(f(0x38)))+
                          ratio(distance))*ratio(span_scale))
    delta_scale=ratio(f32_exact(delta_scale))
    delta=[f32_exact(x87(ratio(direction[n])*delta_scale))
           for n in range(3)]
    if reverse:
        first=[f32(center[n]-half[n]) for n in range(3)]
        second=[f32(center[n]+half[n]) for n in range(3)]
    else:
        first=[f32(center[n]+half[n]) for n in range(3)]
        second=[f32(center[n]-half[n]) for n in range(3)]
    nan_word=0xffffffff
    for index in range(11):
        base=0x08+index*0x18
        first[1]=f32(first[1]+vertical_step)
        second[1]=f32(second[1]+vertical_step)
        struct.pack_into('<6f',result,base,*(first+second))
        for row in (first,second):
            for axis in range(3):
                row[axis]=f32(row[axis]+delta[axis])
        metadata=0x120+index*0x40
        struct.pack_into('<I',result,metadata,nan_word)
        step=f32(index*segment_step)
        struct.pack_into('<f',result,metadata+8,step)
        struct.pack_into('<f',result,metadata+12,0.0)
        struct.pack_into('<I',result,metadata+32,nan_word)
        struct.pack_into('<f',result,metadata+40,step)
        struct.pack_into('<f',result,metadata+44,1.0)
    return bytes(result)
