"""Compare native wheel curves with the original-checked Python corpus."""
import argparse
import json
import math
import subprocess

from client.tire_response import wheel_response, f32
from tools.tire_response_oracle import cases


def verify(runner):
    corpus = list(cases())
    lines = []
    for table, coefficient, wheel, secondary, alternate in corpus:
        values = (int(secondary), int(alternate), coefficient, wheel.slip_angle,
                  wheel.secondary_angle, wheel.normal_load,
                  wheel.surface_multiplier, *table)
        lines.append(' '.join(format(value, '.17g') for value in values))
    result = subprocess.run([str(runner)], input='\n'.join(lines) + '\n',
                            capture_output=True, text=True, check=True, timeout=30)
    output = result.stdout.splitlines()
    if len(output) != len(corpus):
        raise AssertionError('native response count differs from corpus')
    maximum_error = 0.0
    for index, (line, case) in enumerate(zip(output, corpus)):
        table, coefficient, wheel, secondary, alternate = case
        actual = f32(float(line))
        expected = wheel_response(table, coefficient, wheel, secondary=secondary,
                                  alternate_load=alternate)
        error = abs(actual - expected)
        tolerance = max(0.00025, abs(expected) * 3e-7)
        if not math.isfinite(actual) or error > tolerance:
            raise AssertionError((index, actual, expected, error, tolerance))
        maximum_error = max(maximum_error, error)
    return {'cases': len(corpus), 'maximum_absolute_error': maximum_error,
            'scope': 'native/Python synthetic wheel response corpus; no original assets or live driving'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
