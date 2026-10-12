"""EA BIGF/BIG4 archive directory reader; does not decode member contents."""
import argparse
import json
import struct
from pathlib import Path


def inventory(path):
    path = Path(path)
    actual = path.stat().st_size
    with path.open('rb') as stream:
        header = stream.read(16)
        if len(header) != 16:
            raise ValueError('truncated header')
        magic, size, count, end = struct.unpack('>4sIII', header)
        if magic not in (b'BIGF', b'BIG4'):
            raise ValueError(f'unsupported signature {magic!r}')
        if size != actual or not 16 <= end <= actual:
            raise ValueError('invalid archive or directory size')
        if count > (end - 16) // 9:
            raise ValueError('invalid entry count')
        directory = stream.read(end - 16)
    cursor, entries, names = 0, [], set()
    for _ in range(count):
        if cursor + 8 > len(directory):
            raise ValueError('truncated entry')
        offset, length = struct.unpack_from('>II', directory, cursor)
        cursor += 8
        terminator = directory.find(b'\0', cursor)
        if terminator < 0:
            raise ValueError('unterminated name')
        name = directory[cursor:terminator].decode('latin-1')
        cursor = terminator + 1
        if not name or name in names:
            raise ValueError('empty or duplicate name')
        if offset < end or offset + length > actual:
            raise ValueError(f'invalid payload bounds: {name}')
        names.add(name)
        entries.append(dict(name=name, offset=offset, size=length))
    ranges = sorted((e['offset'], e['offset'] + e['size']) for e in entries if e['size'])
    if any(b[0] < a[1] for a, b in zip(ranges, ranges[1:])):
        raise ValueError('overlapping payloads')
    return entries


def read_member(path, name, max_bytes=64 * 1024 * 1024):
    entry = next((e for e in inventory(path) if e['name'] == name), None)
    if entry is None:
        raise KeyError(name)
    if entry['size'] > max_bytes:
        raise ValueError('member exceeds read budget')
    with Path(path).open('rb') as stream:
        stream.seek(entry['offset'])
        data = stream.read(entry['size'])
    if len(data) != entry['size']:
        raise ValueError('archive changed during read')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    print(json.dumps(inventory(args.archive), indent=2))
