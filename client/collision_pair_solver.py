"""Bounded source translation of the oriented-box pair resolver at 0x45af30."""
from dataclasses import dataclass, replace
import itertools
import math
import struct

from client.collision_pair_geometry import (
    OrientedCollisionBox,
    oriented_box_point_test,
    owner_point_contact_test,
    owner_point_direction_test,
    select_pair_contact_normal,
)


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


@dataclass(frozen=True)
class CollisionPairBody:
    box: OrientedCollisionBox
    mass: float = 1.0
    mode: int = 0
    gate: float = 0.0
    peer_gate: float = 0.0


@dataclass(frozen=True)
class CollisionPairResult:
    collided: bool
    owner: CollisionPairBody
    target: CollisionPairBody
    correction_steps: int
    last_contact: tuple | None
    last_selected_normal: tuple | None


_AXIS_SAMPLES = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.),
                 (-1., 0., 0.), (0., -1., 0.), (0., 0., -1.))
_GRID_SAMPLES = tuple(itertools.product((-1., -.5, 0., .5, 1.), repeat=3))


def _first_hit(test, owner, target, points):
    for point in points:
        result = test(owner, target, point)
        if result.inside:
            return result
    return None


def _has_sample_contact(owner, target):
    forward_axis = _first_hit(oriented_box_point_test, owner, target, _AXIS_SAMPLES)
    if forward_axis is not None:
        return forward_axis, None, None
    forward_grid = _first_hit(oriented_box_point_test, owner, target, _GRID_SAMPLES)
    if forward_grid is not None:
        normal = select_pair_contact_normal(owner, target,
                                            forward_grid.owner_local_point, False)
        return forward_grid, normal.normal, False
    reverse_axis = _first_hit(owner_point_direction_test, owner, target, _AXIS_SAMPLES)
    if reverse_axis is not None:
        return reverse_axis, reverse_axis.owner_direction, True
    reverse_grid = _first_hit(owner_point_contact_test, owner, target, _GRID_SAMPLES)
    if reverse_grid is not None:
        normal = select_pair_contact_normal(owner, target,
                                            reverse_grid.target_local_point, True)
        return reverse_grid, normal.normal, True
    return None, None, None


def _response_gates(owner, target):
    owner_mode = bool(owner.mode)
    target_mode = bool(target.mode)
    owner_gate = owner_mode and not target_mode
    target_gate = target_mode and not owner_mode
    if target.peer_gate < owner.gate:
        owner_gate = True
    if owner.peer_gate < target.gate:
        target_gate = True
    if owner_gate and target_gate:
        owner_gate = target_gate = False
    return owner_gate, target_gate


def resolve_collision_pair(owner, target, max_corrections=32):
    """Apply the original 1/32 center-line correction while sampled contacts remain.

    The result describes the recovered pair routine over explicit box records.
    It does not model the separate 0x6f1320 derived-transform refresh call.
    """
    if not isinstance(owner, CollisionPairBody) or not isinstance(target, CollisionPairBody):
        raise ValueError('collision pair bodies are required')
    if not isinstance(owner.box, OrientedCollisionBox) or not isinstance(target.box, OrientedCollisionBox):
        raise ValueError('each body must contain an oriented collision box')
    if type(max_corrections) is not int or not 1 <= max_corrections <= 32:
        raise ValueError('correction limit must be between 1 and 32')
    masses = (_f32(owner.mass), _f32(target.mass))
    if any(not math.isfinite(value) for value in masses):
        raise ValueError('body masses must be finite')
    owner_gate, target_gate = _response_gates(owner, target)
    current_owner, current_target = owner, target
    steps = 0
    contact = normal = None
    for _ in range(max_corrections):
        hit, hit_normal, reverse_side = _has_sample_contact(current_owner.box, current_target.box)
        if hit is None:
            break
        contact = hit.owner_world_point if reverse_side else hit.target_world_point
        normal = hit_normal
        delta = tuple(_f32(current_target.box.center[i] - current_owner.box.center[i])
                      for i in range(3))
        squared = _f32(sum(value * value for value in delta))
        if squared != 0.0:
            inverse = _f32(1.0 / math.sqrt(squared))
            direction = tuple(_f32(value * inverse) for value in delta)
        else:
            direction = (0.0, 0.0, 0.0)
        total_mass = _f32(masses[0] + masses[1])
        owner_scale = _f32(_f32(-masses[1] / total_mass) * .03125)
        target_scale = _f32(_f32(masses[0] / total_mass) * .03125)
        owner_move = tuple(_f32(value * owner_scale) for value in direction)
        target_move = tuple(_f32(value * target_scale) for value in direction)
        if not owner_gate and not target_gate:
            owner_delta = owner_move
            target_delta = target_move
        elif target_gate:
            owner_delta = tuple(_f32(owner_move[i] - target_move[i]) for i in range(3))
            target_delta = (0.0, 0.0, 0.0)
        else:
            owner_delta = (0.0, 0.0, 0.0)
            target_delta = tuple(_f32(-owner_move[i] + target_move[i]) for i in range(3))
        owner_center = tuple(_f32(current_owner.box.center[i] + owner_delta[i])
                             for i in range(3))
        target_center = tuple(_f32(current_target.box.center[i] + target_delta[i])
                              for i in range(3))
        current_owner = replace(current_owner, box=replace(current_owner.box, center=owner_center))
        current_target = replace(current_target, box=replace(current_target.box, center=target_center))
        steps += 1
    return CollisionPairResult(steps != 0, current_owner, current_target,
                               steps, contact, normal)
