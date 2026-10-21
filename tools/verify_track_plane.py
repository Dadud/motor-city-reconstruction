"""Compare track quad plane construction with original 0x42dc50."""
import argparse
import random
import struct
from pathlib import Path

from client.track_plane import track_plane
from tools.native_oracle import DynoOracle


RECORD = 0x71002000
POINT_OUT = 0x71003000
NORMAL_OUT = 0x71003010
VERTICES = 0x71004000


def verify(executable, cases=256):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x42DC50)
    for case in range(cases):
        # A warped quad exercises both native triangle choices and the
        # second-triangle fallback when the first cross product is degenerate.
        p4 = (0.0, 0.0, 0.0)
        p5 = (0.0, 0.0, 10.0)
        p6 = (10.0, rng.uniform(-3, 3), 10.0)
        p7 = (10.0, rng.uniform(-3, 3), 0.0)
        vertices = tuple(tuple(struct.unpack('<f', struct.pack('<f', v))[0]
                               for v in point)
                         for point in (p4, p5, p6, p7))
        x, z = rng.randint(-2, 12), rng.randint(-2, 12)
        cpu.mem_write(VERTICES, b''.join(struct.pack('<3f', *v) for v in vertices))
        pointers = (VERTICES, VERTICES + 12, VERTICES + 24, VERTICES + 36)
        record = bytearray(0x2c)
        struct.pack_into('<I', record, 0x0c, 1)
        # Native parameter fields are [4]=p4, [5]=p5, [6]=p6, [7]=p7.
        for slot, pointer in zip((4, 5, 6, 7), pointers):
            struct.pack_into('<I', record, slot * 4, pointer)
        struct.pack_into('<i', record, 0x20, x)
        struct.pack_into('<i', record, 0x28, z)
        cpu.mem_write(RECORD, bytes(record))
        cpu.mem_write(POINT_OUT, b'\x00' * 12)
        cpu.mem_write(NORMAL_OUT, b'\x00' * 12)
        oracle.call(0x0042DC50, (POINT_OUT, RECORD, NORMAL_OUT),
                    instruction_limit=20000)
        original = (cpu.mem_read(POINT_OUT, 12), cpu.mem_read(NORMAL_OUT, 12))
        point, normal = track_plane(x, z, vertices)
        translated = (struct.pack('<3f', *point), struct.pack('<3f', *normal))
        def ulps(left, right):
            a, b = struct.unpack('<3I', left), struct.unpack('<3I', right)
            def ordered(value):
                return (~value & 0xffffffff) if value & 0x80000000 else value | 0x80000000
            return tuple(abs(ordered(x) - ordered(y)) for x, y in zip(a, b))

        normal_ulp = ulps(original[1], translated[1])
        actual_normal = struct.unpack('<3f', original[1])
        expected_normal = struct.unpack('<3f', translated[1])
        error = max(abs(a - b) for a, b in zip(actual_normal, expected_normal))
        if original[0] != translated[0] or error > 2e-7:
            raise AssertionError(
                f'0x42dc50 mismatch case {case}: xz={(x,z)}, '
                f'original={[v.hex() for v in original]}, '
                f'translated={[v.hex() for v in translated]}, ulps={normal_ulp}, error={error}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(f'0x42dc50 triangle plane point/normal match {verify(args.executable, args.cases)} original cases')


if __name__ == '__main__':
    main()
