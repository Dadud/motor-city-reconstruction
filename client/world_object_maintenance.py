"""World-object maintenance pass from original FUN_004265f0."""
from dataclasses import dataclass
from math import sqrt

from .tire_response import f32
from .world_object_damping import WorldObjectMotion


@dataclass(frozen=True)
class WorldObjectMaintenance:
    motion: WorldObjectMotion
    active: bool
    maintenance_value: float  # owner +0x350 (pfVar3[0xcf])
    reference_value: float  # owner +0xd8 (pfVar3[0x31])


def maintain_world_object(state, update_motion):
    """Run the maintenance after invoking the scheduled 0x520c20 child.

    The child is mandatory and injected because its behavior is a separate
    callback; this routine does not silently substitute a no-op for it.
    """
    if not isinstance(state, WorldObjectMaintenance):
        raise ValueError('explicit world-object maintenance state required')
    if not callable(update_motion):
        raise ValueError('the 0x520c20 child callback is required')
    if type(state.active) is not bool:
        raise ValueError('active must be an observed boolean')
    maintenance_value, reference_value = map(f32, (state.maintenance_value, state.reference_value))
    if not state.active:
        return state

    motion = update_motion(state.motion)
    linear = tuple(map(f32, motion.linear_velocity))
    angular = tuple(map(f32, motion.angular_velocity))
    magnitude = sqrt(sum(float(value) * float(value) for value in angular))
    if maintenance_value < reference_value:
        factor = f32(0.99)
        linear = tuple(f32(value * factor) for value in linear)
        angular = tuple(f32(value * factor) for value in angular)

    if magnitude > 10.0:
        factor = 10.0 / magnitude
        angular = tuple(f32(value * factor) for value in angular)

    if (motion.contact_counter & 0xffff) > 32 and maintenance_value == 0.0 and magnitude == 0.0:
        angular = (f32(angular[0] + f32(0.01)), angular[1], angular[2])
    return WorldObjectMaintenance(
        WorldObjectMotion(motion.contact_counter, linear, angular), state.active,
        maintenance_value, reference_value)


def maintain_world_objects(objects, update_motion):
    """Apply 0x4265f0 in supplied original-array order; inactive owners are skipped."""
    return tuple(maintain_world_object(item, update_motion) for item in objects)
