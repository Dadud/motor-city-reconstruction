"""Native/Python body resistance comparison with explicit supplied producers."""
import argparse
import json
import itertools
import math
import subprocess
from dataclasses import fields
from client.body_resistance import calculate_body_resistance
from tools.body_resistance_oracle import cases,connected_cases


def verify(runner):
    lines,expected=[],[]
    for s in itertools.chain(cases(),(item[0] for item in connected_cases())):
        values=[getattr(s,field.name) for field in fields(s) if field.name not in ('wheel_loads','contacts')]
        values.extend(s.wheel_loads);values.extend(s.contacts)
        values=[int(v) if isinstance(v,bool) else v for v in values]
        lines.append(' '.join(format(v,'.17g') for v in values))
        out=calculate_body_resistance(s)
        expected.append((out.longitudinal_drag,out.yaw_contribution,out.pitch_contribution,*out.wheel_loads))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(expected): raise AssertionError('output count differs')
    maximum=0.0
    for index,(line,target) in enumerate(zip(output,expected)):
        actual=tuple(map(float,line.split()))
        if len(actual)!=len(target): raise AssertionError('output shape differs')
        for a,b in zip(actual,target):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.0005,abs(b)*3e-7): raise AssertionError((index,a,b,error))
            maximum=max(maximum,error)
    return {'cases':len(expected),'maximum_absolute_error':maximum,'scope':'native/Python resistance numeric stage'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
