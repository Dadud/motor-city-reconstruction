"""Native/Python complete mechanical loader results on original-test corpora."""
import argparse
import json
import subprocess
from client.mechanical_loaders import MECHANICAL_LOADERS
from tools.mechanical_engine_block_oracle import cases as engine_cases
from tools.mechanical_loaders_oracle import cases,initial_configuration
from tools.engine_component_loaders_oracle import cases as engine_component_cases
from tools.tire_loader_oracle import cases as tire_cases
from tools.engine_auxiliary_oracle import cases as auxiliary_cases


def verify(runner):
    image=initial_configuration()
    records=[*((k,image,p,None) for k,p in cases()),
        *((160001,image,p,None) for p in engine_cases()),
        *((k,c,p,None) for k,c,p in engine_component_cases()),
        *((110001,c,p,t) for c,p,t in tire_cases()),
        *((k,c,p,None) for k,c,p in auxiliary_cases())]
    lines=[];wanted=[]
    for kind,image,part,templates in records:
        lines.append(f'{kind} {image.hex()} {part.hex()}'+(' '+templates.hex() if templates is not None else ''))
        out=MECHANICAL_LOADERS[kind](image,part,templates) if kind==110001 else MECHANICAL_LOADERS[kind](image,part)
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
        scope='twenty-three native/Python loaders; status and all configuration/component bytes exact; original-function authored corpora')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
