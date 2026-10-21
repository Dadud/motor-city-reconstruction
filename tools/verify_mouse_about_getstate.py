"""Compare the selector-2 wrapper of 0x6efcd0 with native execution."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_state_get import MouseAboutState, get_mouse_about_state
from tools.native_oracle import DynoOracle


INITIALIZED = 0x00B36228
DEVICE = 0x00B3622C
INFORMATION = 0x00B35FE0
INFO_SIZE = 0x21C
DIAGNOSTIC_FILE = 0x00B2BBA4
DIAGNOSTIC_LINE = 0x00B2BBA8
DIAGNOSTIC_CALLBACK = 0x008C4718
DEVICE_INFO_CALL = 0x006F0B20
DIAGNOSTIC_STUB = 0x7100A000
ERROR_FILE = 0x0084A004
ERROR_MESSAGE = 0x0084A0A8
RETURNED_INFO = INFORMATION


def _return(cpu, reg, eax):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    address = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, eax & 0xffffffff)
    # Both the wrapped device call and diagnostic callback are cdecl.
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, address)


def verify(executable, cases=256):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x6EFCD002)
    inputs = {}
    native_errors = []

    def device_info_hook(machine, address, _size, _data):
        if address != DEVICE_INFO_CALL:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        _device, output = struct.unpack('<II', machine.mem_read(sp + 4, 8))
        machine.mem_write(output, inputs['information'])
        _return(machine, reg, inputs['status'])

    def diagnostic_hook(machine, address, _size, _data):
        if address != DIAGNOSTIC_STUB:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        message = struct.unpack('<I', machine.mem_read(sp + 4, 4))[0]
        native_errors.append(message)
        _return(machine, reg, 0)

    hooks = [
        cpu.hook_add(UC_HOOK_CODE, device_info_hook,
                     begin=DEVICE_INFO_CALL, end=DEVICE_INFO_CALL),
        cpu.hook_add(UC_HOOK_CODE, diagnostic_hook,
                     begin=DIAGNOSTIC_STUB, end=DIAGNOSTIC_STUB),
    ]
    try:
        for case in range(cases):
            initialized = rng.randrange(2)
            status = rng.getrandbits(32)
            if case % 3 == 0:
                status = 0
            original_info = rng.randbytes(INFO_SIZE)
            supplied_info = rng.randbytes(INFO_SIZE)
            original_file = rng.getrandbits(32)
            original_line = rng.getrandbits(32)
            state = MouseAboutState(initialized, bytearray(original_info),
                                    original_file, original_line)
            calls = []

            def query(buffer):
                buffer[:] = supplied_info
                return status

            result = get_mouse_about_state(state, query_device_info=query,
                                           report_error=calls.append)
            expected_pointer = INFORMATION if initialized and status == 0 else 0
            if result is None:
                expected_info = bytes(state.information)
            else:
                expected_info = bytes(result)

            inputs.update(information=supplied_info, status=status)
            cpu.mem_write(INITIALIZED, struct.pack('<I', initialized))
            cpu.mem_write(DEVICE, struct.pack('<I', 0x71009000))
            cpu.mem_write(INFORMATION, original_info)
            cpu.mem_write(DIAGNOSTIC_FILE, struct.pack('<I', original_file))
            cpu.mem_write(DIAGNOSTIC_LINE, struct.pack('<I', original_line))
            cpu.mem_write(DIAGNOSTIC_CALLBACK,
                          struct.pack('<I', DIAGNOSTIC_STUB))
            native_errors.clear()
            oracle.call(0x006EFCD0, (2,), instruction_limit=10000)
            pointer = cpu.reg_read(reg.UC_X86_REG_EAX)
            native_info = bytes(cpu.mem_read(INFORMATION, INFO_SIZE))
            native_file = struct.unpack('<I', cpu.mem_read(DIAGNOSTIC_FILE, 4))[0]
            native_line = struct.unpack('<I', cpu.mem_read(DIAGNOSTIC_LINE, 4))[0]
            if (pointer != expected_pointer or native_info != expected_info
                    or native_file != state.diagnostic_file
                    or native_line != state.diagnostic_line
                    or native_errors != calls):
                raise AssertionError(f'case {case}: pointer {pointer:#x}/'
                    f'{expected_pointer:#x}, info match={native_info == expected_info}, '
                    f'diagnostics native={(native_file, native_line, native_errors)} '
                    f'python={(state.diagnostic_file, state.diagnostic_line, calls)}')
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(f'0x6efcd0 selector-2 wrapper matches {verify(args.executable, args.cases)} '
          'native cases; 0x6f0b20 and diagnostics use explicit bridges')


if __name__ == '__main__':
    main()
