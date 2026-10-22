"""Compare the 0x45cf70 dynamic-pair candidate broadphase to mcity.exe."""
import argparse
import json
import math
import random
import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_INVALID

from client.collision_pair_candidate import dynamic_pair_candidate
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
RECORDS_POINTER = 0x0097C410
RECORD = 0x71002000
COUNT = 0x0097C398


def _record(origin, local, radius, flags=(True, True), matrix=None):
    data = bytearray(0x78)
    struct.pack_into('<3f', data, 0, *origin)
    struct.pack_into('<9f', data, 0x0C, *(matrix or (1., 0., 0., 0., 1., 0., 0., 0., 1.)))
    struct.pack_into('<f', data, 0x30, 1. if flags[1] else 0.)
    struct.pack_into('<3f', data, 0x4C, *local)
    struct.pack_into('<f', data, 0x48, radius)
    struct.pack_into('<3f', data, 0x3C, .4, .2, .1)
    struct.pack_into('<f', data, 0x74, 1. if flags[0] else 0.)
    return bytes(data)


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45CF70)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    reached_filter = 0
    faults = []

    def stop_pair_filter(machine, address, _size, _user):
        nonlocal reached_filter
        if address == 0x45AF30:
            reached_filter += 1
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
            machine.reg_write(oracle.reg.UC_X86_REG_EAX, 0)
            machine.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
            machine.reg_write(oracle.reg.UC_X86_REG_EIP, ret)

    cpu.hook_add(UC_HOOK_CODE, stop_pair_filter)
    cpu.hook_add(UC_HOOK_MEM_INVALID,
                 lambda _m, access, address, size, value, _u:
                 faults.append((access, address, size, value)) or False)
    for index in range(count):
        if index == 0:
            origin, local, radius, flags = (0., 0., 0.), (0., 0., 0.), 1., (True, True)
            matrix, position = (1., 0., 0., 0., 1., 0., 0., 0., 1.), (0., 0., 0.)
        elif index == 1:
            origin, local, radius, flags = (0., 0., 0.), (0., 0., 0.), 1., (True, True)
            matrix, position = (1., 0., 0., 0., 1., 0., 0., 0., 1.), (2., 0., 0.)
        elif index == 2:
            origin, local, radius, flags = (0., 0., 0.), (0., 0., 0.), 1., (True, True)
            matrix, position = (1., 0., 0., 0., 1., 0., 0., 0., 1.), (1.75, 0., 0.)
        elif index in (3, 4):
            origin, local, radius = (0., 0., 0.), (0., 0., 0.), 1.
            flags = (index != 3, index != 4)
            matrix, position = (1., 0., 0., 0., 1., 0., 0., 0., 1.), (0., 0., 0.)
        else:
            origin = tuple(rng.uniform(-12., 12.) for _ in range(3))
            local = tuple(rng.uniform(-2., 2.) for _ in range(3))
            radius = rng.uniform(.1, 4.)
            angle = rng.uniform(-math.pi, math.pi)
            cosine, sine = math.cos(angle), math.sin(angle)
            matrix = (cosine, 0., sine, 0., 1., 0., -sine, 0., cosine)
            flags = (index % 7 != 0, index % 11 != 0)
            candidate_record = _record(origin, local, radius, flags, matrix)
            zero_body = bytearray(0x500)
            struct.pack_into('<f', zero_body, 0xD8, .75)
            center = dynamic_pair_candidate(zero_body, candidate_record).center
            if index % 3 == 0:
                position = tuple(center[axis] + radius * .25 for axis in range(3))
            else:
                position = tuple(rng.uniform(-16., 16.) for _ in range(3))
        if index <= 4:
            candidate_record = _record(origin, local, radius, flags, matrix)
        body = bytearray(0x500)
        struct.pack_into('<3f', body, 8, *position)
        struct.pack_into('<f', body, 0x50, 1.)
        struct.pack_into('<f', body, 0xD8, .75)
        struct.pack_into('<I', body, 0x3C4, 0xFFFFFFFF)
        translated = dynamic_pair_candidate(body, candidate_record)
        before_filter = reached_filter
        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(COUNT, struct.pack('<I', 1))
        cpu.mem_write(RECORDS_POINTER, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, candidate_record)
        try:
            oracle.call(0x45CF70, (OWNER,), instruction_limit=1_000_000)
        except Exception as error:
            eip = cpu.reg_read(oracle.reg.UC_X86_REG_EIP)
            raise RuntimeError(f'case {index} failed at {eip:#x}: {faults[-1:]!r}') from error
        native_reached = reached_filter != before_filter
        if native_reached != translated.within_radius:
            raise AssertionError(
                f'case {index}: filter entry {native_reached} != '
                f'{translated.within_radius}; candidate={translated!r}')
        contact_word = struct.unpack('<I', cpu.mem_read(OWNER + 0x3C4, 4))[0]
        wanted_contact_word = 0 if translated.within_radius else 0xFFFFFFFF
        if contact_word != wanted_contact_word:
            raise AssertionError(
                f'case {index}: contact reset {contact_word:#x} != {wanted_contact_word:#x}')
    return {'entry': '0x45cf70', 'cases': count,
            'pair_filter_calls': reached_filter,
            'scope': 'dynamic candidate eligibility, transformed center/radius broadphase, and first-reject path; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases)))
