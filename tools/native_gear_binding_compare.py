"""Native/Python complete gear binding outputs on the original oracle corpus."""
import argparse
from dataclasses import astuple
import json
import subprocess
from client.gear_binding import bind_gear_tables
from tools.gear_binding_oracle import cases


def verify(runner):
    lines=[];expected=[]
    for args in cases():
        rpm,w,a,r,ratios,losses,final=args
        lines.append(' '.join(format(v,'.17g') for v in (rpm,w,a,r,final,len(ratios),*ratios,*losses)))
        expected.append([v for item in astuple(bind_gear_tables(*args))
                         for v in (item if isinstance(item,tuple) else (item,))])
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,
        text=True,check=True,timeout=30)
    rows=result.stdout.splitlines()
    if len(rows)!=len(expected):raise AssertionError('native gear row count')
    for i,(row,wanted) in enumerate(zip(rows,expected)):
        actual=list(map(float,row.split()))
        if actual!=wanted:raise AssertionError((i,actual,wanted))
    return dict(cases=len(rows),maximum_absolute_error=0,
        scope='native/Python five complete gear tables and final-drive inertia; original-function synthetic corpus')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
