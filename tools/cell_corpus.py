"""Replay synthetic original-execution observations against native cells.

Corpora contain decimal uint32 words (byte images are one word per byte),
never executable bytes or original assets. A fresh oracle export and the
committed regression corpus use exactly the same transport and comparator.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'docs/recovery/corpora/wave0'


def _json_bytes(document):
    return json.dumps(document, sort_keys=True, separators=(',', ':')).encode('utf-8')


def _atomic_write(path, payload):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + '.',
                                     suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_shard(directory, index, kind, identifier):
    entry = index[kind][identifier]
    digest = entry['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(
            c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid corpus shard digest')
    compressed = index['shard_schema'] == 2
    payload = (directory / (digest + ('.json.gz' if compressed else '.json'))).read_bytes()
    if compressed:
        payload = gzip.decompress(payload)
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError('corpus shard digest mismatch')
    document = json.loads(payload)
    if document.get('target_sha256') != index.get('target_sha256'):
        raise ValueError('corpus shard index target mismatch')
    if document.get('schema') != 1 or set(document.get(kind, {})) != {identifier}:
        raise ValueError('corpus shard identity mismatch')
    return document[kind][identifier]


def load_corpus(path=DEFAULT, *, cell=None, probe=None):
    """Read legacy JSON/gzip or a checked, versioned shard snapshot.

    Selection reads just one record; full-suite callers read the same snapshot
    once. Missing/corrupt shards fail explicitly, with no stale-cache fallback.
    """
    path = Path(path)
    if not path.is_dir():
        payload = path.read_bytes()
        return json.loads(gzip.decompress(payload) if path.suffix == '.gz' else payload)
    index = json.loads((path / 'index.json').read_bytes())
    if index.get('shard_schema') not in (1, 2):
        raise ValueError('unsupported cell shard schema')
    if index['shard_schema'] == 2:
        document = dict(index['metadata'])
        if document.get('schema') != 1 or document.get('target_sha256') != index['target_sha256']:
            raise ValueError('corpus index metadata identity mismatch')
    else:
        document = dict(schema=1, target_sha256=index['target_sha256'])
    for kind, selected in (('cells', cell), ('probes', probe)):
        if (cell is not None or probe is not None) and selected is None:
            continue
        identifiers = [selected] if selected is not None else index.get(kind, {})
        document[kind] = {identifier: _read_shard(path, index, kind, identifier)
                          for identifier in identifiers}
    return document


def write_corpus(path, corpus):
    """Write shards by default, or an explicitly selected legacy JSON/gzip file."""
    path = Path(path)
    if path.is_dir() or not path.suffix:
        return write_shards(path, corpus)
    if path.suffix == '.gz':
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(_json_bytes(corpus), compresslevel=6, mtime=0))
        return
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
    return cases_for(identifier, load_corpus(path, cell=identifier))


def shard_corpus(source, destination):
    """Migrate JSON, gzip or a shard snapshot to the current shard format."""
    return write_shards(destination, load_corpus(source))


def write_shards(destination, document):
    """Write immutable gzip records, publishing their index atomically last.

    Old unreferenced records are deliberately retained: concurrent readers of
    the previous manifest must remain valid. Garbage collection is explicit.
    """
    destination = Path(destination)
    if document.get('schema') != 1:
        raise ValueError('unsupported cell corpus schema')
    destination.mkdir(parents=True, exist_ok=True)
    index = dict(shard_schema=2, target_sha256=document['target_sha256'],
                 metadata={key: value for key, value in document.items()
                           if key not in ('cells', 'probes')}, cells={}, probes={})
    for kind in ('cells', 'probes'):
        for identifier, record in document.get(kind, {}).items():
            if kind == 'cells':
                cases_for(identifier, document)
            encoded = _json_bytes(dict(schema=1, target_sha256=document['target_sha256'],
                                       **{kind: {identifier: record}}))
            digest = hashlib.sha256(encoded).hexdigest()
            target = destination / (digest + '.json.gz')
            if target.exists():
                if gzip.decompress(target.read_bytes()) != encoded:
                    raise ValueError('existing corpus shard digest mismatch')
            else:
                _atomic_write(target, gzip.compress(encoded, compresslevel=6, mtime=0))
            index[kind][identifier] = dict(sha256=digest)
    _atomic_write(destination / 'index.json', (json.dumps(index, indent=2)+'\n').encode('utf-8'))
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
    print(json.dumps(dict(cells=len(index['cells']), probes=len(index['probes']),
                         output=str(args.shard_to))))
