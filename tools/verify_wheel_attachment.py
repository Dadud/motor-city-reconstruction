"""Compare all four special wheel-marker branches of original 0x52df00."""
import argparse
import struct
from pathlib import Path

from client.fce import Model, Part
from client.scene import ComponentModelNode, collect_component_render_graph
from tools.native_oracle import DynoOracle


def _model(names, origins):
    image = bytearray(0x3000)
    struct.pack_into('<I', image, 0x11c, len(names))
    for index, (name, origin) in enumerate(zip(names, origins)):
        encoded = name.encode('ascii') + b'\0'
        image[0xe28 + index * 0x40:0xe28 + index * 0x40 + len(encoded)] = encoded
        struct.pack_into('<3f', image, 0x120 + index * 12, *origin)
    return image


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    body, node, component, output = (base + offset for offset in
                                     (0x10000, 0x2000, 0x30000, 0x50000))
    marker_origin = (12.5, -7.25, 3.0)
    names = (':PHtire', ':PHhubcap')
    origins = ((1.0, 2.0, 3.0), (-4.0, 5.0, 6.0))
    corner_indices = {'LF': 1, 'RF': 2, 'LR': 3, 'RR': 4}
    reports = []
    for corner, class_index in corner_indices.items():
        for lod in range(4):
            body_image = _model((':PP' + corner + 'wheel',), (marker_origin,))
            component_image = _model(names, origins)
            cpu.mem_write(body, bytes(body_image))
            cpu.mem_write(component, bytes(component_image))
            node_image = bytearray(0x400)
            struct.pack_into('<II', node_image, 0, 0, component)
            struct.pack_into('<I', node_image, 0x18, class_index)
            cpu.mem_write(node, bytes(node_image))
            cpu.mem_write(output, bytes(0x4000))
            oracle.call(0x52df00, (body, node, output, lod, 0),
                        instruction_limit=1_000_000)
            count, = struct.unpack('<I', cpu.mem_read(output, 4))
            if count != 2:
                raise AssertionError((corner, lod, 'record count', count))
            native = tuple(struct.unpack('<9I', cpu.mem_read(output + 4 + i * 36, 36))
                           for i in range(count))
            portable = collect_component_render_graph(
                Model((Part(':PP' + corner + 'wheel', marker_origin, (), (), ()),), 0),
                (ComponentModelNode(class_index, Model(tuple(
                    Part(name, origin, (), (), ()) for name, origin in zip(names, origins)), 0),
                    component),), lod)
            expected = tuple(entry.record.words for entry in portable.entries)
            for i, (actual, wanted) in enumerate(zip(native, expected)):
                adjusted = list(wanted)
                adjusted[0] = output + 4 + (i + 1) * 36 if i + 1 < count else 0
                if actual != tuple(adjusted):
                    raise AssertionError((corner, lod, i, actual, tuple(adjusted)))
            native_origins = tuple(struct.unpack('<3f', cpu.mem_read(component + 0x120 + i * 12, 12))
                                   for i in range(2))
            if native_origins != (marker_origin, marker_origin):
                raise AssertionError((corner, lod, 'part origins', native_origins))
            if tuple(entry.record.words[5] for entry in portable.entries) != (
                    {'LF': 8, 'RF': 9, 'LR': 11, 'RR': 10}[corner],
                    {'LF': 4, 'RF': 5, 'LR': 7, 'RR': 6}[corner]):
                raise AssertionError((corner, lod, 'portable mesh mapping'))
            reports.append((corner, lod, count))
    return {'cases': len(reports), 'records': sum(case[2] for case in reports),
            'max_error': 0, 'original_entry': '0x52df00',
            'scope': 'LF/RF/LR/RR wheel markers, tire/hubcap lookup, four LODs, native flags/types, and both selected FCE origins'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
