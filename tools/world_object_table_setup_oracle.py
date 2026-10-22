"""Compare the 0x428710 object-table preparation loop to the exact client."""
import argparse
import json
import random
import struct

from client.world_object_table_setup import prepare_world_object_table
from tools.native_oracle import DynoOracle


OBJECTS = 0x0092C478
COUNT = 0x0097C180
TABLE_POINTER = 0x0097C404
ROWS = 0x71004000
SOURCES = 0x71006000


def verify(executable, cases=128):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    rng = random.Random(0x428710)

    def return_initializer(cpu, pc, size, _user):
        esp = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        return_address = struct.unpack('<I', cpu.mem_read(esp, 4))[0]
        cpu.reg_write(oracle.reg.UC_X86_REG_EAX, 0)
        cpu.reg_write(oracle.reg.UC_X86_REG_ESP, esp + 4)
        cpu.reg_write(oracle.reg.UC_X86_REG_EIP, return_address)

    def clear_child(cpu, pc, size, _user):
        esp = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
        return_address, destination, length = struct.unpack('<3I', cpu.mem_read(esp, 12))
        cpu.mem_write(destination, bytes(length))
        cpu.reg_write(oracle.reg.UC_X86_REG_EAX, destination)
        cpu.reg_write(oracle.reg.UC_X86_REG_ESP, esp + 4)
        cpu.reg_write(oracle.reg.UC_X86_REG_EIP, return_address)

    hook_init = oracle.cpu.hook_add(UC_HOOK_CODE, return_initializer,
                                    begin=0x426D50, end=0x426D50)
    hook_clear = oracle.cpu.hook_add(UC_HOOK_CODE, clear_child,
                                     begin=0x6EE0C0, end=0x6EE0C0)
    try:
        total_records = 0
        for case in range(cases):
            count = 1 + case % 3
            objects = bytearray(rng.randrange(256) for _ in range(count * 0x4F8))
            rows = bytearray(rng.randrange(256) for _ in range(count * 0x38))
            source_records = {}
            for index in range(count):
                address = SOURCES + index * 0x200
                source = bytes(rng.randrange(256) for _ in range(0xA8))
                source_records[address] = source
                struct.pack_into('<I', rows, index * 0x38 + 0x20, address)

            oracle._reset()
            oracle.cpu.mem_write(COUNT, struct.pack('<I', count))
            oracle.cpu.mem_write(TABLE_POINTER, struct.pack('<I', ROWS))
            oracle.cpu.mem_write(OBJECTS, bytes(objects))
            oracle.cpu.mem_write(ROWS, bytes(rows))
            for address, source in source_records.items():
                oracle.cpu.mem_write(address, source)
            oracle.cpu.ctl_remove_cache(0x428710, 0x4287A0)
            oracle.call(0x428710, instruction_limit=100000)

            expected = bytearray(objects)
            expected_rows = bytearray(rows)
            prepare_world_object_table(
                expected, expected_rows, source_records,
                object_base_address=OBJECTS,
                initialize_body=lambda _record: None)
            actual = bytes(oracle.cpu.mem_read(OBJECTS, len(expected)))
            actual_rows = bytes(oracle.cpu.mem_read(ROWS, len(expected_rows)))
            if actual != expected:
                offset = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise AssertionError(
                    f'0x428710 case {case} object byte {offset:#x}: '
                    f'native={actual[offset]:02x} python={expected[offset]:02x}')
            if actual_rows != expected_rows:
                offset = next(i for i, (a, b) in enumerate(zip(actual_rows, expected_rows))
                              if a != b)
                raise AssertionError(
                    f'0x428710 case {case} row byte {offset:#x}: '
                    f'native={actual_rows[offset]:02x} python={expected_rows[offset]:02x}')
            total_records += count
    finally:
        oracle.cpu.hook_del(hook_init)
        oracle.cpu.hook_del(hook_clear)
    return total_records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--cases', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps({
        'entry': '0x428710', 'cases': args.cases,
        'object_records': verify(args.executable, args.cases),
        'all_object_and_source_row_bytes_matched': True,
        'scope': 'original table loop with 0x426d50 and 0x6ee0c0 child boundaries intercepted',
    }))
