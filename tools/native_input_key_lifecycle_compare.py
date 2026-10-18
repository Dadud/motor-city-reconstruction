"""Compare the connected input key lifecycle with retained complete-call traces."""
import argparse
import json
from pathlib import Path
from tools.cell_corpus import load_corpus, DEFAULT, verify
from client.dyno import _SOURCE_SHA256


def compare(runner, corpus=DEFAULT, document=None):
    if document is None:
        document = load_corpus(corpus, probe='input_key_lifecycle')
    if document.get('target_sha256') != _SOURCE_SHA256 or document.get('schema') != 1:
        raise ValueError('lifecycle corpus target/schema mismatch')
    cases = document.get('probes', {}).get('input_key_lifecycle', {}).get('cases', [])
    result = verify(runner, cases, 'input key lifecycle')
    result['scope'] = 'connected key-query/release lifecycle; actual raw-key child; no substitutions'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner', type=Path)
    parser.add_argument('--corpus', type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(compare(args.runner, args.corpus)))
