"""Compare native BIGF/BIG4 directories against Python using external archives."""
import argparse
from pathlib import Path
import subprocess

from tools.viv import inventory


MAX_BYTES = 64 * 1024 * 1024


def compare(executable, archive):
    archive = Path(archive)
    if archive.stat().st_size > MAX_BYTES:
        raise ValueError(f'archive exceeds native comparison budget: {archive}')
    expected = inventory(archive)
    # Original bytes go directly to the local executable, never to a fixture.
    with archive.open('rb') as stream:
        result = subprocess.run([str(executable)], stdin=stream, capture_output=True,
                                check=True, timeout=30)
    actual = []
    for line in result.stdout.decode('ascii').splitlines():
        offset, size, encoded_name = line.split()
        actual.append(dict(offset=int(offset), size=int(size),
                           name=bytes.fromhex(encoded_name).decode('utf-8')))
    if actual != expected:
        raise RuntimeError(f'native/Python directory mismatch: {archive}')
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path, help='built mco_viv_compare executable')
    parser.add_argument('archive', nargs='?', type=Path)
    parser.add_argument('--root', type=Path, help='scan external installed .viv/.big archives')
    args = parser.parse_args()
    if (args.archive is None) == (args.root is None):
        parser.error('provide exactly one archive or --root')
    executable = args.executable.resolve(strict=True)
    if args.root is None:
        archives = [args.archive]
    else:
        if not args.root.is_dir():
            parser.error('--root must be an installed asset directory')
        archives = sorted((path for path in args.root.rglob('*')
                           if path.is_file() and path.suffix.lower() in ('.viv', '.big')),
                          key=lambda path: str(path).casefold())
        if not archives:
            parser.error('no .viv/.big archives found under --root')
    total = sum(compare(executable, archive) for archive in archives)
    print(f'{len(archives)} archives / {total} ordered entries match native/Python readers; '
          'member decoding and game behavior remain separate checks.')


if __name__ == '__main__':
    main()
