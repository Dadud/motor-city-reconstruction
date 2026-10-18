"""Original-comparison oracle for the wave-0 integer leaf helpers.

Two unrelated leaf routines share one oracle because they share one method:
supply the globals and the arguments, run the original's complete body through
DynoOracle.call, and read the result from the emulated registers and memory.

  0x406a30  stores one global through a pointer and returns another
  0x405910  divides its argument by whichever global the original selects
"""
import argparse
import json
import math
import struct

from tools.native_oracle import DynoOracle

GLOBAL_STORE = 0x406a30
SINGLETON_QUOTIENT = 0x405910
ENTITY_FLAG = 0x405df0
REGISTRY_REGISTER = 0x4072c0
REGISTRY_RESET = 0x407550
REGISTRY_SLOT_WRITE = 0x4077a0
REGISTRY_SLOT_USED = 0x407d70
BUFFER_COPY12_A = 0x4081c0
BUFFER_COPY12_B = 0x408510
ENTITY_CLEAR = 0x408ea0
ENTITY_OR_STORE = 0x409110
STRUCT_INITIALIZER = 0x403200
ENTITY_FLAG3 = 0x403440
STORED = 0x8e3ac0
RETURNED = 0x8e3abc
PRIMARY = 0x9aaa98
FALLBACK = 0x988e38
SCRATCH = 0x71001000
TABLE = 0x71002000
NODE = 0x71003000

GLOBAL_VALUES = (0, 1, 0x1234, 0x4321, 0x80000000, 0xffffffff)
# (primary, numerator, fallback): the divisor is whichever global the original
# selects, read as signed because IDIV treats ECX as signed.
QUOTIENT_CASES = ((3, 100, 7), (7, 100, 3), (7, -100, 3), (0, 100, -7),
                  (0, 7, 2), (0, -7, 2), (3, 0x7fffffff, 5), (0x80000000, 5, 2),
                  (1, 100, 9), (2, 100, 9), (0, 6, 3), (5, 0, 2), (2, -1, 9))


def _signed(value):
    return value-(1 << 32) if value >= (1 << 31) else value


def entity_flag_results(oracle):
    """0x405df0: table_base[index*28 + 26] bit 0, returned as 0 or 1.

    The table base is an emulated address the oracle supplies, so the index
    range stays inside the planted scratch and cannot touch unmapped memory.
    """
    pattern = bytes((index*37 + offset*13) & 255
                    for index in range(8) for offset in range(28))
    rows = []
    for base_offset in (0, 28, 56):
        for index in (0, 1, 2, 5):
            oracle._reset()
            oracle.cpu.mem_write(TABLE, pattern)
            oracle.cpu.mem_write(0x8e3ab8,
                                 struct.pack('<I', TABLE+base_offset))
            oracle.call(ENTITY_FLAG, (index,))
            expected = (pattern[base_offset+index*28+26] & 1) != 0
            actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            if actual not in (0, 1):
                raise AssertionError(
                    f'entity flag must return 0 or 1, got {actual:#x}')
            if actual != int(expected):
                raise AssertionError(
                    f'entity flag mismatch base {base_offset:#x} index {index}: '
                    f'expected {int(expected)}, got {actual}')
            rows.append((base_offset, index, actual))
    return rows


def global_store_results(oracle):
    """Reference outputs: what the original actually did, per case."""
    rows = []
    for stored in GLOBAL_VALUES:
        for returned in GLOBAL_VALUES:
            oracle.cpu.mem_write(STORED, struct.pack('<I', stored))
            oracle.cpu.mem_write(RETURNED, struct.pack('<I', returned))
            oracle.cpu.mem_write(SCRATCH, b'\xcc'*0x10)
            oracle.call(GLOBAL_STORE, (SCRATCH,))
            rows.append((stored, returned,
                         struct.unpack('<I', oracle.cpu.mem_read(SCRATCH, 4))[0],
                         oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)))
    return rows


