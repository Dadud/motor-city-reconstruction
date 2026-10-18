"""Synthetic record-controller fixtures and explicit callback substitutions.

Callback bodies are replaced by RET plus a controlled memory-mutation hook.
The controller bodies and handler-selection jump tables are left unchanged.
Every callback observation contains the entire machine image before mutation.
"""
import struct
from contextlib import contextmanager

BASE = 0x98b9a0
SIZE = 0x780
RECORDS = 0x158
CURRENT = 0x758
HANDLERS = (0x42f630, 0x42f8f0, 0x431ba0, 0x432180,
            0x432730, 0x432bc0, 0x433200, 0x433820)
# Legacy fixture names preserve the original three-word transport; COUNT is
# preset zero and PENDING is the selected preset slot.
COUNT, INDEX, PENDING = 0x9aba98, 0x9abaa8, 0x9abaac
NONE = 0xffffffff


def pack(image, offset, value):
    struct.pack_into('<I', image, offset, value & 0xffffffff)


def machine(seed=0, slot=0, count=3, script=(NONE, NONE, 0, 0)):
    image = bytearray((seed+k*37) & 255 for k in range(SIZE))
    for k in range(6):
        start = RECORDS+k*256
        pack(image, start+4, (0, 15, 24, 29, 14, 22)[k])
        pack(image, start+8, HANDLERS[k % len(HANDLERS)])
    pack(image, 0x13c, BASE+RECORDS)
    pack(image, CURRENT, BASE+RECORDS+slot*256)
    return dict(image=image, count=count, index=0x12345678,
                pending=0x87654321, script=script)


def input_words(fixture):
    return [fixture['count'], fixture['index'], fixture['pending'],
            *fixture['script'], *fixture['image']]


def pair_image(rows):
    result = bytearray(b'\xa5'*64)
    for index, pair in enumerate(rows):
        pack(result, index*8, pair[0]); pack(result, index*8+4, pair[1])
    pack(result, len(rows)*8, NONE)
    return result


def scripts():
    return ((NONE, NONE, 0, 0),
            (NONE, NONE, 2, 0x12345678),
            (NONE, NONE, 4, 0),
            (NONE, NONE, 12, 3),
            (BASE+RECORDS+256, BASE+RECORDS+768, 3, 0xabcdef01),
            (NONE, NONE, 15, 0x80000000))


def fixtures(name):
    if name in ('record_machine_initialize', 'record_machine_reset'):
        for count in (0, 1, 7, 0x80000000, NONE):
            for k, script in enumerate(scripts()):
                yield [], None, machine(k*17, 2, count, script)
    elif name == 'record_transition':
        k = 0
        for pair_kind in range(4):
            for push in (0, 0x80000000):
                for slot in (0, 2):
                    for script in scripts():
                        f = machine(k*13, slot, 3, script)
                        old = (0, 15, 24, NONE)[k % 4]
                        new = (0, 14, 22, 24, NONE)[k % 5]
                        pack(f['image'], RECORDS+slot*256+4, old)
                        rows = ([(old, new)], [(new, old)],
                                [(0xabcdef, 0x765432), (new, old)], [])[pair_kind]
                        yield [new, HANDLERS[k % len(HANDLERS)], push,
                               (0x13579bdf+k) & NONE], pair_image(rows), f
                        k += 1
    elif name == 'record_activate':
        for present in (0, 1):
            for callback in (0, 0x432180):
                for script in scripts():
                    f = machine(37, 1, 3, script)
                    if not present: pack(f['image'], CURRENT, 0)
                    pack(f['image'], RECORDS+256+8, callback)
                    yield [], None, f
    else:
        raise ValueError(name)


class MachineOracle:
    def __init__(self, oracle):
        self.oracle = oracle
        self.logs = []
        self.script = (NONE, NONE, 0, 0)

    def word(self, address):
        return struct.unpack('<I', self.oracle.cpu.mem_read(address, 4))[0]

    def put(self, address, value):
        self.oracle.cpu.mem_write(address, struct.pack('<I', value & NONE))

    def reset(self, fixture):
        self.oracle.cpu.mem_write(BASE, bytes(fixture['image']))
        for address, value in ((COUNT, fixture['count']), (INDEX, fixture['index']),
                               (PENDING, fixture['pending'])):
            self.put(address, value)
        self.logs = []
        self.script = fixture['script']
        flags = self.oracle.cpu.reg_read(self.oracle.reg.UC_X86_REG_EFLAGS)
        self.oracle.cpu.reg_write(self.oracle.reg.UC_X86_REG_EFLAGS, flags & ~0x400)

    def observe(self, cpu, address, size, user):
        if address not in HANDLERS: return
        event = self.word(cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)+4)
        self.logs.append([address, event, self.word(COUNT), self.word(INDEX),
                          self.word(PENDING), *list(cpu.mem_read(BASE, SIZE))])
        redirect3, redirect0, mask, value = self.script
        redirect = redirect3 if event == 3 else redirect0
        if redirect != NONE: self.put(BASE+CURRENT, redirect)
        if mask & 1:
            current = self.word(BASE+CURRENT)
            if not BASE <= current <= BASE+SIZE-256:
                raise ValueError('callback fixture redirects outside arena')
            self.put(current+0x88, value); self.put(current+0xe8, value ^ event)
        if mask & 2:
            for k in range(3): self.put(BASE+0x90+k*4, value+k)
        if mask & 4:
            self.put(COUNT, value); self.put(INDEX, value ^ 0x55aa55aa)
            self.put(PENDING, value+1)
        if mask & 8:
            for offset in (0x140, 0x148, 0x14c, 0x150, 0x75c, 0x760, 0x76c):
                self.put(BASE+offset, value ^ offset)

    def output(self):
        result = [self.word(COUNT), self.word(INDEX), self.word(PENDING),
                  *list(self.oracle.cpu.mem_read(BASE, SIZE)), len(self.logs)]
        for log in self.logs: result.extend(log)
        return result

    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu = self.oracle.cpu
        saved = {address: bytes(cpu.mem_read(address, 1)) for address in HANDLERS}
        for address in HANDLERS: cpu.mem_write(address, b'\xc3')
        hook = cpu.hook_add(UC_HOOK_CODE, self.observe, begin=min(HANDLERS), end=max(HANDLERS))
        try:
            yield
        finally:
            cpu.hook_del(hook)
            for address, original in saved.items(): cpu.mem_write(address, original)
            if hasattr(cpu, 'ctl_flush_tb'): cpu.ctl_flush_tb()


