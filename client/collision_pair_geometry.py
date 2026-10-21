"""Recovered oriented-box point test used by collision pair routine 0x45af30."""
from dataclasses import dataclass
import math
import struct


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


@dataclass(frozen=True)
class OrientedCollisionBox:
    center: tuple
    axes: tuple
    half_extents: tuple

    def __post_init__(self):
        if len(self.center) != 3 or len(self.axes) != 3 or len(self.half_extents) != 3:
            raise ValueError('collision box requires a 3D center, basis, and extents')
        if any(len(axis) != 3 for axis in self.axes):
            raise ValueError('each collision box axis must have three components')
        if any(not math.isfinite(float(x)) for x in
               (*self.center, *self.half_extents,
                *(component for axis in self.axes for component in axis))):
            raise ValueError('collision box values must be finite')
        if any(float(value) < 0 for value in self.half_extents):
            raise ValueError('collision half extents cannot be negative')


@dataclass(frozen=True)
class OrientedBoxPointResult:
    inside: bool
    owner_local_point: tuple
    target_world_point: tuple | None
    target_direction: tuple | None


@dataclass(frozen=True)
class OwnerBoxPointResult:
    inside: bool
    target_local_point: tuple
    owner_world_point: tuple | None
    owner_direction: tuple | None


def oriented_box_point_test(owner, target, local_point):
    """Translate original helper 0x45b8e0 for a normalized target-local point.

    `local_point` components are the helper's three scalar arguments. The
    target's half extents scale its local point before projection into owner
    space. On a hit, the helper also publishes the target-space world contact
    point and the normalized target-basis direction used by its caller.
    """
    if not isinstance(owner, OrientedCollisionBox) or not isinstance(target, OrientedCollisionBox):
        raise ValueError('owner and target collision boxes are required')
    if len(local_point) != 3 or any(not math.isfinite(float(x)) for x in local_point):
        raise ValueError('normalized local point must contain three finite values')
    point = tuple(_f32(x) for x in local_point)
    offset = tuple(_f32(target.center[i] - owner.center[i]) for i in range(3))
    projected = []
    for owner_axis in owner.axes:
        center_projection = sum(owner_axis[k] * offset[k] for k in range(3))
        extent_projection = sum(
            _f32(_f32(sum(owner_axis[k] * target.axes[axis][k]
                          for k in range(3))) * target.half_extents[axis])
            * point[axis]
            for axis in range(3))
        projected.append(_f32(center_projection + extent_projection))
    projected = tuple(projected)
    inside = all(-owner.half_extents[i] <= projected[i] <= owner.half_extents[i]
                 for i in range(3))
    if not inside:
        return OrientedBoxPointResult(False, projected, None, None)

    world_point = tuple(_f32(target.center[k] + sum(
        target.axes[axis][k] * target.half_extents[axis] * point[axis]
        for axis in range(3))) for k in range(3))
    direction = tuple(
        _f32(sum(target.axes[axis][k] * point[axis] for axis in range(3)))
        for k in range(3))
    squared_length = _f32(sum(value * value for value in direction))
    if squared_length != 0.0:
        inverse_length = _f32(1.0 / math.sqrt(squared_length))
        direction = tuple(_f32(value * inverse_length) for value in direction)
    return OrientedBoxPointResult(True, projected, world_point, direction)


def _owner_point_test(owner, target, local_point, with_direction):
    if not isinstance(owner, OrientedCollisionBox) or not isinstance(target, OrientedCollisionBox):
        raise ValueError('owner and target collision boxes are required')
    if len(local_point) != 3 or any(not math.isfinite(float(x)) for x in local_point):
        raise ValueError('normalized local point must contain three finite values')
    point = tuple(_f32(x) for x in local_point)
    offset = tuple(_f32(target.center[i] - owner.center[i]) for i in range(3))
    projected = []
    for target_axis in target.axes:
        center_projection = sum(target_axis[k] * offset[k] for k in range(3))
        extent_projection = sum(
            _f32(_f32(sum(owner.axes[axis][k] * target_axis[k]
                          for k in range(3))) * owner.half_extents[axis])
            * point[axis]
            for axis in range(3))
        projected.append(_f32(extent_projection - center_projection))
    projected = tuple(projected)
    inside = all(-target.half_extents[i] <= projected[i] <= target.half_extents[i]
                 for i in range(3))
    if not inside:
        return OwnerBoxPointResult(False, projected, None, None)

    world_point = tuple(_f32(owner.center[k] + sum(
        owner.axes[axis][k] * owner.half_extents[axis] * point[axis]
        for axis in range(3))) for k in range(3))
    if not with_direction:
        return OwnerBoxPointResult(True, projected, world_point, None)
    direction = tuple(_f32(-sum(owner.axes[axis][k] * point[axis]
                                for axis in range(3))) for k in range(3))
    squared_length = _f32(sum(value * value for value in direction))
    if squared_length != 0.0:
        inverse_length = _f32(1.0 / math.sqrt(squared_length))
        direction = tuple(_f32(value * inverse_length) for value in direction)
    return OwnerBoxPointResult(True, projected, world_point, direction)


def owner_point_direction_test(owner, target, local_point):
    """Translate original 0x45bb70: test an owner point and publish its normal."""
    return _owner_point_test(owner, target, local_point, True)


def owner_point_contact_test(owner, target, local_point):
    """Translate original 0x45be10: test an owner point and publish contact point."""
    return _owner_point_test(owner, target, local_point, False)
