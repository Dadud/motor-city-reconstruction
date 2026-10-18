"""Native/Python exact startup force and full acceleration record comparison."""
import argparse
import json
import struct
import subprocess
from client.acceleration_table import acceleration_table,startup_force
from tools.acceleration_table_oracle import cases,helper_cases


def verify(runner):
    lines=[];expected=[];producers=0
    def line(mode,c,r,rpm=0,selector=0,sample=0.,secondary=False):
        fields=(mode,rpm,selector,struct.unpack('<I',struct.pack('<f',sample))[0],int(secondary),
            *struct.unpack('<520I',c),*struct.unpack('<298I',r))
        lines.append(' '.join(map(str,fields)))
    for c,r in cases():
        line(0,c,r);expected.append(tuple(acceleration_table(c,r)));producers+=1
    for c,r,rpm,selector,sample,secondary in helper_cases():
        line(1,c,r,rpm,selector,sample,secondary)
        expected.append(struct.unpack('<Q',struct.pack('<d',startup_force(c,r,rpm,selector,sample,secondary))))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=60)
    actual=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if actual!=expected:raise AssertionError([(i,a[:4],b[:4]) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b][:4])
    return dict(producer_calls=producers,helper_calls=len(lines)-producers,exact_output_bits=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner');print(json.dumps(verify(p.parse_args().runner)))
