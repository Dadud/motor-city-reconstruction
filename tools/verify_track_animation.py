"""Compare mode-1 animation interpolation with original MCO 0x407940."""
import argparse
import json
import random
import struct

from client.track_object_animation import (evaluate_track_object_animation,
    quaternion_to_matrix)
from tools.native_oracle import DynoOracle


ANIMATION, POSITION, MATRIX, QUATERNION = (0x71001000, 0x71003000,
                                           0x71004000, 0x71005000)


def _near(actual, expected, tolerance=2e-5):
    return abs(actual - expected) <= max(tolerance, abs(expected) * 2e-6)


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 10_000:
        raise ValueError('cases must be between 1 and 10000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x407940)
    max_position_error = 0.0
    max_matrix_error = 0.0
    for case in range(cases):
        key_count = 2 + case % 7
        interval = (0, 1, 6, 17, 400, 401)[case % 6]
        animation = bytearray(8 + key_count * 0x14)
        struct.pack_into('<HH', animation, 4, key_count, interval)
        for frame in range(key_count):
            offset = 8 + frame * 0x14
            struct.pack_into('<3i', animation, offset,
                             *(rng.randint(-500000, 500000) for _ in range(3)))
            struct.pack_into('<4h', animation, offset + 12,
                             *(rng.randint(-16000, 16000) for _ in range(4)))
        period = interval if interval not in (0,) and interval <= 400 else 6
        branch = case % 3
        if branch == 2:
            mode = 2
            time_value = (key_count - 1) * period
            expected_pose = None
        elif branch == 1:
            mode = 2
            time_value = rng.randrange((key_count - 1) * period)
            expected_pose = evaluate_track_object_animation(animation, time_value, mode=mode)
        else:
            mode = 1
            time_value = rng.randint(0, 100_000)
            expected_pose = evaluate_track_object_animation(animation, time_value, mode=mode)
        oracle._reset()
        oracle.cpu.mem_write(ANIMATION, bytes(animation))
        sentinels = bytes([0xA5]) * 12, bytes([0x5A]) * 36
        oracle.cpu.mem_write(POSITION, sentinels[0])
        oracle.cpu.mem_write(MATRIX, sentinels[1])
        oracle.call(0x407940, (ANIMATION, mode, time_value, POSITION, MATRIX),
                    instruction_limit=100_000)
        native_result = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if expected_pose is None:
            if native_result != 0 or bytes(oracle.cpu.mem_read(POSITION, 12)) != sentinels[0] or bytes(oracle.cpu.mem_read(MATRIX, 36)) != sentinels[1]:
                raise AssertionError(f'case {case}: final mode-2 interval did not return without writes')
        else:
            if native_result != 1:
                raise AssertionError(f'case {case}: mode {mode} returned {native_result}')
            actual_position = struct.unpack('<3f', oracle.cpu.mem_read(POSITION, 12))
            actual_matrix = struct.unpack('<9f', oracle.cpu.mem_read(MATRIX, 36))
            for label, actual, expected in (('position', actual_position, expected_pose.translation),
                                            ('matrix', actual_matrix, expected_pose.rotation)):
                for index, (a, b) in enumerate(zip(actual, expected)):
                    error = abs(a - b)
                    if label == 'position':
                        max_position_error = max(max_position_error, error)
                    else:
                        max_matrix_error = max(max_matrix_error, error)
                    if not _near(a, b):
                        raise AssertionError(
                            f'case {case}: mode {mode} {label}[{index}] native={a} port={b} error={error}')

        quaternion = tuple(rng.uniform(-2., 2.) for _ in range(4))
        oracle.cpu.mem_write(QUATERNION, struct.pack('<4f', *quaternion))
        oracle.cpu.mem_write(MATRIX, bytes(36))
        oracle.call(0x553710, (QUATERNION, MATRIX), instruction_limit=100_000)
        actual_matrix = struct.unpack('<9f', oracle.cpu.mem_read(MATRIX, 36))
        expected_matrix = quaternion_to_matrix(quaternion)
        for index, (a, b) in enumerate(zip(actual_matrix, expected_matrix)):
            error = abs(a - b)
            max_matrix_error = max(max_matrix_error, error)
            if not _near(a, b):
                raise AssertionError(
                    f'case {case}: 0x553710 matrix[{index}] native={a} port={b} error={error}')
    return {'entry': '0x407940', 'mode': 1, 'cases': cases,
            'maximum_position_absolute_error': max_position_error,
            'maximum_matrix_absolute_error': max_matrix_error,
            'scope': 'mode-1 and mode-2 animation branches plus standalone quaternion-to-matrix outputs'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.cases)))


if __name__ == '__main__':
    main()
