"""Packed world-contact sample decoding used by 0x45d1f0."""
from dataclasses import dataclass
import math
import struct

from client.collision_heading import heading_byte_for_world_coordinates
from client.tire_response import f32


_FIXED_16_SCALE = f32(1.5258789e-5)


@dataclass(frozen=True)
class CollisionWorldSample:
    position: tuple[float, float, float]
    vertical_value: float
    radius: float
    kind: int


@dataclass(frozen=True)
class WorldContactClassification:
    decision: int
    type_code: int
    sample_id: int
    trigger_tier: int | None
    trigger_state_after: int
    trigger_angle_after: int | None = None
    trigger_substate_after: int | None = None


@dataclass(frozen=True)
class TriggerSlotAllocation:
    result: int
    slots: bytes


@dataclass(frozen=True)
class WorldContactUpdate:
    classification: WorldContactClassification
    trigger_slots: bytes
    sample_state: bytes


def allocate_trigger_slot(slots, resource_ids, category, owner_pointer):
    """Translate the 256-entry, 0x18-byte runtime trigger slot allocator at 0x407710."""
    slots = bytes(slots)
    resources = tuple(resource_ids)
    if len(slots) != 0x1800:
        raise ValueError('trigger slot image must contain exactly 256 0x18-byte records')
    if len(resources) < 256 or any(type(value) is not int or not 0 <= value <= 0xffffffff
                                   for value in resources[:256]):
        raise ValueError('trigger resource table must contain 256 uint32 values')
    if type(category) is not int or not 0 <= category <= 0xffffffff:
        raise ValueError('trigger category must be a uint32')
    if type(owner_pointer) is not int or not 0 <= owner_pointer <= 0xffffffff:
        raise ValueError('trigger owner must be a uint32')

    index = next((i for i in range(256)
                  if struct.unpack_from('<I', slots, i * 0x18)[0] == 0), 256)
    failure = ((index & 0xffffff00) | 0xff)
    if index == 256 or category > 0xff:
        return TriggerSlotAllocation(failure, slots)
    resource = resources[category]
    if resource == 0:
        return TriggerSlotAllocation(failure, slots)

    updated = bytearray(slots)
    offset = index * 0x18
    struct.pack_into('<I', updated, offset, resource)
    struct.pack_into('<I', updated, offset + 4, owner_pointer)
    struct.pack_into('<III', updated, offset + 0x0c, 2, 1, 0)
    return TriggerSlotAllocation(index, bytes(updated))


def decode_collision_world_sample(record):
    """Decode one 0x14-byte packed sample, matching the pure 0x42db70 path."""
    if len(record) < 0x14:
        raise ValueError('world collision sample must span 0x14 bytes')
    kind = record[0x13] & 3
    value = struct.unpack_from('<h', record, 0x0c)[0]
    radius = {
        0: 3.,
        1: 12.,
        2: 2.,
        3: 1.,
    }[kind]
    if kind == 1:
        value >>= 1
    elif kind == 2:
        value = ((value << 1) & 0xffff)
        value = value - 0x10000 if value & 0x8000 else value
    position = tuple(f32(struct.unpack_from('<i', record, offset)[0] *
                          _FIXED_16_SCALE)
                     for offset in (0, 4, 8))
    vertical = f32((value << 8) * _FIXED_16_SCALE)
    return CollisionWorldSample(position, vertical, f32(radius), kind)


def world_sample_overlaps_body(body, sample):
    """Translate the radius and oriented horizontal prefilter in 0x45d1f0."""
    if len(body) < 0x354:
        raise ValueError('collision body image must cover the world-sample fields')
    if not isinstance(sample, CollisionWorldSample):
        raise ValueError('a decoded world collision sample is required')

    x = f32(sample.position[0] - struct.unpack_from('<f', body, 8)[0])
    z = f32(sample.position[2] - struct.unpack_from('<f', body, 0x10)[0])
    horizontal_squared = f32(f32(x * x) + f32(z * z))
    horizontal_distance = f32(math.sqrt(horizontal_squared))
    body_radius = struct.unpack_from('<f', body, 0xD8)[0]
    if not horizontal_distance < f32(sample.vertical_value + body_radius):
        return False
    if not struct.unpack_from('<f', body, 0x350)[0] < sample.radius:
        return False

    matrix = struct.unpack_from('<9f', body, 0x9C)
    extent_x, extent_y, extent_z = struct.unpack_from('<3f', body, 0xCC)
    projections = tuple(f32(f32(f32(z * matrix[z_index]) + 0.0) +
                             f32(x * matrix[x_index]))
                       for z_index, x_index in ((7, 1), (6, 0), (8, 2)))
    for projection, extent in zip(projections, (extent_y, extent_x, extent_z)):
        if not abs(f32(projection)) < f32(sample.vertical_value + extent):
            return False
    return True


