"""Recovered impulse-to-motion and plane-height helpers for original collisions."""
from dataclasses import dataclass
import math
import struct
from client.tire_response import f32


def _vector(values):
    if len(values)!=3: raise ValueError('three-component vector required')
    return tuple(map(f32,values))


def _ieee_f32(value):
    """Round like a stored native float, retaining IEEE NaN and infinity."""
    try:
        return math.copysign(float('inf'), value) if math.isinf(value) else \
            struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error):
        return math.copysign(float('inf'), value)


def _ieee_vector(values):
    if len(values)!=3: raise ValueError('three-component vector required')
    return tuple(map(_ieee_f32,values))


def _ieee_transform(vector, matrix):
    return tuple(_ieee_f32((vector[0]*matrix[i]+vector[1]*matrix[i+3])+
                           vector[2]*matrix[i+6]) for i in range(3))


def _matrix(values):
    if len(values)!=9: raise ValueError('nine-component matrix required')
    return tuple(map(f32,values))


def _transform(vector, matrix):
    return tuple(f32((vector[0]*matrix[i]+vector[1]*matrix[i+3])+
                     vector[2]*matrix[i+6]) for i in range(3))


@dataclass(frozen=True)
class CollisionInertia:
    inverse_mass: float
    inverse_inertia: tuple[float,float,float]
    world_to_body: tuple[float,...]
    body_to_world: tuple[float,...]


@dataclass(frozen=True)
class ImpulseMotion:
    linear: tuple[float,float,float]
    angular: tuple[float,float,float]


def impulse_motion(body, impulse, lever, radial_direction, *, allow_nonfinite=False):
    """Complete 0x457780; angular output uses radians, with no timestep inside."""
    vector = _ieee_vector if allow_nonfinite else _vector
    rounded = _ieee_f32 if allow_nonfinite else f32
    impulse,lever,radial=map(vector,(impulse,lever,radial_direction))
    inverse_mass=rounded(body.inverse_mass)
    inertia=vector(body.inverse_inertia)
    if len(body.world_to_body)!=9 or len(body.body_to_world)!=9:
        raise ValueError('nine-component matrix required')
    world_to_body=tuple(map(rounded,body.world_to_body))
    body_to_world=tuple(map(rounded,body.body_to_world))
    approach_extended=-((impulse[0]*radial[0]+impulse[1]*radial[1])+impulse[2]*radial[2])
    approach=rounded(approach_extended)
    if approach_extended>0:
        length=math.sqrt((impulse[0]**2+impulse[1]**2)+impulse[2]**2)
        inverse_length=1.0/length
        direction=tuple(rounded(p*inverse_length) for p in impulse)
        linear=tuple(rounded(p*inverse_mass*approach) for p in direction)
    else:
        linear=(0.0,0.0,0.0)
    cross=(rounded(lever[1]*impulse[2]-lever[2]*impulse[1]),
           rounded(lever[2]*impulse[0]-lever[0]*impulse[2]),
           rounded(lever[0]*impulse[1]-lever[1]*impulse[0]))
    if allow_nonfinite:
        local=_ieee_transform(cross,world_to_body)
        # Diagonal inverse inertia is applied in the body frame before rotation.
        angular=_ieee_transform(tuple(rounded(v*i) for v,i in zip(local,inertia)),
                                body_to_world)
    else:
        local=_transform(cross,world_to_body)
        angular=_transform(tuple(f32(v*i) for v,i in zip(local,inertia)),body_to_world)
    return ImpulseMotion(linear,angular)


def plane_height(normal, plane_point, query):
    """Float-stored result of complete plane-height helper 0x4b71a0.

    Vertical planes cannot provide a single-valued height and are rejected.
    The original helper itself divides directly and has no error check.
    """
    normal,point,query=map(_vector,(normal,plane_point,query))
    if normal[1]==0: raise ValueError('vertical plane has no unique height')
    numerator=(query[2]-point[2])*normal[2]+(query[0]-point[0])*normal[0]
    return f32(-numerator/normal[1]+point[1])
