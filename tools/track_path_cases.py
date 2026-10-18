"""Original complete path selection and side tests; no substitutions."""
import random
import struct


def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]


def fixtures(name):
    rng=random.Random(0x42e6b0)
    sets=[[(i-16,0,0) for i in range(32)],[(1,2,3)]*32]
    sets += [[tuple(rng.uniform(-100,100) for _ in range(3)) for _ in range(32)] for _ in range(4)]
    positions=[(0,0,0),(1,17,3),(-16,0,0),(16,0,0),(0,0,1),(0,0,-1),
               (0.5,0,0),(1.0000001192092896,0,3),(-1e10,0,1e10),
               (7,0,0),(8,0,0),(31,0,0)]
    for points in sets:
        for position in positions:
            if name=='nearest_path_point':
                for group in range(3):
                    for count in (-1,0,1,2,7,8,9):
                        yield group,count,32,position,points
            elif name=='path_side':
                for size in (1,2,8,17,32):
                    for index in range(size):yield index,0,size,position,points
            else:raise ValueError(name)


def capture(oracle,name):
    cpu=oracle.cpu
    path,blocks,query=0x71001000,0x71004000,0x71008000
    result=[]
    for a,b,size,position,points in fixtures(name):
        image=bytearray(32*0x54)
        for i,point in enumerate(points):struct.pack_into('<3f',image,i*0x54,*point)
        cpu.mem_write(path,bytes(image));cpu.mem_write(query,struct.pack('<3f',*position))
        cpu.mem_write(0x97c38c,struct.pack('<I',path))
        if name=='nearest_path_point':
            cpu.mem_write(0x97c408,struct.pack('<I',blocks))
            cpu.mem_write(blocks+a*0x6c4+0x680,struct.pack('<i',b))
            oracle.call(0x42e6b0,(query,a))
        else:
            cpu.mem_write(0x988e38,struct.pack('<I',size))
            oracle.call(0x42ee50,(query,a))
        inputs=[a,b&0xffffffff,size,*(bits(v) for v in position),*(bits(v) for point in points for v in point)]
        observed=[cpu.reg_read(oracle.reg.UC_X86_REG_EAX),*struct.unpack('<3I',cpu.mem_read(query,12))]
        for i in range(32):observed.extend(struct.unpack('<3I',cpu.mem_read(path+i*0x54,12)))
        result.append(dict(input=inputs,output=observed))
    return result
