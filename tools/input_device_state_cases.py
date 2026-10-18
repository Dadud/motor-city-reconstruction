"""Original state accessor with actual device read wrappers and explicit info/diagnostic bridges."""
from contextlib import contextmanager
from tools.input_device_cases import DeviceOracle,OBJECT,STATUSES
KEYBOARD,INFORMATION,ENABLED,DEVICE,FILE,LINE=0xb36460,0xb36240,0xb36564,0xb36568,0xb2bba4,0xb2bba8
INFO,DIAG=0x6f0b20,0x70009500

def configurations():
    # kind,enabled,seed,method mutation mask,poll1,poll2,acquire1,acquire2,read1,read2,info status,global mutation script
    for kind in (0,1,2,3,6,7,0xffffffff):
        for enabled in (0,1,0x80000000):
            for status in STATUSES:
                for script in (0,7):
                    yield [kind,enabled,(kind+status)&255,15,status,0,0,1,status,0,status,script]
    for poll in STATUSES:
        for read in STATUSES:
            for acquire in (0,1,0x8007001e):
                yield [6,1,(poll+read)&255,15,poll,0,acquire,0x80004005,read,1,0,7]
class StateOracle(DeviceOracle):
    def __init__(self,oracle):super().__init__(oracle,KEYBOARD+4,256)
    def reset_state(self,config):
        self.state_config=config
        kind,enabled,seed,mask,p1,p2,a1,a2,r1,r2,info,script=config
        self.reset([2,256,seed,mask,p1,p2,a1,a2,r1,r2])
        self.put(KEYBOARD,0x12345678);self.put(ENABLED,enabled);self.put(DEVICE,OBJECT)
        self.put(FILE,0x11223344);self.put(LINE,0x55667788)
        self.oracle.cpu.mem_write(INFORMATION,bytes((seed+i*19)&255 for i in range(540)))
        self.state_logs=[]
    def mutate(self):
        script=self.state_config[11]
        if script&1:self.put(ENABLED,0)
        if script&2:self.put(DEVICE,OBJECT+0x100)
        if script&4:self.put(FILE,0x1234);self.put(LINE,0x4321)
    def observe(self,cpu,address,size,user):
        super().observe(cpu,address,size,user);self.mutate()
    def state_observe(self,cpu,address,size,user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        if address==INFO:
            identity=self.word(stack+4);destination=self.word(stack+8)
            if destination!=INFORMATION:raise AssertionError('info destination')
            self.state_logs.append([0,identity,destination,self.word(FILE),self.word(LINE)])
            seed=self.state_config[2]
            cpu.mem_write(INFORMATION,bytes((seed+i*17)&255 for i in range(540)))
            result=self.state_config[10]
        else:
            if self.word(stack+4)!=0x84a118:raise AssertionError('diagnostic format')
            self.state_logs.append([1,self.word(stack+8),0,self.word(FILE),self.word(LINE)])
            result=0xdeadbeef
        self.mutate();cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
    def state_output(self):
        cpu=self.oracle.cpu
        return [self.word(ENABLED),self.word(DEVICE),self.word(FILE),self.word(LINE),
                *cpu.mem_read(KEYBOARD,260),*cpu.mem_read(INFORMATION,540),
                *self.output(),len(self.state_logs),*(v for row in self.state_logs for v in row)]
    @contextmanager
    def state_substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved=bytes(cpu.mem_read(INFO,1));iat=bytes(cpu.mem_read(0x8c4718,4))
        cpu.mem_write(INFO,b'\xc3');cpu.mem_write(DIAG,b'\xc3');self.put(0x8c4718,DIAG)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.state_observe,begin=a,end=a) for a in (INFO,DIAG)]
        try:
            with self.substituted():yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            cpu.mem_write(INFO,saved);cpu.mem_write(0x8c4718,iat)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
    observer=StateOracle(oracle);cases=[]
    with observer.state_substituted():
        for config in configurations():
            observer.reset_state(config);oracle.call(0x6f03c0,(config[0],),instruction_limit=10000)
            cases.append(dict(input=config,output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.state_output()]))
    return cases
