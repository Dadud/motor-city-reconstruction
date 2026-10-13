"""Bounded original component-count, repair/scrap and total-price comparisons."""
import argparse
import json
import random
import struct
from tools.native_oracle import DynoOracle


def synthetic_cases():
    rng = random.Random(0x661d60)
    special = (101, 1001, 2001, 3001, 36001, 210001, 37001, 4001,
               38001, 15001, 5001, 6001)
    yield ()
    for case in range(96):
        count = case % 14 + 1
        order = list(range(count))
        rng.shuffle(order)
        parents = {}
        for rank, index in enumerate(order):
            parents[index] = rng.choice(order[:rank] + [-1, 10000, index])
        slots = []
        for index in range(count):
            record = bytearray(bytes([case + 1]) * 1596)
            abstract = rng.choice(special + (55, 170001, 0))
            for offset, value in ((0, abstract), (0xc, rng.choice((0, 1, -1))),
                                  (0x1e3, rng.choice((0, 1, 32))),
                                  (0x600, parents[index]), (0x60c, rng.choice((0, 0, 1)))):
                struct.pack_into('<i', record, offset, value)
            for offset in (0x1eb, 0x62c, 0x630):
                struct.pack_into('<I', record, offset, rng.choice((0, 1, 0x7fffffff,
                                                                 0x80000000, 0xffffffff,
                                                                 rng.getrandbits(32))))
            slots.append(bytes(record))
        yield tuple(slots)


def verify(executable):
    from client.owned_aggregates import (apply_owned_component_counts,
                                        apply_owned_repair_scrap_aggregates,
                                        apply_owned_total_price)
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    matched = {'component_counts': 0, 'repair_scrap': 0, 'total_price': 0}
    for case, slots in enumerate(synthetic_cases()):
        for name, expected in (('component_counts', apply_owned_component_counts(slots)),
                               ('repair_scrap', apply_owned_repair_scrap_aggregates(slots)),
                               ('total_price', apply_owned_total_price(slots))):
            oracle._reset()
            cpu.mem_write(oracle.inputs, b''.join(slots) if slots else bytes(1596))
            stack = oracle.frame - 0x1000
            if name == 'component_counts':
                for index in range(len(slots)):
                    cpu.reg_write(reg.UC_X86_REG_ESP, stack)
                    cpu.reg_write(reg.UC_X86_REG_ECX, oracle.inputs)
                    cpu.mem_write(stack, struct.pack('<III', oracle.stop, index, len(slots)))
                    oracle._run(0x661370, oracle.stop, count=200000)
                    cpu.mem_write(oracle.inputs + index * 1596 + 0x638,
                                  struct.pack('<I', cpu.reg_read(reg.UC_X86_REG_EAX)))
            else:
                cpu.mem_write(stack, struct.pack('<III', oracle.stop, len(slots), oracle.inputs))
                oracle._run(0x661d60 if name == 'repair_scrap' else 0x6621f0,
                            oracle.stop, count=200000)
            actual = bytes(cpu.mem_read(oracle.inputs, len(slots) * 1596)) if slots else b''
            if actual != b''.join(expected):
                raise ValueError(f'original {name} differs in case {case}')
            matched[name] += 1
    return {'matched_cases': matched,
            'scope': 'complete original count/repair-scrap/total-price functions and real helpers; synthetic acyclic owned graphs; whole records; no DB loading or live transactions'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
