"""Build an owned Windows x86 process and verify bounded REA/Frida hooks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from tools.recovery_export import ROOT, private_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zig', type=Path, required=True)
    parser.add_argument('--rea', default=shutil.which('rea.cmd') or shutil.which('rea'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt' or not args.rea:
        parser.error('requires Windows and the REA CLI')
    output = private_output(args.output)
    if output.exists():
        parser.error('output must be absent; previous observations are never overwritten')
    output.mkdir(parents=True)
    source = ROOT / 'tools/fixtures/frida_canary.c'
    script = ROOT / 'tools/fixtures/frida_canary.js'
    executable = output / 'frida-canary-x86.exe'
    subprocess.run([str(args.zig.resolve()), 'cc', '-target', 'x86-windows-gnu', '-O0',
                    str(source), '-o', str(executable)], check=True, timeout=180)
    process = subprocess.Popen([str(executable)])
    try:
        result = subprocess.run([str(args.rea), 'instrument-with-frida', 'attach',
                                 str(process.pid), '--script-file', str(script),
                                 '--duration-ms', '1800', '--json'],
                                capture_output=True, text=True, timeout=25)
        (output / 'observation.json').write_text(result.stdout, encoding='utf-8')
        (output / 'stderr.log').write_text(result.stderr, encoding='utf-8')
        result.check_returncode()
        document = json.loads(result.stdout)
        evidence = document['evidence']
        observation = evidence['normalized_result']
        messages = [m.get('payload', {}) for m in observation['messages'] if m['type'] == 'send']
        if len(messages) != 4 or not all(
                m.get('kind') == 'mco-hook-canary' and m.get('arch') == 'ia32'
                and m.get('pointer_size') == 4 and m.get('output') == m.get('input', -100) + 7
                for m in messages):
            raise ValueError('missing or incorrect Windows x86 hook observations')
        if observation.get('cleanup_error') or document.get('cleanup_error'):
            raise ValueError('Frida detach/cleanup failed')
        summary = dict(windows_x86_hook_passed=True, observed_calls=len(messages),
                       evidence_id=evidence['evidence_id'],
                       source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                       script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                       executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
                       scope='owned canary only; not an MCO runtime observation')
        (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary, indent=2))
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)


if __name__ == '__main__':
    main()
