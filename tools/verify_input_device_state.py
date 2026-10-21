"""Compare the 0x6f0a30 DirectInput read wrapper with native execution."""
import argparse
import random
import struct
from pathlib import Path

from client.input_device_state import read_input_device_state
from tools.native_oracle import DynoOracle


ENSURE_ACQUIRED = 0x006F0A70
GET_STATE = 0x006F0AA0
ZERO = 0x006EE770
OUTPUT = 0x71002000


def _return(cpu, reg, eax):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    ret = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, eax & 0xffffffff)
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, ret)


def verify(executable, cases=512):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x6F0A30)
    script = {}
    native_calls = []

    def hook(machine, address, _size, _data):
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        if address == ENSURE_ACQUIRED:
            device = struct.unpack('<I', machine.mem_read(sp + 4, 4))[0]
            native_calls.append(('acquire', device))
            _return(machine, reg, 0)
        elif address == GET_STATE:
            device, size, output = struct.unpack('<III', machine.mem_read(sp + 4, 12))
            native_calls.append(('read', device, size))
            machine.mem_write(output, script['read_bytes'][:size])
            _return(machine, reg, script['status'])
        elif address == ZERO:
            output, value, size = struct.unpack('<III', machine.mem_read(sp + 4, 12))
            if value != 0:
                raise AssertionError('failure clear used a nonzero fill value')
            native_calls.append(('clear', size))
            machine.mem_write(output, bytes(size))
            _return(machine, reg, 0)

    hooks = [cpu.hook_add(UC_HOOK_CODE, hook,
                          begin=a, end=a) for a in
             (ENSURE_ACQUIRED, GET_STATE, ZERO)]
    try:
        for index in range(cases):
            device = rng.getrandbits(32)
            size = rng.randrange(0, 65)
            original = rng.randbytes(size)
            read_bytes = rng.randbytes(size)
            status = 0 if index % 2 == 0 else rng.getrandbits(32) or 1
            output = bytearray(original)
            calls = []

            def get_state(actual_device, actual_size, view):
                calls.append(('read', actual_device, actual_size))
                view[:] = read_bytes
                return status

            expected_status = read_input_device_state(
                device, output, size,
                ensure_acquired=lambda value: calls.append(('acquire', value)),
                get_state=get_state)
            script.update(status=status, read_bytes=read_bytes)
            cpu.mem_write(OUTPUT, original)
            native_calls.clear()
            oracle.call(0x006F0A30, (device, OUTPUT, size),
                        instruction_limit=10000)
            actual_status = cpu.reg_read(reg.UC_X86_REG_EAX)
            actual_output = bytes(cpu.mem_read(OUTPUT, size))
            expected_calls = [('acquire', device), ('read', device, size)]
            if status:
                expected_calls.append(('clear', size))
            if (actual_status != expected_status or actual_output != bytes(output)
                    or native_calls != expected_calls):
                raise AssertionError(f'case {index}: status '
                    f'{actual_status:#x}/{expected_status:#x}; '
                    f'output={actual_output.hex()}/{bytes(output).hex()}; '
                    f'calls={native_calls}/{expected_calls}')
    finally:
        for hook_id in hooks:
            cpu.hook_del(hook_id)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x6f0a30 device-state wrapper matches '
          f'{verify(args.executable, args.cases)} native cases')


if __name__ == '__main__':
    main()
