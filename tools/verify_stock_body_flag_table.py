"""Compare the extracted stock-body option table with mcity 0x895568."""
import argparse
import hashlib
from pathlib import Path
import struct

from client.assembly import CONFIGURATION

TARGET_SHA256 = '28c0cdde77ed24bac6aeeea65699c16be0f31e6aa8cb5db38417f0f3d5880164'
TABLE_ADDRESS = 0x895568


def _image(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != TARGET_SHA256:
        raise ValueError('stock body table target SHA-256 mismatch')
    pe_offset, = struct.unpack_from('<I', data, 0x3c)
    if data[pe_offset:pe_offset+4] != b'PE\0\0':
        raise ValueError('PE signature missing')
    count, = struct.unpack_from('<H', data, pe_offset+6)
    optional_size, = struct.unpack_from('<H', data, pe_offset+20)
    optional = pe_offset+24
    if struct.unpack_from('<H', data, optional)[0] != 0x10b:
        raise ValueError('expected a PE32 image')
    image_base, = struct.unpack_from('<I', data, optional+28)
    sections = []
    for index in range(count):
        header = optional+optional_size+index*40
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            '<IIII', data, header+8)
        sections.append((virtual_address, virtual_size, raw_size, raw_offset))

    def offset(address, size):
        rva = address-image_base
        for virtual_address, virtual_size, raw_size, raw_offset in sections:
            if virtual_address <= rva < virtual_address+max(virtual_size, raw_size):
                delta = rva-virtual_address
                if delta+size > raw_size:
                    break
                return raw_offset+delta
        raise ValueError(f'unmapped or uninitialized VA: {address:#x}')

    def read(address, fmt):
        return struct.unpack_from(fmt, data, offset(address, struct.calcsize(fmt)))

    def c_string(address):
        start = offset(address, 1)
        end = data.find(b'\0', start)
        if end < 0:
            raise ValueError(f'unterminated option name at {address:#x}')
        return data[start:end].decode('ascii')

    recovered = []
    for index in range(32):
        record = TABLE_ADDRESS+index*12
        class_id, attachment_id, options = read(record, '<III')
        if options == 0:
            break
        candidates = []
        for option_index in range(32):
            name_address, required_flags = read(options+option_index*8, '<II')
            if name_address == 0:
                break
            candidates.append((c_string(name_address), required_flags))
        else:
            raise ValueError(f'option table at {options:#x} lacks a terminator')
        recovered.append((class_id, attachment_id, tuple(candidates)))
    else:
        raise ValueError('stock-body table lacks a terminator')
    return tuple(recovered)


def verify(path):
    actual = _image(path)
    expected = tuple((class_id, attachment_id, options)
                     for class_id, attachment_id, options in CONFIGURATION)
    if actual != expected:
        raise AssertionError({'original': actual, 'implementation': expected})
    return {'records': len(actual), 'options': sum(map(lambda row: len(row[2]), actual)),
            'table_address': hex(TABLE_ADDRESS), 'target_sha256': TARGET_SHA256}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
