"""Original diagnostic bodies; environment/parser remain synthetic boundaries."""
import struct
from contextlib import contextmanager
ENTRIES=(0x6bedf0,0x6bf220,0x6bef70,0x6bf1e0,0x6bef20)
BASE=0x8c4730
class DiagnosticOracle:
    def __init__(self,oracle): self.oracle=oracle
    def word(self,address): return struct.unpack('<I',self.oracle.cpu.mem_read(address,4))[0]
    def put(self,address,value): self.oracle.cpu.mem_write(address,struct.pack('<I',value&0xffffffff))
    def reset(self,script,values,initialized=0):
        self.script=script;self.logs=[]
        for i,value in enumerate(values): self.put(BASE+i*4,value)
        self.put(0xb2bbe0,initialized)
    def observe(self,cpu,address,size,user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);argument=self.word(stack+4)
        if address==0x699e80:
            channel=bytes(cpu.mem_read(argument,13)).startswith(b'PRINT_CHANNEL')
            self.logs.append(1 if channel else 2)
            cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,0x71001000 if self.script else 0)
        else:
            channel=address==0x6bf2b0;self.logs.extend((3 if channel else 4,argument))
            target=BASE+(1 if channel else 136)*4;self.put(target,self.word(target)^0xabcde123)
    def output(self):
        return [self.word(0xb2bbe0),*(self.word(BASE+i*4) for i in range(160)),len(self.logs),*self.logs]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved={a:bytes(cpu.mem_read(a,1)) for a in (0x699e80,0x6bf2b0,0x6befa0)};hooks=[]
        try:
            for address in saved:
                cpu.mem_write(address,b'\xc3');hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=address,end=address))
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
            yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            for address,data in saved.items():cpu.mem_write(address,data)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
    observer=DiagnosticOracle(oracle);cases=[]
    with observer.substituted():
        for mode,entry in enumerate(ENTRIES):
            selectors=(0,) if mode==0 else ((0,1,2,3,15,16,31,63) if mode in (1,3) else range(8))
            for selector in selectors:
                for enabled in (0,1,2,3,0x80000000,0xffffffff):
                    for ready in (0,1,0xffffffff):
                        for script in (0,1):
                            seed=len(cases);values=[(seed*7919+i*0x1020305)&0xffffffff for i in range(160)]
                            if seed&1: values[(0x8c494c+selector*12-BASE)//4 if mode in (2,4) else 135]=0
                            observer.reset(script,values,ready)
                            oracle.call(entry,() if mode==0 else (selector,enabled),instruction_limit=10000)
                            cases.append(dict(input=[mode,selector,enabled,script,ready,*values],output=observer.output()))
    return cases
