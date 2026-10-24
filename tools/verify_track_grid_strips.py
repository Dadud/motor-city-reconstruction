"""Compare the full 0x495800 grid-strip outputs with mcity.exe."""
import argparse
import random
from pathlib import Path

from client.track_cross_section import build_track_grid_strips
from tools.native_oracle import DynoOracle


def verify(executable, cases=256):
    oracle = DynoOracle(executable)
    rng = random.Random(0x495800)
    max_position_error = max_angle_error = 0.0
    for case in range(cases):
        obj = [rng.uniform(-5.0, 5.0) for _ in range(14)]
        basis = [rng.uniform(-2.0, 2.0) for _ in range(3)]
        view = [rng.uniform(-20.0, 20.0) for _ in range(3)]
        origin = [rng.uniform(-20.0, 20.0) for _ in range(3)]
        values = (obj, basis, rng.uniform(-5.0, 5.0),
                  rng.uniform(0.1, 10.0), view, origin,
                  rng.uniform(0.1, 20.0), rng.uniform(-4.0, 4.0))
        expected_outer, expected_inner, expected_angle = build_track_grid_strips(*values)
        status, actual_outer, actual_inner, actual_angle = oracle.track_grid_strips(*values)
        if status != 1:
            raise AssertionError((case, 'return', status))
        for strip_id, actual, expected in ((0, actual_outer, expected_outer),
                                           (1, actual_inner, expected_inner)):
            if len(actual) != 17 or len(expected) != 17:
                raise AssertionError((case, strip_id, len(actual), len(expected)))
            for point in range(17):
                for axis in range(3):
                    error = abs(actual[point][axis] - expected[point][axis])
                    max_position_error = max(max_position_error, error)
                    if error > 5e-4:
                        raise AssertionError((case, strip_id, point, axis,
                                              actual[point][axis],
                                              expected[point][axis], error))
        angle_error = abs(actual_angle-expected_angle)
        max_angle_error = max(max_angle_error, angle_error)
        if angle_error > 2e-7:
            raise AssertionError((case, 'angle', actual_angle, expected_angle))
    return {'cases': cases, 'points_compared': cases*2*17,
            'maximum_position_error': max_position_error,
            'maximum_angle_error': max_angle_error,
            'domain': 'finite randomized inputs with positive and negative wrapped angles'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    if not 1 <= args.cases <= 2048:
        parser.error('--cases must be within [1, 2048]')
    print(verify(args.executable, args.cases))
