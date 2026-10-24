"""Bounded source model for the particle-record constructor at 0x527060."""
import struct
from fractions import Fraction

from .random_state import RandomState

RECORD_BYTES = 0x6c
POOL_CAPACITY = 600


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _round_x87(value):
    """Round an exact binary rational to the x87 64-bit significand."""
    if not value:
        return value
    sign = -1 if value < 0 else 1
    value = abs(value)
    numerator, denominator = value.numerator, value.denominator
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < denominator << exponent:
            exponent -= 1
    elif numerator << -exponent < denominator:
        exponent -= 1
    quantum = exponent - 63
    if quantum >= 0:
        numerator, denominator = numerator, denominator << quantum
    else:
        numerator, denominator = numerator << -quantum, denominator
    quotient, remainder = divmod(numerator, denominator)
    if remainder * 2 > denominator or (remainder * 2 == denominator and quotient & 1):
        quotient += 1
    if quantum >= 0:
        rounded = Fraction(quotient << quantum, 1)
    else:
        rounded = Fraction(quotient, 1 << -quantum)
    return sign * rounded


def _exact_float(value):
    return Fraction.from_float(float(value))


def _x87_add(left, right):
    return _round_x87(left + right)


def _x87_mul(left, right):
    return _round_x87(left * right)


def _x87_f32(value):
    return _f32(float(value))


def _float_at(data, offset):
    return struct.unpack_from('<f', data, offset)[0]


def _signed_remainder(value, divisor):
    remainder = abs(value) % abs(divisor)
    return -remainder if value < 0 else remainder


def _signed_short(value):
    value &= 0xffff
    return value - 0x10000 if value & 0x8000 else value


