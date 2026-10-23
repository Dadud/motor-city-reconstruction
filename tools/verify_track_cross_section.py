"""Compare the 0x495240 track cross-section builder with mcity.exe."""
import argparse
import random
from pathlib import Path

from client.track_cross_section import build_track_cross_section
from tools.native_oracle import DynoOracle


def verify(executable, cases=128):
    oracle = DynoOracle(executable)
    rng = random.Random(0x495240)
    vectors = []
    for _ in range(cases):
        obj = [rng.uniform(-5.0, 5.0) for _ in range(14)]
        basis = [rng.uniform(-2.0, 2.0) for _ in range(3)]
        view = [rng.uniform(-20.0, 20.0) for _ in range(3)]
        origin = [rng.uniform(-20.0, 20.0) for _ in range(3)]
        vectors.append((obj, basis, rng.uniform(-5.0, 5.0),
                        rng.uniform(0.1, 10.0), view, origin,
                        rng.uniform(0.1, 20.0), 0.0))
    maximum_position_error = maximum_angle_error = 0.0
    for index, args in enumerate(vectors):
        expected_points, expected_angle = build_track_cross_section(*args)
        status, actual_points, actual_angle = oracle.track_cross_section(*args)
        if status != 1:
            raise AssertionError(f'case {index}: native status {status}')
        expected = tuple(value for point in expected_points for value in point)
        for component, (actual, target) in enumerate(zip(actual_points, expected)):
            error = abs(actual-target)
            maximum_position_error = max(maximum_position_error, error)
            if error > 2e-5:
                raise AssertionError((index, component, actual, target, error))
        error = abs(actual_angle-expected_angle)
        maximum_angle_error = max(maximum_angle_error, error)
        if error > 2e-7:
            raise AssertionError((index, 'angle', actual_angle, expected_angle, error))
    return {'cases': len(vectors), 'maximum_position_error': maximum_position_error,
            'maximum_angle_error': maximum_angle_error,
            'comparison': 'original 0x495240; native float stores; angle no-wrap domain'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.cases <= 1024:
        parser.error('--cases must be within [1, 1024]')
    print(verify(args.executable, args.cases))
