"""Complete original part bounding calls on authored and external FCE geometry."""
import argparse
import json
import struct
from pathlib import Path
from client.fce import HEADER,Part,decode
from client.model_bounds import transformed_part_bounds
from tools.native_oracle import DynoOracle


def authored_cases():
    for origin in ((0.,0.,0.),(-0.,-0.,-0.),(.1234567,-.7654321,2.345678),(-3.,.5,-.25)):
        for vertices in ((),((1.,2.,3.),),((-1.,0.,3.),(2.,-3.,4.),(.1234567,.7654321,-2.345678)),
                ((0.,0.,0.),(-0.,-0.,-0.))):
            yield Part('authored',origin,vertices,(),())


def fixture(part):
    image=bytearray(HEADER+len(part.vertices)*12)
    struct.pack_into('<I',image,0x11c,1);struct.pack_into('<3f',image,0x120,*part.origin)
    struct.pack_into('<I',image,0x520,len(part.vertices))
    for index,point in enumerate(part.vertices):struct.pack_into('<3f',image,HEADER+index*12,*point)
    return bytes(image)


def verify(executable,game=None):
    records=[(fixture(p),0,p) for p in authored_cases()];actual=0
    if game:
        from client.assets import Assets
        from client.catalogue import Catalogue
        from tools.viv import read_member
        assets=Assets(game);catalogue=Catalogue.load(assets.paths['data/db/online.mdb'])
        seen=set()
        for vehicle in range(101,109):
            name=catalogue.vehicle(vehicle).body_filename.casefold()
            if name in seen:continue
            seen.add(name);data=read_member(assets.paths[f'data/models/{name}.viv'],'part.fce')
            for index,part in enumerate(decode(data).parts):records.append((data,index,part));actual+=1
    o=DynoOracle(executable);cpu=o.cpu;base=0x73000000;cpu.mem_map(base,0x1000000);count=0
    for data,index,part in records:
        if len(data)>0x1000000:raise ValueError('oracle model limit')
        cpu.mem_write(base,data)
        for mirrored in (False,True):
            o._reset();cpu.mem_write(o.inputs,bytes([0x35])*24)
            stack=cpu.reg_read(o.reg.UC_X86_REG_ESP)
            cpu.mem_write(stack,struct.pack('<6I',o.stop,base,index,o.inputs,o.inputs+12,0x40 if mirrored else 0))
            o._run(0x4c3e50,o.stop,count=1000000)
            expected=transformed_part_bounds(part,mirrored=mirrored)
            status=cpu.reg_read(o.reg.UC_X86_REG_EAX)
            if status!=int(expected is not None):raise AssertionError((count,'status'))
            observed=bytes(cpu.mem_read(o.inputs,24))
            wanted=bytes([0x35])*24 if expected is None else struct.pack('<6f',*expected.minimum,*expected.maximum)
            if observed!=wanted:raise AssertionError((count,'bounds',observed.hex(),wanted.hex()))
            count+=1
    return dict(cases=count,external_parts=actual,maximum_absolute_error=0,
        scope='complete original 0x4c3e50, both mirror modes, full output/status; no caller selection/scaling/centering',
        full_model_startup_verified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable',type=Path)
    p.add_argument('--game',type=Path);a=p.parse_args();print(json.dumps(verify(a.executable,a.game)))
