"""Index existing hash-scoped inventories and explicit reviews into dependency work.

The detailed generated graph belongs in build/, not a second editable function
ledger. Direct-call components are research candidates, never inferred completion.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from tools.function_inventory import ROOT, canonical, load_reviews


def strongly_connected(graph):
    """Iterative Kosaraju traversal: no Python recursion limit on large binaries."""
    reverse = {node: [] for node in graph}
    for node, children in graph.items():
        for child in children:
            reverse[child].append(node)
    seen, order = set(), []
    for node in sorted(graph):
        if node in seen:
            continue
        seen.add(node)
        stack = [(node, iter(graph[node]))]
        while stack:
            current, children = stack[-1]
            child = next(children, None)
            if child is None:
                order.append(current)
                stack.pop()
            elif child not in seen:
                seen.add(child)
                stack.append((child, iter(graph[child])))
    seen, components = set(), []
    for node in reversed(order):
        if node in seen:
            continue
        component, pending = [], [node]
        seen.add(node)
        while pending:
            current = pending.pop()
            component.append(current)
            for parent in reverse[current]:
                if parent not in seen:
                    seen.add(parent)
                    pending.append(parent)
        components.append(sorted(component))
    return components


def module_work(module, reviews):
    digest = module['target_sha256']
    functions = {canonical(row['address']): row for row in module['functions']}
    if len(functions) != module['summary']['function_entries']:
        raise ValueError(f'{digest}: duplicate or incomplete enumeration')
    if set(reviews) - set(functions):
        raise ValueError(f'{digest}: review absent from module inventory')
    graph, unresolved = {}, []
    for address, row in functions.items():
        children = {canonical(child) for child in row['direct_callees']}
        graph[address] = sorted(children & functions.keys())
        unresolved.extend(dict(caller=address, callee=child) for child in sorted(children-functions.keys()))
    groups = strongly_connected(graph)
    membership = {address: index for index, group in enumerate(groups) for address in group}
    packages = []
    for index, group in enumerate(groups):
        dependencies = sorted({membership[child] for address in group for child in graph[address]
                               if membership[child] != index})
        pending = [address for address in group if reviews.get(address, {}).get('translation', 'unreviewed')
                   in ('unreviewed', 'partial', 'missing', 'python-complete-supported-domain;native-partial')]
        packages.append(dict(id=index, members=group, dependencies=dependencies,
                             pending_members=pending, research_candidate=True))
    review_counts = Counter(reviews.get(address, {}).get('translation', 'unreviewed') for address in functions)
    return dict(target_sha256=digest, enumeration_sha256=module['provenance']['enumeration_sha256'],
                supplement_sha256=module['provenance'].get('supplement_sha256'),
                summary=dict(entries=len(functions), explicitly_reviewed=len(reviews),
                             translation=dict(sorted(review_counts.items())), direct_call_components=len(groups),
                             unresolved_direct_edges=len(unresolved)),
                components=packages, unresolved_direct_edges=unresolved)


def generate(root):
    directory = root / 'docs/recovery'
    scope = json.loads((directory / 'binary-scope.json').read_text(encoding='utf-8'))
    roles = json.loads((directory / 'module-roles.json').read_text(encoding='utf-8'))['modules']
    grouped = defaultdict(list)
    for row in scope['binaries']:
        grouped[row['sha256']].append(row)
    if set(grouped) != set(roles):
        raise ValueError('module roles must account for every unique installed hash')
    modules = []
    for digest, rows in sorted(grouped.items()):
        inventory = directory / 'modules' / (digest + '.json')
        role = roles[digest]
        if not all(role.get(key) for key in ('role', 'basis', 'review_status')):
            raise ValueError(f'{digest}: incomplete module role')
        result = dict(target_sha256=digest, installed_names=sorted(row['name'] for row in rows), **role)
        if inventory.is_file():
            from tools.function_supplements import module as supplement_module
            document = supplement_module(json.loads(inventory.read_text(encoding='utf-8')), directory)
            if document['target_sha256'] != digest:
                raise ValueError('module inventory hash mismatch')
            result.update(module_work(document, load_reviews(root, digest)))
        elif any(row['format'] != 'unrecognized-data' for row in rows):
            raise ValueError(f'{digest}: executable inventory missing')
        else:
            result['summary'] = dict(entries=0, explicitly_reviewed=0, translation={})
        modules.append(result)
    # Static imports are candidates, not a proof of the dynamic call targets.
    imports = json.loads((directory / 'dependencies.json').read_text(encoding='utf-8'))
    source_digest = hashlib.sha256(json.dumps(modules, sort_keys=True).encode()).hexdigest()
    return dict(schema_version=1, input_digest=source_digest,
                limitations=['Direct calls only; callbacks, vtables and dynamic loads need explicit recovery.',
                             'Components are research groups, not certified subsystem boundaries.',
                             'Module role does not classify every function or certify a replacement.'],
                summary=dict(modules=len(modules), entries=sum(m['summary']['entries'] for m in modules),
                             explicitly_reviewed=sum(m['summary']['explicitly_reviewed'] for m in modules)),
                modules=modules, import_candidates=imports['dependencies'])


def summary_markdown(backlog):
    lines = ['# Installation work index', '',
             'Generated from the existing module inventories and explicit review records.',
             'Module roles describe investigation scope; they do not certify library equivalence.',
             'Function counts are not a whole-game completion percentage.', '',
             '| Installed paths | Role | Entries | Reviewed | Direct-call components |',
             '| --- | --- | ---: | ---: | ---: |']
    for module in sorted(backlog['modules'], key=lambda m: m['installed_names'][0].lower()):
        summary = module['summary']
        lines.append(f"| {', '.join(module['installed_names'])} | {module['role']} | "
                     f"{summary['entries']:,} | {summary['explicitly_reviewed']:,} | "
                     f"{summary.get('direct_call_components', 0):,} |")
    lines += ['', 'The detailed reproducible dependency graph is generated into `build/recovery/`.',
              'Unknown direct destinations remain explicit; indirect and cross-module targets',
              'must be recovered before claiming a complete dependency closure.', '',
              'Refresh: `python -m tools.recovery_backlog --summary docs/recovery/work-index.md`.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/recovery/work-index.json')
    parser.add_argument('--summary', type=Path)
    parser.add_argument('--check', action='store_true', help='validate inputs without writing outputs')
    args = parser.parse_args()
    backlog = generate(ROOT)
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(backlog, separators=(',', ':'))+'\n', encoding='utf-8')
        if args.summary:
            args.summary.write_text(summary_markdown(backlog), encoding='utf-8')
    print(json.dumps(backlog['summary']))


if __name__ == '__main__':
    main()
