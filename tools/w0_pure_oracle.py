"""Original-comparison oracle for the wave-0 pure leaf batch.

Eight small routines, one oracle: each takes its inputs as planted memory or
registers, runs the original's complete body through DynoOracle.call, and the
result is read from the emulated registers or memory.

  0x414c10  member AND predicate        (state at ECX+0x6c)
  0x414c30  member masked clear         (state at ECX+0x6c, result in EDX)
  0x428980  sentinel equality predicate
  0x41bf80  counter increment
  0x423310  zero predicate
  0x42cae0  three floating-point defaults written to memory
  0x423420  indexed dword read, first table
  0x42f070  indexed dword read, second table
"""
import argparse
import json
import struct

from tools.native_oracle import DynoOracle

AND_FLAG = 0x414c10
CLEAR_MASK = 0x414c30
SENTINEL = 0xfeeeeb19
SENTINEL_MATCH = 0x428980
COUNTER_INCREMENT = 0x41bf80
ZERO_FLAG = 0x423310
DEFAULTS = 0x42cae0
TABLE_READ_A = 0x423420
TABLE_READ_B = 0x42f070
STATE = 0x71004000
SCRATCH = 0x71001000
TABLE_A = 0x71005000
TABLE_B = 0x71006000

VALUES = (0, 1, 5, 0xffffffff, 0xfeeeeb19, 0x1234, 0x80000000)
MASKS = (0, 1, 0xff, 0x7fffffff, 0xffffffff)
INDICES = (0, 1, 3, 7)


def state_and_flag(oracle):
    rows = []
    for state in VALUES:
        for mask in MASKS:
            oracle.cpu.mem_write(STATE+0x6c, struct.pack('<I', state))
            # ret 4 in the body: the callee cleans, so the stub must not.
            result = oracle.call(AND_FLAG, (mask & 0xffffffff,),
                                 this_pointer=STATE, cleanup=b'')
            actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            expected = 1 if (state & mask) != 0 else 0
            if actual != expected:
                raise AssertionError(
                    f'and flag {state:#x} & {mask:#x}: expected {expected}, '
                    f'got {actual:#x}')
            rows.append((state, mask, actual))
    return rows


def state_clear_mask(oracle):
    rows = []
    for state in VALUES:
        for mask in MASKS:
            oracle.cpu.mem_write(STATE+0x6c, struct.pack('<I', state))
            oracle.call(CLEAR_MASK, (mask & 0xffffffff,), this_pointer=STATE,
                        cleanup=b'')
            stored = struct.unpack('<I', oracle.cpu.mem_read(STATE+0x6c, 4))[0]
            expected = state & ~mask & 0xffffffff
            if stored != expected:
                raise AssertionError(
                    f'clear mask {state:#x} ~ {mask:#x}: expected {expected:#x}, '
                    f'got {stored:#x}')
            rows.append((state, mask, stored))
    return rows


def sentinel_match(oracle):
    rows = []
    for value in VALUES + (0xfeeeeb19,):
        result = oracle.call(SENTINEL_MATCH, (value & 0xffffffff,))
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        want = 1 if value == SENTINEL else 0
        if actual != want:
            raise AssertionError(
                f'sentinel {value:#x}: expected {want}, got {actual:#x}')
        rows.append((value, actual))
    return rows


def counter_increment(oracle):
    rows = []
    for counter in (0, 1, 0x7fffffff, 0xffffffff):
        # The counter lives in the global at 0x92beb0; the routine has no
        # arguments at all.
        oracle.cpu.mem_write(0x92beb0, struct.pack('<I', counter))
        result = oracle.call(COUNTER_INCREMENT)
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        want = (counter+1) & 0xffffffff
        if actual != want:
            raise AssertionError(
                f'increment {counter:#x}: expected {want:#x}, got {actual:#x}')
        rows.append((counter, actual))
    return rows


def zero_flag(oracle):
    rows = []
    for value in VALUES:
        # The value lives in the global at 0x929888, which the routine also
        # uses as its store target.
        oracle.cpu.mem_write(0x929888, struct.pack('<I', value))
        result = oracle.call(ZERO_FLAG)
        stored = struct.unpack('<I', oracle.cpu.mem_read(0x929888, 4))[0]
        want = 1 if value == 0 else 0
        if stored != want:
            raise AssertionError(
                f'zero flag {value:#x}: expected {want}, got {stored:#x}')
        rows.append((value, stored))
    return rows


def default_constants(oracle):
    oracle.call(DEFAULTS)
    raw = bytes(oracle.cpu.mem_read(0x88aafc, 12))
    got = struct.unpack('<III', raw)
    want = (0x42c80000, 0x42480000, 0x41f00000)
    if got != want:
        raise AssertionError(f'default constants {got[:]} != {want}')
    return [want]


def table_read(oracle, entry, base):
    """Indexed dword read from a fixed table inside the mapped image."""
    rows = []
    for index in INDICES:
        oracle.call(entry, (index & 0xffffffff,))
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        want = struct.unpack('<I', oracle.cpu.mem_read(base+index*4, 4))[0]
        if actual != want:
            raise AssertionError(
                f'table read index {index}: expected {want:#x}, got {actual:#x}')
        rows.append((index, actual))
    return rows


def verify(executable):
    oracle = DynoOracle(executable)
    oracle.cpu.mem_map(0, 0x1000)  # inert FS:[0] SEH chain
    oracle.cpu.mem_write(0x929888, b'\x00'*4)  # zero flag store target
    return dict(
        and_flag_cases=len(state_and_flag(oracle)),
        clear_mask_cases=len(state_clear_mask(oracle)),
        sentinel_cases=len(sentinel_match(oracle)),
        increment_cases=len(counter_increment(oracle)),
        zero_flag_cases=len(zero_flag(oracle)),
        default_constant_cases=len(default_constants(oracle)),
        table_a_cases=len(table_read(oracle, TABLE_READ_A, TABLE_A)),
        table_b_cases=len(table_read(oracle, TABLE_READ_B, TABLE_B)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(dict(verify(parser.parse_args().executable),
                          exact_output_bits=True,
                          scope='wave-0 pure leaf batch: 0x414c10, 0x414c30, '
                                '0x428980, 0x41bf80, 0x423310, 0x42cae0, '
                                '0x423420, 0x42f070 complete bodies; inputs '
                                'planted, results read from registers and '
                                'original memory')))


if __name__ == '__main__':
    main()