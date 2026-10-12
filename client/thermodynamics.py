"""Portable cylinder-state stages; full cycle integration remains unfinished."""
from dataclasses import dataclass
import math

from .dyno_solver import CylinderGeometry, _f32


@dataclass(frozen=True)
class InitialCylinderState:
    pressure: float
    temperature: float
    crank_radius: float
    rod_ratio: float
    piston_area: float
    mass_term: float
    reference_mass_term: float


@dataclass(frozen=True)
class ExhaustParameters:
    baseline: float
    amplitude: float
    reference_rpm: float
    rpm_exponent: float


@dataclass(frozen=True)
class CyclePreparation:
    temperature_term: float
    angle_step_factor: float
    exhaust_wave_scale: float


@dataclass(frozen=True)
class IntakeBoundary:
    displacement_rate: float
    capacity_scale: float
    pressure: float


def intake_boundary(geometry, rpm, carb_capacity, carb_code, intake_mode, boost=0):
    """Couple 0x479025/0x47903a, 0x479b29 and 0x47a05b–0x47a0b0.

    Requires an assembled core capacity (builder minimum 300), not an unbound
    catalogue value. Native intermediate stores/order are retained, including
    unrounded displacement-rate use and boost addition after the pressure store.
    Negative boundary values are preserved; no new physical clamp is applied.
    """
    if not isinstance(geometry, CylinderGeometry):
        raise ValueError('expected recovered cylinder geometry')
    if (type(carb_capacity) is not int or not 300 <= carb_capacity <= 32767 or
            type(carb_code) is not int or carb_code not in (2, 4) or
            type(intake_mode) is not int or not 1 <= intake_mode <= 6):
        raise ValueError('invalid assembled intake capacity/mode')
    rpm, displacement, boost = _stored_inputs(rpm, geometry.total_displacement, boost)
    if not 2000 <= rpm <= 11000 or displacement <= 0:
        raise ValueError('invalid intake displacement/rpm')
    coefficient = _f32(3.810418e-5 if carb_code == 2 else 5.387931e-5)
    capacity = _f32(carb_capacity*coefficient)
    if intake_mode == 4:
        capacity *= .25
    capacity_scale = _f32(capacity*207360)
    rate = displacement*rpm
    flow = ((rate*70)*_f32(.01))/capacity_scale
    pressure = _f32(_f32(14.7)-(flow*flow)*_f32(7.916e-6))
    if boost > 0:
        pressure = _f32(pressure+boost)
    return IntakeBoundary(_f32(rate), capacity_scale, pressure)


def _stored_inputs(*values):
    if not all(math.isfinite(value) for value in values):
        raise ValueError('non-finite cycle input')
    try:
        return tuple(_f32(value) for value in values)
    except (OverflowError, ValueError) as error:
        raise ValueError('cycle input exceeds float32') from error


def charge_temperature(mode, rpm):
    """0x479bce–0x479c5e selection, using raw dyno word +0x2dc.

    Temperature units and mode meanings remain unverified. Stock core records
    use mode 1; the other native branches are retained for numerical comparison.
    """
    if type(mode) is not int or not 1 <= mode <= 32767:
        raise ValueError('invalid temperature mode')
    rpm, = _stored_inputs(rpm)
    if not 2000 <= rpm <= 11000:
        raise ValueError('rpm outside supported core range')
    if mode < 10 and rpm < 5500:
        return _f32(610-rpm*_f32(.01272))
    if mode > 19:
        return 560.0 if rpm > 5500 else _f32(630-rpm*_f32(.01272))
    return 540.0


def cycle_preparation(rpm, temperature, exhaust):
    """0x47a0b0–0x47a145 polynomial and cycle/exhaust scales.

    Preserve the native multiplication/addition order and float32 input/output
    stores. This prepares terms for integration; it does not evolve gas state.
    """
    if not isinstance(exhaust, ExhaustParameters):
        raise ValueError('expected recovered exhaust parameters')
    rpm, temperature, exponent = _stored_inputs(rpm, temperature, exhaust.rpm_exponent)
    if not (2000 <= rpm <= 11000 and 0 < temperature <= 10000 and 0 < exponent <= 2):
        raise ValueError('invalid cycle preparation input')
    square = temperature*temperature
    cube = temperature*square
    fourth = temperature*cube
    term = square*5.1979e-6+temperature*_f32(.16528)
    term += cube*3.9016e-9
    term -= fourth*9.3632e-13
    term += (temperature*fourth)*6.3156e-17
    term += temperature*_f32(.06857)
    return CyclePreparation(_f32(term), _f32(24000/rpm),
                            _f32(math.pow(rpm, exponent)*_f32(.0013332)))


def exhaust_phase_factor(start_angle):
    """0x479b6c–0x479b81: stored 270/(360-start-angle)."""
    angle, = _stored_inputs(start_angle)
    if not -720 <= angle < 360:
        raise ValueError('unsupported exhaust start angle')
    return _f32(270/(360-angle))


