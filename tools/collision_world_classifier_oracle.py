"""Compare stateful candidate classification with original 0x42d9f0."""
import json
import random
import struct

from unicorn import UC_HOOK_CODE

from client.body_constructor import construct_body
from client.collision_world_candidate import classify_world_contact
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
TABLE = 0x71004000
RECORD = 0x71002000
OUTPUT = 0x71009000
STATUS = 0x0097DBF0
SAMPLE_ID = 17


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x42D9F0)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    allocation_calls = 0

    def fail_allocation(machine, address, _size, _user):
        nonlocal allocation_calls
        if address != 0x407710:
            return
        allocation_calls += 1
        sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
        # The 8-bit slot result 0xff is the native failure sentinel.
        machine.reg_write(oracle.reg.UC_X86_REG_EAX, 0xff)
        machine.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
        machine.reg_write(oracle.reg.UC_X86_REG_EIP, ret)

    cpu.hook_add(UC_HOOK_CODE, fail_allocation)
    trigger_cases = 0
    for index in range(count):
        kind = (0, 1, 2, 3)[index % 4]
        state = (0xff, 0, 3, 0xfe)[index % 4] if index % 8 < 4 else rng.choice((0xff, 0, 2, 0xfe))
        body = bytearray(construct_body(bytearray(0x2000), OWNER, 1.,
                                        (1., 1., 1.), 0, 0))
        body[0x374:0x378] = bytes(4)
        body[6] = 1 if index % 5 == 0 else 0
        body[0x474] = 2 if index % 7 == 0 else 0
        speed = (rng.choice((-1., 0., 10000., 18750., 30000., 37500., 40000.))
                 if kind == 2 else 0.)
        struct.pack_into('<f', body, 0x3c0, speed)
        record = bytearray(0x14)
        struct.pack_into('<H', record, 0x0e, SAMPLE_ID)
        record[0x13] = kind

        expected = classify_world_contact(body, record, state)
        oracle._reset()
        allocation_calls = 0
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097C408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, bytes(record))
        cpu.mem_write(STATUS + SAMPLE_ID * 3, struct.pack('<b', state if state < 128 else state - 256))
        cpu.mem_write(OUTPUT, bytes(4))
        oracle.call(0x42D9F0, (OWNER, 0, OUTPUT), instruction_limit=1_000_000)
        actual_decision = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_decision & 0x80000000:
            actual_decision -= 0x100000000
        actual_code = struct.unpack('<I', cpu.mem_read(OUTPUT, 4))[0]
        actual_state = struct.unpack('<b', cpu.mem_read(STATUS + SAMPLE_ID * 3, 1))[0]
        if (actual_decision, actual_code, actual_state) != (
                expected.decision, expected.type_code,
                expected.trigger_state_after if expected.trigger_state_after <= 127
                else expected.trigger_state_after - 256):
            raise AssertionError(
                f'case {index}: native classification '
                f'{(actual_decision, actual_code, actual_state)!r} != '
                f'{expected!r}')
        if (allocation_calls != int(expected.trigger_tier is not None)):
            raise AssertionError(f'case {index}: allocation request count differs')
        trigger_cases += int(expected.trigger_tier is not None)
    return {'entry': '0x42d9f0', 'cases': count,
            'exhausted_trigger_allocations': trigger_cases,
            'scope': 'contact kind/type code, trigger sentinel, speed gates, tier selection, and allocation failure state'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
