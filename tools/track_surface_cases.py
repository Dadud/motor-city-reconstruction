"""Synthetic complete track surface calls with actual grid/path children."""
import struct
BASE,SIZE,PATH,BLOCKS,GEOMETRY=0x71000000,0x6000,0x71001000,0x71003000,0x71005000


def fixture(mode,cached,previous,neighbors,upward,x,z,seed):
    arena=bytearray(SIZE)
    def word(a,v):struct.pack_into('<I',arena,a-BASE,v&0xffffffff)
    def real(a,v):struct.pack_into('<f',arena,a-BASE,v)
    identifiers=[0,1,2] if mode!=3 else [2,1,0]
    if mode==4:identifiers=[1]
    if mode==1:identifiers=[]
    for i,b in enumerate(identifiers):word(BASE+0x100+i*4,b)
    root=struct.pack('<4I',0xdeadbeef,len(identifiers),BASE+0x100,0) if mode else bytes(16)
    vertices=((0,0,0),(16,0,0),(16,0,16),(0,0,16))
    for b in range(3):
        block=BLOCKS+b*0x6c4;geo=GEOMETRY+b*0x200
        word(block+0x3c,geo+0x80);word(block+0x14c,geo);word(block+0x67c,geo+0xc0)
        word(block+0x680,8)
        for j in range(8):word(block+0x6a4+j*4,previous if neighbors and j==7 else 0xffffffff)
        for off,v in ((0x664,b*24),(0x66c,0),(0x670,b*24+16),(0x678,16)):real(block+off,v)
        for i,point in enumerate(vertices):struct.pack_into('<3f',arena,geo-BASE+i*12,*point)
        struct.pack_into('<4H',arena,geo+0x80-BASE,0,1,2,3)
        struct.pack_into('<10h',arena,geo+0xc0-BASE,0,0,0,0,100+b,
                         (32767 if upward&(1<<b) else -32768),-200-b,300+b,-400-b,500+b)
        for j in range(8):struct.pack_into('<3f',arena,PATH-BASE+(b*8+j)*0x54,b*24+j*2,0,j)
    record=bytearray((seed+i*37)&255 for i in range(68))
    struct.pack_into('<I',record,4,previous)
    struct.pack_into('<I',record,12,GEOMETRY+0xc0 if cached else 0)
    for j in range(4):struct.pack_into('<I',record,16+j*4,GEOMETRY+j*12)
    return arena,root,record


def configurations():
    for mode in range(5):
        for cached in (0,1):
            for previous in (0,1,2,99):
                for neighbors in (0,1):
                    for upward in (0,3,7):
                        for x,z in ((-1,8),(0,0),(8,8),(16,16),(32,8)):
                            yield mode,cached,previous,neighbors,upward,x,z,(mode*37+previous)&255


def capture(oracle):
    cpu=oracle.cpu;result=[]
    for mode,cached,previous,neighbors,upward,x,z,seed in configurations():
        arena,root,record=fixture(mode,cached,previous,neighbors,upward,x,z,seed)
        cpu.mem_write(BASE,bytes(arena));cpu.mem_write(0xa559d8,root+bytes(65536-16))
        cpu.mem_write(0xa55970,struct.pack('<2f',0,0));cpu.mem_write(0xa659d8,struct.pack('<2f',1,1))
        for a,v in ((0x97c408,BLOCKS),(0x97c38c,PATH),(0x988e38,24),(0x97dbec,2)):
            cpu.mem_write(a,struct.pack('<I',v))
        cpu.mem_write(BASE+0x8000,bytes(record));cpu.mem_write(BASE+0x8100,struct.pack('<3f',x,7,z))
        oracle.call(0x42e760,(BASE+0x8100,BASE+0x8000))
        result.append(dict(input=[mode,cached,previous,neighbors,upward,x&0xffffffff,z,seed],
            output=[cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*cpu.mem_read(BASE+0x8000,68)]))
    return result
