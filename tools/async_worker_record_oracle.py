"""Compare original bounded task-ID and worker-result header writes."""
import argparse
import json
import random
import struct

from client.async_worker_record import stamp_operation, store_worker_result
from tools.native_oracle import DynoOracle


def verify(executable):
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    rng = random.Random(0x4a5390)
    stamped = results = rejected = 0
    counters = (0, 1, 0x7fffffff, 0x80000000, 0xfffffffe, 0xffffffff)
    for counter in counters:
        for tracked in (0, 1, 2, 0xffffffff):
            oracle._reset()
            worker, record = oracle.inputs, oracle.inputs + 0x1000
            raw = rng.randbytes(0x80c)
            cpu.mem_write(record, raw)
            cpu.mem_write(worker, bytes(0x100))
            cpu.mem_write(worker + 0x8c, struct.pack('<I', counter))
            cpu.mem_write(oracle.frame + 0xc, struct.pack('<I', tracked))
            cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
            cpu.reg_write(reg.UC_X86_REG_ESI, worker)
            cpu.reg_write(reg.UC_X86_REG_EDI, record)
            cpu.reg_write(reg.UC_X86_REG_EBX, 0)
            oracle._run(0x4a554f, 0x4a5574, count=50)
            expected = stamp_operation(raw, counter=counter, tracked=bool(tracked))
            if bytes(cpu.mem_read(record, len(raw))) != expected.record:
                raise AssertionError('original task-ID write differs')
            if struct.unpack('<I', cpu.mem_read(worker + 0x8c, 4))[0] != expected.counter:
                raise AssertionError('original operation counter differs')
            stamped += 1
    for has_record, manager in ((False, False), (False, True), (True, False)):
        oracle._reset()
        worker, record = oracle.inputs, oracle.inputs + 0x1000
        raw = rng.randbytes(0x80c)
        cpu.mem_write(worker, bytes(0x100))
        cpu.mem_write(worker + 0x8c, struct.pack('<II', 9, worker if manager else 0))
        cpu.mem_write(record, raw)
        cpu.mem_write(0xb36a9c, bytes(4))
        cpu.reg_write(reg.UC_X86_REG_ECX, worker)
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<III', oracle.stop, record if has_record else 0, 1))
        oracle._run(0x4a5390, oracle.stop, count=500)
        if cpu.reg_read(reg.UC_X86_REG_EAX) != 0 or bytes(cpu.mem_read(record, len(raw))) != raw:
            raise AssertionError('original rejected enqueue changed its data/result')
        if struct.unpack('<I', cpu.mem_read(worker + 0x8c, 4))[0] != 9:
            raise AssertionError('original rejected enqueue changed counter')
        rejected += 1
    for operation_id in (0, 1, 0xffffffff):
        for result_bits in (0, 1, 0x7fffffff, 0x80000000, 0xffffffff):
            oracle._reset()
            raw = bytearray(rng.randbytes(0x80c))
            struct.pack_into('<I', raw, 4, operation_id)
            record = oracle.frame - 0x80c
            cpu.mem_write(record, bytes(raw))
            cpu.reg_write(reg.UC_X86_REG_EBP, oracle.frame)
            cpu.reg_write(reg.UC_X86_REG_EAX, result_bits)
            stop = 0x4a55ef if operation_id else 0x4a5603
            oracle._run(0x4a55df, stop, count=50)
            expected, queued = store_worker_result(bytes(raw), result_bits)
            if bytes(cpu.mem_read(record, len(raw))) != expected or queued != bool(operation_id):
                raise AssertionError('original worker result/queue branch differs')
            results += 1
    return {'matched_id_write_cases': stamped, 'matched_rejected_enqueue_cases': rejected,
            'matched_result_write_cases': results,
            'coverage': 'bounded header writes and null/missing-manager returns; queue insertion excluded',
            'live_server_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable), indent=2))
