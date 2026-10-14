"""Native/Python steering-shaping comparison using original-function cases."""
import argparse
import json
import math
import subprocess
from client.steering_response import steering_response
from client.tire_response import f32
from tools.steering_response_oracle import cases


def verify(runner):
    corpus = list(cases())
    payload = ''.join(f'{raw} {speed:.17g}\n' for raw, speed in corpus)
    p = subprocess.run([str(runner)], input=payload, capture_output=True, text=True,
                       check=True, timeout=30)
    output = p.stdout.splitlines()
    if len(output) != len(corpus): raise AssertionError('steering output count differs')
    maximum = 0.0
    for index, (line, (raw, speed)) in enumerate(zip(output, corpus)):
        actual, expected = f32(float(line)), steering_response(raw, speed)
        error = abs(actual-expected)
        if not math.isfinite(actual) or error > 1e-7:
            raise AssertionError((index, actual, expected, error))
        maximum = max(maximum, error)
    return {'cases':len(corpus),'maximum_absolute_error':maximum,
            'scope':'native/Python signed steering response corpus'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
