"""Original 0x52c550 dispatch with an explicit field-copy callback substitute."""
import argparse
import itertools
import json
import struct
from client.mechanical_parts import expand_mechanical_parts
from tools.native_oracle import DynoOracle


def cases():
    for paired,attachment,skip in itertools.product((0,1,-1),(0,1,3,5,10,11,12),(False,True)):
        slots=[]
        for index in range(3):
            image=bytearray(1596)
            struct.pack_into('<I',image,0,101 if index==1 else 10001)
            struct.pack_into('<i',image,0x10,paired if index else 0)
            struct.pack_into('<I',image,0x1e3,0 if skip and index==1 else index+100)
            struct.pack_into('<i',image,0x61c,attachment)
            slots.append(bytes(image))
        yield tuple(slots)


def verify(executable):
    import unicorn
    o=DynoOracle(executable);cpu=o.cpu;count=0;calls=[]
    source=o.inputs;target=o.inputs+0x6000;vehicle_index=o.inputs+0x5000
    def transfer(uc,address,size,user):
        stack=uc.reg_read(o.reg.UC_X86_REG_ESP)
        resume,destination,slot,attachment=struct.unpack('<IIIi',uc.mem_read(stack,16))
        calls.append(((slot-source)//1596,attachment,destination))
        # Deliberately use an inert transfer body: only the original selector,
        # call order, allocation stride, links and vehicle-index output are under
        # comparison. Numeric field transfer has its own original execution test.
        uc.reg_write(o.reg.UC_X86_REG_EIP,resume)
        uc.reg_write(o.reg.UC_X86_REG_ESP,stack+4)
    hook=cpu.hook_add(unicorn.UC_HOOK_CODE,transfer,begin=0x52c2e0,end=0x52c2e0)
    try:
        for slots in cases():
            o._reset();calls.clear()
            cpu.mem_write(source,b''.join(slots));cpu.mem_write(target,bytes(0x8000))
            cpu.mem_write(vehicle_index,bytes(4))
            stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<IIIII',o.stop,target,source,len(slots),vehicle_index))
            o._run(0x52c550,o.stop,count=10000)
            expected=expand_mechanical_parts(slots)
            wanted=[(part.source_index,part.attachment,target+i*0x984) for i,part in enumerate(expected)]
            if calls!=wanted:raise AssertionError((count,calls,wanted))
            for index in range(len(expected)):
                pointer=struct.unpack('<I',cpu.mem_read(target+index*0x984,4))[0]
                expected_pointer=0 if index==len(expected)-1 else target+(index+1)*0x984
                if pointer!=expected_pointer:raise AssertionError(('link',count,index,pointer,expected_pointer))
            actual_index=struct.unpack('<i',cpu.mem_read(vehicle_index,4))[0]
            if actual_index!=(-1 if struct.unpack_from('<I',slots[1],0x1e3)[0]==0 else 1):
                raise AssertionError(('vehicle index',count,actual_index))
            count+=1
    finally:cpu.hook_del(hook)
    return dict(cases=count,maximum_absolute_error=0,
        scope='complete 0x52c550 selector/order/stride/links/source vehicle index; 0x52c2e0 replaced by inert callback; zero-emission original underflow path excluded')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
