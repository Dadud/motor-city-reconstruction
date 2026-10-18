"""Complete original grid query; diagnostic child alone is substituted."""
import struct

GRID,NODES=0xa559d8,0x71001000


def bits(value): return struct.unpack('<I',struct.pack('<f',value))[0]


def fixtures():
    coordinates=(-1,-0.5,0,0.5,1.5,255.5,256,511,511.5,512,767.5,768,
                 1023,1023.5,1024,65535,65535.5,65536,1e20)
    for mode in range(5):
        root=struct.pack('<4I',0xdeadbeef,7,NODES,0) if mode==0 else struct.pack('<4I',*[NODES+i*16 for i in range(4)])
        nodes=bytearray(320)
        for i in range(20):
            words=(0xdeadbeef,i,0,0)
            if i<4 and mode in (2,4):
                words=tuple(NODES+(4+i*4+j)*16 for j in range(4))
            if mode==3: words=(0,0,0,0)
            if mode==4 and i>=4:words=(NODES,)*4
            struct.pack_into('<4I',nodes,i*16,*words)
        for x in coordinates:
            for z in coordinates:
                # Populate every possible selected root without deriving a
                # native result: use each containing cell or the nearest edge.
                ix=max(0,min(63,int(max(0,x))//1024))
                iz=max(0,min(63,int(max(0,z))//1024))
                slot=ix*64+iz
                yield [x,17,z],[0,0],[1,1],slot,root,bytes(nodes)
    for x in (-20,-0.5,0,17,512,1024,65535):
        for origin,scale in (([10,-7],[2,0.5]),([-100,200],[0.25,4]),([0,0],[-1,-2])):
            yield [x,0,x],origin,scale,0,struct.pack('<4I',0xdeadbeef,1,0,0),bytes(320)


def capture(oracle):
    from unicorn import UC_HOOK_CODE
    cpu=oracle.cpu
    saved=bytes(cpu.mem_read(0x4400a0,1))
    logs=[]
    def diagnostic(cpu,address,size,user):
        if address==0x4400a0:
            logs.append(struct.unpack('<I',cpu.mem_read(cpu.reg_read(oracle.reg.UC_X86_REG_ESP)+4,4))[0])
    cpu.mem_write(0x4400a0,b'\xc3')
    if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    hook=cpu.hook_add(UC_HOOK_CODE,diagnostic,begin=0x4400a0,end=0x4400a0)
    result=[]
    try:
        for position,origin,scale,slot,root,nodes in fixtures():
            grid=bytearray(65536);grid[slot*16:slot*16+16]=root
            cpu.mem_write(GRID,bytes(grid));cpu.mem_write(NODES,nodes)
            cpu.mem_write(0xa55970,struct.pack('<2f',*origin))
            cpu.mem_write(0xa659d8,struct.pack('<2f',*scale))
            cpu.mem_write(oracle.inputs+0x8000,struct.pack('<3f',*position))
            logs.clear();oracle.call(0x552880,(oracle.inputs+0x8000,))
            result.append(dict(input=[*(bits(v) for v in (*position,*origin,*scale)),slot,*root,*nodes],
                output=[cpu.reg_read(oracle.reg.UC_X86_REG_EAX),len(logs),*logs,
                        *cpu.mem_read(GRID+slot*16,16),*cpu.mem_read(NODES,320)]))
    finally:
        cpu.hook_del(hook);cpu.mem_write(0x4400a0,saved)
        if hasattr(cpu,'ctl_flush_tb'):cpu.ctl_flush_tb()
    return result
