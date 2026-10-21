"""Compare 0x51e940 with the Python 0x42e760 query and mapped track world."""
import argparse
import random
import struct
from pathlib import Path

from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.world_object_environment import EnvironmentCallbacks, environment_step
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import (BASE, BLOCKS, PATH, configurations,
                                       fixture)


def verify(executable, cases=128, start=0):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x51E940)
    configurations_list = list(configurations())
    selected = [configurations_list[(start + i) % len(configurations_list)]
                for i in range(cases)]
    owner = 0x7100C000
    for case, (mode, cached, previous, neighbors, upward, x, z, seed) in enumerate(selected):
        arena, root, query = fixture(mode, cached, previous, neighbors,
                                     upward, x, z, seed)
        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0.0, 0.0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1.0, 1.0))
        for address, value in ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                               (0x00988E38, 24), (0x0097DBEC, 2),
                               (0x009AAA60, 1)):
            cpu.mem_write(address, struct.pack('<I', value))

        record = bytearray(0x4F8)
        record[4] = 1
        position = (float(x), 2.0, float(z))
        struct.pack_into('<3f', record, 8, *position)
        struct.pack_into('<3f', record, 0x358, *position)
        struct.pack_into('<3f', record, 0x14,
                         *(rng.uniform(-1.0, 1.0) for _ in range(3)))
        struct.pack_into('<9f', record, 0x78, 1,0,0, 0,1,0, 0,0,1)
        struct.pack_into('<66f', record, 0xE0,
                         *(rng.uniform(-1.0, 1.0) for _ in range(66)))
        record[0x370:0x370 + 68] = query
        # 0x42e760 tests retained cache fields, so keep their pointers and
        # coefficients from the dedicated fixture while supplying valid
        # downstream track-row/mode selectors for 0x42df00.
        struct.pack_into('<I', record, 0x370, previous if previous < 24 else 0)
        struct.pack_into('<I', record, 0x378, 1)
        struct.pack_into('<3f', record, 0x370 + 44, 0.0, 1.0, 0.0)
        cpu.mem_write(owner, bytes(record))
        try:
            oracle.call(0x0051E940, (owner,), instruction_limit=500000)
        except Exception as error:
            eip = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EIP)
            raise RuntimeError(f'original 0x51e940 fault case={case} config='
                               f'{(mode,cached,previous,neighbors,upward,x,z,seed)} '
                               f'EIP={eip:#x}') from error
        original = bytes(cpu.mem_read(owner, len(record)))

        memory = TrackSurfaceMemory(grid, bytes(arena), BASE)
        world = TrackSurfaceWorld(memory, (0.0, 0.0), (1.0, 1.0),
                                  BLOCKS, PATH, 2, 24)
        callbacks = EnvironmentCallbacks(
            world=world,
            adjust_contact=lambda *_: None,
            reset_vehicle_state=lambda _: None,
            vertical_step=4.0)
        translated = bytearray(record)
        environment_step(translated, callbacks=callbacks, environment_enabled=True)
        if original != translated:
            differences = [i for i, (a, b) in enumerate(zip(original, translated)) if a != b]
            raise AssertionError(
                f'0x51e940 mismatch in case {case} fixture={mode,cached,previous,neighbors,upward,x,z} '
                f'at {[hex(i) for i in differences[:24]]}; '
                f'original={[(hex(i), original[i:i+4].hex()) for i in differences[:12]]}; '
                f'translated={[(hex(i), translated[i:i+4].hex()) for i in differences[:12]]}; '
                f'input_position={position!r}; velocity={struct.unpack_from("<3f", record, 0x14)!r}; '
                f'local_points={struct.unpack_from("<9f", record, 0xe0)!r}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    parser.add_argument('--start', type=int, default=0)
    args = parser.parse_args()
    print(f'0x51e940 full owner records match for {verify(args.executable, args.cases, args.start)} cases '
          'with actual 0x42e760 source logic and bounded mapped track data')


if __name__ == '__main__':
    main()
