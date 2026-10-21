"""Compare invalid selector diagnostics of 0x6efcd0 with the original."""
import argparse
import random
import struct
from pathlib import Path

from tools.native_oracle import DynoOracle


DIAGNOSTIC_FILE = 0x00B2BBA4
DIAGNOSTIC_LINE = 0x00B2BBA8
DIAGNOSTIC_CALLBACK = 0x008C4718
DIAGNOSTIC_STUB = 0x7100A000
SOURCE_FILE = 0x0084A004
MESSAGE = 0x0084A088


def _return(cpu, reg):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    ret = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, 0)
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, ret)


def verify(executable, cases=512):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x6EFCD0FF)
    messages = []

    def diagnostic(machine, address, _size, _data):
        if address != DIAGNOSTIC_STUB:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        messages.append(struct.unpack('<I', machine.mem_read(sp + 4, 4))[0])
        _return(machine, reg)

    hook = cpu.hook_add(UC_HOOK_CODE, diagnostic,
                        begin=DIAGNOSTIC_STUB, end=DIAGNOSTIC_STUB)
    try:
        selectors = (0, 1, 3, 4, 5, 10, 0xffffffff)
        for index in range(cases):
            selector = selectors[index % len(selectors)]
            if index % 7 == 6:
                selector = rng.getrandbits(32)
                if selector in (2, 6, 7, 8, 9):
                    selector ^= 0x100
            old_file, old_line = rng.getrandbits(32), rng.getrandbits(32)
            cpu.mem_write(DIAGNOSTIC_FILE, struct.pack('<I', old_file))
            cpu.mem_write(DIAGNOSTIC_LINE, struct.pack('<I', old_line))
            cpu.mem_write(DIAGNOSTIC_CALLBACK, struct.pack('<I', DIAGNOSTIC_STUB))
            messages.clear()
            oracle.call(0x006EFCD0, (selector,), instruction_limit=1000)
            result = cpu.reg_read(reg.UC_X86_REG_EAX)
            file_value = struct.unpack('<I', cpu.mem_read(DIAGNOSTIC_FILE, 4))[0]
            line_value = struct.unpack('<I', cpu.mem_read(DIAGNOSTIC_LINE, 4))[0]
            if (result != 0 or file_value != SOURCE_FILE or line_value != 0x256
                    or messages != [MESSAGE]):
                raise AssertionError(f'case {index}, selector={selector:#x}: '
                    f'result={result:#x}, file={file_value:#x}, '
                    f'line={line_value:#x}, messages={messages}')
    finally:
        cpu.hook_del(hook)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x6efcd0 invalid-selector diagnostics match '
          f'{verify(args.executable, args.cases)} original calls')


if __name__ == '__main__':
    main()
