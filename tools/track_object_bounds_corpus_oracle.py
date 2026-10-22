"""Compare 0x427f50 bounds against object payloads from installed FRD tracks."""
import argparse
import json
from pathlib import Path
import struct

from unicorn import UC_HOOK_CODE

from client.track_mesh import decode_mesh
from client.track_object_bounds import build_track_object_bounds
from tools.collision_dynamic_candidate_table_oracle import _return
from tools.native_oracle import DynoOracle


SOURCE_BASE = 0x73000000
VERTEX_BASE = 0x73100000
TABLE_BASE = 0x71004000
COUNT = 0x0097C398
SOURCES = 0x0097C39C
TABLE = 0x0097C410
ALLOC = 0x006EE510
ZERO = 0x006EE0C0


def verify(executable, track_files):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    cpu.mem_map(SOURCE_BASE, 0x2000000)
    allocator_calls = zero_calls = groups_checked = objects_checked = 0

    def helpers(machine, address, _size, _user):
        nonlocal allocator_calls, zero_calls
        sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
        if address == ALLOC:
            allocator_calls += 1
            _tag, size = struct.unpack('<II', machine.mem_read(sp + 4, 8))
            if size > 0x20000:
                raise ValueError('native bounds routine requested oversized table')
            _return(machine, oracle, TABLE_BASE)
        elif address == ZERO:
            zero_calls += 1
            pointer, size = struct.unpack('<II', machine.mem_read(sp + 4, 8))
            if pointer != TABLE_BASE or size > 0x20000:
                raise ValueError('native bounds routine cleared unexpected range')
            machine.mem_write(pointer, bytes(size))
            _return(machine, oracle)

    hooks = [cpu.hook_add(UC_HOOK_CODE, helpers, begin=address, end=address)
             for address in (ALLOC, ZERO)]
    try:
        for track_file in track_files:
            groups = []
            decode_mesh(Path(track_file).read_bytes(), materials=True,
                        object_records=groups)
            for group in groups:
                count = len(group.objects)
                built = build_track_object_bounds(
                    group, source_address=SOURCE_BASE,
                    table_address=TABLE_BASE,
                    payload_address=SOURCE_BASE + count * 0x38)
                candidates = built.candidates
                oracle._reset()
                cpu.mem_write(COUNT, struct.pack('<I', count))
                cpu.mem_write(SOURCES, struct.pack('<I', SOURCE_BASE))
                if built.source_rows:
                    cpu.mem_write(SOURCE_BASE, built.source_rows)
                for address, points in built.vertex_arrays:
                    if points:
                        cpu.mem_write(address, points)
                        if bytes(cpu.mem_read(address, len(points))) != points:
                            raise AssertionError('failed to plant decoded vertex payload')
                cpu.mem_write(TABLE, bytes(4))
                cpu.mem_write(0x72007000, struct.pack('<I', oracle.stop))
                cpu.reg_write(oracle.reg.UC_X86_REG_ESP, 0x72007000)
                cpu.ctl_remove_cache(0x427f50, 0x428141)
                oracle._run(0x427f50, oracle.stop, timeout=0,
                            count=2_000_000)
                native_table_ptr, = struct.unpack('<I', cpu.mem_read(TABLE, 4))
                actual_records = (bytes(cpu.mem_read(native_table_ptr,
                                                       count * 0x78))
                                  if count else b'')
                actual_sources = (bytes(cpu.mem_read(SOURCE_BASE,
                                                       count * 0x38))
                                  if count else b'')
                if actual_records != candidates.records:
                    offset = next(i for i, (a, b) in enumerate(
                        zip(actual_records, candidates.records)) if a != b)
                    raise AssertionError(
                        f'{track_file} group {group.block_index}: '
                        f'candidate byte {offset:#x} differs')
                if actual_sources != candidates.sources:
                    offset = next(i for i, (a, b) in enumerate(
                        zip(actual_sources, candidates.sources)) if a != b)
                    raise AssertionError(
                        f'{track_file} group {group.block_index}: '
                        f'source byte {offset:#x} differs')
                groups_checked += 1
                objects_checked += count
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'entry': '0x427f50', 'tracks': len(tuple(track_files)),
            'object_groups': groups_checked, 'objects': objects_checked,
            'native_candidate_and_source_bytes_matched': True,
            'allocator_calls': allocator_calls, 'zero_helper_calls': zero_calls}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('tracks', nargs='+')
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.tracks)))
