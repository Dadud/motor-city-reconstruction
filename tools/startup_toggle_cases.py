"""Returning key APIs for connected original startup, with explicit register clobbers."""
import struct
from contextlib import contextmanager
from tools.input_toggle_key_cases import QUERY, EVENT, Q, FIRST, SECOND


class ToggleOracle:
    def __init__(self, oracle):
        self.oracle = oracle

    def word(self, address):
        return struct.unpack('<I', self.oracle.cpu.mem_read(address, 4))[0]

    def put(self, address, value):
        self.oracle.cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def reset(self, config):
        self.state, self.script = config
        self.logs = []
        self.put(QUERY, Q)
        self.put(EVENT, FIRST)

    def observe(self, cpu, address, size, user):
        esp = cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        at = lambda n: self.word(esp + 4 + n * 4)
        if address == Q:
            self.logs.append([0, 0, at(0), 0, 0, 0,
                              self.word(0xb3656c), self.word(0xacae00)])
            if self.script & 1:
                self.put(EVENT, SECOND)
            cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX, self.state)
        else:
            key, scan, flags, extra = at(0) & 255, at(1) & 255, at(2), at(3)
            self.logs.append([1, int(address == SECOND), key, scan, flags, extra,
                              self.word(0xb3656c), self.word(0xacae00)])
            if self.script & 2:
                self.put(EVENT, FIRST if address == SECOND else SECOND)
            if flags & 2 and not self.script & 4:
                self.state ^= 1
        # The original local initially holds ECX; its low byte becomes scan 0x45.
        # POP ECX restores that modified local, discarding these API clobbers.
        cpu.reg_write(self.oracle.reg.UC_X86_REG_ECX, 0xdeadbeef)

    def output(self):
        return [self.state, int(self.word(EVENT) == SECOND), len(self.logs),
                *(v for row in self.logs for v in row)]

    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu = self.oracle.cpu
        saved = {a: bytes(cpu.mem_read(a, 4)) for a in (QUERY, EVENT)}
        cpu.mem_write(Q, b'\xc2\x04\x00')
        for address in (FIRST, SECOND):
            cpu.mem_write(address, b'\xc2\x10\x00')
        hooks = [cpu.hook_add(UC_HOOK_CODE, self.observe, begin=a, end=a)
                 for a in (Q, FIRST, SECOND)]
        try:
            yield
        finally:
            for hook in hooks:
                cpu.hook_del(hook)
            for address, data in saved.items():
                cpu.mem_write(address, data)


def lifecycle_cases(oracle):
    from tools.startup_initialize_cases import lifecycle_cases as capture
    return capture(oracle, with_toggle=True)
