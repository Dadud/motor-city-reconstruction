"""Compare the decision-minus-one pair response branch in 0x45d1f0."""
import argparse
import json
import math
import random
import struct

from client.body_constructor import construct_body
from client.collision_world_candidate import (decode_collision_world_sample,
                                              update_world_contact)
from client.collision_world_pair import resolve_world_decision_minus_one
from tools.collision_world_decision_one_oracle import OWNER, TABLE, RECORD
from tools.collision_world_trigger_update_oracle import (OWNER_GLOBAL, RESOURCES,
                                                        SLOTS)
from tools.native_oracle import DynoOracle


SAMPLE_ID = 1
SAMPLE_STATE = 0x0097DBF0 + SAMPLE_ID * 3
PAIR_COEFFICIENTS = (0.8, 0.7)
CLASSIFIER_MINUS_ONE = (b'\xc7\x44\x24\x0c\x19\x00\x00\x00'
                        b'\xb8\xff\xff\xff\xff\xc3')
IGNORED_FLOATS = set(range(8, 0x20)) | set(range(0x38, 0x44))


def _sample(x, y, z, height):
    image = bytearray(0x14)
    struct.pack_into('<3i', image, 0, *(round(value * 65536.)
                                       for value in (x, y, z)))
    struct.pack_into('<h', image, 0x0c, height)
    struct.pack_into('<H', image, 0x0e, SAMPLE_ID)
    image[0x13] = 2
    return bytes(image)


