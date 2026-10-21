"""Port of the per-object motion and vertex-transform update at 0x520250."""
from dataclasses import dataclass

from .matrix_math import (dot_3_f32, integrate_rotation_matrix,
                          float_to_word, repair_rotation_matrix,
                          transpose_3x3_words, word_to_float)
from .tire_response import f32
from .geometry_transform import transform_vertices


@dataclass(frozen=True)
class WorldObjectUpdate:
    object_id: int
    active: bool
    position: tuple[float, float, float]
    linear_velocity: tuple[float, float, float]
    center_of_mass: tuple[float, float, float]
    rotation: tuple[float, ...]
    angular_velocity: tuple[float, float, float]
    projection_vectors: tuple[float, ...]
    local_vertices: tuple[float, ...]
    world_vertices: tuple[float, ...]
    transposed_rotation: tuple[float, ...] = (0.0,) * 9
    projected: tuple[float, ...] = (0.0,) * 3


def update_world_object(state: WorldObjectUpdate, *, object_phase: int,
                        repair_matrix=None):
    """Update motion, matrices, projections, and the object's 22 world vertices.

    This mirrors the original's 1/32-second velocity integration and center
    of mass preservation. The source's periodic matrix correction and mode-6
    vertex transform are included; a repair override is available for probes.
    """
    if not isinstance(state, WorldObjectUpdate):
        raise TypeError('WorldObjectUpdate required')
    if type(object_phase) is not int or not 0 <= object_phase <= 0xffffffff:
        raise ValueError('object phase must be uint32')
    if not state.active:
        return state
    if len(state.position) != 3 or len(state.linear_velocity) != 3 or len(state.center_of_mass) != 3 or len(state.angular_velocity) != 3:
        raise ValueError('world vectors must have three components')
    if len(state.rotation) != 9 or len(state.projection_vectors) != 3 or len(state.local_vertices) != 66 or len(state.world_vertices) != 66:
        raise ValueError('world object requires 3x3 matrices and 22 input/output vertices')

    position = tuple(f32(v) for v in state.position)
    velocity = tuple(f32(v) for v in state.linear_velocity)
    center = tuple(f32(v) for v in state.center_of_mass)
    rotation = tuple(f32(v) for v in state.rotation)
    angular = tuple(f32(v) for v in state.angular_velocity)
    # Original x87 expression order, stored to the three local float slots.
    old_com_world = tuple(f32(center[2] * rotation[6 + axis] +
                              center[1] * rotation[3 + axis] +
                              center[0] * rotation[axis] + position[axis])
                          for axis in range(3))
    delta = tuple(f32(v * f32(0.03125)) for v in angular)
    rotation = integrate_rotation_matrix(rotation, delta)
    new_position = tuple(f32((f32(velocity[axis] * f32(0.03125)) +
                              old_com_world[axis]) -
                             (center[2] * rotation[6 + axis] +
                              center[1] * rotation[3 + axis] +
                              center[0] * rotation[axis] +
                              position[axis]) + position[axis])
                         for axis in range(3))

    if ((object_phase >> 1) & 0xff) == state.object_id:
        selected_repair = repair_matrix or repair_rotation_matrix
        if not callable(selected_repair):
            raise ValueError('matrix repair must be callable')
        rotation = tuple(f32(v) for v in selected_repair(rotation, 10))
        if len(rotation) != 9:
            raise ValueError('matrix repair must return nine values')

    transposed = tuple(word_to_float(word) for word in
                       transpose_3x3_words(tuple(float_to_word(v) for v in rotation)))
    projections = tuple(dot_3_f32(rotation[offset:offset + 3],
                                  state.projection_vectors)
                       for offset in (0, 3, 6))
    result = WorldObjectUpdate(state.object_id, state.active, new_position, velocity,
                               center, rotation, tuple(f32(v) for v in state.angular_velocity),
                               tuple(f32(v) for v in state.projection_vectors),
                               tuple(f32(v) for v in state.local_vertices),
                               transform_vertices(state.local_vertices, rotation,
                                                  new_position), transposed,
                               projections)
    return result, projections
