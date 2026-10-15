"""Publish metadata from private Ghidra exports; never copy raw pseudocode."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from tools.function_inventory import ROOT, TARGET, canonical
from tools.recovery_export import private_output


def json_lines(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def module_metadata(directory, expected):
    metadata_path = directory/'analysis.json'
    if not metadata_path.exists():
        return None
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    if metadata['target_sha256'].lower() != expected:
        raise ValueError('private analysis digest mismatch')
    functions = json_lines(directory/'functions.jsonl')
    entries = {canonical(row['address']): row for row in functions}
    if len(entries) != len(functions) or len(entries) != metadata['function_count']:
        raise ValueError('function enumeration count mismatch or duplicate address')
    journal = {}
    for row in json_lines(directory/'decompilation.jsonl'):
        entry = canonical(row['address'])
        if entry not in entries or row['status'] not in ('success', 'timeout', 'failed'):
            raise ValueError('invalid journal function or status')
        journal[entry] = row['status']
    result = []
    for address, function in entries.items():
        status = journal.get(address, 'not-attempted')
        if function['external']:
            status = 'external'
        if status == 'success':
            code = directory/'pseudocode'/(function['address'].replace(':', '_')+'.c')
            if not code.is_file() or code.stat().st_size == 0:
                status = 'output-missing'
        result.append(dict(address=address, name=function['name'], external=function['external'],
            thunk=function['thunk'], body_bytes=function['body_bytes'],
            direct_callees=sorted(canonical(value) for value in function['direct_callees']),
            decompilation=status, translation='unreviewed'))
    interfaces = json_lines(directory/'interfaces.jsonl')
    summary = dict(function_entries=len(result),
                   decompilation=dict(Counter(row['decompilation'] for row in result)),
                   thunks=sum(row['thunk'] for row in result))
    summary['internal_entries'] = sum(not row['external'] for row in result)
    summary['export_pass'] = ('incomplete' if any(row['decompilation'] == 'not-attempted'
                                               for row in result) else 'all-internal-attempted')
    return dict(target_sha256=expected, provenance=dict(kind='local-ghidra-headless',
        ghidra_version=metadata['ghidra_version'], language=metadata['language'],
        analysis=metadata['analysis'],
        enumeration_sha256=hashlib.sha256((directory/'functions.jsonl').read_bytes()).hexdigest()),
        summary=summary, interfaces=[dict(address=canonical(row['address']), name=row['name'],
            external=row['external'], entry_point=row['entry_point']) for row in interfaces],
        functions=result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, default=ROOT/'evidence/recovery-export')
    args = parser.parse_args()
    args.private_root = private_output(args.private_root)
    output = ROOT/'docs/recovery'
    scope = json.loads((output/'binary-scope.json').read_text(encoding='utf-8'))
    groups = defaultdict(list)
    formats = {}
    roles = {}
    for row in scope['binaries']:
        groups[row['sha256']].append(row['name'])
        formats[row['sha256']] = row.get('format', 'unknown')
        roles[row['sha256']] = row.get('location_role', 'unreviewed')
    modules = output/'modules'
    modules.mkdir(exist_ok=True)
    summaries = []
    private_index = ['# Private recovered-code browser', '',
        'Raw Ghidra pseudocode is research output, not the original source or a compilable game.',
        'Use the authored C++ repository and build.py for supported builds. Original input copies,',
        'databases, pseudocode and failed-function listings in this directory must stay private.', '',
        '| Installed paths | Function browser | Exported |', '| --- | --- | ---: |']
    for digest, names in sorted(groups.items(), key=lambda pair: pair[1][0].lower()):
        module = module_metadata(args.private_root/digest, digest)
        row = dict(sha256=digest, installed_names=names, location_role=roles[digest], enumeration='pending')
        if formats[digest] == 'unrecognized-data':
            row.update(enumeration='not-native-executable', format='unrecognized-data')
        elif module:
            module['installed_names'] = names
            header = json.dumps({k:v for k,v in module.items() if k != 'functions'}, indent=2)
            text = header[:-2] + ',\n  "functions": [\n' + ',\n'.join(
                '    '+json.dumps(f) for f in module['functions']) + '\n  ]\n}\n'
            (modules/(digest+'.json')).write_text(text, encoding='utf-8')
            row.update(enumeration='ghidra-export', **module['summary'])
            directory = args.private_root/digest
            raw_entries = {canonical(f['address']):f for f in json_lines(directory/'functions.jsonl')}
            navigation = ['# '+', '.join(names), '',
                'Private decompiler output; types, boundaries and behavior require review.', '',
                '[Observed type identities](types.jsonl) · [Interfaces](interfaces.jsonl) · '
                '[Direct calls and signatures](functions.jsonl)', '',
                '| Address | Function | Status | Research output |', '| --- | --- | --- | --- |']
            for function in module['functions']:
                original = raw_entries[function['address']]['address'].replace(':', '_')
                link = ('[pseudocode](pseudocode/'+original+'.c)' if function['decompilation']=='success' else
                        '[instructions](failed-listings/'+original+'.asm)' if
                        (directory/'failed-listings'/(original+'.asm')).exists() else '—')
                label = function['name'].replace('|', '\\|').replace('\n', ' ')
                navigation.append('| '+function['address']+' | '+label+' | '+
                                  function['decompilation']+' | '+link+' |')
            (directory/'source-index.md').write_text('\n'.join(navigation)+'\n', encoding='utf-8')
            private_index.append('| '+', '.join(names)+' | [browse]('+digest+'/source-index.md) | '+
                                 str(module['summary']['decompilation'].get('success', 0))+' |')
        elif digest == TARGET:
            existing = json.loads((output/'functions.json').read_text(encoding='utf-8'))
            row.update(enumeration='retained-rea-enumeration', function_entries=len(existing['functions']),
                       retained_rea_decompilation=existing['summary']['retained_decompilation'])
        summaries.append(row)
    (args.private_root/'README.md').write_text('\n'.join(private_index)+'\n', encoding='utf-8')
    report = dict(scope=scope['scope'], installed_files=len(scope['binaries']), unique_binaries=len(groups),
                  modules=summaries)
    installed = defaultdict(list)
    for row in scope['binaries']:
        installed[Path(row['name']).name.lower()].append(row)
    dependencies = []
    for row in summaries:
        module_path = modules/(row['sha256']+'.json')
        if row['enumeration'] != 'ghidra-export':
            continue
        module = json.loads(module_path.read_text(encoding='utf-8'))
        imports = Counter(symbol['name'].split('::', 1)[0] for symbol in module['interfaces']
                          if symbol['external'] and '::' in symbol['name'])
        for library, count in sorted(imports.items()):
            matches = installed.get(library.lower(), [])
            dependencies.append(dict(source_sha256=row['sha256'], library=library, imported_symbols=count,
                resolution='supplied' if matches else 'system-or-missing-unreviewed',
                installed_candidates=[dict(name=match['name'], sha256=match['sha256']) for match in matches]))
    (output/'dependencies.json').write_text(json.dumps(dict(
        scope='static Ghidra external-symbol libraries; dynamic LoadLibrary targets require separate recovery',
        dependencies=dependencies), indent=2)+'\n', encoding='utf-8')
    (output/'export-status.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lines = ['# Installation recovery export status', '',
        f"{report['installed_files']} installed executable-signature/extension candidates; {len(groups)} unique hashes.", '',
        'Header scanning includes ASI plugins and extensionless cache files. Non-executable',
        'extension candidates and historical cache copies are labeled separately.', '',
        '| Installed paths | Role | Enumeration | Entries | Decompiled | Failed/timeout | Not attempted |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for row in summaries:
        counts = row.get('decompilation', {})
        lines.append('| '+', '.join(row['installed_names'])+' | '+row['location_role']+' | '+row['enumeration']+' | '+
            str(row.get('function_entries', '—'))+' | '+str(counts.get('success', 0))+' | '+
            str(counts.get('failed', 0)+counts.get('timeout', 0)+counts.get('output-missing', 0))+' | '+
            str(counts.get('not-attempted', 0) if row['enumeration'] == 'ghidra-export' else '—')+' |')
    lines += ['', 'Decompiled means private pseudocode was exported, not translated or buildable source.',
        'External imports are separate from attempted internal functions. Failed and timed-out',
        'entries remain in each module inventory. Old REA records remain separately indexed in',
        '[the reviewed main-executable worksheet](status.md); zero new exports does not erase them.',
        'Only metadata is published. Runtime behavior and function boundaries remain unverified.', '']
    (output/'export-status.md').write_text('\n'.join(lines), encoding='utf-8')
    failure_rows = []
    for row in summaries:
        if row['enumeration'] != 'ghidra-export':
            continue
        module = json.loads((modules/(row['sha256']+'.json')).read_text(encoding='utf-8'))
        for function in module['functions']:
            if function['decompilation'] in ('failed', 'timeout', 'output-missing'):
                failure_rows.append(dict(target_sha256=row['sha256'], installed_names=row['installed_names'],
                    address=function['address'], name=function['name'], status=function['decompilation']))
    (output/'decompilation-failures.json').write_text(json.dumps(failure_rows, indent=2)+'\n', encoding='utf-8')
    print(f'Accounted for {sum(r["enumeration"] != "pending" for r in summaries)}/{len(groups)} unique hashes; '
          f'{sum(r.get("decompilation", {}).get("success", 0) for r in summaries)} exported functions.')


if __name__ == '__main__':
    main()
