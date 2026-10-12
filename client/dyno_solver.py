"""Portable portions of REA 221's dyno solver, not a complete torque solver."""
import math
import struct
from dataclasses import dataclass


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def interpolate_flow(lift, points, coefficients):
    """Native ten-slot interpolation before pressure correction/clamping.

    REA 221 0x47a256–0x47a54b and 0x47a709–0x47a9fe. A zero next
    point selects extrapolation from the preceding pair. Lift remains double;
    table entries are native float32. The implicit zero-lift coefficient is 1.
    """
    if len(points) != 10 or len(coefficients) != 10:
        raise ValueError('flow tables require ten slots')
    if not all(math.isfinite(v) for v in (lift, *points, *coefficients)) or lift < 0:
        raise ValueError('invalid flow interpolation inputs')
    x, y = tuple(map(_f32, points)), tuple(map(_f32, coefficients))
    if x[0] <= 0:
        raise ValueError('first flow point must be positive')
    if lift <= x[0]:
        return ((y[0]-1)/x[0])*lift+1
    if lift <= x[1]:
        index = 0
    elif lift <= x[2] and x[1] < lift:
        index = 1
    else:
        index = 8
        for candidate in range(2, 8):
            if ((lift <= x[candidate+1] and x[candidate] < lift) or
                    x[candidate+2] == 0):
                index = candidate
                break
    difference = x[index+1]-x[index]
    if difference <= 0:
        raise ValueError('invalid active flow segment')
    change = y[index+1]-y[index]
    intercept = y[index]-(x[index]*change)/difference
    return (change/difference)*lift+intercept


def pressure_correct_flow(coefficient, pressure_ratio):
    """Recovered pressure correction for the second airflow branch.

    REA 221 0x47a54b–0x47a605. Ratio is a stored float32; coefficient
    remains double. The exact threshold returns the native minimum .43.
    """
    if not all(math.isfinite(v) for v in (coefficient, pressure_ratio)) or pressure_ratio < 0:
        raise ValueError('invalid pressure correction inputs')
    ratio = _f32(pressure_ratio)
    threshold, minimum, tenth = _f32(1.8929), _f32(.43), _f32(.1)
    if ratio < threshold:
        value = ((coefficient-tenth)*(ratio-1)*(1-coefficient)*
                 _f32(.78396237)+coefficient)
    elif ratio == threshold:
        return minimum
    else:
        quotient = threshold/ratio
        extra = ((_f32(.27)-coefficient*tenth)*(1-quotient*quotient))*(1-coefficient)
        value = (coefficient-tenth)*(1-coefficient)*_f32(.7)+coefficient+extra
    return min(max(value, minimum), 1)


def airflow_area(lift, points, coefficients, valve_size, *, pressure_ratio=None):
    """Couple native flow interpolation/correction to float32 valve area.

    REA 221 stores at 0x47a613 and 0x47aa38. A supplied pressure ratio
    selects the corrected branch; the other branch clamps coefficient to [0,1].
    Original field conventions are retained, without a claimed SI conversion.
    """
    if not math.isfinite(valve_size) or valve_size <= 0:
        raise ValueError('invalid effective valve size')
    coefficient = interpolate_flow(lift, points, coefficients)
    if pressure_ratio is None:
        coefficient = min(max(coefficient, 0), 1)
    else:
        coefficient = pressure_correct_flow(coefficient, pressure_ratio)
    return _f32(coefficient*lift*_f32(valve_size)*_f32(3.1415927))


@dataclass(frozen=True)
class CylinderGeometry:
    bore_squared: float
    area_term: float
    swept_volume: float
    clearance_volume: float
    rod_length: float
    total_displacement: float


@dataclass(frozen=True)
class ValveEvents:
    angle_b0: float
    angle_b4: float
    angle_a8: float
    angle_ac: float
    intake_size: float
    exhaust_size: float


@dataclass(frozen=True)
class FlowCoefficients:
    scalar_314: float
    series_374: tuple[float, ...]
    series_324: tuple[float, ...]


@dataclass(frozen=True)
class CamProfile:
    radius: float
    phase: float
    quarter_duration: float
    remaining_phase: float
    offset: float
    remaining_radius: float


def valve_lift(profile, start_angle, end_angle, angle):
    """Evaluate recovered lift branches, retaining double output for airflow.

    REA 221 0x47a17b–0x47a256 and 0x47a63d–0x47a709. At the two
    exact phase boundaries the native branch retains zero; preserve that
    behavior rather than smoothing the profile.
    """
    if not isinstance(profile, CamProfile):
        raise ValueError('expected a recovered cam profile')
    values = (*profile.__dict__.values(), start_angle, end_angle, angle)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('non-finite valve-lift input')
    profile = CamProfile(*map(_f32, profile.__dict__.values()))
    start, end, position = map(_f32, (start_angle, end_angle, angle))
    if not start < position < end:
        return 0.0
    delta = position-start
    half = delta*.5
    stored_half = _f32(half)
    baseline = _f32(.55032)
    if half < profile.phase:
        cosine = math.cos(_f32(delta)*_f32(.008726646))
        radius = profile.radius-(profile.radius-baseline)*cosine
    elif profile.phase < half < profile.remaining_phase:
        cosine = math.cos((profile.quarter_duration-stored_half)*_f32(.017453292))
        radius = cosine*profile.remaining_radius+profile.offset
    elif profile.remaining_phase < half:
        cosine = math.cos(((profile.remaining_phase+profile.phase)-stored_half)*
                          _f32(.017453292))
        radius = profile.radius-(profile.radius-baseline)*cosine
    else:
        return 0.0
    lift = (radius-baseline)*1.5
    return _f32(1e-6) if lift < 0 else lift


