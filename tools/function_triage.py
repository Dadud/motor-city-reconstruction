"""Rule-based function triage across every inventoried binary.

The static export pass is complete, but the recovery denominator is not: the
worksheets count tool artifacts, compiler runtime, thunks and game logic as
the same kind of entry. This module assigns each exported function an explicit
class from an ordered, inspectable rule set and records which rule fired, so
every classification can be audited or contested without re-running analysis.

Classes are structural observations, not recovery claims. `game-candidate` is an
upper bound on the required set: it includes functions reachable only through
indirect calls, and excludes nothing that the rules have not yet separated.
`no-direct-callers` is a review signal, never a deadness finding, because
vtable dispatch and function-pointer tables produce call edges this static
pass does not record.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / 'docs' / 'recovery'
CLIENT = '28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164'
_TRIAGE_CACHE = {}


def triage_rows():
    if not _TRIAGE_CACHE:
        _TRIAGE_CACHE.update(json.loads(
            (RECOVERY / 'triage.json').read_text(encoding='utf-8')))
    return _TRIAGE_CACHE
THUNK_BODY_LIMIT = 16
SKELETON_BODY_LIMIT = 512

# Ordered rules. The first match wins, so the families are listed from the most
# specific structural signal to the residual catch-all.
TOOL_ARTIFACT = re.compile(r'^switchD_[0-9a-f]+::caseD_\d+$')
EH_ARTIFACT = re.compile(r'^(Catch@[0-9a-f]+|@[0-9a-f]+@[0-9a-f]+|'
                         r'__C_specific_handler\d*|__catch_\d+)$')
IMPORT_STUB = re.compile(r'^[A-Za-z0-9_]+\.[Dd][Ll][Ll]::')
CRT_RUNTIME = re.compile(
    r'^(__break|__security_cookie|__security_check_cookie|__report_range'
    r'failure|__RTC_\w+|_guard_\w+|_purecall|_\w+|\?\?_\w+|'
    r'(?:\w+<[^>]*>)?::~?\w+|std::\w+|type_info|bad_(?:alloc|cast|exception)'
    r'|operator\s*\S+|atexit|_onexit)$')


def load_image(path, digest):
    """Load the exact inventoried executable and map its image ranges.

    The digest is checked because every classification below is a statement
    about specific bytes; an unrecognized binary would silently produce
    confident nonsense.
    """
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('triage requires the exact inventoried executable')
    pe = struct.unpack_from('<I', data, 60)[0]
    optional = pe+24
    base = struct.unpack_from('<I', data, optional+28)[0]
    count = struct.unpack_from('<H', data, pe+6)[0]
    size = struct.unpack_from('<H', data, pe+20)[0]
    sections = []
    for index in range(count):
        section = optional+size+index*40
        _, rva, raw_size, raw = struct.unpack_from('<4I', data, section+8)
        if raw_size:
            sections.append((base+rva, raw_size, raw))
    return data, sections


def read_range(data, sections, start, end):
    pieces = []
    for base, size, raw in sections:
        if base+size <= start or end <= base:
            continue
        first = max(start, base)-base
        last = min(end, base+size)-base
        pieces.append(data[raw+first:raw+last])
    if sum(len(piece) for piece in pieces) != end-start:
        raise ValueError('range spans unmapped bytes')
    return b''.join(pieces)


def linker_shape(operations):
    """Classify a short body by instruction shape, or None when it is logic.

    Incremental linking and identical COMDAT folding leave behind jump thunks,
    constant getters and empty stubs. They are real addresses with no behavior
    of their own, so recovering them one by one would inflate the required set
    by an order of magnitude. Shapes are matched conservatively: anything that
    could be ordinary logic stays a candidate for review.
    """
    if not operations:
        return 'empty-body'
    mnemonics = [operation.mnemonic for operation in operations]
    if all(mnemonic in ('ret', 'nop', 'int3') for mnemonic in mnemonics):
        return 'empty-stub'
    if len(mnemonics) == 2 and mnemonics == ['mov', 'ret']:
        return 'constant-getter'
    if mnemonics[-1] == 'jmp' and all(mnemonic in ('lea', 'mov', 'push')
                                      for mnemonic in mnemonics[:-1]):
        return 'jump-thunk'
    return None


def shapes_for(entry, image, disassembler):
    """Classify one entry's instruction shape, or None when unavailable."""
    operations = operations_for(entry, image, disassembler)
    return linker_shape(operations) if operations else None


