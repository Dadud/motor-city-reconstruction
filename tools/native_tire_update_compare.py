"""Native/Python full tire-update comparison using original-function cases."""
import argparse
import json
import math
import subprocess
from client.tire_update import update_tires
from client.tire_response import f32
from tools.tire_update_oracle import cases


def verify(runner):
    corpus = list(cases()); lines = []
    for s in corpus:
        modes = sum(int(flag) << i for i, flag in enumerate(s.mode_observations))
        values = [s.raw_control,s.speed,s.mass_parameter,s.front_lever,s.rear_lever,s.front_track,
                  s.wheelbase,s.maximum_steering,s.longitudinal_velocity,s.lateral_velocity,
                  s.lateral_acceleration,s.yaw_rate,s.body_slip,int(s.rear_steering),modes,int(s.alternate_load)]
        for c in (s.front_curves,s.rear_curves): values.extend((*c.primary,*c.secondary,c.angle_coefficient))
        for w in s.wheels:
            values.extend((w.steering_angle,w.slip_angle,w.secondary_angle,w.projected_speed,w.normal_load,
                           int(w.contact),w.surface_multiplier,w.lateral_force,w.longitudinal_force,w.secondary_response))
        lines.append(' '.join(format(v,'.17g') for v in values))
    p = subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,
                       text=True,check=True,timeout=30)
    output=p.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('tire-update output count differs')
    maximum=0.0
    for index,(line,state) in enumerate(zip(output,corpus)):
        result=update_tires(state)
        expected=[result.lateral_velocity,result.lateral_acceleration,result.yaw_rate]
        for w in result.wheels:
            expected.extend((w.steering_angle,w.slip_angle,w.secondary_angle,w.projected_speed,w.normal_load,
                             int(w.contact),w.surface_multiplier,w.lateral_force,w.longitudinal_force,w.secondary_response))
        actual=[f32(float(v)) for v in line.split()]
        if len(actual)!=len(expected):raise AssertionError('tire-update output shape differs')
        for field,(value,target) in enumerate(zip(actual,expected)):
            error=abs(value-target)
            if not math.isfinite(value) or error>max(0.00025,abs(target)*3e-7):
                raise AssertionError((index,field,value,target,error))
            maximum=max(maximum,error)
    return {'cases':len(corpus),'maximum_absolute_error':maximum,
            'scope':'native/Python synthetic full tire-update observations'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
