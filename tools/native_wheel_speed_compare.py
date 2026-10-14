"""Native wheel-speed projection compared with the original-function corpus."""
import argparse
import json
import math
import subprocess
from client.wheel_speed import project_wheel_speeds
from client.tire_response import f32
from tools.wheel_speed_oracle import cases


def verify(runner):
    corpus = list(cases())
    lines = []
    for s in corpus:
        values = [s.lateral_velocity, s.longitudinal_velocity, s.yaw_rate_turns,
                  s.front_offset, s.rear_offset, s.front_track, s.rear_track]
        for w in s.wheels: values.extend((w.angle, int(w.contact), w.spin_value, w.spin_scale))
        lines.append(' '.join(format(v, '.17g') for v in values))
    p = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                       text=True, check=True, timeout=30)
    outputs = p.stdout.splitlines()
    if len(outputs) != len(corpus): raise AssertionError('wheel-speed output count differs')
    maximum = 0.0
    for index, (line, state) in enumerate(zip(outputs, corpus)):
        actual = tuple(f32(float(v)) for v in line.split())
        if len(actual) != 4: raise AssertionError('wheel-speed output shape differs')
        for value, target in zip(actual, project_wheel_speeds(state)):
            error = abs(value-target)
            if not math.isfinite(value) or error > max(0.00025, abs(target)*3e-7):
                raise AssertionError((index, value, target, error))
            maximum = max(maximum, error)
    return {'cases': len(corpus), 'maximum_absolute_error': maximum,
            'scope': 'native/Python synthetic wheel speed projections'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
