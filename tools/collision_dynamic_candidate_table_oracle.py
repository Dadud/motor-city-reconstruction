"""Compare the 0x427f50 dynamic candidate-table producer to mcity.exe."""
import argparse
import json
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_pair_candidate import build_dynamic_candidate_table
from tools.native_oracle import DynoOracle


SOURCE_BASE = 0x71001000
VERTEX_BASE = 0x71002000
TABLE_BASE = 0x71004000
COUNT = 0x0097C398
SOURCES = 0x0097C39C
TABLE = 0x0097C410
ALLOC = 0x006EE510
ZERO = 0x006EE0C0


def _return(cpu, oracle, value=None):
    sp = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
    ret = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    if value is not None:
        cpu.reg_write(oracle.reg.UC_X86_REG_EAX, value)
    cpu.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(oracle.reg.UC_X86_REG_EIP, ret)


def compare(executable, cases=128):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x427F50)
    allocations = 0
    zeroes = 0

    def helpers(machine, address, _size, _user):
        nonlocal allocations, zeroes
        sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
        if address == ALLOC:
            allocations += 1
            _tag, size = struct.unpack('<II', machine.mem_read(sp + 4, 8))
            if size > 0x20000:
                raise ValueError('native producer requested oversized table')
            _return(machine, oracle, TABLE_BASE)
        elif address == ZERO:
            zeroes += 1
            pointer, size = struct.unpack('<II', machine.mem_read(sp + 4, 8))
            if pointer != TABLE_BASE or size > 0x20000:
                raise ValueError('unexpected native zero range')
            machine.mem_write(pointer, bytes(size))
            _return(machine, oracle)

    hook = cpu.hook_add(UC_HOOK_CODE, helpers,
                        begin=ALLOC, end=ALLOC)
    zero_hook = cpu.hook_add(UC_HOOK_CODE, helpers,
                             begin=ZERO, end=ZERO)
    try:
        for case in range(cases):
            count = 0 if case == 0 else rng.randint(1, 12)
            source = bytearray(count * 0x38)
            vertex_map = {}
            for index in range(count):
                offset = index * 0x38
                eligible = (case == 1 or rng.randrange(4) != 0)
                kind = 3 if eligible else rng.choice(tuple(range(3)) + tuple(range(4, 16)))
                struct.pack_into('<H', source, offset + 2,
                                 (rng.randrange(0x10) << 4) | kind)
                struct.pack_into('<I', source, offset + 8, rng.getrandbits(32))
                struct.pack_into('<I', source, offset + 0x0c, rng.getrandbits(32))
                struct.pack_into('<I', source, offset + 0x20, rng.getrandbits(32))
                point_count = rng.randint(1, 8) if eligible else rng.choice((0, 1, 3))
                struct.pack_into('<I', source, offset + 0x24, point_count)
                address = VERTEX_BASE + index * 0x100
                struct.pack_into('<I', source, offset + 0x28, address)
                if eligible:
                    coords = tuple(rng.uniform(-25., 25.) for _ in range(point_count * 3))
                    vertex_map[address] = struct.pack('<' + 'f' * len(coords), *coords)
                    cpu.mem_write(address, vertex_map[address])
            translated = build_dynamic_candidate_table(
                bytes(source), vertex_map, source_address=SOURCE_BASE,
                table_address=TABLE_BASE)
            oracle._reset()
            cpu.mem_write(COUNT, struct.pack('<I', count))
            cpu.mem_write(SOURCES, struct.pack('<I', SOURCE_BASE))
            if source:
                cpu.mem_write(SOURCE_BASE, bytes(source))
            cpu.mem_write(TABLE, b'\0' * 4)
            cpu.mem_write(0x72007000, struct.pack('<I', oracle.stop))
            cpu.reg_write(oracle.reg.UC_X86_REG_ESP, 0x72007000)
            cpu.ctl_remove_cache(0x427f50, 0x428141)
            oracle._run(0x427f50, oracle.stop, timeout=0, count=2_000_000)
            native_table_ptr = struct.unpack('<I', cpu.mem_read(TABLE, 4))[0]
            native_records = (bytes(cpu.mem_read(native_table_ptr, count * 0x78))
                              if count else b'')
            native_sources = (bytes(cpu.mem_read(SOURCE_BASE, count * 0x38))
                              if count else b'')
            if native_records != translated.records:
                for position, (actual, expected) in enumerate(zip(native_records, translated.records)):
                    if actual != expected:
                        raise AssertionError(
                            f'case {case}: table byte {position:#x}: '
                            f'native {actual:#x} != translated {expected:#x}')
                raise AssertionError(f'case {case}: candidate table lengths differ')
            if native_sources != translated.sources:
                for position, (actual, expected) in enumerate(zip(native_sources, translated.sources)):
                    if actual != expected:
                        raise AssertionError(
                            f'case {case}: source byte {position:#x}: '
                            f'native {actual:#x} != translated {expected:#x}')
                raise AssertionError(f'case {case}: source images differ')
    finally:
        cpu.hook_del(hook)
        cpu.hook_del(zero_hook)
    return {'entry': '0x427f50', 'cases': cases,
            'source_records': '0x38 bytes', 'candidate_records': '0x78 bytes',
            'table_and_source_bytes_matched': True,
            'allocator_calls': allocations, 'zero_helper_calls': zeroes,
            'bridges': ['0x6ee510 fixed-address allocation',
                        '0x6ee0c0 exact-range zeroing'],
            'scope': 'original producer body with controlled allocator bridges'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    arguments = parser.parse_args()
    print(json.dumps(compare(arguments.executable, arguments.cases)))
