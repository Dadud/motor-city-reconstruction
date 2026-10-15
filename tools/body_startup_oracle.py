"""Full original shape adjustment and bounded connected startup-body execution."""
import argparse
import json
import struct
from client.body_geometry import customize_body_samples
from client.body_startup import prepare_startup_body
from client.owner_binding import body_inertia_scales
from tools.native_oracle import DynoOracle
from tools.owner_wheel_setup_oracle import cases


def startup_cases():
    for i,(owner,config) in enumerate(cases()):
        for selector in range(8):
            config=bytearray(config)
            struct.pack_into('<i',config,0x48,selector)
            struct.pack_into('<f',config,0x38,.5334+i*.01)
            struct.pack_into('<f',config,0,.25+i*.02)
            if i%3==0:struct.pack_into('<f',config,0x20,0.)
            yield owner,bytes(config),(.7+i*.001,.6,1.8+i*.002),i*37


def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;reg=o.reg;shape_count=0;scale_count=0;count=0
    for seed in range(10):
        values=tuple((i-33)*(seed+1)*.1234567 for i in range(66))
        points=tuple(tuple(values[i:i+3]) for i in range(0,66,3))
        for selector in range(8):
            o._reset();cpu.mem_write(o.inputs,struct.pack('<66f',*values))
            stack=cpu.reg_read(reg.UC_X86_REG_ESP);cpu.mem_write(stack,struct.pack('<III',o.stop,selector,o.inputs))
            o._run(0x43a240,o.stop)
            wanted=struct.pack('<66f',*(v for p in customize_body_samples(selector,points) for v in p))
            if bytes(cpu.mem_read(o.inputs,0x108))!=wanted:raise AssertionError(('shape',seed,selector))
            shape_count+=1
    for selector in range(-2,11):
        for initial in ((1.,1.,1.),(.1234567,-.7654321,-0.)):
            o._reset();cpu.mem_write(o.inputs,struct.pack('<3f',*initial))
            stack=cpu.reg_read(reg.UC_X86_REG_ESP);cpu.mem_write(stack,struct.pack('<IiI',o.stop,selector,o.inputs))
            o._run(0x53a150,o.stop)
            if bytes(cpu.mem_read(o.inputs,12))!=struct.pack('<3f',*body_inertia_scales(selector,initial)):
                raise AssertionError(('inertia scales',selector,initial))
            scale_count+=1
    for owner,config,extents,identity in startup_cases():
        image=bytearray(owner);configuration=o.inputs+0x3000;model=o.inputs+0x4000
        struct.pack_into('<I',image,0x1248,model);struct.pack_into('<I',image,0x1c94,configuration)
        expected=prepare_startup_body(image,config,extents,identity,assembly_finalized=True)
        o._reset();cpu.mem_write(o.inputs,bytes(image));cpu.mem_write(configuration,config)
        cpu.mem_write(model+0x4c,struct.pack('<3f',*extents))
        cpu.reg_write(reg.UC_X86_REG_EBX,o.inputs);cpu.mem_write(o.frame+0x10,struct.pack('<I',identity))
        o._run(0x43ab88,0x43acb1,count=50000)
        actual=bytes(cpu.mem_read(o.inputs,0x2000))
        if actual!=expected:
            raise AssertionError(('connected body startup',count,
                [(hex(i),actual[i:i+4].hex(),expected[i:i+4].hex()) for i in range(0,0x2000,4) if actual[i:i+4]!=expected[i:i+4]][:15]))
        count+=1
    return dict(shape_cases=shape_count,inertia_scale_cases=scale_count,connected_startup_body_cases=count,
        maximum_absolute_error=0,scope='complete 0x43a240 and 0x53a150; connected original 0x43ab88..0x43acb1, all owner bytes exact',
        full_model_and_owner_initialization_verified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
