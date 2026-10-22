"""Compare conditional sampled-world event dispatch in 0x45d1f0."""
import argparse
import json
import random
import struct

from client.body_constructor import construct_body
from client.collision_world_candidate import decode_collision_world_sample
from client.collision_world_response import resolve_world_decision_one_sample
from tools.collision_world_decision_one_oracle import OWNER, RECORD, TABLE, _sample
from tools.native_oracle import DynoOracle


HANDLER = 0x7100C000
HANDLER_VTABLE = 0x0083C170
BODY_BYTES = 0x1100


def _close(actual, expected, tolerance):
    return abs(actual - expected) <= max(tolerance, abs(expected) * 5e-6)


def compare(executable, count=128):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x45D1F0E7)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    queued = 0
    handler_count = 0
    maximum_position_error = 0.0
    maximum_velocity_error = 0.0
    for index in range(count):
        body = bytearray(construct_body(bytearray(0x2000), OWNER, 1.,
                                        (1., 1., 1.), 0, 0))
        struct.pack_into('<3f', body, 8, 0., rng.uniform(-.3, .3), 0.)
        struct.pack_into('<3f', body, 0x14, 1. if index % 2 == 0 else -1.,
                         0., 0.)
        struct.pack_into('<f', body, 0x350, 0.)
        struct.pack_into('<h', body, 0x3bc, 1)
        struct.pack_into('<66f', body, 0xe0, *([1., 0., 0.] * 22))
        struct.pack_into('<66f', body, 0x1e8, *([.125, .25, .375] * 22))
        body[6] = 1
        struct.pack_into('<i', body, 0x464, 0)
        struct.pack_into('<I', body, 0x474, 2)

        sample = _sample(rng.uniform(.2, .6))
        decoded = decode_collision_world_sample(sample)
        event_clock = rng.randrange(0x100000000)
        handler_image = bytearray(0x40)
        struct.pack_into('<I', handler_image, 0, HANDLER_VTABLE)
        struct.pack_into('<I', handler_image, 0x28, index)
        handlers = (HANDLER,) + (0,) * 11
        expected = resolve_world_decision_one_sample(
            body, decoded.position, decoded.vertical_value, 0x1d,
            handlers, event_clock, handler_image)

        oracle._reset()
        cpu.mem_write(OWNER, bytes(body))
        cpu.mem_write(0x0097C408, struct.pack('<I', TABLE))
        cpu.mem_write(TABLE + 0x684, struct.pack('<I', 1))
        cpu.mem_write(TABLE + 0x688, struct.pack('<I', RECORD))
        cpu.mem_write(RECORD, sample)
        cpu.mem_write(0x0098F38C, struct.pack('<12I', *handlers))
        cpu.mem_write(HANDLER, bytes(handler_image))
        cpu.mem_write(0x00AA456C, struct.pack('<I', event_clock))
        # Audio dispatch is an independent outer side effect in this experiment.
        cpu.mem_write(0x00487490, b'\xc3')
        oracle.call(0x45D1F0, (OWNER, 0), instruction_limit=2_000_000)
        actual = bytes(cpu.mem_read(OWNER, BODY_BYTES))
        actual_handler = bytes(cpu.mem_read(HANDLER, len(handler_image)))
        wanted = expected.body_image[:BODY_BYTES]
        actual_position = struct.unpack_from('<3f', actual, 8)
        wanted_position = struct.unpack_from('<3f', wanted, 8)
        actual_velocity = struct.unpack_from('<3f', actual, 0x14)
        wanted_velocity = struct.unpack_from('<3f', wanted, 0x14)
        maximum_position_error = max(
            maximum_position_error,
            *(abs(a - b) for a, b in zip(actual_position, wanted_position)))
        maximum_velocity_error = max(
            maximum_velocity_error,
            *(abs(a - b) for a, b in zip(actual_velocity, wanted_velocity)))
        for label, actual_values, expected_values, tolerance in (
                ('position', actual_position, wanted_position, 2e-6),
                ('velocity', actual_velocity, wanted_velocity, 4e-5)):
            if not all(_close(a, b, tolerance)
                       for a, b in zip(actual_values, expected_values)):
                raise AssertionError(
                    f'case {index}: {label} {actual_values} != {expected_values}')
        ignored = set(range(8, 0x20)) | set(range(0x38, 0x44))
        for offset, (actual_byte, expected_byte) in enumerate(zip(actual, wanted)):
            if offset not in ignored and actual_byte != expected_byte:
                raise AssertionError(
                    f'case {index}: body {offset:#x}: '
                    f'{actual_byte:#x} != {expected_byte:#x}')
        if actual_handler != expected.handler_image:
            raise AssertionError(f'case {index}: handler object differs')
        queued += int(expected.event_queued)
        handler_count += int(struct.unpack_from('<I', actual_handler, 0x28)[0] == index + 1)
    return {'entry': '0x45d1f0', 'cases': count,
            'queued_events': queued, 'handler_counter_updates': handler_count,
            'maximum_absolute_position_error': maximum_position_error,
            'maximum_absolute_velocity_error': maximum_velocity_error,
            'scope': 'decision-one response and conditional 0x43b550 -> 0x465a00 -> 0x4658c0 event callback; audio target stubbed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    arguments = parser.parse_args()
    print(json.dumps(compare(arguments.executable, arguments.cases)))
