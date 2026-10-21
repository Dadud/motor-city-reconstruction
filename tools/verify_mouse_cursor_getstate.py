"""Compare selector 6 absolute-cursor branch of 0x6efcd0 with native code."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_state_get import MouseCursorGlobals, get_mouse_cursor_state_absolute
from tools.native_oracle import DynoOracle


ACCESS_MODE = 0x008C8914
CLAMP_WHEEL = 0x008C891C
X = 0x00B3620C
Y = 0x00B36210
Z = 0x00B36214
BUTTONS = 0x00B36218
WHEEL = 0x00B36238
MIN_Z = 0x00B36224
MAX_Z = 0x00B361FC
CURSOR_BUTTONS = 0x00B36584
CURSOR_X = 0x00B3658C
CURSOR_Y = 0x00B36588
RETURNED_STATE = 0x00B36208


def as_i32(value):
    value &= 0xffffffff
    return value - 0x100000000 if value & 0x80000000 else value


def verify(executable, cases=512):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x6EFCD006)
    for index in range(cases):
        clamp = index & 1
        x, y, z, minimum, maximum, wheel = (
            as_i32(rng.getrandbits(32)) for _ in range(6))
        button_state = rng.getrandbits(32)
        cursor_x = as_i32(rng.getrandbits(32))
        cursor_y = as_i32(rng.getrandbits(32))
        state = MouseCursorGlobals(4, clamp, x, y, z, minimum, maximum, wheel)
        get_mouse_cursor_state_absolute(state, button_state=button_state,
                                        cursor_x=cursor_x, cursor_y=cursor_y)
        values = ((ACCESS_MODE, 4), (CLAMP_WHEEL, clamp), (X, x), (Y, y),
                  (Z, z), (MIN_Z, minimum), (MAX_Z, maximum), (WHEEL, wheel),
                  (CURSOR_BUTTONS, button_state), (CURSOR_X, cursor_x),
                  (CURSOR_Y, cursor_y))
        for address, value in values:
            cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))
        oracle.call(0x006EFCD0, (6,), instruction_limit=10000)
        pointer = cpu.reg_read(reg.UC_X86_REG_EAX)
        if pointer != RETURNED_STATE:
            raise AssertionError(f'case {index}: returned {pointer:#x}, '
                                 f'expected {RETURNED_STATE:#x}')
        native_values = struct.unpack('<3i4B', cpu.mem_read(X, 16))
        translated_values = (state.x, state.y, state.z, state.button0,
                             state.button1, state.button2,
                             state.auxiliary_button)
        if native_values != translated_values:
            raise AssertionError(f'case {index}: native={native_values}, '
                                 f'python={translated_values}; inputs={values}')
        native_wheel = struct.unpack('<i', cpu.mem_read(WHEEL, 4))[0]
        if native_wheel != state.wheel_delta:
            raise AssertionError(f'case {index}: wheel native={native_wheel}, '
                                 f'python={state.wheel_delta}')
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    print(f'0x6efcd0 selector-6 absolute cursor branch matches '
          f'{verify(args.executable, args.cases)} native cases; child '
          '0x6f07a0 executes natively')


if __name__ == '__main__':
    main()
