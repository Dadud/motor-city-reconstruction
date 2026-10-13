"""Check original list lookup with a controlled, already-fetched data result."""
import argparse
import json
import struct
from client.mcots_data_records import MCOTSList145Record, first_145_identifier_for_value
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    result, data = oracle.inputs, oracle.inputs+0x1000
    calls = []
    def fetched_result(cpu, address, size, unused):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        return_address, mode, wait = struct.unpack('<3I',bytes(cpu.mem_read(stack,12)))
        if (mode,wait) != (0,1):
            raise ValueError('unexpected original refresh arguments')
        calls.append(address)
        cpu.reg_write(reg.UC_X86_REG_EAX,result)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+12)
        cpu.reg_write(reg.UC_X86_REG_EIP,return_address)
    hook = cpu.hook_add(UC_HOOK_CODE,fetched_result,begin=0x4ba850,end=0x4ba850)
    cases = (((),7), (((11,3),(42,7)),7), (((0,7),(99,7)),7), (((11,3),),7))
    try:
        for values, query in cases:
            oracle._reset()
            records = []
            for identifier, value in values:
                raw = struct.pack('<II',identifier,value)+bytes(561)
                records.append(MCOTSList145Record(raw))
            cpu.mem_write(result,struct.pack('<3I',0,len(records),data))
            if records:
                cpu.mem_write(data,b''.join(record.raw for record in records))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<2I',oracle.stop,query))
            oracle._run(0x5e89a0,oracle.stop,count=1000)
            if cpu.reg_read(reg.UC_X86_REG_EAX) != first_145_identifier_for_value(records,query):
                raise ValueError('original list lookup differs')
    finally:
        cpu.hook_del(hook)
    if len(calls) != len(cases):
        raise ValueError('unexpected controlled refresh count')
    return {'matched_lookup_cases':len(cases),
            'scope':'original lookup with refresh result substituted; no socket or allocation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
