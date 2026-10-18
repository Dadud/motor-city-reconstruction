"""Synthetic virtual records observed through the original information enumerator."""
import struct
from contextlib import contextmanager
OBJECT,TABLE,OUTPUT,STUB,AXES=0x71001000,0x71006000,0x71003000,0x7000a000,0x8c89b0
METHODS=(0x3c,0xc,0x38)
def configurations():
    k=0
    for device_type in (0,2,4,0x102,0xffffffff):
        for counts in ((0,0,0),(1,1,1),(8,32,4),(9,33,5),(0xffffffff,0xffffffff,0xffffffff)):
            for pattern in range(4):
                for script in (0,1,2,4,8,16,32,63):
                    yield [device_type,(0,1,256,257,0xffffffff)[k%5],*counts,0,0,k&255,(0,1,258,259,260)[k%5],(260,259,258,1,0)[k%5],pattern,script];k+=1
    for instance_status in (1,0x80004005,0xffffffff):
        yield [2,257,8,32,4,instance_status,0,7,260,260,0,63]
    for caps_status in (1,0x80004005,0xffffffff):
        yield [4,257,8,32,4,0,caps_status,7,1,259,0,63]
class InformationOracle:
    def __init__(self,oracle,output=OUTPUT):self.oracle=oracle;self.output_address=output
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def reset(self,config):
        self.config=config;self.logs=[];self.objects=0;self.caps=0
        self.put(OBJECT,TABLE+(config[7]&1)*0x100)
        self.oracle.cpu.mem_write(self.output_address,bytes((config[7]+i*37)&255 for i in range(540)))
        for i in range(8):self.put(AXES+i*4,0x100+i*0x11)
        for table in (0,1):
            for method in METHODS:
                stub=STUB+table*0x100+method;self.put(TABLE+table*0x100+method,stub)
                self.oracle.cpu.mem_write(stub,b'\xc2'+struct.pack('<H',16 if method==0x38 else 8))
    def observe(self,cpu,address,size,user):
        table=(address-STUB)//0x100;method=(address-STUB)%0x100
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        if self.word(stack+4)!=OBJECT:raise AssertionError('information device identity')
        record=self.word(stack+8)
        selector=self.word(stack+12) if method==0x38 else 0
        flags=self.word(stack+16) if method==0x38 else 0
        self.logs.append([method,table,OBJECT,selector,flags,self.word(record),*cpu.mem_read(self.output_address,540),*(self.word(AXES+i*4) for i in range(8))])
        c=self.config;script=c[11]
        if method==0x3c:
            data=bytearray((c[7]+i*23)&255 for i in range(580))
            struct.pack_into('<I',data,0,580);struct.pack_into('<I',data,36,c[0])
            for offset,length in ((40,c[8]),(300,c[9])):
                for i in range(260):data[offset+i]=(c[7]+i*7)%255+1
                if length<260:data[offset+length]=0
            cpu.mem_write(record,bytes(data));status=c[5]
        elif method==0xc:
            self.caps=record
            data=bytearray((c[7]+i*23)&255 for i in range(44))
            for offset,value in ((0,44),(4,c[1]),(12,c[2]),(16,c[3]),(20,c[4])):struct.pack_into('<I',data,offset,value)
            cpu.mem_write(record,bytes(data));status=c[6]
            if script&8:self.put(self.output_address+4,0xa5a5a5a5)
        else:
            self.objects+=1;n=self.objects
            data=bytearray((c[7]+n*11+i*23)&255 for i in range(316))
            struct.pack_into('<I',data,0,316+n if script&32 else 316);cpu.mem_write(record,bytes(data))
            success=(True,False,n%2==0,(selector+c[7]+n)%3==0)[c[10]]
            status=0 if success else 0x80004005
            if script&2:
                value=self.word(self.output_address);self.put(self.output_address,(value&0xffffff00)|(4 if value&255==2 else 2))
            if script&4 and n==1:
                for offset,value in ((16,0),(12,2),(20,1)):self.put(self.caps+offset,value)
            if script&8:self.put(self.output_address+12,self.word(self.output_address+12)^0x80000000)
            if script&16:
                at=AXES+(n&7)*4;self.put(at,self.word(at)^(0xdead0000+n))
        if script&1:self.put(OBJECT,TABLE+(1-table)*0x100)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,status)
    def output(self):
        cpu=self.oracle.cpu
        return [(self.word(OBJECT)-TABLE)//0x100,*cpu.mem_read(self.output_address,540),*(self.word(AXES+i*4) for i in range(8)),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved=bytes(cpu.mem_read(AXES,32))
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=STUB+t*0x100+m,end=STUB+t*0x100+m) for t in (0,1) for m in METHODS]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            cpu.mem_write(AXES,saved)
def capture(oracle):
    observer=InformationOracle(oracle);cases=[]
    with observer.substituted():
        for config in configurations():
            observer.reset(config);oracle.call(0x6f0b20,(OBJECT,OUTPUT),instruction_limit=100000)
            cases.append(dict(input=config,output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()]))
    return cases


def lifecycle_cases(oracle):
    from tools.input_device_state_cases import StateOracle,INFORMATION,DIAG
    from unicorn import UC_HOOK_CODE
    access=StateOracle(oracle);information=InformationOracle(oracle,INFORMATION);cases=[]
    cpu=oracle.cpu;saved=bytes(cpu.mem_read(0x8c4718,4));cpu.mem_write(DIAG,b'\xc3')
    access.put(0x8c4718,DIAG)
    hook=cpu.hook_add(UC_HOOK_CODE,access.state_observe,begin=DIAG,end=DIAG)
    try:
        with access.substituted(),information.substituted():
            for profile in range(4):
                state=[6,1,73,15,0,0,0,0,0,0,0,0]
                if profile==1:state[8]=1
                if profile==2:state[8]=0x8007000c
                if profile==3:state[4]=0x80004005
                config=[2,257,2,3,1,0,0,73,1,260,0,0]
                if profile==1:config[10]=2;config[11]=63
                if profile==2:config[5]=0x80004005
                if profile==3:config[6]=0x80004005
                access.reset_state(state);information.reset(config)
                kinds=[2,6,2,0xffffffff,6,2];output=[]
                for kind in kinds:
                    oracle.call(0x6f03c0,(kind,),instruction_limit=100000)
                    output.extend([cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*access.state_output(),*information.output()])
                cases.append(dict(input=[*state,*config,len(kinds),*kinds],output=output))
    finally:
        cpu.hook_del(hook);cpu.mem_write(0x8c4718,saved)
    return dict(cases=cases,scope='Persistent actual information and keyboard acquisition through state accessor; success, instance/capability failures, callback mutations, diagnostics and repeated access; virtual platform methods only.')
