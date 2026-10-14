"""Native/Python scheduler comparison using the original-backed batch corpus."""
import argparse
import itertools
import json
from pathlib import Path
import subprocess

from client.scheduler import execute_batch, selected_iterations, pending_iterations


def compare(executable):
    batches = list(itertools.product((0, 1, 2, 0xfffffffe, 0xffffffff),
        (-(1 << 31), -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, (1 << 31)-1),
        (0, 1), (-1, 0, 1, 2, 3, 4), (0, 1)))
    cases = [(*case, 0, 0) for case in batches]
    for clock, processed in itertools.product((0, 1, 15, 16, 17, 50, 0x7fffffff, 0x80000000, 0xffffffff), repeat=2):
        cases.append((0, 0, 0, 0, 0, clock, processed))
    data = '\n'.join(' '.join(map(str, case)) for case in cases) + '\n'
    result = subprocess.run([str(Path(executable).resolve())], input=data, text=True,
                            capture_output=True, check=True)
    rows = result.stdout.splitlines()
    if len(rows) != len(cases): raise AssertionError('native scheduler row count')
    for case, row in zip(cases, rows):
        counter, frame, enabled, mode, inhibited, clock, processed = case
        repetitions = selected_iterations(bool(enabled), mode, frame)
        calls = []
        output = execute_batch(counter, repetitions, bool(inhibited), lambda: calls.append(1),
                               lambda: calls.append(2), lambda: calls.append(3))
        expected = [output, repetitions, len(calls), *calls, pending_iterations(clock, processed)]
        if list(map(int, row.split())) != expected: raise AssertionError((case, expected, row))
    return {'cases': len(cases), 'native_matches_python': True}


def verify(executable):
    return compare(executable)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    print(json.dumps(compare(parser.parse_args().executable)))
