"""One connected original startup/input graph; explicitly synthetic OS/COM adapter."""
import struct
from contextlib import ExitStack, contextmanager
from tools.startup_initialize_cases import StartupOracle, GLOBALS as STARTUP
from tools.input_mouse_runtime_cases import FIELDS
from tools.input_mouse_callbacks_cases import EXTRA
from tools.input_device_lifetime_cases import GLOBAL as KEYBOARD
from tools.input_keyboard_layout_cases import LayoutOracle, TABLES, tables
from tools.startup_toggle_cases import ToggleOracle
from tools.input_queue_cases import QueueOracle, fixture, put as image_put
from tools.diagnostic_runtime_cases import DiagnosticOracle

# Distinct object/table/stub namespaces: no keyboard/mouse synthetic aliasing.
OBJECTS=(0x71001000,0x71003000)
TABLES=(0x71006000,0x71007000)
STUBS=(0x70009000,0x7000c000)
METHODS={0:12,8:4,0xc:16,0x18:12,0x1c:4,0x20:4,0x2c:8,0x34:12}
APIS={0x7000b400:4,0x748ba0:16,0x7000b200:16,0x7000b500:4,0x7000b600:8,
      0x70007200:8,0x70007300:8,0x70007400:4,0x6bd640:0,
      0x6be930:0,0x7b54a0:0,0x6cf1b0:0,0x7b54d0:0,0x7000f100:0}
IATS={0x83b264:0x7000b400,0x83b040:0x7000b200,0x83b3d8:0x7000b500,
      0x83b3dc:0x7000b600,0x83b45c:0x70007200,0x83b384:0x70007300,
      0x83b434:0x70007400,0x8c4938:0x7000f100}
STEPS=((0,0,0,0,0,0),(1,1,7,0x100,0x70,1|(17<<16)),
       (2,1,7,0,0,17<<16),(4,42,1,0,0,0),(5,0xff880000,7,0,0,0),
       (6,320,240,0,0,0),(7,0,0,0,0,0),(8,0,0,0,0,0),
       (3,0,0,0,0,0),(3,0,0,0,0,0),(0,0,0,0,0,0),
       (1,1,7,0x100,0x70,2|(42<<16)),(2,1,7,0,0,42<<16),
       (9,800,600,0,0,0),(10,0,0,0,0,0),(0,0,0,0,0,0),
       (5,120<<16,7,0,0,0),(3,0,0,0,0,0))

class CombinedOracle:
    def __init__(self, oracle): self.oracle=oracle
    def word(self,a): return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v): self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def observe(self,cpu,a,size,user):
        at=lambda n:self.word(cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)+4+n*4)
        result=0
        domain=next((d for d,s in enumerate(STUBS) if s<=a<s+0x600),None)
        if domain is not None:
            code=(a-STUBS[domain])%256;identity=at(0)
            if identity not in tuple(OBJECTS[domain]+i*256 for i in range(6)):raise AssertionError('combined COM identity')
            self.events.extend((domain,code,identity))
            if code==0xc:self.put(at(2),OBJECTS[domain]+0x400)
            elif code==0:self.put(at(2),OBJECTS[domain]+0x200)
            stage={0xc:2,0:3,0x2c:4,0x18:5,0x34:5}.get(code,0)
            result=0x80004005 if stage and self.profiles[domain]==stage else 0
        elif a in (0x748ba0,0x7000b200):
            domain=int(at(2)==KEYBOARD[0]);self.put(at(2),OBJECTS[domain]);
            self.events.extend((domain,0x101,0));result=0x80004005 if self.profiles[domain]==1 else 0
        elif a==0x7000b400:result=0x400000
        elif a==0x6bd640:result=0x12345678
        elif a==0x7000b500:self.put(at(0),100);self.put(at(0)+4,200);result=1
        elif a==0x7000b600:self.put(at(1),self.word(at(1))+17);self.put(at(1)+4,self.word(at(1)+4)+31);result=1
        elif a==0x70007200:self.put(at(1),self.word(at(1))+100);self.put(at(1)+4,self.word(at(1)+4)+200);result=1
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu
        saved={a:bytes(cpu.mem_read(a,4)) for a in (*IATS, *[a for a in APIS if a<0x70000000])}
        for a,n in APIS.items():cpu.mem_write(a,b'\xc2'+struct.pack('<H',n))
        for a,v in IATS.items():self.put(a,v)
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in APIS]
        for d in range(2):
            for i in range(6):
                self.put(OBJECTS[d]+i*256,TABLES[d]+i*256)
                for m,n in METHODS.items():
                    a=STUBS[d]+i*256+m;self.put(TABLES[d]+i*256+m,a);cpu.mem_write(a,b'\xc2'+struct.pack('<H',n))
            hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=STUBS[d],end=STUBS[d]+0x5ff))
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        try:yield
        finally:
            for h in hooks:cpu.hook_del(h)
            for a,v in saved.items():cpu.mem_write(a,v)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()

