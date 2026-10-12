"""Write metadata only; never copy game payloads."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from viv import inventory


def catalog(root):
    files, archives, extensions = [], [], Counter()
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        extensions[path.suffix.lower()] += 1
        files.append(dict(path=relative, bytes=path.stat().st_size))
        if path.suffix.lower() == '.viv':
            try:
                archives.append(dict(path=relative, entries=inventory(path)))
            except (ValueError, OSError) as error:
                archives.append(dict(path=relative, error=str(error)))
    with (root / 'mcity.exe').open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(source=str(root.resolve()), client_sha256=digest,
                extensions=dict(extensions), files=files, archives=archives)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = catalog(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    failures = [a for a in result['archives'] if 'error' in a]
    print(f"{len(result['files'])} files; {len(result['archives'])} archives; {len(failures)} unsupported/invalid")
