"""Compare maintenance + physics + translated track environment end to end."""
import argparse
import random
import struct
from pathlib import Path

from client.contact_force import contact_forces_step
from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.world_object_environment import EnvironmentCallbacks, environment_step
from client.world_object_physics_step import step_world_object_physics
from client.world_object_record import RECORD_SIZE, maintain_object_record
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import BASE, BLOCKS, PATH, fixture


OWNER = 0x0092C478


def verify(executable, cases=32):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x4265F051E940)
    cpu.mem_write(0x0097C180, struct.pack('<I', 1))
    for case in range(cases):
        mode = (2, 3, 4)[case % 3]
        cached = case % 2
        previous = (0, 1, 2)[case % 3]
        neighbors = (case // 3) % 2
        arena, root, query = fixture(mode, cached, previous, neighbors,
                                     7, 8, 8, case * 17)
        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0.0, 0.0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1.0, 1.0))
        for address, value in ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                               (0x00988E38, 24), (0x0097DBEC, 2),
                               (0x009AAA60, 1)):
            cpu.mem_write(address, struct.pack('<I', value))

        record = bytearray(RECORD_SIZE)
        struct.pack_into('<I', record, 0, case + 1)
        record[4] = 1
        record[6] = 0
        record[7] = 0
        position = (8.0 + rng.uniform(-0.15, 0.15), 2.0,
                    8.0 + rng.uniform(-0.15, 0.15))
        struct.pack_into('<3f', record, 8, *position)
        struct.pack_into('<3f', record, 0x358, *position)
        struct.pack_into('<3f', record, 0x14,
                         *(rng.uniform(-1, 1) for _ in range(3)))
        struct.pack_into('<3f', record, 0x38,
                         *(rng.uniform(-0.4, 0.4) for _ in range(3)))
        struct.pack_into('<9f', record, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
        points = []
        for _ in range(22):
            points.extend((rng.uniform(1, 15), rng.uniform(0, 0.4),
                           rng.uniform(1, 15)))
        struct.pack_into('<66f', record, 0xE0, *points)
        record[0x370:0x370 + 68] = query
        struct.pack_into('<I', record, 0x370, previous)
        struct.pack_into('<I', record, 0x378, 1)
        struct.pack_into('<3f', record, 0x370 + 44, 0.0, 1.0, 0.0)
        struct.pack_into('<f', record, 0x50, 1.5)
        struct.pack_into('<3f', record, 0x2F0, 0.7, 0.8, 0.9)
        struct.pack_into('<f', record, 0x6C, 0.0)
        struct.pack_into('<h', record, 0x3BC, case % 4)
        for offset in (0x248, 0x254, 0x260, 0x26C, 0x278, 0x284):
            struct.pack_into('<3f', record, offset, 1.0, 0.0, 0.0)
        for offset in (0x54, 0x2FC, 0x300, 0x304, 0x308, 0x30C,
                       0x310, 0x314, 0xD0, 0xCC, 0xD4, 0x9C, 0xA0,
                       0xA4, 0xA8, 0xAC, 0xB0, 0xB4, 0xB8, 0xBC):
            struct.pack_into('<f', record, offset, 1.0)
        cpu.mem_write(OWNER, bytes(record))
        mode_active = bool(case & 1)
        mode_number = case % 2
        cpu.mem_write(0x00AA459C, struct.pack('<B', int(mode_active)))
        cpu.mem_write(0x00A6CC40, struct.pack('<I', mode_number))

        # Native environment executes; collision correction is intercepted
        # only as a safety assertion because these fixtures hit valid surfaces.
        correction_calls = []
        def intercept(machine, address, _size, _data):
            if address in (0x0043BA40, 0x0043B750):
                correction_calls.append(address)
                raise AssertionError(f'unexpected correction branch at {address:#x}')
        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            oracle.call(0x004265F0, (), instruction_limit=1_000_000)
        finally:
            cpu.hook_del(hook)
        original = bytes(cpu.mem_read(OWNER, RECORD_SIZE))

        memory = TrackSurfaceMemory(grid, bytes(arena), BASE)
        world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                                  BLOCKS, PATH, 2, 24)
        callbacks = EnvironmentCallbacks(
            world, lambda *_: None, lambda _: None, 4.0)
        expected = bytearray(record)
        environment_hits = []
        def physics(owner):
            def update_environment(image):
                environment_step(image, callbacks=callbacks,
                                 environment_enabled=True)
                environment_hits.append(
                    struct.unpack_from('<I', image, 0x37C)[0] != 0)
            step_world_object_physics(
                owner, mode_active=mode_active, mode_number=mode_number,
                environment_step=update_environment,
                contact_force_step=contact_forces_step)
        maintain_object_record(expected, update_physics=physics)
        if original != expected:
            differences = [index for index, (left, right)
                           in enumerate(zip(original, expected)) if left != right]
            raise AssertionError(
                f'composed environment mismatch case={case} fixture='
                f'{mode,cached,previous,neighbors} bytes='
                f'{[hex(index) for index in differences[:20]]}; '
                f'native={[(hex(i), original[i:i+4].hex()) for i in differences[:10]]}; '
                f'python={[(hex(i), expected[i:i+4].hex()) for i in differences[:10]]}')
        if correction_calls:
            raise AssertionError(f'case {case} unexpectedly entered correction')
        if not environment_hits or not all(environment_hits):
            raise AssertionError(
                f'case {case} did not retain a successful surface descriptor: '
                f'{environment_hits}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=32)
    args = parser.parse_args()
    print(f'0x4265f0 + 0x520c20 + 0x51e940 + 0x51fc00 match '
          f'{verify(args.executable, args.cases)} complete owner records')


if __name__ == '__main__':
    main()
