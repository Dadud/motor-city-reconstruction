"""Original-comparison oracle for the pseudocode-driven wave-0 batch.

Six routines recovered by reading exported decompiler pseudocode instead of
hand-tracing disassembly, then judged against the original: each takes its
inputs as planted memory or registers, runs the original's complete body
through DynoOracle.call, and the result is read back from emulated registers or
memory. The pseudocode is the draft, never the verdict.

  0x414bf0  member OR-mask            (state at ECX+0x6c, ret 4)
  0x42cc60  modulo-four counter       (counter global at 0x9aba2c)
  0x42d350  300-column byte table     (-1 column sentinel)
  0x42d380  flat byte table           (-1 index sentinel)
  0x4082c0  clear through a fallback  (primary 0x92971c, fallback 0x929720)
  0x429420  clear a pointer, record it (pointer 0x988d08, record 0x988cf4)
"""
import argparse
import json
import struct

from tools.native_oracle import DynoOracle

STATE_OR_MASK = 0x414bf0
COUNTER_MOD4 = 0x42cc60
TABLE_BYTE_XY = 0x42d350
TABLE_BYTE_FLAT = 0x42d380
CLEAR_THROUGH = 0x4082c0
POINTER_CLEAR_RECORD = 0x429420

STATE = 0x71004000
SCRATCH = 0x71001000
SPARE = 0x71002000
COUNTER_GLOBAL = 0x9aba2c
PRIMARY_GLOBAL = 0x92971c
FALLBACK_GLOBAL = 0x929720
POINTER_GLOBAL = 0x988d08
RECORD_GLOBAL = 0x988cf4
COLUMN_TABLE = 0x97e848
FLAT_TABLE = 0x97ebcc

STATES = (0, 1, 0x6c00, 0xffffffff, 0x12345678, 0x80000000)
MASKS = (0, 1, 0x0130, 0x7fffffff, 0xffffffff)
COUNTERS = (0, 1, 2, 3, 4, 5, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)
COLUMNS = (0, 1, 299)


def state_or_mask_results(oracle):
    """0x414bf0 ORs the argument into the member word at ECX+0x6c and returns
    nothing, so the word in memory is the observable."""
    rows = []
    for state in STATES:
        for mask in MASKS:
            oracle.cpu.mem_write(STATE+0x6c, struct.pack('<I', state))
            oracle.call(STATE_OR_MASK, (mask,), this_pointer=STATE, cleanup=b'')
            after = struct.unpack('<I', oracle.cpu.mem_read(STATE+0x6c, 4))[0]
            if after != (state | mask):
                raise AssertionError(
                    f'or-mask {state:#x} | {mask:#x}: word is {after:#x}')
            rows.append((state, mask, after))
    return rows


def counter_mod4_results(oracle):
    """0x42cc60 increments the global, masks with 0x80000003 and repairs a
    negative result; the observable is the global it leaves behind."""
    rows = []
    for counter in COUNTERS:
        oracle.cpu.mem_write(COUNTER_GLOBAL, struct.pack('<I', counter))
        oracle.call(COUNTER_MOD4, ())
        after = struct.unpack('<I', oracle.cpu.mem_read(COUNTER_GLOBAL, 4))[0]
        expect = (counter + 1) & 0x80000003
        if expect & 0x80000000:
            expect = ((expect - 1) | 0xfffffffc) + 1
            expect &= 0xffffffff
        if after != expect:
            raise AssertionError(
                f'counter {counter:#x}: expected {expect:#x}, got {after:#x}')
        rows.append((counter, after))
    return rows


def _byte(oracle, address):
    return oracle.cpu.mem_read(address, 1)[0]


def table_byte_xy_results(oracle):
    """0x42d350: a column of -1 returns 0 without reading, otherwise the byte
    comes from 0x97e848 + row*300 + column."""
    rows = []
    for row in (0, 1, 2):
        for column in COLUMNS:
            oracle.call(TABLE_BYTE_XY, (row, column))
            actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
            want = _byte(oracle, COLUMN_TABLE + row*300 + column)
            if actual != want:
                raise AssertionError(
                    f'table xy {row},{column}: expected {want:#x}, got {actual:#x}')
            rows.append((row, column, actual))
    for column in COLUMNS:
        oracle.call(TABLE_BYTE_XY, (1, -1 & 0xffffffff))
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
        if actual != 0:
            raise AssertionError(f'column -1 must return 0, got {actual:#x}')
        rows.append((-1, actual))
    return rows


