"""Execute the cursor-motion instruction slice and compare native outputs."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_cursor_motion import MouseCursorMotionParameters, update_mouse_cursor_motion
from tools.native_oracle import DynoOracle


STATE = 0x7100C000
ENTRY = 0x004AD747
STOP = 0x004AD869
SET_STATE = 0x006EFAF0
CALLBACK = 0x7100D000
CENTER = 0x009E1674
RADIUS = 0x009E1670
DEADZONE = 0x009E166C
TARGET = 0x009E1678
TIMER = 0x009E1664
AXIS = 0x009E1660


def compare(executable, cases=512):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4ad747)
    setter_calls = []

    def hook(machine, address, _size, _data):
        if address != SET_STATE:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        selector, value = struct.unpack('<II', machine.mem_read(sp + 4, 8))
        setter_calls.append((selector, value if value < 0x80000000 else value - 0x100000000))
        ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
        machine.reg_write(reg.UC_X86_REG_EAX, 1)
        machine.reg_write(reg.UC_X86_REG_ESP, sp + 4)
        machine.reg_write(reg.UC_X86_REG_EIP, ret)

    hook_id = cpu.hook_add(UC_HOOK_CODE, hook, begin=SET_STATE, end=SET_STATE)
    try:
        for case in range(cases):
            oracle._reset()
            center = rng.randrange(-10000, 10001)
            radius = rng.choice((8.0, 25.0, 50.0, 100.0, 250.0))
            deadzone = rng.choice((0.0, 1.0, 3.0, 5.0, 10.0))
            if deadzone >= radius:
                deadzone = radius / 4
            offset = rng.randrange(-int(radius * 2), int(radius * 2) + 1)
            sample = center + offset
            target = rng.randrange(-10000, 10001)
            timer = rng.randrange(0, 120)
            cpu.mem_write(STATE, b'\0' * 0x20)
            cpu.mem_write(STATE + 4, struct.pack('<i', sample))
            cpu.mem_write(CENTER, struct.pack('<i', center))
            cpu.mem_write(RADIUS, struct.pack('<f', radius))
            cpu.mem_write(DEADZONE, struct.pack('<f', deadzone))
            cpu.mem_write(TARGET, struct.pack('<i', target))
            cpu.mem_write(TIMER, struct.pack('<i', timer))
            cpu.mem_write(0x009E1644, struct.pack('<I', 1))
            cpu.mem_write(0x009E1640, struct.pack('<I', 1))
            cpu.reg_write(reg.UC_X86_REG_EAX, STATE)
            cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
            cpu.reg_write(reg.UC_X86_REG_ESP, oracle.frame - 0x1c)
            cpu.mem_write(oracle.frame - 8, struct.pack('<I', STATE))
            expected = update_mouse_cursor_motion(sample,
                MouseCursorMotionParameters(center, radius, deadzone, target, timer))
            setter_calls.clear()
            cpu.emu_start(ENTRY, STOP, timeout=0, count=10000)
            if cpu.reg_read(reg.UC_X86_REG_EIP) != STOP:
                raise AssertionError(f'case {case}: native range did not finish')
            actual_axis = struct.unpack('<i', cpu.mem_read(AXIS, 4))[0]
            actual_timer = struct.unpack('<i', cpu.mem_read(TIMER, 4))[0]
            if (actual_axis, actual_timer, tuple(setter_calls)) != \
                    (expected.signed_axis, expected.center_frames_remaining,
                     expected.setter_calls):
                raise AssertionError(f'case {case}: native '
                    f'{actual_axis}/{actual_timer}/{setter_calls} != source '
                    f'{expected.signed_axis}/{expected.center_frames_remaining}/'
                    f'{expected.setter_calls}, sample={sample}, center={center}, '
                    f'radius={radius}, deadzone={deadzone}')
        return cases
    finally:
        cpu.hook_del(hook_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    count = compare(args.executable, args.cases)
    print(f'cursor clamp, deadzone response, timer, and reset calls matched '
          f'{count} original instruction slices')


if __name__ == '__main__':
    main()
