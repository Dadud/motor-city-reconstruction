"""Compare the 0x45cf70 dynamic-pair candidate broadphase to mcity.exe."""
import argparse
import json
import math
import random
import struct

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_INVALID

from client.body_geometry import body_samples
from client.body_constructor import construct_body
from client.collision_pair_candidate import (dynamic_pair_candidate,
                                             resolve_dynamic_pair_retries)
from client.collision_pair_geometry import OrientedCollisionBox
from client.collision_pair_solver import CollisionPairBody
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


def compare(executable, count=128, execute_pair_resolver=False):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45CF70)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    reached_filter = 0
    response_calls = 0
    total_response_calls = 0
    retry_cases = 0
    total_retry_attempts = 0
    filter_results = []
    faults = []

    def stop_pair_filter(machine, address, _size, _user):
        nonlocal reached_filter, response_calls
        if address == 0x45D108:
            ebp = machine.reg_read(oracle.reg.UC_X86_REG_EBP)
            target = ebp - 0x450
            filter_results.append((machine.reg_read(oracle.reg.UC_X86_REG_EAX),
                                   struct.unpack('<3f', machine.mem_read(OWNER + 8, 12)),
                                   struct.unpack('<3f', machine.mem_read(target + 8, 12))))
        elif address == 0x45AF30:
            reached_filter += 1
            if execute_pair_resolver:
                return
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
            machine.reg_write(oracle.reg.UC_X86_REG_EAX, 0)
            machine.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
            machine.reg_write(oracle.reg.UC_X86_REG_EIP, ret)
        elif address == 0x458530:
            response_calls += 1

    cpu.hook_add(UC_HOOK_CODE, stop_pair_filter)
    cpu.hook_add(UC_HOOK_MEM_INVALID,
                 lambda _m, access, address, size, value, _u:
                 faults.append((access, address, size, value)) or False)
    for index in range(count):
        response_calls = 0
        filter_results.clear()
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
        if execute_pair_resolver and index == 0:
            position = (.5, 0., 0.)
        if execute_pair_resolver:
            body = bytearray(construct_body(bytearray(0x2000), OWNER, 1.,
                                            (1., 1., 1.), 0, 0))
        else:
            body = bytearray(0x500)
            struct.pack_into('<f', body, 0xD8, .75)
        struct.pack_into('<3f', body, 8, *position)
        struct.pack_into('<f', body, 0x50, 1.)
        struct.pack_into('<I', body, 0x3C4, 0xFFFFFFFF)
        translated = dynamic_pair_candidate(body, candidate_record)
        retry_result = None
        if execute_pair_resolver and translated.within_radius:
            axes = tuple(tuple(struct.unpack_from('<3f', body, 0x78 + 12 * axis))
                         for axis in range(3))
            owner_extents = struct.unpack_from('<3f', body, 0xCC)
            owner_body = CollisionPairBody(
                OrientedCollisionBox(position, axes, owner_extents),
                mass=struct.unpack_from('<f', body, 0x50)[0],
                mode=body[5], local_vertices=struct.unpack_from('<66f', body, 0xE0))
            target_extents = struct.unpack_from('<3f', candidate_record, 0x3C)
            target_body = CollisionPairBody(
                OrientedCollisionBox(translated.center,
                                     tuple(tuple(matrix[i:i+3])
                                           for i in (0, 3, 6)),
                                     target_extents),
                mass=owner_body.mass, mode=1,
                local_vertices=tuple(value for point in body_samples(0, target_extents)
                                     for value in point))
            retry_result = resolve_dynamic_pair_retries(owner_body, target_body)
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
        if execute_pair_resolver and retry_result is not None:
            retry_cases += 1
            total_retry_attempts += len(filter_results)
            if len(filter_results) != retry_result.attempts:
                raise AssertionError(
                    f'case {index}: native retry count {len(filter_results)} != '
                    f'{retry_result.attempts}')
            native_owner = filter_results[-1][1]
            native_target = filter_results[-1][2]
            for label, actual, expected in (
                    ('owner', native_owner, retry_result.owner.box.center),
                    ('target', native_target, retry_result.target.box.center)):
                if any(abs(a - b) > max(1e-4, abs(b) * 2e-6)
                       for a, b in zip(actual, expected)):
                    raise AssertionError(
                        f'case {index}: {label} retry position {actual!r} '
                        f'!= {expected!r}')
            if response_calls != int(retry_result.response_due):
                raise AssertionError(
                    f'case {index}: native response calls {response_calls} '
                    f'!= {int(retry_result.response_due)}')
            total_response_calls += response_calls
    return {'entry': '0x45cf70', 'cases': count,
            'pair_filter_calls': reached_filter,
            'response_calls': total_response_calls if execute_pair_resolver else None,
            'retry_cases': retry_cases if execute_pair_resolver else None,
            'retry_attempts': total_retry_attempts if execute_pair_resolver else None,
            'scope': 'candidate broadphase, pair-solver retries, and response scheduling; original x86 execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    parser.add_argument('--execute-pair-resolver', action='store_true')
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases,
                             args.execute_pair_resolver)))
