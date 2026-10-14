"""Recovered impulse-to-motion and plane-height helpers for original collisions."""
from dataclasses import dataclass
import math
from client.tire_response import f32


def _vector(values):
    if len(values)!=3: raise ValueError('three-component vector required')
    return tuple(map(f32,values))


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


def impulse_motion(body, impulse, lever, radial_direction):
    """Complete 0x457780; angular output uses radians, with no timestep inside."""
    impulse,lever,radial=map(_vector,(impulse,lever,radial_direction))
    inverse_mass=f32(body.inverse_mass)
    inertia=_vector(body.inverse_inertia)
    world_to_body=_matrix(body.world_to_body)
    body_to_world=_matrix(body.body_to_world)
    approach_extended=-((impulse[0]*radial[0]+impulse[1]*radial[1])+impulse[2]*radial[2])
    approach=f32(approach_extended)
    if approach_extended>0:
        length=math.sqrt((impulse[0]**2+impulse[1]**2)+impulse[2]**2)
        inverse_length=1.0/length
        direction=tuple(f32(p*inverse_length) for p in impulse)
        linear=tuple(f32(p*inverse_mass*approach) for p in direction)
    else:
        linear=(0.0,0.0,0.0)
    cross=(f32(lever[1]*impulse[2]-lever[2]*impulse[1]),
           f32(lever[2]*impulse[0]-lever[0]*impulse[2]),
           f32(lever[0]*impulse[1]-lever[1]*impulse[0]))
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
