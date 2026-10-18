"""Original lifetime calls with synthetic interface handles and explicit platform bridges."""
import struct
from contextlib import contextmanager
from tools.input_queue_cases import QueueOracle,fixture,words,put as image_put
GLOBAL=(0xb36564,0xb36568,0xb3656c,0xb36570,0x8c8924,0xb2bba4,0xb2bba8)
OBJECT,TABLE,STUB=0x71001000,0x71006000,0x7000c000
IFACE,DEVICE,TEMP=OBJECT,OBJECT+0x200,OBJECT+0x400
SYNC,REGISTER,MODULE,CREATE,DIAG=0x6bd640,0x6bf450,0x7000b100,0x7000b200,0x7000b300
QUEUE_OFFSETS=(0,4,0x4e0,0x4a8,0x524,0x4c4)
METHODS=(0,8,0xc,0x20,0x2c,0x34)
def make(mode,kind,value,profile,script,seed,interface=0,device=0,initialized=0,registered=0):
    config=[mode,kind,value,TEMP,profile,script,seed]
    state=[interface,device,initialized,registered,0xabcdef01,0x11223344,0x55667788]
    f=fixture(seed,4,1);image_put(f['globals'],0x524,0 if seed&1 else 0x12345678);image_put(f['globals'],0x4c4,0xaabb0000+seed)
    return config,state,f
def fixtures():
    seed=0
    for initialized in (0,1,0xffffffff):
        for interface in (0,IFACE):
            for device in (0,DEVICE):
                for registered in (0,1):
                    for profile in range(9):
                        for script in (0,1,2,4,8,16,32,64,128,511):
                            yield make(4,0,0,profile,script,seed&255,interface,device,initialized,registered);seed+=1
    for mode in (0,1):
        for interface in (0,IFACE):
            for device in (0,DEVICE):
                for initialized in (0,0xffffffff):
                    for script in (0,1,2,3,4,7,256,511):
                        yield make(mode,0,0,0,script,seed&255,interface,device,initialized,seed&1);seed+=1
    for kind in (0,10,1,2,6,0xffffffff):
        for value in (0,1,32,33,0x7fffffff,0x80000000,0xffffffff):
            for script in (0,256):
                yield make(2,kind,value,0,script,seed&255);seed+=1
    for value in (0,1,0x80000000,0xffffffff):
        c,s,f=make(3,0,0,0,0,0);image_put(f['globals'],0x4c4,value);yield c,s,f