def capture_cases(oracle, name, entry):
    if name == 'record_handler':
        result = []
        for identifier in (*range(36), 0x80000000, NONE):
            oracle.call(entry, (identifier,))
            result.append(dict(input=[identifier], output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)]))
        return result
    if name == 'record_pair_match':
        result = []
        values = (0, 1, 2, 15, 24, NONE)
        for rows in ([], [(1, 2)], [(2, 1)], [(0, 0)], [(15, NONE)],
                     [(24, 15), (1, 2), (2, 2)]):
            data = pair_image(rows)
            for first in values:
                for second in values:
                    oracle.cpu.mem_write(0x88acdc, bytes(data))
                    oracle.call(entry, (first, second))
                    result.append(dict(input=[first, second, *data],
                                       output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                                               *list(oracle.cpu.mem_read(0x88acdc, 64))]))
        return result
    if name == 'record_should_retain':
        result = []
        record, request = 0x71001000, 0x71004000
        for identifier in (*range(32), 0x80000000, NONE):
            for same in (0, 1):
                for override in (0, 1, 0x80000000):
                    for deadline in (4, 5, 6, 0x80000000, 0x7fffffff):
                        for parameter in (0, 1):
                            image = bytearray((k*37+identifier) & 255 for k in range(272))
                            req = bytearray(b'\xa5'*32)
                            pack(image, 4, identifier if same else identifier ^ 0x12345678)
                            pack(image, 0xe0, deadline); pack(image, 0xe8, parameter)
                            pack(req, 0, identifier); pack(req, 8, 1); pack(req, 12, override)
                            oracle.cpu.mem_write(record, bytes(image)); oracle.cpu.mem_write(request, bytes(req))
                            oracle.cpu.mem_write(0xaa456c, struct.pack('<I', 5))
                            oracle.call(entry, (record, request))
                            result.append(dict(input=[5, *image, *req],
                                               output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 255,
                                                       *list(oracle.cpu.mem_read(record, 272)),
                                                       *list(oracle.cpu.mem_read(request, 32))]))
        return result
    result = []
    machine_oracle = MachineOracle(oracle)
    with machine_oracle.substituted():
        for arguments, pairs, fixture in fixtures(name):
            machine_oracle.reset(fixture)
            if pairs is not None: oracle.cpu.mem_write(0x88acdc, bytes(pairs))
            oracle.call(entry, arguments)
            result.append(dict(input=[*arguments, *(list(pairs) if pairs is not None else []),
                                      *input_words(fixture)], output=machine_oracle.output()))
    return result


def lifecycle_cases(oracle):
    """A connected sequence of complete calls; separate from cell coverage."""
    result = []
    machine_oracle = MachineOracle(oracle)
    with machine_oracle.substituted():
        for seed in (0, 0xa5):
            fixture = machine(seed)
            machine_oracle.reset(fixture)
            pairs = pair_image([(24, 14)])
            oracle.cpu.mem_write(0x88acdc, bytes(pairs))
            oracle.call(0x434e40)
            machine_oracle.put(BASE+RECORDS+0xe0, 4)
            request = bytearray(16); pack(request, 0, 14); pack(request, 8, 0x1234)
            oracle.cpu.mem_write(0x71004000, bytes(request)); machine_oracle.put(0xaa456c, 5)
            oracle.call(0x435840, (BASE+RECORDS, 0x71004000))
            retained = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) & 255
            if retained: raise AssertionError('lifecycle fixture requires expired retention')
            oracle.call(0x435270, (14,)); handler = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            oracle.call(0x433dd0, (24, 14)); matched = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            oracle.call(0x432620, (14, handler, 1, 0x1234))
            oracle.call(0x436230)
            oracle.call(0x435f80)
            oracle.call(0x435fb0, (24,)); has24 = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            oracle.call(0x435fb0, (14,)); has14 = oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            result.append(dict(input=input_words(fixture),
                               output=[retained, handler, matched, has24, has14,
                                       *machine_oracle.output()]))
    return dict(scope='connected complete-call lifecycle; callbacks explicitly substituted',
                cases=result)
