"""Original default callback and action router over one overlapping byte image."""
import struct
from contextlib import contextmanager
from tools.input_callback_dispatch_cases import DispatchOracle,CALLBACK,ENABLED,FIRST,SECOND
from tools.input_queue_cases import QueueOracle,fixture,words,put
from tools.input_consumer_cases import event
from tools.input_translation_cases import TranslationOracle
BASE,SIZE,LOW,HIGH=0xb36594,1024,0x104,0x204
ACTION0,ACTION1=0x7000e200,0x7000e300
DEFAULT=0x6f0580

def map_offset(code):
    signed=code if code<0x80000000 else code-0x100000000
    if signed<256:return LOW+signed
    if signed<65536:return HIGH+(code>>8)
    return None

def image(code,index,present):
    data=bytearray(SIZE);offset=map_offset(code)
    if offset is not None:
        if not 0<=offset<SIZE:raise ValueError('action fixture outside mapped image')
        data[offset]=index
    if present:struct.pack_into('<I',data,index*4,ACTION0 if index&1 else ACTION1)
    # Validate any alias-induced target before original invocation; no output
    # is predicted here. The table/map bytes are deliberately not separated.
    if offset is not None and data[offset]:
        target=struct.unpack_from('<I',data,data[offset]*4)[0]
        if target not in (0,ACTION0,ACTION1):return None
    return bytes(data)

def route_fixtures():
    codes=(0,1,17,127,255,256,0x17f,0x8000,0xffff,0x10000,0x7fffffff,0xfffffffc,0xffffffff,0xfffffefc,0xfffffefd,0xfffffeff)
    for code in codes:
        for index in (0,1,2,64,65,128,255):
            for present in (0,1):
                data=image(code,index,present)
                if data is not None:
                    for script in (0,1,2,4,8,15):yield code,script,data
    for code in (*range(256),*(i<<8 for i in range(1,256))):
        index=(1,2,65,128,255)[code%5]
        data=image(code,index,code&1)
        if data is None:data=image(code,1,code&1)
        yield code,code&15,data
class ActionOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def reset(self,script,data):self.script=script;self.logs=[];self.oracle.cpu.mem_write(BASE,data)
    def observe(self,cpu,address,size,user):
        self.logs.append([address,*cpu.mem_read(BASE,SIZE),self.word(CALLBACK),self.word(ENABLED)])
        if self.script&1:cpu.mem_write(BASE+LOW+17,b'\0');cpu.mem_write(BASE+LOW+65,b'\0')
        if self.script&2:self.put(BASE+4,0)
        if self.script&4:cpu.mem_write(BASE+HIGH+128,b'\xff');self.put(BASE+255*4,ACTION1)
        if self.script&8:self.put(CALLBACK,0);self.put(ENABLED,0)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,0xdeadbeef)
    def output(self):
        return [*self.oracle.cpu.mem_read(BASE,SIZE),self.word(CALLBACK),self.word(ENABLED),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        for a in (ACTION0,ACTION1):self.oracle.cpu.mem_write(a,b'\xc3')
        hooks=[self.oracle.cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in (ACTION0,ACTION1)]
        try:yield
        finally:
            for hook in hooks:self.oracle.cpu.hook_del(hook)

def default_fixtures():
    seed=0
    for enabled in (0,1,0x80000000):
        for kind in range(6):
            for index in (0,1,65,128,255):
                for script in (0,15):
                    f=fixture(seed,4,1);put(f['globals'],4,0);put(f['globals'],0x4e0,0 if kind==0 else 1)
                    character=(0,65,0x8000,0xffff,0,0)[kind]
                    scan=58 if kind==5 else 17;event(f,0,scan,character)
                    t=[17,0,0,128,0,0,0,73,65,1,1]
                    if kind==5:t[8]=0
                    # The selected low word is known only for fixture setup;
                    # the actual return and image changes come from execution.
                    code=character if character else (0 if kind in (0,5) else 65)
                    d=[1,DEFAULT,enabled,seed&1,0x12345680,0xabcdef01,0,seed]
                    data=image(code,index,seed&1)
                    if data is not None:yield script,d,t,f,data
                    seed+=1

def capture(oracle):
    action=ActionOracle(oracle);dispatch=DispatchOracle(oracle);translation=TranslationOracle(oracle);queue=QueueOracle(oracle);cases=[]
    with action.substituted(),dispatch.substituted(),translation.substituted(),queue.substituted():
        seen=set()
        for code,script,data in route_fixtures():
            key=(code,script,data)
            if key in seen:continue
            seen.add(key)
            dispatch.reset([1,DEFAULT,1,0,0,0,0,0]);action.reset(script,data)
            oracle.call(0x6f0e80,(code,))
            cases.append(dict(input=[0,code,script,*data],output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*action.output()]))
        for script,d,t,f,data in default_fixtures():
            translation.reset(t);dispatch.reset(d);queue.reset(f);action.reset(script,data)
            oracle.call(DEFAULT,(),instruction_limit=100000)
            cases.append(dict(input=[1,script,*d,*t,*words(f),*data],output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*action.output(),*dispatch.output(),*queue.output(),*translation.output()]))
    return cases

def lifecycle_cases(oracle):
    action=ActionOracle(oracle);dispatch=DispatchOracle(oracle);translation=TranslationOracle(oracle);queue=QueueOracle(oracle);cases=[]
    with action.substituted(),dispatch.substituted(),translation.substituted(),queue.substituted():
        for profile in range(4):
            f=fixture(73,4,1);put(f['globals'],4,0);put(f['globals'],0x4e0,0)
            d=[1,DEFAULT,0 if profile==3 else 1,1,0x12345680,0xabcdef01,15 if profile==3 else 0,73]
            t=[17,0,0,128,0,0,0,73,65,1,1];data=image(65,65,1)
            script=(0,7,8,15)[profile]
            translation.reset(t);dispatch.reset(d);queue.reset(f);action.reset(script,data)
            steps=[(0,1,7,0x102,65,1),(1,0,0,0,0,0),(1,0,0,0,0,0),
                   (0,1,7,0x102,0x8000,1),(1,0,0,0,0,0),
                   (2,1,7,0x100,0x41,1|(17<<16)),(1,0,0,0,0,0),
                   (3,0,0,0,0,0),(4,0x8000,0,0,0,0),(1,0,0,0,0,0)]
            output=[]
            for op,a,b,c,e,g in steps:
                entry=(0x584370,0x6f0450,0x584450,DEFAULT,0x6f0e80)[op]
                args=(a,b,c,e,g,0xdeadbeef) if op in (0,2) else ((a,) if op==4 else ())
                oracle.call(entry,args,cleanup=b'' if op in (0,2) else None,instruction_limit=100000)
                output.extend([oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*action.output(),*dispatch.output(),*queue.output(),*translation.output()])
            cases.append(dict(input=[script,*d,*t,*words(f),*data,len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,scope='Persistent actual producers, dispatcher, shipped default queue callback, pop/translation and overlapping action router; returning action/provider/fallback bridges only.')
