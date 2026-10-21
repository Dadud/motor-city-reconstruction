"""Compare the pure 0x43b570 reset-result selector with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.world_object_reset import OWNER_SIZE, drive_reset_state_result
from tools.native_oracle import DynoOracle


OWNER = 0x72002000
OWNER_TABLE = 0x0098C1E8
MODE = 0x009AA9A0
MASK = 0x009ABB04


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    cpu = oracle.cpu
    rng = random.Random(0x43B570)
    for case in range(cases):
        record = bytearray(rng.randbytes(OWNER_SIZE))
        if case % 4:
            flags = rng.getrandbits(32) & ~0x212
            if case % 3 == 0:
                flags |= (0x200, 0x2, 0x10)[case % 3]
            struct.pack_into('<I', record, 0x474, flags)
        index = rng.randrange(32)
        mask = rng.getrandbits(32)
        selected_owner = OWNER if case % 5 == 0 else rng.getrandbits(32)
        cpu.mem_write(OWNER, bytes(record))
        cpu.mem_write(MODE, struct.pack('<I', index))
        cpu.mem_write(MASK, struct.pack('<I', mask))
        cpu.mem_write(OWNER_TABLE + index * 4,
                      struct.pack('<I', selected_owner))
        oracle.call(0x0043B570, (OWNER,))
        original = cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        translated = drive_reset_state_result(
            record, owner_address=OWNER, selected_owner=selected_owner,
            result_mask=mask)
        if original != translated:
            raise AssertionError(f'0x43b570 mismatch case {case}: '
                f'flags={struct.unpack_from("<I", record, 0x474)[0]:#x}, '
                f'owner={OWNER:#x}, selected={selected_owner:#x}, '
                f'mask={mask:#x}, original={original:#x}, translated={translated:#x}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x43b570 selector matches {verify(args.executable, args.cases)} original calls')


if __name__ == '__main__':
    main()
