"""Exact native/Python body initialization images and geometry arrays."""
import argparse
import json
import struct
import subprocess
from client.body_constructor import construct_body
from client.body_geometry import body_samples
from tools.body_constructor_oracle import cases


def bits(value): return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(runner):
    lines=[];expected=[]
    owner=bytes((i*73+19)&255 for i in range(0x2000))
    for identity,mass,extent,shape,material in cases():
        lines.append(' '.join(map(str,(1,shape,identity,material,bits(mass),*(bits(v) for v in extent)))))
        image=construct_body(owner,identity,mass,extent,shape,material)
        expected.append(struct.unpack('<2048I',image))
    count=len(lines)
    for extent in ((1.,.5,2.), (2.,.5,1.), (1.,1.,1.), (-0.,0.,-0.), (-1.,.5,-2.),
                   (.1234567,.7654321,2.345678)):
        for shape in range(5):
            lines.append(' '.join(map(str,(0,shape,0,0,0,*(bits(v) for v in extent)))))
            expected.append(tuple(bits(v) for p in body_samples(shape,extent) for v in p))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True,timeout=60)
    observed=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if len(observed)!=len(expected): raise AssertionError('body comparison record count')
    for i,(actual,wanted) in enumerate(zip(observed,expected)):
        if actual!=wanted: raise AssertionError((i,[(hex(k*4),a,b) for k,(a,b) in enumerate(zip(actual,wanted)) if a!=b][:12]))
    return dict(constructor_cases=count,geometry_cases=len(lines)-count,maximum_absolute_error=0,
        scope='native/Python all owner bytes and signed geometry bits exact')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
