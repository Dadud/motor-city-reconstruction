"""Native/Python suspension-load comparison using original-function cases."""
import argparse
import json
import math
import subprocess
from client.suspension_load_correction import correct_suspension_load
from client.tire_response import f32
from tools.suspension_load_oracle import cases


def verify(runner):
    corpus = list(cases()); lines = []
    for s in corpus:
        mask = sum(int(flag) << i for i, flag in enumerate(s.support))
        values = (*s.loads, mask, s.attitude, int(s.enabled), s.speed, s.bank_angle, s.pitch_angle,
                  s.mass, s.mass_offset, s.front_weight_parameter, s.rear_weight_parameter,
                  s.front_lever, s.rear_lever, s.wheelbase, s.rear_track, s.gear_factor,
                  s.torque, s.component_mode, int(s.disable_torque))
        lines.append(' '.join(format(v, '.17g') for v in values))
    p = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                       text=True, check=True, timeout=30)
    outputs = p.stdout.splitlines()
    if len(outputs) != len(corpus): raise AssertionError('suspension-load count differs')
    maximum = 0.0
    for index, (line, state) in enumerate(zip(outputs, corpus)):
        actual = tuple(f32(float(v)) for v in line.split())
        if len(actual) != 4: raise AssertionError('suspension-load shape differs')
        for value, target in zip(actual, correct_suspension_load(state)):
            error = abs(value-target)
            if not math.isfinite(value) or error > max(0.00025, abs(target)*3e-7):
                raise AssertionError((index,value,target,error))
            maximum = max(maximum,error)
    return {'cases':len(corpus),'maximum_absolute_error':maximum,
            'scope':'native/Python synthetic attitude and torque load correction'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
