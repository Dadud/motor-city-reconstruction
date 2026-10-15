"""Native/Python ordered drafting scan and cross-car state comparison."""
import argparse
import json
import math
import subprocess
from client.drafting import calculate_drafting
from tools.drafting_oracle import cases


def flatten(car):
    return (car.identifier, *car.position, *car.basis, *car.half_extents,
            *car.wake_origin, *(v for normal in car.wake_normals for v in normal))


def verify(runner):
    lines, expected = [], []
    for identifier, cars in cases():
        values = (identifier, len(cars), *(v for car in cars for v in flatten(car)))
        lines.append(' '.join(format(v, '.17g') for v in values))
        out = calculate_drafting(identifier, cars)
        expected.append((out.factor, -1 if out.selected_vehicle is None else out.selected_vehicle,
                         int(out.inside_wake), *(v for car in out.vehicles for v in flatten(car))))
    result = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                            text=True, check=True, timeout=30)
    output = result.stdout.splitlines()
    if len(output) != len(expected):
        raise AssertionError('drafting output count differs')
    maximum = 0.
    for index, (line, target) in enumerate(zip(output, expected)):
        actual = tuple(map(float, line.split()))
        if len(actual) != len(target) or actual[1:3] != target[1:3]:
            raise AssertionError(('drafting output shape or selection differs', index, actual, target))
        for offset, (a, b) in enumerate(zip(actual, target)):
            error = abs(a-b)
            if not math.isfinite(a) or error > max(3e-6, abs(b)*4e-7):
                raise AssertionError((index, offset, a, b, error))
            maximum = max(maximum, error)
    return {'cases': len(expected), 'maximum_absolute_error': maximum,
            'scope': 'native/Python drafting factor, ordered selection and complete cross-car state'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
