"""Record identities of top-level installed EXE/DLL files without copying them."""
import argparse
import hashlib
import json
from pathlib import Path
from tools.function_inventory import TARGET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_root', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    entries = []
    for path in sorted(args.game_root.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or path.suffix.lower() not in ('.exe', '.dll'):
            continue
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        entries.append(dict(name=path.name, bytes=path.stat().st_size, sha256=digest,
            function_inventory='function-enumeration.json' if digest == TARGET else None,
            status='enumerated' if digest == TARGET else 'function-enumeration-pending'))
    if not any(entry['sha256'] == TARGET for entry in entries):
        parser.error('the verified mcity.exe was not found in this folder')
    payload = dict(scope='top-level EXE/DLL files only; nested binaries and system libraries not inventoried',
                   binaries=entries)
    destination = root/'docs/recovery/binary-scope.json'
    destination.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    print(f'Recorded {len(entries)} binary identities; original files remain external.')


if __name__ == '__main__':
    main()
