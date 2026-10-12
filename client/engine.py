"""Recovered engine-block fields and assembled torque-table lookup.

Block binding: REA 191/194, 0x54a5a0 and 0x542ef0; dimensions are consumed
by the dyno builder 0x46d1d0. Torque curves are assembled outputs, not Physics
table rows. Their construction from heads/cam/intake remains incomplete.
"""
from dataclasses import dataclass
import math
import struct


@dataclass(frozen=True)
class ValveTrain:
    train_type: int
    lift_factor: float
    mass: float

    @classmethod
    def from_physics(cls, record):
        """REA 209/218: +0x564 type, +0x568 lift factor; core bounds only.

        Family compatibility and the additional rounded field at +0x570
        remain unresolved. The factor is not assigned a physical rocker ratio.
        """
        if record.mass is None or len(record.values) < 2:
            raise ValueError('valve train requires mass and two physics values')
        kind, factor = record.values[:2]
        if not all(math.isfinite(v) for v in (record.mass, kind, factor)):
            raise ValueError('non-finite valve-train values')
        kind = round(kind)
        if not (5 <= record.mass <= 30 and 0 <= kind <= 2 and .9 <= factor <= 1.1):
            raise ValueError('valve train outside native core validation ranges')
        return cls(kind, factor, record.mass)


@dataclass(frozen=True)
class Camshaft:
    cam_type: int
    configuration: int
    flow_factor: float
    intake_lift_mm: float
    exhaust_lift_mm: float
    timing_fields: tuple
    mass: float

    @classmethod
    def from_physics(cls, record):
        """REA 206/216: 0x54bef0 binding and core 0x544710 bounds.

        Four timing values are retained in their original order; their names
        and the unresolved compatibility/validation branch remain unknown.
        """
        if record.mass is None or len(record.values) < 9:
            raise ValueError('camshaft requires mass and nine physics values')
        values = record.values[:9]
        if not all(math.isfinite(v) for v in (record.mass, *values)):
            raise ValueError('non-finite camshaft values')
        kind, configuration = map(round, values[:2])
        flow, intake, exhaust = values[2:5]
        if not (5 <= record.mass <= 25 and 0 <= kind <= 2 and
                0 <= configuration <= 9 and .9 <= flow <= 1.1 and
                5 <= intake <= 20 and 5 <= exhaust <= 20):
            raise ValueError('camshaft outside native core validation ranges')
        return cls(kind, configuration, flow, intake, exhaust, tuple(values[5:9]), record.mass)

    def valve_lift_inches(self, valve_train_factor):
        """0x46d1d0 converts cam lift mm and multiplies by assembled +0x568.

        The caller must provide the recovered valve-train factor; no default
        factor is invented. Intermediate x87 precision is not emulated.
        """
        if not math.isfinite(valve_train_factor) or valve_train_factor <= 0:
            raise ValueError('positive finite valve-train factor required')
        def f32(value):
            return struct.unpack('<f', struct.pack('<f', value))[0]
        try:
            factor = f32(valve_train_factor)
            result = tuple(f32(v) * f32(.001) * f32(39.3701) * factor
                       for v in (self.intake_lift_mm, self.exhaust_lift_mm))
        except (OverflowError, struct.error) as error:
            raise ValueError('valve lift input exceeds float32') from error
        if not all(math.isfinite(v) for v in result):
            raise ValueError('non-finite effective valve lift')
        return result


