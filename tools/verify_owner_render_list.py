"""Compare the complete body-only owner render-list path at 0x52dd70."""
import argparse
from pathlib import Path
import struct

from client.assembly import collect_body_render_records
from client.fce import Model, Part
from client.render_list import RenderRecord, build_render_list
from client.scene import (ComponentModelNode, collect_component_render_graph)
from tools.native_oracle import DynoOracle


def _model_image(names, origins=None, vertices=()):
    image = bytearray(0x4000)
    struct.pack_into('<I', image, 0x11c, len(names))
    origins = origins or ((0, 0, 0),) * len(names)
    if len(origins) != len(names):
        raise ValueError('part origin count must match part names')
    struct.pack_into('<I', image, 0x58, len(vertices))
    for index, name in enumerate(names):
        encoded = name.encode('ascii') + b'\0'
        if len(encoded) > 0x40:
            raise ValueError('FCE part name exceeds its fixed 64-byte slot')
        start = 0xe28 + index*0x40
        image[start:start+len(encoded)] = encoded
        struct.pack_into('<3f', image, 0x120+index*12, *origins[index])
    for index, vertex in enumerate(vertices):
        struct.pack_into('<3f', image, 0x5c+index*12, *vertex)
    return bytes(image)


def _apply_model_mutations(image, model):
    expected = bytearray(image)
    for index, part in enumerate(model.parts):
        struct.pack_into('<3f', expected, 0x120+index*12, *part.origin)
    vertices = tuple(vertex for part in model.parts for vertex in part.vertices)
    struct.pack_into('<I', expected, 0x58, len(vertices))
    for index, vertex in enumerate(vertices):
        struct.pack_into('<3f', expected, 0x5c+index*12, *vertex)
    return bytes(expected)


