"""Compare the connected record lifecycle with retained complete-call traces."""
import argparse
import json
from pathlib import Path
from tools.cell_corpus import DEFAULT, verify
from client.dyno import _SOURCE_SHA256


def compare(runner, corpus=DEFAULT, document=None):
    if document is None:
        document = json.loads(Path(corpus).read_text(encoding='utf-8'))
    if document.get('target_sha256') != _SOURCE_SHA256 or document.get('schema') != 1:
        raise ValueError('lifecycle corpus target/schema mismatch')
    cases = document.get('probes', {}).get('record_lifecycle', {}).get('cases', [])
    result = verify(runner, cases, 'record lifecycle')
    result['scope'] = 'connected complete-call lifecycle with declared callback substitutions'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner', type=Path)
    parser.add_argument('--corpus', type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(compare(args.runner, args.corpus)))
