"""Replay synthetic original-execution observations against native cells.

Corpora contain decimal uint32 words (byte images are one word per byte),
never executable bytes or original assets. A fresh oracle export and the
committed regression corpus use exactly the same transport and comparator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'docs/recovery/corpora/wave0.json'


def write_corpus(path, corpus):
    """Keep byte arrays inline and cases on separate lines for useful diffs."""
    metadata = {key: value for key, value in corpus.items() if key != 'cells'}
    chunks = [json.dumps(metadata)[:-1] + ', "cells": {\n']
    cells = []
    for name, cell in corpus['cells'].items():
        rows = ',\n'.join('    '+json.dumps(case, separators=(',', ':'))
                         for case in cell['cases'])
        cells.append('  '+json.dumps(name)+': {"address": '+json.dumps(cell['address'])
                     + ', "cases": [\n'+rows+'\n  ]}')
    chunks.append(',\n'.join(cells)+'\n}}\n')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(''.join(chunks).encode('utf-8'))


def words(values):
    if not isinstance(values, list) or any(
            type(v) is not int or not 0 <= v <= 0xffffffff for v in values):
        raise ValueError('corpus values must be uint32 words')
    return values


def load_cases(identifier, path=DEFAULT):
    path = Path(path)
    if path.is_dir():
        index = json.loads((path / 'index.json').read_text(encoding='utf-8'))
        if index.get('shard_schema') != 1:
            raise ValueError('unsupported cell shard schema')
        entry = index['cells'][identifier]
        # Derive the filename from the digest, never from an index-provided path.
        digest = entry['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('invalid cell shard digest')
        payload = (path / (digest + '.json')).read_bytes()
        if hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError('cell shard digest mismatch')
        document = json.loads(payload)
        if document.get('target_sha256') != index.get('target_sha256'):
            raise ValueError('cell shard index target mismatch')
    else:
        document = json.loads(path.read_text(encoding='utf-8'))
    return cases_for(identifier, document)


def shard_corpus(source, destination):
    """Export an explicit immutable snapshot for fast individual comparisons.

    The source corpus remains authoritative for full-suite/lifecycle runs.
    Re-export after changing it; no implicit cache or fallback hides stale data.
    """
    source, destination = Path(source), Path(destination)
    payload = source.read_bytes()
    document = json.loads(payload)
    if document.get('schema') != 1:
        raise ValueError('unsupported cell corpus schema')
    destination.mkdir(parents=True, exist_ok=True)
    index = dict(shard_schema=1, source_sha256=hashlib.sha256(payload).hexdigest(),
                 target_sha256=document['target_sha256'], cells={})
    for identifier, cell in document['cells'].items():
        cases_for(identifier, document)
        shard = dict(schema=1, target_sha256=document['target_sha256'],
                     cells={identifier: cell})
        encoded = json.dumps(shard, separators=(',', ':')).encode('utf-8')
        digest = hashlib.sha256(encoded).hexdigest()
        (destination / (digest + '.json')).write_bytes(encoded)
        index['cells'][identifier] = dict(sha256=digest, cases=len(cell['cases']))
    temporary = destination / 'index.json.tmp'
    temporary.write_text(json.dumps(index, indent=2)+'\n', encoding='utf-8')
    temporary.replace(destination / 'index.json')
    return index


def cases_for(identifier, corpus):
    """Validate one cell against an already-loaded, consistent corpus snapshot."""
    from tools.function_cell import CELLS, load_manifest
    manifest = load_manifest(CELLS / f'{identifier}.json')
    if corpus.get('schema') != 1:
        raise ValueError('unsupported cell corpus schema')
    if corpus.get('target_sha256') != manifest['roots'][0]['target_sha256']:
        raise ValueError('cell corpus target mismatch')
    cell = corpus.get('cells', {}).get(identifier, {})
    if cell.get('address') != manifest['roots'][0]['address']:
        raise ValueError(f'{identifier}: corpus address mismatch')
    cases = cell.get('cases', [])
    if not cases:
        raise ValueError(f'{identifier}: comparison requires a nonempty corpus')
    for case in cases:
        words(case['input'])
        if not words(case['output']):
            raise ValueError(f'{identifier}: case has no observed output')
    return cases


def verify(runner, cases, identifier):
    if not cases:
        raise ValueError(f'{identifier}: comparison requires a nonempty corpus')
    # A leading case marker also represents zero-argument routines unambiguously.
    lines = [' '.join(map(str, [0, *words(case['input'])])) for case in cases]
    expected = [tuple(words(case['output'])) for case in cases]
    if any(not row for row in expected):
        raise ValueError('comparison requires observed outputs')
    result = subprocess.run([str(runner)], input='\n'.join(lines)+'\n',
                            text=True, capture_output=True, check=True, timeout=120)
    observed = [tuple(map(int, line.split())) for line in result.stdout.splitlines()]
    if len(observed) != len(expected):
        raise AssertionError(f'{identifier}: got {len(observed)} output rows; '
                             f'expected {len(expected)}')
    for index, (got, want) in enumerate(zip(observed, expected)):
        if got != want:
            first = next((k for k, (a, b) in enumerate(zip(got, want)) if a != b),
                         min(len(got), len(want)))
            raise AssertionError(f'{identifier}: case {index}, word {first}: '
                                 f'got {got[first:first+4]}, expected {want[first:first+4]} '
                                 f'(widths {len(got)}/{len(want)})')
    return dict(cases=len(cases), exact_output_bits=True,
                scope=f'{identifier}: native replay of original observations')


def main(identifier):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner', type=Path)
    parser.add_argument('--corpus', type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(verify(args.runner, load_cases(identifier, args.corpus), identifier)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export per-cell comparison snapshots')
    parser.add_argument('--corpus', type=Path, default=DEFAULT)
    parser.add_argument('--shard-to', type=Path, required=True)
    args = parser.parse_args()
    index = shard_corpus(args.corpus, args.shard_to)
    print(json.dumps(dict(cells=len(index['cells']), source_sha256=index['source_sha256'])))
