"""Verify original finalization's induction pruning, excluding missing-part insertion."""
import argparse
import json
import random
import struct
from client.owned_induction import prune_owned_induction_placeholders
from tools.native_oracle import DynoOracle


def synthetic_cases():
    rng = random.Random(0x66ed71)
    identifiers = (340001, 340333, 340666, 350001, 360001, 350666)
    owned_flags = {340001: 0, 340333: 1, 350001: 2, 360001: 3}
    yield ()
    for case in range(96):
        ids = list(identifiers) + [rng.choice(identifiers + (12345,)) for _ in range(case % 7)]
        rng.shuffle(ids)
        slots = []
        for index, identifier in enumerate(ids):
            record = bytearray(bytes([case + 1]) * 1596)
            struct.pack_into('<i', record, 0, identifier)
            owned = bool((case % 16) & (1 << owned_flags[identifier])) if identifier in owned_flags else bool(case % 2)
            struct.pack_into('<I', record, 0x5f8, index + 1 if owned else 0)
            slots.append(bytes(record))
        yield tuple(slots)


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    count_address = oracle.inputs + 0xe000
    matched = 0
    for case, slots in enumerate(synthetic_cases()):
        oracle._reset()
        if slots:
            cpu.mem_write(oracle.inputs, b''.join(slots))
        cpu.mem_write(count_address, struct.pack('<II', len(slots), oracle.inputs))
        cpu.mem_write(oracle.frame + 0x10, struct.pack('<I', count_address + 4))
        cpu.reg_write(reg.UC_X86_REG_EBX, count_address)
        # Skip allocation/insertion and stop before restoring host SEH state.
        oracle._run(0x66ed71, 0x66f0ba, count=100000)
        actual_count = struct.unpack('<I', bytes(cpu.mem_read(count_address, 4)))[0]
        expected = prune_owned_induction_placeholders(slots)
        actual = bytes(cpu.mem_read(oracle.inputs, actual_count * 1596)) if actual_count else b''
        if actual_count != len(expected) or actual != b''.join(expected) or cpu.reg_read(reg.UC_X86_REG_EAX) != 1:
            raise ValueError(f'original induction pruning differs in case {case}')
        matched += 1
    return {'matched_induction_pruning_cases': matched,
            'scope': 'original 0x66ed71..0x66f0ba tail, whole-record pruning and count updates; prior allocation/missing-part insertion and SEH restoration excluded'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
