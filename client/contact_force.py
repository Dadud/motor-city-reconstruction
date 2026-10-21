"""Bounded contact-force and object-pair response helpers from the client."""
import math
from fractions import Fraction

from .tire_response import f32


def _dot(left, right):
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _cross(left, right):
    return (f32(left[1]*right[2] - left[2]*right[1]),
            f32(left[2]*right[0] - left[0]*right[2]),
            f32(left[0]*right[1] - left[1]*right[0]))


def _binary_round(value, precision=64):
    if value == 0:
        return value
    sign = -1 if value < 0 else 1
    value = abs(value)
    n, d = value.numerator, value.denominator
    exponent = n.bit_length() - d.bit_length()
    if (n < (d << exponent)) if exponent >= 0 else ((n << -exponent) < d):
        exponent -= 1
    shift = precision - 1 - exponent
    if shift >= 0:
        q, r = divmod(n << shift, d)
        divisor = d
    else:
        divisor = d << -shift
        q, r = divmod(n, divisor)
    if r*2 > divisor or (r*2 == divisor and q & 1):
        q += 1
    if q == 1 << precision:
        q >>= 1
        exponent += 1
    rounded = Fraction(q, 1 << shift) if shift >= 0 else Fraction(q << -shift, 1)
    return rounded if sign > 0 else -rounded


def _ext(value):
    return value if isinstance(value, Fraction) else Fraction.from_float(float(value))


def _ext_mul(left, right):
    return _binary_round(_ext(left)*_ext(right))


def _ext_add(left, right):
    return _binary_round(_ext(left)+_ext(right))


def _ext_f32(value):
    return f32(float(value))


def _sum3_then_scale(terms, scale):
    # 0x457780 stores the three-term matrix product to a float local before
    # loading it again and applying the per-axis scale.
    return f32(f32(sum(left*right for left,right in terms))*scale)


def _normalize(vector):
    magnitude = math.sqrt(_dot(vector, vector))
    if magnitude == 0.0:
        return (0.0, 0.0, 0.0)
    inverse = 1.0 / magnitude
    return tuple(f32(value * inverse) for value in vector)


def contact_response(record, force, contact_point, normal):
    """Translate the per-contact response at 0x457780.

    ``record`` is the original 0x4f8-byte owner image. The two returned vectors
    are the linear and angular contributions written by that helper.
    """
    if not isinstance(record, (bytes, bytearray, memoryview)) or len(record) < 0x4f8:
        raise ValueError('complete world-object record required')
    force, contact_point, normal = tuple(map(f32, force)), tuple(map(f32, contact_point)), tuple(map(f32, normal))
    if any(len(vector) != 3 for vector in (force, contact_point, normal)):
        raise ValueError('three-component contact vectors required')

    normal_speed = _dot(force, normal)
    if normal_speed >= 0.0:
        linear = (0.0, 0.0, 0.0)
    else:
        force_direction = _normalize(force)
        mass_scale = _read_f(record, 0x54)
        impulse = -normal_speed
        linear = tuple(f32(direction * mass_scale * f32(impulse))
                       for direction in force_direction)

    cross = _cross(contact_point, force)
    # The inverse-inertia rows and diagonal scale occupy the owner's recovered
    # +0x9c..+0xbc and +0x2fc..+0x304 fields respectively.
    m = tuple(_read_f(record, offset) for offset in
              (0x9c, 0xa0, 0xa4, 0xa8, 0xac, 0xb0,
               0xb4, 0xb8, 0xbc))
    scale = tuple(_read_f(record, offset) for offset in (0x2fc, 0x300, 0x304))
    transformed = (
        _sum3_then_scale(((cross[2],m[6]),(cross[1],m[3]),
                          (cross[0],m[0])),scale[0]),
        _sum3_then_scale(((cross[2],m[7]),(cross[1],m[4]),
                          (cross[0],m[1])),scale[1]),
        _sum3_then_scale(((cross[2],m[8]),(cross[1],m[5]),
                          (cross[0],m[2])),scale[2]))
    rotation = tuple(_read_f(record, offset) for offset in
                     (0x78, 0x7c, 0x80, 0x84, 0x88, 0x8c,
                      0x90, 0x94, 0x98))
    angular = (
        f32(transformed[2]*rotation[6] + transformed[1]*rotation[3] +
            transformed[0]*rotation[0]),
        f32(transformed[2]*rotation[7] + transformed[1]*rotation[4] +
            transformed[0]*rotation[1]),
        f32(transformed[2]*rotation[8] + transformed[1]*rotation[5] +
            transformed[0]*rotation[2]))
    return linear, angular


