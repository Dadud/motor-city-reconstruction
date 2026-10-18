"""Original complete matrix rotations, including actual trig children."""
import random
import struct


def bits(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def capture(oracle):
    rng=random.Random(0x6f1780)
    result=[]
    matrices=[[1,0,0,0,1,0,0,0,1],[-0.0,0.0,1,-1,2,-3,4,-5,6]]
    matrices += [[rng.uniform(-10,10) for _ in range(9)] for _ in range(20)]
    angles=[0.0,-0.0,0.125,-0.125,0.25,-0.25,0.5,1,-1,0.001,-0.001,1024,-1024]
    angles += [rng.uniform(-2,2) for _ in range(20)]
    for axis,entry in enumerate((0x6f1780,0x6f1850,0x6f1910)):
        for alias in (0,1):
            for matrix in matrices:
                source=struct.pack('<9f',*matrix)
                destination=struct.pack('<9I',*[0xcccccccc]*9)
                for angle in angles:
                    oracle.cpu.mem_write(oracle.inputs,source)
                    oracle.cpu.mem_write(oracle.inputs+0x100,destination)
                    output=oracle.inputs if alias else oracle.inputs+0x100
                    oracle.call(entry,(oracle.inputs,bits(angle),output))
                    observed=struct.unpack('<9I',oracle.cpu.mem_read(oracle.inputs,36))
                    observed+=struct.unpack('<9I',oracle.cpu.mem_read(output,36))
                    result.append(dict(input=[axis,alias,bits(angle),*struct.unpack('<9I',source),
                                              *struct.unpack('<9I',destination)],output=list(observed)))
    return result
