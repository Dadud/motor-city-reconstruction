"""Complete original support predictor, supplied terrain projection observations."""
import argparse
from dataclasses import replace
import itertools
import json
import struct
from client.support_prediction import PredictionWheel,SupportRecord,SupportPredictionState,SupportProjection,predict_support
from client.tire_response import f32
from tools.native_oracle import DynoOracle

def cases():
    for mask,velocity,height,rotation in itertools.product(range(16),(-20.,0.,20.),(-.50001,-.5,-.49999,0.,.5),range(3)):
        matrix=((1.,0.,0.,0.,1.,0.,0.,0.,1.),(.8,0.,-.6,0.,1.,0.,.6,0.,.8),
            (.8,.1,-.6,.07,.99,.03,.6,-.04,.8))[rotation]
        wheels=tuple(PredictionWheel(((-1 if i%2==0 else 1)*.8,.2+i*.03,1.4 if i<2 else -1.5),
            (8.,100.+i,9.),.5,SupportRecord(10,1,7,88,(1,2,3,4),201),9.,True,23) for i in range(4))
        s=SupportPredictionState(wheels,(120.25,height,-90.75),(velocity,-.25,velocity*.7),matrix,
            -17 if rotation==2 else 91,rotation*8,3)
        yield s,(mask,False)
    for rewritten in (False,True):
        s,observation=next(cases());yield replace(s,position=(100000.,-.1,-100000.),velocity=(.01,0.,-.01)),(15,rewritten)

def projection(query,observations):
    mask,rewrite=observations
    slot=query.slot;found=bool(mask&(1<<slot));p=query.point
    # Authored projection fixtures, explicitly not an authentic track service.
    reference=(p[0],f32(p[1]+.125) if rewrite else p[1],p[2])
    point=(p[0],f32(-.3+slot*.1) if found else p[1],p[2])
    record=SupportRecord(query.context,query.context>>3,3+slot,
        100+slot if found else None,(10+slot*4,11+slot*4,12+slot*4,13+slot*4) if found else (None,)*4,
        (0,0xff,0xa6,20)[slot] if found else None)
    return SupportProjection(point,reference,record)

def _address(identity):return 0 if identity is None else 0x71008000+identity*8

def record_bytes(record):
    return struct.pack('<ii6I',record.sector,record.group,record.status,_address(record.surface_id),*map(_address,record.vertex_ids))

def encode(s, *, raw_addresses=False):
    image=bytearray(b'\x5a'*0x2000)
    struct.pack_into('<3f',image,8,*s.position);struct.pack_into('<3f',image,0x14,*s.velocity)
    struct.pack_into('<9f',image,0xc10,*s.to_world)
    struct.pack_into('<i',image,0x370,s.context);struct.pack_into('<I',image,0x404,s.fallback_surface)
    struct.pack_into('<i',image,0xc08,s.support_count)
    for i,w in enumerate(s.wheels):
        base=0x5fc+i*0x10c
        record = (struct.pack('<ii6I',w.record.sector,w.record.group,w.record.status,
                    w.record.surface_id or 0,*(value or 0 for value in w.record.vertex_ids))
                  if raw_addresses else record_bytes(w.record))
        image[base+0x14:base+0x34]=record
        if w.query_tail is not None: image[base+0x40:base+0x58]=w.query_tail
        struct.pack_into('<3f',image,base+0x34,*w.world_point);struct.pack_into('<3f',image,base+0x100,*w.local_point)
        struct.pack_into('<f',image,base+0xb8,w.clear_reference);struct.pack_into('<f',image,base+0xe8,w.support_delta)
        struct.pack_into('<I',image,base+0x58,w.surface_class);image[base+0xec]=int(w.contact)
    return image

def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu=o.cpu;reg=o.reg;owner=o.inputs
    count=0;current=None;s=None;queries=[];maximum=0
    # Select the shipped scalar/x87 vector dispatch, not a replacement helper.
    cpu.mem_write(0x8c4674,b'\0');cpu.mem_write(0x8c465c,b'\0')
    def hook(cpu,address,size,user):
        if address!=0x42e010:return
        stack=cpu.reg_read(reg.UC_X86_REG_ESP);record,point,context=struct.unpack('<IIi',cpu.mem_read(stack+4,12))
        slot=(record-owner-0x610)//0x10c
        if not 0<=slot<4 or record!=owner+0x610+slot*0x10c:raise AssertionError('terrain record target differs')
        from client.support_prediction import SupportQuery
        p=struct.unpack('<3f',cpu.mem_read(point,12));previous=struct.unpack('<3f',cpu.mem_read(record+0x20,12))
        query=SupportQuery(slot,p,context,previous,s.wheels[slot].record,
                           s.wheels[slot].query_tail);queries.append(query)
        result=projection(query,current)
        cpu.mem_write(record,record_bytes(result.record)+struct.pack('<3f',*result.reference_position))
        cpu.mem_write(point,struct.pack('<3f',*result.point))
        if result.record.surface_id is not None:cpu.mem_write(_address(result.record.surface_id)+4,bytes([result.record.surface_code]))
        cpu.reg_write(reg.UC_X86_REG_EAX,int(result.record.surface_id is not None))
        cpu.reg_write(reg.UC_X86_REG_EIP,struct.unpack('<I',cpu.mem_read(stack,4))[0]);cpu.reg_write(reg.UC_X86_REG_ESP,stack+4)
    cpu.hook_add(UC_HOOK_CODE,hook)
    for s,current in cases():
        o._reset();cpu.mem_write(owner,bytes(encode(s)));queries.clear()
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x53d320,o.stop,count=10000)
        out=predict_support(s,lambda q:projection(q,current))
        if queries!=list(out.queries):raise AssertionError(('queries',count,queries,out.queries))
        actual=bytes(cpu.mem_read(owner,0x2000));expected=encode(out.state)
        if actual!=expected:
            off=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
            raise AssertionError(('owner',count,hex(off),actual[off:off+8],expected[off:off+8]))
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
        'scope':'complete original support predictor and original scalar/x87 transform dispatch; terrain projection boundary supplied, exact ordered query points/context and full owner bytes'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');print(json.dumps(verify(p.parse_args().executable)))
