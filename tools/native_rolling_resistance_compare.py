"""Native/Python comparison of the bounded resistance oracle scenarios."""
import argparse
import itertools
import json
import math
import subprocess

from client.rolling_resistance import ResistanceWheel, rolling_resistance
from client.tire_response import f32


def cases():
    # Same synthetic state matrix as the complete original-function oracle.
    for speed, disabled, mode, alternate, angle, contact_mask, rolling in itertools.product(
            (-20, -2, -1.9999, 0, 1.9999, 2, 20), (False, True), (False, True),
            (False, True), (0, 0.1), (0, 5, 15), (-2, 0.5, 0.5001, 2)):
        wheels = tuple(ResistanceWheel((i-1)*0.01, surface,
            0 if i == 3 else 1500+i*500, rolling, 2,
            bool(contact_mask & (1 << i)), 100+i) for i, surface in enumerate((2, 3, 5, 0)))
        yield wheels, speed, 1.2, 0.8, 0.3, -0.1, angle, disabled, mode, alternate


def verify(runner):
    corpus = list(cases())
    lines, expected = [], []
    for wheels, speed, front, rear, fa, ra, angle, disabled, mode, alternate in corpus:
        values = [speed, front, rear, fa, ra, angle, int(disabled), int(mode), int(alternate)]
        for w in wheels:
            values.extend((w.slip_angle, w.surface_id, w.normal_load, w.rolling_speed,
                           w.speed_scale, int(w.contact), w.longitudinal_force))
        lines.append(' '.join(format(x, '.17g') for x in values))
        expected.append(rolling_resistance(wheels, speed, front, rear, fa, ra, angle,
            disabled_flag=disabled, mode_predicate=mode, alternate=alternate))
    process = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                             text=True, check=True, timeout=30)
    outputs = process.stdout.splitlines()
    if len(outputs) != len(expected):
        raise AssertionError('native resistance output count differs')
    maximum_error = 0.0
    for index, (line, result) in enumerate(zip(outputs, expected)):
        fields = line.split()
        if len(fields) != 29:
            raise AssertionError('native resistance output shape differs')
        actual_return = f32(float(fields[0]))
        pairs = [(actual_return, result.last_contribution)]
        for i, wheel in enumerate(result.wheels):
            actual = fields[1+i*7:8+i*7]
            if int(actual[1]) != wheel.surface_id or int(actual[5]) != int(wheel.contact):
                raise AssertionError((index, 'wheel identity changed'))
            pairs.extend((f32(float(actual[j])), value) for j, value in
                ((0, wheel.slip_angle), (2, wheel.normal_load), (3, wheel.rolling_speed),
                 (4, wheel.speed_scale), (6, wheel.longitudinal_force)))
        for value, target in pairs:
            error = abs(value-target)
            if not math.isfinite(value) or error > max(0.00025, abs(target)*3e-7):
                raise AssertionError((index, value, target, error))
            maximum_error = max(maximum_error, error)
    return {'cases': len(corpus), 'maximum_absolute_error': maximum_error,
            'scope': 'native/Python complete wheel observations and final contribution; synthetic state'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
