"""Compare native and Python translations of the 0x45af30 pair resolver."""
import argparse
import json
import subprocess

from tools.collision_pair_solver_oracle import cases
from client.collision_pair_solver import resolve_collision_pair


def body_values(body):
    box = body.box
    return (*box.center, *(value for axis in box.axes for value in axis),
            *box.half_extents, body.mass, body.mode, body.gate, body.peer_gate,
            *body.local_vertices)


def verify(runner, case_count=128):
    corpus = list(cases(case_count))
    payload = ''.join(' '.join(format(value, '.17g') for value in
                               (*body_values(owner), *body_values(target))) + '\n'
                      for owner, target in corpus)
    process = subprocess.run([str(runner)], input=payload, capture_output=True,
                             text=True, check=True, timeout=30)
    rows = process.stdout.splitlines()
    if len(rows) != len(corpus):
        raise AssertionError('native pair-solver output count differs')
    maximum = 0.0
    total_steps = 0
    for index, (line, (owner, target)) in enumerate(zip(rows, corpus)):
        fields = line.split()
        if len(fields) != 140:
            raise AssertionError(f'case {index} has malformed output: {line}')
        result = resolve_collision_pair(owner, target)
        hit, steps = map(int, fields[:2])
        if hit != int(result.collided) or steps != result.correction_steps:
            raise AssertionError(f'case {index} hit/step mismatch')
        actual = tuple(float(value) for value in fields[2:8])
        expected = result.owner.box.center + result.target.box.center
        for component, (a, b) in enumerate(zip(actual, expected)):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > max(2e-6, abs(b) * 2e-7):
                raise AssertionError(f'case {index} position[{component}] differs: {a} != {b}')
        actual_vertices = tuple(float(value) for value in fields[8:])
        expected_vertices = ((result.owner.world_vertices or (0.0,) * 66) +
                             (result.target.world_vertices or (0.0,) * 66))
        for component, (a, b) in enumerate(zip(actual_vertices, expected_vertices)):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error > max(2e-6, abs(b) * 2e-7):
                raise AssertionError(f'case {index} world vertex[{component}] differs: {a} != {b}')
        total_steps += steps
    return {'cases': len(corpus), 'total_correction_steps': total_steps,
            'maximum_absolute_float_error': maximum,
            'scope': 'native/Python 0x45af30 pair solver translation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(verify(args.runner, args.cases)))


if __name__ == '__main__':
    main()