def cam_profiles(record):
    """Build the two recovered cam profiles, preserving x87 store boundaries.

    REA 221 0x4798a4–0x479af2. Field labels describe algebraic roles;
    this does not yet implement the pressure loop's valve-lift evaluation.
    """
    events = valve_events(record)
    train = struct.unpack_from('<h', record, 0x84)[0]
    base = _f32({2: 1.55, 3: 1.6}.get(train, 1.5))
    raw_delta = base-_f32(.55032)
    delta = _f32(raw_delta)
    delta_squared = _f32(raw_delta*delta)
    base_squared = _f32(base*base)
    twice_base = _f32(base+base)
    def profile(start, end, lift, retain_radius):
        half = (end-start)*.5
        stored_half = _f32(half)
        cosine = math.cos(_f32(3.1415927)-half*_f32(.008726646))
        raw_radius = lift*_f32(.6666667)+_f32(.55032)
        radius = _f32(raw_radius)
        product = (raw_radius if retain_radius else radius)*delta*cosine
        numerator = (product+product)-((radius*radius+delta_squared)-base_squared)
        component = delta*cosine
        denominator = (component+component)+(twice_base-(radius+radius))
        if denominator == 0:
            raise ValueError('degenerate cam profile')
        offset = _f32(numerator/denominator)
        remaining_radius = _f32(radius-offset)
        difference = base-offset
        cosine_phase = _f32(((difference*difference+delta_squared)-
                             remaining_radius*remaining_radius)/
                            (difference*delta+difference*delta))
        if not -1 <= cosine_phase <= 1:
            raise ValueError('invalid cam profile phase')
        root = math.sqrt(1-cosine_phase*cosine_phase)
        quotient = root/cosine_phase if cosine_phase else math.copysign(math.inf, cosine_phase)
        phase = _f32(math.atan(quotient)*_f32(57.295776))
        return CamProfile(base, phase, _f32(stored_half*.5),
                          _f32(stored_half-phase), offset, remaining_radius)
    first_lift, second_lift = struct.unpack_from('<2f', record, 0xb8)
    if not all(math.isfinite(v) and v > 0 for v in (first_lift, second_lift)):
        raise ValueError('invalid cam lift')
    return (profile(events.angle_a8, events.angle_ac, second_lift, False),
            profile(events.angle_b0, events.angle_b4, first_lift, True))


def flow_coefficients(record):
    """Normalize the two ten-slot flow series (REA 221 0x479513–0x4798a4).

    Labels retain native offsets until physical meanings are verified. One
    scalar is stored as float32 before normalization; the other remains in
    double intermediates on the original x87 stack.
    """
    if not isinstance(record, bytes) or len(record) != 1004:
        raise ValueError('expected a 1004-byte dyno record')
    def floating(offset):
        value = struct.unpack_from('<f', record, offset)[0]
        if not math.isfinite(value):
            raise ValueError('non-finite flow input')
        return value
    inch_fraction = _f32(.083333336)
    def scalar(size_offset, pressure_offset):
        size, pressure = floating(size_offset), floating(pressure_offset)
        if size <= 0 or pressure < 0:
            raise ValueError('invalid flow size or pressure')
        return (size*inch_fraction)*math.sqrt(pressure*_f32(423.943))*_f32(618.26544)
    stored_scalar = _f32(scalar(0x314, 0x318))
    unrounded_scalar = scalar(0x31c, 0x320)
    def normalize(series_offset, denominator_offset, scale):
        result = []
        for index in range(10):
            numerator = floating(series_offset+index*4)
            denominator = floating(denominator_offset+index*4)
            if numerator <= 0:
                result.append(0.0)
                continue
            divisor = scale*denominator*inch_fraction
            if divisor <= 0:
                raise ValueError('nonpositive active flow divisor')
            result.append(_f32(numerator/divisor))
        return tuple(result)
    return FlowCoefficients(stored_scalar,
                            normalize(0x374, 0x39c, unrounded_scalar),
                            normalize(0x324, 0x34c, stored_scalar))


