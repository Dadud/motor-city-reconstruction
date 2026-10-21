"""Original startup-record constructor 0x53a1f0..0x53ab90.

Builds the 0x4a8-byte startup record the original copies to owner +0x17ec:
gear tables from the recovered gear binding, inertia and resistance scalars,
crossing-derived shift thresholds, and the two 112-sample acceleration tables.
The original FUN_00483450 scene-area query return is an explicit input; its
zero branch selects the translated fallback formula. Model-marker search and
body-shape inertia scales are translated inline.
"""
import math
import struct
from fractions import Fraction
from client.acceleration_table import acceleration_table
from client.gear_binding import bind_gear_tables
from client.gear_force_table import gear_force_table
from client.startup_balance import (startup_balance_coefficient,
                                    startup_brake_balance,
                                    startup_load_coefficient)
from client.startup_resistance import startup_resistance_table
from client.tire_response import f32

_SHAPES = {0: (f32(0.88), f32(0.94), f32(0.83)),
           2: (f32(0.88), f32(0.94), f32(0.83)),
           1: (f32(0.6), f32(0.8), f32(0.7)),
           3: (f32(0.6), f32(0.8), f32(0.7)),
           7: (f32(0.6), f32(0.8), f32(0.7)),
           4: (f32(0.65), f32(0.73), f32(0.85)),
           5: (f32(0.65), f32(0.73), f32(0.85)),
           6: (f32(0.65), f32(0.68), f32(0.8))}


def _marker_index(model, name):
    """Original 0x4c5ca0: 0x40-stride NUL-terminated name search."""
    count = struct.unpack_from('<i', model, 0x11c)[0]
    for index in range(count):
        base = 0xe28+index*0x40
        end = model.index(b'\0', base)
        if model[base:end] == name:
            return index
    return -1


def _wheel_marker(model, suffix):
    """The original searches the colon-delimited marker name constants."""
    index = _marker_index(model, b':'+suffix)
    return -1 if index < 0 else index


def _turns(rise, run):
    """Original 0x6f1430: atan2 of binary32 arguments, double turns scale.

    Returns the raw binary64 result; callers apply the FSTP rounding where
    the original stores one."""
    return math.atan2(rise, run)*0.15915493667125702


def _turn_limit(delta):
    """Original 0x536d80: degrees-to-samples scale clamped to half a turn."""
    scaled = f32(f32(delta*f32(360.))*f32(0.08330000191926956))
    return max(-0.5, min(scaled, 0.5))


_F0254 = Fraction(f32(0.0254))
_F001 = Fraction(f32(0.01))
_F0001 = Fraction(f32(0.001))


def _round_mant64(value):
    """Round an exact binary rational to 64 significant bits (half-even),
    mirroring the x87 64-bit-mantissa result register."""
    if value == 0:
        return Fraction(0)
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    exponent = (magnitude.numerator.bit_length()
                - magnitude.denominator.bit_length())
    scaled = (magnitude/Fraction(1 << exponent) if exponent >= 0
              else magnitude*Fraction(1 << -exponent))
    mantissa = round(scaled*(1 << 63))
    return sign*Fraction(mantissa, 1 << 63)*Fraction(1 << exponent) if exponent >= 0 \
        else sign*Fraction(mantissa, 1 << 63)/Fraction(1 << -exponent)


def _wheel_radius(diameter, aspect, rim):
    """Tire radius: the original chains the products and their sum through
    the x87 result register at 64-bit mantissa precision before the single
    binary32 store. binary64 intermediates double-round differently on
    boundary inputs, so the sum is rounded the way the original does."""
    exact = (Fraction(diameter)*_F0254
             + Fraction(aspect)*_F001*Fraction(rim)*_F0001*2)
    return f32(float(_round_mant64(exact)/2))


