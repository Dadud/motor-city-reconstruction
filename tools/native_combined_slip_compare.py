"""Native/Python combined-slip force and component-effect comparison."""
import argparse
from dataclasses import astuple
import json
import math
import subprocess
from client.combined_slip import limit_combined_slip
from tools.combined_slip_oracle import cases


def verify(runner):
    corpus=list(cases());lines=[]
    for s in corpus:
        values=list(astuple(s)[1:])
        for w in s.wheels:values.extend(astuple(w))
        lines.append(' '.join(format(v,'.17g') for v in values))
    p=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=p.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('combined-slip output count differs')
    maximum=0.0
    for index,(line,s) in enumerate(zip(output,corpus)):
        out,effects=limit_combined_slip(s);expected=[]
        for w in out.wheels:expected.extend((w.lateral_force,w.longitudinal_force,w.secondary_response))
        expected.append(len(effects))
        for e in effects:expected.extend(astuple(e))
        actual=list(map(float,line.split()))
        if len(actual)!=len(expected):raise AssertionError('combined-slip output shape differs')
        for a,b in zip(actual,expected):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.0005,abs(b)*3e-7):raise AssertionError((index,a,b,error))
            maximum=max(maximum,error)
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python complete combined-slip and effects'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
