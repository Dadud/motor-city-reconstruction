"""Compare complete native drive records and ordered calls against Python.

Uses the same synthetic corpus as the separately verified original-function
comparison, plus component-mutation and signed-counter boundary scenarios.
"""
import argparse
from dataclasses import fields, replace
import json
import math
import subprocess
from client.drivetrain_stages import DriveCall
from tools.drivetrain_stages_oracle import cases, base, METHODS


def state_values(s):
    return [*(getattr(w,f.name) for w in s.wheels for f in fields(w)),
            *(getattr(s,f.name) for f in fields(s) if f.name!='wheels')]


def config_values(c):
    values=[]
    for f in fields(c):
        value=getattr(c,f.name)
        if isinstance(value,tuple):values.extend((len(value),*value))
        else:values.append(value)
    return values


def corpus():
    for stage,s,c,gate in cases():yield stage,s,c,gate,False
    s,c=base()
    for local in (False,True):
        for flags in (0,2,0x10,0x200):
            for setting in (0,3):
                yield 'distribute',replace(s,effective_torque=1000,clutch_gain=1,
                    vehicle_flags=flags,local_player=local,mode_setting=setting),c,True,True
    yield 'distribute',replace(s,hold_ticks=-0x80000000),c,True,False


def verify(runner):
    expected=[];lines=[];counts={}
    for stage,s,c,gate,mutation in corpus():
        tokens=(stage,gate,mutation,*state_values(s),*config_values(c))
        lines.append(' '.join(str(int(v)) if isinstance(v,(bool,int)) else format(v,'.17g')
                              if isinstance(v,float) else v for v in tokens))
        calls=[]
        def execute(call,current):
            calls.append(call)
            if mutation and call.stage=='damage':current.damage_one=.75
            return gate if call.stage=='vehicle_gate' else None
        method=METHODS[stage]
        result=method(s,c,execute) if stage in ('distribute','apply') else method(s,c)
        expected.append((state_values(result),calls))
        counts[stage]=counts.get(stage,0)+1
    process=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,
        capture_output=True,check=True,timeout=60)
    rows=process.stdout.splitlines()
    if len(rows)!=len(expected):raise AssertionError('native drivetrain row count')
    maximum=0.;events=0
    for index,(row,(values,calls)) in enumerate(zip(rows,expected)):
        tokens=iter(row.split())
        def compare(actual,target):
            nonlocal maximum
            if isinstance(target,(bool,int)):
                if int(actual)!=target:raise AssertionError((index,actual,target))
            else:
                error=abs(float(actual)-target)
                if not math.isfinite(float(actual)) or error>max(1e-7,abs(target)*4e-7):
                    raise AssertionError((index,actual,target,error))
                maximum=max(maximum,error)
        for value in values:compare(next(tokens),value)
        if int(next(tokens))!=len(calls):raise AssertionError((index,'drive call count'))
        for call in calls:
            identity=(next(tokens),int(next(tokens)),int(next(tokens)))
            if identity!=(call.stage,call.code if call.code is not None else -1,len(call.values)):
                raise AssertionError((index,'drive call identity',identity,call))
            for value in call.values:compare(next(tokens),value)
            events+=1
        if next(tokens,None) is not None:raise AssertionError('unexpected native output fields')
    return dict(cases=counts,ordered_calls=events,maximum_absolute_error=maximum,
        scope='native/Python complete drive state and ordered effects; synthetic original-function corpus plus mutation/counter boundaries')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
