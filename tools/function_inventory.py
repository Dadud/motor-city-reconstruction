"""Join a REA function enumeration to tracked source and private evidence metadata.

Only function identities, evidence IDs and tracked-file references are published.
Address references are candidates, never automatic claims of completed recovery.
"""
import argparse
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = '28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164'
ADDRESS = re.compile(r'(?i)\b(?:0x([0-9a-f]{6,8})|FUN_([0-9a-f]{8}))\b')


def records(value):
    """Unwrap saved MCP text blocks without treating pseudocode as metadata."""
    if isinstance(value, dict):
        if 'operation' in value and 'normalized_result' in value:
            yield value
        for key in ('structuredContent', 'content', 'result'):
            if key in value:
                yield from records(value[key])
        if value.get('type') == 'text':
            try:
                yield from records(json.loads(value['text']))
            except (ValueError, KeyError):
                pass
    elif isinstance(value, list):
        for item in value:
            yield from records(item)


def canonical(value):
    if ':' in value:
        space, offset = value.rsplit(':', 1)
        return space + ':' + hex(int(offset, 16))
    return hex(int(value, 16))


def source_references(root, entries):
    references = defaultdict(lambda: defaultdict(set))
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    for name in filter(None, paths):
        if not name.startswith(('client/', 'native/', 'tools/', 'docs/')):
            continue
        if name.startswith('docs/recovery/functions') or Path(name).suffix not in ('.py', '.cpp', '.hpp', '.md'):
            continue
        path = root / name
        if not path.is_file():
            continue
        group = ('python' if name.startswith('client/') else
                 'native' if name.startswith(('native/src/', 'native/include/')) else
                 'verification' if name.startswith(('tools/', 'native/tests/')) else 'docs')
        for line_number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            for match in ADDRESS.finditer(line):
                address = canonical(match.group(1) or match.group(2))
                if address in entries:
                    references[address][group].add(f'{name}:{line_number}')
    return references


def evidence_index(directory):
    result = defaultdict(set)
    for path in sorted(directory.rglob('*.json')):
        if 'publication-clone' in path.parts:
            continue
        try:
            document = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError):
            continue
        for record in records(document):
            if (record.get('subject') or {}).get('digest', {}).get('sha256') != TARGET:
                continue
            if record['operation'] not in ('analyze_function', 'procedure_pseudo_code'):
                continue
            address = record.get('parameters', {}).get('procedure', '')
            if not re.fullmatch(r'0x[0-9a-fA-F]+', address):
                continue
            normal = record['normalized_result']
            code = normal.get('pseudocode') if isinstance(normal, dict) else normal
            if code:
                result[canonical(address)].add(record['evidence_id'])
    return result


