"""Owned state updates of the scheduled object physics callback 0x520c20."""
import math
import struct

from .tire_response import f32


RECORD_SIZE = 0x4f8


def _read_f(record, offset):
    return struct.unpack_from('<f', record, offset)[0]


def _write_f(record, offset, value):
    struct.pack_into('<f', record, offset, f32(value))


def step_world_object_physics(record, *, mode_active, mode_number,
                              environment_step, contact_force_step):
    """Execute 0x520c20's own updates, requiring its two native child stages.

    The callbacks correspond to 0x51e940 and 0x51fc00. Their effects are not
    approximated here: each receives the same mutable object record.
    """
    if not isinstance(record, bytearray) or len(record) < RECORD_SIZE:
        raise ValueError('a mutable 0x4f8-byte world-object record is required')
    if type(mode_active) is not bool or type(mode_number) is not int:
        raise ValueError('observed scheduler mode values are required')
    if not callable(environment_step) or not callable(contact_force_step):
        raise ValueError('both original physics child stages are required')

    run_forces = not (record[6] != 0 and mode_active and mode_number == 1)
    environment_step(record)

    if run_forces and record[4] != 0 and record[7] == 0:
        # The binary first installs its default acceleration, then replaces it
        # with gravity projected through the object's basis when contact count
        # is zero. Every value is rounded where the original writes a float.
        for offset, value in ((0x2c, 0.0), (0x30, -9.81), (0x34, 0.0)):
            _write_f(record, offset, value)
        if struct.unpack_from('<h', record, 0x3bc)[0] == 0:
            accel_local = tuple(f32(_read_f(record, offset) * f32(-9.81))
                                for offset in (0x320, 0x32c, 0x338))
            basis = tuple(_read_f(record, offset)
                          for offset in (0x31c, 0x320, 0x324,
                                         0x328, 0x32c, 0x330,
                                         0x334, 0x338, 0x33c))
            x, y, z = accel_local
            rows = ((basis[6], basis[3], basis[0]),
                    (basis[7], basis[4], basis[1]),
                    (basis[8], basis[5], basis[2]))
            for offset, row in zip((0x2c, 0x30, 0x34), rows):
                _write_f(record, offset, z*row[0] + y*row[1] + x*row[2])

        if _read_f(record, 0x6c) == 0.0:
            for velocity, acceleration in zip((0x14, 0x18, 0x1c),
                                              (0x2c, 0x30, 0x34)):
                _write_f(record, velocity,
                         _read_f(record, velocity) + _read_f(record, acceleration)*0.03125)
        else:
            for offset in (0x14, 0x18, 0x1c, 0x38, 0x3c, 0x40):
                _write_f(record, offset, 0.0)

    if run_forces:
        contact_force_step(record)

    angular = tuple(_read_f(record, offset) for offset in (0x38, 0x3c, 0x40))
    linear = tuple(_read_f(record, offset) for offset in (0x14, 0x18, 0x1c))
    inertia = tuple(_read_f(record, offset) for offset in (0x2f0, 0x2f4, 0x2f8))
    angular_speed = math.sqrt(sum(value*value for value in angular))
    linear_speed = f32(math.sqrt(sum(value*value for value in linear)))
    turns_per_second = f32(angular_speed * f32(6.2831855))
    energy = (linear_speed * _read_f(record, 0x50) * linear_speed * 0.5 +
              math.sqrt(sum(value*value for value in inertia)) *
              turns_per_second * turns_per_second * 0.5)
    _write_f(record, 0x3c0, energy)
    return record
