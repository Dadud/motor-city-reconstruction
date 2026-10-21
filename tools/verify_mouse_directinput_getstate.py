"""Compare selector-6 DirectInput branch with an explicit 16-byte device read."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_state_get import (MouseCursorGlobals,
    get_mouse_cursor_state_direct_input)
from tools.native_oracle import DynoOracle


ACCESS_MODE = 0x008C8914
POSITION_MODE = 0x008C8918
CLAMP_STATE = 0x008C891C
X = 0x00B3620C
Y = 0x00B36210
Z = 0x00B36214
BUTTONS = 0x00B36218
MIN_X = 0x00B3621C
MAX_X = 0x00B36200
MIN_Y = 0x00B36220
MAX_Y = 0x00B36204
MIN_Z = 0x00B36224
MAX_Z = 0x00B361FC
DEVICE = 0x00B3622C
DEVICE_GET_STATE = 0x006F0A30
RETURNED_STATE = 0x00B36208


def as_i32(value):
    value &= 0xffffffff
    return value - 0x100000000 if value & 0x80000000 else value


def _return(cpu, reg, eax):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    ret = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, eax & 0xffffffff)
    # The DirectInput wrapper is cdecl; its caller removes the three args.
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, ret)


def verify(executable, cases=512):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x6EFCD006 ^ 0x0A30)
    sample_slot = {}

    def intercept(machine, address, _size, _data):
        if address != DEVICE_GET_STATE:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        _, destination, length = struct.unpack('<III', machine.mem_read(sp + 4, 12))
        if length != 16:
            raise AssertionError(f'unexpected native device-state size {length}')
        machine.mem_write(destination, sample_slot['sample'])
        _return(machine, reg, 0)

    hook = cpu.hook_add(UC_HOOK_CODE, intercept,
                        begin=DEVICE_GET_STATE, end=DEVICE_GET_STATE)
    try:
        for index in range(cases):
            mode = 3 if index % 3 == 0 else rng.randrange(0, 8)
            if mode == 4:
                mode = 2
            clamp = index & 1
            x, y, z = (as_i32(rng.getrandbits(32)) for _ in range(3))
            min_x, max_x, min_y, max_y, min_z, max_z = (
                as_i32(rng.getrandbits(32)) for _ in range(6))
            sample = struct.pack('<3i4B',
                as_i32(rng.getrandbits(32)), as_i32(rng.getrandbits(32)),
                as_i32(rng.getrandbits(32)), *(rng.randrange(256) for _ in range(4)))
            state = MouseCursorGlobals(
                access_mode=mode, clamp_wheel=clamp, x=x, y=y, z=z,
                minimum_z=min_z, maximum_z=max_z, wheel_delta=0,
                minimum_x=min_x, maximum_x=max_x,
                minimum_y=min_y, maximum_y=max_y, position_mode=mode)
            get_mouse_cursor_state_direct_input(state, sample)
            sample_slot['sample'] = sample
            values = ((ACCESS_MODE, mode), (POSITION_MODE, mode),
                      (CLAMP_STATE, clamp), (X, x), (Y, y), (Z, z),
                      (MIN_X, min_x), (MAX_X, max_x), (MIN_Y, min_y),
                      (MAX_Y, max_y), (MIN_Z, min_z), (MAX_Z, max_z),
                      (DEVICE, 0x71009000))
            for address, value in values:
                cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))
            oracle.call(0x006EFCD0, (6,), instruction_limit=10000)
            if cpu.reg_read(reg.UC_X86_REG_EAX) != RETURNED_STATE:
                raise AssertionError(f'case {index}: wrong returned state pointer')
            native = struct.unpack('<3i4B', cpu.mem_read(X, 16))
            translated = (state.x, state.y, state.z, state.button0,
                          state.button1, state.button2, state.auxiliary_button)
            if native != translated:
                raise AssertionError(f'case {index}: native={native}, '
                                     f'python={translated}, mode={mode}, clamp={clamp}')
    finally:
        cpu.hook_del(hook)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x6efcd0 selector-6 DirectInput branch matches '
          f'{verify(args.executable, args.cases)} original cases; only the '
          '16-byte device-state result is supplied')


if __name__ == '__main__':
    main()
