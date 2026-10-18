"""Full original startup control flow with explicit returning subsystem boundaries."""
import struct
from contextlib import contextmanager
from tools.input_queue_cases import QueueOracle,fixture,words,put
GLOBALS=(0x8c4718,0xb2bba4,0xb2bba8,0x8c45f8,0xb35fc4,0x8c4690,0xb31fe0,0xb31fec,0xb2c138,0x8c4618,0x8c461c,0x8c4620,0x8c4628,0x8c462c,0x89bdd8)
DIAG0,DIAG1=0x7000e900,0x7000ea00
EMPTY,NAME=0x71005000,0x71005010
HELPERS={0x6bedf0:0,0x6bda50:0,0x699284:1,0x6be4f0:1,0x6eed30:0,0x6bd2e0:1,0x6bdd10:0,0x6f3860:0,0x6bf9b0:3,0x6d0f20:0,0x6d0820:1,0x6d0cd0:5,0x6c1c80:0,0x6ef890:0,0x6bfc80:0,0x6f0200:0,0x6f09f0:0,0x6f0360:2,0x6e24f0:2,0x6e2510:3,0x6e8d40:0,0x6f2de0:7,0x6cb710:1,0x6cb610:6,DIAG0:1,DIAG1:1}
CONNECTED=(0x6f0200,0x6f09f0,0x6f0360)
class StartupOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,address):return struct.unpack('<I',self.oracle.cpu.mem_read(address,4))[0]
    def put(self,address,value):self.oracle.cpu.mem_write(address,struct.pack('<I',value&0xffffffff))
    def values(self):return [self.word(a) for a in GLOBALS]
    def reset(self,config,values):
        self.config=config;self.logs=[];self.env_calls=0
        for a,v in zip(GLOBALS,values):self.put(a,v)
        self.oracle.cpu.mem_write(EMPTY,b'\0');self.oracle.cpu.mem_write(NAME,b'x\0')
    def observe(self,cpu,address,size,user):
        count=HELPERS[address];esp=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        args=list(struct.unpack('<'+str(count)+'I',cpu.mem_read(esp+4,count*4))) if count else []
        values=self.values();self.logs.append([address,count,*args,*([0]*(7-count)),*values,self.word(0xacae00),self.word(0xacae04)])
        script,recommend,loader,graphics,ready,seed=self.config
        result=(0x11110000+(address&65535))&0xffffffff
        if address==0x6bedf0 and script&1:self.put(GLOBALS[0],DIAG1)
        elif address==0x6bda50:self.put(GLOBALS[0],DIAG1 if script&2 else DIAG0)
        elif address==0x6be4f0 and script&4:self.put(GLOBALS[4],0);self.put(GLOBALS[5],0x12340000+seed)
        elif address==0x6f3860 and script&8:self.put(GLOBALS[3],self.word(GLOBALS[3])^1)
        elif address==0x6bf9b0:
            self.env_calls+=1
            if script&16 and self.env_calls%5==1:self.put(GLOBALS[6],EMPTY);self.put(GLOBALS[8],self.word(GLOBALS[8])^1)
        elif address==0x6d0f20:
            result=recommend
            if script&32:self.put(GLOBALS[8],self.word(GLOBALS[8])^1);self.put(GLOBALS[6],NAME)
        elif address==0x6d0820:
            result=loader
            if script&64:self.put(GLOBALS[9],0x1000001);self.put(GLOBALS[10],0x80000001)
        elif address==0x6d0cd0:
            result=graphics;self.put(GLOBALS[3],ready)
            if script&256:self.put(GLOBALS[7],0xabcdef01);self.put(GLOBALS[10],self.word(GLOBALS[10])^0xffffffff)
        elif address in (DIAG0,DIAG1) and script&128:
            self.put(GLOBALS[1],0x11223344);self.put(GLOBALS[2],0x55667788);self.put(GLOBALS[3],self.word(GLOBALS[3])^1);self.put(GLOBALS[0],DIAG1 if address==DIAG0 else DIAG0);self.put(GLOBALS[9],self.word(GLOBALS[9])+1)
        elif address==0x6e8d40 and script&512:self.put(GLOBALS[9],0x1000001+seed);self.put(GLOBALS[10],0x7fffffff-seed)
        elif address==0x6cb710 and script&1024:self.put(GLOBALS[9],0x80000000+seed);self.put(GLOBALS[10],0x1000001+seed)
        elif address==0x6f0200 and script&2048:self.put(0xaca8f0,7);self.put(0xacae04,0xabcdef02)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
        if address==0x6ef890 and getattr(self,'numlock_temporary',None) is not None:
            cpu.reg_write(self.oracle.reg.UC_X86_REG_ECX,self.numlock_temporary)
    def output(self):return [*self.values(),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self,connected=False,incoming_temporary=0,real_numlock=False,real_helpers=()):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;addresses=[a for a in HELPERS if (not connected or a not in CONNECTED) and (not real_numlock or a!=0x6bfc80) and a not in real_helpers]
        self.numlock_temporary=incoming_temporary if real_numlock else None
        saved={a:bytes(cpu.mem_read(a,6 if connected and a==0x6bfc80 else 1)) for a in addresses if a not in (DIAG0,DIAG1)}
        for a in addresses:cpu.mem_write(a,b'\xc3')
        if connected and not real_numlock:cpu.mem_write(0x6bfc80,b'\xb9'+struct.pack('<I',incoming_temporary)+b'\xc3')
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in addresses]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            for a,data in saved.items():cpu.mem_write(a,data)
            self.numlock_temporary=None
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()

