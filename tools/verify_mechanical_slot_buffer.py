"""Compare original `0x52c6b0` mechanical-slot allocation and initialization."""
import argparse
import struct

from client.mechanical_parts import create_mechanical_slot_buffer
from tools.native_oracle import DynoOracle


def verify(executable):
    import unicorn

    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    # The original uses FS:[0] for its local SEH registration chain.
    cpu.mem_map(0, 0x1000)
    base = 0x74000000
    cpu.mem_map(base, 0x100000)
    allocate_at = base + 0x10000
    cases = (0, 1, 2, 7, 16)
    allocation_log = []
    constructor_log = []
    active_case = 0
    cursor = allocate_at

    def hook(uc, address, _size, _user):
        nonlocal cursor
        if address == 0x661160:
            constructor_log.append(uc.reg_read(reg.UC_X86_REG_ECX))
            return
        if address != 0x6ee530:
            return
        esp = uc.reg_read(reg.UC_X86_REG_ESP)
        ret, tag_ptr, size, pool = struct.unpack('<IIII', uc.mem_read(esp, 16))
        tag = bytes(uc.mem_read(tag_ptr, 32)).split(b'\0', 1)[0]
        allocation_log.append((tag, size, pool))
        # Count two deliberately exercises the original allocation-failure path.
        if active_case == 2:
            result = 0
        else:
            result = cursor
            cursor = (cursor + size + 15) & ~15
        uc.reg_write(reg.UC_X86_REG_EAX, result)
        uc.reg_write(reg.UC_X86_REG_ESP, esp + 4)
        uc.reg_write(reg.UC_X86_REG_EIP, ret)

    hook_id = cpu.hook_add(unicorn.UC_HOOK_CODE, hook)
    comparisons = 0
    try:
        for count in cases:
            active_case = count
            allocation_log.clear()
            constructor_log.clear()
            cursor = allocate_at
            try:
                result = oracle.call(0x52c6b0, (count,), instruction_limit=100_000)
            except Exception as error:
                raise RuntimeError(('original allocation routine failed', count,
                                    hex(cpu.reg_read(reg.UC_X86_REG_EIP)),
                                    allocation_log, len(constructor_log))) from error
            actual_pointer = cpu.reg_read(reg.UC_X86_REG_EAX)
            failed = count == 2
            expected_pointer = 0 if count == 0 or failed else allocate_at
            if actual_pointer != expected_pointer:
                raise AssertionError(('return pointer', count, hex(actual_pointer),
                                      hex(expected_pointer)))
            expected_calls = [] if count == 0 else [(b'PARTS', count * 0x1308, 0)]
            if allocation_log != expected_calls:
                raise AssertionError(('allocator calls', count, allocation_log,
                                      expected_calls))
            expected_constructors = 0 if count == 0 or failed else 2 * count
            if len(constructor_log) != expected_constructors:
                raise AssertionError(('initializer calls', count,
                                      len(constructor_log), expected_constructors))
            if actual_pointer:
                actual = bytes(cpu.mem_read(actual_pointer, count * 0x1308))
                expected = create_mechanical_slot_buffer(
                    count, lambda *_: bytearray([0xa5]) * (count * 0x1308), pool=0)
                if actual != expected:
                    offset = next(i for i, (a, b) in enumerate(zip(actual, expected))
                                  if a != b)
                    raise AssertionError(('cleared image', count, hex(offset)))
            comparisons += 1
    finally:
        cpu.hook_del(hook_id)
    return {'cases': comparisons, 'counts': list(cases),
            'allocation_failures': 1, 'maximum_byte_error': 0,
            'original_entry': '0x52c6b0',
            'scope': 'zero-count, successful allocation, one stubbed allocation failure, original two-initializers-per-slot, and complete post-initialization clear'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args = parser.parse_args()
    print(verify(args.executable))


if __name__ == '__main__':
    main()
