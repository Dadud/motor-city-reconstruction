"""Original cleanup registration/run with returning synthetic callback boundaries."""
import struct
from contextlib import contextmanager
BASE=0xb2bbe8
FIRST,SECOND,THIRD=0x7000e400,0x7000e500,0x7000e600
REGISTER,RUN=0x6bf450,0x6bf410

def images():
    yield [0]*64
    yield [FIRST]*64
    yield [FIRST if i%2 else SECOND for i in range(64)]
    for position in (0,1,30,31,32,62,63):
        a=[FIRST]*64;a[position]=0;yield a
        a=[0]*64;a[position]=FIRST;yield a
    yield [THIRD if i%3==0 else 0 for i in range(64)]

def configurations():
    for image in images():
        for identity in (0,FIRST,SECOND,THIRD,0xffffffff):
            yield [0,0,identity,*image]
        for script in (0,1,2,4,8,16,32,64,127,128,255):
            yield [1,script,0,*image]

class RegistryOracle:
    def __init__(self,oracle):self.oracle=oracle
    def slots(self):return list(struct.unpack('<64I',self.oracle.cpu.mem_read(BASE,256)))
    def put(self,index,value):self.oracle.cpu.mem_write(BASE+index*4,struct.pack('<I',value))
    def reset(self,config):
        self.script=config[1];self.logs=[];self.depth=0
        self.oracle.cpu.mem_write(BASE,struct.pack('<64I',*config[3:67]))
        # Callback machine stubs call the actual original registration body.
        for address in (FIRST,SECOND,THIRD):
            code=bytearray()
            for mask,identity in ((8,FIRST),(16,THIRD),(128,0)):
                if self.script&mask:
                    code+=b'\x68'+struct.pack('<I',identity)
                    next_ip=address+len(code)+5
                    code+=b'\xe8'+struct.pack('<i',REGISTER-next_ip)+b'\x83\xc4\x04'
            code+=b'\xb8'+struct.pack('<I',0xdeadbeef if self.script&64 else 0)+b'\xc3'
            self.oracle.cpu.mem_write(address,bytes(code))
        if hasattr(self.oracle.cpu,'ctl_flush_tb'):self.oracle.cpu.ctl_flush_tb()
    def observe(self,cpu,address,size,user):
        self.logs.append([address,self.depth,*self.slots()])
        s=self.script
        if s&1:self.put(0,SECOND)
        if s&2:self.put(63,THIRD)
        if s&4:self.put(31,0)
        if s&32:self.put(1,0)
    def output(self):return [*self.slots(),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu
        for a in (FIRST,SECOND,THIRD):cpu.mem_write(a,b'\xc3')
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in (FIRST,SECOND,THIRD)]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()

def capture(oracle):
    observer=RegistryOracle(oracle);cases=[]
    with observer.substituted():
        for config in configurations():
            observer.reset(config)
            oracle.call(REGISTER if config[0]==0 else RUN,(config[2],) if config[0]==0 else (),instruction_limit=100000)
            cases.append(dict(input=config,output=observer.output()))
    return cases


def lifecycle_cases(oracle):
    from tools.input_device_lifetime_cases import LifetimeOracle,make
    from tools.input_queue_cases import words
    device=LifetimeOracle(oracle);registry=RegistryOracle(oracle);cases=[]
    steps=[(0,0),(0,0),(1,0),(0,0),(2,0x6f0350),(0,0),
           (1,0),(1,0),(2,FIRST),(2,0x6f0350),(0,0),(1,0)]
    with device.substituted(real_registry=True),registry.substituted():
        for profile,device_script,registry_script,full in ((0,0,0,False),(4,7,0,False),(0,511,3,False),(0,0,127,True)):
            config,state,queue=make(4,0,0,profile,device_script,73)
            device.reset(config,state,queue)
            slots=[FIRST]*64 if full else [0]*64
            if not full:slots[31]=FIRST;slots[63]=THIRD
            registry_config=[1,registry_script,0,*slots];registry.reset(registry_config)
            output=[]
            for mode,value in steps:
                device.temporary=0
                oracle.cpu.reg_write(oracle.reg.UC_X86_REG_ECX,config[3])
                oracle.call((0x6f0200,RUN,REGISTER)[mode],(value,) if mode==2 else (),instruction_limit=100000)
                result=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX) if mode==0 else 0
                output.extend([result,*device.output(),*registry.output()])
            cases.append(dict(input=[*config,*state,*words(queue),*registry_config,len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,scope='Persistent actual device initialization, cleanup registration, reverse registry run and device shutdown. Registration remains original, including nested registration from returning synthetic callbacks. Only platform/other callback boundaries substituted; void returns normalized.')
