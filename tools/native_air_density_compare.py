"""Native/Python comparison of the complete original-verified density corpus."""
import argparse
import json
import subprocess
from client.air_density import calculate_air_density
from tools.air_density_oracle import cases


def verify(runner):
    corpus=list(cases())
    lines=[' '.join(format(int(v) if isinstance(v,bool) else v,'.17g') for v in s) for s in corpus]
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=30)
    output=result.stdout.splitlines()
    if len(output)!=len(corpus): raise AssertionError('output count differs')
    for index,(line,state) in enumerate(zip(output,corpus)):
        actual=float(line);expected=calculate_air_density(*state)
        if actual!=expected: raise AssertionError((index,actual,expected))
    return {'cases':len(corpus),'maximum_absolute_error':0,'scope':'native/Python air density'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
