"""Replay connected console buffering and game fallback observations."""
import argparse
import json
from pathlib import Path
from client.dyno import _SOURCE_SHA256
from tools.cell_corpus import DEFAULT, verify


def compare(runner, corpus=DEFAULT, document=None):
    if document is None:
        document=json.loads(Path(corpus).read_bytes())
    if document.get('schema')!=1 or document.get('target_sha256')!=_SOURCE_SHA256:
        raise ValueError('console lifecycle corpus target/schema mismatch')
    return verify(runner,document['probes']['input_console_lifecycle']['cases'],'input console lifecycle')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner',type=Path)
    parser.add_argument('--corpus',type=Path,default=DEFAULT)
    args=parser.parse_args()
    print(json.dumps(compare(args.runner,args.corpus)))
