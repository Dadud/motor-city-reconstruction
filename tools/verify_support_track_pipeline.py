"""Compare original 0x53d320 with its real 0x42e010 terrain dependency."""
import argparse
import struct

from client.driving_support import project_track_surface
from client.support_prediction import SupportRecord, predict_support
from client.track_surface_lookup import TrackSurfaceMemory, TrackSurfaceWorld
from tools.native_oracle import DynoOracle
from tools.support_prediction_oracle import cases, encode
from tools.track_surface_cases import BASE, BLOCKS, GEOMETRY, PATH, fixture


def verify(executable, limit=48):
    oracle = DynoOracle(executable)
    cpu, reg, owner = oracle.cpu, oracle.reg, oracle.inputs + 0x8000
    cpu.mem_write(0x8c4674, b'\0'); cpu.mem_write(0x8c465c, b'\0')
    vertices = ((0, 0, 0), (16, 1, 0), (16, 3, 16), (0, -2, 16))
    checked = 0
    for source, _ in list(cases())[:limit]:
        # Keep all four support points above the same known triangle while
        # retaining each fixture's transform, velocity, references and bytes.
        from dataclasses import replace
        source = replace(source, position=(8., 7., 8.), context=0,
                         wheels=tuple(replace(w, local_point=(0., 0., 0.),
                                              world_point=(8., 7., 8.),
                                              record=SupportRecord())
                                      for w in source.wheels))
        arena, root, _ = fixture(2, 0, 0, 0, 7, 8, 8, checked + 1)
        for block in range(3):
            for vertex, coordinates in enumerate(vertices):
                struct.pack_into('<3f', arena, GEOMETRY - BASE + block * 0x200 + vertex * 12,
                                 *coordinates)
        grid = root + bytes(65536 - len(root))
        cpu.mem_write(BASE, bytes(arena)); cpu.mem_write(0xa559d8, grid)
        cpu.mem_write(0xa55970, struct.pack('<2f', 0, 0))
        cpu.mem_write(0xa659d8, struct.pack('<2f', 1, 1))
        for address, value in ((0x0097c408, BLOCKS), (0x0097c38c, PATH),
                               (0x00988e38, 24), (0x0097dbec, 2)):
            cpu.mem_write(address, struct.pack('<I', value))
        world = TrackSurfaceWorld(TrackSurfaceMemory(grid, bytes(arena), BASE),
            (0., 0.), (1., 1.), BLOCKS, PATH, 2, 24)
        expected_prediction = predict_support(source, lambda q: project_track_surface(
            world, q, normal_seed=(.3, .8, -.2)))
        oimage = bytearray(encode(source))
        for i, wheel in enumerate(expected_prediction.state.wheels):
            base = 0x5fc + i * 0x10c
            record = wheel.record
            struct.pack_into('<ii6I', oimage, base + 0x14,
                record.sector, record.group, record.status, record.surface_id or 0,
                *(value or 0 for value in record.vertex_ids))
        oracle._reset(); cpu.mem_write(owner, bytes(oimage))
        stack = oracle.frame - 0x1000
        cpu.mem_write(stack, struct.pack('<II', oracle.stop, owner))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack)
        try:
            oracle._run(0x53d320, oracle.stop, count=30000)
        except Exception as error:
            raise RuntimeError((error, hex(cpu.reg_read(reg.UC_X86_REG_EIP)),
                hex(struct.unpack('<I',cpu.mem_read(0x97c408,4))[0]),
                {name:hex(cpu.reg_read(getattr(reg,'UC_X86_REG_'+name)))
                 for name in ('EAX','EBX','ECX','EDX','ESI','EDI','EBP')})) from error
        actual = bytes(cpu.mem_read(owner, len(oimage)))
        expected = bytearray(encode(expected_prediction.state, raw_addresses=True))
        for i, wheel in enumerate(expected_prediction.state.wheels):
            base = 0x5fc + i * 0x10c; record = wheel.record
            struct.pack_into('<ii6I', expected, base + 0x14,
                record.sector, record.group, record.status, record.surface_id or 0,
                *(value or 0 for value in record.vertex_ids))
        if actual != bytes(expected):
            offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
            raise AssertionError((checked, hex(offset), actual[offset:offset+16].hex(),
                                  bytes(expected[offset:offset+16]).hex()))
        checked += 1
    return {'cases': checked, 'owner_bytes': 'exact',
            'scope': 'original 0x53d320 with original 0x42e010/0x42e760/0x42dc50 and triangle plane; full wheel-owner image including aliased 24-byte query tails'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable'); parser.add_argument('--cases', type=int, default=48)
    args = parser.parse_args(); print(verify(args.executable, args.cases))
