"""Compare sky-material height generation stages against original 0x4943f0."""
import argparse
import json
import math
import struct

from client.random_state import RandomState
from client.sky import (sky_material_normalize_grid, sky_material_random_grid,
                        sky_material_smooth_grid, sky_material_mesh_outputs)
from tools.native_oracle import DynoOracle


_INITIAL = (0xf22d0e56, 0x883126e9, 0xc624dd2f,
            0x0702c49c, 0x9e353f7d, 0x6fdf3b64)


def verify(executable):
    oracle = DynoOracle(executable)
    cases = 0
    max_smoothing_error = 0.0
    max_vertex_error = 0.0
    for (bound, modulus, angle, row_scale, column_scale, base, amplitude,
         color_scale, invert) in (
            (64, 8, 0.125, 1.0, 1.0, 0.75, 1.25, 0.8, False),
            (0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, False),
            (255, 31, -0.375, 1.25, 0.75, -0.3, 2.0, 0.6, True),
            (128, 1, 0.25, -0.5, 2.0, 1.25, 0.5, 1.1, False)):
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
        expected_smoothed = sky_material_smooth_grid(
            expected_normalized, upper_bound=bound)
        actual_smoothed = oracle.sky_material_height_grid(
            'smoothed', upper_bound=bound, modulus=modulus, angle=angle,
            row_scale=row_scale, column_scale=column_scale, random_state=_INITIAL)
        smooth_errors = [abs(a-b) for a, b in zip(actual_smoothed, expected_smoothed)]
        max_smoothing_error = max(max_smoothing_error, *smooth_errors)
        if any(not math.isfinite(error) or error > 2e-4 for error in smooth_errors):
            index = max(range(len(smooth_errors)), key=smooth_errors.__getitem__)
            raise AssertionError(('smoothed', bound, modulus, index,
                                  actual_smoothed[index], expected_smoothed[index],
                                  smooth_errors[index]))
        expected_positions, expected_mesh = sky_material_mesh_outputs(
            expected_smoothed, angle=angle, row_scale=row_scale,
            column_scale=column_scale, base_offset=base, amplitude=amplitude,
            color_scale=color_scale, invert=invert)
        actual_output = oracle.sky_material_height_grid(
            'output', upper_bound=bound, modulus=modulus, angle=angle,
            row_scale=row_scale, column_scale=column_scale, random_state=_INITIAL,
            base_offset=base, amplitude=amplitude, color_scale=color_scale,
            invert=invert)
        actual_positions = struct.unpack_from('<2028f', actual_output, 0)
        for index, vertex in enumerate(expected_positions):
            for axis, expected in enumerate(vertex):
                error = abs(actual_positions[index*3+axis] - expected)
                max_vertex_error = max(max_vertex_error, error)
                if not math.isfinite(error) or error > 0.001:
                    raise AssertionError(('position', bound, index, axis,
                                          actual_positions[index*3+axis], expected, error))
        expected_mesh_bytes = b''.join(
            struct.pack('<ffI', *vertex) for vertex in expected_mesh)
        actual_mesh_bytes = actual_output[0x1fb0:0x1fb0+len(expected_mesh_bytes)]
        if actual_mesh_bytes != expected_mesh_bytes:
            raise AssertionError(('mesh coordinates or packed grayscale differ', bound))
        cases += 1
    return {'parameter_sets': cases, 'raw_values': cases*676,
            'normalized_values': cases*676,
            'maximum_normalization_error': max(errors),
            'maximum_smoothing_error': max_smoothing_error,
            'maximum_position_error': max_vertex_error,
            'mesh_and_grayscale_bytes_match': True,
            'scope': 'full local sky-material output arrays including 20 in-place smoothing passes; synthetic execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
