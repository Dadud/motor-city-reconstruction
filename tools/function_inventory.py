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


def load_reviews(root, target=TARGET):
    """Merge explicit, hash-scoped reviews without silently overriding a claim."""
    directory = root / 'docs/recovery'
    result = {}
    documents = []
    if target == TARGET:
        documents.append((directory / 'function-reviews.json', None))
    for path in sorted((directory / 'review-batches').glob('*.json')):
        batch = json.loads(path.read_text(encoding='utf-8'))
        digest = batch.get('target_sha256', '')
        if not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError(f'{path.name}: explicit lowercase target hash required')
        if digest == target:
            documents.append((path, batch.get('functions')))
    for path, rows in documents:
        if rows is None:
            rows = json.loads(path.read_text(encoding='utf-8'))
            if path.parent.name == 'review-batches':
                raise ValueError(f'{path.name}: functions mapping required')
        if not isinstance(rows, dict):
            raise ValueError(f'{path.name}: functions mapping required')
        for supplied, review in rows.items():
            address = canonical(supplied)
            if address in result:
                raise ValueError(f'duplicate review for {target}:{address}')
            if not isinstance(review, dict) or not all(review.get(key) for key in
                    ('translation', 'verification', 'scope')):
                raise ValueError(f'{address}: translation, verification and scope required')
            if review['translation'] == 'missing':
                review = dict(sources=[], **review) if 'sources' not in review else review
            elif not review.get('sources'):
                raise ValueError(f'{address}: implementation review requires sources')
            if not isinstance(review['sources'], list):
                raise ValueError(f'{address}: sources list required')
            for source in review['sources']:
                if not isinstance(source, str):
                    raise ValueError(f'{address}: source path required')
                relative = Path(source)
                if relative.is_absolute() or '..' in relative.parts or not (root / relative).is_file():
                    raise ValueError(f'{address}: missing or unsafe source {source}')
            result[address] = review
    return result


def records(value):
    """Unwrap saved MCP text blocks without treating pseudocode as metadata."""
    if isinstance(value, dict):
        if 'operation' in value and 'normalized_result' in value:
            yield value
        for key in ('structuredContent', 'content', 'result', 'records'):
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


def load_triage(root, target=TARGET):
    """Read published triage classifications; absence is not a classification."""
    path = root / 'docs/recovery/triage.json'
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding='utf-8'))
    module = document.get('functions', {}).get(target)
    if not module:
        return {}
    return {row['address']: row for row in module}


