"""Run resumable private Ghidra exports against the hashed installation inventory."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def private_output(path):
    path = path.resolve()
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        raise ValueError('output must be inside the repository ignored evidence directory')
    if not relative.parts or relative.parts[0] != 'evidence':
        raise ValueError('raw exports must remain under ignored evidence/')
    if subprocess.run(['git', 'check-ignore', '-q', str(path)], cwd=ROOT).returncode:
        raise ValueError('output is not ignored by Git')
    tracked = subprocess.check_output(['git', 'ls-files', '--', str(relative)], cwd=ROOT)
    if tracked:
        raise ValueError('output contains tracked files')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_root', type=Path)
    parser.add_argument('--ghidra', type=Path, required=True)
    parser.add_argument('--java-home', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/recovery-export')
    parser.add_argument('--binary', action='append', help='inventory filename; repeat to select several')
    parser.add_argument('--max-functions', type=int, default=200,
                        help='attempts per binary: 0 inventory only; -1 all remaining')
    parser.add_argument('--timeout', type=int, default=30, help='decompiler seconds per function')
    parser.add_argument('--failure-listings', action='store_true', help='export failed-function instructions without retrying decompilation')
    retry = parser.add_mutually_exclusive_group()
    retry.add_argument('--retry-failed', action='store_true')
    retry.add_argument('--retry-timeouts', action='store_true', help='retry only timed-out functions')
    args = parser.parse_args()
    if args.max_functions < -1 or args.timeout < 1:
        parser.error('max-functions must be -1 or nonnegative; timeout must be positive')
    try:
        output = private_output(args.output)
    except ValueError as error:
        parser.error(str(error))
    headless = args.ghidra/'support'/('analyzeHeadless.bat' if os.name == 'nt' else 'analyzeHeadless')
    if not headless.is_file():
        parser.error('Ghidra analyzeHeadless was not found')
    scope = json.loads((ROOT/'docs/recovery/binary-scope.json').read_text())['binaries']
    selected = set(args.binary or [row['name'] for row in scope])
    unknown = selected - {row['name'] for row in scope}
    if unknown:
        parser.error(f'unknown inventory filenames: {sorted(unknown)}')
    environment = os.environ.copy()
    if args.java_home:
        environment['JAVA_HOME'] = str(args.java_home.resolve())
        environment['PATH'] = str(args.java_home.resolve()/'bin') + os.pathsep + environment.get('PATH', '')
    seen = set()
    for row in scope:
        if row['name'] not in selected or row['sha256'] in seen:
            continue
        source = args.game_root/row['name']
        with source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != row['sha256']:
            raise ValueError(f'installed binary digest mismatch: {row["name"]}')
        seen.add(digest)
        if row.get('format') == 'unrecognized-data':
            print(f'Skipping non-executable extension candidate: {row["name"]}', flush=True)
            continue
        target = output/digest
        project = target/'project'
        project.mkdir(parents=True, exist_ok=True)
        # Ghidra's Windows batch launcher mishandles parentheses in import paths.
        # Keep an exact private copy; never alter the installed artifact.
        imported = target/'input'/row['name']
        imported.parent.mkdir(parents=True, exist_ok=True)
        if not imported.exists():
            shutil.copyfile(source, imported)
        with imported.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise ValueError('private import copy digest mismatch')
        existing = (project/'recovery.gpr').exists()
        metadata = target/'analysis.json'
        if existing and metadata.exists():
            recorded = json.loads(metadata.read_text())
            if recorded['target_sha256'].lower() != digest:
                raise ValueError('cached project identity mismatch')
            mode = ['-process', recorded['program'], '-noanalysis']
        elif existing:
            mode = ['-process', source.name]
        else:
            mode = ['-import', str(imported)]
        run_id = str(uuid.uuid4())
        script = (['RecoverFailureListings.java', str(target), run_id] if args.failure_listings else
                  ['RecoverProgram.java', str(target), str(args.max_functions), str(args.timeout),
                   'timeouts' if args.retry_timeouts else str(args.retry_failed).lower(), run_id])
        command = [str(headless.resolve()), str(project), 'recovery', *mode,
                   '-scriptPath', str(ROOT/'tools/ghidra'), '-postScript', *script]
        print(f'Exporting {row["name"]} ({digest[:12]}): {"resume" if existing else "initial analysis"}', flush=True)
        with (target/'headless.log').open('a', encoding='utf-8') as log:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        batch = target/'batch-result.json'
        if (result.returncode or not metadata.exists() or not batch.exists()
                or json.loads(batch.read_text()).get('run_id') != run_id):
            raise RuntimeError(f'Ghidra export failed; inspect {target / "headless.log"}')
        print(f'Export stored privately: {target}', flush=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
