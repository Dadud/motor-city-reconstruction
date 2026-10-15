"""Compare every postload configuration byte across Python and native ports."""
import argparse
import json
import subprocess
from client.assembly_finalization import finalize_loaded_configuration
from tools.assembly_finalization_oracle import cases


def verify(runner):
    images=list(cases())
    result=subprocess.run([str(runner)],input='\n'.join(v.hex() for v in images)+'\n',
        text=True,capture_output=True,check=True,timeout=30)
    rows=result.stdout.splitlines()
    if len(rows)!=len(images):raise AssertionError('native postload row count')
    for index,(line,image) in enumerate(zip(rows,images)):
        actual=bytes.fromhex(line)
        expected=finalize_loaded_configuration(image,components_loaded=True)
        if actual!=expected:raise AssertionError(('native postload image mismatch',index))
    return dict(cases=len(rows),maximum_absolute_error=0,
        scope='native/Python postload numeric tail; all 0x820 configuration bytes exact')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner')
    print(json.dumps(verify(p.parse_args().runner)))
