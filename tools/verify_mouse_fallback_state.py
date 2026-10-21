"""Differentially compare inactive mouse-action outputs with the original."""
import argparse
import random
import struct
from pathlib import Path

from client.mouse_fallback_state import build_fallback_mouse_outputs
from tools.native_oracle import DynoOracle


ACTION_WORDS = 0x009E1CE8
OUTPUT = 0x009E1E89
DISPATCH = 0x0088E648
CALLBACK_STUB = 0x7100A000
ENTRY = 0x004ADC28
STOP = 0x004ADD71


def compare(executable, cases=512):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4adc28)
    results = {}
    trace = []

    def hook(machine, address, _size, _data):
        if address != CALLBACK_STUB:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        action = struct.unpack('<I', machine.mem_read(sp + 4, 4))[0]
        trace.append(action)
        ret = struct.unpack('<I', machine.mem_read(sp, 4))[0]
        machine.reg_write(reg.UC_X86_REG_EAX, results[action])
        machine.reg_write(reg.UC_X86_REG_ESP, sp + 4)
        machine.reg_write(reg.UC_X86_REG_EIP, ret)

    hook_id = cpu.hook_add(UC_HOOK_CODE, hook,
                           begin=CALLBACK_STUB, end=CALLBACK_STUB)
    for signed in range(-128, 128):
        cpu.mem_write(DISPATCH + signed * 4, struct.pack('<I', CALLBACK_STUB))
    try:
        for case in range(cases):
            oracle._reset()
            words = tuple(rng.choice((0, 1, 2, 0x101, 0x201, 0x304,
                                      0x408, 0x510, 0x620, 0x730))
                          for _ in range(8))
            values = {word: rng.getrandbits(32) for word in set(words)}
            results.clear()
            results.update(values)
            image = struct.pack('<8I', *words)
            cpu.mem_write(ACTION_WORDS, image)
            cpu.mem_write(OUTPUT, b'\0' * 4)
            cpu.mem_write(oracle.frame - 1, b'\0')
            cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
            cpu.reg_write(reg.UC_X86_REG_ESP, oracle.frame - 0x1c)
            cpu.reg_write(reg.UC_X86_REG_EBX, 0)
            expected = build_fallback_mouse_outputs(image,
                dispatch_action=values.__getitem__)
            trace.clear()
            cpu.emu_start(ENTRY, STOP, timeout=0, count=10000)
            if cpu.reg_read(reg.UC_X86_REG_EIP) != STOP:
                raise AssertionError(f'case {case}: native range failed')
            actual = bytes(cpu.mem_read(OUTPUT, 4))
            wanted = bytes((expected.cursor_delta, expected.button_state_0,
                            expected.button_state_1, expected.transition_flags))
            if actual != wanted or tuple(trace) != expected.dispatch_trace:
                raise AssertionError(f'case {case}: native {actual.hex()}/{trace} != '
                    f'source {wanted.hex()}/{expected.dispatch_trace}')
        return cases
    finally:
        cpu.hook_del(hook_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=512)
    args = parser.parse_args()
    count = compare(args.executable, args.cases)
    print(f'inactive mouse action outputs and callback order matched '
          f'{count} original instruction ranges')


if __name__ == '__main__':
    main()
