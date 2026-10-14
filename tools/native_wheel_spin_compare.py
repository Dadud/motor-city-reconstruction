"""Native/Python wheel integration and ordered component-event comparison."""
import argparse
from dataclasses import astuple
import json
import math
import subprocess
from client.wheel_spin import integrate_wheel_spin
from tools.wheel_spin_oracle import cases


def verify(runner):
    corpus=list(cases());lines=[]
    for s in corpus:
        values=list(astuple(s)[1:])
        for w in s.wheels:values.extend(astuple(w))
        lines.append(' '.join(format(v,'.17g') for v in values))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('spin output count differs')
    maximum=0.0
    for index,(line,s) in enumerate(zip(output,corpus)):
        out=integrate_wheel_spin(s);expected=[]
        for w in out.state.wheels:expected.extend((w.spin_value,w.spin_scale,w.phase,w.secondary_angle,
            w.slip_ratio,w.kinetic_value,w.local_lateral,w.local_vertical,w.local_longitudinal))
        expected.append(len(out.wear_events))
        for slot,amount in out.wear_events:expected.extend((slot,amount))
        actual=list(map(float,line.split()))
        if len(actual)!=len(expected):raise AssertionError('spin output shape differs')
        for a,b in zip(actual,expected):
            error=abs(a-b)
            if not math.isfinite(a) or error>max(.00025,abs(b)*3e-7):raise AssertionError((index,a,b,error))
            maximum=max(maximum,error)
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python complete wheel integration and events'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
