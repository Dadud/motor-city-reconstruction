"""Compare original dependency linking using synthetic in-memory template caches."""
import argparse
import json
import random
import struct
from client.owned_dependencies import link_owned_dependencies
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(662060)
    identifiers = (1001, 2001, 20001, 6001, 160001, 170001, 180001)
    template_base = oracle.inputs + 0x8000
    matched = 0
    for case in range(64):
        oracle._reset()
        count = 1 + case % 12
        dependencies = {identifier: rng.choice((0,) + identifiers) for identifier in identifiers}
        templates = bytearray(1596 * (len(identifiers) + 1))
        for index, identifier in enumerate(identifiers, 1):
            struct.pack_into('<i', templates, index * 1596, identifier)
            dependency = dependencies[identifier]
            target = identifiers.index(dependency) + 1 if dependency else -1
            struct.pack_into('<i', templates, index * 1596 + 0x604, target)
        slots, resolved = [], []
        for index in range(count):
            slot = bytearray(b'\xa5' * 1596)
            identifier = rng.choice(identifiers)
            struct.pack_into('<i', slot, 0, identifier)
            struct.pack_into('<I', slot, 0x5f8, 0 if case % 2 == 0 and index == 0 else index + 1)
            struct.pack_into('<ii', slot, 0x600, rng.randrange(count), rng.randrange(count))
            struct.pack_into('<i', slot, 0x61c, rng.choice((0, 1, 2)))
            slots.append(bytes(slot))
            resolved.append(dependencies[identifier])
        expected = link_owned_dependencies(slots, resolved)
        cpu.mem_write(oracle.inputs, b''.join(slots))
        cpu.mem_write(template_base, bytes(templates))
        cpu.mem_write(0xb18018, struct.pack('<II', len(identifiers) + 1, template_base))
        stack = oracle.frame - 0x1000
        cpu.mem_write(stack, struct.pack('<III', oracle.stop, count, oracle.inputs))
        oracle._run(0x662060, oracle.stop, count=100000)
        actual = bytes(cpu.mem_read(oracle.inputs, count * 1596))
        if actual != b''.join(expected) or cpu.reg_read(reg.UC_X86_REG_EAX) != 1:
            raise ValueError(f'original dependency linking differs in case {case}')
        matched += 1
    return {'matched_dependency_cases': matched,
            'scope': 'complete 0x662060 and real 0x64c720 helper; synthetic resolved template cache, valid parent indices; prior finalization/parent linking excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