def operations_for(entry, image, disassembler, limit=SKELETON_BODY_LIMIT):
    """Disassemble one entry's body, or None when it is not readable."""
    if image is None or entry['external']:
        return None
    if not 0 < entry['body_bytes'] <= limit:
        return None
    start = int(entry['address'], 16)
    try:
        code = read_range(*image, start, start+entry['body_bytes'])
    except ValueError:
        return None
    return list(disassembler.disasm(code, start))


LITERAL = re.compile(r'0x[0-9a-fA-F]+|\b\d+\b')


def skeleton_key(operations):
    """Reduce a body to a structural key, discarding data values.

    Two functions sharing a skeleton are the same code shape with different
    constants: template instantiations, inlined clones or folded COMDATs. The
    count of distinct skeletons is therefore a lower bound on the number of
    distinct behaviors, which is what a recovery denominator needs.
    """
    if not operations:
        return ''
    parts = []
    for operation in operations:
        operands = LITERAL.sub('I', operation.op_str) if operation.op_str else ''
        parts.append(f'{operation.mnemonic}:{operands}')
    return ' '.join(parts)


def classify(entry, image=None, disassembler=None):
    """Return (class, rule) for one module function entry."""
    name = entry['name']
    if entry['external']:
        return 'import', 'external-flag'
    if entry['thunk'] or name.startswith('thunk_'):
        return 'thunk', 'thunk-flag-or-prefix'
    if TOOL_ARTIFACT.match(name):
        return 'tool-artifact', 'ghidra-switch-pseudo-function'
    if EH_ARTIFACT.match(name):
        return 'eh-artifact', 'msvc-seh-funclet'
    if entry['body_bytes'] == 0:
        return 'zero-body', 'empty-function-body'
    shape = shapes_for(entry, image, disassembler)
    if shape:
        return 'linker-artifact', f'instruction-shape:{shape}'
    if IMPORT_STUB.match(name):
        return 'import-stub', 'namespaced-dll-symbol'
    if CRT_RUNTIME.match(name):
        return 'crt-runtime', 'msvc-crt-symbol'
    return 'game-candidate', 'residual'


def triage_module(document, image=None, disassembler=None,
                  module_disposition=None, region_dispositions=None):
    """Classify one module inventory and return its rows, class totals and
    review signals. Review signals are never mixed into the class counts.

    Dispositions decide what counts as work. A module can be dropped wholesale
    when it is a replaceable library, an installer or a third-party patch, and
    an address region can be dropped when the original's own strings identify
    it as bundled library code. What survives is still an upper bound.
    """
    functions = {entry['address']: entry for entry in document['functions']}
    callers = defaultdict(int)
    for entry in document['functions']:
        for callee in entry['direct_callees']:
            if callee in functions:
                callers[callee] += 1
    rows = []
    module = module_disposition or {}
    regions = region_dispositions or {}
    for entry in document['functions']:
        if entry.get('boundary_origin') == 'supplement':
            # A supplement records an independently evidenced callable
            # boundary. Keep it in the candidate work set until normal
            # structural review can classify it from an exported body.
            klass, rule = 'game-candidate', 'evidenced-callable-supplement'
        else:
            klass, rule = classify(entry, image, disassembler)
        address = entry['address']
        block = f'{int(address, 16) & ~0x3ffff:#x}' if ':' not in address else ''
        region = regions.get(block, {})
        evidenced_callback = entry.get('boundary_origin') == 'supplement'
        if evidenced_callback:
            required, disposition = True, 'evidenced-game-callback'
        elif klass != 'game-candidate':
            required, disposition = False, module.get('disposition', 'unclassified')
        elif module.get('counts_toward_required') is False:
            required, disposition = False, module['disposition']
        elif region.get('disposition') == 'library':
            required, disposition = False, 'library-region'
        else:
            required = True
            disposition = region.get('disposition', module.get('disposition',
                                                                'pending'))
        rows.append(dict(address=address, name=entry['name'],
                         **{'class': klass, 'rule': rule},
                         direct_callers=callers[address],
                         required=required, disposition=disposition))
        if entry.get('boundary_origin') == 'supplement':
            rows[-1].update(boundary_origin='supplement', boundary_evidence=entry['boundary_evidence'])
    groups = Counter()
    for row, entry in zip(rows, document['functions']):
        key = skeleton_key(operations_for(entry, image, disassembler)) or None
        row['skeleton'] = hashlib.sha256(key.encode()).hexdigest()[:12] if key else ''
        if row['required'] and key:
            groups[row['skeleton']] += 1
    for row in rows:
        row['clone_count'] = groups.get(row['skeleton'], 0) if row['required'] else 0
    totals = dict(Counter(row['class'] for row in rows))
    review = dict(no_direct_callers=sum(row['direct_callers'] == 0
                                       for row in rows if row['required']),
                  required_entries=sum(row['required'] for row in rows),
                  required_skeletons=len(groups),
                  cloned_entries=sum(count for count in groups.values() if count > 1),
                  pending_disposition=sum(
                      row['disposition'] in ('pending', 'unclassified')
                      for row in rows if row['required']))
    return rows, totals, review