@dataclass(frozen=True)
class CylinderHead:
    head_type: int
    configuration: int
    port_type: int
    flow_factor: float
    compression_ratio: float
    intake_valve_mm: float
    exhaust_valve_mm: float
    mass: float

    @classmethod
    def from_physics(cls, record):
        """REA 205/213: 0x54bd70 fields and core 0x543a10 bounds.

        Family compatibility and the unresolved __ftol validation branch are
        not reproduced. This decoder does not certify native part acceptance.
        """
        if record.mass is None or len(record.values) < 7:
            raise ValueError('cylinder head requires mass and seven physics values')
        values = record.values[:7]
        if not all(math.isfinite(v) for v in (record.mass, *values)):
            raise ValueError('non-finite cylinder head values')
        head, configuration, port = map(round, values[:3])
        flow, compression, intake, exhaust = values[3:]
        if not (10 <= record.mass <= 80 and 0 <= head <= 2 and
                0 <= configuration <= 9 and 0 <= port <= 5 and
                .97 <= flow <= 1.03 and 6 <= compression <= 20 and
                25.4 <= intake <= 63.5 and 25.4 <= exhaust <= 50.8):
            raise ValueError('cylinder head outside native core validation ranges')
        return cls(head, configuration, port, flow, compression, intake, exhaust, record.mass)

    def flow_template_id(self, bore_m, engine_family):
        """Selection in 0x46d1d0; family supplied separately from Physics.

        Python numeric evaluation does not claim exact x87 boundary behavior.
        """
        if not math.isfinite(bore_m) or bore_m <= 0:
            raise ValueError('positive finite bore required')
        if type(engine_family) is not int or not 1 <= engine_family <= 26:
            raise ValueError('engine family must be within [1, 26]')
        large = (self.intake_valve_mm / (bore_m*1000) >= .49 and
                 self.exhaust_valve_mm / (bore_m*1000) >= .41 and engine_family != 10)
        port = self.port_type
        if self.head_type == 1:
            return 5+int(large) if port == 1 else 7 if port in (2, 4) else 8 if port in (3, 5) else 4
        if self.head_type == 2:
            return 10+int(large) if port == 1 else 12 if port in (2, 4) else 13 if port in (3, 5) else 9
        return (3 if large else 1) if port == 0 else 2 if port == 1 else 7 if port in (2, 4) else 8 if port in (3, 5) else 1


@dataclass(frozen=True)
class EngineBlock:
    bore_m: float
    stroke_m: float
    displacement_l: float
    cylinders: int
    mass: float

    @classmethod
    def from_physics(cls, record):
        """Decode core block fields, preserving the stored displacement.

        Native bounds below cover mass and Val1–4 only. Family/configuration
        metadata and the remaining block parameters are not interpreted here.
        """
        if record.mass is None or len(record.values) < 4:
            raise ValueError('engine block requires mass and four physics values')
        bore, stroke, displacement, cylinders = record.values[:4]
        if not all(math.isfinite(v) for v in (record.mass, bore, stroke, displacement, cylinders)):
            raise ValueError('non-finite engine block values')
        cylinders = round(cylinders)
        if not (30 <= record.mass <= 200 and 0.0508 <= bore <= 0.127 and
                0.0635 <= stroke <= 0.127 and 3 <= displacement <= 10 and
                6 <= cylinders <= 8):
            raise ValueError('engine block outside native core validation ranges')
        return cls(bore, stroke, displacement, cylinders, record.mass)

    @property
    def geometric_displacement_l(self):
        """Authored dimensional cross-check, never a replacement for Val3."""
        return math.pi / 4 * self.bore_m**2 * self.stroke_m * self.cylinders * 1000


@dataclass(frozen=True)
class TorqueCurve:
    """25 assembled torque samples spaced by 500 RPM from zero.

    Native 0x548f00 interpolates neighboring entries. Callers normally remain
    below the last knot. The portable API rejects unsafe out-of-table RPM.
    No curve generation or throttle behavior is implied by supplying samples.
    """
    samples: tuple

    def __post_init__(self):
        if len(self.samples) != 25 or not all(math.isfinite(v) for v in self.samples):
            raise ValueError('torque curve requires 25 finite samples')
        object.__setattr__(self, 'samples', tuple(self.samples))

    def torque(self, rpm):
        if type(rpm) is not int or not 0 <= rpm < 12000:
            raise ValueError('integer RPM must be within [0, 12000)')
        index, remainder = divmod(rpm, 500)
        lo, hi = self.samples[index:index+2]
        return lo + (hi-lo) * remainder * 0.002

    def power_kw(self, rpm):
        """Recovered 0x545af0 power factor; SI interpretation is derived."""
        return max(self.torque(rpm) * rpm * 0.00010471976, 0)
