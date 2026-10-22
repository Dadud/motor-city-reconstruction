"""Compare collision event lookup and state transitions with mcity.exe."""
import argparse
import json
import random
import struct

from client.collision_event import (HANDLER_COUNT, apply_collision_contact_event,
                                    lookup_collision_event_handler)
from tools.native_oracle import DynoOracle


BODY, HANDLER = 0x71008000, 0x7100C000
VTABLES = (0x0083C084, 0x0083C170, 0x0083C30C)


def compare(executable, count=512):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x4658F0)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    transition_cases = 0
    active_cases = 0
    for index in range(count):
        image = bytearray(0x1100)
        handler_index = (-1, 0, 11, 12)[index % 4]
        struct.pack_into('<i', image, 0x464, handler_index)
        handlers = tuple(rng.randrange(0, 0xffffffff) for _ in range(HANDLER_COUNT))
        expected_pointer = lookup_collision_event_handler(image, handlers)
        cpu.mem_write(BODY, bytes(image))
        cpu.mem_write(0x0098F38C, struct.pack('<12I', *handlers))
        oracle.call(0x43B550, (), this_pointer=BODY,
                    instruction_limit=100_000)
        actual_pointer = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual_pointer != expected_pointer:
            raise AssertionError(f'case {index}: handler {actual_pointer:#x} != {expected_pointer:#x}')

        image = bytearray(rng.randbytes(0x1100))
        vtable = VTABLES[index % len(VTABLES)]
        flags = 2 if index % 7 else 0
        magnitude = 1. if index % 11 else 0.
        state = (0, 1, 2)[index % 3]
        threshold = (2.0, 2.23515, 2.5)[index % 3]
        matrix = tuple(struct.unpack('<f', struct.pack('<f', rng.uniform(-2., 2.)))[0]
                       for _ in range(9))
        impulse = tuple(struct.unpack('<f', struct.pack('<f', rng.uniform(-3., 3.)))[0]
                        for _ in range(3))
        event_value = rng.randrange(0x100000000)
        struct.pack_into('<I', image, 0x474, flags)
        struct.pack_into('<f', image, 0x3c8, magnitude)
        struct.pack_into('<3f', image, 0x3cc, *impulse)
        struct.pack_into('<9f', image, 0x78, *matrix)
        struct.pack_into('<I', image, 0xe00, state)
        struct.pack_into('<f', image, 0x105c, threshold)
        struct.pack_into('<I', image, 0xdf4, rng.randrange(0x100000000))
        expected = apply_collision_contact_event(image, event_value)

        cpu.mem_write(BODY, bytes(image))
        cpu.mem_write(HANDLER, struct.pack('<I', vtable) + bytes(0x100 - 4))
        cpu.mem_write(0x00AA456C, struct.pack('<I', event_value))
        oracle.call(0x4658F0, (BODY,), this_pointer=HANDLER, cleanup=b'',
                    instruction_limit=100_000)
        actual = bytes(cpu.mem_read(BODY, len(image)))
        if actual != expected:
            for offset, (a, b) in enumerate(zip(actual, expected)):
                if a != b:
                    raise AssertionError(f'case {index}: body byte {offset:#x}: {a:#x} != {b:#x}')
        changed = struct.unpack_from('<I', expected, 0xe00)[0] != state
        transition_cases += int(changed)
        active_cases += int(bool(flags & 2 and magnitude != 0.0))
    return {'lookup_entry': '0x43b550', 'event_entry': '0x4658f0',
            'cases_per_entry': count, 'state_transitions': transition_cases,
            'active_gate_cases': active_cases,
            'scope': '12-slot handler lookup and three shared-vtable contact-event transitions with body bytes compared exactly'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