def triage(modules, images=None, dispositions=None):
    """Triage every module inventory, keyed by target digest."""
    images = images or {}
    dispositions = dispositions or {}
    disassembler = None
    if images:
        try:
            from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        except ImportError:
            raise SystemExit('capstone is required for instruction shapes')
        disassembler = Cs(CS_ARCH_X86, CS_MODE_32)
    result = {}
    for document in modules:
        digest = document['target_sha256']
        regions = {record['block']: record
                   for record in dispositions.get('regions', {}).get(
                       'client', {}).get('regions', [])}
        rows, totals, review = triage_module(
            document, images.get(digest), disassembler,
            dispositions.get('modules', {}).get(digest), regions)
        result[digest] = dict(
            installed_names=document['installed_names'], totals=totals,
            review=review, functions=rows)
    return result




def wave_progress():
    """Count required entries covered by recovered cells, grouped by wave."""
    covered = Counter()
    for path in manifests_or_cells():
        manifest = load_cell_manifest(path)
        if manifest.get('status', 'scaffolded') != 'implemented':
            continue
        waves = {}
        wave_path = RECOVERY / 'waves.json'
        if wave_path.exists():
            waves = json.loads(wave_path.read_text(
                encoding='utf-8')).get('regions', {})
        for root in manifest['roots']:
            if int(root['address'], 16) == 0x0:
                continue
            block = f'{int(root["address"], 16) & ~0x3ffff:#x}'
            wave = waves.get(block, {}).get('wave', 'unassigned')
            rows = triage_rows().get('functions', {}).get(CLIENT, [])
            for row in rows:
                if row['address'] == root['address'] and row['required']:
                    covered[wave] += 1
                    break
    return [dict(id=f'{wave}:{count}', wave=wave, entries=count)
            for wave, count in sorted(covered.items())]


def manifests_or_cells():
    return sorted((RECOVERY / 'cells').glob('*.json'))


def load_cell_manifest(path):
    return json.loads(path.read_text(encoding='utf-8'))


def wave_report(directory, triage_result):
    """Order the required set into waves from the published wave map."""
    path = directory / 'waves.json'
    if not path.exists():
        return []
    waves = json.loads(path.read_text(encoding='utf-8')).get('regions', {})
    totals = defaultdict(int)
    shapes = defaultdict(int)
    for record in triage_result.values():
        if record['installed_names'][0] != 'mcity.exe':
            continue
        for row in record['functions']:
            if not row['required']:
                continue
            block = f"{int(row['address'], 16) & ~0x3ffff:#x}" \
                if ':' not in row['address'] else ''
            wave = waves.get(block, {}).get('wave', 'unassigned')
            totals[wave] += 1
            if row.get('skeleton'):
                shapes[wave] += 0
    return [dict(wave=wave, entries=count)
            for wave, count in sorted(totals.items())]


