"""Compare installed Ford stock mechanical records through owner-list creation."""
import argparse
import struct

from client.assets import Assets
from client.catalogue import Catalogue
from client.mechanical_parts import expand_mechanical_parts
from client.model_owner import build_stock_component_node_list
from tools.inspect_stock_mechanical import stock_slots
from tools.native_oracle import DynoOracle
from tools.verify_component_node_list import OWNER_SIZE, NODE_SIZE
from tools.verify_mechanical_presentation import _initialize_model_prefix


def verify(executable, game_root, vehicle_id=101):
    import unicorn

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    prefix = _initialize_model_prefix(oracle, game_root)
    assets = Assets(game_root)
    catalogue = Catalogue.load(assets.paths['data/db/online.mdb'])
    slots = stock_slots(catalogue, vehicle_id, percent_damage=0, item_wear=0)
    part_count = len(expand_mechanical_parts(slots, model_prefix=prefix))
    base = 0x74000000
    allocation_base = base + 0x70000
    allocation_stride = 0x1000
    driver_address = allocation_base + part_count * allocation_stride
    expected_parts = build_stock_component_node_list(
        slots, tuple(0x74070000 + i * 0x1000 for i in range(part_count)),
        lambda kind, attachment: 0x73000000 + kind * 0x10 + attachment,
        model_prefix=prefix, driver_node_address=driver_address)
    # The helper inserts records in tPartInfo order but nodes are prepended.
    ordered_node_addresses = tuple(node.address for node in reversed(
        expected_parts.component_nodes.nodes))
    count = len(expected_parts.mechanical_parts)

    cpu.mem_map(base, 0x200000)
    source = base + 0x10000
    records = base + 0x30000
    vehicle_index = base + 0x58000
    owner = base + 0x60000
    if count > 100:
        raise AssertionError(('unexpectedly many mechanical nodes', count))
    cpu.mem_write(source, b''.join(slots))
    cpu.mem_write(records, bytes(count * NODE_SIZE))
    cpu.mem_write(vehicle_index, struct.pack('<i', -1))
    oracle.call(0x52c550, (records, source, len(slots), vehicle_index),
                instruction_limit=1_000_000)
    returned_record_count = cpu.reg_read(reg.UC_X86_REG_EAX)

    for index, part in enumerate(expected_parts.mechanical_parts):
        actual = bytes(cpu.mem_read(records + index * NODE_SIZE, NODE_SIZE))
        expected = bytearray(part.image)
        following = records + (index + 1) * NODE_SIZE if index + 1 < count else 0
        struct.pack_into('<I', expected, 0, following)
        if actual != expected:
            offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
            raise AssertionError(('0x52c550 full record', index, hex(offset),
                                  actual[offset:offset + 16], expected[offset:offset + 16]))

    actual_vehicle_index, = struct.unpack('<i', cpu.mem_read(vehicle_index, 4))
    if returned_record_count != part_count:
        raise AssertionError(('expanded record count', returned_record_count, part_count))
    # This selector field is a loader-specific auxiliary index, and stock
    # catalogue product IDs are not the sentinel 0x65 used by the synthetic
    # pairing cases. Preserve the original output as evidence without treating
    # it as part of the node-list comparison.

    allocation_index = 0
    lookup_calls = []
    free_calls = []

    def intercept(uc, address, _size, _user_data):
        nonlocal allocation_index
        if address not in (0x6ee530, 0x528a70, 0x6ee550):
            return
        esp = uc.reg_read(reg.UC_X86_REG_ESP)
        return_address, = struct.unpack('<I', uc.mem_read(esp, 4))
        if address == 0x6ee530:
            _, size, _pool = struct.unpack('<III', uc.mem_read(esp + 4, 12))
            if size != NODE_SIZE:
                raise AssertionError(('allocation size', size))
            uc.reg_write(reg.UC_X86_REG_EAX,
                         allocation_base + allocation_index * allocation_stride)
            allocation_index += 1
        elif address == 0x528a70:
            kind, attachment = struct.unpack('<II', uc.mem_read(esp + 4, 8))
            lookup_calls.append((kind, attachment))
            uc.reg_write(reg.UC_X86_REG_EAX,
                         0x73000000 + kind * 0x10 + attachment)
        else:
            pointer, = struct.unpack('<I', uc.mem_read(esp + 4, 4))
            free_calls.append(pointer)
            uc.reg_write(reg.UC_X86_REG_EAX, 0)
        uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
        uc.reg_write(reg.UC_X86_REG_EIP, return_address)

    hook = cpu.hook_add(unicorn.UC_HOOK_CODE, intercept)
    try:
        owner_image = bytes((i * 13 + 9) & 0xff for i in range(OWNER_SIZE))
        owner_image = bytearray(owner_image)
        struct.pack_into('<I', owner_image, 0x40, 0)
        struct.pack_into('<I', owner_image, 0x19c, 0)
        cpu.mem_write(owner, bytes(owner_image))
        result = oracle.call(0x52add0, (owner, records, count),
                             instruction_limit=1_000_000)
        if cpu.reg_read(reg.UC_X86_REG_EAX) != owner:
            raise AssertionError('0x52add0 returned unexpected owner pointer')
        actual_owner = bytes(cpu.mem_read(owner, OWNER_SIZE))
        expected_owner = bytearray(owner_image)
        struct.pack_into('<I', expected_owner, 0x40, count)
        mechanical_head = expected_parts.component_nodes.nodes[count - 1].address
        struct.pack_into('<I', expected_owner, 0x19c, mechanical_head)
        if actual_owner != bytes(expected_owner):
            raise AssertionError('0x52add0 owner image differs')
        # The stock worker calls this fallback when its mechanical list has no
        # driver-class node. It prepends a fully initialized default Driver.
        oracle.call(0x52c190, this_pointer=owner, instruction_limit=20_000)
        expected_owner = bytearray(expected_owner)
        struct.pack_into('<I', expected_owner, 0x40, expected_parts.count)
        struct.pack_into('<I', expected_owner, 0x19c, expected_parts.head)
        actual_owner = bytes(cpu.mem_read(owner, OWNER_SIZE))
        if actual_owner != bytes(expected_owner):
            raise AssertionError('0x52c190 owner image differs')
        for expected_node in expected_parts.component_nodes.nodes:
            actual = bytes(cpu.mem_read(expected_node.address, NODE_SIZE))
            if actual != expected_node.image:
                offset = next(i for i, (a, b) in enumerate(zip(actual, expected_node.image))
                              if a != b)
                raise AssertionError(('0x52add0 full node', hex(expected_node.address),
                                      hex(offset), actual[offset:offset + 16],
                                      expected_node.image[offset:offset + 16]))
        expected_lookups = [(
            struct.unpack_from('<I', part.image, 0x338)[0],
            struct.unpack_from('<I', part.image, 0x18)[0])
            for part in expected_parts.mechanical_parts]
        expected_lookups.append((0x80e9, 0))
        if lookup_calls != expected_lookups or free_calls:
            raise AssertionError(('lookup/free calls', lookup_calls, free_calls))
    finally:
        cpu.hook_del(hook)

    return {'vehicle_id': vehicle_id, 'stock_slots': len(slots),
            'expanded_records': count, 'owner_nodes': expected_parts.count,
            'vehicle_source_index': actual_vehicle_index,
            'max_error': 0,
            'original_entries': ['0x52c550', '0x52c2e0', '0x52add0', '0x52c190'],
            'scope': 'full stock mechanical records, empty-owner mechanical list and default Driver fallback; allocation and class/attachment resource lookup stubbed',
            'node_order': ordered_node_addresses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--game-root', required=True)
    parser.add_argument('--vehicle-id', type=int, default=101)
    args = parser.parse_args()
    print(verify(args.executable, args.game_root, args.vehicle_id))


if __name__ == '__main__':
    main()
