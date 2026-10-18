"""Complete original free-camera handler with actual key/math/spatial children."""
import random
import struct
from contextlib import contextmanager,nullcontext
from tools.track_surface_cases import BASE,SIZE,PATH,BLOCKS

CONTROLS=(0x38,0x1d,0x13,0xd2,0xd3,0x2a,0x36,0xcd,0xcb,0xd0,0xc8,0xc9,0xd1)
CAMERA=BASE+0x9000
SUBJECT=BASE+0xb000


def fixtures():
    rng=random.Random(0x433820)
    masks=[0,*(1<<i for i in range(len(CONTROLS))),8191,
           (1<<5)|(1<<7),(1<<6)|(1<<8),(1<<0)|(1<<1)|(1<<10)]
    masks += [rng.randrange(8192) for _ in range(160)]
    for i,mask in enumerate(masks):
        seed=(i*37)&255
        image=bytearray((seed+j*17)&255 for j in range(512))
        for off in (0,0x100):
            struct.pack_into('<3f',image,off+12,8,7,8)
            matrix=(1,0,0,0,1,0,0,0,1) if i%2 else (0.75,0.25,0.1,-0.25,0.75,0.2,0.1,0.2,1)
            struct.pack_into('<9f',image,off+24,*matrix)
            struct.pack_into('<f',image,off+60,(0.25,1,3.5)[i%3])
            struct.pack_into('<I',image,off+68+12,0)
        struct.pack_into('<I',image,0x8c,SUBJECT if i&1 else 0)
        struct.pack_into('<I',image,0x18c,SUBJECT if i&2 else 0)
        keys=bytearray(128)
        for k,code in enumerate(CONTROLS):
            if mask&(1<<k):keys[code&127]=(1,128,255)[i%3]
        latches=bytearray((seed+j*11)&255 for j in range(512));latches[0x13]=0 if i%2 else 255
        subject=bytearray((seed+j*19)&255 for j in range(68));struct.pack_into('<I',subject,12,0)
        yield 1,0x12345678,image,keys,latches,subject
        if i<8:
            for event in (0,2,0xffffffff):yield event,0x87654321,image,keys,latches,subject


def initialize(oracle,stamp,image,keys,latches,subject):
    cpu=oracle.cpu
    arena=bytearray(SIZE);struct.pack_into('<I',arena,BLOCKS-BASE+0x680,8)
    cpu.mem_write(BASE,bytes(arena));cpu.mem_write(0xa559d8,bytes(65536))
    cpu.mem_write(0xa55970,struct.pack('<2f',0,0));cpu.mem_write(0xa659d8,struct.pack('<2f',1,1))
    for a,v in ((0x97c408,BLOCKS),(0x97c38c,PATH),(0x988e38,8),(0x97dbec,0),
                (0x98c0f8,CAMERA+0x100),(0xaa456c,stamp)):
        cpu.mem_write(a,struct.pack('<I',v))
    cpu.mem_write(CAMERA,bytes(image));cpu.mem_write(0x8c8648,bytes(keys))
    cpu.mem_write(0x9e1be8,bytes(latches));cpu.mem_write(SUBJECT+0x370,bytes(subject))


def capture(oracle):
    cpu=oracle.cpu;result=[]
    for event,stamp,image,keys,latches,subject in fixtures():
        initialize(oracle,stamp,image,keys,latches,subject)
        oracle.call(0x433820,(event,))
        result.append(dict(input=[event,stamp,*image,*keys,*latches,*subject],
            output=[*cpu.mem_read(CAMERA,512),*cpu.mem_read(0x8c8648,128),
                    *cpu.mem_read(0x9e1be8,512),*cpu.mem_read(SUBJECT+0x370,68)]))
    return result


@contextmanager
def window_platform(oracle):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu
    create,default=0x6bd640,0x70009200
    saved_create=bytes(cpu.mem_read(create,1));saved_default=bytes(cpu.mem_read(0x83b380,4))
    state=dict(creations=0,defaults=[])
    def observe(cpu,address,size,user):
        if address==create:
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,0x12340000+state['creations']*0x100)
            state['creations']+=1
        else:
            args=list(struct.unpack('<4I',cpu.mem_read(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4,16)))
            state['defaults'].append(args)
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX,0xd3f00000^args[1])
    cpu.mem_write(create,b'\xc3');cpu.mem_write(default,b'\xc2\x10\x00')
    cpu.mem_write(0x83b380,struct.pack('<I',default))
    if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    hooks=[cpu.hook_add(UC_HOOK_CODE,observe,begin=a,end=a) for a in (create,default)]
    try:yield state
    finally:
        for hook in hooks:cpu.hook_del(hook)
        cpu.mem_write(create,saved_create);cpu.mem_write(0x83b380,saved_default)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()


