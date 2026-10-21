"""Local engine-flow inputs recovered from REA 0x46dc20.

The original templates stay in the user's executable. This reader supports
only the verified build; it does not execute code or construct torque curves.
Series names/units and the remaining dyno solver are still unresolved.
"""
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import struct

_SOURCE_SHA256 = '28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164'


def build_dyno_record(block, head, camshaft, valve_train, template, *,
                      intake_mode, intake_flow, exhaust_mode, exhaust_flow,
                      carb_capacity, carb_code):
    """Serialize the recovered naturally aspirated 0x46d1d0 core input.

    Intake/exhaust modes are already transformed dyno codes. Additional stock
    Boost branches are not represented; the carburetor-six finalizer reuses
    this record with its own second-pass capacity. Template flow must already
    include assembled modifiers; this is not a complete stock engine assembler.
    Evidence: REA 198/221; 1004-byte buffer, cam field permutation and flow
    series placement. Unwritten fields keep the builder's zero initialization.
    """
    if (type(intake_mode) is not int or not 1 <= intake_mode <= 6 or
            type(exhaust_mode) is not int or not 1 <= exhaust_mode <= 6 or
            type(carb_code) is not int or carb_code not in (2, 4)):
        raise ValueError('unsupported dyno mode/code')
    if not all(math.isfinite(v) for v in (intake_flow, exhaust_flow, carb_capacity)):
        raise ValueError('non-finite dyno inputs')
    if type(carb_capacity) is not int or not 0 <= carb_capacity <= 32767:
        raise ValueError('carb capacity outside representable dyno range')
    data = bytearray(1004)
    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    metres_to_inches = f32(39.3701)
    millimetres_to_metres = f32(.001)
    intake_inches = f32(head.intake_valve_mm)*millimetres_to_metres*metres_to_inches
    exhaust_inches = f32(head.exhaust_valve_mm)*millimetres_to_metres*metres_to_inches
    def short(offset, value):
        struct.pack_into('<h', data, offset, value)
    def floating(offset, value):
        if not math.isfinite(value):
            raise ValueError('non-finite assembled dyno input')
        try:
            struct.pack_into('<f', data, offset, value)
        except (OverflowError, struct.error) as error:
            raise ValueError('dyno input exceeds float32') from error
    for offset, value in ((0x6e, intake_mode), (0x76, template.identifier),
                          (0x7a, exhaust_mode), (0x80, camshaft.cam_type+1),
                          (0x84, valve_train.train_type+1),
                          (0x94, block.cylinders), (0xa4, max(carb_capacity, 300)),
                          (0xa6, carb_code), (0x2dc, 1), (0x310, 1), (0x312, 1)):
        short(offset, value)
    lift = camshaft.valve_lift_inches(valve_train.lift_factor)
    timing = camshaft.timing_fields
    for offset, value in ((0x70, min(max(f32(intake_flow), f32(.9)), f32(1.1))),
                          (0x7c, min(max(f32(exhaust_flow), f32(.95)), f32(1.08))),
                          (0x8c, f32(block.bore_m)*metres_to_inches),
                          (0x90, f32(block.stroke_m)*metres_to_inches),
                          (0x98, intake_inches), (0x9c, exhaust_inches),
                          (0xa0, min(max(f32(head.compression_ratio), 6), 18)),
                          (0xa8, timing[2]), (0xac, timing[3]),
                          (0xb0, timing[0]), (0xb4, timing[1]),
                          (0xb8, lift[0]), (0xbc, lift[1]),
                          (0x314, intake_inches),
                          (0x318, template.scalar_fields[2]),
                          (0x31c, exhaust_inches),
                          (0x320, template.scalar_fields[3])):
        floating(offset, value)
    for offset, series in ((0x324, template.series[2]), (0x34c, template.series[3]),
                           (0x374, template.series[0]), (0x39c, template.series[1])):
        for index, value in enumerate(series):
            floating(offset+index*4, value)
    return bytes(data)


