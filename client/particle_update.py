"""Particle simulation state transitions recovered from the MCO client."""
import struct
from fractions import Fraction

from .particle_spawn import _exact_float, _x87_add, _x87_f32, _x87_mul
from .particle_spawn import POOL_CAPACITY, RECORD_BYTES

_MASK32 = 0xffffffff
TRAIL_CAPACITY = 200
TRAIL_RECORD_BYTES = 0x3c


def _signed32(value):
    value &= _MASK32
    return value - 0x100000000 if value & 0x80000000 else value


def advance_particle_motion(pool, source_y_acceleration, current_tick,
                            last_update_tick):
    """Advance the original 600-slot particle pool for elapsed half-ticks.

    Source acceleration is keyed by each record's source token. The original
    multiplies size rates by the integer tick delta, applies source Y
    acceleration to vertical velocity, then integrates position at 1/32
    world-time units per tick. Inactive and source-less records are untouched.
    """
    if len(pool) != POOL_CAPACITY or any(
            not isinstance(slot, bytearray) or len(slot) != RECORD_BYTES for slot in pool):
        raise ValueError('particle pool must contain 600 records of 0x6c bytes')
    if type(current_tick) is not int or not -0x80000000 <= current_tick <= 0x7fffffff:
        raise ValueError('current tick must fit signed int32')
    if type(last_update_tick) is not int or not -0x80000000 <= last_update_tick <= 0x7fffffff:
        raise ValueError('last update tick must fit signed int32')

    half_tick = current_tick >> 1
    delta = _signed32(half_tick - last_update_tick)
    if delta <= 0:
        return last_update_tick

    tick_value = Fraction(delta)
    step = _x87_mul(tick_value, _exact_float(0.03125))
    for slot in pool:
        if struct.unpack_from('<h', slot, 4)[0] == 0:
            continue
        source = struct.unpack_from('<I', slot, 0)[0]
        if source == 0:
            continue
        try:
            y_acceleration = _exact_float(source_y_acceleration[source])
        except KeyError as exc:
            raise ValueError(f'missing source acceleration for token {source:#x}') from exc

        size = _exact_float(struct.unpack_from('<f', slot, 0x24)[0])
        size_rate = _exact_float(struct.unpack_from('<f', slot, 0x2c)[0])
        struct.pack_into('<f', slot, 0x24,
                         _x87_f32(_x87_add(_x87_mul(tick_value, size_rate), size)))
        size2 = _exact_float(struct.unpack_from('<f', slot, 0x30)[0])
        size_rate2 = _exact_float(struct.unpack_from('<f', slot, 0x34)[0])
        struct.pack_into('<f', slot, 0x30,
                         _x87_f32(_x87_add(_x87_mul(tick_value, size_rate2), size2)))

        velocity_y = _exact_float(struct.unpack_from('<f', slot, 0x1c)[0])
        struct.pack_into('<f', slot, 0x1c,
                         _x87_f32(_x87_add(_x87_mul(tick_value, y_acceleration),
                                           velocity_y)))
        for position_offset, velocity_offset in ((0xc, 0x18), (0x10, 0x1c),
                                                 (0x14, 0x20)):
            position = _exact_float(struct.unpack_from('<f', slot, position_offset)[0])
            velocity = _exact_float(struct.unpack_from('<f', slot, velocity_offset)[0])
            struct.pack_into('<f', slot, position_offset,
                             _x87_f32(_x87_add(_x87_mul(step, velocity), position)))
    return half_tick


def _c_divide(numerator, denominator):
    quotient = abs(numerator) // abs(denominator)
    return -quotient if (numerator < 0) != (denominator < 0) else quotient


def advance_particle_trails(records, definitions, type_counts):
    """Update the selected 200-entry trail-effect pool from its definitions.

    Each record's active count decreases by one. A byte progress value is the
    signed-int32 product of count and definition weight divided by the
    definition duration; a zero byte clears the record. Type counts increment
    for active definitions with IDs in the original 1..25 bucket range.
    """
    if len(records) != TRAIL_CAPACITY or any(
            not isinstance(record, bytearray) or len(record) != TRAIL_RECORD_BYTES
            for record in records):
        raise ValueError('trail pool must contain 200 records of 0x3c bytes')
    if len(type_counts) != 26:
        raise ValueError('trail type counts must contain 26 entries')
    for record in records:
        count = struct.unpack_from('<i', record, 4)[0]
        if count == 0:
            continue
        token = struct.unpack_from('<I', record, 0)[0]
        try:
            definition = definitions[token]
        except KeyError as exc:
            raise ValueError(f'missing trail definition for token {token:#x}') from exc
        if len(definition) < 0x84:
            raise ValueError('trail definition must contain at least 0x84 bytes')
        effect_type = struct.unpack_from('<i', definition, 0)[0]
        duration = struct.unpack_from('<i', definition, 0x70)[0]
        weight = definition[0x83]
        if duration == 0:
            raise ValueError('zero trail duration is outside the normal domain')
        if 0 < effect_type < 0x1a:
            type_counts[effect_type] = _signed32(type_counts[effect_type] + 1)

        product = _signed32(count * weight)
        progress = _c_divide(product, duration) & 0xff
        record[0x2b] = progress
        count = _signed32(count - 1)
        if progress == 0:
            count = 0
        struct.pack_into('<i', record, 4, count)
