"""Complete original support-mask normal-load comparison; no substituted calls."""
import argparse
import itertools
import json
import struct
from client.normal_load import NormalLoadInput, normal_force_vectors
from tools.native_oracle import DynoOracle


def cases():
    for mask, pitch, bank, speed, vertical, curvature in itertools.product(range(16),
            (-0.25001, -0.25, -0.03, 0, 0.03, 0.25, 0.25001),
            (-0.1, 0, 0.1), (0, 15, 50), (0, 12), (-40, 40)):
        yield NormalLoadInput(tuple(bool(mask & (1 << i)) for i in range(4)),
            pitch, bank, 1450, 2.7, 1.6, 1.7, 0.55, 1.2, 1.5, speed, curvature,
            vertical, (9.8, 10, 9.5, 9.9))


def verify(executable):
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    owner, config = o.inputs, o.inputs+0x3000
    forces = (0x6cc, 0x7d8, 0x9f0, 0x8e4)
    count, maximum = 0, 0.0
    for state in cases():
        o._reset()
        image = bytearray([0xa5])*0x1d00
        struct.pack_into('<I', image, 0x1c94, config)
        for offset, value in ((0xc00, state.pitch), (0xc04, state.bank),
            (0x18b8, state.front_lever), (0x18bc, state.rear_lever),
            (0xa2c, state.speed), (0xbe8, state.curvature_scale),
            (0xa34, state.vertical_correction)):
            struct.pack_into('<f', image, offset, value)
        for force, flag, scale, supported, value in zip(forces, (0x6e8,0x7f4,0xa0c,0x900),
                (0x670,0x77c,0x994,0x888), state.support, state.wheel_scales):
            image[flag] = int(supported)
            struct.pack_into('<f', image, scale, value)
            struct.pack_into('<3f', image, force, 111, 222, 333)
        cpu.mem_write(owner, bytes(image))
        configuration = bytearray([0x5a])*0x100
        for offset, value in ((0x20,state.mass),(0x2c,state.wheelbase),(0x30,state.front_track),
                              (0x34,state.rear_track),(0x38,state.height_parameter)):
            struct.pack_into('<f', configuration, offset, value)
        cpu.mem_write(config, bytes(configuration))
        stack=o.frame-0x1000
        cpu.mem_write(stack, struct.pack('<II',o.stop,owner))
        cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x53d920,o.stop,count=20000)
        actual=bytes(cpu.mem_read(owner,len(image)))
        expected=normal_force_vectors(state)
        for force,target in zip(forces,expected):
            observed=struct.unpack_from('<3f',actual,force)
            for component,(value,wanted) in enumerate(zip(observed,target)):
                error=abs(value-wanted)
                tolerance=max(0.00025,abs(value)*3e-7)
                if (component != 1 and value != wanted) or error > tolerance:
                    raise AssertionError((count,state,hex(force),component,value,wanted,error))
                maximum=max(maximum,error)
            struct.pack_into('<3f',image,force,*target)
        if actual != image or cpu.mem_read(config,len(configuration)) != configuration:
            raise AssertionError('unexpected owner/configuration mutation')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
            'scope':'all four complete force vectors written by 0x53d920; original sine/cosine helpers; no substituted calls; synthetic owner state; unused x87 return excluded'}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
