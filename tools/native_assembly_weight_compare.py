"""Native/Python weight distribution on the original-function corpus."""
import argparse
import json
import subprocess
from client.assembly_weight import assembled_front_weight_fraction
from client.tire_response import f32
from tools.assembly_weight_oracle import cases


def verify(runner):
    lines=[];expected=[]
    for args in cases():
        body,fraction,length,shared,front,rear=args
        lines.append(' '.join(format(v,'.17g') for v in (body,fraction,length,shared,*front,*rear)))
        result=assembled_front_weight_fraction(*args)
        expected.append([result,f32(result)])
    output=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,
        text=True,check=True,timeout=30).stdout.splitlines()
    if len(output)!=len(expected):raise AssertionError('native weight row count')
    for index,(line,wanted) in enumerate(zip(output,expected)):
        actual=list(map(float,line.split()))
        if actual!=wanted:raise AssertionError((index,actual,wanted))
    return dict(cases=len(output),maximum_absolute_error=0,
        scope='native/Python helper return and caller float store; supplied mechanical mass slots')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
