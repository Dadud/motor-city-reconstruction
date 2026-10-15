"""Complete native/Python comparison of the recovered body startup phase."""
import argparse
import json
import struct
import subprocess
from client.body_startup import prepare_startup_body
from tools.body_startup_oracle import startup_cases


def verify(runner):
    lines=[];expected=[]
    for owner,config,extents,identity in startup_cases():
        numbers=(identity,*struct.unpack('<3I',struct.pack('<3f',*extents)),
                 *struct.unpack('<2048I',owner),*struct.unpack('<520I',config))
        lines.append(' '.join(map(str,numbers)))
        expected.append(struct.unpack('<2048I',prepare_startup_body(owner,config,extents,identity,assembly_finalized=True)))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=60)
    observed=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if len(observed)!=len(expected):raise AssertionError('startup record count')
    for i,(actual,wanted) in enumerate(zip(observed,expected)):
        if actual!=wanted:raise AssertionError((i,[(hex(k*4),a,b) for k,(a,b) in enumerate(zip(actual,wanted)) if a!=b][:10]))
    return dict(cases=len(lines),maximum_absolute_error=0,scope='native/Python connected body startup; all 0x2000 owner bytes exact')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
