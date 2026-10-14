"""Bounded original worker completion query with synthetic linked queues.

Executes wrapper 0x4a5610, removal 0x45f440 and comparator 0x4a51c0.
Virtual size/copy/payload-free and node-free are captured substitutions; locks
are disabled. No host threads, services, allocation or credentials execute.
"""
import argparse
import itertools
import json
import random
import struct

from client.async_worker_completion import WORKER_RECORD_SIZE, WorkerCompletionQueue
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    worker, queue, table = oracle.inputs, oracle.inputs + 0x48, oracle.inputs + 0x1000
    output = oracle.inputs + 0x9000
    size_address, copy_address, payload_free = oracle.stub + 0x8000, oracle.stub + 0x8100, oracle.stub + 0x8200
    rng = random.Random(0x4a5610)
    state = {}

    def boundary(_cpu, address, _size, _user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        if address == 0x4a51c0:
            selector, payload = struct.unpack('<2I', cpu.mem_read(stack + 4, 8))
            if struct.unpack('<I', cpu.mem_read(selector, 4))[0] != state['requested']:
                raise AssertionError('original completion selector differs')
            index = state['payloads'].index(payload)
            state['events'].append(('compare', index))
            return  # Execute the original comparator, rather than substitute it.
        if address == 0x69b30f:
            exception, descriptor = struct.unpack('<2I', cpu.mem_read(stack + 4, 8))
            if descriptor != 0x85a8a8 or struct.unpack('<I', cpu.mem_read(exception, 4))[0] != 0x892b5c:
                raise AssertionError('original zero-ID throw arguments differ')
            state['events'].append(('throw', 0))
            cpu.reg_write(reg.UC_X86_REG_EIP, oracle.stop)
            return
        selected = state['selected']
        if selected is None:
            raise AssertionError('original unmatched query invoked copy/free boundary')
        payload = state['payloads'][selected]
        if address == size_address:
            if cpu.reg_read(reg.UC_X86_REG_ECX) != queue:
                raise AssertionError('original size owner differs')
            if struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0] != payload:
                raise AssertionError('original size source differs')
            state['events'].append(('size', selected))
            cpu.reg_write(reg.UC_X86_REG_EAX, WORKER_RECORD_SIZE)
            cleanup = 4
        elif address == copy_address:
            destination, source, count = struct.unpack('<3I', cpu.mem_read(stack + 4, 12))
            if (cpu.reg_read(reg.UC_X86_REG_ECX), destination, source, count) != (queue, output, payload, WORKER_RECORD_SIZE):
                raise AssertionError('original completion copy arguments differ')
            if bytes(cpu.mem_read(worker, 0x100)) != state['before']:
                raise AssertionError('original queue changed before output copy')
            cpu.mem_write(destination, bytes(cpu.mem_read(source, count)))
            state['events'].append(('copy', selected))
            cleanup = 12
        elif address in (payload_free, 0x6992c5):
            supplied = struct.unpack('<I', cpu.mem_read(stack + 4, 4))[0]
            expected = payload if address == payload_free else state['nodes'][selected]
            if supplied != expected:
                raise AssertionError('original completion free argument differs')
            if address == payload_free and cpu.reg_read(reg.UC_X86_REG_ECX) != queue:
                raise AssertionError('original payload-free owner differs')
            if bytes(cpu.mem_read(worker, 0x100)) != state['after']:
                raise AssertionError('original queue fields not detached before free')
            for node, expected_image in zip(state['nodes'], state['node_images']):
                if bytes(cpu.mem_read(node, 0x14)) != expected_image:
                    raise AssertionError('original queue links not detached before free')
            state['events'].append(('payload_free' if address == payload_free else 'node_free', selected))
            cleanup = 4 if address == payload_free else 0
        else:
            raise AssertionError('unexpected completion boundary')
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cpu.reg_write(reg.UC_X86_REG_ESP, stack + 4 + cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    hooks = [cpu.hook_add(UC_HOOK_CODE, boundary, begin=address, end=address)
             for address in (0x4a51c0, 0x69b30f, size_address, copy_address, payload_free, 0x6992c5)]

    def initialize(ids, mark_pattern, requested, copy_output):
        oracle._reset()
        records = []
        nodes = [oracle.inputs + 0x2000 + index * 0x40 for index in range(len(ids))]
        payloads = [oracle.inputs + 0x3000 + index * 0x1000 for index in range(len(ids))]
        marks = [0 if mark_pattern == 0 else (1 if mark_pattern == 1 else index % 2) for index in range(len(ids))]
        before = bytearray(rng.randbytes(0x100))
        struct.pack_into('<II', before, 0x48, table, WORKER_RECORD_SIZE)
        struct.pack_into('<4I', before, 0x48 + 0x14,
                         nodes[0] if nodes else 0, nodes[-1] if nodes else 0, len(nodes), sum(marks))
        struct.pack_into('<I', before, 0x48 + 0x3c, 0)
        struct.pack_into('<I', before, 0x48 + 0x40, 0x87654321)
        cpu.mem_write(worker, bytes(before))
        cpu.mem_write(table + 8, struct.pack('<I', 0x4a51c0))
        cpu.mem_write(table + 0x10, struct.pack('<I', size_address))
        cpu.mem_write(table + 0x1c, struct.pack('<I', payload_free))
        cpu.mem_write(table + 0x20, struct.pack('<I', copy_address))
        initial_nodes = []
        for index, (node, payload, operation_id, mark) in enumerate(zip(nodes, payloads, ids, marks)):
            node_image = struct.pack('<5I', nodes[index-1] if index else 0,
                nodes[index+1] if index+1 < len(nodes) else 0, rng.getrandbits(32), mark, payload)
            initial_nodes.append(bytearray(node_image))
            cpu.mem_write(node, node_image)
            record = bytearray(rng.randbytes(WORKER_RECORD_SIZE))
            struct.pack_into('<I', record, 4, operation_id)
            records.append(bytes(record))
            cpu.mem_write(payload, bytes(record))
        selected = next((index for index, value in enumerate(ids) if value == requested), None)
        after = bytearray(before)
        if selected is not None:
            prev = nodes[selected-1] if selected else 0
            nxt = nodes[selected+1] if selected+1 < len(nodes) else 0
            if selected == 0:
                struct.pack_into('<I', after, 0x48 + 0x14, nxt)
            if selected == len(nodes)-1:
                struct.pack_into('<I', after, 0x48 + 0x18, prev)
            struct.pack_into('<I', after, 0x48 + 0x1c, len(nodes)-1)
            struct.pack_into('<I', after, 0x48 + 0x20, sum(marks)-bool(marks[selected]))
            struct.pack_into('<I', after, 0x48 + 0x40, 1)
            if prev:
                struct.pack_into('<I', initial_nodes[selected-1], 4, nxt)
            if nxt:
                struct.pack_into('<I', initial_nodes[selected+1], 0, prev)
        state.clear()
        state.update(requested=requested, selected=selected, nodes=nodes, payloads=payloads,
                     before=bytes(before), after=bytes(after), node_images=[bytes(value) for value in initial_nodes], events=[])
        sentinel = bytes([0x5a]) * WORKER_RECORD_SIZE
        cpu.mem_write(output, sentinel)
        cpu.reg_write(reg.UC_X86_REG_ECX, worker)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<3I', oracle.stop, requested, output if copy_output else 0))
        return records, sentinel

    layouts = ((), (1,), (1,2,3), (1,2,1), (3,3,3), (0xffffffff,1,0x80000000), (0,1,0))
    matched = found = copied = throws = 0
    try:
        for ids, requested, copy_output, mark_pattern in itertools.product(
            layouts, (1,2,3,999,0xffffffff,0x80000000), (False,True), range(3)):
            records, sentinel = initialize(ids, mark_pattern, requested, copy_output)
            model = WorkerCompletionQueue(records)
            expected = model.query(requested, copy_output=copy_output)
            oracle._run(0x4a5610, oracle.stop, count=10000)
            if cpu.reg_read(reg.UC_X86_REG_EAX) != int(expected.found):
                raise AssertionError('original completion query return differs')
            if bytes(cpu.mem_read(worker, 0x100)) != state['after']:
                raise AssertionError('original completion queue fields differ')
            actual_output = bytes(cpu.mem_read(output, WORKER_RECORD_SIZE))
            if actual_output != (expected.record if expected.record is not None else sentinel):
                raise AssertionError('original completion output differs')
            remaining = []
            node = struct.unpack('<I', cpu.mem_read(queue + 0x14, 4))[0]
            for _ in range(len(records)+1):
                if not node:
                    break
                payload = struct.unpack('<I', cpu.mem_read(node + 0x10, 4))[0]
                remaining.append(bytes(cpu.mem_read(payload, WORKER_RECORD_SIZE)))
                node = struct.unpack('<I', cpu.mem_read(node + 4, 4))[0]
            if node or tuple(remaining) != model.records:
                raise AssertionError('original completion remaining queue differs')
            selected = state['selected']
            comparisons = len(records) if selected is None else selected+1
            events = [('compare', index) for index in range(comparisons)]
            if selected is not None:
                if copy_output:
                    events += [('size', selected), ('copy', selected)]
                events += [('payload_free', selected), ('node_free', selected)]
            if state['events'] != events:
                raise AssertionError('original completion boundary order differs')
            matched += 1
            found += expected.found
            copied += expected.record is not None
        for ids, copy_output in itertools.product(((), (1,), (1,2,1)), (False,True)):
            _, sentinel = initialize(ids, 1, 0, copy_output)
            oracle._run(0x4a5610, oracle.stop, count=1000)
            if state['events'] != [('throw', 0)] or bytes(cpu.mem_read(worker, 0x100)) != state['before']:
                raise AssertionError('original zero-ID rejection touched queue')
            if bytes(cpu.mem_read(output, WORKER_RECORD_SIZE)) != sentinel:
                raise AssertionError('original zero-ID rejection touched output')
            throws += 1
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return dict(matched_completion_queries=matched, found_queries=found, copied_records=copied,
        zero_id_throw_boundaries=throws, compared_original_comparator=True,
        coverage='original4a5610 and45f440 entry through return; zero-ID path stops at C++ throw boundary',
        substituted_boundaries=['virtual record size/copy/payload-free','node free6992c5','zero-ID throw69b30f'],
        lock_flag=0, live_server_tested=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
