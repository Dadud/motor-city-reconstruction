"""Compare active-row dispatch at callback entry 0x426730 to the original."""
import argparse
import struct
from pathlib import Path

from client.world_object_array import update_active_world_objects
from client.world_object_record import RECORD_SIZE, update_object_array
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    base, stride, count_address = 0x0092C478, 0x4F8, 0x0097C180
    calls = []

    def skip_object_handler(machine, address, _size, _data):
        if address == 0x00520250:
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            calls.append(struct.unpack('<I', machine.mem_read(stack + 4, 4))[0])
            return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, return_address)

    cpu.hook_add(UC_HOOK_CODE, skip_object_handler,
                 begin=0x00520250, end=0x00520250)
    cases = ((), (True, False, True), (False, False, False), (False, True))
    for flags in cases:
        calls.clear()
        cpu.mem_write(count_address, struct.pack('<i', len(flags)))
        cpu.mem_write(base, bytes(stride * len(flags)))
        for index, active in enumerate(flags):
            address = base + index * stride
            cpu.mem_write(address + 4, struct.pack('<?', active))
        oracle.call(0x00426730)
        expected = []
        update_active_world_objects(base, flags, expected.append)
        if calls != expected:
            raise AssertionError(f'original dispatched {calls!r}, expected {expected!r}')

    # Now leave 0x520250 live and compare the composed active-array path,
    # including complete owner bytes for active and skipped rows.
    integrated = DynoOracle(executable)
    base, count_address = 0x0092C478, 0x0097C180
    patterns = ((), (True,), (True, False, True), (False, False, False))
    for flags in patterns:
        rows = []
        for index, active in enumerate(flags):
            row = bytearray(RECORD_SIZE)
            struct.pack_into('<I', row, 0, index + 1)
            row[4] = int(active)
            struct.pack_into('<3f', row, 8, 2.0, -3.0, 1.0)
            struct.pack_into('<3f', row, 0x14, 0.75, -0.25, 0.5)
            struct.pack_into('<3f', row, 0x38, 0.03125, -0.015625, 0.0078125)
            struct.pack_into('<3f', row, 0x5c, 0.25, -0.5, 0.125)
            struct.pack_into('<9f', row, 0x78, 1, 0, 0, 0, 1, 0, 0, 0, 1)
            struct.pack_into('<3f', row, 0x328, 0.5, -0.25, 1.0)
            struct.pack_into('<66f', row, 0xe0,
                             *((i % 7 - 3) / 8 for i in range(66)))
            rows.append(row)
        image = bytearray().join(rows)
        if image:
            integrated.cpu.mem_write(base, bytes(image))
        integrated.cpu.mem_write(count_address, struct.pack('<i', len(flags)))
        integrated.cpu.mem_write(0x00AA456C, struct.pack('<I', 0))
        integrated.call(0x00426730, instruction_limit=1_000_000)
        original = bytes(integrated.cpu.mem_read(base, len(image)))
        expected = update_object_array(bytearray(image), object_phase=0)
        if original != expected:
            differences = [i for i, (left, right) in
                           enumerate(zip(original, expected)) if left != right]
            raise AssertionError(f'composed 0x426730/0x520250 path differs at '
                                 f'{[hex(i) for i in differences[:16]]}')
    return len(cases), len(patterns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path, help='exact verified original executable')
    args = parser.parse_args()
    dispatch_cases, integrated_cases = verify(args.executable)
    print(f'original active-object dispatcher matches for {dispatch_cases} pointer cases; '
          f'composed dispatcher and child match complete bytes for {integrated_cases} cases')


if __name__ == '__main__':
    main()
