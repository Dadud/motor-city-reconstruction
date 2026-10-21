"""Compare native and Python vector-array translation helpers."""
import argparse
import json
import subprocess

from client.geometry_transform import add_vector_to_points
from tools.collision_pair_geometry_oracle import f32
from tools.vector_array_oracle import cases


def compare(runner, count=128):
    corpus = list(cases(count))
    payload = ''.join(' '.join(format(value, '.17g') for value in
                               (size, *points, *vector)) + '\n'
                      for points, vector, size, _ in corpus)
    result = subprocess.run([str(runner)], input=payload, capture_output=True,
                            text=True, check=True, timeout=30)
    rows = result.stdout.splitlines()
    if len(rows) != len(corpus):
        raise AssertionError('native output count differs from the corpus')
    maximum = 0.0
    for index, (line, (points, vector, size, _)) in enumerate(zip(rows, corpus)):
        actual = tuple(f32(float(value)) for value in line.split())
        expected = add_vector_to_points(points, vector, count=size)
        if len(actual) != len(expected):
            raise AssertionError(f'case {index} output length differs')
        for a, b in zip(actual, expected):
            error = abs(a - b)
            maximum = max(maximum, error)
            if error != 0:
                raise AssertionError(f'case {index} float output differs: {a} != {b}')
    return {'cases': len(corpus), 'maximum_absolute_error': maximum,
            'scope': 'native/Python 0x6f1450 vector-array translation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.runner, args.cases)))


if __name__ == '__main__':
    main()
