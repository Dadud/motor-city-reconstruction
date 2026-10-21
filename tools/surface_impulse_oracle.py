"""Compare single-body support impulse response 0x457df0 with the original."""
import argparse
import json
import struct

from client.collision_pair_response import resolve_surface_impulse
from tools.collision_pair_response_oracle import body_image, cases
from tools.native_oracle import DynoOracle


OWNER = 0x71000000


def run_native(oracle, body, contact, normal, coefficients):
    oracle._reset()
    cpu = oracle.cpu
    cpu.mem_write(OWNER, body_image(body))
    cpu.mem_write(0x71002000, struct.pack('<3f', *contact))
    cpu.mem_write(0x71003000, struct.pack('<3f', *normal))
    oracle.call(0x457df0, (OWNER, 0x71002000, 0x71003000,
                           struct.unpack('<I', struct.pack('<f', coefficients[0]))[0],
                           struct.unpack('<I', struct.pack('<f', coefficients[1]))[0]),
                instruction_limit=1_000_000)
    return (cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
            struct.unpack('<3f', cpu.mem_read(OWNER + 0x14, 12)),
            struct.unpack('<3f', cpu.mem_read(OWNER + 0x38, 12)),
            bytes(cpu.mem_read(OWNER + 0x3c4, 0x3c)))


def compare(executable, count=128):
    oracle = DynoOracle(executable)
    maximum = 0.0
    for index, (owner, _target, contact, normal, coefficients) in enumerate(cases(count)):
        native_hit, native_linear, native_angular, native_record = run_native(
            oracle, owner, contact, normal, coefficients)
        expected = resolve_surface_impulse(owner, contact, normal, *coefficients)
        if native_hit != int(expected.collided):
            raise AssertionError(f'case {index} impact decision differs')
        for part, (actual, wanted) in enumerate(zip(
                (*native_linear, *native_angular),
                (*expected.body.linear_velocity, *expected.body.angular_turn_velocity))):
            error = abs(actual - wanted)
            maximum = max(maximum, error)
            if error > max(3e-5, abs(actual) * 5e-6):
                raise AssertionError(f'case {index} velocity[{part}] differs: {actual} != {wanted}')
        record = expected.body.contact_record[0x3c4:0x400]
        actual_ints = (struct.unpack_from('<I', native_record, 0)[0],
                       struct.unpack_from('<I', native_record, 32)[0],
                       *struct.unpack_from('<II', native_record, 48))
        wanted_ints = (struct.unpack_from('<I', record, 0)[0],
                       struct.unpack_from('<I', record, 32)[0],
                       *struct.unpack_from('<II', record, 48))
        if actual_ints != wanted_ints:
            raise AssertionError(f'case {index} contact record integer fields differ')
        float_offsets = (4, 8, 12, 16, 20, 24, 28, 36, 40, 44, 56)
        for offset in float_offsets:
            actual = struct.unpack_from('<f', native_record, offset)[0]
            wanted = struct.unpack_from('<f', record, offset)[0]
            error = abs(actual - wanted)
            maximum = max(maximum, error)
            if error > max(2e-4, abs(actual) * 1e-6):
                raise AssertionError(f'case {index} contact record float at {offset:#x} differs')
    return {'entry': '0x457df0', 'cases': count,
            'maximum_absolute_output_error': maximum,
            'scope': 'single-body support impulse accumulation and contact record'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
