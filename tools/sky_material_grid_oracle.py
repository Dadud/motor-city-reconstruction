"""Compare sky-material height generation stages against original 0x4943f0."""
import argparse
import json
import math

from client.random_state import RandomState
from client.sky import sky_material_normalize_grid, sky_material_random_grid
from tools.native_oracle import DynoOracle


_INITIAL = (0xf22d0e56, 0x883126e9, 0xc624dd2f,
            0x0702c49c, 0x9e353f7d, 0x6fdf3b64)


def verify(executable):
    oracle = DynoOracle(executable)
    cases = 0
    for bound, modulus, angle, row_scale, column_scale in (
            (64, 8, 0.125, 1.0, 1.0), (0, 0, 0.0, 0.0, 0.0),
            (255, 31, -0.375, 1.25, 0.75), (128, 1, 0.25, -0.5, 2.0)):
        state = RandomState(_INITIAL)
        expected_raw = sky_material_random_grid(state, upper_bound=bound, modulus=modulus)
        actual_raw = oracle.sky_material_height_grid(
            'raw', upper_bound=bound, modulus=modulus, angle=angle,
            row_scale=row_scale, column_scale=column_scale, random_state=_INITIAL)
        if actual_raw != expected_raw:
            mismatch = next(i for i, pair in enumerate(zip(actual_raw, expected_raw))
                            if pair[0] != pair[1])
            raise AssertionError(('raw', bound, modulus, mismatch,
                                  actual_raw[mismatch], expected_raw[mismatch]))
        expected_normalized = sky_material_normalize_grid(expected_raw)
        actual_normalized = oracle.sky_material_height_grid(
            'normalized', upper_bound=bound, modulus=modulus, angle=angle,
            row_scale=row_scale, column_scale=column_scale, random_state=_INITIAL)
        errors = [abs(a-b) for a, b in zip(actual_normalized, expected_normalized)]
        if any(not math.isfinite(error) or error > 2e-5 for error in errors):
            index = max(range(len(errors)), key=errors.__getitem__)
            raise AssertionError(('normalized', bound, modulus, index,
                                  actual_normalized[index], expected_normalized[index], errors[index]))
        cases += 1
    return {'parameter_sets': cases, 'raw_values': cases*676,
            'normalized_values': cases*676,
            'maximum_normalization_error': max(errors),
            'scope': 'local random-height and signed-square-root stages only; native kernel stops before smoothing'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
