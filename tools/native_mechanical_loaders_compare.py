"""Native/Python complete mechanical loader results on original-test corpora."""
import argparse
import json
import subprocess
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.mechanical_engine_block_oracle import cases as engine_cases
from tools.mechanical_loaders_oracle import cases,initial_configuration


def verify(runner):
    image=initial_configuration();records=[*cases(),*((160001,p) for p in engine_cases())]
    lines=[];wanted=[]
    for kind,part in records:
        lines.append(f'{kind} {image.hex()} {part.hex()}')
        out=MECHANICAL_LOADERS[kind](image,part)
        wanted.append(f'{out.status} {out.configuration.hex()} {out.component.hex()}')
    result=subprocess.run([str(runner)],input='\n'.join(lines)+'\n',capture_output=True,
        text=True,check=True,timeout=60)
    rows=result.stdout.splitlines()
    if len(rows)!=len(wanted):raise AssertionError('native mechanical row count')
    for index,(actual,expected) in enumerate(zip(rows,wanted)):
        if actual!=expected:
            fields=actual.split();expected_fields=expected.split()
            for field,(a,b) in enumerate(zip(fields,expected_fields)):
                if a!=b:
                    offset=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
                    raise AssertionError((index,records[index][0],field,offset,a[offset:offset+16],b[offset:offset+16]))
            raise AssertionError((index,'native mechanical field count'))
    return dict(cases=len(rows),maximum_absolute_error=0,
        scope='seven native/Python loaders; status and all configuration/component bytes exact; original-function authored corpora')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
