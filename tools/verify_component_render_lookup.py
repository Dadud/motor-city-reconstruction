"""Compare component-name selection with original 0x52e670 calls."""
import argparse
import struct
from types import SimpleNamespace

from client.fce import Part
from client.scene import select_component_part
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    node, model, listing = base+0x1000, base+0x10000, base+0x20000
    suffix, class_prefix = base+0x30000, base+0x30100
    out_model, out_index = base+0x30200, base+0x30204

    def run(names, option, prefix='LF'):
        image = bytearray(0x2038)
        struct.pack_into('<I', image, 0x11c, len(names))
        for index, name in enumerate(names):
            image[0xe28+index*0x40:0xe28+index*0x40+len(name)+1] = name.encode()+b'\0'
        cpu.mem_write(model, bytes(image))
        node_data = bytearray(0x33c)
        struct.pack_into('<II', node_data, 0, 0, model)
        struct.pack_into('<I', node_data, 0x18, {'LF':1,'RF':2,'LR':3,'RR':4}[prefix])
        cpu.mem_write(node, bytes(node_data))
        cpu.mem_write(listing, bytes(0x100))
        cpu.mem_write(listing, struct.pack('<I', 0))
        cpu.mem_write(suffix, b'tire\0')
        cpu.mem_write(class_prefix, prefix.encode()+b'\0')
        cpu.mem_write(out_model, bytes(8))
        oracle.call(0x52e670, (node, listing, suffix, class_prefix,
                              out_model, option, out_index), instruction_limit=20000)
        count = struct.unpack('<I', cpu.mem_read(listing, 4))[0]
        selected_model = struct.unpack('<I', cpu.mem_read(out_model, 4))[0]
        selected_index = struct.unpack('<I', cpu.mem_read(out_index, 4))[0]
        entry = cpu.mem_read(listing+4, 36) if count else bytes(36)
        expected = select_component_part(
            SimpleNamespace(parts=tuple(Part(name, (0,0,0), (), (), ()) for name in names)),
            'tire', option)
        assert count == (1 if expected else 0), (names, option, count, expected)
        if expected:
            part_index = names.index(expected.name)
            flags, = struct.unpack_from('<I', entry, 16)
            assert selected_model == model
            assert selected_index == 0
            native_part = struct.unpack_from('<H', entry, 12)[0]
            assert native_part == part_index, (names, option, native_part, part_index, entry.hex())
            assert struct.unpack_from('<I', entry, 4)[0] == model
            assert flags == ((1 << min(option, 3)) | (0x40 if prefix.startswith('R') else 0))
        return bool(expected)

    cases = [
        ((':PHtire',), 0, 'LF'),
        ((':PHtire', ':PTtire'), 3, 'RF'),
        ((':PHother',), 3, 'LR'),
        ((':PHtire', ':PTtire'), 2, 'RR'),
        ((':PHtire', ':PTtire'), 7, 'LF'),
    ]
    for case in cases:
        run(*case)
    return len(cases)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    args = parser.parse_args()
    print(f'component render lookup: {verify(args.executable)} exact original cases')


if __name__ == '__main__':
    main()
