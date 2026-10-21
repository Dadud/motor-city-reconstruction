"""Compare 0x52e880 owner-node name rewrites with original execution."""
import argparse
from pathlib import Path
import struct

from client.assembly import BodyComponentNameNode, normalize_body_component_names
from tools.native_oracle import DynoOracle

NODE_SIZE = 0x33c
NAME_OFFSET = 0x22c
CLASS_OFFSET = 0x338


def _cases():
    yield ((40001, '.large'), (340333, 'blower'), (1001, 'suspension'))
    yield ((40001, '.unsupported'), (340333, ''), (350001, 'scoop'))
    yield ((40001, '.factory'), (340333, ''), (350001, 'scoop'))
    yield ((40001, '.large'), (340333, ''), (350001, 'scoop'))
    yield ((40001, '.small'), (350001, 'scoop'))
    yield ((40001, '.unsupported'),)
    yield ((40001, '.large'), (40001, '.small'), (340333, 'blower'),
           (1001, 'first'), (1001, 'second'))
    yield ()


def _node_image(address, following, class_id, name):
    if len(name.encode('ascii')) >= NAME_OFFSET-4:
        raise ValueError('node name exceeds its native field')
    image = bytearray([0xa5])*NODE_SIZE
    struct.pack_into('<II', image, 0, following, 0)
    encoded = name.encode('ascii')+b'\0'
    image[NAME_OFFSET:NAME_OFFSET+len(encoded)] = encoded
    struct.pack_into('<I', image, CLASS_OFFSET, class_id)
    return bytes(image)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    owner = base+0x1000
    nodes_base = base+0x4000
    cases = tuple(_cases())
    mutation_count = 0
    for case_index, definitions in enumerate(cases):
        cpu.mem_write(owner, bytes([0x5a])*0x300)
        node_images = []
        normalized = normalize_body_component_names(
            tuple(BodyComponentNameNode(class_id, name)
                  for class_id, name in definitions))
        for index, (class_id, name) in enumerate(definitions):
            address = nodes_base+index*0x400
            following = nodes_base+(index+1)*0x400 if index+1<len(definitions) else 0
            image = _node_image(address, following, class_id, name)
            node_images.append(image)
            cpu.mem_write(address, image)
        head = nodes_base if definitions else 0
        cpu.mem_write(owner+0x19c, struct.pack('<I', head))
        oracle.call(0x52e880, (), this_pointer=owner, instruction_limit=1_000_000)

        flags, = struct.unpack('<I', cpu.mem_read(owner+0x22c, 4))
        if flags != 0x10000:
            raise AssertionError((case_index, 'flags', hex(flags)))
        for index, (before, after) in enumerate(zip(node_images, normalized)):
            actual = bytes(cpu.mem_read(nodes_base+index*0x400, NODE_SIZE))
            expected = bytearray(before)
            if after.name != definitions[index][1]:
                encoded = after.name.encode('ascii')+b'\0'
                expected[NAME_OFFSET:NAME_OFFSET+len(encoded)] = encoded
                mutation_count += 1
            if actual != bytes(expected):
                raise AssertionError((case_index, index, actual[NAME_OFFSET:NAME_OFFSET+32],
                                      bytes(expected)[NAME_OFFSET:NAME_OFFSET+32]))
    return {'cases': len(cases), 'rewritten_nodes': mutation_count,
            'max_error': 0, 'original_entry': '0x52e880',
            'scope': 'bodyless synthetic owner lists; exact name writes, untouched node bytes and firewall-only output flag'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
