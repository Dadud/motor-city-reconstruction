"""Original raw-scan translation with synthetic layout/state and explicit bridges."""
import struct
from contextlib import contextmanager
TABLES,DEVICE,PROVIDER,EXIT=0x8c8748,0x71004000,0x6f03c0,0x69c189
MODIFIERS=(0x3c,0xbc,0x21,0xa1,0x2e,0x3a)


def configurations():
    masks=(0,1,2,4,8,16,32,21,20,48,3,12)
    for i,mask in enumerate(masks):
        for scan in range(256):
            yield [scan,(0,1,128,0xffffffff)[scan%4],mask,(1,128,255)[(scan+i)%3],
                   (0,1,0xffffffff)[(scan+i)%3],scan&1,0,(i*17+scan)&255,256,1,
                   int(scan in (0,1,0x3a,255))]
    for mask,caps in ((0,0),(16,1),(0,1),(4,0),(1,0)):
        for value in (0,1,127,128,143,144,255):
            yield [17,0xffffffff,mask,255,caps,0,0,7,value,1,1]
    for script in (1,2,4,8,15):
        for scan in (1,0x3a,17):
            for mask in (4,20,5):
                yield [scan,1,mask,128,0xffffffff,1,script,script*17,256,
                       0 if scan==0x3a else 1,1]


def images(config):
    scan,_,mask,value,_,_,_,seed,forced,_,_=config
    device=bytearray((i*37+seed)&255 for i in range(260))
    for bit,offset in enumerate(MODIFIERS):device[offset]=value if mask&(1<<bit) else 0
    tables=bytearray((i*29+seed)&255 for i in range(620))
    if forced<256:
        for plane in range(5):tables[plane*91+scan]=forced
    return device,tables


class TranslationOracle:
    def __init__(self,oracle,on_get=None):
        self.oracle=oracle;self.on_get=on_get
    def word(self,address):return struct.unpack('<I',self.oracle.cpu.mem_read(address,4))[0]
    def put(self,address,value):self.oracle.cpu.mem_write(address,struct.pack('<I',value&0xffffffff))
    def reset(self,config):
        self.config=config;device,tables=images(config);cpu=self.oracle.cpu
        cpu.mem_write(DEVICE,bytes(device));cpu.mem_write(TABLES,bytes(tables))
        self.put(0x8c8644,config[4]);self.put(0x8c8640,config[5])
        self.logs=[];self.exited=False;self.get_calls=0
    def observe(self,cpu,address,size,user):
        oracle=self.oracle
        argument=self.word(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4)
        self.logs.append([0 if address==PROVIDER else 1,argument,self.word(0x8c8644),self.word(0x8c8640)])
        if address==PROVIDER:
            mask=self.config[6];self.get_calls+=1
            if mask&1:self.put(0x8c8644,self.word(0x8c8644)^1)
            if mask&2:self.put(0x8c8640,self.word(0x8c8640)^1)
            if mask&4:cpu.mem_write(DEVICE+0x3c,b'\x01')
            if mask&8:
                for plane in range(5):cpu.mem_write(TABLES+plane*91+self.config[0],bytes([255-plane]))
            if self.on_get:self.on_get(self)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,DEVICE if self.config[9] else 0)
        else:
            self.exited=True
            # The selected original exit helper calls ExitProcess(code); stop
            # at that explicit boundary, without executing process cleanup.
            cpu.reg_write(oracle.reg.UC_X86_REG_EIP,oracle.stop);cpu.emu_stop()
    def output(self,snapshot=True):
        result=[self.word(0x8c8644),self.word(0x8c8640),len(self.logs),*(v for row in self.logs for v in row)]
        if snapshot:result.extend([*self.oracle.cpu.mem_read(DEVICE,260),*self.oracle.cpu.mem_read(TABLES,620)])
        return result
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved=bytes(cpu.mem_read(PROVIDER,1));cpu.mem_write(PROVIDER,b'\xc3')
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in (PROVIDER,EXIT)]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            cpu.mem_write(PROVIDER,saved)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()


def capture(oracle):
    observer=TranslationOracle(oracle);result=[]
    with observer.substituted():
        for config in configurations():
            observer.reset(config);oracle.call(0x6f05b0,(config[0],config[1]))
            output=[int(observer.exited),0 if observer.exited else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                    *observer.output(config[10])]
            result.append(dict(input=config,output=output))
    return result