def exhaust_wave_value(angle, start_angle, phase_factor, rpm, exhaust,
                       wave_scale, previous_value=0, boost=0):
    """0x47aa3d–0x47aafd exhaust wave, including retained exact boundaries.

    The native wave variable's physical units remain unverified. Positive boost
    selects a separate RPM-only value. Previous state is supplied explicitly;
    this function is not the complete cylinder-pressure integration loop.
    """
    if not isinstance(exhaust, ExhaustParameters):
        raise ValueError('expected recovered exhaust parameters')
    angle, start, factor, rpm, scale, previous, boost, reference, amplitude, baseline = _stored_inputs(
        angle, start_angle, phase_factor, rpm, wave_scale, previous_value, boost,
        exhaust.reference_rpm, exhaust.amplitude, exhaust.baseline)
    if not (2000 <= rpm <= 11000 and abs(angle) <= 1440 and abs(start) <= 720 and
            factor > 0 and reference > 0 and scale >= 0):
        raise ValueError('invalid exhaust wave input')
    if boost > 0:
        return _f32(rpm*_f32(.0013333333)+25)
    phase = ((angle-start)*reference/rpm)*factor
    if phase == 180 or phase == 360:
        return previous
    wave = math.sin(phase*_f32(.017453292))*scale
    if phase < 180:
        wave += wave
    elif phase < 360:
        wave *= amplitude
    else:
        wave *= _f32(.8)
    return _f32(wave+baseline)


def exhaust_parameters(mode, rpm, flow_factor):
    """Recover exhaust branch setup at 0x479f42–0x47a05b.

    Field roles follow their subsequent arithmetic; physical units and the
    complete pressure-wave evolution remain unverified. This is preparation
    for the cycle loop, not an exhaust-force or engine-output calculation.
    """
    if type(mode) is not int or not 1 <= mode <= 7:
        raise ValueError('exhaust mode must be within [1, 7]')
    if not all(math.isfinite(v) for v in (rpm, flow_factor)):
        raise ValueError('non-finite exhaust input')
    try:
        rpm, factor = map(_f32, (rpm, flow_factor))
    except (OverflowError, ValueError) as error:
        raise ValueError('exhaust input exceeds float32') from error
    if not 2000 <= rpm <= 11000 or factor <= 0:
        raise ValueError('invalid exhaust rpm/flow factor')
    baseline, amplitude, reference, exponent = (
        (35, .3, 4000, 1.06), (32, .3, 4000, 1.04),
        (26.5, .5, 5000, 1.04), (22.5, .5, 5000, 1),
        (25.7, .5, 5000, 1.02), (22.7, .5, 5500, .94),
        (21, .5, 6000, .95))[mode-1]
    baseline = _f32(baseline)
    if mode == 7 and rpm < 5500:
        baseline = ((5500-rpm)/rpm)*3+21
    return ExhaustParameters(_f32(baseline/factor), _f32(amplitude),
                             _f32(reference), _f32(exponent))


def initial_cylinder_state(geometry, stroke_inches, start_angle, pressure=44.1):
    """Initialize the cycle state recovered at 0x479e4d–0x479f35.

    Pressure is supplied by the caller: the original first RPM starts at 44.1
    and later cycles retain/carry state. Mass-term units remain unverified.
    This function does not select or evolve that inter-cycle pressure.
    """
    if not isinstance(geometry, CylinderGeometry):
        raise ValueError('expected recovered cylinder geometry')
    values = (stroke_inches, start_angle, pressure, geometry.bore_squared,
              geometry.rod_length, geometry.clearance_volume)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('non-finite cylinder initialization input')
    stroke, angle, stored_pressure, bore_squared, rod, clearance = map(_f32, values)
    if not (0 < stroke <= 5.1 and rod > 0 and bore_squared > 0 and
            clearance > 0 and stored_pressure > 0):
        raise ValueError('invalid cylinder initialization geometry/state')
    radians = angle*_f32(.017453292)
    sine = _f32(math.sin(radians))
    one_minus_cosine = _f32(1-math.cos(radians))
    crank_radius = _f32(stroke*.5)
    projection = _f32((stroke*.5/rod)*sine)
    ratio = _f32((rod+rod)/stroke)
    area = _f32(bore_squared*_f32(.7853982))
    root_argument = 1-projection*projection
    if root_argument < 0:
        raise ValueError('invalid connecting-rod geometry')
    volume = (((1-math.sqrt(root_argument))*ratio+one_minus_cosine)*
              area*crank_radius+clearance)
    return InitialCylinderState(stored_pressure, 2000, crank_radius, ratio, area,
                                _f32(volume*stored_pressure*_f32(7.8104307e-7)),
                                _f32(volume*_f32(4.357242e-5)))
