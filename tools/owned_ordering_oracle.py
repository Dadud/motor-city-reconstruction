"""Bounded original recursive ordering comparison with isolated allocation."""
import argparse
import json
import random
import struct
from tools.native_oracle import DynoOracle


def synthetic_cases():
    rng = random.Random(0x66f0d0)
    ids = (101, 1001, 2001, 10001, 11001, 55, 56)
    for case in range(96):
        cache = [bytes(1596)]
        for index, identifier in enumerate(ids, 1):
            record = bytearray(1596)
            struct.pack_into('<i', record, 0, identifier)
            struct.pack_into('<i', record, 0x600, 0 if index == 1 else rng.randrange(1, index))
            cache.append(bytes(record))
        if case % 4 == 0:
            duplicate = bytearray(cache[4])
            struct.pack_into('<i', duplicate, 0x600, 1)
            cache.append(bytes(duplicate))
        slots = []
        for index in range(case % 25):
            record = bytearray(bytes([index + 1]) * 1596)
            identifier = 101 if index == 0 else rng.choice(ids + (999,))
            struct.pack_into('<i', record, 0, identifier)
            struct.pack_into('<i', record, 0x61c, rng.randrange(-1, 14))
            slots.append(bytes(record))
        if case == 95:
            # Prove the complete fixed attachment permutation, with records
            # deliberately supplied in numeric rather than original order.
            slots = []
            for attachment in range(12):
                record = bytearray(bytes([attachment + 1]) * 1596)
                struct.pack_into('<i', record, 0, 101)
                struct.pack_into('<i', record, 0x61c, attachment)
                slots.append(bytes(record))
        yield tuple(slots), tuple(cache)


def verify(executable):
    from unicorn import UC_HOOK_CODE
    from client.owned_ordering import order_owned_candidates, reorder_owned_parts
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cpu.mem_map(0, 0x1000)  # Isolated FS:[0] SEH-chain storage, not host state.
    temporary, destination = 0x73000000, 0x74000000
    cpu.mem_map(temporary, 0x200000)
    cpu.mem_map(destination, 0x100000)
    allocation_offset = 0

    def allocation(uc, address, size, user_data):
        nonlocal allocation_offset
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        result = 0
        if address == 0x699382:
            length = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
            if allocation_offset + length > 0x200000:
                raise ValueError('oracle allocation exceeds bound')
            result = temporary + allocation_offset
            allocation_offset += (length + 15) & ~15
            cpu.mem_write(result, bytes(length))
        cpu.reg_write(reg.UC_X86_REG_EAX, result)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    for address in (0x699382, 0x6992c5):
        cpu.hook_add(UC_HOOK_CODE, allocation, begin=address, end=address)
    count_address = oracle.inputs + 0xe000
    cache_base = oracle.inputs + 0xa000
    matched = 0
    for case, (slots, cache) in enumerate(synthetic_cases()):
        expected = order_owned_candidates(slots, cache)
        if not slots:
            # The caller has no first abstract type for an empty interface.
            if expected or reorder_owned_parts(slots, cache):
                raise ValueError('empty ordering differs')
            matched += 1
            continue
        oracle._reset()
        allocation_offset = 0
        cpu.mem_write(0, bytes(4))
        cpu.mem_write(oracle.inputs, b''.join(slots))
        cpu.mem_write(cache_base, b''.join(cache))
        cpu.mem_write(0xb18018, struct.pack('<II', len(cache), cache_base))
        cpu.mem_write(count_address, bytes(4))
        stack = oracle.frame - 0x1000
        root = struct.unpack_from('<i', slots[0])[0]
        cpu.mem_write(stack, struct.pack('<IIIIII', oracle.stop, oracle.inputs,
                                        len(slots), destination, count_address, root))
        oracle._run(0x66f0d0, oracle.stop, count=1000000)
        count = struct.unpack('<I', cpu.mem_read(count_address, 4))[0]
        if count > 512:
            raise ValueError('oracle ordering output exceeds bound')
        actual = bytes(cpu.mem_read(destination, count * 1596)) if count else b''
        if count != len(expected) or actual != b''.join(expected):
            raise ValueError(f'original ordering differs in case {case}, counts {count}/{len(expected)}')
        accepted = expected if len(expected) == len(slots) else slots
        if reorder_owned_parts(slots, cache) != accepted:
            raise ValueError('caller count-equality acceptance differs')
        matched += 1
    return {'matched_cases': matched,
            'scope': 'original 0x66f0d0 recursive traversal, cache lookup, initialization and whole-record copies; allocation/free substituted and SEH chain isolated; empty inputs checked at authored API; loader count-equality acceptance derived statically, not DB-loader execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
