"""Observe original cache parameter binding with controlled SQL outcomes."""
import argparse
import json
import struct
from tools.native_oracle import DynoOracle


def verify(executable):
    from unicorn import UC_HOOK_CODE
    oracle = DynoOracle(executable)
    cpu, reg = oracle.cpu, oracle.reg
    context = oracle.inputs
    bindings, executions = {}, []
    outcome = [1,1]
    def boundary(cpu,address,size,unused):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        target = cpu.reg_read(reg.UC_X86_REG_ECX)
        ret = struct.unpack('<I',bytes(cpu.mem_read(stack,4)))[0]
        if address == 0x680230:
            index,value = struct.unpack('<2I',bytes(cpu.mem_read(stack+4,8)))
            bindings.setdefault(target,{})[index] = value
            cleanup = 12
        elif address == 0x680190:
            index = struct.unpack('<I',bytes(cpu.mem_read(stack+4,4)))[0]
            bindings.setdefault(target,{})[index] = None
            cleanup = 8
        else:
            output = struct.unpack('<I',bytes(cpu.mem_read(stack+4,4)))[0]
            executions.append((target,dict(bindings[target])))
            if output:
                cpu.mem_write(output,struct.pack('<I',outcome[1]))
            cleanup = 8
        cpu.reg_write(reg.UC_X86_REG_EAX,outcome[0] if address==0x6803c0 else 1)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+cleanup)
        cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    hooks = [cpu.hook_add(UC_HOOK_CODE,boundary,begin=a,end=a)
             for a in (0x680230,0x680190,0x6803c0)]
    try:
        for status,affected,identifier in ((1,1,42),(1,0,42),(3,0,42),(1,1,0)):
            oracle._reset()
            bindings.clear()
            executions.clear()
            outcome[:] = status,affected
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<10I',oracle.stop,identifier,123,456,0,0,0,0,0,0))
            cpu.reg_write(reg.UC_X86_REG_ECX,context)
            oracle._run(0x6725d0,oracle.stop,count=3000)
            expected = []
            if identifier:
                expected.append((context+0x14,{0:123,1:456,2:None,3:0,4:0,5:0,6:42,7:0,8:0}))
                if status!=1 or not affected:
                    expected.append((context,{0:123,1:42,2:456,3:None,4:0,5:0,6:0,7:0,8:0}))
            if executions != expected:
                raise ValueError('original owned-part cache bindings differ')
    finally:
        for hook in hooks:
            cpu.hook_del(hook)
    return {'matched_cache_update_cases':4,
            'scope':'original binding and fallback flow; SQL boundaries substituted, no database writes'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable),indent=2))
