"""Exact C++/Python part bounds, including signed-zero output bits."""
import argparse
import json
import struct
import subprocess
from client.model_bounds import transformed_part_bounds
from tools.model_bounds_oracle import authored_cases


def bits(value): return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(runner):
    records=[(part,mirror) for part in authored_cases() for mirror in (False,True)]
    lines=[]; expected=[]
    for part,mirror in records:
        values=[int(mirror),len(part.vertices),*(bits(v) for v in part.origin),
                *(bits(v) for point in part.vertices for v in point)]
        lines.append(' '.join(map(str,values)))
        bounds=transformed_part_bounds(part,mirrored=mirror)
        expected.append('0' if bounds is None else '1 '+' '.join(
            str(bits(v)) for v in bounds.minimum+bounds.maximum))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True,timeout=30)
    if result.stdout.splitlines()!=expected:raise AssertionError('native part bounds differ')
    return dict(cases=len(records),maximum_absolute_error=0,scope='authored native/Python part bounds; status and signed output bits exact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
