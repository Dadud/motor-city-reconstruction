"""Compare recovered clip-code behavior with direct mcity.exe execution."""
import argparse
import random

from tools.native_oracle import DynoOracle
from client.render_clip_code import RenderClipBounds, render_clip_code


def verify(executable, cases=512):
    if type(cases) is not int or not 1 <= cases <= 100_000:
        raise ValueError('cases must be between 1 and 100000')
    oracle = DynoOracle(executable)
    rng = random.Random(0x6cb810)
    bounds = RenderClipBounds(-0x100000, 0x100000, -0x80000,
                             0x80000, 0x200000, -0x200000)
    vertices = [
        (bounds.x_lower, bounds.y_lower, bounds.z_lower, 1),
        (bounds.x_upper, bounds.y_upper, bounds.z_lower - 1, bounds.w_upper),
        (bounds.x_lower - 1, bounds.y_upper + 1, bounds.z_lower, -1),
        (bounds.x_upper + 1, bounds.y_lower - 1, bounds.z_lower - 1,
         bounds.w_upper + 1),
        (0, 0, 0, 0),
    ]
    for _ in range(max(0, cases - len(vertices))):
        vertices.append(tuple(rng.randint(-(1 << 31), (1 << 31) - 1)
                              for _ in range(4)))
    limits=(bounds.x_lower, bounds.x_upper, bounds.y_lower, bounds.y_upper,
            bounds.w_upper, bounds.z_lower)
    for index, vertex in enumerate(vertices):
        expected = render_clip_code(vertex, bounds)
        actual = oracle.render_clip_code(vertex, limits)
        if actual != expected:
            raise AssertionError(
                f'case {index}: vertex={vertex!r}, expected={expected:#04x}, '
                f'actual={actual:#04x}')
    return len(vertices)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args=parser.parse_args()
    count=verify(args.executable,args.cases)
    print(f'0x6cb810 matches {count} signed XYZW clip-code cases')


if __name__ == '__main__':
    main()