def classify_world_contact(body, record, trigger_state, allocation_result=0xff):
    """Translate the classifier decisions and trigger-state failure path at 0x42d9f0.

    Trigger slot allocation is supplied by the runtime table model. The
    heading byte is computed by the fixed-angle helper at 0x6f2cc0;
    allocation exhaustion preserves the original 0xfe state transition.
    """
    if len(body) < 0x478 or len(record) < 0x14:
        raise ValueError('body and world-contact record images are too short')
    if type(trigger_state) is not int or not -128 <= trigger_state <= 255:
        raise ValueError('trigger state must fit an unsigned or signed byte')
    if type(allocation_result) is not int or not -1 <= allocation_result <= 0xffffffff:
        raise ValueError('trigger allocation result must fit a signed or unsigned dword')
    kind = record[0x13] & 3
    sample_id = struct.unpack_from('<H', record, 0x0e)[0]
    if kind == 3:
        return WorldContactClassification(2, 0x1a, sample_id, None, trigger_state)
    if kind != 2:
        return WorldContactClassification(1, 0x1d, sample_id, None, trigger_state)

    state = trigger_state - 256 if trigger_state > 127 else trigger_state
    if state != -1:
        return WorldContactClassification(0, 0x19, sample_id, None, trigger_state)
    active_trigger = body[6] != 0 and (body[0x474] & 2) != 0
    speed_gate = 0. if active_trigger else 18750.
    object_gate = struct.unpack_from('<f', body, 0x3c0)[0]
    if speed_gate > object_gate:
        return WorldContactClassification(1, 0x19, sample_id, None, trigger_state)
    tier = 3 if speed_gate + speed_gate <= object_gate else 2
    allocated_byte = allocation_result & 0xff
    allocated_signed = allocated_byte - 256 if allocated_byte > 127 else allocated_byte
    if allocated_signed >= 0:
        x = struct.unpack_from('<f', body, 0x14)[0]
        z = struct.unpack_from('<f', body, 0x1c)[0]
        heading_byte = heading_byte_for_world_coordinates(x, z)
        return WorldContactClassification(-1, 0x19, sample_id, tier,
                                          allocated_byte, heading_byte, 0)
    return WorldContactClassification(-1, 0x19, sample_id, tier, 0xfe)


def update_world_contact(body, record, sample_state, trigger_slots,
                         resource_ids, owner_pointer):
    """Compose 0x42d9f0 classification, 0x407710 allocation and 0x4077a0 writes."""
    sample_state = bytes(sample_state)
    if len(sample_state) != 3:
        raise ValueError('world-contact sample state must contain exactly three bytes')
    classification = classify_world_contact(body, record, sample_state[0])
    trigger_slots = bytes(trigger_slots)
    if classification.trigger_tier is None:
        if len(trigger_slots) != 0x1800:
            raise ValueError('trigger slot image must contain exactly 256 0x18-byte records')
        return WorldContactUpdate(classification, trigger_slots, sample_state)

    allocation = allocate_trigger_slot(
        trigger_slots, resource_ids, classification.trigger_tier, owner_pointer)
    classification = classify_world_contact(
        body, record, sample_state[0], allocation_result=allocation.result)
    updated_slots = bytearray(allocation.slots)
    if classification.trigger_angle_after is not None:
        slot_index = classification.trigger_state_after
        angle = classification.trigger_angle_after
        signed_angle = angle - 0x100 if angle & 0x80 else angle
        struct.pack_into('<IIi', updated_slots, slot_index * 0x18 + 0x0c,
                         2, 0, signed_angle)
        updated_state = bytes((slot_index, classification.trigger_angle_after, 0))
    elif classification.trigger_state_after == 0xfe:
        updated_state = bytes((0xfe,)) + sample_state[1:]
    else:
        updated_state = sample_state
    return WorldContactUpdate(classification, bytes(updated_slots), updated_state)
