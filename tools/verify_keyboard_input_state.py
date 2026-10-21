"""Compare translated 0x4606b0 keyboard-state pass with native execution."""
import argparse
import random
import struct
from pathlib import Path

from client.keyboard_input_state import (KEY_RECORDS_SIZE, KeyboardInputState,
    update_keyboard_direction_flags)
from tools.native_oracle import DynoOracle


MAP = 0x0098E394
FLAGS = 0x0098E390
RECORDS = 0x0098E400
MODE = 0x00AA4598
ENVIRONMENT = 0x00AA459C
KEY_STATES = 0x008C8648
ZERO_HELPER = 0x006EE0C0
RECORD_LOOKUP = 0x00472DD0


def _return(cpu, reg, argc, eax):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    ret = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, eax & 0xffffffff)
    # Both hooks are cdecl, so their native callers discard arguments.
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, ret)


def verify(executable, cases=256):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4606B0)
    available_records = {}
    active_case = {}
    missing = []

    def intercept(machine, address, _size, _data):
        if address == RECORD_LOOKUP:
            sp = machine.reg_read(reg.UC_X86_REG_ESP)
            key, destination = struct.unpack('<II', machine.mem_read(sp + 4, 8))
            missing.append(key)
            row = active_case['records'].get(key)
            if row is None:
                _return(machine, reg, 2, 0)
            else:
                machine.mem_write(destination, row)
                _return(machine, reg, 2, destination)
        elif address == ZERO_HELPER:
            sp = machine.reg_read(reg.UC_X86_REG_ESP)
            destination, size = struct.unpack('<II', machine.mem_read(sp + 4, 8))
            machine.mem_write(destination, bytes(size))
            _return(machine, reg, 2, 0)

    hook = cpu.hook_add(UC_HOOK_CODE, intercept,
                        begin=min(RECORD_LOOKUP, ZERO_HELPER),
                        end=max(RECORD_LOOKUP, ZERO_HELPER))
    try:
        for case in range(cases):
            count = rng.randrange(0, 18)
            mapping = bytes(rng.randrange(0x80) for _ in range(count)) + b'\x80'
            initial = bytearray(rng.randbytes(KEY_RECORDS_SIZE))
            supplied = {}
            for key in set(mapping[:-1]):
                if rng.randrange(4) != 0:
                    supplied[key] = bytes(rng.randbytes(0x84))
            mode = rng.randrange(0, 8)
            environment = rng.randrange(2)
            suppressed = rng.randrange(2)
            cpu.mem_write(MAP, mapping)
            cpu.mem_write(FLAGS, struct.pack('<I', rng.getrandbits(32)))
            cpu.mem_write(RECORDS, bytes(initial))
            cpu.mem_write(MODE, struct.pack('<I', mode))
            cpu.mem_write(ENVIRONMENT, struct.pack('<I', environment))
            cpu.mem_write(KEY_STATES + 0x0f, bytes((suppressed,)))
            missing.clear()
            active_case['records'] = supplied

            translated_records = bytearray(initial)
            state = KeyboardInputState(mapping, translated_records, mode,
                                       environment, suppressed)

            def lookup(key, row):
                record = supplied.get(key)
                if record is None:
                    return False
                row[:] = record
                return True

            flags = update_keyboard_direction_flags(state,
                                                    lookup_record=lookup)
            oracle.call(0x004606B0, (), instruction_limit=100000)
            actual_flags = struct.unpack('<I', cpu.mem_read(FLAGS, 4))[0]
            actual_records = bytes(cpu.mem_read(RECORDS, KEY_RECORDS_SIZE))
            if actual_flags != flags or actual_records != bytes(translated_records):
                raise AssertionError(f'case {case} mismatch: flags '
                    f'native={actual_flags:#x}, translated={flags:#x}; '
                    f'lookup_keys={missing}')
    finally:
        cpu.hook_del(hook)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--cases', type=int, default=256)
    args = parser.parse_args()
    print(f'0x4606b0 keyboard-state updates match {verify(args.executable, args.cases)} '
          'native cases; record lookup and memory zeroing are explicit bridges')


if __name__ == '__main__':
    main()
