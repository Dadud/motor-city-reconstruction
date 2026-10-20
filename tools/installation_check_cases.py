"""Complete installation coordinator; explicit synthetic OS/registry services."""
import struct
from contextlib import contextmanager

TABLE = 0xa52d48
GLOBALS = (0xa55494, 0xa55498, 0xa5549c, 0x929dec)
ROOT, CANDIDATE, CDROOT, OWNER, LEVEL = (0x71000100, 0x71000200, 0x71000300,
                                          0x71000400, 0x71000500)
HELPERS = {0x51d330:(1,12), 0x51d490:(2,0), 0x51d7c0:(3,12),
           0x51d580:(4,12), 0x51d690:(5,8), 0x699330:(7,0),
           0x533f60:(8,0), 0x699e6d:(9,0), 0x699d47:(10,0),
           0x51d1d0:(12,0), 0x7000e100:(11,4)}
LEVELS = (0, 1, 2, 0xffffffff, 3, 0x80000000, 0x7fffffff, 0xfffffffe)
STOCK_ROWS = ((0x8e3ac4,0),(0x896110,0),(0x896100,0),(0x8960f0,0),
 (0x8960e4,0),(0x8960d0,2),(0x8960c0,0),(0x8960ac,0),(0x896094,0),
 (0x896088,0),(0x89607c,0),(0x896070,0),(0x896064,0),(0x896058,0),
 (0x896048,2),(0x896038,0),(0x89602c,0),(0x896020,0),(0x896014,0))

