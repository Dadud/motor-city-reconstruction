"""Compare pending and early-return states in owner worker `0x52c790`."""
import argparse
import struct

from client.model_owner import poll_owner_job_result
from tools.native_oracle import DynoOracle
from tools.verify_component_node_list import OWNER_SIZE


def _case(oracle, initial_state, transitions, current_thread, pump_thread):
    import unicorn

    cpu, reg = oracle.cpu, oracle.reg
    base = 0x74000000
    owner = base + 0x1000
    image = bytearray((i * 31 + 7) & 0xff for i in range(OWNER_SIZE))
    struct.pack_into('<I', image, 0x170, base + 0x8000)
    image[0x190] = 0
    cpu.mem_write(owner, bytes(image))
    cpu.mem_write(0xa3810c, struct.pack('<I', pump_thread))
    events=[]
    transitions=iter(transitions)
    observed=[]

    def intercept(uc, address, _size, _user):
        if address == 0x66df20:
            esp=uc.reg_read(reg.UC_X86_REG_ESP)
            ret,_handle,out_ptr,_flags=struct.unpack('<IIII',uc.mem_read(esp,16))
            uc.mem_write(out_ptr,struct.pack('<i',initial_state))
            uc.reg_write(reg.UC_X86_REG_EAX,1)
            uc.reg_write(reg.UC_X86_REG_ESP,esp+4)
            uc.reg_write(reg.UC_X86_REG_EIP,ret)
        elif address == 0x52c7d0:
            uc.reg_write(reg.UC_X86_REG_EAX,current_thread)
            uc.reg_write(reg.UC_X86_REG_EIP,address+6)
            events.append(('thread',current_thread))
        elif address == 0x6bd810:
            esp=uc.reg_read(reg.UC_X86_REG_ESP)
            ret,arg=struct.unpack('<II',uc.mem_read(esp,8))
            events.append(('pump_call',arg))
            uc.reg_write(reg.UC_X86_REG_ESP,esp+8)
            uc.reg_write(reg.UC_X86_REG_EIP,ret)
        elif address == 0x52c7fa:
            frame=uc.reg_read(reg.UC_X86_REG_EBP)
            state=next(transitions)
            uc.mem_write(frame-4,struct.pack('<i',state))
            observed.append(state)
            events.append(('sleep',10))
            uc.reg_write(reg.UC_X86_REG_EIP,address+2)

    hook=cpu.hook_add(unicorn.UC_HOOK_CODE,intercept)
    try:
        oracle.call(0x52c790,this_pointer=owner,instruction_limit=100_000)
    finally:
        cpu.hook_del(hook)

    expected_state=observed[-1] if observed else initial_state
    reads=iter(observed)
    expected=poll_owner_job_result(
        initial_state,lambda:next(reads),current_thread,pump_thread,
        lambda value:None,lambda _ms:None)
    actual_return=cpu.reg_read(reg.UC_X86_REG_EAX)
    if actual_return != 0:
        raise AssertionError(('early-return status',initial_state,actual_return))
    actual_owner=bytes(cpu.mem_read(owner,OWNER_SIZE))
    if actual_owner != bytes(image):
        changed=[i for i,(a,b) in enumerate(zip(actual_owner,image)) if a!=b]
        raise AssertionError(('owner mutated before ready state',initial_state,changed[:16]))
    waits=len(observed)
    pumps=sum(event[0]=='pump_call' for event in events)
    if waits!=expected.waits or pumps!=expected.pumps:
        raise AssertionError(('poll trace',initial_state,events,expected))
    return {'initial_state':initial_state,'final_state':expected_state,
            'waits':waits,'pump_calls':pumps,'return':actual_return,
            'owner_unchanged':True}


def verify(executable):
    oracle=DynoOracle(executable)
    oracle.cpu.mem_map(0x74000000,0x40000)
    cases=(
        _case(oracle,0,(),0x1111,0x1111),
        _case(oracle,98,(),0x1111,0x2222),
        _case(oracle,2,(2,0),0x1111,0x1111),
        _case(oracle,2,(2,98),0x1111,0x2222),
    )
    return {'cases':len(cases),'observations':cases,'maximum_byte_error':0,
            'original_entry':'0x52c790',
            'scope':'initial terminal states and pending-to-terminal polling with matched/mismatched pump thread; completion query and OS thread/sleep services stubbed'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    args=parser.parse_args()
    print(verify(args.executable))


if __name__=='__main__':
    main()
