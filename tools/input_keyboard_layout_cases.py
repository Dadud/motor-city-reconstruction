"""Keyboard setup with explicit type queries and aliased translation/remap bytes."""
import struct
from contextlib import contextmanager
from tools.input_queue_cases import QueueOracle,fixture,words,put,REMAP
from tools.input_translation_cases import TABLES
ENTRY,IAT,FIRST,SECOND=0x6f09f0,0x83b3d4,0x7000e700,0x7000e800
REMAP_ID,OFFSET=0x8c8930,488

def configurations():
    for kind in (0,1,6,7,8,0x7fffffff,0x80000000,0xffffffff):
        for subtype in (0,0xd00,0xd01,0xd02,0xd03,0xd04,0xd05,0x7fffffff,0x80000000,0xffffffff):
            for script in (0,1,2,4,8,16,31):
                yield [kind,subtype,script,(kind+subtype+script)&255]

def tables(seed):return bytes((seed+i*29)&255 for i in range(620))
class LayoutOracle:
    def __init__(self,oracle):self.oracle=oracle
    def word(self,address):return struct.unpack('<I',self.oracle.cpu.mem_read(address,4))[0]
    def put(self,address,value):self.oracle.cpu.mem_write(address,struct.pack('<I',value))
    def reset(self,config):self.config=config;self.logs=[];self.put(IAT,FIRST)
    def observe(self,cpu,address,size,user):
        kind=self.word(cpu.reg_read(self.oracle.reg.UC_X86_REG_ESP)+4)
        if kind not in (0,1):raise AssertionError('keyboard type kind')
        self.logs.append([int(address==SECOND),kind,self.word(0xacae18),self.word(0xaca8f0),cpu.mem_read(REMAP_ID+17,1)[0],cpu.mem_read(REMAP_ID+42,1)[0]])
        script=self.config[2]
        if script&1:self.put(IAT,SECOND)
        if script&2:self.put(0xacae18,0 if self.word(0xacae18) else REMAP)
        if script&4:cpu.mem_write(REMAP_ID+17,bytes([(self.config[3]+len(self.logs))&255]))
        if script&8:self.put(0xaca8f0,self.word(0xaca8f0)^1)
        if script&16 and kind==1:self.put(0xacae18,0xdeadbeef)
        result=(7 if kind==0 else 0xd04) if address==SECOND else self.config[kind]
        cpu.reg_write(self.oracle.reg.UC_X86_REG_EAX,result)
    def output(self):
        return [int(self.word(IAT)==SECOND),*self.oracle.cpu.mem_read(TABLES,620),len(self.logs),*(v for row in self.logs for v in row)]
    @contextmanager
    def substituted(self):
        from unicorn import UC_HOOK_CODE
        cpu=self.oracle.cpu;saved=bytes(cpu.mem_read(IAT,4))
        for address in (FIRST,SECOND):cpu.mem_write(address,b'\xc2\x04\x00')
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
        hooks=[cpu.hook_add(UC_HOOK_CODE,self.observe,begin=a,end=a) for a in (FIRST,SECOND)]
        try:yield
        finally:
            for hook in hooks:cpu.hook_del(hook)
            cpu.mem_write(IAT,saved)
            if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()

def capture(oracle):
    layout=LayoutOracle(oracle);queue=QueueOracle(oracle);cases=[]
    with layout.substituted():
        for config in configurations():
            f=fixture(config[3],4,1)
            put(f['globals'],0x528,(0,REMAP,REMAP_ID,0xffffffff)[config[3]%4])
            queue.reset(f);layout.reset(config);data=tables(config[3]);oracle.cpu.mem_write(TABLES,data)
            oracle.call(ENTRY,())
            cases.append(dict(input=[*config,*words(f),*data],output=[oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*queue.output(),*layout.output()]))
    return cases


def lifecycle_cases(oracle):
    from tools.input_translation_cases import TranslationOracle,DEVICE
    layout=LayoutOracle(oracle);queue=QueueOracle(oracle);translation=TranslationOracle(oracle);cases=[]
    with layout.substituted(),queue.substituted(),translation.substituted():
        for config,initial,mask in (([7,0xd01,0,73],0,0),([6,0,1,73],REMAP,1),([7,0xd04,4,41],0,1),([7,0xd05,2,73],REMAP_ID,1)):
            f=fixture(config[3],4,1);put(f['globals'],4,0);put(f['globals'],0x4e0,0);put(f['globals'],0x528,initial);f['keys']=bytes(256)
            t=[17,0,mask,128,0,0,0,73,256,1,1];translation.reset(t)
            data=bytearray(tables(config[3]))
            for scan,value in ((17,42),(42,54),(54,17),(58,58),(127,255)):data[OFFSET+scan]=value
            oracle.cpu.mem_write(TABLES,bytes(data));queue.reset(f);layout.reset(config);latches=bytes(512);oracle.cpu.mem_write(0x9e1be8,latches)
            steps=[(0,0,0,0,0,0),(1,1,7,0x100,0x70,2|(17<<16)),(2,0,0,0,0,0),
                   (3,0,0,0,0,0),(5,42,1,0,0,0),(5,42,1,0,0,0),(4,1,7,0,0,17<<16),
                   (6,17,54,0,0,0),(1,1,7,0x100,0x70,1|(17<<16)),(3,0,0,0,0,0),
                   (4,1,7,0,0,17<<16),(7,141,1,0,0,0),(0,0,0,0,0,0),
                   (1,1,7,0x100,0x70,1|(127<<16)),(3,0,0,0,0,0),(4,1,7,0,0,127<<16),
                   (8,0,0,0,0,0),(1,1,7,0x100,0x70,1|(17<<16)),(3,0,0,0,0,0),
                   (0,0,0,0,0,0),(1,1,7,0x100,0x70,1|(58<<16)),(3,0,0,0,0,0)]
            output=[]
            for op,a,b,c,d,e in steps:
                result=0
                if op==0:oracle.call(ENTRY,())
                elif op==1:oracle.call(0x584450,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                elif op==2:oracle.call(0x583160,())
                elif op==3:oracle.call(0x5830c0,())
                elif op==4:oracle.call(0x584610,(a,b,c,d,e,0xdeadbeef),cleanup=b'')
                elif op==5:oracle.call(0x4acdc0,(a,b))
                elif op==6:oracle.cpu.mem_write(REMAP_ID+a,bytes([b]))
                elif op==7:oracle.call(0x6f05b0,(a,b))
                elif op==8:layout.put(0xacae18,a)
                if op not in (6,8):result=oracle.cpu.reg_read(oracle.reg.UC_X86_REG_EAX)
                output.extend([result,*queue.output(),*layout.output(),*translation.output(False),*oracle.cpu.mem_read(DEVICE,260),*oracle.cpu.mem_read(0x9e1be8,512)])
            cases.append(dict(input=[*config,*t,*words(f),*data,*latches,len(steps),*(v for step in steps for v in step)],output=output))
    return dict(cases=cases,scope='Persistent actual layout selection, down/release, key query/latches, peek/pop and scan translation. Selected remap aliases the live translation image; explicit table/pointer fixture writes. Returning type queries, synchronization imports and translation state provider only substituted.')
