"""Compare portable render-group selection with original 0x52db70 calls."""
import argparse
from pathlib import Path
import struct

from client.assembly import collect_render_group
from client.fce import Model, Part
from tools.native_oracle import DynoOracle


def _model_image(names):
    image = bytearray(0x1200)
    struct.pack_into('<I', image, 0x11c, len(names))
    for index, name in enumerate(names):
        encoded = name.encode('ascii') + b'\0'
        if len(encoded) > 0x40:
            raise ValueError('native FCE part name exceeds its 64-byte slot')
        image[0xe28+index*0x40:0xe28+index*0x40+len(encoded)] = encoded
    return bytes(image)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    node_base, model_base = base+0x1000, base+0x10000
    render, group_addr, out_model = base+0x30000, base+0x40000, base+0x50000
    cases = (
        ((':Hdoor', ':Mdoor'), (':Hdoor',), 'door', 0, 0, 0),
        ((':Hdoor', ':Mdoor'), (':Hdoor',), 'door', 1, 0x100, 7),
        ((':Hother',), (':Mdoor',), 'door', 3, 0x80, 0x13),
        ((':Sdoor',), (':Tdoor',), 'door', 2, 0, 1),
        ((':Hdoor-extra',), (), 'door', 0, 0, 2),
        ((), (':Hdoor',), 'door', 0, 0, 3),
        ((':Mdoor',), (':Hdoor',), 'door', 1, 0x180, 0x12),
        ((':Hdoor',), (':Hdoor',), 'missing', 3, 0, 4),
    )
    for case_index, (first_names, second_names, group, lod, flags, mesh_type) in enumerate(cases):
        models = [Model(tuple(Part(name, (0, 0, 0), (), (), ())
                              for name in names), 0)
                  for names in (first_names, second_names)]
        images = [_model_image(names) for names in (first_names, second_names)]
        first_node, second_node = node_base, node_base+0x100
        first_model, second_model = model_base, model_base+0x2000
        cpu.mem_write(first_node, struct.pack('<II', second_node, first_model))
        cpu.mem_write(second_node, struct.pack('<II', 0, second_model))
        cpu.mem_write(first_model, images[0])
        cpu.mem_write(second_model, images[1])
        cpu.mem_write(render, bytes(0x2000))
        cpu.mem_write(out_model, struct.pack('<I', 0xffffffff))
        cpu.mem_write(group_addr, group.encode('ascii')+b'\0')
        oracle.call(0x52db70,
                    (first_node, render, group_addr, out_model, lod, flags, mesh_type),
                    instruction_limit=300_000)
        result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        count, = struct.unpack('<I', cpu.mem_read(render, 4))
        out_pointer, = struct.unpack('<I', cpu.mem_read(out_model, 4))
        record = bytes(cpu.mem_read(render+4, 36))
        expected = collect_render_group(models, group, lod, flags, mesh_type)
        if expected is None:
            if result != 0xffffffff or count != 0 or out_pointer != 0:
                raise AssertionError((case_index, result, count, out_pointer))
            continue
        selected_model = (first_model, second_model)[expected.words[1]]
        part_index, = struct.unpack_from('<H', record, 12)
        observed = (count, out_pointer, result, part_index,
                    struct.unpack_from('<I', record, 16)[0],
                    struct.unpack_from('<I', record, 20)[0])
        wanted = (1, selected_model, expected.words[3], expected.words[3],
                  expected.words[4], expected.words[5])
        if observed != wanted:
            raise AssertionError((case_index, observed, wanted))
    return {'cases': len(cases), 'max_error': 0,
            'original_entry': '0x52db70',
            'scope': 'synthetic linked FCE model lists, exact LOD fallback, model order, record fields and misses'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    print(verify(args.executable))


if __name__ == '__main__':
    main()
