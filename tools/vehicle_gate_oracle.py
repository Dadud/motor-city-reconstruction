"""Complete 0x55cfc0 comparison with only the virtual operation substituted."""
import argparse
import itertools
import json
import struct
from client.vehicle_gate import vehicle_gate_result
from tools.native_oracle import DynoOracle


def cases():
    values = (-0x80000000, -1, 0, 1, 0x7fffffff)
    yield from itertools.product((False, True), values, values)


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable)
    cpu,reg=o.cpu,o.reg
    owner,interface,vtable,callee=o.inputs,o.inputs+0x3000,o.inputs+0x3100,o.stub+0x100
    state={}

    def observe(_cpu,address,_size,_user):
        if address!=callee:return
        state['calls']+=1
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        ret,operation,argument=struct.unpack('<III',cpu.mem_read(stack,12))
        if operation!=5 or argument!=owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=interface:
            raise AssertionError('unexpected virtual operation arguments/receiver')
        cpu.reg_write(reg.UC_X86_REG_EAX,state['result'] & 0xffffffff)
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+12)
        cpu.reg_write(reg.UC_X86_REG_EIP,ret)

    cpu.hook_add(UC_HOOK_CODE,observe)
    count=0
    for present,current,result in cases():
        o._reset()
        image=bytes([0xa5])*0x1d00
        cpu.mem_write(owner,image)
        cpu.mem_write(interface,struct.pack('<I',vtable))
        cpu.mem_write(vtable+0x10,struct.pack('<I',callee))
        # A null owner must not dereference this intentionally null interface.
        cpu.mem_write(0xa65bd0,struct.pack('<I',interface if present else 0))
        cpu.mem_write(0xaa456c,struct.pack('<i',current))
        state.update(result=result,calls=0)
        stack=o.frame-0x1000
        cpu.mem_write(stack,struct.pack('<II',o.stop,owner if present else 0))
        cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x55cfc0,o.stop,count=2000)
        actual=cpu.reg_read(reg.UC_X86_REG_EAX)&0xff
        expected=vehicle_gate_result(present,current,result)
        if actual!=int(expected) or state['calls']!=int(present):
            raise AssertionError((present,current,result,actual,state['calls']))
        if cpu.mem_read(owner,len(image))!=image or struct.unpack('<i',cpu.mem_read(0xaa456c,4))[0]!=current:
            raise AssertionError('predicate changed owner or counter')
        count+=1
    return {'cases':count,'scope':'complete 0x55cfc0; virtual operation 5 substituted; signed boundary observations; owner and counter unchanged'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
