"""Compare initialized message dispatch through actual keyboard and camera routines."""
import argparse
import json
from pathlib import Path
from client.dyno import _SOURCE_SHA256
from tools.cell_corpus import load_corpus, DEFAULT,verify


def compare(runner,corpus=DEFAULT,document=None):
    if document is None:document=load_corpus(corpus, probe='window_camera_lifecycle')
    if document.get('schema')!=1 or document.get('target_sha256')!=_SOURCE_SHA256:
        raise ValueError('window camera lifecycle target/schema mismatch')
    return verify(runner,document['probes']['window_camera_lifecycle']['cases'],'window camera lifecycle')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner',type=Path)
    parser.add_argument('--corpus',type=Path,default=DEFAULT)
    args=parser.parse_args()
    print(json.dumps(compare(args.runner,args.corpus)))
