"""Native/Python normal-load comparison using the original-function corpus."""
import argparse
import json
import math
import subprocess
from client.normal_load import normal_load
from client.tire_response import f32
from tools.normal_load_oracle import cases


def verify(runner):
    corpus = list(cases())
    lines = []
    for s in corpus:
        mask = sum(int(flag) << i for i, flag in enumerate(s.support))
        values = (mask, s.pitch, s.bank, s.mass, s.wheelbase, s.front_track, s.rear_track,
                  s.height_parameter, s.front_lever, s.rear_lever, s.speed, s.curvature_scale,
                  s.vertical_correction, *s.wheel_scales)
        lines.append(' '.join(format(v, '.17g') for v in values))
    p = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                       text=True, check=True, timeout=30)
    outputs = p.stdout.splitlines()
    if len(outputs) != len(corpus): raise AssertionError('normal-load output count differs')
    maximum = 0.0
    for index, (line, state) in enumerate(zip(outputs, corpus)):
        actual = tuple(f32(float(v)) for v in line.split())
        if len(actual) != 4: raise AssertionError('normal-load output shape differs')
        for value, target in zip(actual, normal_load(state)):
            error = abs(value-target)
            if not math.isfinite(value) or error > max(0.00025, abs(target)*3e-7):
                raise AssertionError((index, value, target, error))
            maximum = max(maximum, error)
    return {'cases': len(corpus), 'maximum_absolute_error': maximum,
            'scope': 'native/Python synthetic support-mask normal loads'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
