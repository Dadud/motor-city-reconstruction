"""Original world-object motion damping callback FUN_005779d0."""
from dataclasses import dataclass
from math import isfinite

from .tire_response import f32


@dataclass(frozen=True)
class WorldObjectMotion:
    """Observed fields consumed/written by 0x5779d0.

    ``contact_counter`` is the signed short at owner offset +0x3bc,
    ``linear_velocity`` maps to +0x14/+0x18/+0x1c, and ``angular_velocity``
    maps to +0x38/+0x3c/+0x40. Other owner bytes are outside this callback's writes.
    """
    contact_counter: int
    linear_velocity: tuple[float, float, float]
    angular_velocity: tuple[float, float, float]


def update_world_object_motion(state: WorldObjectMotion) -> WorldObjectMotion:
    """Apply the original callback's branch-specific damping and rest gates.

    Floats are treated as stored binary32 values. The original callback's three
    angle gates all clear +0x3c, including gates that inspect +0x38 and +0x40.
    """
    if not isinstance(state, WorldObjectMotion):
        raise ValueError('explicit world-object motion state required')
    if type(state.contact_counter) is not int or not -0x8000 <= state.contact_counter <= 0x7fff:
        raise ValueError('contact counter must be a signed short')
    if len(state.linear_velocity) != 3 or len(state.angular_velocity) != 3:
        raise ValueError('three linear and angular velocity values required')
    linear = tuple(f32(value) for value in state.linear_velocity)
    angular = tuple(f32(value) for value in state.angular_velocity)
    if not all(isfinite(value) for value in (*linear, *angular)):
        raise ValueError('finite world-object motion values required')

    if state.contact_counter != 0:
        decay = f32(0.9)
        return WorldObjectMotion(state.contact_counter, linear,
                                 tuple(f32(value * decay) for value in angular))

    linear = tuple(0.0 if abs(value) < f32(0.5) else value for value in linear)
    angle_x, angle_y, angle_z = angular
    if abs(angle_x) < f32(0.05):
        angle_y = 0.0
    if abs(angle_y) < f32(0.05):
        angle_y = 0.0
    if abs(angle_z) < f32(0.05):
        angle_y = 0.0
    return WorldObjectMotion(state.contact_counter, linear, (angle_x, angle_y, angle_z))
