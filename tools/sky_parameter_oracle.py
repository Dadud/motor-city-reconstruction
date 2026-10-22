"""Compare recovered 0x494dc0 parameter normalization with mcity.exe."""
import argparse
import json
import math

from client.sky import prepare_sky_material_parameters
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cases = (
        (64, 8, 4, 0.25, 0.0, 2.0, 90, 1000),
        (8, 31, 0, 0.125, 0.75, 0.0, -45, 2500),
        (0, 0, -3, 9.0, -1.5, 2.0, 720, -1200),
        (255, 1, 10, -0.5, 1.25, -2.0, 13, 17000),
    )
    max_error = 0.0
    for case in cases:
        bound, modulus, divisor, reciprocal, column, row, angle, radius = case
        expected = prepare_sky_material_parameters(
            height_bound=bound, random_modulus=modulus,
            random_divisor=divisor, random_reciprocal=reciprocal,
            column_scale=column, row_scale=row,
            angle_degrees=angle, radial_distance=radius)
        actual = oracle.sky_material_parameters(
            height_bound=bound, random_modulus=modulus,
            random_divisor=divisor, random_reciprocal=reciprocal,
            column_scale=column, row_scale=row,
            angle_degrees=angle, radial_distance=radius)
        expected_values = (expected.random_modulus, expected.random_reciprocal,
                           expected.column_scale, expected.row_scale,
                           expected.profile_cosine, expected.profile_sine)
        for index, (got, target) in enumerate(zip(actual, expected_values)):
            if index == 0:
                if got != target:
                    raise AssertionError((case, index, got, target))
            else:
                error = abs(got-target)
                max_error = max(max_error, error)
                if not math.isfinite(error) or error > 2e-5:
                    raise AssertionError((case, index, got, target, error))
    return {'parameter_sets': len(cases), 'fields_per_case': 6,
            'maximum_float_error': max_error,
            'scope': '0x494dc0 mutating fields under synthetic x86 state'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
