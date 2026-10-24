"""Particle simulation state transitions recovered from the MCO client."""
import struct
from fractions import Fraction
import math

from .particle_spawn import _exact_float, _x87_add, _x87_f32, _x87_mul
from .particle_spawn import POOL_CAPACITY, RECORD_BYTES, construct_particle
from .random_state import RandomState

_MASK32 = 0xffffffff
_TAU_F32 = struct.unpack('<f', struct.pack('<I', 0x40c90fdb))[0]
TRAIL_CAPACITY = 200
TRAIL_RECORD_BYTES = 0x3c


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


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


def advance_particle_frame_core(pool, sources, trail_records, type_counts,
                               frame_counter, *, random_state=None,
                               effect_mode=0):
    """Translate the direct update slice of parent routine 0x527490.

    It clears the per-frame type counters, ages the selected trail pool, and
    applies source-direction selection, frame-gated spin/orbit and color fade,
    lifetime-factor scaling, lifetime decrement and expiry respawns. Child
    emitter expansion remains outside this core.
    """
    if len(pool) != POOL_CAPACITY or any(
            not isinstance(slot, bytearray) or len(slot) != RECORD_BYTES for slot in pool):
        raise ValueError('particle pool must contain 600 records of 0x6c bytes')
    if len(type_counts) != 52:
        raise ValueError('particle type-counter block must contain 52 entries')
    if random_state is not None and not isinstance(random_state, RandomState):
        raise TypeError('random_state must be a RandomState')
    if effect_mode not in (0, 1, 2):
        raise ValueError('effect mode must be 0, 1 or 2')
    if type(frame_counter) is not int or not -0x80000000 <= frame_counter <= 0x7fffffff:
        raise ValueError('frame counter must fit signed int32')
    if any(not isinstance(record, bytearray) or len(record) != TRAIL_RECORD_BYTES
           for record in trail_records) or len(trail_records) != TRAIL_CAPACITY:
        raise ValueError('trail pool must contain 200 records of 0x3c bytes')

    animate = bool(frame_counter & 2)
    factors = {}
    for slot in pool:
        if struct.unpack_from('<h', slot, 4)[0] == 0:
            continue
        token = struct.unpack_from('<I', slot, 0)[0]
        if token == 0:
            continue
        try:
            source = sources[token]
        except KeyError as exc:
            raise ValueError(f'missing particle source for token {token:#x}') from exc
        if len(source) < 0x6c:
            raise ValueError('particle source must contain at least 0x6c bytes')
        if struct.unpack_from('<I', source, 0x68)[0] != 0:
            raise ValueError('child-emitter branch is outside core scope')
        if slot[0x68] and random_state is None:
            raise ValueError('respawn records require the shared RandomState')
        if slot[0x68] and struct.unpack_from('<h', slot, 4)[0] == 1:
            lifetime = struct.unpack_from('<h', source, 8)[0]
            cadence_divisor = struct.unpack_from('<i', source, 0xc)[0] + 1
            if lifetime == 0 or cadence_divisor <= 0:
                raise ValueError('respawn source has invalid lifetime or cadence')
        factors[token] = _exact_float(struct.unpack_from('<f', source, 0x38)[0])

    for record in trail_records:
        if struct.unpack_from('<i', record, 4)[0] == 0:
            continue
        token = struct.unpack_from('<I', record, 0)[0]
        definition = sources.get(token)
        if definition is None or len(definition) < 0x84:
            raise ValueError(f'missing complete trail definition for token {token:#x}')
        if struct.unpack_from('<i', definition, 0x70)[0] == 0:
            raise ValueError('zero trail duration is outside the normal domain')

    type_counts[:] = [0] * 52
    trail_counts = [0] * 26
    advance_particle_trails(trail_records, sources, trail_counts)
    type_counts[:26] = trail_counts

    for slot_index, slot in enumerate(pool):
        if struct.unpack_from('<h', slot, 4)[0] == 0:
            continue
        token = struct.unpack_from('<I', slot, 0)[0]
        if token == 0:
            continue
        factor = factors[token]
        if struct.unpack_from('<I', sources[token], 0x3c)[0] != 0:
            selector = struct.unpack_from('<f', slot, 0x30)[0]
            signed_rate = struct.unpack_from('<f', slot, 0x34)[0]
            if selector > 0.25:
                struct.pack_into('<f', slot, 0x34, -abs(signed_rate))
            elif selector < -0.25:
                struct.pack_into('<f', slot, 0x34, abs(signed_rate))
        if animate:
            if struct.unpack_from('<I', sources[token], 0x50)[0] != 0:
                initial = struct.unpack_from('<h', slot, 6)[0]
                remaining = struct.unpack_from('<h', slot, 4)[0]
                age_ratio = _f32((initial - remaining) *
                                 struct.unpack_from('<f', slot, 8)[0])
                base_color = bytes(slot[0x4c:0x50])
                limits = bytes(slot[0x50:0x54])
                for index, (channel, limit) in enumerate(zip(base_color, limits)):
                    # x87 FISTP rounds the binary32 product to nearest-even;
                    # subtraction is byte-sized and wraps modulo 256.
                    decrement = round(_f32(limit * age_ratio))
                    slot[0x48 + index] = (channel - decrement) & 0xff
            spin_rate = struct.unpack_from('<f', slot, 0x3c)[0]
            if spin_rate != 0.0:
                angle = struct.unpack_from('<f', slot, 0x38)[0]
                radians = _f32(angle * _TAU_F32)
                sine, cosine = _f32(math.sin(radians)), _f32(math.cos(radians))
                radius = struct.unpack_from('<f', slot, 0x40)[0]
                velocity_x = struct.unpack_from('<f', slot, 0x18)[0]
                velocity_z = struct.unpack_from('<f', slot, 0x20)[0]
                struct.pack_into('<f', slot, 0x18,
                                 _x87_f32(_x87_add(
                                     _x87_mul(_exact_float(sine), _exact_float(radius)),
                                     _exact_float(velocity_x))))
                struct.pack_into('<f', slot, 0x20,
                                 _x87_f32(_x87_add(
                                     _x87_mul(_exact_float(cosine), _exact_float(radius)),
                                     _exact_float(velocity_z))))
                vertical = _exact_float(struct.unpack_from('<f', slot, 0x44)[0])
                struct.pack_into('<f', slot, 0x44,
                                 _x87_f32(_x87_mul(factor, vertical)))
                updated_rate = _x87_f32(_x87_mul(factor, _exact_float(spin_rate)))
                struct.pack_into('<f', slot, 0x3c, updated_rate)
                struct.pack_into('<f', slot, 0x40,
                                 _f32(struct.unpack_from('<f', slot, 0x44)[0] + radius))
                struct.pack_into('<f', slot, 0x38,
                                 _f32(updated_rate + struct.unpack_from('<f', slot, 0x38)[0]))
        for offset in (0x34, 0x18, 0x1c, 0x20):
            value = _exact_float(struct.unpack_from('<f', slot, offset)[0])
            struct.pack_into('<f', slot, offset, _x87_f32(_x87_mul(factor, value)))
        remaining = struct.unpack_from('<h', slot, 4)[0]
        struct.pack_into('<h', slot, 4, (remaining - 1) & 0xffff)
        if slot[0x68] != 0 and struct.unpack_from('<h', slot, 4)[0] == 0:
            velocity = struct.unpack_from('<3f', slot, 0x18)
            if any(component != 0.0 for component in velocity):
                from .matrix_math import normalize_vector3
                direction = normalize_vector3(velocity)
                position = struct.unpack_from('<3i', slot, 0xc)
                respawns = slot[0x68]
                for _ in range(respawns):
                    random_fraction = random_state.next_unit_fraction()
                    scale = _x87_f32(_x87_add(
                        _x87_mul(_exact_float(random_fraction), _exact_float(0.75)),
                        _exact_float(0.25)))
                    spawned = construct_particle(
                        sources[token], token, position, scale, direction,
                        (0.0, 0.0, 0.0), velocity, random_state, pool,
                        frame_counter=frame_counter, effect_mode=effect_mode,
                        cadence_flag=1,
                        acceleration_alias_index=slot_index)
                    if spawned is not None:
                        child = pool[spawned]
                        life = struct.unpack_from('<h', child, 4)[0]
                        struct.pack_into('<h', child, 4, life >> 1)
                        child[0x68] = 0
    return tuple(type_counts)
