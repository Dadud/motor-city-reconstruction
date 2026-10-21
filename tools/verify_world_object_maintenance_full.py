"""Compare composed 0x4265f0 + 0x520c20 object updates to the original."""
import argparse
import random
import struct
from pathlib import Path

from client.contact_force import contact_forces_step
from client.world_object_physics_step import step_world_object_physics
from client.world_object_record import RECORD_SIZE, maintain_object_record
from tools.native_oracle import DynoOracle


OWNER = 0x0092C478


def _record(rng, active, object_mode_flag, special, contacts, acceleration_gate,
            mode_active, mode_number):
    record = bytearray(RECORD_SIZE)
    struct.pack_into('<I', record, 0, 1)
    record[4] = int(active)
    record[6] = int(object_mode_flag)
    record[7] = int(special)
    struct.pack_into('<3f', record, 0x14, 1.25, -2.5, 0.75)
    struct.pack_into('<3f', record, 0x38, 0.125, -0.25, 0.5)
    struct.pack_into('<f', record, 0x6c, acceleration_gate)
    struct.pack_into('<h', record, 0x3bc, contacts)
    basis = tuple(rng.uniform(-2, 2) for _ in range(9))
    struct.pack_into('<9f', record, 0x31c, *basis)
    struct.pack_into('<f', record, 0x50, rng.uniform(0, 5))
    struct.pack_into('<3f', record, 0x2f0,
                     *(rng.uniform(0, 3) for _ in range(3)))
    for offset in (0x248, 0x254, 0x260, 0x26c, 0x278, 0x284):
        struct.pack_into('<3f', record, offset,
                         rng.uniform(.5, 2), rng.uniform(-.5, .5),
                         rng.uniform(-.5, .5))
    for offset in (0x54, 0x2fc, 0x300, 0x304, 0x308, 0x30c,
                   0x310, 0x314, 0xd0, 0xcc, 0xd4, 0x9c,
                   0xa0, 0xa4, 0xa8, 0xac, 0xb0, 0xb4,
                   0xb8, 0xbc):
        struct.pack_into('<f', record, offset, rng.uniform(.25, 2))
    struct.pack_into('<f', record, 0x350, 0.0)
    struct.pack_into('<f', record, 0xd8, 1.0)
    return record


def verify(executable, cases=64):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4265F0)
    cpu.mem_write(0x0097C180, struct.pack('<I', 1))
    cpu.hook_add(UC_HOOK_CODE,
        lambda machine, address, _size, _data: _skip_environment(machine, address, reg),
        begin=0x0051E940, end=0x0051E940)
    for case in range(cases):
        mode_active = bool(rng.getrandbits(1))
        mode_number = rng.randrange(2)
        active = case % 7 != 0
        object_mode_flag = bool(rng.getrandbits(1))
        special = bool(rng.getrandbits(1))
        contacts = rng.choice((-1, 0, 1, 32, 33))
        acceleration_gate = rng.choice((0.0, 1.0))
        record = _record(rng, active, object_mode_flag, special,
                         contacts, acceleration_gate, mode_active, mode_number)
        cpu.mem_write(OWNER, bytes(record))
        cpu.mem_write(0x00AA459C, struct.pack('<B', int(mode_active)))
        cpu.mem_write(0x00A6CC40, struct.pack('<I', mode_number))
        oracle.call(0x004265F0, (), instruction_limit=800_000)
        original = bytes(cpu.mem_read(OWNER, RECORD_SIZE))

        expected = bytearray(record)
        def physics(owner):
            step_world_object_physics(
                owner, mode_active=mode_active, mode_number=mode_number,
                environment_step=lambda _: None,
                contact_force_step=contact_forces_step)
        maintain_object_record(expected, update_physics=physics)
        if original != expected:
            differences = [index for index, (left, right)
                           in enumerate(zip(original, expected)) if left != right]
            raise AssertionError(
                f'composed 0x4265f0 mismatch case={case} active={active} '
                f'mode={(mode_active, mode_number)} contacts={contacts} '
                f'bytes={[hex(index) for index in differences[:16]]}; '
                f'original={[(hex(index), original[index:index+4].hex()) for index in differences[:8]]}; '
                f'python={[(hex(index), expected[index:index+4].hex()) for index in differences[:8]]}')
    return cases


def _skip_environment(machine, address, reg):
    if address == 0x0051E940:
        stack = machine.reg_read(reg.UC_X86_REG_ESP)
        return_address = struct.unpack('<I', machine.mem_read(stack, 4))[0]
        machine.reg_write(reg.UC_X86_REG_ESP, stack + 4)
        machine.reg_write(reg.UC_X86_REG_EIP, return_address)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=64)
    args = parser.parse_args()
    print(f'composed 0x4265f0 + 0x520c20 matches '
          f'{verify(args.executable, args.cases)} original owner records '
          '(0x51e940 isolated)')


if __name__ == '__main__':
    main()
