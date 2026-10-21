"""Recovered per-RPM boost-state update from original 0x586730."""
import math
import struct
from client.tire_response import f32


STATE_SIZE = 0x10c


def update_boost_state(configuration, state):
    """Apply one original boost update to its 0x10c-byte solver scratch record.

    The record offsets mirror the original solver's stack layout. This is the
    helper stage only; the caller remains responsible for invoking it at the
    original point in each RPM cycle and composing all downstream effects.
    """
    if len(configuration) != 1004 or len(state) < STATE_SIZE:
        raise ValueError('expected 1004-byte dyno record and boost-state record')

    def sf(image, offset):
        value = struct.unpack_from('<f', image, offset)[0]
        if not math.isfinite(value):
            raise ValueError('non-finite boost input')
        return value

    def si(image, offset):
        return struct.unpack_from('<i', image, offset)[0]

    mode = struct.unpack_from('<h', configuration, 0x3c4)[0]
    if mode not in (0, 1, 2, 3):
        raise ValueError('boost mode outside original cases 0..3')
    if mode == 0:
        return bytes(state)

    rpm = sf(state, 0xfc)
    displacement = sf(state, 0xf4)
    fill = sf(state, 0xf0)
    boost = sf(state, 0x100)
    base_flow = f32(fill * .01 * rpm * .5 * displacement * .0005787037)
    if mode == 1:
        drive = base_flow * .32000002
        regulator = drive / sf(configuration, 0x3cc) * sf(configuration, 0x3d4)
        threshold = ((boost * f32(.06802721) + 1.) * sf(configuration, 1000)) / sf(configuration, 0x3c8)
        if drive < threshold:
            regulator *= .8
        boost_measure = (((sf(configuration, 0x3c8) - 1.) * regulator * 14.7) /
                         sf(configuration, 0x3d4))
        phase = abs(regulator - sf(configuration, 0x3d4)) / sf(configuration, 0x3d4)
    elif mode == 2:
        flow = sf(configuration, 0x3e4) * sf(configuration, 0x3e0) * rpm
        boost_measure = ((((sf(configuration, 0x3c8) - 1.) * flow * 14.7) /
                          sf(configuration, 0x3d4)) * (1. - 1500. / flow) * .9)
        phase = abs(flow - sf(configuration, 0x3d4)) / sf(configuration, 0x3d4)
    else:
        flow = sf(configuration, 0x3e4) * rpm
        boost_measure = (flow * sf(configuration, 0x3cc) * f32(.0005787037) *
                         f32(.01) * (1. - 1500. / flow) * .85)
        phase = abs(flow - 30000.) * 3.3333333333333335e-5

    boost_measure = f32(boost_measure)
    phase = math.cos(phase)
    multiplier = f32(phase * sf(configuration, 0x3d0) * f32(.01))
    if multiplier < .3:
        multiplier = .3
    boost_measure = min(boost_measure, sf(configuration, 0x3d8))
    power = math.pow((boost_measure + 14.7) * f32(.06802721), .2366)
    charge = f32((((power - 1.) / multiplier) * (1. - sf(configuration, 0x3dc) * .01) + 1.) * 540.)
    updated = bytearray(state)
    struct.pack_into('<f', updated, 0xf8, charge)
    if mode == 1:
        struct.pack_into('<ff', updated, 0x104, 0., 0.)
    else:
        work = ((power - 1.) * base_flow * .2710126) / multiplier
        struct.pack_into('<f', updated, 0x108, work)
        struct.pack_into('<f', updated, 0x104,
                         work * 802973. / (sf(state, 0xf4) * rpm))
    boost_measure = f32((1. - (sf(configuration, 0x3dc) * .005 * boost_measure * 20.) /
                          (sf(configuration, 0x3d8) * 100.)) * boost_measure)
    struct.pack_into('<f', updated, 0x100, boost_measure)
    return bytes(updated)
