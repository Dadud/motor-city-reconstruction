"""Native/Python drivetrain-coupling comparison using original-tail cases."""
import argparse
from dataclasses import astuple
import json
import subprocess
from client.drivetrain_coupling import couple_drivetrain
from client.tire_response import f32
from tools.drivetrain_coupling_oracle import scenarios


def verify(runner):
    corpus=list(scenarios())
    payload=''.join(' '.join(f'{int(v) if isinstance(v,bool) else v:.17g}' for v in astuple(s))+'\n' for s in corpus)
    result=subprocess.run([str(runner)],input=payload,text=True,capture_output=True,check=True,timeout=30)
    lines=result.stdout.splitlines()
    if len(lines)!=len(corpus): raise AssertionError('coupling output count differs')
    maximum=0.
    for line,state in zip(lines,corpus):
        values=line.split()
        if len(values)!=5: raise AssertionError('coupling field count differs')
        for raw,expected in zip(values,astuple(couple_drivetrain(state))):
            error=abs(f32(float(raw))-expected); maximum=max(maximum,error)
            if error>1e-5: raise AssertionError((line,state,expected))
    return {'cases':len(corpus),'maximum_absolute_error':maximum}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
