"""Native/Python differential corpus for the recovered collision helper."""
import argparse
import json
import subprocess
from client.collision_response import tangential_response
from client.tire_response import f32
from tools.collision_response_oracle import cases


def verify(runner):
    corpus=list(cases())
    payload=''.join(' '.join(format(x,'.17g') for x in (*v,*n,t,s))+'\n' for v,n,t,s in corpus)
    p=subprocess.run([str(runner)],input=payload,capture_output=True,text=True,check=True,timeout=30)
    output=p.stdout.splitlines()
    if len(output)!=len(corpus): raise AssertionError('collision output count differs')
    maximum=0.0
    for line,(v,n,t,s) in zip(output,corpus):
        parts=line.split(); expected=tangential_response(v,n,t,s)
        if len(parts)!=4 or int(parts[0])!=expected.status: raise AssertionError((line,expected))
        actual=tuple(f32(float(x)) for x in parts[1:])
        maximum=max(maximum,*[abs(a-b) for a,b in zip(actual,expected.vector)])
        if actual!=expected.vector: raise AssertionError((actual,expected))
    return {'cases':len(corpus),'maximum_absolute_error':maximum,'scope':'native/Python complete collision response helper'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
