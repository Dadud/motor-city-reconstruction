"""Compare pre-expansion early returns in stock owner worker `0x52c790`."""
import argparse
import struct

from client.model_owner import admit_stock_owner_job
from tools.native_oracle import DynoOracle
from tools.verify_component_node_list import OWNER_SIZE


def verify(executable):
    import unicorn

    oracle=DynoOracle(executable)
    cpu,reg=oracle.cpu,oracle.reg
    cpu.mem_map(0,0x1000)  # 0x52c6b0's local SEH registration.
    base=0x74000000
    cpu.mem_map(base,0x40000)
    owner,completion,job,source=base+0x1000,base+0x2000,base+0x3000,base+0x4000
    cases=((2,1,False),(1,0,False),(1,1,True))
    observations=[]

    for status,count,allocation_fails in cases:
        owner_image=bytearray((i*29+3)&0xff for i in range(OWNER_SIZE))
        struct.pack_into('<I',owner_image,0x40,0)
        struct.pack_into('<I',owner_image,0x170,base+0x7000)
        struct.pack_into('<I',owner_image,0x174,0)
        struct.pack_into('<I',owner_image,0x178,0)
        struct.pack_into('<I',owner_image,0x19c,0)
        cpu.mem_write(owner,bytes(owner_image))
        completion_image=bytearray(0x20)
        struct.pack_into('<I',completion_image,0x04,status)
        struct.pack_into('<I',completion_image,0x08,job)
        cpu.mem_write(completion,bytes(completion_image))
        job_image=bytearray(0xbc0)
        struct.pack_into('<I',job_image,0x04,count)
        struct.pack_into('<I',job_image,0x08,source)
        cpu.mem_write(job,bytes(job_image))

        allocator_calls=[]
        completion_releases=[]
        def intercept(uc,address,_size,_user):
            if address==0x66df20:
                esp=uc.reg_read(reg.UC_X86_REG_ESP)
                ret,_handle,out_ptr,_flags=struct.unpack('<IIII',uc.mem_read(esp,16))
                uc.mem_write(out_ptr,struct.pack('<I',completion))
                uc.reg_write(reg.UC_X86_REG_EAX,1)
                uc.reg_write(reg.UC_X86_REG_ESP,esp+4)
                uc.reg_write(reg.UC_X86_REG_EIP,ret)
            elif address==0x52c7d0:
                uc.reg_write(reg.UC_X86_REG_EAX,0x1234)
                uc.reg_write(reg.UC_X86_REG_EIP,address+6)
            elif address==0x6ee530:
                esp=uc.reg_read(reg.UC_X86_REG_ESP)
                ret,tag_ptr,size,pool=struct.unpack('<IIII',uc.mem_read(esp,16))
                tag=bytes(uc.mem_read(tag_ptr,32)).split(b'\0',1)[0]
                allocator_calls.append((tag,size,pool))
                uc.reg_write(reg.UC_X86_REG_EAX,0)
                uc.reg_write(reg.UC_X86_REG_ESP,esp+4)
                uc.reg_write(reg.UC_X86_REG_EIP,ret)
            elif address==0x66df80:
                esp=uc.reg_read(reg.UC_X86_REG_ESP)
                ret,arg=struct.unpack('<II',uc.mem_read(esp,8))
                completion_releases.append(arg)
                uc.reg_write(reg.UC_X86_REG_EAX,1)
                uc.reg_write(reg.UC_X86_REG_ESP,esp+4)
                uc.reg_write(reg.UC_X86_REG_EIP,ret)

        hook=cpu.hook_add(unicorn.UC_HOOK_CODE,intercept)
        try:
            oracle.call(0x52c790,this_pointer=owner,instruction_limit=200_000)
        finally:
            cpu.hook_del(hook)

        actual_return=cpu.reg_read(reg.UC_X86_REG_EAX)
        if actual_return!=0:
            raise AssertionError(('return',status,count,actual_return))
        if bytes(cpu.mem_read(owner,OWNER_SIZE))!=bytes(owner_image):
            raise AssertionError(('owner changed',status,count))
        expected_gate=admit_stock_owner_job(status,count,not allocation_fails)
        expected_allocations=[]
        if status==1 and count>0:
            expected_allocations=[(b'PARTS',count*0x1308,
                                   struct.unpack('<I',cpu.mem_read(0xa52be8,4))[0])]
        if allocator_calls!=expected_allocations:
            raise AssertionError(('allocator calls',status,count,allocator_calls,
                                  expected_allocations))
        expected_releases=[completion] if expected_gate.release_completion else []
        if completion_releases!=expected_releases:
            raise AssertionError(('completion cleanup',status,count,completion_releases,
                                  expected_releases))
        observations.append({'completion_status':status,'source_slots':count,
                             'allocation_failed':allocation_fails,
                             'return':actual_return,
                             'completion_released':bool(completion_releases),
                             'owner_unchanged':True})
    return {'cases':len(observations),'observations':observations,
            'maximum_byte_error':0,'original_entry':'0x52c790',
            'scope':'invalid completion status, empty source list and scratch-allocation failure; worker query and allocator/free services stubbed'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args=parser.parse_args()
    print(verify(args.executable))


if __name__=='__main__':
    main()
