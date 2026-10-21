"""Compare the 0x51e460 post-environment finalizer with the original binary."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_contact import (apply_contact_frame,
                                         finish_contact_frame,
                                         prepare_contact_frame)
from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.world_object_environment import EnvironmentCallbacks
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import BASE, BLOCKS, PATH, configurations, fixture

RECORD = 0x72002000
POSITION = 0x71003000


def _plant_world(oracle, arena, root):
    cpu = oracle.cpu
    grid = root + bytes(65536 - len(root))
    cpu.mem_write(BASE, bytes(arena))
    cpu.mem_write(0x00A559D8, grid)
    cpu.mem_write(0x00A55970, struct.pack('<2f', 0.0, 0.0))
    cpu.mem_write(0x00A659D8, struct.pack('<2f', 1.0, 1.0))
    for address, value in ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                           (0x00988E38, 24), (0x0097DBEC, 2),
                           (0x009AAA60, 1)):
        cpu.mem_write(address, struct.pack('<I', value))
    return grid


def verify(executable, cases=16):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x51E46F)
    configs = list(configurations())
    selected = [configs[(i * 53 + 17) % len(configs)] for i in range(cases)]
    maximum_error = 0.0
    float_offsets = (set(range(8, 20, 4)) | set(range(0x78, 0xcc, 4))
                     | set(range(0x1e8, 0x2f0, 4))
                     | set(range(0x31c, 0x364, 4)) | {0x350, 0x3b4, 0x3b8})
    for case, (mode, cached, previous, neighbors, upward, _x, _z, seed) in enumerate(selected):
        arena, root, query = fixture(mode, cached, previous, neighbors,
                                     upward, 8, 8, seed)
        row = [8.0, 0.0, 8.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0,
               1.0, 0.0, 0.0] + [0.0] * 9
        struct.pack_into('<21f', arena, PATH - BASE, *row)
        grid = _plant_world(oracle, arena, root)

        initial = bytearray(rng.randbytes(0x4f8))
        struct.pack_into('<I', initial, 4, 1)
        struct.pack_into('<3f', initial, 8, 8.0, 2.0, 8.0)
        struct.pack_into('<3f', initial, 0x358, 8.0, 2.0, 8.0)
        struct.pack_into('<3f', initial, 0x14, 0.1, 0.2, -0.1)
        struct.pack_into('<9f', initial, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        points = []
        for _ in range(22):
            points.extend((rng.uniform(2, 14), rng.uniform(-0.5, 0.5),
                           rng.uniform(2, 14)))
        struct.pack_into('<66f', initial, 0xe0, *points)
        position = (8.0, 2.0, 8.0)
        flags = 4

        # Run the real environment child from the exact record prefix produced
        # by this routine; its independent reconstruction has its own verifier.
        prefix = bytearray(initial)
        prepare_contact_frame(prefix, (tuple(row),), 0, position, flags)
        cpu.mem_write(RECORD, bytes(prefix))
        oracle.call(0x0051E940, (RECORD,), instruction_limit=800000)
        environment_result = bytes(cpu.mem_read(RECORD, 0x4f8))

        # Execute 0x51e460's real suffix while supplying that captured child
        # result at the child boundary, preserving the original stack locals.
        cpu.mem_write(RECORD, bytes(initial))
        cpu.mem_write(POSITION, struct.pack('<3f', *position))
        stopped = []

        def intercept(machine, address, _size, _data):
            if address != 0x0051E940:
                return
            machine.mem_write(RECORD, environment_result)
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            ret = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, ret)
            stopped.append(True)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x0051E460, (RECORD, 0, POSITION, flags),
                        instruction_limit=1_000_000)
        finally:
            cpu.hook_del(hook)
        if not stopped:
            raise AssertionError(f'case {case} did not reach environment boundary')
        original = bytes(cpu.mem_read(RECORD, 0x4f8))

        expected = bytearray(environment_result)
        # The caller stores the selected path row's surface value immediately
        # after the child returns; this precedes the clearance loop.
        struct.pack_into('<f', expected, 0x34c, row[1])
        memory = TrackSurfaceMemory(grid, bytes(arena), BASE)
        world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                                  BLOCKS, PATH, 2, 24)
        try:
            finish_contact_frame(expected, world=world, track_index=0)
        except Exception as error:
            raise RuntimeError(f'case {case} fixture={(mode,cached,previous,neighbors,upward,seed)}') from error

        # The original call above ran to the function return. Keep every byte
        # comparison because the remaining owner fields should be untouched.
        for offset in range(0, 0x4f8, 4):
            actual_word, expected_word = original[offset:offset + 4], expected[offset:offset + 4]
            if actual_word == expected_word:
                continue
            if offset in float_offsets:
                actual_value = struct.unpack('<f', actual_word)[0]
                expected_value = struct.unpack('<f', expected_word)[0]
                error = abs(actual_value - expected_value)
                maximum_error = max(maximum_error, error)
                if error <= 2e-4:
                    continue
            raise AssertionError(f'case {case} 0x51e460 mismatch at {offset:#x}: '
                                 f'native={actual_word.hex()} python={expected_word.hex()}')

        # Verify the composed port against an uninterrupted original caller,
        # including the environment stage and its real lookup data.
        cpu.mem_write(RECORD, bytes(initial))
        cpu.mem_write(POSITION, struct.pack('<3f', *position))
        oracle.call(0x0051E460, (RECORD, 0, POSITION, flags),
                    instruction_limit=1_000_000)
        full_original = bytes(cpu.mem_read(RECORD, 0x4f8))
        translated = bytearray(initial)
        callbacks = EnvironmentCallbacks(world=world,
            adjust_contact=lambda *_: None, reset_vehicle_state=lambda _: None,
            vertical_step=4.0)
        apply_contact_frame(translated, track_rows=(tuple(row),), track_index=0,
                            query_position=position, flags=flags,
                            environment_callbacks=callbacks,
                            environment_enabled=True)
        for offset in range(0, 0x4f8, 4):
            actual_word = full_original[offset:offset + 4]
            expected_word = translated[offset:offset + 4]
            if actual_word == expected_word:
                continue
            if offset in float_offsets:
                actual_value = struct.unpack('<f', actual_word)[0]
                expected_value = struct.unpack('<f', expected_word)[0]
                error = abs(actual_value - expected_value)
                maximum_error = max(maximum_error, error)
                if error <= 2e-4:
                    continue
            raise AssertionError(f'case {case} composed 0x51e460 mismatch at {offset:#x}: '
                                 f'native={actual_word.hex()} python={expected_word.hex()}')
    return cases, maximum_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=16)
    args = parser.parse_args()
    cases, error = verify(args.executable, args.cases)
    print(f'0x51e460 suffix and composed routine match {cases} original executions; '
          f'maximum compared float-field error {error:.9g}')


if __name__ == '__main__':
    main()