def construct_particle(config, source_token, position, scale, velocity_a,
                       velocity_b, acceleration, random_state, pool, *,
                       frame_counter=0, effect_mode=0, cadence_flag=0):
    """Create/update one 0x6c-byte particle slot, or return ``None``.

    ``config`` is the original 0x60-byte emitter record. The pool contains
    exactly 600 mutable record byte strings; its six-word RNG and global
    cadence/mode are supplied explicitly. This models the constructor's
    writes and gating, not the surrounding particle simulation or rendering.
    """
    if not isinstance(config, (bytes, bytearray, memoryview)) or len(config) < 0x60:
        raise ValueError('particle configuration must contain at least 0x60 bytes')
    if type(source_token) is not int or not 0 <= source_token <= 0xffffffff:
        raise ValueError('source token must fit uint32')
    if (len(position) != 3 or any(type(v) is not int or not -0x80000000 <= v <= 0x7fffffff
                                  for v in position)):
        raise ValueError('position must contain three signed int32 values')
    if not isinstance(random_state, RandomState):
        raise TypeError('random_state must be a RandomState')
    if (len(pool) != POOL_CAPACITY or
            any(not isinstance(slot, bytearray) or len(slot) != RECORD_BYTES for slot in pool)):
        raise ValueError('particle pool must contain 600 records of 0x6c bytes')
    if effect_mode not in (0, 1, 2):
        raise ValueError('effect mode must be 0, 1 or 2')
    if type(cadence_flag) is not int:
        raise ValueError('cadence flag must be an integer')

    lifetime = struct.unpack_from('<h', config, 8)[0]
    divisor = struct.unpack_from('<i', config, 0xc)[0] + 1
    if lifetime == 0 or divisor <= 0:
        raise ValueError('zero lifetime or invalid cadence divisor is outside scope')
    tick_half = frame_counter >> 1
    rem_twice = _signed_remainder(tick_half, divisor * 2)
    cadence = int(rem_twice == 0)
    if effect_mode == 2 or (effect_mode == 1 and cadence):
        return None
    if cadence_flag and _signed_remainder(tick_half, divisor) != 0:
        return None

    index = None
    smallest_life = None
    for slot_index, slot in enumerate(pool):
        active = _signed_short(struct.unpack_from('<H', slot, 4)[0])
        if active == 0:
            index = slot_index
            break
        if smallest_life is None or active <= smallest_life:
            smallest_life = active
            index = slot_index
    if index is None:
        index = 0

    # The original stores these as float fields in a byte-oriented record.
    slot = bytearray(pool[index])
    struct.pack_into('<Ihh', slot, 0, source_token, lifetime, lifetime)
    struct.pack_into('<f', slot, 8, _f32(1.0 / lifetime))
    struct.pack_into('<3i', slot, 0xc, *position)

    random_a = random_state.next_unit_fraction()
    random_b = random_state.next_unit_fraction()
    random_c = random_state.next_unit_fraction()
    config_1c = _exact_float(_float_at(config, 0x1c))
    config_10 = _exact_float(_float_at(config, 0x10))
    config_14 = _exact_float(_float_at(config, 0x14))
    config_18 = _exact_float(_float_at(config, 0x18))
    scale = _exact_float(_f32(scale))
    velocity_a = tuple(_exact_float(_f32(v)) for v in velocity_a)
    velocity_b = tuple(_exact_float(_f32(v)) for v in velocity_b)
    acceleration = tuple(_exact_float(_f32(v)) for v in acceleration)
    if any(len(v) != 3 for v in (velocity_a, velocity_b, acceleration)):
        raise ValueError('velocity and acceleration vectors must be 3D')

    # The original keeps this third random coefficient in x87 until each
    # velocity component has been multiplied and stored.
    component_b = _x87_mul(
        _x87_add(_x87_mul(_x87_add(_exact_float(random_c), Fraction(-1, 2)), config_1c),
                 Fraction(1)), config_18)
    component_a = _x87_f32(_x87_mul(
        _x87_add(_x87_mul(_x87_add(_exact_float(random_b), Fraction(-1, 2)), config_1c),
                 Fraction(1)), config_14))
    velocity = []
    for axis in range(3):
        value = _x87_f32(_x87_mul(_x87_mul(component_b, velocity_b[axis]), scale))
        if axis == 1:
            extra_coefficient = _x87_f32(_x87_mul(
                _x87_add(_x87_mul(_x87_add(_exact_float(random_a), Fraction(-1, 2)),
                                  config_1c), Fraction(1)), config_10))
            value = _x87_f32(_x87_add(
                _x87_mul(_exact_float(extra_coefficient), scale), _exact_float(value)))
        value = _x87_f32(_x87_add(
            _x87_mul(_x87_mul(_exact_float(component_a), velocity_a[axis]), scale),
            _exact_float(value)))
        value = _x87_f32(_x87_add(
            _x87_mul(_exact_float(_float_at(config, 0x34)), acceleration[axis]),
            _exact_float(value)))
        velocity.append(value)
    struct.pack_into('<3f', slot, 0x18, *velocity)

    random_size = random_state.next_unit_fraction()
    size_product = _x87_mul(_exact_float(_float_at(config, 0x48)),
                            _exact_float(_float_at(config, 0x40)))
    size_product = _x87_mul(_exact_float(random_size), size_product)
    size = _x87_f32(_x87_add(size_product, _exact_float(_float_at(config, 0x40))))
    struct.pack_into('<2f', slot, 0x24, size, size)
    struct.pack_into('<f', slot, 0x2c,
                     _f32(_float_at(config, 0x44) * _f32(1.0 / lifetime) * scale))
    struct.pack_into('<f', slot, 0x30, random_state.next_unit_fraction())
    struct.pack_into('<f', slot, 0x34, _f32(scale * _float_at(config, 0x30)))
    struct.pack_into('<f', slot, 0x38, random_state.next_unit_fraction())
    slot[0x3c:0x48] = config[0x20:0x2c]

    color = struct.unpack_from('<I', config, 0x4c)[0]
    if struct.unpack_from('<I', config, 0x54)[0] != 0:
        for channel in range(3, -1, -1):
            amount = config[0x54 + channel]
            decrement = int(round(amount * random_state.next_unit_fraction()))
            shift = channel * 8
            value = ((color >> shift) - decrement) & 0xff
            color = (color & ~(0xff << shift)) | (value << shift)
    struct.pack_into('<II', slot, 0x48, color, color)
    slot[0x50] = min(config[0x50], slot[0x4c])
    slot[0x51] = min(config[0x51], slot[0x4d])
    slot[0x52] = min(config[0x52], slot[0x4e])
    slot[0x53] = min(config[0x53], slot[0x4f])
    slot[0x64] = 0
    slot[0x65] = 0
    slot[0x66] = config[0x5c]
    slot[0x67] = cadence
    slot[0x68] = 0
    pool[index][:] = slot
    return index