def masks(seed):
    return ((0,1<<2,(1<<2)|(1<<5)|(1<<25),0x3ffffff)[(seed//8)%4],
            (0,1<<2,(1<<5)|(1<<25),0x3ffffff)[(seed//32)%4])

class CheckOracle:
    def __init__(self, oracle): self.oracle = oracle
    def word(self, address):
        return struct.unpack('<I', self.oracle.cpu.mem_read(address,4))[0]
    def put(self, address, value):
        self.oracle.cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))
    def image(self, address, size): return bytes(self.oracle.cpu.mem_read(address,size))
    def flags(self): return [self.word(address) for address in GLOBALS]
    def observe(self, cpu, address, size, user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)
        frame=cpu.reg_read(self.oracle.reg.UC_X86_REG_EBP)
        arg=lambda i:self.word(stack+4+i*4)
        candidate=frame-0x530
        cdroot=frame-0x21c
        ident=HELPERS[address][0]
        if ident in (1,4): args=[OWNER,arg(0),arg(1),arg(2)]
        elif ident in (2,12): args=[OWNER]
        elif ident==3: args=[OWNER,arg(0),ROOT,arg(2)]
        elif ident==5: args=[OWNER,arg(0),LEVEL]
        elif ident==7:
            normalize=lambda value:{frame-0x118:ROOT,candidate:CANDIDATE,
                                    cdroot:CDROOT}.get(value,value)
            count=3 if arg(1)==0x8885b8 else 2 if arg(1)==0x896148 else 4
            args=[normalize(arg(i)) for i in range(count)]
        elif ident in (8,10,11): args=[arg(0)]
        elif ident==9: args=[CANDIDATE,arg(1)]
        self.log.extend((ident,len(args),*args))
        config=self.seed%8; result=0
        def write(destination, payload):
            cpu.mem_write(destination,payload+b'\0')
        if ident==2: result=int(config!=0)
        elif ident==3:
            text=(b'C:\\ROOT\\',b'C:\\ROOT\\\\',b'ROOT',b'C:\\')[self.seed%4]
            write(arg(1),text); result=self.seed%2
        elif ident==4: result=int(config!=1)
        elif ident==5:
            self.put(arg(1),LEVELS[(self.seed//8)%8]); result=int(config!=2)
        elif ident==7:
            fmt=arg(1); destination=arg(0)
            if fmt==0x8885b8: value=b'C:\\mcity.exe'
            elif fmt==0x896148: value=b'c:\\'
            else:
                root=self.image(arg(2),260).split(b'\0')[0]
                name=arg(3)
                if 0x71008000<=name<0x710081f0:
                    value=b'ITEM%02d'%((name-0x71008000)//16)
                else:
                    value={0x8e3ac4:b'',0x896110:b'SaveData\\',0x896100:b'Data\\Tracks\\',
                      0x8960f0:b'Data\\GameArt\\',0x8960e4:b'Data\\Parts\\',
                      0x8960d0:b'Data\\Audio\\Music\\',0x8960c0:b'Data\\Audio\\SFX\\',
                      0x8960ac:b'Data\\Audio\\Speech\\',0x896094:b'Data\\Audio\\Speechdata\\',
                      0x896088:b'Data\\Menus\\',0x89607c:b'Data\\Text\\',
                      0x896070:b'Data\\Fonts\\',0x896064:b'Data\\FeArt\\',
                      0x896058:b'Data\\DB\\',0x896048:b'Data\\Movies\\',
                      0x896038:b'Data\\Models\\',0x89602c:b'Data\\Skins\\',
                      0x896020:b'Data\\GUI\\',0x896014:b'Data\\Html\\'}[name]
                value=root+(b'\\' if fmt==0x896140 else b'')+value
            write(destination,value)
            if self.seed&64:self.put(GLOBALS[1],self.word(GLOBALS[1])^0x80000000)
        elif ident==8:
            if self.seed&256:self.put(GLOBALS[3],self.word(GLOBALS[3])+17)
            result=int(bool(masks(self.seed)[0]&(1<<arg(0))))
        elif ident==9:
            drive=self.image(arg(0),1)[0]-97
            result=0x71009000+drive*16 if masks(self.seed)[1]&(1<<drive) else 0
        elif ident==10:
            if self.seed&128:cpu.mem_write(candidate,b'M')
        elif ident==11: result=0x12340000+self.seed
        elif ident==12:
            if self.seed&32:self.put(GLOBALS[1],self.word(GLOBALS[1])^0x80000000)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)

    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu
        addresses=[a for a in HELPERS if a<0x70000000]
        saved={a:self.image(a,4) for a in (*addresses,0x83b284)}
        saved_fake=self.image(0x7000e100,4) if any(
            lo<=0x7000e100<hi for lo,hi,_ in cpu.mem_regions()) else None
        rowtable=self.image(0x895f14,256); hooks=[]
        if not any(lo==0 for lo,hi,perm in cpu.mem_regions()):cpu.mem_map(0,0x1000)
        if not any(lo<=0x7000e100<hi for lo,hi,_ in cpu.mem_regions()):
            cpu.mem_map(0x7000e000,0x1000)
        old_exception=self.word(0);self.put(0,0)
        try:
            for a,(_,n) in HELPERS.items():cpu.mem_write(a,b'\xc2'+struct.pack('<H',n))
            self.put(0x83b284,0x7000e100)
            for a in HELPERS:hooks.append(cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a))
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
            yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            for a,data in saved.items():cpu.mem_write(a,data)
            if saved_fake is not None:cpu.mem_write(0x7000e100,saved_fake)
            else:cpu.mem_unmap(0x7000e000,0x1000)
            cpu.mem_write(0x895f14,rowtable);self.put(0,old_exception)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()

def capture(oracle):
    helper=CheckOracle(oracle); cpu=oracle.cpu; cases=[]
    cases_to_run=[]
    for seed in range(512):
        count=(seed*7+seed//8)%32
        level=LEVELS[(seed//8)%8]
        rows=[]
        for i in range(count):
            typ=(0,1,2,3,4,0xffffffff)[(seed+i)%6]
            if level==2 and typ==3:typ=2
            rows.append((0x71008000+i*16,typ))
        cases_to_run.append((seed,rows))
    for block in range(8):cases_to_run.append((block*8+3,list(STOCK_ROWS)))
    with helper.substituted():
        for seed,rows in cases_to_run:
            helper.seed=seed;helper.log=[]
            count=len(rows)
            for i in range(32):
                identity,typ=rows[i] if i<count else (0,0)
                helper.put(0x895f14+i*4,identity)
                helper.put(0x895f94+i*4,typ)
            initial=bytes((seed+i*13)&255 for i in range(8320))
            cpu.mem_write(TABLE,initial)
            flags=[(seed*37+i*19)&0xffffffff for i in range(4)]
            for address,value in zip(GLOBALS,flags):helper.put(address,value)
            oracle.call(0x530790,instruction_limit=100000)
            result=cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            inputs=[seed,count,*[v for row in rows for v in row],*flags]
            output=[result,*helper.flags(),*helper.image(TABLE,8320),len(helper.log),*helper.log]
            cases.append(dict(input=inputs,output=output))
    return cases