def configurations():
    k=0
    for ready in (0,1):
        for diagnostic in (0,DIAG0):
            for auxiliary in (0,1):
                for name in (0,EMPTY,NAME):
                    for external in (0,1):
                        for loader,graphics,after in ((0,0,0),(1,1,1),(0xffffffff,0x80000000,0)):
                            for script in (0,1,2,4,8,16,32,64,128,256,512,1024,2048,4095):
                                seed=k&255
                                config=[script,(0,EMPTY,NAME)[k%3],loader,graphics,after,seed]
                                dimensions=(0,640,0xffffffff,0x80000000,0x1000001,0x7fffffff)
                                values=[diagnostic,0x1234,0x5678,ready,auxiliary,0x7777,name,0xa5,external,dimensions[k%6],dimensions[(k+1)%6],32,1,2,0xabcdef01]
                                yield 0,config,values,fixture(seed,4,1),[0,0];k+=1
    for flag in (0,1,0x80000000,0xffffffff):
        for callback in (0,0x6bfc60,0xffffffff):
            yield 1,[0,0,1,1,1,17],[0x12345678]*15,fixture(17,4,1),[flag,callback]

def capture(oracle):
    startup=StartupOracle(oracle);queue=QueueOracle(oracle);cases=[]
    with startup.substituted():
        for mode,config,values,f,args in configurations():
            startup.reset(config,values);queue.reset(f)
            oracle.call(0x6bfa10 if mode==0 else 0x584c80,() if mode==0 else args,instruction_limit=100000)
            cases.append(dict(input=[mode,*config,*values,*words(f),*args],output=[*queue.output(),*startup.output()]))
    return cases


