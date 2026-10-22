"""Compare the 0x42d890/0x45cd80 candidate gates to mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_pair_gate import (PairCandidateRecord,
                                        accepts_pair_candidate)
from tools.native_oracle import DynoOracle


WORLD = 0x71000000
BODY = WORLD + 0x1000
RECORD = WORLD + 0x2000
MATERIAL = WORLD + 0x3000
VERTICES = WORLD + 0x4000


def _f(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def compare(executable, cases=256):
    if type(cases) is not int or cases < 1:
        raise ValueError('case count must be positive')
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x45CD80)
    accepted = 0
    for index in range(cases):
        owner_id = 2 + index % 5
        candidate_id = 7 + index % 11
        links = [0] * 8
        if index % 8 == 0:
            links[index % 8] = candidate_id
        elif index % 13 == 0:
            candidate_id = owner_id
        height_limit = _f(rng.uniform(-2., 2.))
        below_limit = index % 8 == 0
        base_height = height_limit - .5 if below_limit else height_limit + rng.uniform(-.5, .5)
        vertices = tuple((rng.uniform(-4., 4.), _f(base_height + (rng.uniform(0., .1)
                                                                 if below_limit else
                                                                 rng.uniform(0., .4))),
                          rng.uniform(-4., 4.)) for _ in range(4))
        material_flags = 3 if below_limit else (0, 0x0e, 1, 3, 0x10, 0xff)[index % 6]
        gate_value = 0 if below_limit else index % 2
        model_record = PairCandidateRecord(candidate_id, material_flags,
                                           gate_value, vertices, height_limit)
        expected = accepts_pair_candidate(owner_id, tuple(links), model_record)

        oracle._reset()
        body = bytearray(0x380)
        struct.pack_into('<I', body, 0x374, owner_id)
        record = bytearray(0x44)
        struct.pack_into('<I', record, 4, candidate_id)
        struct.pack_into('<I', record, 8, gate_value)
        struct.pack_into('<I', record, 12, MATERIAL)
        struct.pack_into('<4I', record, 16,
                         *(VERTICES + i * 0x10 for i in range(4)))
        struct.pack_into('<f', record, 0x24, height_limit)
        cpu.mem_write(BODY, bytes(body))
        cpu.mem_write(RECORD, bytes(record))
        cpu.mem_write(MATERIAL, bytes(4) + bytes((material_flags,)))
        for i, vertex in enumerate(vertices):
            cpu.mem_write(VERTICES + i * 0x10, struct.pack('<3f', *vertex))
        cpu.mem_write(0x0097C408, struct.pack('<I', WORLD))
        cpu.mem_write(WORLD + owner_id * 0x6c4 + 0x6a4,
                      struct.pack('<8I', *links))
        oracle.call(0x45CD80, (BODY, RECORD), instruction_limit=100_000)
        actual = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        native = bool(actual)
        if native != expected:
            raise AssertionError(
                f'case {index}: native={native}, model={expected}; '
                f'id={candidate_id}, links={links}, flags={material_flags:#x}, '
                f'gate={gate_value}, heights={tuple(v[1] for v in vertices)}, '
                f'limit={height_limit}')
        accepted += int(expected)
    return {'identity_cases': cases, 'candidate_gate_cases': cases,
            'accepted_candidates': accepted,
            'scope': 'direct 0x42d890 identity-link scan and 0x45cd80 material/height gate'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))


if __name__ == '__main__':
    main()
