"""Original callback/fallback selection with synthetic no-argument helpers."""
import struct
from contextlib import contextmanager
CALLBACK,ENABLED=0x8c8924,0xacae24
PROBE,READ=0x7b0e17,0x7b0cd6
FIRST,SECOND=0x7000e000,0x7000e100
VALUES=(0,1,0x7f,0x80,0xff,0x100,0x12345678,0xffffffff)
def configurations():
    seed=0
    for probe in (0,1,0x80000000,0xffffffff):
        for read in VALUES:
            for script in (0,1,2,4,8,15):
                yield [0,FIRST,1,probe,read,0xdeadbeef,script,seed];seed+=1
    for callback in (0,FIRST,SECOND):
        for enabled in (0,1,0x80000000,0xffffffff):
            for probe in (0,1,0x80000000,0xffffffff):
                for result in VALUES:
                    for script in (0,1,2,4,8,15):
                        yield [1,callback,enabled,probe,VALUES[seed%8],result,script,seed];seed+=1
class DispatchOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def reset(self,config):
        self.config=config;self.logs=[];self.put(CALLBACK,config[1]);self.put(ENABLED,config[2])
    def observe(self,cpu,address,size,user):
        kind=0 if address==PROBE else 1 if address==READ else 2
        identity=address if kind==2 else 0
        self.logs.append([kind,identity,self.word(CALLBACK),self.word(ENABLED)])
        script=self.config[6]
        if kind==0:
            if script&1:self.put(CALLBACK,SECOND)
            if script&2:self.put(ENABLED,0)
        elif kind==1:
            if script&4:self.put(CALLBACK,0);self.put(ENABLED,0x80000000)
        elif script&8:
            self.put(CALLBACK,SECOND if identity==FIRST else FIRST);self.put(ENABLED,self.word(ENABLED)^1)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,self.config[3+kind])
    def output(self):
        return [self.word(CALLBACK),self.word(ENABLED),*self.oracle.cpu.mem_read(CALLBACK,4),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved={a:bytes(cpu.mem_read(a,1)) for a in (PROBE,READ)}
        for a in (PROBE,READ,FIRST,SECOND):cpu.mem_write(a,b'\xc3')
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in (PROBE,READ,FIRST,SECOND)]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            for a,data in saved.items():cpu.mem_write(a,data)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
    observer=DispatchOracle(oracle);cases=[]
    with observer.substituted():
        for config in configurations():
            observer.reset(config);oracle.call(0x6f01d0 if config[0]==0 else 0x6f0450,())
            cases.append(dict(input=config,output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()]))
    return cases

def lifecycle_cases(oracle):
    observer=DispatchOracle(oracle);cases=[]
    with observer.substituted():
        for enabled,probe,read,result,script in ((0,0,0xffffffff,0x12345678,3),(0,1,0x12345680,0x12345678,15),(1,0,0x100,0xdeadbeef,8),(1,0xffffffff,0xffffffff,0xdeadbeef,15)):
            config=[1,0,enabled,probe,read,result,script,0];observer.reset(config)
            steps=[(2,FIRST),(0,0),(0,0),(2,SECOND),(0,0),(2,0),(0,0),(1,0),(2,FIRST),(0,0)]
            output=[]
            for op,value in steps:
                oracle.call((0x6f0450,0x6f01d0,0x6f0360)[op],(10,value) if op==2 else ())
                output.extend([oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()])
            cases.append(dict(input=[*config,len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,scope='Persistent actual kind-10 setter, full-return callback dispatch and byte-masked fallback. Returning no-argument platform helpers only are substituted.')
