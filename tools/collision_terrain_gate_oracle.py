"""Check early 0x45a320 triangle-rejection cases against original execution."""
import argparse
import json
import struct

from unicorn import UC_HOOK_CODE

from client.collision_terrain import triangle_candidate_gate
from tools.native_oracle import DynoOracle


TABLE = 0x88C9D4  # shape-0 triangle index list observed in 0x45a320


def cases():
    triangle = ((0., 0., 0.), (0., 0., 10.), (10., 0., 0.))
    for point in ((20., 20.), (-1., 2.), (2., -1.), (11., 0.)):
        yield point, triangle, 0
    # All three projected inequalities pass on this shared edge, so the
    # original reaches the zero-length helper once for each of 12 candidates.
    yield (0., 0.), (triangle[0], triangle[0], triangle[2]), 12


def compare(executable):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    owner = oracle.inputs
    calls = []
    cpu.hook_add(UC_HOOK_CODE,
                 lambda _cpu, address, _size, _user: calls.append(address)
                 if address in (0x6F14F0, 0x42E760) else None)
    # Point all 12 candidates at one supplied triangle so every case exits at
    # the projected-edge or nonzero-edge-length gate before world queries.
    cpu.mem_write(TABLE, struct.pack('<36I', *([0, 1, 2] * 12)))
    checked = 0
    for point, vertices, expected_edge_calls in cases():
        if triangle_candidate_gate(point, vertices):
            raise AssertionError('oracle case must be rejected by a candidate gate')
        image = bytearray(0x300)
        struct.pack_into('<f', image, 8, point[0])
        struct.pack_into('<f', image, 0x10, point[1])
        struct.pack_into('<I', image, 0xdc, 0)
        struct.pack_into('<9f', image, 0x1e8, *(v for vertex in vertices for v in vertex))
        cpu.mem_write(owner, bytes(image))
        before = bytes(cpu.mem_read(owner, len(image)))
        calls.clear()
        oracle.call(0x45A320, (owner,), instruction_limit=100_000)
        actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != 0:
            raise AssertionError(f'case {checked} unexpectedly returned {actual}')
        if bytes(cpu.mem_read(owner, len(image))) != before:
            raise AssertionError(f'case {checked} mutated the object on early rejection')
        edge_calls = calls.count(0x6F14F0)
        query_calls = calls.count(0x42E760)
        if edge_calls != expected_edge_calls or query_calls:
            raise AssertionError(f'case {checked} reached {edge_calls} edge helpers and '
                                 f'{query_calls} terrain queries')
        checked += 1
    return {'cases': checked, 'entry': '0x45a320',
            'scope': 'shape-0 early projected-edge/degenerate-triangle rejection'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(compare(parser.parse_args().executable)))