def generate(root, enumeration, evidence, reviews):
    if enumeration['target_sha256'] != TARGET:
        raise ValueError('enumeration target digest mismatch')
    entries = {canonical(item['address']): item['name'] for item in enumeration['functions']}
    if len(entries) != enumeration['procedure_count']:
        raise ValueError('duplicate entries or incomplete function enumeration')
    references = source_references(root, entries)
    observations = evidence_index(evidence) if evidence else {}
    unknown_reviews = set(reviews) - set(entries)
    if unknown_reviews:
        raise ValueError(f'review addresses absent from enumeration: {sorted(unknown_reviews)}')
    rows = []
    for address in sorted(entries, key=lambda value:
            (value.rsplit(':', 1)[0] if ':' in value else '', int(value.rsplit(':', 1)[-1], 16))):
        refs = references[address]
        review = reviews.get(address, {})
        rows.append(dict(address=address, name=entries[address],
            address_space=address.rsplit(':', 1)[0] if ':' in address else 'default',
            decompilation='retained' if observations.get(address) else 'not-indexed',
            translation=review.get('translation', 'unreviewed'),
            verification=review.get('verification', 'unreviewed'),
            scope=review.get('scope', ''),
            reviewed_sources=review.get('sources', []),
            evidence_ids=sorted(observations.get(address, [])),
            python_refs=sorted(refs.get('python', [])),
            native_refs=sorted(refs.get('native', [])),
            verification_refs=sorted(refs.get('verification', [])),
            doc_refs=sorted(refs.get('docs', []))))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enumeration', type=Path, default=ROOT/'docs/recovery/function-enumeration.json')
    parser.add_argument('--evidence', type=Path, help='private evidence directory; metadata only is retained')
    args = parser.parse_args()
    output = ROOT/'docs/recovery'
    enumeration = json.loads(args.enumeration.read_text(encoding='utf-8'))
    reviews = json.loads((output/'function-reviews.json').read_text(encoding='utf-8'))
    rows = generate(ROOT, enumeration, args.evidence, reviews)
    # On public checkouts preserve the already indexed evidence identities.
    previous = output/'functions.json'
    if args.evidence is None and previous.exists():
        existing = {r['address']: r for r in json.loads(previous.read_text())['functions']}
        for row in rows:
            prior = existing.get(row['address'], {})
            row['evidence_ids'] = prior.get('evidence_ids', [])
            row['decompilation'] = 'retained' if row['evidence_ids'] else 'not-indexed'
    bulk_path = output/'modules'/(TARGET+'.json')
    bulk = {}
    if bulk_path.exists():
        document = json.loads(bulk_path.read_text(encoding='utf-8'))
        if document['target_sha256'] != TARGET:
            raise ValueError('bulk metadata target mismatch')
        bulk = {r['address']: r for r in document['functions']}
        if set(bulk) != {r['address'] for r in rows}:
            raise ValueError('bulk and REA enumerations disagree; review profiles before merging')
    for row in rows:
        row['bulk_decompilation'] = bulk.get(row['address'], {}).get('decompilation', 'not-indexed')
    summary = dict(total=len(rows), address_spaces=dict(Counter(r['address_space'] for r in rows)),
        retained_decompilation=sum(bool(r['evidence_ids']) for r in rows),
        bulk_decompilation=dict(Counter(r['bulk_decompilation'] for r in rows)),
        source_reference_candidates=sum(bool(r['python_refs'] or r['native_refs']) for r in rows),
        translation=dict(Counter(r['translation'] for r in rows)),
        verification=dict(Counter(r['verification'] for r in rows)))
    payload = dict(target_sha256=TARGET, enumeration_evidence_id=enumeration['evidence_id'],
                   summary=summary, functions=rows)
    status = ['# Inventory status', '',
        f"Main executable: **{summary['total']:,} analyzed entries**, including "
        f"**{summary['address_spaces'].get('EXTERNAL', 0):,} external imports**.", '',
        f"- Retained decompilation records indexed: **{summary['retained_decompilation']:,} functions**.",
        f"- Bulk private pseudocode exports: **{summary['bulk_decompilation'].get('success', 0):,} functions**.",
        f"- Functions with address mentions in tracked Python/native source: **{summary['source_reference_candidates']:,}** (review candidates).",
        f"- Explicitly reviewed entries: **{sum(bool(r['scope']) for r in rows):,}**.", '',
        '| Reviewed translation label | Entries |', '| --- | ---: |']
    status += [f'| {label} | {count:,} |' for label, count in sorted(summary['translation'].items())]
    status += ['', 'These counts do not measure whole-game completion. Most entries await review.',
               'See [label definitions and refresh instructions](README.md) and the sortable',
               '[CSV worksheet](functions.csv). Supporting binaries are outside this enumeration.', '']
    (output/'status.md').write_text('\n'.join(status), encoding='utf-8')
    # One record per line keeps generated inventory diffs navigable.
    header = json.dumps({k: v for k,v in payload.items() if k != 'functions'}, indent=2)
    body = header[:-2] + ',\n  "functions": [\n' + ',\n'.join(
        '    ' + json.dumps(row) for row in rows) + '\n  ]\n}\n'
    (output/'functions.json').write_text(body, encoding='utf-8')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ';'.join(v) if isinstance(v, list) else v for k,v in row.items()})
    (output/'functions.csv').write_text(stream.getvalue(), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