def generate(root, enumeration, evidence, reviews, triage=None):
    if enumeration['target_sha256'] != TARGET:
        raise ValueError('enumeration target digest mismatch')
    entries = {canonical(item['address']): item['name'] for item in enumeration['functions']}
    identities = {canonical(item['address']): item for item in enumeration['functions']}
    if len(entries) != enumeration['procedure_count']:
        raise ValueError('duplicate entries or incomplete function enumeration')
    references = source_references(root, entries)
    observations = evidence_index(evidence) if evidence else {}
    unknown_reviews = set(reviews) - set(entries)
    if unknown_reviews:
        raise ValueError(f'review addresses absent from enumeration: {sorted(unknown_reviews)}')
    triage = triage or {}
    rows = []
    for address in sorted(entries, key=lambda value:
            (value.rsplit(':', 1)[0] if ':' in value else '', int(value.rsplit(':', 1)[-1], 16))):
        refs = references[address]
        review = reviews.get(address, {})
        classification = triage.get(address, {})
        rows.append(dict(address=address, name=entries[address],
            boundary_origin=identities[address].get('boundary_origin', 'retained-enumeration'),
            boundary_evidence=identities[address].get('boundary_evidence', ''),
            address_space=address.rsplit(':', 1)[0] if ':' in address else 'default',
            decompilation='retained' if observations.get(address) else 'not-indexed',
            **{'class': classification.get('class', 'unclassified'),
               'triage_rule': classification.get('rule', ''),
               'required': classification.get('required', False),
               'disposition': classification.get('disposition', 'pending')},
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


def preserve_evidence_ids(rows, previous_rows):
    """Merge refreshed evidence with prior retained IDs without dropping history."""
    existing = {row['address']: set(row.get('evidence_ids', []))
                for row in previous_rows}
    for row in rows:
        row['evidence_ids'] = sorted(existing.get(row['address'], set()) |
                                     set(row.get('evidence_ids', [])))
        row['decompilation'] = 'retained' if row['evidence_ids'] else 'not-indexed'
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enumeration', type=Path, default=ROOT/'docs/recovery/function-enumeration.json')
    parser.add_argument('--evidence', type=Path, help='private evidence directory; metadata only is retained')
    args = parser.parse_args()
    output = ROOT/'docs/recovery'
    from tools.function_supplements import enumeration as supplement_enumeration, module as supplement_module
    enumeration = supplement_enumeration(json.loads(args.enumeration.read_text(encoding='utf-8')), output)
    reviews = load_reviews(ROOT)
    triage = load_triage(ROOT)
    rows = generate(ROOT, enumeration, args.evidence, reviews, triage)
    # Preserve prior evidence identities when refreshing from a partial private
    # session export; a refreshed export is not the complete historical corpus.
    previous = output/'functions.json'
    if previous.exists():
        preserve_evidence_ids(rows, json.loads(previous.read_text())['functions'])
    bulk_path = output/'modules'/(TARGET+'.json')
    bulk = {}
    if bulk_path.exists():
        document = supplement_module(json.loads(bulk_path.read_text(encoding='utf-8')), output)
        if document['target_sha256'] != TARGET:
            raise ValueError('bulk metadata target mismatch')
        bulk = {r['address']: r for r in document['functions']}
        if set(bulk) != {r['address'] for r in rows}:
            raise ValueError('bulk and REA enumerations disagree; review profiles before merging')
    for row in rows:
        row['bulk_decompilation'] = bulk.get(row['address'], {}).get('decompilation', 'not-indexed')
    summary = dict(total=len(rows), base_entries=enumeration.get('base_procedure_count', len(rows)),
        supplemental_entries=enumeration.get('supplemental_entries', 0), address_spaces=dict(Counter(r['address_space'] for r in rows)),
        retained_decompilation=sum(bool(r['evidence_ids']) for r in rows),
        bulk_decompilation=dict(Counter(r['bulk_decompilation'] for r in rows)),
        source_reference_candidates=sum(bool(r['python_refs'] or r['native_refs']) for r in rows),
        triage=dict(Counter(r['class'] for r in rows)),
        required=sum(bool(r['required']) for r in rows),
        translation=dict(Counter(r['translation'] for r in rows)),
        verification=dict(Counter(r['verification'] for r in rows)))
    payload = dict(target_sha256=TARGET, enumeration_evidence_id=enumeration['evidence_id'],
                   supplement_sha256=enumeration.get('supplement_sha256'), summary=summary, functions=rows)
    status = ['# Inventory status', '',
        f"Main executable: **{summary['total']:,} inventoried entries**, including "
        f"**{summary['address_spaces'].get('EXTERNAL', 0):,} external imports**.", '',
        f"- Boundary inventory: **{summary['base_entries']:,} retained enumeration entries + {summary['supplemental_entries']:,} explicit supplements**.",
        f"- Retained decompilation records indexed: **{summary['retained_decompilation']:,} functions**.",
        f"- Bulk private pseudocode exports: **{summary['bulk_decompilation'].get('success', 0):,} functions**.",
        f"- Functions with address mentions in tracked Python/native source: **{summary['source_reference_candidates']:,}** (review candidates).",
        f"- Explicitly reviewed entries: **{sum(bool(r['scope']) for r in rows):,}**.",
        f"- Structural triage: game candidates **{summary['triage'].get('game-candidate', 0):,}**, "
        f"classified non-game **{sum(v for k, v in summary['triage'].items() if k not in ('game-candidate', 'unclassified')):,}**. "
        f"**Required after dispositions: {summary['required']:,}**. "
        'An entry is required when its module is in recovery scope and no published '
        'disposition removes it; see [triage](triage.md) and '
        '[dispositions](dispositions.json).', '',
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
