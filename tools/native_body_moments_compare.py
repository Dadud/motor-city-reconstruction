"""Native comparison for original-verified moment and orientation corpora."""
import argparse
import json
import math
import subprocess
from client.body_moments import accumulate_body_moments
from client.wheel_force_orientation import orient_wheel_forces
from tools.body_moments_oracle import cases as moment_cases
from tools.wheel_force_orientation_oracle import cases as orientation_cases


def verify(runner,kind='moments'):
    lines,expected=[],[]
    for s in moment_cases() if kind=='moments' else orientation_cases():
        if kind=='moments':
            values=[s.speed,s.front_lever,s.rear_lever,s.front_track,s.rear_track,s.height_parameter,
                s.mass_parameter,s.inverse_pitch,s.inverse_yaw,s.inverse_roll,s.pitch_multiplier,
                s.front_vertical,s.rear_vertical,s.yaw_contribution,int(s.alternate_mode)]
            for w in s.wheels:
                values.extend((w.lateral_force,w.longitudinal_force,w.secondary_response,w.support_correction,int(w.contact)))
            expected.append(accumulate_body_moments(s))
        else:
            wheels,front,rear=s
            values=[front,rear]
            for w in wheels: values.extend((w.steering_angle,w.phase_angle,w.lateral_force,w.longitudinal_force))
            expected.append(tuple(v for w in orient_wheel_forces(wheels,front,rear) for v in (w.lateral_force,w.longitudinal_force)))
        lines.append(' '.join(format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(expected): raise AssertionError('output count differs')
    maximum=0.0
    for index,(line,target) in enumerate(zip(output,expected)):
        actual=tuple(map(float,line.split()))
        if len(actual)!=len(target): raise AssertionError('output shape differs')
        for a,b in zip(actual,target):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.00025,abs(b)*3e-7): raise AssertionError((index,a,b,error))
            maximum=max(maximum,error)
    return {'cases':len(expected),'maximum_absolute_error':maximum,'scope':'native/Python '+kind}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');p.add_argument('--kind',choices=('moments','orientation'),default='moments')
    args=p.parse_args(); print(json.dumps(verify(args.runner,args.kind)))
