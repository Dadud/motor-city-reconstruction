"""Compare stock body flag calculation with complete original 0x52e880 calls."""
import argparse
from pathlib import Path
import struct

from client.assembly import (AVAILABLE_GROUPS, BodyComponentNameNode,
    normalize_body_component_names, stock_body_flags)
from client.fce import Model, Part
from tools.native_oracle import DynoOracle

NODE_SIZE = 0x33c
NODE_NAME = 0x22c
NODE_ATTACHMENT = 0x18
NODE_CLASS = 0x338
BODY_CLASS = 0x4e21


def _model_image(names):
    image = bytearray(0x2000)
    struct.pack_into('<I', image, 0x11c, len(names))
    for index, name in enumerate(names):
        encoded = name.encode('ascii')+b'\0'
        if len(encoded) > 0x40:
            raise ValueError('body FCE part name exceeds 64 bytes')
        start = 0xe28+index*0x40
        image[start:start+len(encoded)] = encoded
    return bytes(image)


def _groups(mask):
    return tuple(':H'+group for index, (group, _) in enumerate(AVAILABLE_GROUPS)
                 if mask & (1 << index))


def _cases():
    roof = lambda name: ((31001, name, 0),)
    yield (0x7ffff, roof('.chopped'), 'all body groups, ordered chopped roof')
    yield ((1 << 7) | 1, roof('.convert'), 'convertible roof option')
    yield ((1 << 5) | 1, roof('.vinyl'), 'vinyl roof option')
    yield (0x7ffff, (
        (31001, '.chopped', 0), (34001, 'leftMirror', 10),
        (34001, 'rightMirror', 11), (23001, 'boards', 0),
        (35001, 'bumper', 0), (21001, 'skirt', 0), (29001, 'chin', 0),
        (40001, '.large', 0), (17001, 'cage', 0), (340333, 'blower', 0)),
        'every table class, blower forced hole and mirror attachments')
    yield ((1 << 1) | 1, ((40001, '.large', 0),),
           'large scoop prefers the hood-plus-hole mask')
    yield ((1 << 2) | 1, ((40001, '.large', 0),),
           'large scoop falls to the hood-plus-large mask')
    yield ((1 << 3) | 1, ((40001, '.small', 0),),
           'small scoop maps to small scoop group')
    yield ((1 << 4) | 1, ((40001, '.factory', 0),),
           'factory scoop option')
    yield ((1 << 1) | 1, ((40001, '.unsupported', 0), (350001, 'scoop', 0)),
           'unsupported scoop rewrites to hood hole')
    yield ((1 << 1) | 1, ((40001, '.large', 0), (350001, 'scoop', 0),
                            (340333, 'blower', 0)),
           'blower forces hole ahead of accepted large scoop name')
    yield (1 << 8, (), 'mirror groups enabled by default')
    yield (0, (), 'body-only model selects default firewall')
    yield (1, (), 'hood availability with default firewall')
    yield ((1 << 5) | (1 << 6), ((31001, '.missing', 0),),
           'unavailable roof filename falls back to default roof')


def _node_image(address, following, model, component):
    image = bytearray([0xa5])*NODE_SIZE
    class_id, name, attachment = component
    encoded = name.encode('ascii')+b'\0'
    if len(encoded) >= NODE_NAME-4:
        raise ValueError('component name exceeds its owner node')
    struct.pack_into('<II', image, 0, following, model)
    struct.pack_into('<I', image, NODE_ATTACHMENT, attachment)
    image[NODE_NAME:NODE_NAME+len(encoded)] = encoded
    struct.pack_into('<I', image, NODE_CLASS, class_id)
    return bytes(image)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    owner = base+0x1000
    node_base = base+0x4000
    body_model = base+0x20000
    comparisons = 0
    for case_index, (group_mask, components, label) in enumerate(_cases()):
        group_names = _groups(group_mask)
        body_names = (':Hbody', ':Hheadlight')+group_names
        body_model_data = _model_image(body_names)
        model = Model(tuple(Part(name, (0, 0, 0), (), (), ())
                            for name in body_names), 0x101015)
        body_node = BodyComponentNameNode(BODY_CLASS, 'body')
        nodes = (body_node,)+tuple(BodyComponentNameNode(*item) for item in components)
        expected_flags = stock_body_flags(model, nodes)
        normalized = normalize_body_component_names(nodes)

        owner_image = bytearray([0x5a])*0x300
        struct.pack_into('<I', owner_image, 0x19c, node_base)
        cpu.mem_write(owner, bytes(owner_image))
        cpu.mem_write(body_model, body_model_data)
        images = []
        for index, component in enumerate(((BODY_CLASS, 'body', 0),)+components):
            address = node_base+index*0x400
            following = node_base+(index+1)*0x400 if index+1<len(nodes) else 0
            image = _node_image(address, following,
                                body_model if index == 0 else 0, component)
            images.append(image)
            cpu.mem_write(address, image)
        oracle.call(0x52e880, (), this_pointer=owner, instruction_limit=5_000_000)
        actual_flags, = struct.unpack('<I', cpu.mem_read(owner+0x22c, 4))
        if actual_flags != expected_flags:
            raise AssertionError((case_index, label, hex(actual_flags),
                                  hex(expected_flags), group_names, components))
        expected_owner = bytearray(owner_image)
        expected_owner[0x22c:0x230] = struct.pack('<I', expected_flags)
        actual_owner = bytes(cpu.mem_read(owner, len(owner_image)))
        if actual_owner != bytes(expected_owner):
            raise AssertionError((case_index, label, 'unexpected owner writes'))
        for index, (before, normalized_node) in enumerate(zip(images, normalized)):
            expected_node = bytearray(before)
            if normalized_node.name != nodes[index].name:
                encoded = normalized_node.name.encode('ascii')+b'\0'
                expected_node[NODE_NAME:NODE_NAME+len(encoded)] = encoded
            actual_node = bytes(cpu.mem_read(node_base+index*0x400, NODE_SIZE))
            if actual_node != bytes(expected_node):
                raise AssertionError((case_index, label, index,
                    actual_node[NODE_NAME:NODE_NAME+32],
                    bytes(expected_node)[NODE_NAME:NODE_NAME+32]))
        comparisons += 1
    return {'cases': comparisons, 'max_error': 0,
            'original_entry': '0x52e880',
            'scope': 'complete body-group scan, stock option table, node-name mutations, output flags and owner/node write boundaries'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    print(verify(parser.parse_args().executable))


if __name__ == '__main__':
    main()
