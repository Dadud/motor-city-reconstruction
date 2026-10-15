"""Native/Python whole wheel startup images from authored original-test cases."""
import argparse
import json
import subprocess
from client.owner_wheel_setup import initialize_owner_wheels,adjust_owner_stance
from tools.owner_wheel_setup_oracle import cases


def verify(runner):
    records=list(cases())
    result=subprocess.run([str(runner)],input=''.join(f'{o.hex()} {c.hex()}\n' for o,c in records),
        capture_output=True,text=True,check=True,timeout=30)
    rows=result.stdout.splitlines()
    if len(rows)!=len(records):raise AssertionError('startup comparison row count')
    for index,((owner,config),actual) in enumerate(zip(records,rows)):
        expected=initialize_owner_wheels(owner,config,assembly_finalized=True).hex()+' '+adjust_owner_stance(owner).hex()
        if actual!=expected:
            offset=next(k for k,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError((index,offset,actual[offset:offset+16],expected[offset:offset+16]))
    return dict(cases=len(records),maximum_absolute_error=0,scope='native/Python complete wheel setup and stance; all owner bytes exact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
