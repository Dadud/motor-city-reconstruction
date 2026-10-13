"""Bounded original insertion comparison; allocation and sprintf are substituted."""
import argparse
import json
import random
import struct
from client.owned_insertion import insert_owned_placeholders
from tools.native_oracle import DynoOracle


def synthetic_cases():
    rng = random.Random(0x66ea20)
    identifiers = (101, 1001, 2001, 100001, 110001, 10001, 12001,
                   11001, 13001, 14001, 23001, 34001, 35001, 36001, 170001)
    for case in range(96):
        templates = [bytes(1596)]
        for index, identifier in enumerate(identifiers, 1):
            record = bytearray(1596)
            struct.pack_into('<i', record, 0, identifier)
            parent = 0 if index == 1 else rng.randrange(1, index)
            struct.pack_into('<i', record, 0x600, parent)
            for offset, text in ((0x180, b'Category'), (0x287, b'Old short'),
                                 (0x2c7, b'Brand'), (0x307, b'Model'),
                                 (0x347, f'Type {index}'.encode())):
                record[offset:offset + len(text) + 1] = text + b'\0'
            templates.append(bytes(record))
        if case % 4 == 0:
            duplicate = bytearray(templates[4])
            duplicate[0x347:0x387] = b'Duplicate description\0'.ljust(64, b'\0')
            struct.pack_into('<i', duplicate, 0x600, 1)
            templates.append(bytes(duplicate))
        slots = []
        for index in range(case % 7):
            record = bytearray(templates[rng.randrange(1, len(templates))])
            struct.pack_into('<I', record, 0x5f8, index + 1 if case % 3 else 0)
            struct.pack_into('<i', record, 0x61c, rng.choice((0, 10, 11)))
            struct.pack_into('<i', record, 0x1e7, 2001 if case % 5 == 0 else 0)
            slots.append(bytes(record))
        yield tuple(slots), tuple(templates), (0, 2, 3)[case % 3]


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    temporary, slots_base = 0x73000000, 0x74000000
    cpu.mem_map(temporary, 0x10000)
    cpu.mem_map(slots_base, 0x100000)
    parameters = oracle.inputs + 0xe000

    def cstring(address):
        result = bytearray()
        for offset in range(256):
            value = cpu.mem_read(address + offset, 1)[0]
            if value == 0:
                return bytes(result)
            result.append(value)
        raise ValueError('oracle string exceeds bound')

    def boundary(uc, address, size, user_data):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        if address == 0x699382:
            allocation_size = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
            if allocation_size > 0x10000:
                raise ValueError('oracle allocation exceeds bound')
            cpu.mem_write(temporary, bytes(allocation_size))
            value = temporary
        elif address == 0x6992c5:
            value = 0
        elif address == 0x699330:
            destination, fmt_address = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            fmt = cstring(fmt_address)
            if fmt not in (b'%s', b'%s %s'):
                raise ValueError(f'unsupported original format {fmt!r}')
            addresses = struct.unpack('<' + 'I' * fmt.count(b'%s'),
                                      cpu.mem_read(stack + 12, 4 * fmt.count(b'%s')))
            text = b' '.join(cstring(item) for item in addresses)
            cpu.mem_write(destination, text + b'\0')
            value = len(text)
        else:
            raise ValueError('unexpected boundary')
        cpu.reg_write(reg.UC_X86_REG_EAX, value)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    for address in (0x699382, 0x6992c5, 0x699330):
        cpu.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
    matched = 0
    for case, (slots, templates, mode) in enumerate(synthetic_cases()):
        oracle._reset()
        cpu.mem_write(slots_base, bytes(512 * 1596))
        if slots:
            cpu.mem_write(slots_base, b''.join(slots))
        cpu.mem_write(oracle.inputs, b''.join(templates))
        cpu.mem_write(0xb18014, struct.pack('<III', mode, len(templates), oracle.inputs))
        # Preallocated slots avoid the original buffer-manager growth boundary.
        cpu.mem_write(parameters, struct.pack('<III', 512, slots_base, len(slots)))
        cpu.mem_write(oracle.frame + 8, struct.pack('<IIIIII', 0, parameters,
                                                   parameters + 4, parameters + 8, 0, 1))
        oracle._run(0x66ea54, 0x66ed71, count=1000000)
        count = struct.unpack('<I', cpu.mem_read(parameters + 8, 4))[0]
        if count > 512:
            raise ValueError('original insertion exceeded capacity')
        expected = insert_owned_placeholders(slots, templates, display_mode=mode)
        actual = bytes(cpu.mem_read(slots_base, count * 1596))
        if count != len(expected) or actual != b''.join(expected):
            mismatch = next((i for i, (a, b) in enumerate(zip(actual, b''.join(expected))) if a != b), None)
            raise ValueError(f'original insertion differs in case {case}, offset {mismatch}, counts {count}/{len(expected)}')
        matched += 1
    return {'matched_insertion_cases': matched,
            'scope': 'original insertion prefix and real cache/eligibility/name/category helpers; allocation/free and two bounded sprintf formats substituted; preallocated capacity; entry skip flags, growth, induction tail and host SEH excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
