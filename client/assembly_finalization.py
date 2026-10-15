"""Numeric postload tail of original 0x54e720, before engine-curve generation.

Complete component loading and preceding component quality updates are required
inputs. This does not certify a mechanically complete stock or modified vehicle.
"""
import math
import struct
from client.assembly_weight import finalize_weight_distribution
from client.tire_response import f32


# Preserve instruction order: the decompiler's expression reorders these sums.
WEIGHTED_SLOTS = ((0x444,0x428),(0x514,0x504),(0x3b0,0x3a4),
    (0x538,0x52c),(0x480,0x478),(0x4b0,0x4ac),(0x498,0x490))
COEFFICIENTS=tuple(map(f32,(.45,.42,.9,.9,.47,.46,.45,.52,1.02,1.7)))


def finalize_loaded_configuration(configuration,*,components_loaded):
    """Recover 0x54e8ea..0x54ea89, including the real weight helper.

    Only the five possible output areas change. Engine curves, total component
    mass accumulation, quality updates and semantic validation remain separate.
    Reject unsafe indices/zero divisors instead of reading adjacent stack data.
    """
    if components_loaded is not True:
        raise ValueError('complete component loading and quality updates first')
    if len(configuration)!=0x820:
        raise ValueError('expected 0x820-byte mechanical configuration')
    out=bytearray(configuration)
    def number(offset):
        v=struct.unpack_from('<f',out,offset)[0]
        if not math.isfinite(v):raise ValueError('finite postload observation required')
        return v
    def integer(offset):return struct.unpack_from('<i',out,offset)[0]
    def put(offset,value):struct.pack_into('<f',out,offset,value)
    if number(0x5a0)<=0:
        selector=integer(0x57c)
        put(0x5b0,.025 if selector==0 else .03 if selector==1 else 0.)
    if number(0x610)!=0 and number(0x620)!=0:
        out[0x114:0x118]=out[0x610:0x614]
        out[0x118:0x11c]=out[0x620:0x624]
    put(0x28,number(0x20)*f32(.02)+number(0x28))
    terms=[]
    for selector_offset,mass_offset in WEIGHTED_SLOTS:
        selector=integer(selector_offset)
        if not 0<=selector<10:raise ValueError('postload coefficient selector outside [0,9]')
        terms.append(COEFFICIENTS[selector]*number(mass_offset))
    total=terms[0]
    for term in terms[1:]:total+=term
    total+=number(0x55c)*f32(.42)
    selector=integer(0x580)
    if not 0<=selector<10:raise ValueError('postload coefficient selector outside [0,9]')
    total+=COEFFICIENTS[selector]*number(0x574)
    total+=(number(0x4f0)*f32(.4))*f32(1.92)
    if total==0:raise ValueError('nonzero postload weighted divisor required')
    put(0x448,1./total)
    return finalize_weight_distribution(out,components_loaded=True)
