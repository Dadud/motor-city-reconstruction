"""Mouse lifetime original instructions with explicit synthetic helper/COM boundaries."""
import struct
from contextlib import contextmanager
BASE=0xb361fc
GLOBALS=tuple(BASE+i*4 for i in range(15))+(0x8c4618,0x8c461c)
OBJECT,TABLE,STUB=0x71001000,0x71006000,0x70009000
IFACE,DEVICE,TEMP=OBJECT,OBJECT+0x200,OBJECT+0x400
MODULE,CURSOR,CLIENT=0x7000b400,0x7000b500,0x7000b600
DIRECT={0x6f06c0:0,0x582e40:2,0x748ba0:4,0x6efaf0:2,0x6f0720:4,0x6bf450:1,0x584cf0:0,MODULE:1,CURSOR:1,CLIENT:2}
METHODS={0:12,8:4,0xc:16,0x18:12,0x20:4,0x2c:8}
SCRIPTS=(0,1,2,4,8,16,32,64,128,255)
class MouseLifetimeOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def values(self):return [self.word(a) for a in GLOBALS]
    def reset(self,config,values):
        self.config=config;self.logs=[];self.temporary=0;self.point=0
        for a,v in zip(GLOBALS,values):self.put(a,v)
        for index in range(6):
            self.put(OBJECT+index*256,TABLE+index*512+(config[3]+index)%2*256)
            for table in (0,1):
                for method,cleanup in METHODS.items():
                    stub=STUB+index*1024+table*256+method
                    self.put(TABLE+index*512+table*256+method,stub)
                    self.oracle.cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup))
    def observe(self,cpu,address,size,user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);at=lambda n:self.word(stack+4+n*4)
        profile,script,seed=self.config[1:];code=address;identity=0;table=0xffffffff;slot=0;out=0
        if address==MODULE:code=0x100;args=[at(0)]
        elif address==0x748ba0:code=0x101;args=[at(0),at(1),at(3)];slot=1;out=at(2)
        elif address==CURSOR:code=0x102;args=[];slot=4;out=at(0);self.point=out
        elif address==CLIENT:code=0x103;out=at(1);slot=4;args=[at(0),self.word(out),self.word(out+4)]
        elif address in DIRECT:args=[at(n) for n in range(DIRECT[address])]
        else:
            rel=address-STUB;index=rel//1024;table=rel%1024//256;code=rel%256;identity=at(0)
            if identity!=OBJECT+index*256:raise AssertionError('mouse virtual identity')
            if code==0xc:args=[at(1),at(3)];slot=2;out=at(2);self.temporary=out
            elif code==0:args=[at(1)];slot=3;out=at(2)
            elif code==0x2c:args=[at(1)]
            elif code==0x18:args=[at(1),*(self.word(at(2)+i*4) for i in range(5))]
            else:args=[]
        self.logs.append([code,identity,table,slot,len(args),*args,*([0]*(6-len(args))),*self.values()])
        status=0
        if code==0x6f06c0 and script&1:self.put(GLOBALS[13],9)
        elif code==0x100:
            status=0x400000
            if script&2:self.put(GLOBALS[11],IFACE+256);self.put(GLOBALS[12],DEVICE+256)
        elif code==0x101:self.put(out,IFACE);status=0x80004005 if profile==1 else 0
        elif code==0xc:self.put(out,TEMP);status=0x80004005 if profile==2 else 0
        elif code==0:
            self.put(out,DEVICE);status=0x80004005 if profile==3 else 0
            if script&128:self.put(self.temporary,TEMP+256)
        elif code==0x2c:status=0x80004005 if profile==4 else 0
        elif code==0x18:status=0x80004005 if profile==5 else 0
        elif code==0x20:
            if script&4:self.put(GLOBALS[12],DEVICE+256);self.put(GLOBALS[11],IFACE+256)
        elif code==8:
            if script&8:self.put(GLOBALS[12],DEVICE+256);self.put(GLOBALS[11],IFACE+256)
        elif code==0x6efaf0:
            if script&16:self.put(GLOBALS[11],IFACE);self.put(GLOBALS[15],0x80000000+seed);self.put(GLOBALS[16],0x1000001+seed)
        elif code==0x6bf450:
            if script&32:self.put(GLOBALS[13],0);self.put(GLOBALS[14],0xdeadbeef)
        elif code==0x102:
            self.put(out,0x80000000+seed);self.put(out+4,0xffffffff-seed);status=int(profile!=7)
        elif code==0x103:
            self.put(out,self.word(out)+17);self.put(out+4,self.word(out+4)+31);status=int(profile!=6)
        elif code==0x584cf0:
            status=0xabcdef00+seed
            if script&64:self.put(GLOBALS[13],7)
        if table!=0xffffffff and script&1:self.put(identity,TABLE+index*512+(1-table)*256)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,status)
    @contextmanager
    def substituted(self,real_helpers=()):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;addresses=[a for a in DIRECT if a not in real_helpers];saved={a:bytes(cpu.mem_read(a,3)) for a in addresses if a not in (MODULE,CURSOR,CLIENT)}
        iats=(0x83b264,0x83b3d8,0x83b3dc);saved_iats=[self.word(a) for a in iats]
        for a in addresses:cpu.mem_write(a,b'\xc2'+struct.pack('<H',DIRECT[a]*4) if a in (MODULE,CURSOR,CLIENT,0x748ba0,0x582e40) else b'\xc3')
        for a,v in zip(iats,(MODULE,CURSOR,CLIENT)):self.put(a,v)
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in addresses]
        hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=STUB,end=STUB+0x1800-1))
        try:
            yield
        finally:
            for h in hooks:cpu.hook_del(h)
            for a,data in saved.items():cpu.mem_write(a,data)
            for a,v in zip(iats,saved_iats):self.put(a,v)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    def capture(self):
        cpu=self.oracle.cpu;cases=[]
        with self.substituted():
            seed=0
            for mode in (0,1,2):
                for flags in (range(16) if mode==0 else range(4) if mode==1 else range(8)):
                    for profile in (range(8) if mode==0 else (0,)):
                        for script in SCRIPTS:
                            config=[mode,profile,script,seed&255];v=[(seed+i*37)&0xffffffff for i in range(17)]
                            v[11]=IFACE if flags&1 else 0;v[12]=DEVICE if flags&2 else 0;v[13]=1 if flags&4 else 0;v[14]=1 if flags&8 else 0
                            args=[(0,1,0xffffffff,0x80000000,0x1000001,0x7fffffff)[(seed+i)%6] for i in range(6)]
                            self.reset(config,v);self.put(self.oracle.frame-0x1024,TEMP)
                            try:self.oracle.call((0x6ef890,0x6efa90,0x6effd0)[mode],args if mode==2 else (),instruction_limit=10000)
                            except Exception as error:raise RuntimeError((config,v,hex(cpu.reg_read(self.oracle.reg.UC_X86_REG_EIP)),self.logs[-2:])) from error
                            result=self.oracle.cpu.reg_read(self.oracle.reg.UC_X86_REG_EAX) if mode==0 else 0
                            tables=[(self.word(OBJECT+i*256)-TABLE-i*512)//256 for i in range(6)]
                            cases.append(dict(input=[*config,*v,*args],output=[result,*self.values(),*tables,len(self.logs),*(x for row in self.logs for x in row)]));seed+=1
        return cases
def capture(oracle):return MouseLifetimeOracle(oracle).capture()
