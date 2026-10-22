"""Verify recovered 0x45a320 shape tables and traversal against mcity.exe."""
import argparse
import json
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import terrain_shape_triangle_indices
from tools.native_oracle import DynoOracle


TABLES = {
    0x88C9D4: (0, 2, 12),
    0x88CA64: (1, 1, 6),
    0x88C7F4: (3, 4, 40),
}
OWNER = 0x71002000


def compare(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    table_values = {}
    for address, (first_shape, second_shape, count) in TABLES.items():
        words = struct.unpack('<' + str(count * 3) + 'I',
                              cpu.mem_read(address, count * 12))
        observed = tuple(tuple(words[i:i + 3])
                         for i in range(0, len(words), 3))
        if observed != terrain_shape_triangle_indices(first_shape):
            raise AssertionError(f'shape {first_shape} index table differs from executable')
        if observed != terrain_shape_triangle_indices(second_shape):
            raise AssertionError(f'shape {second_shape} index table differs from executable')
        table_values[first_shape] = observed

    helper_calls = []
    cpu.hook_add(UC_HOOK_CODE,
                 lambda _cpu, address, _size, _user:
                 helper_calls.append(address) if address == 0x6F14F0 else None)
    traversal = {}
    for shape in range(5):
        image = bytearray(0x300)
        struct.pack_into('<I', image, 0xdc, shape)
        cpu.mem_write(OWNER, bytes(image))
        helper_calls.clear()
        oracle.call(0x45A320, (OWNER,), instruction_limit=100_000)
        result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        expected_count = len(terrain_shape_triangle_indices(shape))
        if result != 0 or len(helper_calls) != expected_count:
            raise AssertionError(f'shape {shape}: return={result}, '
                                 f'edge calls={len(helper_calls)}, expected={expected_count}')
        if bytes(cpu.mem_read(OWNER, len(image))) != bytes(image):
            raise AssertionError(f'shape {shape} changed the body on degenerate rejection')
        traversal[shape] = len(helper_calls)
    return {'entry': '0x45a320', 'tables': {
                'shapes_0_2': len(table_values[0]),
                'shape_1': len(table_values[1]),
                'shapes_3_4': len(table_values[3])},
            'original_traversal_edge_calls': traversal,
            'scope': 'exact table values and all-candidate degenerate-edge traversal'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(compare(parser.parse_args().executable)))
