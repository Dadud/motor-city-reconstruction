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
from client.collision_impulse import CollisionInertia
from client.collision_pair_response import CollisionImpactBody, resolve_pair_impulse
from client.collision_pair_solver import CollisionPairBody
from tools.native_oracle import DynoOracle


OWNER = 0x71008000
RECORDS_POINTER = 0x0097C410
RECORD = 0x71002000
COUNT = 0x0097C398
IMPACT_POINT = 0x0098CD90
FALLBACK_GLOBALS = (0x0098CDE0, 0x0098CDE4, 0x0098CDE8)


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


def _impact_body(address, image):
    inertia = CollisionInertia(
        struct.unpack_from('<f', image, 0x54)[0],
        struct.unpack_from('<3f', image, 0x2FC),
        struct.unpack_from('<9f', image, 0x9C),
        struct.unpack_from('<9f', image, 0x78))
    return CollisionImpactBody(
        address, struct.unpack_from('<3f', image, 8),
        struct.unpack_from('<3f', image, 0x14),
        struct.unpack_from('<3f', image, 0x38),
        struct.unpack_from('<3f', image, 0x5C), inertia,
        struct.unpack_from('<f', image, 0x50)[0], mode=image[5],
        response_coefficient=struct.unpack_from('<f', image, 0x68)[0],
        gate=struct.unpack_from('<f', image, 0x6C)[0],
        peer_gate=struct.unpack_from('<f', image, 0x3C0)[0],
        contact_record=bytes(image[:0x400]),
        embedded_contact_pointer=struct.unpack_from('<I', image, 0x404)[0])


def compare(executable, count=128, execute_pair_resolver=False):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45CF70)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    reached_filter = 0
    response_calls = 0
    response_cases = []
    total_response_calls = 0
    retry_cases = 0
    total_retry_attempts = 0
    response_impacts = 0
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
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            owner_ptr, target_ptr, point_ptr, normal_ptr = struct.unpack(
                '<4I', machine.mem_read(sp + 4, 16))
            response_cases.append((
                owner_ptr, target_ptr,
                bytes(machine.mem_read(owner_ptr, 0x408)),
                bytes(machine.mem_read(target_ptr, 0x408)),
                struct.unpack('<3f', machine.mem_read(point_ptr, 12)),
                struct.unpack('<3f', machine.mem_read(normal_ptr, 12)),
                struct.unpack('<2f', machine.mem_read(0x0089C070, 8))))

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
        if execute_pair_resolver and index == 0:
            struct.pack_into('<3f', body, 0x14, 1., 0., 0.)
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
        response_cases.clear()
        if execute_pair_resolver:
            cpu.mem_write(IMPACT_POINT, struct.pack('<3f', .5, 0., 0.))
            fallback = (-1., 0., 0.) if index == 0 else (0., 0., 0.)
            for address, value in zip(FALLBACK_GLOBALS, fallback):
                cpu.mem_write(address, struct.pack('<f', value))
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
            for owner_ptr, target_ptr, owner_image, target_image, point, normal, coeffs in response_cases:
                expected = resolve_pair_impulse(
                    _impact_body(owner_ptr, owner_image),
                    _impact_body(target_ptr, target_image), point, normal, *coeffs)
                response_impacts += int(expected.collided)
                native_owner = bytes(cpu.mem_read(owner_ptr, 0x408))
                native_target = bytes(cpu.mem_read(target_ptr, 0x408))
                for label, actual, expected_body in (
                        ('owner', native_owner, expected.owner),
                        ('target', native_target, expected.target)):
                    if label == 'owner':
                        expected_record = bytearray(expected_body.contact_record)
                        # 0x45cf70 clears the owner contact-link word after response.
                        struct.pack_into('<I', expected_record, 0x3C4, 0)
                    else:
                        expected_record = expected_body.contact_record
                    for offset, length in ((0x14, 12), (0x38, 12), (0x3C4, 0x3C)):
                        actual_part = actual[offset:offset + length]
                        expected_part = (bytes(expected_record[offset:offset + length])
                                         if offset == 0x3C4 else
                                         struct.pack('<3f', *(expected_body.linear_velocity
                                                              if offset == 0x14 else
                                                              expected_body.angular_turn_velocity)))
                        if offset == 0x3C4:
                            if actual_part != expected_part:
                                raise AssertionError(
                                    f'case {index}: {label} integrated response record differs')
                        else:
                            values_a = struct.unpack('<3f', actual_part)
                            values_b = struct.unpack('<3f', expected_part)
                            if any(abs(a - b) > max(3e-5, abs(b) * 5e-6)
                                   for a, b in zip(values_a, values_b)):
                                raise AssertionError(
                                    f'case {index}: {label} integrated response velocity differs')
    return {'entry': '0x45cf70', 'cases': count,
            'pair_filter_calls': reached_filter,
            'response_calls': total_response_calls if execute_pair_resolver else None,
            'retry_cases': retry_cases if execute_pair_resolver else None,
            'retry_attempts': total_retry_attempts if execute_pair_resolver else None,
            'response_impacts': response_impacts if execute_pair_resolver else None,
            'scope': ('candidate broadphase, pair-solver retries, and integrated pair response; original x86 execution'
                      if execute_pair_resolver else
                      'candidate broadphase and first-rejection path; original x86 execution')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    parser.add_argument('--execute-pair-resolver', action='store_true')
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases,
                             args.execute_pair_resolver)))
