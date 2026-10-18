"""Replay connected original mouse runtime observations."""
import argparse
import json
from pathlib import Path
from client.dyno import _SOURCE_SHA256
from tools.cell_corpus import DEFAULT,verify
def compare(runner,corpus=DEFAULT,document=None):
    if document is None:document=json.loads(Path(corpus).read_bytes())
    if document.get('schema')!=1 or document.get('target_sha256')!=_SOURCE_SHA256:
        raise ValueError('mouse runtime corpus identity mismatch')
    return verify(runner,document['probes']['input_mouse_runtime_lifecycle']['cases'],'mouse runtime lifecycle')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runner',type=Path);p.add_argument('--corpus',type=Path,default=DEFAULT)
    a=p.parse_args();print(json.dumps(compare(a.runner,a.corpus)))
