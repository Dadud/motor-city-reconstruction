"""Compare TRxx.CAN decoding and coordinate normalization with 0x407570."""
import json
from pathlib import Path
import random
import struct

from unicorn import UC_HOOK_CODE

from client.collision_trigger_resources import normalize_collision_trigger_archive
from tools.native_oracle import DynoOracle


TABLE = 0x008E5390


def _archive(rng, count):
    data = bytearray(8 + count * 0x14)
    struct.pack_into('<IH', data, 0, rng.getrandbits(32), count)
    struct.pack_into('<H', data, 6, rng.randrange(0x10000))
    for index in range(count):
        values = tuple(rng.randint(-0x70000000, 0x70000000) for _ in range(3))
        struct.pack_into('<3i', data, 8 + index * 0x14, *values)
        struct.pack_into('<II', data, 8 + index * 0x14 + 12,
                         rng.getrandbits(32), rng.getrandbits(32))
    return bytes(data)


def compare(executable, count=48, data_root=None):
    if type(count) is not int or count < 1:
        raise ValueError('case count must be positive')
    rng = random.Random(0x407570)
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    resource_addrs = [oracle.inputs + 0x1000 * (i + 1) for i in range(7)]
    resources = []

    def callbacks(machine, address, _size, _user):
        if address == 0x699330:
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
            machine.reg_write(oracle.reg.UC_X86_REG_EAX, 0)
            machine.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
            machine.reg_write(oracle.reg.UC_X86_REG_EIP, ret)
        elif address == 0x6E1850:
            sp = machine.reg_read(oracle.reg.UC_X86_REG_ESP)
            index = len(load_order)
            load_order.append(index)
            ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
            pointer = resource_addrs[index] if index < len(resources) else 0
            machine.reg_write(oracle.reg.UC_X86_REG_EAX, pointer)
            machine.reg_write(oracle.reg.UC_X86_REG_ESP, sp + 4)
            machine.reg_write(oracle.reg.UC_X86_REG_EIP, ret)

    cpu.hook_add(UC_HOOK_CODE, callbacks)
    actual_archives = None
    if data_root is not None:
        root = Path(data_root)
        paths = [root / 'TR00A.CAN'] + [root / f'TR{index:02}.CAN'
                                         for index in range(1, 7)]
        actual_archives = [path.read_bytes() for path in paths]
    total_cases = count + int(actual_archives is not None)
    for case in range(total_cases):
        archive_count = (0, 1, 6, 17, 41, 51, 94)[case % 7]
        resources = [_archive(rng, (archive_count + i * 13) % 95)
                     for i in range(7)]
        if case % 9 == 0:
            resources = resources[:case % 7]
        if case == count and actual_archives is not None:
            resources = actual_archives
        expected = [normalize_collision_trigger_archive(item).encode()
                    for item in resources]
        oracle._reset()
        load_order = []
        for index, item in enumerate(resources):
            cpu.mem_write(resource_addrs[index], item)
        cpu.mem_write(TABLE, bytes(7 * 4))
        oracle.call(0x407570, (), instruction_limit=2_000_000)
        actual_count = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        expected_count = len(resources)
        if actual_count != expected_count:
            raise AssertionError(
                f'case {case}: loader returned {actual_count}, expected {expected_count}')
        expected_attempts = expected_count + 1
        if load_order != list(range(expected_attempts)):
            raise AssertionError(f'case {case}: loaded slots {load_order!r}')
        actual_pointers = struct.unpack('<7I', cpu.mem_read(TABLE, 28))
        expected_pointers = tuple(
            resource_addrs[i] if i < expected_count else 0 for i in range(7))
        if actual_pointers != expected_pointers:
            raise AssertionError(
                f'case {case}: resource pointers {actual_pointers!r} != {expected_pointers!r}')
        for index, item in enumerate(resources):
            actual = bytes(cpu.mem_read(resource_addrs[index], len(item)))
            if actual != expected[index]:
                for offset, (a, b) in enumerate(zip(actual, expected[index])):
                    if a != b:
                        break
                raise AssertionError(
                    f'case {case}, archive {index}: normalized bytes differ at '
                    f'{offset:#x} (actual={actual[offset:offset + 12].hex()}, '
                    f'expected={expected[index][offset:offset + 12].hex()}, '
                    f'input={item[offset:offset + 12].hex()})')
    loaded_archives = sum(7 if case % 9 else case % 7 for case in range(count))
    if actual_archives is not None:
        loaded_archives += 7
    return {'entry': '0x407570', 'cases': total_cases,
            'loaded_archives': loaded_archives,
            'scope': 'seven resource slots, missing-file termination, record bounds and all 20-byte record writes against the original loader'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=48)
    parser.add_argument('--data-root',
                        help='GameArt directory containing TR00A.CAN and TR01.CAN through TR06.CAN')
    args = parser.parse_args()
    print(json.dumps(compare(args.executable, args.cases, args.data_root)))