def regions(rows, block=1 << 18):
    """Bucket required entries by address region and flag density anomalies.

    A region holding thousands of entries in a few hundred kilobytes cannot be
    game logic: it is either a bundled library, heavily inlined template code,
    or an inventory artifact. The flag asks for review, it does not decide.
    Each region also reports how many distinct code shapes it contains, which
    is what separates a farm of instantiations from genuine per-function work.
    """
    buckets = defaultdict(list)
    for row in rows:
        if not row['required']:
            continue
        address = row['address']
        if ':' in address or not re.fullmatch('0x[0-9a-f]+', address):
            continue
        buckets[int(address, 16) >> 18].append(row)
    result = []
    for index in sorted(buckets):
        members = buckets[index]
        result.append(dict(block=f'{index << 18:#08x}', entries=len(members),
                           shapes=len({row['skeleton'] for row in members
                                       if row.get('skeleton')}),
                           density_anomaly=len(members) > 2000))
    return result


def region_table(document_rows, label):
    """Render the address-region work queue for one binary."""
    table = regions(document_rows)
    lines = [f'### {label}', '',
        '| Region | Required entries | Distinct shapes | Ratio | Note |',
        '| --- | ---: | ---: | ---: | --- |']
    for row in table:
        note = ('inventory density anomaly: review before counting'
                if row['density_anomaly'] else '')
        ratio = (f"{row['entries'] / max(row['shapes'], 1):.1f}x")
        lines.append(f"| `{row['block']}` | {row['entries']:,} | {row['shapes']:,} | "
                     f"{ratio} | {note} |")
    lines.append('')
    return lines


def summary_markdown(triage_result, roles):
    """Render the per-binary disposition table."""
    lines = ['# Function triage', '',
        'Rule-based classification of every exported function, then published',
        'dispositions decide what counts as required work. `no-direct-callers`',
        'is a review signal rather than a deadness finding.', '',
        '| Binary | Role | Entries | Required | Distinct shapes |',
        '| --- | --- | ---: | ---: | ---: |']
    for digest, record in sorted(triage_result.items(),
                                 key=lambda kv: -kv[1]['review']['required_entries']):
        lines.append(f"| {record['installed_names'][0]} | "
                     f"{roles.get(digest, '')} | "
                     f"{sum(record['totals'].values()):,} | "
                     f"{record['review']['required_entries']:,} | "
                     f"{record['review']['required_skeletons']:,} |")
    lines += ['']
    aggregate = Counter()
    unreviewed = 0
    for record in triage_result.values():
        aggregate.update(record['totals'])
        unreviewed += record['review']['no_direct_callers']
    lines.append('| Class | Entries |')
    lines.append('| --- | ---: |')
    for label, count in sorted(aggregate.items(), key=lambda kv: -kv[1]):
        lines.append(f'| {label} | {count:,} |')
    lines += ['', f'Review signal — `game-candidate` entries with no direct caller: '
                  f'**{unreviewed:,}**. Indirect dispatch is not recorded by this '
                  'pass, so this is a work queue, not dead code.', '']
    required = sum(record['review']['required_entries']
                   for record in triage_result.values())
    shapes = sum(record['review']['required_skeletons']
                 for record in triage_result.values())
    pending = sum(record['review']['pending_disposition']
                  for record in triage_result.values())
    untreat = sum(record['review']['required_entries']
                  for record in triage_result.values()
                  if record['review']['required_skeletons'] == 0
                  and record['review']['required_entries'])
    lines += ['## Required set', '',
        f'- Required entries after dispositions: **{required:,}**',
        f'- Distinct code shapes behind them (lower bound on behaviors): **{shapes:,}**',
        f'- Entries still awaiting a disposition: **{pending:,}**',
        f'- Of which in modules whose internals have not had region treatment: '
        f'**{untreat:,}** (their module role is reviewed, their contents are not)', '',
        'An entry counts as required when its module is in recovery scope and no',
        'published disposition removes it. Dispositions live in',
        '`docs/recovery/dispositions.json` with the evidence for each decision.', '',
        'Distinct code shapes are measured only for modules whose original binary',
        'was supplied to this run, so the shape total understates the full set.', '']
    order = wave_report(RECOVERY, triage_result)
    recovered = wave_progress()
    by_wave = {row['wave']: row['entries'] for row in recovered}
    done = sum(row['entries'] for row in recovered)
    if order:
        lines += ['## Wave order (region-level first cut)', '',
                  'Wave execution: ' + ', '.join(
                      f"{row['wave']} {by_wave.get(row['wave'], 0):,}/"
                      f"{row['entries']:,}" for row in order),
                  f"{done:,} of {sum(r['entries'] for r in order):,} required entries "
                  f"covered across {len(recovered)} active wave(s).", '',
                  '| Wave | Required entries |', '| --- | ---: |']
        lines += [f"| {row['wave']} | {row['entries']:,} |" for row in order]
        lines += ['']
    client = triage_result.get(CLIENT)
    if client:
        lines += ['## Address-region work queue: mcity.exe', '',
            'Game logic and bundled libraries share address space and carry no',
            'symbols, so the rules above cannot separate them. Regions are the',
            'review unit: each needs an owner decision before the required count',
            'is real. Known-good reviewed functions all fall in 0x430000-0x550000.',
            '']
        lines += region_table(client['functions'], 'mcity.exe')
    lines += ['Refresh: `python -m tools.function_triage`. Rules live in this module and',
        'are deliberately explicit so a contested classification is a one-line',
        'change with a recorded consequence.', '']
    return '\n'.join(lines)


