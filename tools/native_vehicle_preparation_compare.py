"""Native/Python preparation and surface-support comparison."""
import argparse
from dataclasses import astuple
import json
import math
import subprocess
from client.vehicle_preparation import prepare_vehicle,update_support_disturbance
from tools.vehicle_preparation_oracle import preparation_cases,support_cases

def flatten(values):
    for value in values:
        if isinstance(value,tuple):yield from flatten(value)
        else:yield value

def verify(runner):
    prep=list(preparation_cases());support=list(support_cases());corpus=[(0,s) for s in prep]+[(1,s) for s in support]
    lines=[' '.join(format(x,'.17g') for x in (mode,*flatten(astuple(s)))) for mode,s in corpus]
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('preparation output count differs')
    maximum=0
    for index,(line,(mode,s)) in enumerate(zip(output,corpus)):
        if mode==0:
            out=prepare_vehicle(s)
            expected=(out.damping,out.pitch_target,out.roll_target,out.pitch,out.roll,out.extent,*out.angle_delta,*out.auxiliary,*out.to_world,*out.to_local)
        else:
            out=update_support_disturbance(s);expected=tuple(x for w in out.wheels for x in (w.displacement,w.correction))
        actual=list(map(float,line.split()))
        if len(actual)!=len(expected):raise AssertionError('preparation output shape differs')
        for a,b in zip(actual,expected):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(3e-6,abs(b)*4e-7):raise AssertionError((index,a,b,error))
            maximum=max(maximum,error)
    return {'preparation_cases':len(prep),'support_cases':len(support),'maximum_absolute_error':maximum}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
