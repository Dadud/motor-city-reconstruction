"""Callable mouse labels and driver setup; shutdown executes actual cleanup."""
import struct
from tools.input_mouse_lifetime_cases import MouseLifetimeOracle,GLOBALS,OBJECT,TABLE,SCRIPTS
EXTRA=(0x8c45fc,0x8c4714,*range(0xb36574,0xb36590,4),0x8c4600,0x8c4604,0x8c4608,0xb36238,0xb36590,0x8c4708,0x8c470c,0x8c4710,0xacadb0)
ENTRIES=(0x6f06c0,0x6efa60,0x6efad0,0x6f0670,0x6f06a0,0x6f06b0)
EDGES=(0,1,0x7fffffff,0x80000000,0xfffffffe,0xffffffff)
def capture(oracle):
    backend=MouseLifetimeOracle(oracle);cpu=oracle.cpu;cases=[]
    with backend.substituted(real_helpers=(0x6f06c0,)):
        for mode,entry in enumerate(ENTRIES):
            for seed in range(96):
                script=SCRIPTS[seed%len(SCRIPTS)];values=[(seed+i*37)&0xffffffff for i in range(17)]
                values[11]=OBJECT if seed&1 else 0;values[12]=OBJECT+512 if seed&2 else 0
                extra=[EDGES[(seed+i)%6] for i in range(len(EXTRA))];extra[-1]=7
                args=[0 if seed%3==0 else 1,8 if seed&4 else 7,((0,1,120,0x7fff,0x8000,0xffff,0xff88,0x1234)[seed%8]<<16)|seed]
                backend.reset([0,0,script,seed],values)
                for a,v in zip(EXTRA,extra):backend.put(a,v)
                if mode==1:oracle.call(entry,(args[0],args[1],0x20a,args[2],0xdeadbeef,0x12345678),cleanup=b'')
                else:oracle.call(entry,(),instruction_limit=10000)
                result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX) if mode in (1,3) else 0
                tables=[(backend.word(OBJECT+i*256)-TABLE-i*512)//256 for i in range(6)]
                cases.append(dict(input=[mode,script,seed,*values,*extra,*args],output=[result,*backend.values(),*(backend.word(a) for a in EXTRA),*tables,len(backend.logs),*(v for row in backend.logs for v in row)]))
    return cases
