"""Recovered owner mass, inertia and axle-lever binding numeric sections.

Configuration must be finalized before calling ``bind_finalized_owner``. A body
loader image is not finalized configuration. Half extents come from the original
model geometry setup, not wheel-marker spacing.
"""
from dataclasses import dataclass
import math
import struct

from client.tire_response import f32


def _bits(word): return struct.unpack('<f',struct.pack('<I',word))[0]


def body_inertia_scales(shape, initial=(1.,1.,1.)):
    """Original 0x53a150; unknown selectors preserve supplied prior values."""
    if shape == 6: words=(0x3f266666,0x3f2e147b,0x3f4ccccd)
    elif shape in (4,5): words=(0x3f266666,0x3f3ae148,0x3f59999a)
    elif shape in (1,7,3): words=(0x3f19999a,0x3f4ccccd,0x3f333333)
    elif shape in (0,2): words=(0x3f6147ae,0x3f70a3d7,0x3f547ae1)
    else:
        values=tuple(map(f32,initial))
        if len(values)!=3 or not all(math.isfinite(v) for v in values):
            raise ValueError('three finite initial inertia scales required')
        return values
    return tuple(map(_bits,words))


@dataclass(frozen=True)
class OwnerInertia:
    mass: float
    inverse_mass: float
    half_extents: tuple[float,float,float]
    shape_scales: tuple[float,float,float]
    inertia: tuple[float,float,float]
    inverse_inertia: tuple[float,float,float]


def bind_owner_inertia(mass,half_extents,shape):
    """0x51f4dd mass binding followed by 0x53a3f5 inertia calculation.

    Default x87 53-bit precision retains products until float32 stores. Zero
    input mass follows the original 1000 fallback; this is observable original
    behavior, not permission to invent a missing assembled mass.
    """
    mass=f32(mass);half_extents=tuple(map(f32,half_extents))
    if len(half_extents)!=3 or not all(math.isfinite(v) for v in (mass,*half_extents)):
        raise ValueError('finite mass and three half extents required')
    if mass<0 or min(half_extents)<=0:
        raise ValueError('nonnegative mass and positive half extents required')
    if mass==0:mass=1000.
    scales=body_inertia_scales(shape)
    x,y,z=(v*v*4. for v in half_extents)
    factor=_bits(0x3daaaaab)
    inertia=tuple(f32(v*s*mass*factor) for v,s in zip((z+y,z+x,y+x),scales))
    return OwnerInertia(mass,f32(1./mass),half_extents,scales,inertia,
                        tuple(f32(1./v) for v in inertia))


@dataclass(frozen=True)
class AxleLevers:
    front: float
    rear: float


@dataclass(frozen=True)
class StartupCOMCoordinates:
    vertical: float
    longitudinal: float


def bind_startup_com(height_parameter,half_height,observed_front_marker_z,observed_front_lever):
    """0x43ac8e, before 0x53a1f0; preserve that original observation order.

    This stage reads existing owner+18c4 and +18b8. Their prior initialization
    must be established; substituting the subsequently calculated lever changes
    startup ordering. The lateral COM coordinate is not written by this range.
    """
    height,half,marker,lever=map(f32,(height_parameter,half_height,
                                    observed_front_marker_z,observed_front_lever))
    return StartupCOMCoordinates(f32(height*_bits(0x3f68ba2e)-half),f32(marker-lever))


def bind_axle_levers(wheelbase,assembled_front_weight_fraction):
    """0x53a7b6: FINAL cfg+3c fraction, not body-only cfg+40 fraction."""
    wheelbase=f32(wheelbase);fraction=f32(assembled_front_weight_fraction)
    if not all(math.isfinite(v) for v in (wheelbase,fraction)) or wheelbase<=0:
        raise ValueError('positive wheelbase and finite finalized weight fraction required')
    return AxleLevers(f32((1.-fraction)*wheelbase),f32(wheelbase*fraction))


@dataclass(frozen=True)
class FinalizedOwnerBinding:
    inertia: OwnerInertia
    axle_levers: AxleLevers


def bind_finalized_owner(configuration,model_half_extents,*,assembly_finalized):
    """Bind supplied finalized original configuration and model observations.

    The explicit completion assertion prevents body-only catalogue callers from
    silently treating their initial mass/fraction accumulators as whole-car data.
    It is the caller's responsibility to establish their original provenance.
    """
    if assembly_finalized is not True:
        raise ValueError('complete component loading and assembly aggregation first')
    if len(configuration)!=0x820:
        raise ValueError('expected assembled 0x820-byte configuration')
    def number(offset):return struct.unpack_from('<f',configuration,offset)[0]
    shape=struct.unpack_from('<i',configuration,0x48)[0]
    return FinalizedOwnerBinding(bind_owner_inertia(number(0x20),model_half_extents,shape),
        bind_axle_levers(number(0x2c),number(0x3c)))