def compare(executable, count=128, *, zero_proxy=False,
            real_classifier=False):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45D1F0FF)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    maximum_velocity_error = 0.0
    maximum_angular_error = 0.0
    collision_cases = 0
    temporary_body_cases = 0
    target_address = 0
    for index in range(count):
        body = bytearray(construct_body(bytes(0x2000), OWNER, 1000.,
                                        (1., 1., 1.), 0, 2))
        body_position = (rng.uniform(-.15, .15), rng.uniform(-.15, .15),
                         rng.uniform(-.15, .15))
        sample_position = (body_position[0] + .12 + (index % 3) * .035,
                           body_position[1] + rng.uniform(-.1, .1),
                           body_position[2] - .04)
        velocity_scale = rng.uniform(.2, 3.)
        direction = (sample_position[0] - body_position[0],
                     sample_position[2] - body_position[2])
        length = (direction[0] ** 2 + direction[1] ** 2) ** .5
        approach = 1. if index % 2 == 0 else -1.
        velocity = (approach * direction[0] / length * velocity_scale, 0.,
                    approach * direction[1] / length * velocity_scale)
        struct.pack_into('<3f', body, 8, *body_position)
        struct.pack_into('<3f', body, 0x14, *velocity)
        struct.pack_into('<f', body, 0x350, 0.)
        struct.pack_into('<f', body, 0x3b4, (index % 5) * .25)
        if real_classifier:
            struct.pack_into('<f', body, 0x3c0, 40000.)
        record = bytearray(_sample(*sample_position, 0 if zero_proxy else
                                   100 + (index % 40) * 10))
        if real_classifier:
            record[0x13] = 2
        record = bytes(record)
        decoded = decode_collision_world_sample(record)

        trigger_slots = bytes(0x1800)
        resources = [0] * 256
        resources[3] = 0x7100A003
        sample_state = bytes((0xff, 0, 0))
        expected_update = (update_world_contact(
            body, record, sample_state, trigger_slots, resources, 0x7100BEEF)
            if real_classifier else None)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097C408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, record)
        cpu.mem_write(SAMPLE_STATE, b'\xff')
        if real_classifier:
            cpu.mem_write(SLOTS, trigger_slots)
            cpu.mem_write(RESOURCES, struct.pack('<256I', *resources))
            cpu.mem_write(OWNER_GLOBAL, struct.pack('<I', 0x7100BEEF))
        else:
            # Isolate the sampled pair response when the classifier itself is
            # outside this oracle mode.
            cpu.mem_write(0x0042D9F0, CLASSIFIER_MINUS_ONE)
        cpu.mem_write(0x0089C070, struct.pack('<2f', *PAIR_COEFFICIENTS))
        captured = []

        def capture_solver(machine, address, _size, _user_data):
            if address == 0x00458530:
                stack = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
                owner_ptr, target_ptr, point_ptr, normal_ptr = struct.unpack(
                    '<4I', machine.mem_read(stack + 4, 16))
                captured.append((
                    target_ptr,
                    bytes(machine.mem_read(target_ptr, 0x418)),
                    struct.unpack('<3f', machine.mem_read(point_ptr, 12)),
                    struct.unpack('<3f', machine.mem_read(normal_ptr, 12))))

        from unicorn import UC_HOOK_CODE
        hook = cpu.hook_add(UC_HOOK_CODE, capture_solver)
        oracle.call(0x0045D1F0, (OWNER, 0), instruction_limit=3_000_000)
        actual = bytes(cpu.mem_read(OWNER, 0x408))
        if real_classifier:
            actual_state = bytes(cpu.mem_read(SAMPLE_STATE, 3))
            actual_slots = bytes(cpu.mem_read(SLOTS, 0x1800))
            if actual_state != expected_update.sample_state:
                raise AssertionError(f'case {index}: real classifier sample-state bytes differ')
            if actual_slots != expected_update.trigger_slots:
                difference = next(i for i, (a, b) in enumerate(
                    zip(actual_slots, expected_update.trigger_slots)) if a != b)
                start = difference // 0x18 * 0x18
                raise AssertionError(
                    f'case {index}: real allocator slot differs at {difference:#x}; '
                    f'native={actual_slots[start:start + 0x18].hex()} '
                    f'model={expected_update.trigger_slots[start:start + 0x18].hex()}')
        if captured:
            target_address, actual_target, _point, _normal = captured[-1]
        expected = resolve_world_decision_minus_one(
            body, decoded.position, decoded.vertical_value, 0x19, OWNER,
            target_address, *PAIR_COEFFICIENTS)
        if not captured:
            if expected.collided:
                raise AssertionError(f'case {index}: model expects solver call')
        else:
            _ptr, actual_target, point, normal = captured[-1]
            expected_point, expected_normal = expected.contact_point, expected.normal
            if point != expected_point or normal != expected_normal:
                raise AssertionError(
                    f'case {index}: contact frame {(point, normal)} != '
                    f'{(expected_point, expected_normal)}')
            if actual_target != expected.temporary_body_image[:0x418]:
                raise AssertionError(f'case {index}: temporary proxy body differs')
            temporary_body_cases += 1

        expected_body = expected.body_image
        for offset, label in ((0x14, 'velocity'), (0x38, 'angular velocity')):
            actual_values = struct.unpack_from('<3f', actual, offset)
            expected_values = struct.unpack_from('<3f', expected_body, offset)
            if any(math.isnan(a) != math.isnan(b) or
                   (not math.isnan(a) and not math.isnan(b) and
                    abs(a-b) > max(4e-5, abs(b) * 5e-6))
                   for a, b in zip(actual_values, expected_values)):
                raise AssertionError(f'case {index}: {label} {actual_values} != '
                                     f'{expected_values}')
            finite_errors = [abs(a-b) for a, b in zip(actual_values,
                                                      expected_values)
                             if math.isfinite(a) and math.isfinite(b)]
            maximum_error = max(finite_errors, default=0.0)
            if offset == 0x14:
                maximum_velocity_error = max(maximum_velocity_error,
                                             maximum_error)
            else:
                maximum_angular_error = max(maximum_angular_error,
                                            maximum_error)
        for offset, (a, b) in enumerate(zip(actual, expected_body)):
            if offset not in IGNORED_FLOATS and a != b:
                raise AssertionError(
                    f'case {index}: body {offset:#x}: {a:#x} != {b:#x}')
        collision_cases += int(expected.collided)
        cpu.hook_del(hook)
    return {'entry': '0x45d1f0', 'cases': count,
            'temporary_pair_calls': temporary_body_cases,
            'collisions': collision_cases,
            'maximum_absolute_velocity_error': maximum_velocity_error,
            'maximum_absolute_angular_error': maximum_angular_error,
            'zero_proxy': zero_proxy,
            'real_classifier': real_classifier,
            'scope': ('original decode, real classifier/allocator/heading writer, '
                      'proxy construction and pair/cache branch'
                      if real_classifier else
                      'original decode and proxy/pair/cache branch; classifier '
                      'forced to -1 and pair coefficients supplied')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    parser.add_argument('--zero-proxy', action='store_true')
    parser.add_argument('--real-classifier', action='store_true')
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases,
                             zero_proxy=args.zero_proxy,
                             real_classifier=args.real_classifier)))