def lifecycle_cases(oracle,with_toggle=False):
    from contextlib import nullcontext
    from tools.startup_toggle_cases import ToggleOracle
    from tools.input_device_lifetime_cases import LifetimeOracle,make
    from tools.input_keyboard_layout_cases import LayoutOracle,tables,OFFSET,TABLES,REMAP_ID
    from tools.cleanup_registry_cases import RegistryOracle,FIRST,THIRD,BASE,REGISTER,RUN
    startup=StartupOracle(oracle);device=LifetimeOracle(oracle);layout=LayoutOracle(oracle);registry=RegistryOracle(oracle);cases=[]
    profiles=((0,0,0,[7,0xd01,0,73],False),(128,4,7,[6,0,1,73],False),(512,0,511,[7,0xd04,4,41],False),(0,0,0,[7,0xd05,2,73],True))
    steps=[(0,0,0,0,0,0),(1,1,7,0x100,0x70,1|(17<<16)),(2,1,7,0,0,17<<16),
           (3,0,0,0,0,0),(0,0,0,0,0,0),(1,1,7,0x100,0x70,2|(17<<16)),
           (4,42,1,0,0,0),(5,0x6f0350,0,0,0,0),(3,0,0,0,0,0),
           (6,1,0,0,0,0),(0,0,0,0,0,0),(3,0,0,0,0,0)]
    profiles=[(*p,t) for p in profiles for t in (((0,0,0),(1,0,0x71001400),(0xffff,3,0x800000ff),(1,7,0xffffffff)) if with_toggle else (None,))]
    for startup_script,profile,device_script,layout_config,full,toggle_profile in profiles:
        config,values,f=make(4,0,0,profile,device_script,73);put(f['globals'],4,0);put(f['globals'],0x4e0,0);put(f['globals'],0x528,0);f['keys']=bytes(256)
        toggle_config=toggle_profile[:2] if toggle_profile else None
        if toggle_profile:config[3]=toggle_profile[2]
        startup_config=[startup_script,0,0 if startup_script==128 else 1,0 if startup_script==128 else 1,0 if startup_script==128 else 1,73]
        startup_values=[0,0x1234,0x5678,1 if full or startup_script==512 else 0,1,0x7777,0,0xa5,0,640,480,32,1,2,0]
        data=bytearray(tables(73));data[OFFSET+17]=42;data[OFFSET+42]=54
        slots=[FIRST]*64 if full else [0]*64
        if not full:slots[63]=THIRD
        registry_config=[1,0,0,*slots];latches=bytes(512)
        toggle=ToggleOracle(oracle) if with_toggle else None
        with device.substituted(real_registry=True),device.queue.substituted(),layout.substituted(),registry.substituted(),startup.substituted(connected=True,incoming_temporary=config[3],real_numlock=with_toggle), (toggle.substituted() if toggle else nullcontext()):
            device.reset(config,values,f);startup.reset(startup_config,startup_values);layout.reset(layout_config);registry.reset(registry_config)
            oracle.cpu.mem_write(TABLES,bytes(data));device.put(0x8c8924,values[4]);oracle.cpu.mem_write(0x9e1be8,latches)
            if toggle:toggle.reset(toggle_config)
            output=[]
            for op,a,b,c,d,e in steps:
                device.temporary=0;result=0
                if op==0:oracle.call(0x6bfa10,(),instruction_limit=100000)
                elif op==1:oracle.call(0x584450,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                elif op==2:oracle.call(0x584610,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                elif op==3:oracle.call(RUN,(),instruction_limit=100000)
                elif op==4:oracle.call(0x4acdc0,(a,b))
                elif op==5:oracle.call(REGISTER,(a,))
                elif op==6:startup.put(GLOBALS[3],a)
                if op in (1,2,4):result=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                output.extend([result,*startup.output(),*device.output(),*layout.output(),*registry.output(),*oracle.cpu.mem_read(0x9e1be8,512)])
                if toggle:output.extend(toggle.output())
            cases.append(dict(input=[*startup_config,*startup_values,*config,*values,*words(f),*layout_config,*data,*registry_config,*latches,*(toggle_config or ()),len(steps),*(v for step in steps for v in step)],output=output))
    if with_toggle:
        return dict(cases=cases,scope='Persistent full startup with actual Num Lock wrapper/setter, device initialization/setter, keyboard layout, policy and cleanup bodies. Key API bridges define state, import-target mutation and ECX clobbers; the preceding mouse boundary defines a word whose low byte becomes scan 0x45 through the actual toggle local/POP ECX before device initialization. Renderer/mouse/runtime and OS adapters remain synthetic. Void returns normalized.')
    return dict(cases=cases,scope='Persistent full startup body with actual device initialization/setter, keyboard layout, policy setter, cleanup registration/run and device shutdown, plus down/release/query. Renderer/mouse/runtime and device/type/synchronization/other callback boundaries remain explicit. The preceding synthetic helper supplies a defined incoming temporary word for device initialization; its real body is not claimed. Void returns normalized.')
