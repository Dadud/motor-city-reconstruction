"""Native/Python complete startup record constructor comparisons."""
import argparse
import json
import itertools
import struct
import subprocess
from client.startup_record import construct_startup_record
from tools.startup_record_oracle import cases, owner_image, radius_cases


def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]


def verify(runner, extra_radius_cases=0):
    lines=[];expected=[]
    for index,config,model,kind,area in itertools.chain(cases(), radius_cases(extra_radius_cases)):
        owner=owner_image(index,area)
        record,code=construct_startup_record(bytes(owner),config,
            None if kind=='null' else model,area)
        lines.append(' '.join(map(str,(1 if kind!='null' else 0,bits(area),
            *struct.unpack('<2048I',bytes(owner)),
            *struct.unpack('<520I',config),
            *struct.unpack('<1280I',model)))))
        expected.append((code,)+((struct.unpack('<1192B',record)) if code else ()))
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',text=True,
        capture_output=True,check=True,timeout=120)
    observed=[tuple(map(int,line.split())) for line in result.stdout.splitlines()]
    if observed!=expected:
        for index,(a,b) in enumerate(zip(observed,expected)):
            if a!=b:
                words=[i for i,(x,y) in enumerate(zip(a[1:],b[1:])) if x!=y]
                raise AssertionError((index,words[:8],len(a),len(b),a[:2],b[:2]))
        raise AssertionError((len(observed),len(expected)))
    return dict(cases=len(lines),maximum_absolute_error=0,
        scope='native/Python complete 0x53a1f0 startup record; output bits exact')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('runner')
    parser.add_argument('--radius-cases', type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.radius_cases <= 4096:
        parser.error('--radius-cases must be between 0 and 4096')
    print(json.dumps(verify(args.runner, args.radius_cases)))
