"""Original console bodies with synthetic event APIs and one overlapping data image."""
import struct
from contextlib import contextmanager
BASE,SIZE,PENDING,HANDLE=0x8dc2d0,2168,0x8dc610,0x8dc6d0
LOCK,UNLOCK=0x69fee9,0x69ff4a
STUB=0x7000a000
IATS=(0x83b2f0,0x83b2c4,0x83b2c0,0x83b2bc,0x83b2b8,0x83b2b4)
ENTRIES=(0x7b0cd6,0x7b0e17,0x7b0d0e,0x7b0e33,0x7b0f33,0x7b1fe9)

def data_image(pending=0xffffffff,handle=0x12345678,scan=17,first=0,second=75,seed=0,match=True):
    data=bytearray((seed+i*29)&255 for i in range(SIZE))
    for row in range(12):
        struct.pack_into('<H',data,row*10,0x100+row)
        for plane in range(4):data[row*10+2+plane*2:row*10+4+plane*2]=bytes([224,(row+plane+1)&255])
    if match:
        struct.pack_into('<H',data,30,scan)
        for plane in range(4):data[32+plane*2:34+plane*2]=bytes([first,(second+plane*2)&255])
    for index in range(256):
        for plane in range(4):data[120+index*8+plane*2:122+index*8+plane*2]=bytes([0 if (index+plane)%2 else 224,(index+plane+1)&255])
    if scan<256:
        for plane in range(4):data[120+scan*8+plane*2:122+scan*8+plane*2]=bytes([first,(second+plane*2)&255])
    struct.pack_into('<I',data,PENDING-BASE,pending);struct.pack_into('<I',data,HANDLE-BASE,handle)
    return bytes(data)
def key(scan=17,flags=0,down=1,char=0):
    data=bytearray(16);struct.pack_into('<I',data,0,down);struct.pack_into('<H',data,8,scan);data[10]=char;struct.pack_into('<I',data,12,flags);return bytes(data)
def record(event_type=1,down=1,char=0,scan=17,flags=0):return struct.pack('<HH',event_type,0)+key(scan,flags,down,char)
def stream(pattern):
    ascii=record(char=65)
    patterns={0:[(1,1,ascii)],1:[(1,1,record(2)),(1,1,record(down=0)),(1,1,record(flags=0x100))],
              2:[(1,1,record(scan=19,flags=0x100)),(1,1,ascii)],3:[(1,1,record(char=255))],
              4:[(0,1,ascii)],5:[(1,0,ascii)]}
    return patterns[pattern]
def config(mode,script=0):return [mode,0x12345678,1,4,1,1,1,0x76543210,1,script,0]
def fixture(cfg,data=None,k=None,records=None):return cfg,data or data_image(),k or key(),stream(0) if records is None else records
def fixtures():
    for mode in range(4):
        for pending in (0xffffffff,0,0x12345680):
            for handle in (0xffffffff,0xfffffffe,0x12345678):
                for pattern in range(6):
                    for script in (0,1,2,8,48,255):
                        c=config(mode,script);events=stream(pattern);c[5]=len(events)
                        yield fixture(c,data_image(pending,handle),records=events)
    for mode in (1,3):
        for ok in (0,1):
            for count in (0,1,4):
                for peek in (0,1):
                    for received in (0,1,4,5):
                        for script in (0,64):
                            c=config(mode,script);c[2]=ok;c[3]=count;c[4]=peek;c[5]=received
                            yield fixture(c,records=stream(1))
    for mode in (0,2):
        for opened in (0xffffffff,0x12345678):
            for mode_ok in (0,1):
                for set_ok in (0,1):
                    for pattern in (0,4,5):
                        c=config(mode,16);c[1]=opened;c[6]=mode_ok;c[8]=set_ok
                        yield fixture(c,data_image(handle=0xfffffffe),records=stream(pattern))
    for mode in (0,2):
        yield fixture(config(mode,256),records=[(1,1,record(scan=89))])
    for scan in (0,1,17,88,89,113,255,65535):
        for flags in (0,1,3,4,12,16,19,28,0x100,0x101,0x104,0x110,0x113):
            if scan>255 and not flags&0x100:continue
            for first,second in ((0,0),(0,75),(224,255),(65,75)):
                yield fixture(config(4),data_image(scan=scan,first=first,second=second),key(scan,flags),[])
    yield fixture(config(4),data_image(match=False),key(65535,0x100),[])
    for result in (0,0xffffffff,0x87654321):
        for script in (0,4,255):
            c=config(5,script);c[1]=result;yield fixture(c)
class ConsoleOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,a):return struct.unpack('<I',self.oracle.cpu.mem_read(a,4))[0]
    def put(self,a,v):self.oracle.cpu.mem_write(a,struct.pack('<I',v&0xffffffff))
    def reset(self,c,data,k,records):
        self.config=c;self.records=records;self.index=0;self.logs=[];self.count_pointer=0
        self.oracle.cpu.mem_write(BASE,data);self.oracle.cpu.mem_write(0x71004000,k)
    def observe(self,cpu,address,size,user):
        stack=cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP);at=lambda n:self.word(stack+4+n*4)
        code=0 if address==LOCK else 1 if address==UNLOCK else 2+(address-STUB)//0x100
        handle=0;arg=0;extra=[0]*6
        if code<2:
            arg=at(0)
            if arg!=8:raise AssertionError('console lock ABI')
        elif code==2:
            if bytes(cpu.mem_read(at(0),7))!=b'CONIN$\0':raise AssertionError('console open name')
            handle=1;arg=at(1);extra[:5]=[at(i) for i in range(2,7)]
        else:
            handle=at(0)
            if code==4:arg=at(2)
            if code==6:arg=at(1)
            if code==7:
                arg=at(2)
                if arg!=1:raise AssertionError('console read count ABI')
        self.logs.append([code,handle,arg,self.word(PENDING),self.word(HANDLE),self.index,*extra])
        c=self.config;script=c[9];result=0
        if code==0:
            if script&1:self.put(PENDING,0x1234)
        elif code==1:
            if script&2:self.put(PENDING,0xabcd)
        elif code==2:
            if script&4:self.put(HANDLE,0x11223344);self.put(PENDING,0x7788)
            result=c[1]
        elif code==3:
            self.count_pointer=at(1);self.put(self.count_pointer,c[3]);result=c[2]
            if script&8:self.put(HANDLE,0x22334455)
        elif code==4:
            buffer=bytearray(arg*20)
            for i,(_,_,event) in enumerate(self.records[self.index:self.index+arg]):buffer[i*20:i*20+20]=event
            cpu.mem_write(at(1),bytes(buffer));self.put(at(3),c[5]);result=c[4]
            if script&64:self.put(self.count_pointer,0)
        elif code==5:
            self.put(at(1),c[7]);result=c[6]
            if script&16:self.put(HANDLE,0x33445566)
        elif code==6:
            result=c[8]
            if script&128:self.put(PENDING,0x12345678)
        elif code==7:
            status,count,event=self.records[self.index] if self.index<len(self.records) else (0,0,bytes(20))
            self.index+=1;cpu.mem_write(at(1),event);self.put(at(3),count);result=status
            if script&32:self.put(HANDLE,0x44556677);self.put(PENDING,0xaabbccdd)
            if script&256:self.put(PENDING,0x4b00)
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
    def output(self):return [*self.oracle.cpu.mem_read(BASE,SIZE),self.index,len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved={a:bytes(cpu.mem_read(a,1)) for a in (LOCK,UNLOCK)};iats={a:bytes(cpu.mem_read(a,4)) for a in IATS}
        for a in (LOCK,UNLOCK):cpu.mem_write(a,b'\xc3')
        for i,(iat,cleanup) in enumerate(zip(IATS,(28,8,16,8,8,16))):
            target=STUB+i*0x100;cpu.mem_write(target,b'\xc2'+struct.pack('<H',cleanup));self.put(iat,target)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in (LOCK,UNLOCK,*(STUB+i*0x100 for i in range(6)))]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            for a,data in saved.items():cpu.mem_write(a,data)
            for a,data in iats.items():cpu.mem_write(a,data)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
def capture(oracle):
    observer=ConsoleOracle(oracle);cases=[]
    with observer.substituted():
        for c,data,k,records in fixtures():
            observer.reset(c,data,k,records);args=(0x71004000,) if c[0]==4 else ()
            oracle.call(ENTRIES[c[0]],args,instruction_limit=100000)
            result=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
            cases.append(dict(input=[*c,*data,*k,len(records),*(v for status,count,event in records for v in (status,count,*event))],output=[result,*observer.output()]))
    return cases


def lifecycle_cases(oracle):
    observer=ConsoleOracle(oracle);cases=[]
    with observer.substituted():
        for profile in range(4):
            c=config(0,(0,2,48,255)[profile]);c[5]=1
            events=[(1,1,record(flags=0x100)),(1,1,record(char=65)),(0,0,record())]
            if profile==2:events=[(0,1,record(char=65))]
            data=data_image(handle=0xfffffffe if profile in (0,2) else 0x12345678)
            observer.reset(c,data,key(),events);observer.put(0x8c8924,0);observer.put(0xacae24,0)
            steps=[0,2,0,3,0,4,1,2,0,3];output=[]
            for op in steps:
                observer.count_pointer=0
                entry=(0x7b0e17,0x7b0cd6,0x6f01d0,0x6f0450,0x6f0580)[op]
                oracle.call(entry,(),instruction_limit=100000)
                output.extend([oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*observer.output()])
            cases.append(dict(input=[*c,*data,*key(),len(events),*(v for status,count,event in events for v in (status,count,*event)),len(steps),*steps],output=output))
    return dict(cases=cases,scope='Persistent actual console locking/availability/read/decode/pending and fallback/dispatcher/disabled-default bodies, with console API bridges; records are peeked relative to consumed event position.')
