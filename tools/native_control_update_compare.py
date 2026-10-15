"""Native/Python controls and ordered child-call comparison."""
import argparse
from dataclasses import astuple
import json
import subprocess
from client.control_update import update_controls
from tools.control_update_oracle import cases,Executor
STAGES=('remote_controls','assisted_gears','manual_gears','stopped_query','override_query','vehicle_gate','trace_controls')
def verify(runner):
    corpus=list(cases())
    lines=[' '.join(format(x,'.17g') for x in (*astuple(s),*observations)) for s,observations in corpus]
    output=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30).stdout.splitlines()
    if len(output)!=len(corpus):raise AssertionError('control output count differs')
    for index,(line,(s,observations)) in enumerate(zip(output,corpus)):
        out=update_controls(s,Executor(observations));expected=[*astuple(out.state),len(out.calls)]
        for c in out.calls:expected.extend((STAGES.index(c.stage),len(c.values),*c.values))
        actual=list(map(float,line.split()))
        if actual!=expected:raise AssertionError((index,actual,expected))
    return {'cases':len(corpus),'maximum_absolute_error':0,'scope':'complete typed controls and exact ordered supplied child calls'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
