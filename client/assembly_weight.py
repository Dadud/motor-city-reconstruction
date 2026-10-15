"""Recovered post-component weight distribution, original 0x53b590.

Component slots retain observed order; their full part-loader interpretation is
still under recovery. These are mechanical configuration inputs, not valuations.
"""
import math
import struct

from client.tire_response import f32


FRONT_MASS_OFFSETS = (0x428,0x504,0x52c,0x490,0x5c8,0x628,0x608,
    0x700,0x220,0x648,0x660,0x3d8,0x378,0x3ec,0x3a4,0x3c0,
    0x408,0x55c,0x574,0x4d4,0x4c0,0x4f0,0x80c)
REAR_MASS_OFFSETS = (0x6d8,0x5e8,0x638,0x618,0x70c,0x324,0x654,
    0x670,0x418,0x7bc,0x58c,0x5a0,0x5b4)


def assembled_front_weight_fraction(body_mass,body_fraction,wheelbase,
                                    shared_mass,front_masses,rear_masses):
    """Return the original helper's double-precision fraction before its store.

    Input slots are float32. Only half body mass is stored as float32 inside
    this helper. Do not cancel wheelbase or reorder the component additions.
    Finite physical-domain validation is an authored boundary; the original
    helper has no guard against zero denominators or nonphysical observations.
    """
    body,fraction,length,shared=map(f32,(body_mass,body_fraction,wheelbase,shared_mass))
    front=tuple(map(f32,front_masses));rear=tuple(map(f32,rear_masses))
    if len(front)!=23 or len(rear)!=13:
        raise ValueError('expected 23 front and 13 rear component mass slots')
    if not all(math.isfinite(v) for v in (body,fraction,length,shared,*front,*rear)):
        raise ValueError('finite weight distribution inputs required')
    if length<=0 or not 0<=fraction<=1 or min(body,shared,*front,*rear)<0:
        raise ValueError('positive wheelbase, fraction in [0,1], and nonnegative masses required')
    half=f32(body*.5)
    front_sum=shared*.25+half
    for index,mass in enumerate(front):
        front_sum += mass+mass if 4<=index<9 else mass
    front_moment=front_sum*(fraction*length)
    rear_sum=shared*.75+half
    for index,mass in enumerate(rear):
        rear_sum += mass+mass if 1<=index<6 else mass
    rear_moment=((1.-fraction)*length)*rear_sum
    denominator=rear_moment+front_moment
    if denominator==0:
        raise ValueError('nonzero combined mass moment required')
    return front_moment/denominator


def finalize_weight_distribution(configuration,*,components_loaded):
    """Write only cfg+3c after established component loading.

    This does not complete the original assembly routine, mass accumulation,
    curve generation, or semantic validation. A body-only image is insufficient.
    """
    if components_loaded is not True:
        raise ValueError('complete original component loading first')
    if len(configuration)!=0x820:
        raise ValueError('expected 0x820-byte mechanical configuration')
    def value(offset):return struct.unpack_from('<f',configuration,offset)[0]
    fraction=assembled_front_weight_fraction(value(0x1c),value(0x40),value(0x2c),
        value(0x680),tuple(map(value,FRONT_MASS_OFFSETS)),tuple(map(value,REAR_MASS_OFFSETS)))
    out=bytearray(configuration)
    struct.pack_into('<f',out,0x3c,fraction)
    return bytes(out)
