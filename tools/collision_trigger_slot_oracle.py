"""Compare runtime trigger slot allocation with original 0x407710."""
import json
import random
import struct

from client.collision_world_candidate import allocate_trigger_slot
from tools.native_oracle import DynoOracle


SLOTS = 0x008E3B38
RESOURCES = 0x008E5390
OWNER_GLOBAL = 0x00AA456C


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x407710)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    for case in range(count):
        first_free = 256 if case % 17 == 0 else rng.randrange(257)
        slots = bytearray(rng.randbytes(0x1800))
        for index in range(256):
            occupied = index < first_free
            struct.pack_into('<I', slots, index * 0x18,
                             (rng.randrange(1, 0xffffffff) if occupied else 0))
        resources = [rng.randrange(1, 0xffffffff) for _ in range(256)]
        category = (256 if case % 13 == 0 else
                    (0xffffffff if case % 19 == 0 else rng.randrange(256)))
        if category <= 255 and case % 7 == 0:
            resources[category] = 0
        owner = rng.randrange(1, 0xffffffff)
        expected = allocate_trigger_slot(slots, resources, category, owner)

        oracle._reset()
        cpu.mem_write(SLOTS, bytes(slots))
        cpu.mem_write(RESOURCES, struct.pack('<256I', *resources))
        cpu.mem_write(OWNER_GLOBAL, struct.pack('<I', owner))
        oracle.call(0x407710, (category,), instruction_limit=100_000)
        actual_result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        actual_slots = bytes(cpu.mem_read(SLOTS, 0x1800))
        if actual_result != expected.result:
            raise AssertionError(
                f'case {case}: result {actual_result:#x} != {expected.result:#x}')
        if actual_slots != expected.slots:
            raise AssertionError(f'case {case}: trigger slot table differs')
    return {'entry': '0x407710', 'cases': count,
            'scope': 'free-slot scan, invalid categories, missing resources, and exact 0x18-byte slot writes'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
