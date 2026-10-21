"""Compare the 0x42e010 track-surface sampling composition with the original."""
import argparse
import struct
from pathlib import Path

from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from client.track_surface_sample import sample_track_surface
from tools.native_oracle import DynoOracle
from tools.track_surface_cases import (BASE, BLOCKS, GEOMETRY, PATH,
                                       configurations, fixture)


def verify(executable, cases=1200):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    max_height_error = 0.0
    sampled = 0
    for case_index, (mode, cached, previous, neighbors, upward, x, z, seed) in enumerate(
            configurations()):
        arena, root, initial_query = fixture(
            mode, cached, previous, neighbors, upward, x, z, seed)
        vertices = ((0, 0, 0), (16, 1, 0), (16, 3, 16), (0, -2, 16))
        for block in range(3):
            for vertex, coordinates in enumerate(vertices):
                struct.pack_into('<3f', arena,
                                 GEOMETRY - BASE + block * 0x200 + vertex * 12,
                                 *coordinates)
        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena))
        cpu.mem_write(0x00A559D8, grid)
        cpu.mem_write(0x00A55970, struct.pack('<2f', 0, 0))
        cpu.mem_write(0x00A659D8, struct.pack('<2f', 1, 1))
        for address, value in ((0x0097C408, BLOCKS), (0x0097C38C, PATH),
                               (0x00988E38, 24), (0x0097DBEC, 2)):
            cpu.mem_write(address, struct.pack('<I', value))

        query_address, point_address = BASE + 0x8000, BASE + 0x8100
        input_point = bytearray(struct.pack('<3f', x, 7.0, z))
        cpu.mem_write(query_address, bytes(initial_query))
        cpu.mem_write(point_address, bytes(input_point))
        oracle.call(0x0042E010, (query_address, point_address, 0),
                    instruction_limit=500000)
        original_result = cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xffffffff
        original_query = cpu.mem_read(query_address, 68)
        original_point = cpu.mem_read(point_address, 12)

        query = bytearray(initial_query)
        point = bytearray(input_point)
        world = TrackSurfaceWorld(
            TrackSurfaceMemory(grid, bytes(arena), BASE), (0.0, 0.0), (1.0, 1.0),
            BLOCKS, PATH, 2, 24)
        result = sample_track_surface(world, query, point, 0)
        expected = struct.unpack('<3f', original_point)
        actual = struct.unpack('<3f', point)
        height_error = abs(expected[1] - actual[1])
        max_height_error = max(max_height_error, height_error)
        if result:
            sampled += 1
        if (int(result) != original_result or bytes(query) != original_query or
                actual[0] != expected[0] or actual[2] != expected[2] or
                height_error > 2e-6):
            raise AssertionError(
                f'0x42e010 mismatch case={case_index} mode={mode} cached={cached} '
                f'result={result}/{original_result} point={actual}/{expected} '
                f'height_error={height_error}; query equal={bytes(query) == original_query}')
    return cases, sampled, max_height_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=1200)
    args = parser.parse_args()
    cases, sampled, error = verify(args.executable, args.cases)
    print(f'0x42e010 return/query state matches {cases} original cases; '
          f'{sampled} sampled surfaces, max height error {error:.9g}')


if __name__ == '__main__':
    main()
