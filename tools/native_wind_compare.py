"""Compare native wind calculation with the original-verified Python corpus."""
import argparse
import json
import math
import subprocess
from client.wind import calculate_wind
from tools.wind_oracle import cases


def verify(runner):
    lines, expected = [], []
    for state in cases():
        values = (state.simulation_counter, state.weather_seed, *state.track_direction,
                  *state.world_to_body, int(state.disabled))
        lines.append(' '.join(format(value, '.17g') for value in values))
        out = calculate_wind(state)
        expected.append((*out.body_velocity, int(out.present)))
    result = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                            text=True, check=True, timeout=30)
    output = result.stdout.splitlines()
    if len(output) != len(expected):
        raise AssertionError('wind output count differs')
    maximum = 0.
    for index, (line, target) in enumerate(zip(output, expected)):
        actual = tuple(map(float, line.split()))
        if len(actual) != 4 or actual[3] != target[3]:
            raise AssertionError(('wind output shape or presence differs', index, actual, target))
        for a, b in zip(actual[:3], target[:3]):
            error = abs(a-b)
            if not math.isfinite(a) or error > max(2e-6, abs(b)*4e-7):
                raise AssertionError((index, actual, target, error))
            maximum = max(maximum, error)
    return {'cases': len(expected), 'maximum_absolute_error': maximum,
            'scope': 'native/Python wind calculation; counter, track, seed and mode supplied'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
