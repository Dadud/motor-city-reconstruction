"""Original mouse state setter with explicit window/position/COM boundaries."""
import struct
GLOBALS=tuple(0xb361fc+i*4 for i in range(15))+(0x8c8914,0x8c8918,0x8c891c,0x8c4718,0xb2bba4,0xb2bba8)
OBJECT,TABLE,STUB=0x71001000,0x71006000,0x70009000
DIAG=0x7000b000
METHODS={0x1c:4,0x20:4,0x34:12}
DIRECT={0x584cf0:0,0x6f07f0:2,DIAG:1}
PROFILES=((0,0,0),(0x80004005,0,0),(0x80004005,1,0x80004005),(0x80004005,2,0),(1,0,1),(0xffffffff,0,0x8007001e))
class MouseStateOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def values(self):return [self.word(a) for a in GLOBALS]
    def reset(self,config,values):
        self.config=config;self.logs=[];self.cooperative=0
        for a,v in zip(GLOBALS,values):self.put(a,v)
        for index in range(2):
            self.put(OBJECT+index*256,TABLE+index*512+(config[2]+index)%2*256)
            for table in range(2):
                for method,cleanup in METHODS.items():
                    stub=STUB+index*1024+table*256+method
                    self.put(TABLE+index*512+table*256+method,stub)
                    self.oracle.cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup))
    def mutate_device(self):
        identity=self.word(GLOBALS[12]);index=(identity-OBJECT)//256
        table=(self.word(identity)-TABLE-index*512)//256
        self.put(identity,TABLE+index*512+(1-table)*256)
        self.put(GLOBALS[12],OBJECT+(1-index)*256)
    def observe(self,cpu,address,size,user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);at=lambda n:self.word(stack+4+n*4)
        profile,script,seed=self.config;target=0;identity=0;code=address
        if address in DIRECT:args=[at(i) for i in range(DIRECT[address])]
        else:
            target=address;code=(address-STUB)%256;identity=at(0)
            args=[at(i) for i in (1,2)] if code==0x34 else []
        self.logs.append([code,target,identity,len(args),*(args+[0]*(2-len(args))),*self.values()])
        result=0
        if code==0x584cf0:
            result=0xabcdef00+seed
            if script&128:
                base=self.word(self.word(GLOBALS[12]));target=self.word(base+0x34)
                self.put(base+0x34,target^0x100)
            if script&1:self.mutate_device()
            if script&32:self.put(GLOBALS[15],0xf00d);self.put(GLOBALS[4],31);self.put(GLOBALS[5],37)
        elif code==0x20:
            result=PROFILES[profile][1]
            if script&2:self.mutate_device()
        elif code==0x34:
            result=PROFILES[profile][0 if self.cooperative==0 else 2];self.cooperative+=1
            if script&4:self.mutate_device()
        elif code==0x6f07f0:
            if script&8:self.put(GLOBALS[4],0x80000000+seed);self.put(GLOBALS[5],0xffffffff-seed);self.put(GLOBALS[15],0x123)
        elif code==DIAG:
            if script&16:self.put(GLOBALS[19],0xcafe);self.put(GLOBALS[20],0xbeef);self.put(GLOBALS[15],0x333)
        if code in METHODS and script&64:self.put(GLOBALS[11],0)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
    def capture(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved={a:bytes(cpu.mem_read(a,3)) for a in DIRECT if a!=DIAG}
        for a in DIRECT:cpu.mem_write(a,b'\xc3')
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in DIRECT]
        hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=STUB,end=STUB+2047))
        cases=[]
        def one(selector,value,mode,present,profile,script):
            seed=len(cases)&255;config=[profile,script,seed]
            values=[(seed+i*37)&0xffffffff for i in range(len(GLOBALS))]
            values[11]=OBJECT+0x400 if present else 0;values[12]=OBJECT;values[15]=mode;values[18]=DIAG
            self.reset(config,values)
            try:self.oracle.call(0x6efaf0,(selector,value),instruction_limit=10000)
            except Exception as error:raise RuntimeError((config,selector,value,mode,present,hex(cpu.reg_read(self.oracle.reg.UC_X86_REG_EIP)),self.logs[-2:])) from error
            result=cpu.reg_read(self.oracle.reg.UC_X86_REG_EAX)&255
            tables=[(self.word(OBJECT+i*256)-TABLE-i*512)//256 for i in range(2)]
            cases.append(dict(input=[*config,selector,value,*values],output=[result,*self.values(),*tables,len(self.logs),*(v for row in self.logs for v in row)]))
        try:
            for selector in (0,3,4,5,6,8,9,10,0xffffffff):
                for value in (0,1,4,5,0x80000000,0xffffffff):
                    for mode in (0,4,5,0xffffffff):
                        for script in (0,8,16,255):one(selector,value,mode,1,0,script)
            for mode in (0,4,5,0xffffffff):
                for value in (0,1,4,5,0x80000000,0xffffffff):
                    for present in (0,1):
                        for profile in range(len(PROFILES)):
                            for script in (0,1,2,4,8,16,31,255):one(7,value,mode,present,profile,script)
        finally:
            for h in hooks:cpu.hook_del(h)
            for a,data in saved.items():cpu.mem_write(a,data)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        return cases
def capture(oracle):return MouseStateOracle(oracle).capture()
