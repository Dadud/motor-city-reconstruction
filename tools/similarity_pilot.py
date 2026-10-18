"""Seed BSim from a retained private Ghidra export without reanalysis or mutation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from tools.recovery_export import ROOT, private_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, required=True)
    parser.add_argument('--ghidra', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=200, choices=range(1, 201), metavar='1..200')
    args = parser.parse_args()
    export = private_output(args.export)
    output = private_output(args.output)
    if output.exists():
        parser.error('output must be absent; retained databases are never overwritten')
    metadata = json.loads((export / 'analysis.json').read_text())
    project = export / 'project'
    if not (project / 'recovery.gpr').is_file():
        parser.error('retained recovery.gpr project not found')
    script = ROOT / 'tools/ghidra/McoSimilarityPilot.java'
    launcher = args.ghidra.resolve() / 'support' / ('analyzeHeadless.bat' if os.name == 'nt' else 'analyzeHeadless')
    output.mkdir(parents=True)
    environment = os.environ.copy()
    environment['JAVA_HOME'] = str(args.java_home.resolve())
    environment['PATH'] = str(args.java_home.resolve() / 'bin') + os.pathsep + environment.get('PATH', '')
    command = [str(launcher), str(project), 'recovery', '-process', metadata['program'],
               '-readOnly', '-noanalysis', '-scriptPath', str(script.parent),
               '-postScript', script.name, str(output), metadata['target_sha256'], str(args.limit)]
    provenance = dict(command=command, export_metadata=metadata,
                      script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                      limitations=['Supplemental Ghidra pilot, not primary REA Evidence',
                                   'Retained project is read-only; no reanalysis'])
    fid_directory = args.ghidra / 'Ghidra/Features/FunctionID/data'
    provenance['fid_databases'] = {}
    for path in sorted(fid_directory.glob('*.fidbf')):
        with path.open('rb') as stream:
            provenance['fid_databases'][path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    with (output / 'headless.log').open('w') as log:
        subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=600)
    # Ghidra can exit zero after script errors; a verified report is mandatory.
    report = json.loads((output / 'report.json').read_text())
    if report['target_sha256'] != metadata['target_sha256']:
        raise ValueError('pilot target identity mismatch')
    print(json.dumps({k: v for k, v in report.items() if k != 'candidates'}, indent=2))


if __name__ == '__main__':
    main()
