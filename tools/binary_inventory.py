"""Record identities of installed EXE/DLL files without copying them."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from tools.function_inventory import TARGET


def executable_format(path):
    with path.open('rb') as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:2] != b'MZ':
            return 'unrecognized-data'
        offset = struct.unpack_from('<I', header, 60)[0]
        stream.seek(offset)
        signature = stream.read(4)
        if signature == b'PE\0\0':
            return 'pe'
        if signature[:2] in (b'NE', b'LE', b'LX'):
            return signature[:2].decode().lower()
        return 'dos-mz'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game_root', type=Path)
    parser.add_argument('--top-level', action='store_true', help='omit nested binaries')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    entries = []
    paths = args.game_root.iterdir() if args.top_level else args.game_root.rglob('*')
    for path in sorted(paths, key=lambda p: p.as_posix().lower()):
        if path.is_symlink() or not path.is_file():
            continue
        format_name = executable_format(path)
        if path.suffix.lower() not in ('.exe', '.dll') and format_name not in ('pe','ne','le','lx'):
            continue
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        entries.append(dict(name=path.relative_to(args.game_root).as_posix(), bytes=path.stat().st_size, sha256=digest,
            format=format_name,
            location_role=('historical-cache' if '.castanet/undo/' in path.as_posix().lower() else 'installation'),
            function_inventory='function-enumeration.json' if digest == TARGET else None,
            status=('not-native-executable' if format_name == 'unrecognized-data' else
                    'enumerated' if digest == TARGET else 'function-enumeration-pending')))
    if not any(entry['sha256'] == TARGET for entry in entries):
        parser.error('the verified mcity.exe was not found in this folder')
    payload = dict(scope=('top-level' if args.top_level else 'recursive') +
                   ' header-discovered PE/NE/LE/LX files plus EXE/DLL filename candidates; '
                   'symlinks and system libraries outside installation not inventoried',
                   binaries=entries)
    destination = root/'docs/recovery/binary-scope.json'
    destination.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    print(f'Recorded {len(entries)} binary identities; original files remain external.')


if __name__ == '__main__':
    main()