def verify(executable):
    import unicorn
    from unicorn import x86_const

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    owner, node = base+0x1000, base+0x2000
    model, allocation = base+0x10000, base+0x70000
    flags_cases = (0, 0x40000, 0x40000|0x20|0x800|0x1000,
                   0x40000|0x80|0x20000|0x400,
                   0x40000|0x40|0x10000|0x2000,
                   0x40000|0x1f|0x300|0x7800|0x20000)
    names = ('body', 'headlight', 'interior', 'dashlight', 'steer',
             'hood', 'hoodhole', 'scooplarge', 'scoopsmall', 'scoopfact',
             'top', 'shield', 'swin', 'convertible', 'topchop',
             'shieldchop', 'swinchop', 'cage', 'cagechop', 'bumper',
             'rmirror', 'lmirror', 'skirt', 'wheelwell', 'ffender',
             'fenderlight', 'rfender', 'boards', 'chin', 'firewall')
    prefixes = (':H', ':M', ':S', ':T')
    all_names = tuple(prefix+name for prefix in prefixes for name in names)
    native_model = Model(tuple(Part(name, (0, 0, 0), (), (), ())
                               for name in all_names), 0)
    image = _model_image(all_names)
    node_image = bytearray(0x400)
    struct.pack_into('<II', node_image, 0, 0, model)
    struct.pack_into('<I', node_image, 0x338, 0x4e21)
    owner_image = bytearray(0x300)
    struct.pack_into('<I', owner_image, 0x19c, node)

    requests = []
    def allocation_boundary(uc, address, _size, _user_data):
        esp = uc.reg_read(reg.UC_X86_REG_ESP)
        tag_ptr, size, _pool = struct.unpack('<III', uc.mem_read(esp, 12))
        if tag_ptr != 0x895e48:
            raise AssertionError(('allocator tag', hex(tag_ptr)))
        if size > 0x10000:
            raise AssertionError(('render allocation exceeds fixture', size))
        requests.append(size)
        uc.mem_write(allocation, bytes(size))
        uc.reg_write(reg.UC_X86_REG_EAX, allocation)
        # Replace only the external allocator call; resume immediately after
        # CALL with the same stack state its RET would have left.
        uc.reg_write(reg.UC_X86_REG_EIP, 0x52de31)

    hook = cpu.hook_add(unicorn.UC_HOOK_CODE, allocation_boundary,
                        begin=0x52de2c, end=0x52de2c)
    reports = []
    try:
        for lod in range(5):
            for flags in flags_cases:
                cpu.mem_write(owner, bytes(owner_image))
                cpu.mem_write(owner+0x22c, struct.pack('<I', flags))
                cpu.mem_write(node, bytes(node_image))
                cpu.mem_write(model, image)
                before = len(requests)
                oracle.call(0x52dd70, (lod,), this_pointer=owner, cleanup=b'',
                            instruction_limit=5_000_000)
                result = cpu.reg_read(x86_const.UC_X86_REG_EAX)
                expected_records = collect_body_render_records(
                    native_model, flags & (0xfffeffff if lod > 2 else 0xffffffff),
                    min(lod, 3), include_interior=(lod < 3))
                expected = build_render_list(expected_records).records
                if not expected:
                    if result != 0:
                        raise AssertionError(('empty-result', lod, hex(flags), hex(result)))
                    if len(requests) != before:
                        raise AssertionError(('unexpected-allocation', lod, hex(flags)))
                    reports.append((lod, flags, 0))
                    continue
                if result != allocation:
                    raise AssertionError(('result pointer', lod, hex(flags), hex(result)))
                if len(requests) != before+1:
                    raise AssertionError(('allocation count', lod, hex(flags), requests[before:]))
                count = len(expected)
                if requests[-1] != count*36:
                    raise AssertionError(('allocation size', lod, hex(flags), requests[-1], count*36))
                for index, record in enumerate(expected):
                    actual = struct.unpack('<9I', cpu.mem_read(allocation+index*36, 36))
                    next_pointer = allocation+(index+1)*36 if index+1<count else 0
                    wanted = list(record.words)
                    wanted[0] = next_pointer
                    wanted[1] = model
                    if actual != tuple(wanted):
                        raise AssertionError(('record', lod, hex(flags), index, actual, tuple(wanted)))
                reports.append((lod, flags, count))

        # Exercise the same owner entry with a generic component marker and a
        # nested right-side marker. The only replacement remains the allocator.
        body, foo, fog = base+0x10000, base+0x20000, base+0x30000
        root_node, fog_node, body_node = base+0x2000, base+0x2400, base+0x2800
        root_marker = Part(':PPLfoo', (20, 30, 40), (), (), ())
        body_model = Model((root_marker,), 0)
        foo_parts = (Part(':PHfoo', (2, 3, 4), ((8, 10, 12),), (), ()),
                     Part(':PPRfog', (4, 5, 6), ((3, 4, 5),), (), ()))
        fog_parts = (Part(':PHfog', (1, 2, 3), ((7, 8, 9),), (), ()),)
        foo_model, fog_model = Model(foo_parts, 0), Model(fog_parts, 0)
        body_image = _model_image((':PPLfoo',), ((20, 30, 40),))
        foo_image = _model_image(tuple(p.name for p in foo_parts),
            tuple(p.origin for p in foo_parts),
            tuple(v for p in foo_parts for v in p.vertices))
        fog_image = _model_image(tuple(p.name for p in fog_parts),
            tuple(p.origin for p in fog_parts),
            tuple(v for p in fog_parts for v in p.vertices))
        body_node_image = bytearray(0x400)
        struct.pack_into('<II', body_node_image, 0, 0, body)
        struct.pack_into('<I', body_node_image, 0x18, 0)
        struct.pack_into('<I', body_node_image, 0x338, 0x4e21)
        fog_node_image = bytearray(0x400)
        struct.pack_into('<II', fog_node_image, 0, body_node, fog)
        struct.pack_into('<I', fog_node_image, 0x18, 6)
        root_node_image = bytearray(0x400)
        struct.pack_into('<II', root_node_image, 0, fog_node, foo)
        struct.pack_into('<I', root_node_image, 0x18, 5)
        owner_image = bytearray(0x300)
        struct.pack_into('<I', owner_image, 0x19c, root_node)
        cpu.mem_write(owner, bytes(owner_image))
        cpu.mem_write(root_node, bytes(root_node_image))
        cpu.mem_write(fog_node, bytes(fog_node_image))
        cpu.mem_write(body_node, bytes(body_node_image))
        cpu.mem_write(body, body_image)
        cpu.mem_write(foo, foo_image)
        cpu.mem_write(fog, fog_image)
        nodes = (ComponentModelNode(5, foo_model, foo),
                 ComponentModelNode(6, fog_model, fog),
                 ComponentModelNode(0, body_model, body))
        expected_graph = collect_component_render_graph(body_model, nodes, 0)
        expected_records = build_render_list(tuple(entry.record
            for entry in expected_graph.entries)).records
        before = len(requests)
        oracle.call(0x52dd70, (0,), this_pointer=owner, cleanup=b'',
                    instruction_limit=5_000_000)
        result = cpu.reg_read(x86_const.UC_X86_REG_EAX)
        if result != allocation or len(expected_records) != 2:
            raise AssertionError(('recursive graph result', hex(result), expected_graph))
        if len(requests) != before+1 or requests[-1] != len(expected_records)*36:
            raise AssertionError(('recursive graph allocation', requests[before:]))
        for index, record in enumerate(expected_records):
            actual = struct.unpack('<9I', cpu.mem_read(allocation+index*36, 36))
            wanted = list(record.words)
            wanted[0] = allocation+(index+1)*36 if index+1<len(expected_records) else 0
            if actual != tuple(wanted):
                raise AssertionError(('recursive graph record', index, actual, tuple(wanted)))
        expected_foo = _apply_model_mutations(foo_image, expected_graph.models[0])
        expected_fog = _apply_model_mutations(fog_image, expected_graph.models[1])
        actual_foo = bytes(cpu.mem_read(foo, len(foo_image)))
        actual_fog = bytes(cpu.mem_read(fog, len(fog_image)))
        if actual_foo != expected_foo:
            raise AssertionError(('recursive foo FCE', actual_foo, expected_foo))
        if actual_fog != expected_fog:
            raise AssertionError(('recursive fog FCE', actual_fog, expected_fog))
        reports.append(('recursive-generic', 0, len(expected_records)))
    finally:
        cpu.hook_del(hook)
    return {'cases': len(reports), 'records': sum(item[2] for item in reports),
            'max_error': 0, 'original_entry': '0x52dd70',
            'scope': '30 body-only owner profiles plus one recursive generic component graph; compares native owner lookup, body collection, generic class lookup, nested transforms, output records, allocator boundary, stable sort and links'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
