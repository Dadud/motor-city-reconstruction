"""Build and verify an explicit recovery package without shell command strings."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from tools.function_inventory import ROOT, canonical


def load_packages(root):
    directory = root/'docs/recovery'
    document = json.loads((directory/'packages.json').read_text(encoding='utf-8'))
    packages = document['packages']
    ids = [p['id'] for p in packages]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate package identity')
    modules = {}
    for package in packages:
        if not re.fullmatch('[a-z][a-z0-9-]*', package['id']):
            raise ValueError('invalid package identity')
        if not all(package.get(key) for key in ('owner', 'acceptance', 'unresolved')):
            raise ValueError('package owner, acceptance and unresolved work required')
        for dependency in package['depends_on']:
            if dependency not in ids or dependency == package['id']:
                raise ValueError('invalid package dependency')
        for identity in package['roots']:
            digest, address = identity['target_sha256'], canonical(identity['address'])
            if digest not in modules:
                inventory = json.loads((directory/'modules'/(digest+'.json')).read_text(encoding='utf-8'))
                if inventory['target_sha256'] != digest:
                    raise ValueError('package module hash mismatch')
                modules[digest] = {canonical(r['address']) for r in inventory['functions']}
            if address not in modules[digest]:
                raise ValueError('package root absent from hash-scoped inventory')
        for target in package['targets']:
            if not re.fullmatch('mco_[a-z0-9_]+_(?:test|compare)', target):
                raise ValueError('invalid native target')
        for check in package['comparisons']:
            if not re.fullmatch(r'tools\.[a-z0-9_]+', check['module']):
                raise ValueError('comparison must name a tools module')
            if check.get('runner') and check['runner'] not in package['targets']:
                raise ValueError('comparison runner is not a package target')
            if not (root / (check['module'].replace('.', '/')+'.py')).is_file():
                raise ValueError('comparison module missing')
    # Cycles in hand-assigned package dependencies are configuration errors.
    remaining = {p['id']: set(p['depends_on']) for p in packages}
    while remaining:
        ready = {key for key, children in remaining.items() if not children}
        if not ready:
            raise ValueError('cyclic package dependencies')
        remaining = {key: children-ready for key, children in remaining.items() if key not in ready}
    return {p['id']: p for p in packages}


def runner_path(directory, config, target):
    suffix = '.exe' if sys.platform == 'win32' else ''
    for path in (directory/config/(target+suffix), directory/(target+suffix)):
        if path.is_file():
            return path
    raise ValueError(f'package executable missing: {target}')


def check_commands(package, directory, config, original=None):
    commands, skipped = [], []
    for check in package['comparisons']:
        command = [sys.executable, '-m', check['module']]
        if check.get('original'):
            if original is None:
                skipped.append(check['module'])
                continue
            command.append(str(original))
        else:
            command.append(str(runner_path(directory, config, check['runner'])))
        commands.append(command)
    return commands, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', nargs='?')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--check', action='store_true', help='validate metadata without building/running')
    parser.add_argument('--build-dir', type=Path, default=ROOT/'build/recovery-packages')
    parser.add_argument('--config', choices=('Debug', 'Release'), default='Release')
    parser.add_argument('--cmake', default='cmake')
    parser.add_argument('--no-build', action='store_true')
    parser.add_argument('--original-executable', type=Path)
    parser.add_argument('--require-original', action='store_true')
    arguments = sys.argv[1:]
    separator = arguments.index('--') if '--' in arguments else len(arguments)
    extra = arguments[separator+1:]
    args = parser.parse_args(arguments[:separator])
    try:
        packages = load_packages(ROOT)
        if args.list or args.check:
            print(json.dumps({key: dict(owner=p['owner'], acceptance=p['acceptance']) for key, p in packages.items()}, indent=2))
            return 0
        if args.package not in packages:
            parser.error('choose a package from --list')
        if args.require_original and args.original_executable is None:
            parser.error('--require-original needs --original-executable')
        if args.original_executable and not args.original_executable.is_file():
            parser.error('original executable not found')
        package = packages[args.package]
        directory = args.build_dir.resolve()
        cmake = shutil.which(args.cmake)
        if cmake is None:
            parser.error('CMake required; select it with --cmake')
        commands = []
        if not args.no_build:
            commands.extend([
                [cmake, '-S', str(ROOT), '-B', str(directory), f'-DCMAKE_BUILD_TYPE={args.config}',
                 '-DMCO_BUILD_SCRIPTING=OFF', '-DMCO_BUILD_PLATFORM=OFF', '-DBUILD_TESTING=ON', *extra],
                [cmake, '--build', str(directory), '--config', args.config, '--parallel',
                 '--target', *package['targets']]])
        for command in commands:
            subprocess.run(command, cwd=ROOT, check=True)
        test_names = [t.removeprefix('mco_').removesuffix('_test') for t in package['targets'] if t.endswith('_test')]
        if test_names:
            ctest = Path(cmake).with_name('ctest.exe' if sys.platform == 'win32' else 'ctest')
            subprocess.run([str(ctest), '--test-dir', str(directory), '-C', args.config,
                            '--output-on-failure', '--no-tests=error', '-R', '^('+ '|'.join(test_names)+')$'], cwd=ROOT, check=True)
        checks, skipped = check_commands(package, directory, args.config, args.original_executable)
        for command in checks:
            subprocess.run(command, cwd=ROOT, check=True)
        print(json.dumps(dict(package=args.package, checks_passed=len(checks), original_checks_skipped=skipped,
                              scope=package['acceptance'], complete_client_verified=False)))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Package verification failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
