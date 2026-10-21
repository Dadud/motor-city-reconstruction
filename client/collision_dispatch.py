"""Original world-collision dispatcher at mcity.exe 0x45abe0.

The dispatcher owns ordering, counter updates, candidate filtering and retries.
Geometry, terrain queries and downstream collision side effects remain explicit
callbacks because their original bodies have separate source boundaries.
"""
from dataclasses import dataclass
import math
import struct


def _i16(image, offset):
    return struct.unpack_from('<h', image, offset)[0]


def _u8(image, offset):
    return image[offset]


def _u32(image, offset):
    return struct.unpack_from('<I', image, offset)[0]


def _i32(image, offset):
    return struct.unpack_from('<i', image, offset)[0]


def _f32(image, offset):
    return struct.unpack_from('<f', image, offset)[0]


def _put_i16(image, offset, value):
    value = ((value + 0x8000) & 0xffff) - 0x8000
    struct.pack_into('<h', image, offset, value)


def _put_f32(image, offset, value):
    struct.pack_into('<f', image, offset, value)


def _fadd(a, b):
    return struct.unpack('<f', struct.pack('<f', a + b))[0]


def _fsub(a, b):
    return struct.unpack('<f', struct.pack('<f', a - b))[0]


def _round_f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


@dataclass
class CollisionDispatchServices:
    """Required original child behavior, supplied at the boundary."""
    initialize_contact_fields: object
    terrain_query: object
    support_correction: object
    high_speed_action: object
    inactive_object_update: object
    pair_filter: object
    pair_response: object
    after_candidates: object
    contact_followup: object
    post_collision: object
    final_update: object

    def __post_init__(self):
        for name, callback in vars(self).items():
            if not callable(callback):
                raise ValueError(f'{name} callback is required')


@dataclass
class CollisionDispatchWorld:
    """Shared candidate table and fallback data used by 0x45abe0."""
    candidates: list
    mode_records: tuple
    impact_record: object
    fallback_direction: tuple
    contact_neighbor_rows: tuple = ()
    contact_index_limit: int = -1
    impact_count: int = 0


def _record_mode(world, index):
    if not 0 <= index < len(world.mode_records):
        raise ValueError('owner mode-record index is outside the supplied table')
    record = world.mode_records[index]
    if len(record) < 0x1c:
        raise ValueError('owner mode record must include +0x18')
    return struct.unpack_from('<i', record, 0x18)[0]


def _fallback_normal(values):
    if len(values) != 3:
        raise ValueError('fallback direction requires three components')
    vector = tuple(-float(value) for value in values)
    squared = _round_f32(vector[0] * vector[0] + vector[1] * vector[1] +
                         vector[2] * vector[2])
    if squared != 0.0:
        length = math.sqrt(squared)
        inverse = struct.unpack('<f', struct.pack('<f', 1.0 / length))[0]
        vector = tuple(struct.unpack('<f', struct.pack('<f', value * inverse))[0]
                       for value in vector)
    return vector


def dispatch_world_collision(owner, world, services):
    """Run one bounded dispatcher call and return its observable decisions.

    `owner` is the mutable original owner image. Each child callback receives
    that same image so mutations are visible to later stages. The world keeps
    earlier candidate images in insertion order; `impact_count` is the original
    global count before this call.
    """
    if not isinstance(owner, bytearray) or len(owner) < 0x414:
        raise ValueError('owner image must be a mutable bytearray through +0x413')
    if not isinstance(world, CollisionDispatchWorld):
        raise ValueError('collision world state is required')
    if not isinstance(services, CollisionDispatchServices):
        raise ValueError('all original child callbacks are required')
    count = world.impact_count
    if type(count) is not int or count < 0 or count > len(world.candidates):
        raise ValueError('impact count must index the supplied candidate prefix')

    owner[0x3c4:0x400] = bytes(0x3c)
    services.initialize_contact_fields(owner)
    countdown = _i32(owner, 0x410)
    if countdown > 0:
        struct.pack_into('<i', owner, 0x410, countdown - 1)

    pairs = []
    response_count = 0
    if _u8(owner, 4) == 0:
        return {'active': False, 'pairs': (), 'responses': 0,
                'impact_count': count}

    contact = _i16(owner, 0x3bc)
    if contact == 0 and services.terrain_query(owner) == 0:
        _put_i16(owner, 0x3bc, contact + 1)
        contact = 1
    if _f32(owner, 0x350) >= _round_f32(0.6):
        if contact == 0:
            _put_i16(owner, 0x3bc, 1)
            contact = 1
    elif contact != 0 and services.support_correction(owner) != 0:
        _put_f32(owner, 0x350, 0.0)
        if (_u8(owner, 6) != 0 and
                _f32(owner, 0xc4) > _round_f32(0.9722222)):
            services.high_speed_action(owner)
        if services.terrain_query(owner) != 0:
            _put_i16(owner, 0x3bc, 0)
            contact = 0
    if contact != 0:
        _put_i16(owner, 0x3bc, contact + 1)
    if _u8(owner, 7) == 0:
        services.inactive_object_update(owner)

    flags = _u32(owner, 0x474)
    mode_index = _u32(owner, 0x464)
    collision_allowed = (_i32(owner, 0x410) == 0 and
                         (_u8(owner, 6) == 0 or (flags & 0x200) == 0 or
                          _record_mode(world, mode_index) != 6))
    if collision_allowed:
        if count == len(world.candidates):
            world.candidates.append(owner)
        else:
            world.candidates[count] = owner
        for candidate_index in range(count):
            other = world.candidates[candidate_index]
            radius = _fadd(_f32(other, 0xd8), _f32(owner, 0xd8))
            if not all(abs(_fsub(_f32(owner, axis), _f32(other, axis))) < radius
                       for axis in (0x10, 0x08, 0x0c)):
                continue
            attempts = 0
            had_accept = False
            response = False
            while True:
                accepted = services.pair_filter(owner, other)
                attempts += 1
                if accepted == 0:
                    if not had_accept:
                        break
                    response = True
                    break
                had_accept = True
                if attempts > 32:
                    response = True
                    break
            pairs.append((candidate_index, attempts, bool(had_accept)))
            if response:
                normal = _fallback_normal(world.fallback_direction)
                services.pair_response(owner, other, world.impact_record, normal)
                response_count += 1
        world.impact_count = count + 1
        services.after_candidates(owner)
        if _u8(owner, 0x400) & 0x40:
            contact_index = _u32(owner, 0x374)
            services.contact_followup(owner, contact_index)
            if not 0 <= contact_index < len(world.contact_neighbor_rows):
                raise ValueError('contact index is outside supplied neighbor rows')
            row = world.contact_neighbor_rows[contact_index]
            if len(row) < 8:
                raise ValueError('contact neighbor row must contain eight indices')
            for slot in range(8):
                neighbor = row[slot]
                if -1 < neighbor <= world.contact_index_limit:
                    services.contact_followup(owner, neighbor)
    services.post_collision(owner)
    services.final_update(owner)
    return {'active': True, 'pairs': tuple(pairs), 'responses': response_count,
            'impact_count': world.impact_count, 'collision_allowed': collision_allowed}