class LifetimeOracle:
    def __init__(self,oracle):self.oracle=oracle;self.queue=QueueOracle(oracle)
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def reset(self,config,state,f):
        self.config=config;self.logs=[];self.temporary=0;self.queue.reset(f)
        for address,value in zip(GLOBAL,state):self.put(address,value)
        for index in range(6):
            self.put(OBJECT+index*0x100,TABLE+index*0x200+((config[6]+index)&1)*0x100)
            for table in (0,1):
                for method in METHODS:
                    stub=STUB+index*0x400+table*0x100+method
                    self.put(TABLE+index*0x200+table*0x100+method,stub)
                    cleanup={0:12,8:4,0xc:16,0x20:4,0x2c:8,0x34:12}[method]
                    self.oracle.cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup))
    def observe(self,cpu,address,size,user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);at=lambda n:self.word(stack+4+n*4)
        table=0xffffffff;slot=0;output=0;identity=0
        if address==SYNC:code=0x100;args=[]
        elif address==REGISTER:code=0x103;args=[at(0)]
        elif address==MODULE:code=0x101;args=[at(0)]
        elif address==CREATE:
            code=0x102;args=[at(0),at(1),at(3)];slot=1;output=at(2)
            if output!=GLOBAL[0]:raise AssertionError('create input output')
        elif address==DIAG:code=0x104;args=[at(0)]
        else:
            relative=address-STUB;index=relative//0x400;table=(relative%0x400)//0x100;code=relative%0x100
            identity=at(0)
            if identity!=OBJECT+index*0x100:raise AssertionError('lifetime virtual identity')
            if code==0xc:
                args=[at(1),at(3)];slot=2;output=at(2);self.temporary=output
            elif code==0:args=[at(1)];slot=3;output=at(2)
            elif code==0x2c:args=[at(1)]
            elif code==0x34:args=[at(1),at(2)]
            elif code in (8,0x20):args=[]
            else:raise AssertionError('lifetime method')
        c=self.config;profile,script,seed=c[4:7]
        self.logs.append([code,identity,table,slot,len(args),*args,*([0]*(4-len(args))),self.word(self.temporary) if self.temporary else c[3],*(self.word(a) for a in GLOBAL),*(self.queue.word(o) for o in QUEUE_OFFSETS)])
        status=0
        if code==0x100:
            status=0x12345678
            if script&8:
                self.put(GLOBAL[2],9)
                for offset,value in ((0,7),(4,2),(0x4e0,1),(0x4a8,3)):self.queue.put(offset,value)
        elif code==0x101:
            status=0x400000
            if script&32:self.put(GLOBAL[0],IFACE+0x100);self.put(GLOBAL[1],DEVICE+0x100)
        elif code==0x102:
            self.put(output,0 if profile==6 else IFACE);status=0x80004005 if profile in (1,6) else 0
        elif code==0xc:
            if profile!=7:self.put(output,TEMP)
            status=0x80004005 if profile in (2,7) else 0
        elif code==0:
            if profile!=8:self.put(output,DEVICE)
            status=0x80004005 if profile in (3,8) else 0
            if script&128:self.put(self.temporary,TEMP+0x100)
        elif code==0x2c:
            status=0x80004005 if profile==4 else 0
            if script&64:self.put(GLOBAL[1],DEVICE+0x100);self.queue.put(0x4c4,0xdeadbeef)
        elif code==0x34:status=0x80004005 if profile==5 else 0
        elif code==0x20:
            status=0x80004005
            if script&1:self.put(GLOBAL[1],DEVICE+0x100);self.put(GLOBAL[0],IFACE+0x100)
        elif code==8:
            status=0xdeadbeef
            if script&2:self.put(GLOBAL[1],DEVICE+0x100);self.put(GLOBAL[0],IFACE+0x100)
        elif code==0x103:
            status=0xffffffff
            if script&16:self.put(GLOBAL[2],0x1234);self.put(GLOBAL[3],0x5678)
        elif code==0x104:
            status=0xdeadbeef
            if script&256:self.put(GLOBAL[2],555)
        if table!=0xffffffff and script&4:
            self.put(identity,TABLE+index*0x200+(1-table)*0x100)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,status)
    def output(self):
        tables=[(self.word(OBJECT+i*0x100)-TABLE-i*0x200)//0x100 for i in range(6)]
        return [*(self.word(a) for a in GLOBAL),*self.queue.output(),*tables,len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self,real_registry=False):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu
        saved_code={a:bytes(cpu.mem_read(a,1)) for a in ((SYNC,) if real_registry else (SYNC,REGISTER))}
        saved_iat={a:bytes(cpu.mem_read(a,4)) for a in (0x83b264,0x83b040,0x8c4718)}
        for a in ((SYNC,DIAG) if real_registry else (SYNC,REGISTER,DIAG)):cpu.mem_write(a,b'\xc3')
        cpu.mem_write(MODULE,b'\xc2\x04\x00');cpu.mem_write(CREATE,b'\xc2\x10\x00')
        for a,target in ((0x83b264,MODULE),(0x83b040,CREATE),(0x8c4718,DIAG)):self.put(a,target)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        addresses=([SYNC,MODULE,CREATE,DIAG] if real_registry else [SYNC,REGISTER,MODULE,CREATE,DIAG])+[STUB+i*0x400+t*0x100+m for i in range(6) for t in (0,1) for m in METHODS]
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in addresses]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            for a,data in saved_code.items():cpu.mem_write(a,data)
            for a,data in saved_iat.items():cpu.mem_write(a,data)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
    observer=LifetimeOracle(oracle);cases=[]
    with observer.substituted():
        for config,state,f in fixtures():
            observer.reset(config,state,f);mode,kind,value,temp=config[:4]
            oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ECX,temp)
            entry=(0x6f0310,0x6f0350,0x6f0360,0x584cf0,0x6f0200)[mode]
            oracle.call(entry,(kind,value) if mode==2 else (),instruction_limit=100000)
            result=0 if mode in (0,1) else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            cases.append(dict(input=[*config,*state,*words(f)],output=[result,*observer.output()]))
    return cases


def lifecycle_cases(oracle):
    observer=LifetimeOracle(oracle);cases=[]
    with observer.substituted():
        for profile,script in ((0,0),(0,511),(4,0),(3,511)):
            config,state,f=make(4,0,0,profile,script,73)
            observer.reset(config,state,f)
            steps=[(4,0,0),(4,0,0),(2,10,0x12345678),(2,0,2),
                   (2,6,0),(0,0,0),(0,0,0),(4,0,0),
                   (1,0,0),(1,0,0),(4,0,0),(3,0,0)]
            output=[]
            for mode,kind,value in steps:
                observer.temporary=0
                oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ECX,config[3])
                entry=(0x6f0310,0x6f0350,0x6f0360,0x584cf0,0x6f0200)[mode]
                oracle.call(entry,(kind,value) if mode==2 else (),instruction_limit=100000)
                result=0 if mode in (0,1) else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                output.extend([result,*observer.output()])
            cases.append(dict(input=[*config,*state,*words(f),len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,scope='Persistent actual initialization/cleanup/shutdown/set-state/window calls, success/failure and callback mutation profiles; platform calls only substituted. Void cleanup returns normalized to zero.')