def valve_events(record):
    """Prepare four solver angles and effective valve sizes (REA 221).

    Angle labels follow input offsets; physical opening/closing names remain
    unverified. This covers both timing-adjustment branches at +0x82 and
    the two-valve multipliers at +0x310/+0x312.
    """
    if not isinstance(record, bytes) or len(record) != 1004:
        raise ValueError('expected a 1004-byte dyno record')
    def short(offset):
        return struct.unpack_from('<h', record, offset)[0]
    def floating(offset):
        value = struct.unpack_from('<f', record, offset)[0]
        if not math.isfinite(value):
            raise ValueError('non-finite valve event input')
        return value
    adjustment = ({2: 20.5, 3: 17}.get(short(0x84), 28.5)
                  if short(0x82) else 0)
    advance = short(0xc0)
    a8, ac, b0, b4 = (floating(offset) for offset in (0xa8, 0xac, 0xb0, 0xb4))
    intake, exhaust = floating(0x98), floating(0x9c)
    return ValveEvents(_f32((360-(adjustment+b0))-advance),
                       _f32((adjustment+b4+540)-advance),
                       _f32((180-(adjustment+a8))-advance+20),
                       _f32((adjustment+ac+360)-advance),
                       _f32(intake*2 if short(0x310) == 2 else intake),
                       _f32(exhaust*2 if short(0x312) == 2 else exhaust))


def cylinder_geometry(bore_inches, stroke_inches, compression, cylinders):
    """Recover solver geometry, including its precise float-store boundaries.

    REA 221, 0x478f44–0x47901d. Volumes use the original inch-based field
    convention. rod_length is the solver's fixed stroke*1.62 assumption.
    """
    if type(cylinders) is not int or not 6 <= cylinders <= 8:
        raise ValueError('unsupported cylinder count')
    if not all(math.isfinite(v) for v in (bore_inches, stroke_inches, compression)):
        raise ValueError('non-finite cylinder geometry')
    if not (0 < bore_inches <= 5.1 and 0 < stroke_inches <= 5.1 and
            6 <= compression <= 18):
        raise ValueError('unsupported cylinder geometry')
    bore, stroke, ratio = map(_f32, (bore_inches, stroke_inches, compression))
    square = bore*bore
    stored_square = _f32(square)
    pi_quarter = _f32(.7853982)
    volume = _f32(stroke*stored_square*pi_quarter)
    return CylinderGeometry(stored_square, _f32(square*_f32(1.57)), volume,
                            _f32(volume/(ratio-1)), _f32(stroke*_f32(1.62)),
                            _f32(cylinders*stroke*stored_square*pi_quarter))


def mechanical_loss(rpm, stroke_inches):
    """Return the solver's +0x28c output; physical units remain unverified.

    Recovered from 0x47b2b7–0x47b2df and 0x47b43f. The original retains
    intermediates on the x87 stack with double precision (control word 0x27f)
    and stores only the final result as float32.
    """
    if type(rpm) is not int or rpm not in range(2000, 11001, 500):
        raise ValueError('RPM must be a supported dyno knot')
    if not math.isfinite(stroke_inches) or not 0 < stroke_inches <= 5.1:
        raise ValueError('stroke outside supported engine range')
    return _f32(_mechanical_loss(rpm, _f32(stroke_inches)))


def _mechanical_loss(rpm, stroke_inches):
    speed = rpm*stroke_inches*_f32(.16666667)
    return (speed*_f32(6.5476e-7)+_f32(.0030476))*speed+_f32(12.964)


def rpm_work_factor(rpm):
    """Recovered work multiplier at the solver's nineteen discrete RPM knots."""
    if type(rpm) is not int or rpm not in range(2000, 11001, 500):
        raise ValueError('RPM must be a supported dyno knot')
    return _f32({2000: 1.18, 2500: 1.12, 3000: 1.095,
                 3500: 1.07}.get(rpm, 1.06))


def work_outputs(rpm, stroke_inches, integrated_work, cylinder_volume,
                 displacement_rpm, boost_loss, additional_power):
    """Convert solver work into its five output fields (REA 221).

    Inputs are recovered stack values, not a replacement for the unfinished
    pressure/airflow integration. additional_power is the already-computed
    stack contribution at EBP-0x220. Returns fields +c4, +110, +1f4, +240,
    +28c in original field conventions, before stock finalizer conversion.
    """
    factor = rpm_work_factor(rpm)
    values = (stroke_inches, integrated_work, cylinder_volume,
              displacement_rpm, boost_loss, additional_power)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('non-finite solver work input')
    try:
        stroke, work, volume, rate, boost, extra = map(_f32, values)
    except (OverflowError, struct.error) as error:
        raise ValueError('solver work input exceeds float32') from error
    if not 0 < stroke <= 5.1 or volume <= 0 or rate <= 0:
        raise ValueError('invalid solver geometry/rate')
    loss = _mechanical_loss(rpm, stroke)
    power = ((work/volume-loss)-boost)*rate*_f32(1.2453719e-6)*factor+extra
    raw_work = power*802973/rate
    stored_work = _f32(raw_work)
    combined = _f32(raw_work+loss)
    output_loss = _f32((factor-1)*stored_work+combined)
    power = max(power, 0)
    return (_f32(power), _f32(power*5250/rpm), output_loss,
            stored_work, _f32(loss))
