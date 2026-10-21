"""Compare the 0x52d710 ordered body-group collector with original calls."""
import argparse
from pathlib import Path
import struct

from client.assembly import collect_body_render_records
from client.fce import Model, Part
from tools.native_oracle import DynoOracle

GROUPS = ('body', 'headlight', 'interior', 'dashlight', 'steer', 'hood',
          'hoodhole', 'scooplarge', 'scoopsmall', 'scoopfact', 'top', 'shield',
          'swin', 'convertible', 'topchop', 'shieldchop', 'swinchop', 'cage',
          'cagechop', 'bumper', 'rmirror', 'lmirror', 'skirt', 'wheelwell',
          'ffender', 'fenderlight', 'rfender', 'boards', 'chin', 'firewall')
PREFIXES = (':H', ':M', ':S', ':T')


def _image(names):
    data = bytearray(0x4000)
    struct.pack_into('<I', data, 0x11c, len(names))
    for index, name in enumerate(names):
        encoded = name.encode('ascii')+b'\0'
        if len(encoded) > 0x40:
            raise ValueError('part name too long')
        data[0xe28+index*0x40:0xe28+index*0x40+len(encoded)] = encoded
    return bytes(data)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    model, records = base+0x10000, base+0x30000
    all_names = tuple(prefix+group for prefix in PREFIXES for group in GROUPS)
    native_model = Model(tuple(Part(name, (0, 0, 0), (), (), ())
                               for name in all_names), 0)
    data = _image(all_names)
    cases = ((0, 0, True), (0x40000, 0, True),
             (0x40000|0x20|0x800|0x1000, 1, True),
             (0x40000|0x80|0x20000|0x400, 2, True),
             (0x40000|0x40|0x10000|0x2000, 3, False),
             (0x40000|0x1f|0x300|0x7800|0x20000, 4, False))
    total_records = 0
    for case_index, (flags, lod, interior) in enumerate(cases):
        cpu.mem_write(model, data)
        cpu.mem_write(records, bytes(0x10000))
        oracle.call(0x52d710, (model, flags, records, lod, int(interior)),
                    instruction_limit=2_000_000)
        count, = struct.unpack('<I', cpu.mem_read(records, 4))
        expected = collect_body_render_records(native_model, flags, lod, interior)
        if count != len(expected):
            raise AssertionError((case_index, count, len(expected)))
        for index, item in enumerate(expected):
            address = records+4+index*36
            observed = bytes(cpu.mem_read(address, 36))
            words = struct.unpack('<9I', observed)
            part_index, = struct.unpack_from('<H', observed, 12)
            wanted_link = address+36 if index+1 < len(expected) else 0
            wanted = (wanted_link, model, 0, item.words[3],
                      item.words[4], item.words[5])
            actual = (words[0], words[1], words[2], part_index,
                      words[4], words[5])
            if actual != wanted:
                raise AssertionError((case_index, index, actual, wanted))
        total_records += count
    return {'cases': len(cases), 'records': total_records, 'max_error': 0,
            'original_entry': '0x52d710',
            'scope': 'complete ordered body-group call sequence and records for six synthetic flag/LOD profiles'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
