"""Compare original postload orchestration with explicit description substitution."""
import argparse
import json
import random
import struct
from tools.native_oracle import DynoOracle


def description_fixture(slots):
    """Authored description boundary, never an original-description claim."""
    output = []
    for slot in slots:
        record = bytearray(slot)
        text = f'Fixture type {struct.unpack_from("<i", slot)[0]}'.encode() + b'\0'
        record[0x20:0x20 + len(text)] = text
        output.append(bytes(record))
    return tuple(output)


def synthetic_cases():
    rng = random.Random(0x66f586)
    identifiers = (101, 1001, 2001, 6001, 340001, 340333, 340666,
                   350001, 360001, 350666)
    parents = (0, 1, 2, 2, 3, 3, 3, 3, 3, 3)
    templates = [bytes(1596)]
    for identifier, parent in zip(identifiers, parents):
        record = bytearray(1596)
        struct.pack_into('<i', record, 0, identifier)
        struct.pack_into('<i', record, 0x600, parent)
        for offset, text in ((0x180, b'Category'), (0x2c7, b'Brand'),
                             (0x307, b'Model'), (0x347, b'Type')):
            record[offset:offset + len(text) + 1] = text + b'\0'
        templates.append(bytes(record))
    for case in range(96):
        slots = []
        chosen = list(range(1, 4)) + [i for i in range(4, 11) if rng.randrange(2)]
        for index in chosen:
            record = bytearray(templates[index])
            struct.pack_into('<I', record, 0x5f8, index if index < 4 or rng.randrange(2) else 0)
            struct.pack_into('<I', record, 0x1e3, index)
            struct.pack_into('<i', record, 0xc, int(index < 5))
            for offset in (0x1eb, 0x62c, 0x630):
                struct.pack_into('<I', record, offset, rng.getrandbits(32))
            slots.append(bytes(record))
        options = {'finalize_enabled': bool(case & 1), 'finalize_mode': (case // 2) % 3,
                   'display_mode': (case // 6) % 3, 'reorder': bool(case & 2),
                   'enriched': bool(case & 4)}
        yield tuple(slots), tuple(templates), options


def verify(executable):
    from unicorn import UC_HOOK_CODE
    from client.owned_postload import postprocess_owned_slots
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    cpu.mem_map(0, 0x1000)
    pool, slots_base = 0x73000000, 0x74000000
    cpu.mem_map(pool, 0x400000)
    cpu.mem_map(slots_base, 0x100000)
    bump = 0
    parameters, cache_base = oracle.inputs + 0xe000, oracle.inputs

    def allocate(length):
        nonlocal bump
        aligned = (length + 15) & ~15
        if bump + aligned > 0x400000:
            raise ValueError('oracle allocation bound exceeded')
        address = pool + bump
        bump += aligned
        cpu.mem_write(address, bytes(length))
        return address

    def cstring(address):
        data = bytearray()
        for offset in range(256):
            value = cpu.mem_read(address + offset, 1)[0]
            if not value:
                return bytes(data)
            data.append(value)
        raise ValueError('oracle text bound exceeded')

    def boundary(uc, address, size, user_data):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        value = 0
        if address == 0x699382:
            length = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
            value = allocate(length)
        elif address == 0x65e910:
            # Substitute the buffer-manager boundary and reserve spare output
            # capacity. It preserves the observed manager's first pointer field.
            manager = allocate(16)
            output = allocate(0x100000)
            cpu.mem_write(manager, struct.pack('<I', output))
            value = manager
        elif address == 0x699330:
            destination, fmt_address = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            fmt = cstring(fmt_address)
            if fmt not in (b'%s', b'%s %s'):
                raise ValueError('unsupported sprintf boundary')
            pointers = struct.unpack('<' + 'I' * fmt.count(b'%s'),
                                     cpu.mem_read(stack + 12, 4 * fmt.count(b'%s')))
            text = b' '.join(cstring(item) for item in pointers)
            cpu.mem_write(destination, text + b'\0')
            value = len(text)
        elif address == 0x6628d0:
            count, source = struct.unpack('<II', cpu.mem_read(stack + 4, 8))
            if count > 512:
                raise ValueError('description fixture count exceeds bound')
            records = tuple(bytes(cpu.mem_read(source + i * 1596, 1596)) for i in range(count))
            cpu.mem_write(source, b''.join(description_fixture(records)))
        cpu.reg_write(reg.UC_X86_REG_EAX, value)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    for address in (0x699382, 0x6992c5, 0x65e910, 0x65e870, 0x699330, 0x6628d0):
        cpu.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
    matched = 0
    for case, (slots, cache, options) in enumerate(synthetic_cases()):
        oracle._reset()
        bump = 0
        cpu.mem_write(0, bytes(4))
        cpu.mem_write(slots_base, bytes(0x100000))
        cpu.mem_write(slots_base, b''.join(slots))
        cpu.mem_write(cache_base, b''.join(cache))
        cpu.mem_write(0xb18014, struct.pack('<III', options['display_mode'], len(cache), cache_base))
        cpu.mem_write(parameters, struct.pack('<II', len(slots), slots_base))
        cpu.mem_write(oracle.frame - 0x1c, struct.pack('<II', 512, parameters + 4))
        cpu.mem_write(oracle.frame + 8, struct.pack('<I', slots_base))
        cpu.mem_write(oracle.frame + 0x18, struct.pack('<IIII', int(options['finalize_enabled']),
                           options['finalize_mode'], int(options['enriched']), int(options['reorder'])))
        cpu.reg_write(reg.UC_X86_REG_EBX, parameters)
        cpu.reg_write(reg.UC_X86_REG_ESI, options['finalize_mode'])
        cpu.reg_write(reg.UC_X86_REG_EDI, 0)
        oracle._run(0x66f586, 0x66f699, count=2000000)
        count = struct.unpack('<I', cpu.mem_read(parameters, 4))[0]
        source = struct.unpack('<I', cpu.mem_read(oracle.frame + 8, 4))[0]
        if count > 512:
            raise ValueError('postload output exceeds bound')
        expected = postprocess_owned_slots(slots, cache, description_pass=description_fixture, **options)
        actual = bytes(cpu.mem_read(source, count * 1596))
        if count != len(expected) or actual != b''.join(expected):
            mismatch = next((i for i, (a, b) in enumerate(zip(actual, b''.join(expected))) if a != b), None)
            raise ValueError(f'original postload differs in case {case}, byte {mismatch}, counts {count}/{len(expected)}')
        matched += 1
    return {'matched_cases': matched,
            'scope': 'original 0x66f586..0x66f699 orchestration, finalizer/pruning/ordering/linking/count/cost/price helpers; allocation/free, two sprintf formats and entire description pass substituted; prior DB discovery/enrichment, allocation failures and subsequent manager handoff excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
