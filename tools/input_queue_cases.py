"""Input message queue bodies; only critical-section imports are substituted."""
import struct
from contextlib import contextmanager
BASE,SIZE,RAW,REMAP=0xaca8f0,0x530,0x8c8648,0x71002000
ENTER,LEAVE=0x70008000,0x70008100


def put(image,offset,value): struct.pack_into('<I',image,offset,value&0xffffffff)
def pattern(size,seed): return bytes((seed+k*37)&255 for k in range(size))


def fixture(seed=0,capacity=4,raw_mode=1,mask=0,value=0,remap_kind=0):
    globals=bytearray(pattern(SIZE,seed))
    for offset,word in ((0,raw_mode),(4,0),(0x4a8,capacity),(0x4c0,7),
                        (0x4e0,max(capacity-1,0)),(0x4e4,0xabcdef01),
                        (0x520,0x12345678),(0x528,REMAP if remap_kind else 0)):
        put(globals,offset,word)
    remap=bytes(k if remap_kind==0 else 127-k if remap_kind==1 else k+128
                if remap_kind==2 else 42 if k%2 else 54 for k in range(128))
    return dict(globals=globals,keys=pattern(256,seed^0x55),remap=remap,mask=mask,value=value)


def words(f): return [f['mask'],f['value'],*f['globals'],*f['keys'],*f['remap']]


class QueueOracle:
    def __init__(self,oracle): self.oracle=oracle
    def word(self,offset): return struct.unpack('<I',self.oracle.cpu.mem_read(BASE+offset,4))[0]
    def put(self,offset,value): self.oracle.cpu.mem_write(BASE+offset,struct.pack('<I',value&0xffffffff))
    def reset(self,f):
        self.oracle.cpu.mem_write(BASE,bytes(f['globals']))
        self.oracle.cpu.mem_write(RAW,f['keys']);self.oracle.cpu.mem_write(REMAP,f['remap'])
        self.mask,self.value=f['mask'],f['value'];self.logs=[]
    def observe(self,cpu,address,size,user):
        if address not in (ENTER,LEAVE): return
        entering=address==ENTER
        identity=struct.unpack('<I',cpu.mem_read(cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)+4,4))[0]
        self.logs.append([int(entering),identity,*list(cpu.mem_read(BASE,SIZE)),*list(cpu.mem_read(RAW,256))])
        mask,value=self.mask,self.value
        if entering:
            if mask&1: self.put(0x4e0,value);self.put(4,(value+1)&3)
            if mask&2: self.put(0x4a8,2)
            if mask&4: self.put(0x4e4,value^0x55aa)
            if mask&8: self.put(0x520,value^0x11223344)
        else:
            if mask&16: self.put(0x4e0,value);self.put(0x4e4,value+128)
            if mask&32:
                self.put(0,self.word(0)^1)
                cpu.mem_write(RAW+(value&127),b'\0')
    def output(self):
        result=[*list(self.oracle.cpu.mem_read(BASE,SIZE)),*list(self.oracle.cpu.mem_read(RAW,256)),
                *list(self.oracle.cpu.mem_read(REMAP,128)),len(self.logs)]
        for log in self.logs: result.extend(log)
        return result
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu
        saved={address:bytes(cpu.mem_read(address,4)) for address in (0x83b270,0x83b274)}
        for iat,stub in ((0x83b270,ENTER),(0x83b274,LEAVE)):
            cpu.mem_write(stub,b'\xc2\x04\x00');cpu.mem_write(iat,struct.pack('<I',stub))
        hook=cpu.hook_add(UC_HOOK_CODE,self.observe,begin=ENTER,end=LEAVE)
        try: yield
        finally:
            cpu.hook_del(hook)
            for address,data in saved.items(): cpu.mem_write(address,data)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()


def down_fixtures():
    k=0
    scripts=((0,0),(1,3),(2,0),(4,0x1234),(8,2),(16,3),(32,0),(63,1))
    for mode in (0,1,0x80000000):
        for cap in (1,2,4):
            for repeat in sorted({0,1,cap,65535}):
                for message,key in ((0x100,0x70),(0x104,0x41),(0x102,0x70)):
                    for mask,value in scripts:
                        f=fixture(k*11,cap,mode,mask,value,k%4)
                        scan=(0,1,42,54,127)[k%5]
                        bits=repeat|(scan<<16)|((k%2)<<24)|0x80000000
                        yield (1,7,message,key,bits),f;k+=1
    for mode in (0,1):
        for cap in (0,32):
            for repeat in (0,1,65535):
                yield (1,7,0x100,0x7b,repeat|(42<<16)),fixture(7,cap,mode)
    for enabled,window in ((0,7),(1,8)):
        yield (enabled,window,0x100,0x70,65535),fixture(11,0x80000000,1,63,1)
    for mode in (0,1):
        for tail in (0xffffffff,0xfffffffe,0x40000000,62,0x40000020):
            f=fixture(13,4,mode);put(f['globals'],0x4e0,tail)
            yield (1,7,0x100,0x70,1|(1<<24)),f


