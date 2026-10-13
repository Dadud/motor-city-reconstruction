"""Verify original root selection and parent/family linking with bounded CPU runs."""
import argparse
import json
import random
import struct
from client.owned_parent_links import select_owned_root, link_owned_parents
from tools.native_oracle import DynoOracle


def synthetic_cases():
    """Authored, asset-free cases shared with native/Python port checks."""
    rng = random.Random(0x661ed0)
    identifiers = (101, 1001, 2001, 36001, 160001, 6001, 170001, 180001)
    parent_ids = {101: 0, 1001: 101, 2001: 1001, 36001: 2001,
                  160001: 36001, 6001: 1001, 170001: 160001, 180001: 6001}
    for case in range(96):
        count = 1 + case % 12
        templates = [bytes(1596)]
        for identifier in identifiers:
            template = bytearray(1596)
            struct.pack_into('<i', template, 0, identifier)
            parent = parent_ids[identifier]
            struct.pack_into('<i', template, 0x600,
                             identifiers.index(parent) + 1 if parent else 0)
            struct.pack_into('<i', template, 0x14, rng.choice((0, 1, -1)))
            templates.append(bytes(template))
        slots = []
        for index in range(count):
            slot = bytearray(b'\xa5' * 1596)
            choices = identifiers if case % 4 == 0 else identifiers[2:]
            identifier = rng.choice(choices)
            if case % 8 == 1 and index == 0:
                identifier = 990001  # Missing first template: root status 3.
            struct.pack_into('<i', slot, 0, identifier)
            struct.pack_into('<i', slot, 0x600, rng.randrange(count))
            struct.pack_into('<i', slot, 0x61c, rng.choice((0, 1, 2)))
            struct.pack_into('<I', slot, 0x1e3, rng.choice((0, 321)))
            struct.pack_into('<i', slot, 0x203, rng.choice((0, 4, -7, 42)))
            slots.append(bytes(slot))
        yield tuple(slots), tuple(templates)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    template_base = oracle.inputs + 0x8000
    matched_root = matched_parent = 0
    for case, (slots, templates) in enumerate(synthetic_cases()):
        count = len(slots)
        for entry, root in ((0x661a40, True), (0x661ed0, False)):
            oracle._reset()
            cpu.mem_write(oracle.inputs, b''.join(slots))
            cpu.mem_write(template_base, b''.join(templates))
            cpu.mem_write(0xb18018, struct.pack('<II', len(templates), template_base))
            stack = oracle.frame - 0x1000
            args = (oracle.inputs, count) if root else (count, oracle.inputs)
            cpu.mem_write(stack, struct.pack('<III', oracle.stop, *args))
            oracle._run(entry, oracle.stop, count=200000)
            expected, status = select_owned_root(slots, templates) if root else (
                link_owned_parents(slots, templates), 1)
            actual = bytes(cpu.mem_read(oracle.inputs, count * 1596))
            if actual != b''.join(expected) or cpu.reg_read(reg.UC_X86_REG_EAX) != status:
                raise ValueError(f'original {"root" if root else "parent"} pass differs in case {case}')
            if root:
                matched_root += 1
            else:
                matched_parent += 1
    return {'matched_root_cases': matched_root, 'matched_parent_cases': matched_parent,
            'scope': 'complete root/parent/family passes and real native lookup/initializer helpers; synthetic acyclic template caches; DB initialization/finalization excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
