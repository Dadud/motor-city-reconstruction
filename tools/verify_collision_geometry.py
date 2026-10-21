"""Compare the early 0x43bd30 collision filters and query point with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.collision_geometry import probe_collision_candidate
from client.track_topology import track_index_is_rejected
from tools.native_oracle import DynoOracle


TABLE = 0x71003000
OWNER = 0x72002000
OTHER = 0x72004000
TRAFFIC = 0x0092C7E8


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _row(rng, index, path_count, mask):
    row = bytearray(0x54)
    struct.pack_into('<3f', row, 0, *(rng.uniform(-20, 20) for _ in range(3)))
    struct.pack_into('<6f', row, 0x18, *(rng.uniform(-1, 1) for _ in range(6)))
    struct.pack_into('<2f', row, 0x38, _f32(rng.uniform(1, 8)),
                     _f32(rng.uniform(1, 8)))
    struct.pack_into('<II', row, 0x44, rng.randrange(5), rng.randrange(5))
    struct.pack_into('<I', row, 0x4c, mask)
    return bytes(row)


def _object(path_index, slot, active=True):
    row = bytearray(0xE7C)
    row[4] = int(active)
    struct.pack_into('<I', row, 0x370, path_index)
    struct.pack_into('<I', row, 0xE78, slot)
    return bytes(row)


def _traffic(path_index, offset):
    row = bytearray(0x4F8)
    struct.pack_into('<I', row, 0, path_index)
    struct.pack_into('<f', row, 0x48, offset)
    return bytes(row)


def verify(executable, cases=128):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x43BD30)
    cpu.mem_write(0x0097C38C, struct.pack('<I', TABLE))
    cpu.mem_write(0x00988E38, struct.pack('<I', 8))
    cpu.mem_write(0x009AAA74, struct.pack('<I', 1))
    cpu.mem_write(0x009AAA78, struct.pack('<I', 0))
    cpu.mem_write(0x009AAA7C, struct.pack('<I', 0))
    cpu.mem_write(0x009AAA90, struct.pack('<i', 0))
    cpu.mem_write(0x009AAA94, struct.pack('<i', 0))

    for case in range(cases):
        path_count = 8
        track_index = rng.randrange(path_count)
        longitudinal = _f32(rng.uniform(-40, 40))
        lateral = _f32(rng.uniform(-1, 1))
        rows = tuple(_row(rng, index, path_count,
                          0 if case % 7 == 0 else 0xffffffff)
                     for index in range(path_count))
        cpu.mem_write(TABLE, b''.join(rows))
        candidate_slot = rng.randrange(14)
        owner = bytearray(0xE7C)
        owner[4] = 1
        struct.pack_into('<I', owner, 0xE78, candidate_slot)
        cpu.mem_write(OWNER, bytes(owner))

        objects = []
        if case % 4 == 1:
            other_index = (track_index + rng.choice((-1, 0, 1))) % path_count
            other = _object(other_index, candidate_slot, active=bool(case & 2))
            objects.append(other)
            cpu.mem_write(OTHER, other)
            cpu.mem_write(0x0098C1E8, struct.pack('<I', OTHER))
        cpu.mem_write(0x0098C218, struct.pack('<I', len(objects)))

        traffic_rows = []
        if case % 5 == 2:
            traffic_index = (track_index + rng.choice((-1, 0, 1))) % path_count
            traffic = _traffic(traffic_index, longitudinal)
            traffic_rows.append(traffic)
            cpu.mem_write(TRAFFIC, traffic)
        cpu.mem_write(0x0097C180, struct.pack('<I', len(traffic_rows)))

        actual_samples = []

        def intercept(machine, address, _size, _data):
            if address == 0x0042E010:
                stack = machine.reg_read(reg.UC_X86_REG_ESP)
                ret, query, point, index = struct.unpack(
                    '<4I', machine.mem_read(stack, 16))
                point_value = struct.unpack('<3f', machine.mem_read(point, 12))
                actual_samples.append((point_value, index))
                machine.reg_write(reg.UC_X86_REG_EAX, 0)
                machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
                machine.reg_write(reg.UC_X86_REG_EIP, ret)

        hook = cpu.hook_add(UC_HOOK_CODE, intercept)
        try:
            offset_bits = struct.unpack('<I', struct.pack('<f', longitudinal))[0]
            lateral_bits = struct.unpack('<I', struct.pack('<f', lateral))[0]
            oracle.call(0x0043BD30,
                        (OWNER, track_index, offset_bits, 0, lateral_bits),
                        instruction_limit=500000)
        finally:
            cpu.hook_del(hook)
        original_result = oracle.cpu.reg_read(reg.UC_X86_REG_EAX) & 0xff

        expected_samples = []

        def sample(point, index):
            expected_samples.append((point, index))
            return False, None, 0.0

        translated_result = probe_collision_candidate(
            bytes(owner), track_index, longitudinal, lateral,
            path_rows=rows, path_count=path_count,
            range_start=0, range_end=0, lower_limit=0, upper_limit=0,
            clamp_indices=True, surface_vcall_result=0,
            world_objects=objects,
            traffic_rows=traffic_rows, sample_surface=sample)
        if bool(original_result) != translated_result or actual_samples != expected_samples:
            raise AssertionError(
                f'0x43bd30 early-filter mismatch case {case}: '
                f'index={track_index}, offset={longitudinal}, lateral={lateral}, '
                f'actual={bool(original_result)}/{actual_samples}, '
                f'translated={translated_result}/{expected_samples}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(f'0x43bd30 early collision gates and query-point construction match '
          f'{verify(args.executable, args.cases)} original cases with the '
          'surface sampler intercepted')


if __name__ == '__main__':
    main()