def quotient_results(oracle):
    """Reference outputs, including the divide-by-zero fault case.

    A zero effective divisor faults in the original, so those rows carry a
    fault rather than a quotient and are reported instead of compared.
    """
    rows = []
    for primary, numerator, fallback in QUOTIENT_CASES:
        oracle.cpu.mem_write(PRIMARY, struct.pack('<I', primary & 0xffffffff))
        oracle.cpu.mem_write(FALLBACK, struct.pack('<I', fallback & 0xffffffff))
        oracle.call(SINGLETON_QUOTIENT, (numerator & 0xffffffff,))
        divisor = _signed(primary if primary != 0 else fallback)
        rows.append((primary, numerator, fallback,
                     oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                     None if divisor == 0 else math.trunc(
                         _signed(numerator)/divisor)))
    return rows


def registry_register_results(oracle):
    """0x4072c0: node[0x20]=counter, counter+1, node[0x54]=head.

    A NULL node is rejected by the original, so the oracle always supplies a
    planted 0x58-byte image. The counter wrap at 0xffffffff is a real case.
    """
    rows = []
    for counter in (0, 1, 0x7fffffff, 0xffffffff):
        for head in (0, 0x1234, 0x4321):
            oracle._reset()
            oracle.cpu.mem_write(NODE, b'\xcc'*0x58)
            oracle.cpu.mem_write(0x886b9c, struct.pack('<I', counter))
            oracle.cpu.mem_write(0x8e3b30, struct.pack('<I', head))
            oracle.call(REGISTRY_REGISTER, (NODE,))
            image = bytes(oracle.cpu.mem_read(NODE, 0x58))
            identifier = struct.unpack('<I', image[0x20:0x24])[0]
            linked = struct.unpack('<I', image[0x54:0x58])[0]
            new_counter = struct.unpack('<I',
                oracle.cpu.mem_read(0x886b9c, 4))[0]
            new_head = struct.unpack('<I',
                oracle.cpu.mem_read(0x8e3b30, 4))[0]
            expected_id = (counter+1) & 0xffffffff
            good = (identifier == counter and linked == head
                    and new_counter == expected_id and new_head == NODE)
            if not good:
                raise AssertionError(
                    f'registry register counter {counter:#x} head {head:#x}: '
                    f'id {identifier:#x} link {linked:#x} new counter '
                    f'{new_counter:#x} new head {new_head:#x}')
            rows.append((counter, head, identifier, linked, new_counter,
                         new_head))
    return rows


def entity_flag3_results(oracle):
    """0x403440: inverse of the flag predicate on bit 3, with a NULL default.

    An empty or NULL table returns 1; a record whose flag byte has bit 3 set
    returns 0; bit 3 clear returns 1. Verified across records and bases.
    """
    pattern = bytes((index*41 + offset*7) & 255
                    for index in range(6) for offset in range(28))
    rows = []
    for base_offset in (0, 28):
        for index in (0, 1, 3):
            for extra in (0, 8):
                oracle._reset()
                patched = bytearray(pattern)
                patched[base_offset+index*28+26] = (pattern[
                    base_offset+index*28+26] & 0xf7) | extra
                oracle.cpu.mem_write(TABLE, bytes(patched))
                oracle.cpu.mem_write(0x8e3ab8,
                                     struct.pack('<I', TABLE+base_offset))
                oracle.call(ENTITY_FLAG3, (index,))
                flag3 = (patched[base_offset+index*28+26] >> 3) & 1
                expected = 0 if flag3 else 1
                actual = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                if actual != expected:
                    raise AssertionError(
                        f'entity flag3 mismatch base {base_offset:#x} index '
                        f'{index} byte {patched[base_offset+index*28+26]:#x}: '
                        f'expected {expected}, got {actual}')
                rows.append((base_offset, index, extra, actual))
    return rows


