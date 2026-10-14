"""Compare native wheel correction with the original-verified Python matrix."""
import argparse
import json
import subprocess

from client.tire_response import f32
from client.wheel_force_correction import correct_wheel_forces
from tools.wheel_force_correction_oracle import cases


def verify(runner):
    lines,expected=[],[]
    for wheels,service,other,parking,direction,override in cases():
        values=[service,other,int(parking),direction,int(override)]
        for w in wheels:
            values.extend((w.projected_speed,w.spin_value,w.spin_adjustment,w.spin_scale,
                w.lateral_force,w.longitudinal_force,w.normal_load,w.primary_coefficient,
                w.secondary_coefficient,int(w.contact),int(w.correction_enabled)))
        lines.append(' '.join(format(v,'.17g') for v in values))
        result=correct_wheel_forces(wheels,service,other,parking,direction,override)
        expected.append(tuple(v for w in result for v in (w.spin_value,w.spin_adjustment)))
    p=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,
        capture_output=True,check=True,timeout=30)
    output=p.stdout.splitlines()
    if len(output)!=len(expected):raise AssertionError('native output count mismatch')
    maximum=0
    for i,(line,target) in enumerate(zip(output,expected)):
        actual=tuple(f32(float(v)) for v in line.split())
        if len(actual)!=8:raise AssertionError('native output shape mismatch')
        for a,b in zip(actual,target):
            error=abs(a-b)
            if error>max(.00005,abs(b)*3e-7):raise AssertionError((i,a,b))
            maximum=max(maximum,error)
    return {'cases':len(expected),'maximum_absolute_error':maximum}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