def intake_rpm_correction(mode, rpm, flow_factor):
    """Port the dyno term at 0x479c5e–0x479deb (REA 201/221).

    Mode is the *dyno* code (1–6), not raw intake-manifold Val1. Builder
    0x46d1d0 derives it from manifold type and the intake-pipe field +0x5a0.
    Stock solver RPM samples run 2000–11000. The term's physical units are
    unresolved; this is neither engine torque nor an intake force.
    Float constants/exponents are source values, but x87 intermediate precision
    and libm equivalence are not claimed. Mode 5 intentionally becomes negative
    above 8000 RPM, matching the native branch.
    """
    if type(mode) is not int or not 1 <= mode <= 6:
        raise ValueError('dyno intake mode must be within [1, 6]')
    if not math.isfinite(rpm) or not 2000 <= rpm <= 11000:
        raise ValueError('dyno RPM must be within [2000, 11000]')
    if not math.isfinite(flow_factor) or not .9 <= flow_factor <= 1.1:
        raise ValueError('dyno intake flow factor must be within [.9, 1.1]')
    # Both inputs occupy float32 fields in the native dyno/stack records.
    rpm, flow_factor = struct.unpack('<ff', struct.pack('<ff', rpm, flow_factor))
    if mode == 1:
        term = min(max(rpm**1.2999999523162842 * 8.030000026337802e-05, 0), 7.5)
    elif mode == 2:
        term = min(max(rpm**1.3300000429153442 * 9.030000001075678e-06 + 3, 0), 5)
    elif mode == 3:
        term = max(rpm**1.2699999809265137 * .00010299999848939478, 0)
    elif mode == 4:
        term = min(max(rpm**1.2999999523162842 * .0001429999974789098, 0), 7.5)
    elif mode == 5:
        term = 4 if rpm <= 4000 else 8 - rpm*.0010000000474974513
    else:
        term = min(rpm**1.309999942779541 * .00010299999848939478, 4.5)
    return struct.unpack('<f', struct.pack('<f', term*flow_factor))[0]


@dataclass(frozen=True)
class FlowTemplate:
    identifier: int
    scalar_fields: tuple
    series: tuple

    def __post_init__(self):
        scalars = tuple(self.scalar_fields)
        series = tuple(tuple(values) for values in self.series)
        if (type(self.identifier) is not int or not 1 <= self.identifier <= 16 or
                len(scalars) != 4 or len(series) != 4 or
                any(len(values) != 8 for values in series) or
                not all(math.isfinite(v) for v in scalars + sum(series, ()))):
            raise ValueError('invalid flow template')
        object.__setattr__(self, 'scalar_fields', scalars)
        object.__setattr__(self, 'series', series)

    def scaled(self, modifier):
        """Scale series 0 and 2, preserving the other fields (0x46f32d).

        Native stores each product as float32. Python multiplication does not
        emulate intermediate x87 extended precision.
        """
        if not math.isfinite(modifier):
            raise ValueError('non-finite flow modifier')
        try:
            series = tuple(tuple(struct.unpack('<f', struct.pack('<f', value * modifier))[0]
                                 for value in values) if index in (0, 2) else values
                           for index, values in enumerate(self.series))
            return FlowTemplate(self.identifier, self.scalar_fields, series)
        except (OverflowError, struct.error) as error:
            raise ValueError('flow scaling exceeds float32') from error


def load_flow_templates(executable):
    """Extract 592 stack-initializer words from the exact verified PE build.

    File offsets equal RVAs in this build. The digest guard binds those offsets
    and the two MOV encodings to the complete binary analyzed by REA 204.
    This is a build-specific data extractor, not a general x86 disassembler.
    """
    path = Path(executable)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('executable exceeds supported size')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != _SOURCE_SHA256:
        raise ValueError('unsupported executable: SHA-256 differs from verified build')
    words = {}
    cursor, end = 0x6dc20, 0x6f349
    while cursor < end:
        opcode = data[cursor:cursor+2]
        if opcode == b'\xc7\x85':
            displacement, word = struct.unpack_from('<iI', data, cursor+2)
            length = 10
        elif opcode == b'\xc7\x45':
            displacement = struct.unpack_from('<b', data, cursor+2)[0]
            word = struct.unpack_from('<I', data, cursor+3)[0]
            length = 7
        else:
            cursor += 1
            continue
        if -0x940 <= displacement <= -4 and displacement % 4 == 0:
            if displacement in words:
                raise ValueError('duplicate template initializer')
            words[displacement] = word
        cursor += length
    if len(words) != 592:
        raise ValueError('incomplete flow template initialization')
    templates = {}
    for index in range(16):
        record = [words[-0x940 + (index*37 + field)*4] for field in range(37)]
        if record[0] != index+1:
            raise ValueError('flow template identity mismatch')
        values = struct.unpack('<36f', struct.pack('<36I', *record[1:]))
        templates[index+1] = FlowTemplate(index+1, values[:4],
            tuple(values[4+series*8:12+series*8] for series in range(4)))
    return templates
