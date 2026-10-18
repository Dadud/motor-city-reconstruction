"""Persistent original mouse subsystem, actual registration/dispatch/cleanup children."""
import struct
from tools.input_mouse_lifetime_cases import MouseLifetimeOracle,GLOBALS,OBJECT,TABLE,STUB,METHODS
from tools.input_mouse_callbacks_cases import EXTRA
FIELDS=GLOBALS+EXTRA+(0x8c8914,0x8c8918,0x8c891c,0x8c4718,0xb2bba4,0xb2bba8)
QUERY,CTOR,CONTEXT,DTOR,GATE,DIAG=0x6be930,0x7b54a0,0x6cf1b0,0x7b54d0,0x7000f100,0x7000f200
BINDINGS=((0x83b270,0x70007000,4),(0x83b274,0x70007100,4),(0x83b45c,0x70007200,8),(0x83b384,0x70007300,8),(0x83b434,0x70007400,4))
STEPS=((0,0,0,0),(1,7,5,0),(1,3,0xffffffff,0),(1,7,4,0),(1,4,90,0),(2,400,300,0),(4,0xff880000,7,0),(5,0,0,0),(6,0,0,0),(7,0,0,0),(8,0,0,0),(0,0,0,0),(4,120<<16,7,0),(8,0,0,0),(9,0,0,0),(8,0,0,0),(0,0,0,0),(3,0x7fffffff,0x80000000,0))
class RuntimeOracle(MouseLifetimeOracle):
    def event(self,code,args=(),identity=0,table=0xffffffff,slot=0):self.events.append([code,identity,table,slot,len(args),*args,*([0]*(6-len(args)))])
    def reset(self,config,values):
        super().reset(config,values);self.events=[];self.cooperative=0;self.queries=0
        for i in range(6):
            for t in range(2):
                for method,cleanup in ((0x1c,4),(0x34,12)):
                    a=STUB+i*1024+t*256+method;self.put(TABLE+i*512+t*256+method,a);self.oracle.cpu.mem_write(a,b'\xc2'+struct.pack('<H',cleanup))
    def observe(self,cpu,address,size,user):
        super().observe(cpu,address,size,user)
        row=list(self.logs[-1][:11])
        if STUB<=address<STUB+0x1800 and (address-STUB)%256==0x34:
            esp=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);row[4]=2;row[5]=self.word(esp+8);row[6]=self.word(esp+12)
            cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,0x80004005 if self.config[1]==6 and self.cooperative%2==0 else 0);self.cooperative+=1
        self.events.append(row)
    def api(self,cpu,address,size,user):
        esp=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);at=lambda i:self.word(esp+4+i*4)
        match=next(((iat,cleanup) for iat,stub,cleanup in BINDINGS if stub==address),None)
        if match:
            code=match[0]
            if code==0x83b45c:
                point=at(1);args=[at(0),self.word(point),self.word(point+4)];self.event(code,args)
                self.put(point,args[1]+100);self.put(point+4,args[2]+200);result=int(self.config[1]!=7)
            else:self.event(code,[at(i) for i in range(match[1]//4)]);result=0
        else:
            code=0x8c4938 if address==GATE else address;args=[at(0)] if address in (QUERY,GATE,DIAG) else []
            self.event(code,args);result=(self.config[3]+self.queries)%2 if address==QUERY else 0
            if address==QUERY:self.queries+=1
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
    def output(self,result):
        return [result,*(self.word(a) for a in FIELDS),*self.oracle.cpu.mem_read(0xaca8f0,0x530),*(self.word(0xb2bbe8+i*4) for i in range(64)),*[(self.word(OBJECT+i*256)-TABLE-i*512)//256 for i in range(6)],len(self.events),*(v for row in self.events for v in row)]
def lifecycle_cases(oracle):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu;b=RuntimeOracle(oracle);cases=[]
    saved={a:bytes(cpu.mem_read(a,3)) for a in (QUERY,CTOR,CONTEXT,DTOR)}
    pointers=[iat for iat,_,_ in BINDINGS]+[0x8c4938];pointer_values=[b.word(a) for a in pointers]
    for iat,stub,cleanup in BINDINGS:b.put(iat,stub);cpu.mem_write(stub,b'\xc2'+struct.pack('<H',cleanup))
    for a in (QUERY,CTOR,CONTEXT,DTOR,GATE,DIAG):cpu.mem_write(a,b'\xc3')
    b.put(0x8c4938,GATE)
    hooks=[cpu.hook_add(UC_HOOK_CODE,b.api,begin=a,end=a) for a in (QUERY,CTOR,CONTEXT,DTOR,GATE,DIAG,*[s for _,s,_ in BINDINGS])]
    try:
        with b.substituted(real_helpers=(0x6f06c0,0x582e40,0x6efaf0,0x6f0720,0x6bf450,0x584cf0)):
            for seed,(profile,script) in enumerate(((0,0),(1,0),(3,4),(4,8),(5,1),(6,1),(7,128),(0,12))):
                values=[0]*17;values[15]=640;values[16]=480;b.reset([0,profile,script,seed],values)
                for a in EXTRA:b.put(a,0)
                for a in FIELDS[-6:]:b.put(a,0)
                b.put(0x8c4718,DIAG);b.put(0x89bdd4,1);b.put(0x8c4938,GATE)
                cpu.mem_write(0xaca8f0,bytes(0x530));b.put(0xacadb0,7);b.put(0xacadb4,7);b.put(0xacae14,0x12345678)
                cpu.mem_write(0xb2bbe8,bytes(256));out=[]
                for op,a,c,d in STEPS:
                    result=0
                    if op==0:b.put(oracle.frame-0x1024,OBJECT+0x400);oracle.call(0x6ef890,(),instruction_limit=100000);result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op==1:oracle.call(0x6efaf0,(a,c));result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)&255
                    elif op==2:oracle.call(0x6effd0,(0,0,0,a,c,500),instruction_limit=100000)
                    elif op==3:oracle.call(0x6f07f0,(a,c),instruction_limit=100000)
                    elif op==4:oracle.call(0x583210,(c,0x20a,a,0,0),instruction_limit=100000);result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op==5:oracle.call(0x6f0670);result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op in (6,7):oracle.call(0x6f06a0 if op==6 else 0x6f06b0)
                    elif op==8:oracle.call(0x6bf410,instruction_limit=100000)
                    elif op==9:oracle.call(0x6bf450,(0x6efad0,))
                    out.extend(b.output(result));b.events.clear()
                cases.append(dict(input=[profile,script,seed,len(STEPS),*(v for s in STEPS for v in s)],output=out))
    finally:
        for h in hooks:cpu.hook_del(h)
        for a,v in saved.items():cpu.mem_write(a,v)
        for a,v in zip(pointers,pointer_values):b.put(a,v)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    return dict(cases=cases,scope='Persistent actual mouse initializer, state setter, geometry/update/warp, wheel registration/dispatch, reporting/counters, cleanup registry/shutdown and reinitialization. COM/import/context helpers remain synthetic returning boundaries; POINT query fully writes both words. Compare shared observations and ordered external events at every step.')
