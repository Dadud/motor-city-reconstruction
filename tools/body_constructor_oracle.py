"""Compare complete original body construction and geometry with authored inputs."""
import argparse
import json
import random
import struct
from pathlib import Path
from client.body_constructor import construct_body
from client.body_geometry import body_samples
from tools.native_oracle import DynoOracle


def cases():
    dimensions = [(1., .5, 2.), (2., .5, 1.), (1., 1., 1.), (.1234567, .7654321, 2.345678)]
    dimensions += [(0., 3., 0.), (-1., .5, -2.), (0., 0., 0.)]
    rng = random.Random(0x51f440)
    dimensions += [tuple(rng.uniform(.05, 5.) for _ in range(3)) for _ in range(20)]
    for i, extent in enumerate(dimensions):
        for shape in range(5):
            for material in (0,1,2,3,4,5,6,7,0xffffffff):
                yield (i*37, 0. if i%3 == 0 else 500.+i*71.125, extent, shape, material)


def verify(executable):
    o = DynoOracle(executable); cpu = o.cpu
    count = geometry_count = 0
    owner = bytes((i*73+19)&255 for i in range(0x2000))
    for identity, mass, extent, shape, material in cases():
        o._reset(); cpu.mem_write(o.inputs, owner)
        stack = cpu.reg_read(o.reg.UC_X86_REG_ESP)
        cpu.mem_write(stack, struct.pack('<III4fII', o.stop, o.inputs, identity, mass, *extent, shape, material))
        o._run(0x51f440, o.stop, count=1000000)
        observed = bytes(cpu.mem_read(o.inputs, len(owner)))
        expected = construct_body(owner, identity, mass, extent, shape, material)
        if observed != expected:
            mismatch = [hex(i) for i,(a,b) in enumerate(zip(observed,expected)) if a != b]
            raise AssertionError((count, shape, material, extent, mismatch[:25],
                [(hex(p), struct.unpack_from('<f',observed,p)[0], struct.unpack_from('<f',expected,p)[0])
                 for p in range(0,len(owner),4) if observed[p:p+4] != expected[p:p+4]][:25]))
        count += 1
    # Independent geometry calls cover negative and signed-zero observations too.
    extents = [(1.,.5,2.), (2.,.5,1.), (1.,1.,1.), (-0.,0.,-0.), (-1.,.5,-2.),
               (.1234567,.7654321,2.345678)]
    for extent in extents:
        for shape in range(5):
            o._reset(); cpu.mem_write(o.inputs, bytes([0xa5])*0x108)
            stack = cpu.reg_read(o.reg.UC_X86_REG_ESP)
            cpu.mem_write(stack, struct.pack('<II3fI',o.stop,shape,*extent,o.inputs))
            o._run(0x51ed40,o.stop)
            expected = struct.pack('<66f',*(v for p in body_samples(shape,extent) for v in p))
            observed = bytes(cpu.mem_read(o.inputs,0x108))
            if observed != expected:
                raise AssertionError(('geometry',shape,extent,
                    [(i,struct.unpack_from('<f',observed,i)[0],struct.unpack_from('<f',expected,i)[0])
                     for i in range(0,0x108,4) if observed[i:i+4] != expected[i:i+4]]))
            geometry_count += 1
    return dict(constructor_cases=count, geometry_cases=geometry_count, maximum_absolute_error=0,
        scope='complete original calls; full 0x2000 owner observations and all 66 geometry values exact',
        integrated_vehicle_startup_verified=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('executable',type=Path)
    print(json.dumps(verify(parser.parse_args().executable)))