def construct_startup_record(owner, configuration, model, area_query=None, *,
                             scene_nodes=None):
    """Whole original function. owner is read for dimensions and mass;
    configuration must be the finalized 0x820-byte assembly. model may be
    None (authored half-wheelbase axle defaults) or a model image containing
    the PPL wheel markers. Provide either the original FUN_00483450 binary32
    result or decoded scene nodes for its recovered geometry calculation.
    Returns (record bytes, 1) or (None, 0) on the original failure.
    """
    if area_query is not None and scene_nodes is not None:
        raise ValueError('provide area_query or scene_nodes, not both')
    if scene_nodes is not None:
        from client.scene_area_measure import scene_area_from_nodes
        area_query = scene_area_from_nodes(scene_nodes)
    if area_query is None:
        raise ValueError('scene-area result or decoded scene nodes required')

    def integer(offset):
        return struct.unpack_from('<i', configuration, offset)[0]

    def number(offset):
        return f32(struct.unpack_from('<f', configuration, offset)[0])

    def own(offset):
        return f32(struct.unpack_from('<f', owner, offset)[0])

    def own_int(offset):
        return struct.unpack_from('<i', owner, offset)[0]

    wheelbase = number(0x2c)
    if model is None:
        front_axle = f32(wheelbase*f32(0.5))
        rear_axle = f32(wheelbase*f32(-0.5))
    else:
        index = _wheel_marker(model, b'PPLFwheel')
        if index < 0:
            return None, 0
        front_axle = f32(struct.unpack_from('<f', model, 0x128+index*0xc)[0])
        index = _wheel_marker(model, b'PPLRwheel')
        if index < 0:
            return None, 0
        rear_axle = f32(struct.unpack_from('<f', model, 0x128+index*0xc)[0])
    scales = _SHAPES.get(integer(0x48), (1., 1., 1.))
    width_sq = own(0xcc)*own(0xcc)*4.
    length_sq = own(0xd0)*own(0xd0)*4.
    height_sq = own(0xd4)*own(0xd4)*4.
    mass = own(0x50)
    quarter = f32(0.0833333358168602)
    inertia_1 = f32((height_sq+length_sq)*scales[0]*mass*quarter)
    inertia_2 = f32((height_sq+width_sq)*scales[1]*mass*quarter)
    inertia_3 = f32((length_sq+width_sq)*scales[2]*mass*quarter)
    span = f32(number(0x11c)*number(0x120))
    if number(0x11c) < number(0x120):
        span = f32(number(0x120))
    # FUN_006f1430 outputs and the enclosing record prefix scalars.
    record = bytearray(0x4a8)
    struct.pack_into('<f', record, 0x110, _turns(number(0x120), wheelbase))
    struct.pack_into('<f', record, 0x114, _turns(number(0x11c), wheelbase))
    struct.pack_into('<f', record, 0x118,
                     _turns(max(number(0x11c), number(0x120)),
                            f32(own(0xcc)*2.)))
    gear_count = integer(0x32c)
    binding = bind_gear_tables(integer(0x70), number(0x228), number(0x22c),
                               number(0x230),
                               tuple(number(0x334+i*4)
                                     for i in range(gear_count)),
                               tuple(number(0x354+i*4)
                                     for i in range(gear_count)),
                               number(0x374))
    struct.pack_into('<f', record, 0xc4, binding.final_drive_inertia)
    struct.pack_into('<f', record, 0xc8, _turns(wheelbase, number(0xec)))
    for i, value in enumerate(binding.inverse_near_limit_speed):
        struct.pack_into('<f', record, 0x04+i*4, value)
    for i, value in enumerate(binding.rpm_per_speed):
        struct.pack_into('<f', record, 0x24+i*4, value)
    for i, value in enumerate(binding.speed_per_rpm):
        struct.pack_into('<f', record, 0x44+i*4, value)
    for i, value in enumerate(binding.loss_final_ratio):
        struct.pack_into('<f', record, 0x64+i*4, value)
    for i, value in enumerate(binding.wheel_inertia_factors):
        struct.pack_into('<f', record, 0x84+i*4, value)
    struct.pack_into('<f', record, 0x00,
                     f32(float(integer(0x70)-250)
                         * binding.speed_per_rpm[gear_count-1])
                     if gear_count else 0.)
    near_limit = _turns(wheelbase, number(0xec))
    if 0.5 < abs(f32(front_axle-rear_axle)-wheelbase):
        return None, 0
    front_radius = _wheel_radius(number(0x12c), number(0x128), number(0x124))
    rear_radius = _wheel_radius(number(0x230), number(0x22c), number(0x228))
    struct.pack_into('<f', record, 0x100, front_radius)
    struct.pack_into('<f', record, 0x104, rear_radius)
    clamped_front = max(f32(front_radius-f32(0.37)), 0.)
    clamped_rear = max(f32(rear_radius-f32(0.37)), 0.)
    rear_sum = f32(clamped_rear+rear_radius)
    front_outer = f32(clamped_front+front_radius)
    forward = max(f32(front_outer-rear_sum), 0.)
    reverse = max(f32(rear_sum-front_outer), 0.)
    turn_difference = f32(f32(_turns(forward, wheelbase))
                          - _turns(reverse, wheelbase))
    struct.pack_into('<f', record, 0x108, turn_difference)
    struct.pack_into('<f', record, 0x10c, f32(_turn_limit(turn_difference)))
    struct.pack_into('<f', record, 0xcc,
                     f32((1.0-number(0x3c))*wheelbase))
    struct.pack_into('<f', record, 0xd0, f32(number(0x3c)*wheelbase))
    struct.pack_into('<f', record, 0x11c,
                     startup_load_coefficient(configuration))
    struct.pack_into('<f', record, 0x120,
                     startup_balance_coefficient(configuration))
    struct.pack_into('<f', record, 0x124, startup_brake_balance(configuration))
    fallback = f32((own(0xd0)*2.)*(own(0xcc)*2.)*f32(0.8))
    area = f32(area_query) if area_query != 0. else fallback
    struct.pack_into('<f', record, 0xd4, area)
    weight_delta = number(0x20)-number(0x28)
    springs = number(0x104)+number(0xfc)
    rolling_forward = f32(springs - number(0x38)*f32(0.45454543828964233)
                          * weight_delta*f32(0.17121680080890656))
    rolling_reverse = f32(springs - number(0x38)*f32(0.3181818127632141)
                          * weight_delta*f32(0.17121680080890656))
    struct.pack_into('<f', record, 0xe4, rolling_forward)
    struct.pack_into('<f', record, 0xe0, rolling_reverse)
    struct.pack_into('<f', record, 0xe8, inertia_1)
    struct.pack_into('<f', record, 0xec, inertia_2)
    struct.pack_into('<f', record, 0xf0, inertia_3)
    struct.pack_into('<f', record, 0xf4, f32(1./inertia_1) if inertia_1 else 0.)
    struct.pack_into('<f', record, 0xf8, f32(1./inertia_2) if inertia_2 else 0.)
    struct.pack_into('<f', record, 0xfc, f32(1./inertia_3) if inertia_3 else 0.)
    struct.pack_into('<f', record, 0xd8, front_axle)
    struct.pack_into('<f', record, 0xdc, rear_axle)
    for gear in range(8):
        if gear < 2:
            struct.pack_into('<f', record, 0xa4+gear*4, f32(-10000.))
            continue
        if gear >= gear_count-1:
            struct.pack_into('<f', record, 0xa4+gear*4, f32(12000.))
            continue
        if gear > gear_count-2:
            fraction = -1.0
        else:
            first = gear_force_table(configuration,
                                     binding.rpm_per_speed, gear)
            second = gear_force_table(configuration,
                                      binding.rpm_per_speed, gear+1)
            resistance = startup_resistance_table(number(0x20), number(0x00),
                                                  area, integer(0x238))
            first = [f32(max(f32(a-r), 0.))
                     for a, r in zip(first, resistance)]
            second = [f32(max(f32(b-r), 0.))
                      for b, r in zip(second, resistance)]
            fraction = None
            for index in range(134):
                if (first[index+1] < second[index+1]
                        and first[index] >= second[index]):
                    interpolated = f32(
                        (first[index]*(index+1)
                         + (second[index+1]*index
                            - second[index]*(index+1))
                         - first[index+1]*index)
                        / ((first[index]-first[index+1])
                           + second[index+1]-second[index]))
                    crossing = f32(interpolated
                                   * binding.rpm_per_speed[gear])
                    rounded = round(crossing)
                    if rounded >= (integer(0x6c)+integer(0x70))//2:
                        fraction = interpolated
                        if gear < gear_count-2:
                            fraction = f32(interpolated
                                           * f32(0.9800000190734863))
                        break
            if fraction is None:
                maximum = integer(0x70)
                fallback_rpm = (maximum*7)//10 if gear == 2 else (maximum*3)//4
                fraction = f32(float(fallback_rpm)
                               / binding.rpm_per_speed[gear])
        struct.pack_into('<f', record, 0xa4+gear*4, f32(fraction))
    tables = acceleration_table(configuration, bytes(record))
    record[0x128:] = tables[0x128:]
    return bytes(record), 1