def registry_reset_results(oracle):
    """0x407550: each 24-byte record gets 0/0xffffffff/0 in its first three
    dwords and keeps whatever sits in its tail, which the oracle plants as
    nonzero so the untouched bytes are provably untouched."""
    registry = bytearray(b'\xaa'*0x1804)
    oracle._reset()
    oracle.cpu.mem_write(0x8e3b38, bytes(registry))
    oracle.call(REGISTRY_RESET, (), cleanup=b'')
    after = bytes(oracle.cpu.mem_read(0x8e3b38, 0x1804))
    for record in range(256):
        base = record*24
        if after[base:base+4] != b'\x00'*4 or after[base+4:base+8] != b'\xff'*4 \
                or after[base+8:base+12] != b'\x00'*4:
            raise AssertionError(
                f'registry record {record} head is wrong: '
                f'{after[base:base+12].hex()}')
        if after[base+12:base+24] != b'\xaa'*12:
            raise AssertionError(
                f'registry record {record} tail was rewritten')
    # The loop stops once its cursor reaches 0x8e533c, so the last 16 bytes
    # of the span are never written and must keep the planted bytes.
    if after[0x17e8:0x17ec] != b'\x00'*4 or after[0x17ec:0x17f0] != b'\xff'*4 \
            or after[0x17f0:0x17f4] != b'\x00'*4:
        raise AssertionError('the last written record head is wrong')
    if after[0x17f4:0x1804] != b'\xaa'*16:
        raise AssertionError('bytes past the last record were rewritten')
    return [len(after)]


def registry_slot_results(oracle):
    """0x4077a0 writes three dwords into slot*24; 0x407d70 reports whether a
    slot's first dword is nonzero."""
    rows = []
    for slot in (0, 1, 7, 255):
        oracle._reset()
        oracle.cpu.mem_write(0x8e3b38, b'\x00'*0x1804)
        oracle.call(REGISTRY_SLOT_WRITE, (slot, 0x11111111, 0x22222222,
                                          0x33333333))
        base = slot*24
        read = struct.unpack('<III',
                             oracle.cpu.mem_read(0x8e3b38+base+12, 12))
        if read != (0x11111111, 0x22222222, 0x33333333):
            raise AssertionError(
                f'slot write {slot}: {read} at offsets 12/16/20')
        # The used predicate tests dword[slot*24], the field the registration
        # write leaves untouched, so the oracle plants it directly.
        oracle.cpu.mem_write(0x8e3b38+base, struct.pack('<I', 0x999))
        oracle.call(REGISTRY_SLOT_USED, (slot,))
        used = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if used != 1:
            raise AssertionError(f'slot {slot} should read used, got {used}')
        oracle.cpu.mem_write(0x8e3b38+base, struct.pack('<I', 0))
        oracle.call(REGISTRY_SLOT_USED, (slot,))
        unused = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
        if unused != 0:
            raise AssertionError(
                f'slot {slot} should read unused, got {unused}')
        rows.append((slot, used, unused))
    return rows


def verify(executable):
    oracle = DynoOracle(executable)
    oracle.cpu.mem_map(0, 0x1000)  # inert FS:[0] SEH chain
    stored = global_store_results(oracle)
    quotient = quotient_results(oracle)
    flags = entity_flag_results(oracle)
    flags3 = entity_flag3_results(oracle)
    registered = registry_register_results(oracle)
    reset = registry_reset_results(oracle)
    slots = registry_slot_results(oracle)
    mismatched = [row for row in quotient
                  if row[4] is not None and _signed(row[3]) != row[4]]
    if mismatched:
        raise AssertionError(
            'the original did not follow truncating division: '
            f'{[(r[0], r[1], r[2], hex(r[3]), r[4]) for r in mismatched[:3]]}')
    wrong_store = [row for row in stored
                   if row[2] != row[0] or row[3] != row[1]]
    if wrong_store:
        raise AssertionError(
            f'global store did not copy and return: {wrong_store[:3]}')
    return dict(global_store_cases=len(stored), quotient_cases=len(quotient),
                entity_flag_cases=len(flags),
                entity_flag3_cases=len(flags3),
                registry_register_cases=len(registered),
                registry_reset_bytes=reset[0],
                registry_slot_cases=len(slots))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(dict(verify(parser.parse_args().executable),
                          exact_output_bits=True,
                          scope='0x406a30 and 0x405910 complete bodies; '
                                'globals and arguments planted, results read '
                                'from original memory and registers; covers 0x406a30, 0x405910, '
                                '0x405df0, 0x4072c0')))


if __name__ == '__main__':
    main()