def lifecycle_cases(oracle):
    b=CombinedOracle(oracle);startup=StartupOracle(oracle);layout=LayoutOracle(oracle);queue=QueueOracle(oracle);toggle=ToggleOracle(oracle);diagnostic=DiagnosticOracle(oracle);cpu=oracle.cpu;cases=[]
    with ExitStack() as stack:
        stack.enter_context(b.substituted());stack.enter_context(queue.substituted());stack.enter_context(layout.substituted());stack.enter_context(toggle.substituted())
        stack.enter_context(startup.substituted(connected=True,real_numlock=True,real_helpers=(0x6ef890,0x6bedf0)))
        stack.enter_context(diagnostic.substituted())
        for mp,kp in ((0,0),(1,0),(2,3),(3,2),(4,4),(5,5),(0,1)):
            for variant in range(2):
                b.profiles=(mp,kp);b.events=[]
                f=fixture(0,4,1);f['globals']=bytearray(0x530);f['keys']=bytes(256);image_put(f['globals'],0x4c0,7);image_put(f['globals'],0x4c4,7)
                queue.reset(f)
                for a in set(FIELDS+KEYBOARD):b.put(a,0)
                sv=[0,0x1234,0x5678,0,1,0x7777,0,0xa5,0,640,480,32,1,2,0]
                startup.reset([0,0,1,1,1,0],sv);layout.reset([7,0xd01,0,0]);toggle.reset([variant,0])
                diagnostic_values=[i*7919 for i in range(160)]
                diagnostic_values[(0x8c4938-0x8c4730)//4]=0x7000f100
                diagnostic.reset(variant,diagnostic_values)
                data=bytearray(tables(0));data[488+17]=42;data[488+42]=54;cpu.mem_write(TABLES_ADDR,bytes(data))
                b.put(0xacadb0,7);b.put(0xacae14,0x12345678);b.put(0x89bdd4,1);cpu.mem_write(0xb2bbe8,bytes(256));cpu.mem_write(0x9e1be8,bytes(512))
                out=[]
                for op,a,c,d,e,g in STEPS:
                    result=0
                    if op==0:oracle.call(0x6bfa10,instruction_limit=100000)
                    elif op in (1,2):oracle.call(0x584450 if op==1 else 0x584610,(a,c,d,e,g,0xdeadbeef),cleanup=b'');result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op==3:oracle.call(0x6bf410,instruction_limit=100000)
                    elif op==4:oracle.call(0x4acdc0,(a,c));result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op==5:oracle.call(0x583210,(c,0x20a,a,0,0),instruction_limit=100000);result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op==6:oracle.call(0x6f07f0,(a,c),instruction_limit=100000)
                    elif op==7:oracle.call(0x6f0670);result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                    elif op==8:oracle.call(0x6f06a0)
                    elif op==9:b.put(0x8c4618,a);b.put(0x8c461c,c)
                    elif op==10:b.put(0x8c45f8,a)
                    out.extend((result,*startup.values(),*(b.word(x) for x in FIELDS),*(b.word(x) for x in KEYBOARD),*cpu.mem_read(0xaca8f0,0x530),*cpu.mem_read(0x8c8648,256),*cpu.mem_read(TABLES_ADDR,620),*cpu.mem_read(0x9e1be8,512),*(b.word(0xb2bbe8+i*4) for i in range(64)),toggle.state,len(toggle.logs),len(b.events)//3,*b.events))
                    out.extend(diagnostic.output())
                cases.append(dict(input=[mp,kp,variant,len(STEPS),*(v for s in STEPS for v in s)],output=out))
    return dict(cases=cases,scope='Actual connected startup, Num Lock, mouse and keyboard initialization, layout, down/release/query, wheel/report/geometry, one shared cleanup registry, repeat cleanup and restart. Distinct synthetic mouse/keyboard COM object and table namespaces; output slots always fully written. Platform imports/graphics/context/device factories remain explicit returning boundaries. Selected full shared images/words and ordered COM events observed after every operation; no live OS acceptance.')

# Avoid confusion with the pair of synthetic COM table bases above.
from tools.input_keyboard_layout_cases import TABLES as TABLES_ADDR
