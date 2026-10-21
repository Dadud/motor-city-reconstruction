"""Compare the recovered 0x5779d0 port to the exact shipped x86 routine."""
import argparse
import struct
from pathlib import Path

from client.world_object_damping import WorldObjectMotion, update_world_object_motion
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    base = oracle.inputs
    cases = (
        WorldObjectMotion(1, (0.1, -0.2, 0.3), (1.0, -2.0, 3.0)),
        WorldObjectMotion(-3, (4.0, 5.0, 6.0), (-0.1, 0.25, 10.0)),
        WorldObjectMotion(0, (0.49, -0.5, 0.6), (0.049, 0.08, -0.1)),
        WorldObjectMotion(0, (1.0, 2.0, 3.0), (0.2, 0.049, 0.049)),
        WorldObjectMotion(0, (0.5, 0.0, 0.0), (0.05, 0.05, 0.05)),
    )
    for case in cases:
        oracle.cpu.mem_write(base, bytes(0x400))
        oracle.cpu.mem_write(base + 0x3BC, struct.pack('<h', case.contact_counter))
        oracle.cpu.mem_write(base + 0x14, struct.pack('<3f', *case.linear_velocity))
        oracle.cpu.mem_write(base + 0x38, struct.pack('<3f', *case.angular_velocity))
        oracle.call(0x5779D0, arguments=(base,))
        actual = (bytes(oracle.cpu.mem_read(base + 0x14, 12)),
                  bytes(oracle.cpu.mem_read(base + 0x38, 12)))
        expected_state = update_world_object_motion(case)
        expected = (struct.pack('<3f', *expected_state.linear_velocity),
                    struct.pack('<3f', *expected_state.angular_velocity))
        if actual != expected:
            raise AssertionError(f'original mismatch for {case}: {actual!r} != {expected!r}')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path,
                        help='exact verified Motor City Online executable')
    args = parser.parse_args()
    print(f'original callback matches Python port for {verify(args.executable)} cases')


if __name__ == '__main__':
    main()
