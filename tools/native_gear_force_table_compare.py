"""Exact native/Python complete per-gear force table comparison."""
import argparse
import json
import struct
import subprocess
from client.gear_force_table import gear_force_table
from tools.gear_force_table_oracle import cases


def verify(runner):
    lines=[];expected=[]
    for config,steps in cases():
        for selector in range(8):
            words=struct.unpack('<8I',struct.pack('<8f',*steps))+struct.unpack('<520I',config)
            lines.append(' '.join(map(str,(selector,*words))))
            expected.append(struct.unpack('<135I',struct.pack('<135f',*gear_force_table(config,steps,selector))))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=60)
    actual=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if actual!=expected:raise AssertionError([(i,a[:5],b[:5]) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:4])
    return dict(calls=len(expected),samples=len(expected)*135,maximum_absolute_error=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
