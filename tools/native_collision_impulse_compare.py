"""Native/Python differential corpus for complete collision impulse/height helpers."""
import argparse
import json
import subprocess
from client.collision_impulse import impulse_motion, plane_height
from client.tire_response import f32
from tools.collision_impulse_oracle import impulse_cases, height_cases


def verify(runner):
    corpus=list(impulse_cases());heights=list(height_cases());expected=[];lines=[]
    for body,p,l,r in corpus:
        lines.append('I '+' '.join(format(v,'.17g') for v in (body.inverse_mass,*body.inverse_inertia,*body.world_to_body,*body.body_to_world,*p,*l,*r)))
        result=impulse_motion(body,p,l,r);expected.append((*result.linear,*result.angular))
    for n,p,q in heights:
        lines.append('H '+' '.join(format(v,'.17g') for v in (*n,*p,*q)));expected.append((plane_height(n,p,q),))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(expected):raise AssertionError('collision impulse output count differs')
    for actual,want in zip(output,expected):
        values=tuple(f32(float(v)) for v in actual.split())
        if values!=want:raise AssertionError((values,want))
    return {'impulse_cases':len(corpus),'plane_height_cases':len(heights),'maximum_absolute_error':0.0}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
