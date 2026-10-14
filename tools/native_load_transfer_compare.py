"""Compare native load transfer with the complete original-function corpus."""
import argparse
import json
import math
import subprocess

from client.load_transfer import transfer_load
from client.tire_response import f32
from tools.load_transfer_oracle import cases


def verify(runner):
    corpus = list(cases())
    lines = []
    for s in corpus:
        values = (*s.loads, s.attitude, s.longitudinal_acceleration, s.lateral_acceleration,
                  s.speed, s.mass, s.wheelbase, s.front_track, s.rear_track,
                  s.height_parameter, s.front_offset, s.rear_offset)
        lines.append(' '.join(format(value, '.17g') for value in values))
    process = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                             text=True, check=True, timeout=30)
    outputs = process.stdout.splitlines()
    if len(outputs) != len(corpus):
        raise AssertionError('native load-transfer output count differs')
    maximum_error = 0.0
    for index, (line, state) in enumerate(zip(outputs, corpus)):
        actual = tuple(f32(float(field)) for field in line.split())
        expected = transfer_load(state)
        if len(actual) != 4:
            raise AssertionError('native load-transfer shape differs')
        for value, target in zip(actual, expected):
            error = abs(value-target)
            if not math.isfinite(value) or error > max(0.00025, abs(target)*3e-7):
                raise AssertionError((index, value, target, error))
            maximum_error = max(maximum_error, error)
    return {'cases': len(corpus), 'maximum_absolute_error': maximum_error,
            'scope': 'native/Python load-transfer corpus; synthetic isolated component state'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
