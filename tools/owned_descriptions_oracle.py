"""Compare original outer descriptions with leaf and localization boundaries."""
import argparse
import json
import random
import struct
from client.owned_descriptions import apply_owned_descriptions
from tools.native_oracle import DynoOracle


LABELS = {i: f'Attachment {i}'.encode() for i in range(1, 12)}


def leaf_fixture(slot):
    output = bytearray(slot)
    output[0x20:0x20 + 13] = b'Leaf fixture\0'
    return bytes(output)


def synthetic_cases():
    rng = random.Random(0x6628d0)
    for case in range(96):
        templates = [bytes(1596)]
        for abstract in (101, 1001, 2001, 55, 56):
            record = bytearray(1596)
            struct.pack_into('<i', record, 0, abstract)
            text = b'' if case % 3 == 0 else b'Template description'
            record[0x20:0x20 + len(text) + 1] = text + b'\0'
            templates.append(bytes(record))
        slots = []
        count = case % 18
        for index in range(count):
            record = bytearray(b'\xa5' * 1596)
            abstract = 101 if index == 0 else rng.choice((1001, 2001, 55, 56, 999))
            for offset, value in ((0, abstract), (0x1e3, rng.choice((0, 1))),
                                  (0x600, rng.randrange(count)), (0x61c, rng.randrange(-1, 14))):
                struct.pack_into('<i', record, offset, value)
            for offset, text in ((0x20, b'Old description'),
                                 (0x287, b'M' * rng.randrange(1, 64)),
                                 (0x180, b'C' * rng.randrange(1, 64))):
                record[offset:offset + len(text) + 1] = text + b'\0'
            slots.append(bytes(record))
        # Dense assembly cases exercise rollback of the first overflowing line.
        if case % 4 == 0:
            for index, slot in enumerate(slots):
                record = bytearray(slot)
                struct.pack_into('<i', record, 0x600, 0)
                struct.pack_into('<i', record, 0x1e3, 1)
                slots[index] = bytes(record)
        yield tuple(slots), tuple(templates)


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    label_address = oracle.inputs + 0xf000

    def cstring(address):
        data = bytearray()
        for i in range(704):
            value = cpu.mem_read(address + i, 1)[0]
            if not value:
                return bytes(data)
            data.append(value)
        raise ValueError('oracle string exceeds bound')

    def boundary(uc, address, size, user_data):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        value = 0
        if address == 0x668710:
            source = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
            cpu.mem_write(source, leaf_fixture(bytes(cpu.mem_read(source, 1596))))
        elif address == 0x66fb40:
            attachment = struct.unpack('<i', cpu.mem_read(stack + 4, 4))[0]
            cpu.mem_write(label_address, LABELS.get(attachment, b'') + b'\0')
            value = label_address
        else:
            destination, limit, fmt, *pointers = struct.unpack('<7I', cpu.mem_read(stack + 4, 28))
            if cstring(fmt) != b'%s %s%s%s':
                raise ValueError('unexpected original formatting boundary')
            values = [cstring(pointer) for pointer in pointers]
            text = values[0] + b' ' + values[1] + values[2] + values[3]
            if len(text) >= limit:
                raise ValueError('fixture reaches unsupported CRT truncation boundary')
            cpu.mem_write(destination, text + b'\0')
            value = len(text)
        cpu.reg_write(reg.UC_X86_REG_EAX, value)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    for address in (0x668710, 0x66fb40, 0x6998d8):
        cpu.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
    matched = 0
    for case, (slots, templates) in enumerate(synthetic_cases()):
        oracle._reset()
        if slots:
            cpu.mem_write(oracle.inputs, b''.join(slots))
        cache = oracle.inputs + 0x9000
        cpu.mem_write(cache, b''.join(templates))
        cpu.mem_write(0xb18018, struct.pack('<II', len(templates), cache))
        cpu.mem_write(oracle.frame - 0x1000, struct.pack('<III', oracle.stop, len(slots), oracle.inputs))
        oracle._run(0x6628d0, oracle.stop, count=1000000)
        expected = apply_owned_descriptions(slots, templates, attachment_labels=LABELS, leaf_description=leaf_fixture)
        actual = bytes(cpu.mem_read(oracle.inputs, len(slots) * 1596)) if slots else b''
        if actual != b''.join(expected):
            raise ValueError(f'original outer description differs in case {case}')
        matched += 1
    return {'matched_cases': matched,
            'scope': 'complete outer 0x6628d0 and real type lookup/special checks; branded leaf rendering, localized attachment text and bounded snprintf substituted; all record bytes compared'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
