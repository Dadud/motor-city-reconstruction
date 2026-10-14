"""Check original wait-unit conversion without calling host Sleep."""
import argparse
import json
import struct

from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    boundary = oracle.stub + 0x100
    cpu.mem_write(0x83b298, struct.pack('<I', boundary))
    observed = []

    def capture(_cpu, _address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target, milliseconds = struct.unpack('<II', cpu.mem_read(stack, 8))
        observed.append(milliseconds)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 8)
        cpu.reg_write(reg.UC_X86_REG_EIP, target)

    hook = cpu.hook_add(UC_HOOK_CODE, capture, begin=boundary, end=boundary)
    values = (0, 1, 999, 1000, 1001, 249999, 250000, 250001,
              0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)
    try:
        for value in values:
            oracle._reset()
            observed.clear()
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<II', oracle.stop, value))
            oracle._run(0x7e3e50, oracle.stop, count=30)
            if observed != [value // 1000]:
                raise AssertionError('original Sleep-unit conversion differs')
    finally:
        cpu.hook_del(hook)
    return {'matched_unsigned_conversion_cases': len(values),
            'poll_microseconds': 250000, 'sleep_milliseconds': 250,
            'substituted_boundary': 'Windows Sleep import: capture argument and return',
            'host_sleep_executed': False, 'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