def table_byte_flat_results(oracle):
    """0x42d380: the same sentinel guard over a flat byte table."""
    rows = []
    for index in (0, 1, 2, 127, 255):
        oracle.call(TABLE_BYTE_FLAT, (index,))
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
        want = _byte(oracle, FLAT_TABLE + index)
        if actual != want:
            raise AssertionError(
                f'flat table {index}: expected {want:#x}, got {actual:#x}')
        rows.append((index, actual))
    oracle.call(TABLE_BYTE_FLAT, (0xffffffff,))
    sentinel = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 0xff
    if sentinel != 0:
        raise AssertionError(f'index -1 must return 0, got {sentinel:#x}')
    rows.append((-1, sentinel))
    return rows


def clear_through_results(oracle):
    """0x4082c0 reads the primary, clears the fallback when it is set, and
    returns the primary either way."""
    rows = []
    for primary, fallback in ((0x00abcd00, SCRATCH), (0x1, 0),
                              (0xffffffff, SPARE), (0x5a5a5a5a, 0)):
        oracle.cpu.mem_write(SCRATCH, b'\xaa'*4)
        oracle.cpu.mem_write(SPARE, b'\xbb'*4)
        oracle.cpu.mem_write(PRIMARY_GLOBAL, struct.pack('<I', primary))
        oracle.cpu.mem_write(FALLBACK_GLOBAL, struct.pack('<I', fallback))
        oracle.call(CLEAR_THROUGH, ())
        actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if actual != primary:
            raise AssertionError(
                f'primary {primary:#x} came back as {actual:#x}')
        target = SCRATCH if fallback == SCRATCH else SPARE
        left = bytes(oracle.cpu.mem_read(target, 4))
        if fallback and left != b'\x00'*4:
            raise AssertionError(f'fallback target left as {left.hex()}')
        if not fallback and left != (b'\xbb'*4 if target == SPARE
                                     else b'\xaa'*4):
            raise AssertionError('a null fallback must leave memory alone')
        rows.append((primary, fallback))
    return rows


def pointer_clear_record_results(oracle):
    """0x429420 clears the dword behind the pointer and stores that pointer in
    the record global; a null pointer does neither."""
    rows = []
    for pointer, planted in ((SCRATCH, 0xcccccccc), (0, 0xcccccccc),
                             (SPARE, 0x12345678)):
        oracle.cpu.mem_write(SCRATCH, struct.pack('<I', planted))
        oracle.cpu.mem_write(SPARE, struct.pack('<I', planted))
        oracle.cpu.mem_write(POINTER_GLOBAL, struct.pack('<I', pointer))
        oracle.cpu.mem_write(RECORD_GLOBAL, struct.pack('<I', 0x5a5a5a5a))
        oracle.call(POINTER_CLEAR_RECORD, ())
        record = struct.unpack('<I', oracle.cpu.mem_read(RECORD_GLOBAL, 4))[0]
        if pointer:
            target = SCRATCH if pointer == SCRATCH else SPARE
            cleared = struct.unpack('<I', oracle.cpu.mem_read(target, 4))[0]
            if cleared != 0:
                raise AssertionError(f'pointer target left as {cleared:#x}')
            if record != pointer:
                raise AssertionError(
                    f'record global is {record:#x}, expected {pointer:#x}')
        else:
            left = struct.unpack('<I', oracle.cpu.mem_read(SCRATCH, 4))[0]
            if left != planted:
                raise AssertionError('a null pointer must not clear anything')
            if record != 0x5a5a5a5a:
                raise AssertionError('a null pointer must not record')
        rows.append((pointer, record))
    return rows


def verify(executable):
    oracle = DynoOracle(executable)
    oracle.cpu.mem_map(0, 0x1000)  # inert FS:[0] SEH chain
    return dict(
        state_or_mask_cases=len(state_or_mask_results(oracle)),
        counter_mod4_cases=len(counter_mod4_results(oracle)),
        table_byte_xy_cases=len(table_byte_xy_results(oracle)),
        table_byte_flat_cases=len(table_byte_flat_results(oracle)),
        clear_through_cases=len(clear_through_results(oracle)),
        pointer_clear_record_cases=len(pointer_clear_record_results(oracle)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(dict(verify(parser.parse_args().executable),
                          exact_output_bits=True,
                          scope='pseudocode-driven wave-0 batch: 0x414bf0, '
                                '0x42cc60, 0x42d350, 0x42d380, 0x4082c0, '
                                '0x429420 complete bodies; globals planted, '
                                'results read from registers and original '
                                'memory')))


if __name__ == '__main__':
    main()