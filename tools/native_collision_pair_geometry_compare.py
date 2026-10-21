"""Differential-check the native oriented-box point test against Python."""
import argparse
import json
import subprocess

from client.collision_pair_geometry import oriented_box_point_test
from tools.collision_pair_geometry_oracle import cases


def verify(runner, case_count=192):
    corpus = list(cases(case_count))
    values = []
    for owner, target, point in corpus:
        values.extend((*owner.center, *(x for axis in owner.axes for x in axis),
                       *owner.half_extents, *target.center,
                       *(x for axis in target.axes for x in axis),
                       *target.half_extents, *point))
    payload = ''.join(' '.join(format(value, '.17g') for value in values[i:i + 33]) + '\n'
                      for i in range(0, len(values), 33))
    process = subprocess.run([str(runner)], input=payload, capture_output=True,
                             text=True, check=True, timeout=30)
    rows = process.stdout.splitlines()
    if len(rows) != len(corpus):
        raise AssertionError('native collision geometry output count differs')
    maximum = 0.0
    hits = 0
    for index, (line, (owner, target, point)) in enumerate(zip(rows, corpus)):
        fields = line.split()
        if len(fields) != 10:
            raise AssertionError(f'case {index} returned malformed native output: {line}')
        expected = oriented_box_point_test(owner, target, point)
        if int(fields[0]) != int(expected.inside):
            raise AssertionError(f'case {index} hit status mismatch')
        actual = tuple(float(value) for value in fields[1:])
        want = expected.owner_local_point
        if expected.inside:
            want += expected.target_world_point + expected.target_direction
            hits += 1
        else:
            want += (0.0,) * 6
        for component, (a, b) in enumerate(zip(actual, want)):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > max(2e-6, abs(b) * 2e-7):
                raise AssertionError(f'case {index} output {component}: {a} != {b}')
    return {'cases': len(corpus), 'hits': hits,
            'maximum_absolute_error': maximum,
            'scope': 'native/Python complete bounded 0x45b8e0 helper'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    parser.add_argument('--cases', type=int, default=192)
    args = parser.parse_args()
    print(json.dumps(verify(args.runner, args.cases)))


if __name__ == '__main__':
    main()