def capture(oracle,name,entry):
    result=[]
    if name=='input_key_translate':
        for message in (0,0x100,0x104,0x101,0x102,0xffffffff):
            for key in (*range(256),0x80000000,0xffffffff):
                oracle.call(entry,(message,key))
                result.append(dict(input=[message,key],output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)]))
        return result
    observer=QueueOracle(oracle)
    with observer.substituted():
        if name=='input_queue_resize':
            for seed in (0,0xa5):
                for requested in (0,1,2,31,32,33,0x7fffffff,0x80000000,0xffffffff):
                    f=fixture(seed);observer.reset(f);oracle.call(entry,(requested,))
                    result.append(dict(input=[requested,*words(f)],output=observer.output()))
        elif name=='input_character':
            fixtures=list(down_fixtures())
            base_count=len(fixtures)
            for tail in (46,0x4000002e,0xfffffef7):
                for character in (0x1234,0x7fff):
                    f=fixture(13,4,1);put(f['globals'],0x4e0,tail)
                    fixtures.append(((1,7,0x102,character,1|(42<<16)|(1<<24)),f))
            characters=(0,1,0xff,0x100,0x7fff,0xffff,0x1234abcd)
            for i,(args,f) in enumerate(fixtures):
                character=characters[i%len(characters)] if i<base_count else args[3]
                if struct.unpack_from('<I',f['globals'],0x4e0)[0]==0x40000020:character=0x1234
                actual=(*args[:3],character,args[4])
                observer.reset(f);oracle.call(entry,(*actual,0xdeadbeef),cleanup=b'')
                result.append(dict(input=[*actual,*words(f)],output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()]))
        elif name=='input_key_down':
            for args,f in down_fixtures():
                observer.reset(f)
                oracle.call(entry,(*args,0xdeadbeef),cleanup=b'')
                result.append(dict(input=[*args,*words(f)],output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()]))
        else: raise ValueError(name)
    return result


def lifecycle_cases(oracle):
    """Complete calls sharing queue, raw keys, and query latch state."""
    result=[]
    from tools.input_translation_cases import TranslationOracle
    from tools.input_device_state_cases import StateOracle
    observer=QueueOracle(oracle)
    translation=TranslationOracle(oracle)
    acquisition=StateOracle(oracle)
    for mode in (0,1):
        for remap_kind in (0,1):
            f=fixture(17,4,mode,remap_kind=remap_kind)
            code=42 if remap_kind==0 else 85
            bits=(42<<16)|(1<<24)
            # op: 0 down, 1 query, 2 release, 3 resize. Five args per step.
            steps=[(0,1,7,0x100,0x70,bits|3),
                   (1,code,1,0,0,0),(1,code,1,0,0,0),
                   (0,1,7,0x100,0x7b,bits|4),
                   (2,1,7,0,0,bits),(1,code,1,0,0,0),
                   (3,2,0,0,0,0),(0,1,7,0x100,0x70,bits|5),
                   (1,code,0,0,0,0),(0,0,7,0x100,0x70,bits|1),
                   (0,1,8,0x100,0x70,bits|1),
                   (2,1,7,0,0,bits),(1,code,1,0,0,0)]
            latches=pattern(512,0x55)
            config=[17,0,0,128,0,0,0,73,65,1,1]
            translation.reset(config)
            profile=mode*2+remap_kind
            state_config=[6,1,73,15,0,0,0,0,0,0,0,0]
            if profile==1:state_config[8]=1 # final read failure -> zeroed payload
            if profile==2:state_config[8]=0x8007000c # successful reacquisition/retry
            if profile==3:state_config[4]=0x80004005 # polling failure, successful read
            acquisition.reset_state(state_config)
            observer.reset(f);oracle.cpu.mem_write(0x9e1be8,latches)
            output=[]
            # Continue from the producer/query path into actual consumers.
            steps.extend([(3,8,0,0,0,0),
                          (0,1,7,0x100,0x41,1|(58<<16)),
                          (0,1,7,0x100,0x41,1|(17<<16)),
                          (4,1,7,0x102,0x8000,1),
                          (5,0,0,0,0,0),(5,0,0,0,0,0),
                          (6,0,0,0,0,0),(5,0,0,0,0,0),
                          (6,0,0,0,0,0),(6,0,0,0,0,0),
                          (0,1,7,0x100,0x41,1|(58<<16)),
                          (6,0,0,0,0,0),(6,0,0,0,0,0)])
            with observer.substituted(),acquisition.state_substituted():
                for op,a,b,c,d,e in steps:
                    if op==0: oracle.call(0x584450,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                    elif op==1: oracle.call(0x4acdc0,(a,b))
                    elif op==2: oracle.call(0x584610,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                    elif op==3: oracle.call(0x584ca0,(a,))
                    elif op==4: oracle.call(0x584370,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                    elif op==5: oracle.call(0x583160,())
                    else: oracle.call(0x5830c0,())
                    output.extend([0 if op==3 else oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),
                                   *observer.output(),*list(oracle.cpu.mem_read(0x9e1be8,512)),*translation.output(),*acquisition.state_output()])
            result.append(dict(input=[*config,*state_config,*words(f),*latches,len(steps),
                                      *(word for step in steps for word in step)],output=output))
    return dict(cases=result,scope='Connected down/character/resize/query/release/peek/pop complete calls sharing queue, keys, latches, caps and translation state; actual state accessor/poll/read/retry/clear path; only critical-section imports and platform virtual methods substituted (information/diagnostic branches unused).')
