"""Compare 0x52e880 against installed stock body assets and catalogue assemblies.

Each supported stock vehicle is represented as the direct native linked-node
shape consumed by the routine. Missing local VIV archives and malformed stock
body definitions are reported separately; they are not counted as comparisons.
"""
import argparse
from pathlib import Path
import struct

from client.assembly import BodyComponentNameNode, normalize_body_component_names, stock_body_flags
from client.assets import Assets
from client.catalogue import Catalogue
from client.fce import decode
from tools.native_oracle import DynoOracle
from tools.viv import read_member

NODE_SIZE = 0x33c
NODE_STRIDE = 0x400
NODE_NAME = 0x22c
NODE_ATTACHMENT = 0x18
NODE_CLASS = 0x338
BODY_CLASS = 20001


def verify(executable, data_root):
    assets = Assets(data_root)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    base = 0x74000000
    cpu.mem_map(base, 0x400000)
    owner = base + 0x1000
    node_base = base + 0x4000
    body_model = base + 0x40000
    passed = []
    missing = []
    invalid = []

    for vehicle_id in sorted(catalogue.vehicles):
        vehicle = catalogue.vehicle(vehicle_id)
        try:
            body_filename = vehicle.body_filename
            archive_key = ('data/models/' + body_filename + '.viv').casefold()
            archive = assets.paths[archive_key]
        except (KeyError, ValueError) as error:
            record = (vehicle_id, vehicle.name, str(error))
            (missing if isinstance(error, KeyError) else invalid).append(record)
            continue

        body_bytes = read_member(archive, 'part.fce')
        body_model_data = decode(body_bytes)
        if len(body_bytes) > 0x400000 - 0x40000:
            raise ValueError(f'{vehicle_id}: body FCE exceeds verifier memory region')
        components = (BodyComponentNameNode(BODY_CLASS, 'body'),) + tuple(
            BodyComponentNameNode(part.abstract_type_id, part.filename or '',
                                  part.attachment_id)
            for part in vehicle.parts)
        normalized = normalize_body_component_names(components)
        owner_image = bytearray([0x5a]) * 0x300
        owner_image[0x19c:0x1a0] = struct.pack('<I', node_base)
        cpu.mem_write(owner, bytes(owner_image))
        cpu.mem_write(owner + 0x19c, struct.pack('<I', node_base))
        cpu.mem_write(body_model, body_bytes)

        expected_nodes = []
        for index, (part, before) in enumerate(zip((None,) + vehicle.parts,
                                                   components)):
            address = node_base + index * NODE_STRIDE
            following = (node_base + (index + 1) * NODE_STRIDE
                         if index + 1 < len(components) else 0)
            image = bytearray([0xa5]) * NODE_SIZE
            struct.pack_into('<II', image, 0, following,
                             body_model if index == 0 else 0)
            struct.pack_into('<I', image, NODE_ATTACHMENT,
                             0 if part is None else part.attachment_id)
            encoded = before.name.encode('ascii') + b'\0'
            image[NODE_NAME:NODE_NAME + len(encoded)] = encoded
            struct.pack_into('<I', image, NODE_CLASS, before.class_id)
            cpu.mem_write(address, bytes(image))
            expected = bytearray(image)
            expected_encoded = normalized[index].name.encode('ascii') + b'\0'
            expected[NODE_NAME:NODE_NAME + len(expected_encoded)] = expected_encoded
            expected_nodes.append(bytes(expected))

        expected_flags = stock_body_flags(body_model_data, vehicle.parts)
        oracle.call(0x52e880, (), this_pointer=owner,
                    instruction_limit=5_000_000)
        actual_flags, = struct.unpack('<I', cpu.mem_read(owner + 0x22c, 4))
        if actual_flags != expected_flags:
            raise AssertionError((vehicle_id, vehicle.name,
                                  hex(actual_flags), hex(expected_flags)))
        owner_image[0x22c:0x230] = struct.pack('<I', expected_flags)
        actual_owner = bytes(cpu.mem_read(owner, len(owner_image)))
        if actual_owner != bytes(owner_image):
            changed = [offset for offset, (actual, expected) in
                       enumerate(zip(actual_owner, owner_image)) if actual != expected]
            raise AssertionError((vehicle_id, vehicle.name, 'unexpected owner writes',
                                  changed[:24]))
        for index, expected_node in enumerate(expected_nodes):
            address = node_base + index * NODE_STRIDE
            actual = bytes(cpu.mem_read(address, NODE_SIZE))
            if actual != expected_node:
                raise AssertionError((vehicle_id, index, 'unexpected node writes'))
        passed.append(vehicle_id)

    return {'compared': len(passed), 'catalogue_vehicles': len(catalogue.vehicles),
            'missing_archives': missing, 'invalid_body_definitions': invalid,
            'original_entry': '0x52e880', 'max_error': 0,
            'scope': 'installed stock body FCEs and catalogue component identities in a direct native linked-node fixture; flags and name rewrites compared'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('data_root', type=Path)
    args = parser.parse_args()
    result = verify(args.executable, args.data_root)
    print(result)


if __name__ == '__main__':
    main()
