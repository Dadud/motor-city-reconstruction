"""Compare keyboard action progress and active predicates with native code."""
import argparse
import random
import struct
from pathlib import Path

from client.keyboard_action_state import (ACTION_TABLE_SIZE,
    action_progress_value, is_keyboard_action_active)
from tools.native_oracle import DynoOracle


ACTION_TABLE = 0x0098E450
KEY_STATES = 0x008C8648
DIRECTION_FLAGS = 0x0098E390
STATE_DISPATCH = 0x0088E648
STATE_STUB = 0x7100A000


def _return(cpu, reg, value):
    sp = cpu.reg_read(reg.UC_X86_REG_ESP)
    address = struct.unpack('<I', cpu.mem_read(sp, 4))[0]
    cpu.reg_write(reg.UC_X86_REG_EAX, value & 0xffffffff)
    # The child state function is cdecl; 0x460950 removes the argument.
    cpu.reg_write(reg.UC_X86_REG_ESP, sp + 4)
    cpu.reg_write(reg.UC_X86_REG_EIP, address)


def verify_progress(executable, cases=4096):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x460890)
    table = bytearray(rng.randbytes(ACTION_TABLE_SIZE))
    cpu.mem_write(ACTION_TABLE, bytes(table))
    for index in range(cases):
        action = rng.getrandbits(32)
        record_index = (action >> 28) * 0x21 + ((action >> 24) & 0xf)
        current = rng.randrange(-(1 << 23), 1 << 23)
        struct.pack_into('<i', table, record_index * 4, current << 8)
        cpu.mem_write(ACTION_TABLE + record_index * 4,
                      struct.pack('<i', current << 8))
        expected = action_progress_value(action, table)
        oracle.call(0x00460890, (action,), instruction_limit=1000)
        actual = cpu.reg_read(reg.UC_X86_REG_EAX)
        if actual != expected:
            raise AssertionError(f'progress case {index}: action={action:#x}, '
                                 f'native={actual:#x}, python={expected:#x}')
    return cases


def verify_predicate(executable, cases=2048):
    from unicorn import UC_HOOK_CODE

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x460950)
    callback_result = {}
    callback_actions = []

    def state_callback(machine, address, _size, _data):
        if address != STATE_STUB:
            return
        sp = machine.reg_read(reg.UC_X86_REG_ESP)
        action = struct.unpack('<I', machine.mem_read(sp + 4, 4))[0]
        callback_actions.append(action)
        _return(machine, reg, callback_result['value'])

    hook = cpu.hook_add(UC_HOOK_CODE, state_callback,
                        begin=STATE_STUB, end=STATE_STUB)
    table = bytearray(rng.randbytes(ACTION_TABLE_SIZE))
    try:
        for index in range(cases):
            branch = index % 3
            states = bytearray(rng.randbytes(0x80))
            direction_flags = rng.getrandbits(32)
            if branch == 0:
                low = 1
                action = ((rng.randrange(16) << 28) |
                          (rng.randrange(16) << 24) |
                          (rng.randrange(256) << 16) |
                          (rng.randrange(256) << 8) | low)
                value = rng.randrange(-(1 << 23), 1 << 23)
                record_index = (action >> 28) * 0x21 + ((action >> 24) & 0xf)
                struct.pack_into('<i', table, record_index * 4, value << 8)
            elif branch == 1:
                code = rng.choice((0xcb, 0xcd, 0xc8, 0xd0, 0x1c,
                                   0x00, 0x7f, 0x80, 0xff))
                low = 4
                action = (code << 8) | low
                if index % 4 == 0:
                    states[code & 0x7f] = 1
                direction_flags = rng.choice((0, 1, 2, 4, 8, 0x10,
                                               0xffffffff))
            else:
                low = rng.choice((0, 2, 3, 5, 0x7f, 0x80, 0xff))
                action = rng.getrandbits(32) & 0xffffff00 | low
                signed = low if low < 0x80 else low - 0x100
                cpu.mem_write(STATE_DISPATCH + signed * 4,
                              struct.pack('<I', STATE_STUB))
                callback_result['value'] = rng.getrandbits(32)

            cpu.mem_write(KEY_STATES, bytes(states))
            cpu.mem_write(DIRECTION_FLAGS, struct.pack('<I', direction_flags))
            cpu.mem_write(ACTION_TABLE, bytes(table))
            expected_callback = []
            expected = is_keyboard_action_active(
                action, key_states=states, direction_flags=direction_flags,
                action_table=table,
                query_other_action=lambda value: expected_callback.append(value)
                    or callback_result['value'])
            callback_actions.clear()
            oracle.call(0x00460950, (action,), instruction_limit=3000)
            actual = cpu.reg_read(reg.UC_X86_REG_EAX)
            if actual != expected or callback_actions != expected_callback:
                raise AssertionError(f'predicate case {index}: action={action:#x}, '
                    f'native={actual:#x}, python={expected:#x}, '
                    f'callback={callback_actions}/{expected_callback}')
    finally:
        cpu.hook_del(hook)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    parser.add_argument('--progress-cases', type=int, default=4096)
    parser.add_argument('--predicate-cases', type=int, default=2048)
    args = parser.parse_args()
    progress = verify_progress(args.executable, args.progress_cases)
    predicate = verify_predicate(args.executable, args.predicate_cases)
    print(f'0x460890 progress matches {progress} original calls; '
          f'0x460950 predicates match {predicate} original calls across '
          'type-1, type-4, and callback-dispatched action types')


if __name__ == '__main__':
    main()
