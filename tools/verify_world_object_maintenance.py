"""Compare FUN_004265f0's own updates, with its 0x520c20 child isolated."""
import argparse
import struct
from pathlib import Path

from client.world_object_damping import WorldObjectMotion
from client.world_object_maintenance import WorldObjectMaintenance
from client.world_object_record import RECORD_SIZE, maintain_object_record
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    owner = 0x0092C478  # first object, inferred from pfVar3 - 5 floats
    cpu.mem_write(0x0097C180, struct.pack('<i', 1))

    def skip_child(machine, address, _size, _data):
        if address == 0x00520C20:
            stack = machine.reg_read(reg.UC_X86_REG_ESP)
            return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
            machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
            machine.reg_write(reg.UC_X86_REG_EIP, return_address)

    cpu.hook_add(UC_HOOK_CODE, skip_child, begin=0x00520C20, end=0x00520C20)
    cases = (
        WorldObjectMaintenance(WorldObjectMotion(0, (4, 5, 6), (1, 2, 3)), True, 0, 1),
        WorldObjectMaintenance(WorldObjectMotion(0, (1, 2, 3), (12, 0, 0)), True, 1, 1),
        WorldObjectMaintenance(WorldObjectMotion(0, (4, 5, 6), (12, 0, 0)), True, 0, 1),
        WorldObjectMaintenance(WorldObjectMotion(33, (0, 0, 0), (0, 0, 0)), True, 0, 0),
        WorldObjectMaintenance(WorldObjectMotion(32, (0, 0, 0), (0, 0, 0)), True, 0, 0),
        WorldObjectMaintenance(WorldObjectMotion(0, (4, 5, 6), (1, 2, 3)), False, 0, 1),
    )
    for case in cases:
        record = bytearray(RECORD_SIZE)
        record[4] = int(case.active)
        struct.pack_into('<3f', record, 0x14, *case.motion.linear_velocity)
        struct.pack_into('<3f', record, 0x38, *case.motion.angular_velocity)
        struct.pack_into('<f', record, 0xD8, case.reference_value)
        struct.pack_into('<f', record, 0x350, case.maintenance_value)
        struct.pack_into('<h', record, 0x3BC, case.motion.contact_counter)
        cpu.mem_write(owner, bytes(record))
        oracle.call(0x004265F0)
        actual = bytes(cpu.mem_read(owner, RECORD_SIZE))
        expected = bytearray(record)
        maintain_object_record(expected, update_physics=lambda _record: None)
        if actual != expected:
            differences = [index for index, (left, right) in
                           enumerate(zip(actual, expected)) if left != right]
            raise AssertionError(f'original record mismatch for {case} at '
                                 f'{[hex(index) for index in differences[:16]]}')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path, help='exact verified original executable')
    args = parser.parse_args()
    print(f'original maintenance callback matches for {verify(args.executable)} cases')


if __name__ == '__main__':
    main()