def _read_f(record, offset):
    import struct
    return struct.unpack_from('<f', record, offset)[0]


def contact_forces_step(record, contact_response_fn=contact_response):
    """Translate the six-point contact-force accumulation at 0x51fc00."""
    import struct
    if not isinstance(record, bytearray) or len(record) < 0x4f8:
        raise ValueError('mutable 0x4f8-byte world-object record required')
    if not callable(contact_response_fn):
        raise ValueError('the per-contact response is required')

    counter = struct.unpack_from('<h', record, 0x3bc)[0]
    if counter == 0 or (record[6] != 0 and _read_f(record, 0x88) >= 0.707):
        return record

    velocity = tuple(_read_f(record, offset) for offset in (0x14, 0x18, 0x1c))
    speed = f32(math.sqrt(_dot(velocity, velocity)))
    direction = _normalize(velocity) if speed != 0.0 else (0.0, 0.0, 0.0)
    basis = (0x78, 0x84, 0x90)
    abs_projection = tuple(f32(abs(_dot(direction, tuple(
        _read_f(record, offset + axis*4) for axis in range(3))))
        ) for offset in basis)
    d0, d1, d2 = (_read_f(record, offset) for offset in (0xd0, 0xcc, 0xd4))
    term1=_ext_f32(_ext_mul(_ext_mul(_ext_mul(_ext_mul(d0,d2),
        _read_f(record,0x30c)),abs_projection[0]),4.0))
    term2=_ext_f32(_ext_add(_ext_mul(_ext_mul(_ext_mul(_ext_mul(d2,d1),
        _read_f(record,0x310)),abs_projection[1]),4.0),term1))
    # The first and second terms spill to float locals; the third remains in
    # the x87 accumulator through area and density scaling, then drag stores.
    coefficient=_ext_mul(_ext_mul(_ext_add(_ext_mul(_ext_mul(_ext_mul(
        _ext_mul(d0,d1),_read_f(record,0x314)),abs_projection[2]),4.0),
        term2),_read_f(record,0x308)),f32(0.6125))
    drag = tuple(_ext_f32(-_ext_mul(_ext_mul(speed,velocity[i]),coefficient))
                 for i in range(3))

    position = tuple(_read_f(record, offset) for offset in (8, 0xc, 0x10))
    points = tuple(tuple(f32(_read_f(record, offset + axis*4) - position[axis])
                         for axis in range(3))
                   for offset in (0x248,0x254,0x260,0x26c,0x278,0x284))
    linear_total = [0.0,0.0,0.0]
    angular_total = [0.0,0.0,0.0]
    for point in points:
        if _dot(velocity, point) > 0.0:
            normal = _normalize(point)
            linear, angular = contact_response_fn(record, drag, point, normal)
            linear_total = [f32(a+b) for a,b in zip(linear_total,linear)]
            angular_total = [f32(a+b) for a,b in zip(angular_total,angular)]

    for offset, value in zip((0x14,0x18,0x1c), linear_total):
        struct.pack_into('<f',record,offset,
                         f32(_read_f(record,offset)+f32(value*0.03125)))
    for offset, value in zip((0x38,0x3c,0x40), angular_total):
        struct.pack_into('<f',record,offset,
                         f32(_read_f(record,offset)+f32(value*f32(0.004973592))))
    return record
