"""Native/Python complete driving RPM helper differential corpus."""
import argparse
from dataclasses import astuple
import json
import subprocess
from client.driving_engine_rpm import update_driving_engine_rpm
from client.tire_response import f32
from tools.driving_engine_rpm_oracle import scenarios


def verify(runner):
    corpus = list(scenarios())
    payload = ''.join(' '.join(f'{int(v) if isinstance(v, bool) else v:.17g}'
                        for v in (*astuple(s), minimum))+'\n' for s, minimum in corpus)
    result = subprocess.run([str(runner)], input=payload, text=True, capture_output=True,
                            check=True, timeout=30)
    lines = result.stdout.splitlines()
    if len(lines) != len(corpus):
        raise AssertionError('native RPM output count differs')
    maximum = 0.
    for line, (state, minimum) in zip(lines, corpus):
        target, rpm, omega, acceleration = line.split()
        expected = update_driving_engine_rpm(state, minimum)
        if int(target) != expected.target_rpm or int(rpm) != expected.rpm:
            raise AssertionError((line, expected))
        for value, wanted in ((omega, expected.angular_speed), (acceleration, expected.acceleration_output)):
            error = abs(f32(float(value))-wanted)
            maximum = max(maximum, error)
            if error > 1e-5: raise AssertionError((line, expected))
    return {'cases': len(corpus), 'maximum_absolute_error': maximum}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
