"""Reconstructed task-list registration from original MCity FUN_00567940.

This builds the two callback lists for one game-session schedule. Callback
identifiers remain original x86 entry addresses until their behavior has a
portable implementation; this module does not execute the original binary.
"""
from dataclasses import dataclass

from .scheduler import ScheduledCall, insert_callback


@dataclass(frozen=True)
class GameTaskLists:
    primary: tuple[ScheduledCall, ...]
    secondary: tuple[ScheduledCall, ...]
    primary_capacity: int
    secondary_capacity: int


def _pointer(value, name):
    if type(value) is not int or not 0 < value < (1 << 32):
        raise ValueError(f'{name} must be a non-null 32-bit object address')
    return value


def _count(value, name):
    if type(value) is not int or value < 0 or value > 0x7fffffff:
        raise ValueError(f'{name} must be a nonnegative signed 32-bit count')
    return value


def build_game_task_lists(vehicles, world_objects, vehicle_flags,
                          dynamic_service_payload, capacity_source_count):
    """Translate the ordered registrations in original routine 0x567940.

    The caller supplies addresses in the order of the original global arrays,
    each vehicle's already-observed flags, the value returned by original
    ``FUN_004870c0(10)``, and the distinct count used in the allocator's
    capacity formulas. Those last two values are required observations; this
    builder does not guess the owning globals or service object.

    The original task-list allocator receives capacities
    ``world_count*3 + 12 + capacity_source_count*5`` and
    ``world_count + 8 + capacity_source_count*4``. Insertion remains stable for
    equal priorities because it delegates to the verified scheduler routine.
    """
    vehicles = tuple(_pointer(value, 'vehicle address') for value in vehicles)
    world_objects = tuple(_pointer(value, 'world object address') for value in world_objects)
    vehicle_flags = tuple(vehicle_flags)
    if len(vehicle_flags) != len(vehicles):
        raise ValueError('one observed flag word is required per vehicle')
    if any(type(flags) is not int or not 0 <= flags <= 0xffffffff for flags in vehicle_flags):
        raise ValueError('vehicle flags must be uint32 observations')
    if type(dynamic_service_payload) is not int or not 0 <= dynamic_service_payload <= 0xffffffff:
        raise ValueError('service payload must be a uint32 observation')
    capacity_source_count = _count(capacity_source_count, 'capacity source count')

    # Callback order here is registration order. insert_callback reproduces the
    # original stable priority sort performed by FUN_00565d20.
    primary: list[ScheduledCall] = []
    secondary: list[ScheduledCall] = []

    def add(queue, priority, callback, payload=0):
        insert_callback(queue, ScheduledCall(priority, callback, payload))

    def each(queue, priority, callback, owners):
        for owner in owners:
            add(queue, priority, callback, owner)

    # Primary task list.
    each(primary, 6, 0x00520c20, vehicles)
    each(primary, 6, 0x00520c20, world_objects)
    add(primary, 6, 0x0042d730)
    add(primary, 8, 0x0043f550)
    add(primary, 10, 0x00487790, dynamic_service_payload)
    each(primary, 0x15, 0x00469010, vehicles)
    each(primary, 0x1e, 0x0053c140, vehicles)
    each(primary, 0x1e, 0x005779d0, world_objects)
    add(primary, 0x1e, 0x004265f0)
    add(primary, 0x1e, 0x00426730)
    each(primary, 0x28, 0x0045abe0, vehicles)
    add(primary, 0x28, 0x004265b0)
    each(primary, 0x28, 0x0045abe0, world_objects)
    each(primary, 0x32, 0x0043d6e0, vehicles)
    add(primary, 0x32, 0x00424ec0)
    add(primary, 0x32, 0x00426770)
    add(primary, 100, 0x0055f520)
    add(primary, 0x6e, 0x0055d300)
    add(primary, 0x78, 0x005678f0)

    # Secondary task list.
    add(secondary, 6, 0x0042d780)
    add(secondary, 6, 0x00459df0)
    for owner, flags in zip(vehicles, vehicle_flags):
        if ((flags & 1 and flags & 2) or flags & 4):
            add(secondary, 0x19, 0x00585790, owner)
    each(secondary, 0x1e, 0x00520450, vehicles)
    each(secondary, 0x1e, 0x00520450, world_objects)
    add(secondary, 0x23, 0x0040adb0)
    each(secondary, 100, 0x0043f9d0, vehicles)
    add(secondary, 100, 0x0055f540)
    add(secondary, 0x6e, 0x005850b0)

    world_count = len(world_objects)
    primary_capacity = world_count * 3 + 12 + capacity_source_count * 5
    secondary_capacity = world_count + 8 + capacity_source_count * 4
    if max(primary_capacity, secondary_capacity) > 0x7fffffff:
        raise ValueError('task-list capacity overflows signed int32')
    return GameTaskLists(tuple(primary), tuple(secondary),
        primary_capacity, secondary_capacity)
