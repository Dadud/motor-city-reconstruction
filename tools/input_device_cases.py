"""Original device wrappers with synthetic stdcall virtual methods."""
import struct
from contextlib import contextmanager
OBJECT,TABLE0,TABLE1,BUFFER,STUB=0x71001000,0x71006000,0x71006100,0x71004000,0x70009000
METHODS=(0x64,0x1c,0x24)
STATUSES=(0,1,0x8007000c,0x8007001e,0x80004005,0xffffffff)
def configurations():
    # mode,size,seed,mutation mask,poll1,poll2,acquire1,acquire2,read1,read2
    k=0
    for mode in (0,1,2):
        for first in STATUSES:
            for retry in STATUSES:
                for acquire in STATUSES:
                    for mask in (0,7,8,15):
                        size=(0,1,4,32,64)[k%5]
                        yield [mode,size,k&255,mask,first,retry,acquire,0,first,retry]
                        k+=1
    # Independent poll/read errors, including a second acquisition result.
    for poll in STATUSES:
        for read in STATUSES:
            for a1 in (0,1,0x8007000c):
                for a2 in (0,0x80004005):
                    yield [2,64,k&255,15,poll,0x8007001e,a1,a2,read,0];k+=1
class DeviceOracle:
    def __init__(self,oracle,buffer=BUFFER,length=64):
        self.oracle=oracle;self.buffer=buffer;self.length=length
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def reset(self,config):
        self.config=config;self.logs=[];self.counts=[0,0,0]
        self.put(OBJECT,TABLE0+(config[2]&1)*0x100)
        self.oracle.cpu.mem_write(self.buffer,bytes((config[2]+i*13)&255 for i in range(self.length)))
        for table in (0,1):
            for method in METHODS:
                stub=STUB+table*0x100+method
                self.put(TABLE0+table*0x100+method,stub)
                self.oracle.cpu.mem_write(stub,b'\xc2'+struct.pack('<H',12 if method==0x24 else 4))
    def observe(self,cpu,address,size,user):
        table=(address-STUB)//0x100;method=(address-STUB)%0x100
        if method not in METHODS:raise AssertionError('unexpected method')
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        identity=self.word(stack+4)
        requested=self.word(stack+8) if method==0x24 else 0
        if identity!=OBJECT or (method==0x24 and self.word(stack+12)!=self.buffer):raise AssertionError('device ABI mismatch')
        self.logs.append([method,table,identity,requested,*cpu.mem_read(self.buffer,self.length)])
        index=METHODS.index(method);self.counts[index]+=1
        n=self.counts[index]
        config=self.config
        pair=((4,5),(6,7),(8,9))[index]
        status=config[pair[min(n-1,1)]]
        if method==0x24:
            cpu.mem_write(self.buffer,bytes((config[2]+len(self.logs)*37+i)&255 for i in range(requested)))
        if config[3]&8:
            cpu.mem_write(self.buffer+self.length-1,bytes([cpu.mem_read(self.buffer+self.length-1,1)[0]^len(self.logs)]))
        if config[3]&(1<<index):self.put(OBJECT,TABLE0+(1-table)*0x100)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,status)
    def output(self):
        return [(self.word(OBJECT)-TABLE0)//0x100,*self.oracle.cpu.mem_read(self.buffer,self.length),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        hooks=[self.oracle.cpu.hook_add(UC_HOOK_CODE,self.observe,begin=STUB+t*0x100+m,end=STUB+t*0x100+m) for t in (0,1) for m in METHODS]
        try:yield
        finally:
            for hook in hooks:self.oracle.cpu.hook_del(hook)
def capture(oracle):
    observer=DeviceOracle(oracle);cases=[]
    with observer.substituted():
        for config in configurations():
            observer.reset(config);mode,size=config[:2]
            entry=(0x6f0a70,0x6f0aa0,0x6f0a30)[mode]
            args=(OBJECT,) if mode==0 else ((OBJECT,size,BUFFER) if mode==1 else (OBJECT,BUFFER,size))
            oracle.call(entry,args,instruction_limit=10000)
            cases.append(dict(input=config,output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()]))
    return cases
