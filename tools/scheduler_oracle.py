"""Bounded original callback executor with supplied callback bodies.

No PE entry point, imports, clock, sockets, or actual game callbacks execute.
"""
import argparse
import itertools
import json
import struct

from client.scheduler import ScheduledCall, insert_callback, execute_callbacks, execute_batch, selected_iterations, pending_iterations
from tools.native_oracle import DynoOracle


class SchedulerOracle(DynoOracle):
    def insert(self, entries, entry):
        self._reset()
        data = bytearray(8 + (len(entries) + 2) * 16)
        struct.pack_into('<ii', data, 0, len(entries) + 1, len(entries))
        for index in range(len(entries) + 2):
            struct.pack_into('<iIII', data, 8 + index * 16, 0x7ffe, 0, 0, 0)
        for index, current in enumerate(entries):
            struct.pack_into('<iIII', data, 8 + index * 16, current.priority,
                             current.callback, current.payload, 0)
        self.cpu.mem_write(self.inputs, bytes(data))
        stack = self.frame - 0x1000
        self.cpu.mem_write(stack, struct.pack('<IIIIi', self.stop, self.inputs,
            entry.callback, entry.payload, entry.priority))
        self._run(0x565d20, self.stop, count=10000)
        count = struct.unpack('<i', self.cpu.mem_read(self.inputs + 4, 4))[0]
        return [ScheduledCall(*struct.unpack('<iII', self.cpu.mem_read(self.inputs + 8 + index*16, 12)))
                for index in range(count)]

    def pending(self, clock, processed):
        from unicorn import UC_HOOK_CODE
        self._reset()
        self.cpu.mem_write(0x98ccac, struct.pack('<I', clock))
        self.cpu.mem_write(0xaa4568, struct.pack('<I', processed))
        def hook(cpu, address, size, user):
            if address == 0x6bd810:
                stack = cpu.reg_read(self.reg.UC_X86_REG_ESP)
                target = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
                cpu.reg_write(self.reg.UC_X86_REG_ESP, stack + 4)
                cpu.reg_write(self.reg.UC_X86_REG_EIP, target)
        token = self.cpu.hook_add(UC_HOOK_CODE, hook)
        try:
            self._run(0x568863, 0x5688a0, count=1000)
        finally:
            self.cpu.hook_del(token)
        result = self.cpu.reg_read(self.reg.UC_X86_REG_EDI)
        return 0 if result & 0x80000000 else result

    def batch(self, counter, frame, enabled, mode, inhibited):
        from unicorn import UC_HOOK_CODE
        self._reset()
        for index in range(2):
            owner = self.inputs + index * 0x100
            callback = self.stub + 0x300 + index * 16
            self.cpu.mem_write(owner, struct.pack('<iiiIII', 1, 1, 30, callback, index + 10, 0))
            self.cpu.mem_write(callback, b'\xc3')
            self.cpu.mem_write(0xaa4594 - index * 4, struct.pack('<I', owner))
        self.cpu.mem_write(0xaa456c, struct.pack('<I', counter))
        self.cpu.mem_write(0xaa4570, struct.pack('<i', frame))
        self.cpu.mem_write(self.frame - 4, struct.pack('<i', 1))
        self.cpu.mem_write(self.frame + 8, struct.pack('<i', int(inhibited)))
        self.cpu.reg_write(self.reg.UC_X86_REG_EDI, 1)
        calls = []
        def hook(cpu, address, size, user):
            if address in (0x55fc10, 0x55fc80, 0x434f90):
                if address == 0x434f90:
                    calls.append('after')
                value = int(enabled) if address == 0x55fc10 else mode if address == 0x55fc80 else 0
                stack = cpu.reg_read(self.reg.UC_X86_REG_ESP)
                target = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
                cpu.reg_write(self.reg.UC_X86_REG_ESP, stack + 4)
                cpu.reg_write(self.reg.UC_X86_REG_EIP, target)
                cpu.reg_write(self.reg.UC_X86_REG_EAX, value & 0xffffffff)
            elif address in (self.stub + 0x300, self.stub + 0x310):
                stack = cpu.reg_read(self.reg.UC_X86_REG_ESP)
                payload = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
                expected = 10 if address == self.stub + 0x300 else 11
                if payload != expected:
                    raise AssertionError('callback payload')
                calls.append('first' if expected == 10 else 'second')
        token = self.cpu.hook_add(UC_HOOK_CODE, hook)
        try:
            self._run(0x568523, 0x5685c5, count=10000)
        finally:
            self.cpu.hook_del(token)
        result = struct.unpack('<I', self.cpu.mem_read(0xaa456c, 4))[0]
        return result, calls

    def execute(self, entries, mutation=None):
        from unicorn import UC_HOOK_CODE
        self._reset()
        owner = self.inputs
        # Each supplied callback has a distinct stable stub; no rewriting code.
        callback_base = self.stub + 0x100
        data = bytearray(8 + (len(entries) + 2) * 16)
        struct.pack_into('<ii', data, 0, len(entries) + 1, len(entries))
        for index, entry in enumerate(entries):
            callback = callback_base + entry.callback * 16 if entry.callback else 0
            struct.pack_into('<iIII', data, 8 + index * 16,
                             entry.priority, callback, entry.payload, 0x12345678)
            if callback:
                self.cpu.mem_write(callback, b'\xc3')
        self.cpu.mem_write(owner, bytes(data))
        calls = []
        def hook(cpu, address, size, user):
            if callback_base <= address < callback_base + 128:
                stack = cpu.reg_read(self.reg.UC_X86_REG_ESP)
                payload = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
                calls.append(((address - callback_base) // 16, payload))
                if mutation and len(calls) == 1:
                    # Replace second entry and enlarge count. The original
                    # captured count must prevent visiting the appended entry.
                    cpu.mem_write(owner + 8 + 16 + 4,
                                  struct.pack('<II', callback_base + 16, 0xffffffff))
                    cpu.mem_write(owner + 4, struct.pack('<i', len(entries) + 1))
                    cpu.mem_write(owner + 8 + len(entries) * 16,
                                  struct.pack('<iIII', 100, callback_base + 16, 99, 0))
        token = self.cpu.hook_add(UC_HOOK_CODE, hook)
        stack = self.frame - 0x1000
        self.cpu.mem_write(stack, struct.pack('<II', self.stop, owner))
        try:
            self._run(0x565e40, self.stop, count=10000)
        finally:
            self.cpu.hook_del(token)
        return calls


def compare(executable):
    oracle = SchedulerOracle(executable)
    insertion_count = 0
    for priorities in itertools.product((-(1 << 31), -1, 0, 30, 0x7ffe, (1 << 31)-1), repeat=3):
        entries = []
        for index, priority in enumerate(priorities):
            entry = ScheduledCall(priority, index + 1, 0xffffffff - index)
            expected = oracle.insert(entries, entry)
            insert_callback(entries, entry)
            if entries != expected:
                raise AssertionError(('insertion', priorities, entries, expected))
            insertion_count += 1
    count = 0
    for length in range(6):
        for mask in itertools.product((0, 1, 2), repeat=length):
            entries = [ScheduledCall((i % 3) - 1, value, 0xffffffff - i)
                       for i, value in enumerate(mask)]
            expected = []
            execute_callbacks(entries, lambda callback, payload: expected.append((callback, payload)))
            if expected != oracle.execute(entries):
                raise AssertionError((entries, expected))
            count += 1
    entries = [ScheduledCall(7, 2, 42), ScheduledCall(-1, 2, 17)]
    expected = []
    def mutate(callback, payload):
        expected.append((callback, payload))
        if len(expected) == 1:
            entries[1] = ScheduledCall(-1, 1, 0xffffffff)
            entries.append(ScheduledCall(100, 1, 99))
    original_entries = list(entries)
    execute_callbacks(entries, mutate)
    if expected != oracle.execute(original_entries, mutation=True):
        raise AssertionError('count snapshot or entry mutation mismatch')
    batch_count = 0
    for counter, frame, enabled, mode, inhibited in itertools.product(
            (0, 1, 2, 0xfffffffe, 0xffffffff),
            (-(1 << 31), -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, (1 << 31)-1),
            (False, True), (-1, 0, 1, 2, 3, 4), (False, True)):
        calls = []
        repeats = selected_iterations(enabled, mode, frame)
        result = execute_batch(counter, repeats, inhibited,
            lambda: calls.append('first'), lambda: calls.append('second'), lambda: calls.append('after'))
        if (result, calls) != oracle.batch(counter, frame, enabled, mode, inhibited):
            raise AssertionError((counter, frame, enabled, mode, inhibited, result, calls))
        batch_count += 1
    pending_count = 0
    for clock, processed in itertools.product((0, 1, 15, 16, 17, 50, 0x7fffffff, 0x80000000, 0xffffffff), repeat=2):
        if pending_iterations(clock, processed) != oracle.pending(clock, processed):
            raise AssertionError(('pending', clock, processed))
        pending_count += 1
    return {'insertion_cases': insertion_count, 'executor_cases': count + 1,
            'batch_cases': batch_count, 'pending_cases': pending_count,
            'scope': 'original executor, repeat selector and interleaving; supplied callbacks/mode observations; no wall clock'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    print(json.dumps(compare(parser.parse_args().executable)))
