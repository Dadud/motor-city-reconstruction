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


@dataclass(frozen=True)
class IntakeExchange:
    """Stored branch outputs; pressure_ratio is meaningful for an open valve.

    A closed valve retains the caller's native scratch/feedback fields. The
    boundary-feedback stage overwrites the native ratio slot with valve scale;
    a future full loop must preserve that ordering when composing these stages.
    """
    mass_delta: float = 0
    pressure_ratio: float = 0
    flow_term: float = 0
    thermal_root: float = 0
    density_term: float = 0


@dataclass(frozen=True)
class CylinderEnergyTerms:
    """Native stored polynomial terms; physical units remain unverified."""
    capacity_term: float
    energy_term: float


def cylinder_energy_terms(temperature):
    """Temperature polynomials at 0x47ae8f–0x47af0b.

    Preserve the original operation order and float32 stores. These terms
    prepare the energy exchange; they do not evolve temperature or pressure.
    """
    temperature, = _stored_inputs(temperature)
    if not 0 < temperature <= 10000:
        raise ValueError('invalid cylinder temperature')
    square = temperature*temperature
    cube = temperature*square
    fourth = temperature*cube
    capacity = square*1.17048e-8+temperature*1.0396e-5
    capacity += _f32(.16528)
    capacity -= cube*3.74528e-12
    capacity += fourth*3.1578e-16
    energy = square*5.1979e-6+temperature*_f32(.16528)
    energy += cube*_f32(3.9016e-9)
    energy -= fourth*9.3632e-13
    energy += (temperature*fourth)*6.3156e-17
    return CylinderEnergyTerms(_f32(capacity), _f32(energy))


def _mass_inputs(cylinder_pressure, cylinder_temperature, boundary_pressure, area, rpm):
    pressure, temperature, boundary, area, rpm = _stored_inputs(
        cylinder_pressure, cylinder_temperature, boundary_pressure, area, rpm)
    if not (area >= 0 and 2000 <= rpm <= 11000):
        raise ValueError('invalid valve mass-exchange input')
    if area > 0 and not (pressure > 0 and temperature > 0 and boundary > 0):
        raise ValueError('invalid active valve gas state')
    return pressure, temperature, boundary, area, rpm


def _flow_term(ratio):
    return _f32((math.pow(ratio, 1.4279999732971191)-
                 math.pow(ratio, 1.7139999866485596))*5)


def intake_pressure_feedback(boundary_pressure, area, valve_scale, previous, wave=0):
    """0x47ab69–0x47abe4 boundary feedback before the current exchange.

    Consume prior stored flow/thermal/density fields and the current valve area.
    Valve scale is the native stored input, not a guessed diameter conversion.
    The caller supplies the separately evolved wave term. No pressure clamp or
    original failure/abort handling is added to this numerical stage.
    """
    if not isinstance(previous, IntakeExchange):
        raise ValueError('expected intake feedback state')
    boundary, area, scale, wave, term, root, density = _stored_inputs(
        boundary_pressure, area, valve_scale, wave, previous.flow_term,
        previous.thermal_root, previous.density_term)
    if not (area >= 0 and scale > 0 and term >= 0 and root >= 0 and density >= 0):
        raise ValueError('invalid intake feedback input')
    velocity = ((math.sqrt(term)*root)*area)/((scale*scale)*_f32(.7853982))
    result = boundary*144-((velocity*velocity)*density)*.5
    return _f32(result*_f32(.0069444445)+wave)


def intake_mass_exchange(cylinder_pressure, cylinder_temperature, intake_pressure,
                         intake_temperature, area, rpm, previous=None):
    """0x47abe4–0x47ad3b intake exchange and feedback fields.

    Positive delta flows into the cylinder. A closed valve zeros delta while
    retaining prior feedback fields. Inputs require positive boundary pressure;
    native failure/abort paths for invalid gas state are not integrated here.
    Delta units and its subsequent accumulation interval remain unverified.
    """
    pressure, temperature, boundary, area, rpm = _mass_inputs(
        cylinder_pressure, cylinder_temperature, intake_pressure, area, rpm)
    incoming_temperature, = _stored_inputs(intake_temperature)
    if area > 0 and incoming_temperature <= 0:
        raise ValueError('invalid intake temperature')
    previous = IntakeExchange() if previous is None else previous
    if not isinstance(previous, IntakeExchange):
        raise ValueError('expected intake feedback state')
    if area == 0:
        fields = _stored_inputs(previous.pressure_ratio, previous.flow_term,
                                previous.thermal_root, previous.density_term)
        return IntakeExchange(0, *fields)
    high, low = max(pressure, boundary), min(pressure, boundary)
    source_temperature = incoming_temperature if boundary > pressure else temperature
    ratio = _f32(low/high)
    term = _flow_term(ratio)
    root = _f32(math.sqrt(source_temperature*_f32(2405.01806640625)))
    delta = ((root*high)*_f32(.01874414272606373))/source_temperature
    delta *= math.sqrt(term)
    delta *= area
    delta *= _f32(.16666667)
    delta = _f32(delta/rpm)
    if boundary < pressure:
        delta = -delta
    density = _f32((boundary*144)/(source_temperature*1716))
    return IntakeExchange(delta, ratio, term, root, density)


def exhaust_mass_transfer(cylinder_pressure, cylinder_temperature, exhaust_pressure, area, rpm):
    """0x47ad3b–0x47ae8f exhaust exchange; positive delta flows out.

    Reverse flow uses the native fixed incoming temperature 2000. Unlike the
    intake branch, this branch retains its unrounded thermal square root during
    multiplication. The positive-pressure domain has a ratio at most one; the
    native alternate ratio>1.892 path is unreachable in this supported domain.
    """
    pressure, temperature, boundary, area, rpm = _mass_inputs(
        cylinder_pressure, cylinder_temperature, exhaust_pressure, area, rpm)
    if area == 0:
        return 0.0
    high, low = max(pressure, boundary), min(pressure, boundary)
    source_temperature = 2000.0 if pressure < boundary else temperature
    ratio = _f32(low/high)
    term = _flow_term(ratio)
    root = math.sqrt(source_temperature*_f32(2405.01806640625))
    delta = ((root*high)*_f32(.01874414272606373))/source_temperature
    delta *= math.sqrt(term)
    delta *= area
    delta *= _f32(.16666667)
    delta = _f32(delta/rpm)
    return -delta if pressure < boundary else delta


def intake_boundary(geometry, rpm, carb_capacity, carb_code, intake_mode, boost=0):
    """Couple 0x479025/0x47903a, 0x479b29 and 0x47a05b–0x47a0b0.

    Accepts the builder's ordinary minimum-300 capacity and the special
    carburetor-six rerun capacity (which can be lower). Native intermediate stores/order are retained, including
    unrounded displacement-rate use and boost addition after the pressure store.
    Negative boundary values are preserved; no new physical clamp is applied.
    """
    if not isinstance(geometry, CylinderGeometry):
        raise ValueError('expected recovered cylinder geometry')
    if (type(carb_capacity) is not int or not 1 <= carb_capacity <= 32767 or
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
