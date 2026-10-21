"""Differential-check native and Python owner-to-target box point tests."""
import argparse
import json
import subprocess

from client.collision_pair_geometry import (owner_point_contact_test,
                                            owner_point_direction_test)
from tools.collision_pair_geometry_oracle import reverse_cases


def verify(runner, case_count=192):
    corpus = list(reverse_cases(case_count))
    values = []
    for owner, target, point, with_direction in corpus:
        values.extend((*owner.center, *(x for axis in owner.axes for x in axis),
                       *owner.half_extents, *target.center,
                       *(x for axis in target.axes for x in axis),
                       *target.half_extents, *point, int(with_direction)))
    payload = ''.join(' '.join(format(value, '.17g') for value in values[i:i + 34]) + '\n'
                      for i in range(0, len(values), 34))
    process = subprocess.run([str(runner)], input=payload, capture_output=True,
                             text=True, check=True, timeout=30)
    rows = process.stdout.splitlines()
    if len(rows) != len(corpus):
        raise AssertionError('native reverse-geometry output count differs')
    maximum = 0.0
    for index, (line, (owner, target, point, with_direction)) in enumerate(zip(rows, corpus)):
        fields = line.split()
        if len(fields) != 10:
            raise AssertionError(f'case {index} has malformed output: {line}')
        result = (owner_point_direction_test(owner, target, point) if with_direction else
                  owner_point_contact_test(owner, target, point))
        if int(fields[0]) != int(result.inside):
            raise AssertionError(f'case {index} hit status differs')
        actual = tuple(float(x) for x in fields[1:])
        expected = result.target_local_point
        if result.inside:
            expected += result.owner_world_point
            expected += result.owner_direction or (0.0, 0.0, 0.0)
        else:
            expected += (0.0,) * 6
        for component, (a, b) in enumerate(zip(actual, expected)):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > max(2e-6, abs(b) * 2e-7):
                raise AssertionError(f'case {index} output {component}: {a} != {b}')
    return {'cases': len(corpus), 'maximum_absolute_error': maximum,
            'scope': 'native/Python bounded 0x45bb70 and 0x45be10 helpers'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    parser.add_argument('--cases', type=int, default=192)
    args = parser.parse_args()
    print(json.dumps(verify(args.runner, args.cases)))


if __name__ == '__main__':
    main()
