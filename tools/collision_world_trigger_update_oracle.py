"""Compare composed world-trigger updates with the real 0x42d9f0 call path."""
import json
import random
import struct

from client.body_constructor import construct_body
from client.collision_world_candidate import update_world_contact
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
TABLE = 0x71004000
RECORD = 0x71002000
OUTPUT = 0x71009000
STATUS = 0x0097DBF0
SAMPLE_ID = 17
SLOTS = 0x008E3B38
RESOURCES = 0x008E5390
OWNER_GLOBAL = 0x00AA456C


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x42D9F0A)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    for index in range(count):
        kind = (0, 1, 2, 3)[index % 4]
        body = bytearray(construct_body(bytearray(0x2000), OWNER, 1.,
                                        (1., 1., 1.), 0, 0))
        body[0x374:0x378] = bytes(4)
        body[6] = 1 if index % 5 == 0 else 0
        body[0x474] = 2 if index % 7 == 0 else 0
        coordinates = (rng.uniform(-1000., 1000.), rng.uniform(-1000., 1000.))
        struct.pack_into('<f', body, 0x14, coordinates[0])
        struct.pack_into('<f', body, 0x1c, coordinates[1])
        speed = (rng.choice((-1., 0., 10000., 18750., 30000., 37500., 40000.))
                 if kind == 2 else 0.)
        struct.pack_into('<f', body, 0x3c0, speed)
        record = bytearray(0x14)
        struct.pack_into('<H', record, 0x0e, SAMPLE_ID)
        record[0x13] = kind

        sample_state = bytes((rng.choice((0xff, 0, 2, 0xfe)),
                              rng.randrange(256), rng.randrange(256)))
        first_free = (0, 1, 127, 128, 255, 256)[index % 6]
        if index >= 6:
            first_free = rng.randrange(257)
        slots = bytearray(rng.randbytes(0x1800))
        for slot in range(256):
            pointer = (rng.randrange(1, 0xffffffff)
                       if slot < first_free else 0)
            struct.pack_into('<I', slots, slot * 0x18, pointer)
        resources = [0] * 256
        resources[2] = 0x7100A002 if index % 5 != 0 else 0
        resources[3] = 0x7100A003 if index % 7 != 0 else 0
        owner_pointer = 0x7100BEEF
        expected = update_world_contact(
            body, record, sample_state, slots, resources, owner_pointer)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097C408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, bytes(record))
        cpu.mem_write(STATUS + SAMPLE_ID * 3, sample_state)
        cpu.mem_write(SLOTS, bytes(slots))
        cpu.mem_write(RESOURCES, struct.pack('<256I', *resources))
        cpu.mem_write(OWNER_GLOBAL, struct.pack('<I', owner_pointer))
        cpu.mem_write(OUTPUT, bytes(4))
        oracle.call(0x42D9F0, (OWNER, 0, OUTPUT), instruction_limit=1_000_000)

        actual_decision = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_decision & 0x80000000:
            actual_decision -= 0x100000000
        actual_code = struct.unpack('<I', cpu.mem_read(OUTPUT, 4))[0]
        actual_state = bytes(cpu.mem_read(STATUS + SAMPLE_ID * 3, 3))
        actual_slots = bytes(cpu.mem_read(SLOTS, 0x1800))
        if actual_decision != expected.classification.decision:
            raise AssertionError(
                f'case {index}: decision {actual_decision} != '
                f'{expected.classification.decision}')
        if actual_code != expected.classification.type_code:
            raise AssertionError(
                f'case {index}: type {actual_code:#x} != '
                f'{expected.classification.type_code:#x}')
        if actual_state != expected.sample_state:
            raise AssertionError(
                f'case {index}: sample state {actual_state.hex()} != '
                f'{expected.sample_state.hex()}')
        if actual_slots != expected.trigger_slots:
            raise AssertionError(f'case {index}: full trigger slot memory differs')
    return {'entry': '0x42d9f0', 'cases': count,
            'scope': 'real classifier, allocator, heading helper and state writer; exact three-byte sample state and full 0x1800-byte trigger table comparison'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
