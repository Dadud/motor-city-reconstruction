"""Native/Python comparison using the original-verified vertical-load corpus."""
import argparse
import json
import math
import subprocess
from dataclasses import fields
from client.body_vertical_load import adjust_body_vertical_load
from tools.body_vertical_load_oracle import cases


def verify(runner):
    lines,expected=[],[]
    for s in cases():
        values=[getattr(s,field.name) for field in fields(s) if field.name!='wheel_loads']
        values.extend(s.wheel_loads)
        lines.append(' '.join(format(v,'.17g') for v in values))
        out=adjust_body_vertical_load(s)
        expected.append((out.front_vertical,out.rear_vertical,out.total_vertical,*out.wheel_loads))
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
    return {'cases':len(expected),'maximum_absolute_error':maximum,'scope':'native/Python vertical load'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