def load_dispositions(directory):
    """Read published dispositions; an absent file leaves everything pending."""
    path = directory / 'dispositions.json'
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding='utf-8'))
    return {key: value for key, value in document.items()
            if key in ('modules', 'regions')}


def load_modules(directory):
    documents = []
    for path in sorted((directory / 'modules').glob('*.json')):
        document = json.loads(path.read_text(encoding='utf-8'))
        if not re.fullmatch('[0-9a-f]{64}', document['target_sha256']):
            raise ValueError(f'{path.name}: lowercase target hash required')
        from tools.function_supplements import module as supplement_module
        documents.append(supplement_module(document, directory))
    if not documents:
        raise ValueError('no module inventories found')
    return documents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', nargs='?',
                        help='original binary enabling instruction shapes')
    parser.add_argument('--directory', type=Path, default=RECOVERY)
    parser.add_argument('--output', type=Path,
                        default=RECOVERY / 'triage.json')
    parser.add_argument('--summary', type=Path, default=RECOVERY / 'triage.md')
    parser.add_argument('--check', action='store_true',
                        help='validate inputs without writing outputs')
    parser.add_argument('--detail-all', action='store_true',
                        help='publish per-function rows for every binary, not '
                             'only the active game-client target')
    args = parser.parse_args()
    documents = load_modules(args.directory)
    images = {}
    if args.executable:
        wanted = {document['target_sha256'] for document in documents}
        for digest in sorted(wanted):
            path = Path(args.executable)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                continue
            images[digest] = load_image(path, digest)
        if CLIENT not in images:
            raise SystemExit('no supplied binary matched an inventoried target; '
                             'instruction shapes stay unavailable')
    result = triage(documents, images, load_dispositions(args.directory))
    roles = {}
    index = args.directory / 'module-roles.json'
    if index.exists():
        roles = {digest: record.get('role', '')
                 for digest, record in json.loads(
                     index.read_text(encoding='utf-8')).get('modules',
                                                              {}).items()}
    aggregate = Counter()
    for record in result.values():
        aggregate.update(record['totals'])
    payload = dict(schema_version=1, totals=dict(aggregate),
                   modules={digest: dict(installed_names=record['installed_names'],
                                         totals=record['totals'],
                                         review=record['review'])
                            for digest, record in result.items()})
    if args.check:
        print(json.dumps(payload['totals'], indent=2))
        return
    args.output.write_text(json.dumps(dict(
        payload,
        functions={digest: record['functions']
                   for digest, record in result.items()
                   if args.detail_all or digest == CLIENT}), indent=1),
        encoding='utf-8')
    args.summary.write_text(summary_markdown(result, roles), encoding='utf-8')
    print(json.dumps(payload['totals'], indent=2))


if __name__ == '__main__':
    main()