def lifecycle_cases(oracle,dispatched=False):
    from tools.input_queue_cases import fixture,words,QueueOracle
    observer=QueueOracle(oracle);cpu=oracle.cpu;result=[]
    cameras=[row for row in fixtures() if row[0]==1][:4]
    for variant,(_,_,image,_,_,subject) in enumerate(cameras):
        remapped=variant&1
        queue=fixture(variant*37,1 if variant<2 else 4,1,remap_kind=remapped)
        if dispatched:
            for offset,value in ((0x51c,0),(0x524,0),(0x4f4,0),(0,0 if variant>=2 else 1)):
                struct.pack_into('<I',queue['globals'],offset,value)
        queue['keys']=bytes(256)
        latches=bytes(512)
        shift=0x2a if variant<2 else 0x36
        arrow=0xcd if variant<2 else 0xcb
        steps=[(2,0,0x1000),(0,shift,1),(0,arrow,3),(2,1,0x1001),(2,1,0x1002),
               (1,shift,1),(2,1,0x1003),(1,arrow,1),(0,0xc8,1),(2,1,0x1004),
               (0,0x38,1),(0,0x1d,1),(2,1,0x1005),(1,0x38,1),(1,0x1d,1),
               (1,0xc8,1),(0,0xd2,1),(2,1,0x1006),(1,0xd2,1),
               (0,0x13,1),(2,1,0x1007),(2,1,0x1008),(1,0x13,1),
               (2,1,0x1009),(0,0x13,1),(2,1,0x100a),(3,2,0)]
        if dispatched:
            steps=[(4,0,0),(4,0,0),(5,0,0),(0,shift,1),(6,0x777,0),(5,1,0)]+steps+[
                (7,0x1234abcd,0x012a0002),(7,0xe9,0x007f0001),(6,0x777,0),(4,0,0)]
        if remapped:
            steps=[(op,((a&128)|(127-(a&127))) if op in (0,1) else a,b) for op,a,b in steps]
        initialize(oracle,0,image,bytes(128),latches,subject);observer.reset(queue)
        if dispatched:cpu.mem_write(0x89bdd4,struct.pack('<I',1))
        output=[]
        with observer.substituted(), (window_platform(oracle) if dispatched else nullcontext()) as platform:
            for op,a,b in steps:
                bits=((a&127)<<16)|((a>>7)<<24)|(b&65535)
                if dispatched and op in (0,1,6,7):
                    message=(0x104 if variant>=2 else 0x100) if op==0 else (0x105 if variant>=2 else 0x101) if op==1 else 0x102 if op==7 else a
                    args=(7,message,a if op==7 else 0x70,b if op==7 else bits if op!=6 else 0)
                    if variant&1:oracle.call(0x583290,args,cleanup=b'')
                    else:oracle.call(0x583210,(*args,0))
                elif op==0:oracle.call(0x584450,(1,7,0x100,0x70,bits,0xdeadbeef),cleanup=b'')
                elif op==1:oracle.call(0x584610,(1,7,0,0,bits,0xdeadbeef),cleanup=b'')
                elif op==2:
                    cpu.mem_write(0xaa456c,struct.pack('<I',b));oracle.call(0x433820,(a,))
                elif op==3:oracle.call(0x584ca0,(a,))
                elif op==4:oracle.call(0x583c30,instruction_limit=1_000_000)
                elif op==5:cpu.mem_write(0x89bdd4,struct.pack('<I',a))
                else:raise ValueError(op)
                observed_return=op in (0,1) or (dispatched and op in (4,6,7))
                output.extend([cpu.reg_read(oracle.reg.UC_X86_REG_EAX) if observed_return else 0,
                    *cpu.mem_read(CAMERA,512),*cpu.mem_read(0x9e1be8,512),
                    *observer.output(),*cpu.mem_read(SUBJECT+0x370,68)])
                observer.logs.clear()
                if dispatched:
                    output.extend([struct.unpack('<I',cpu.mem_read(0x89bdd4,4))[0],platform['creations'],len(platform['defaults']),
                                   *(v for row in platform['defaults'] for v in row)])
                    platform['defaults'].clear()
        prefix=[variant&1,int(variant>=2)] if dispatched else []
        result.append(dict(input=[*prefix,*image,*latches,*subject,*words(queue),len(steps),
                                  *(v for step in steps for v in step)],output=output))
    scope=('Initialized general/Windows dispatch through actual key/camera children; only synchronizer creation, locks and default procedure substituted.' if dispatched else
           'Connected key-down/release/resize and free-camera calls; only critical-section imports substituted; state observed after every operation.')
    return dict(cases=result,scope=scope)
