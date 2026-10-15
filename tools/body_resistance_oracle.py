"""Full 0x536480 comparison with supplied density, wind and drafting producers."""
import argparse
import itertools
import json
import math
import struct
from dataclasses import replace
from client.air_density import calculate_air_density
from client.body_resistance import BodyResistanceState,calculate_body_resistance
from client.wind import WindState,calculate_wind
from client.drafting import calculate_drafting
from client.body_environment import BodyEnvironment,calculate_body_environment
from tools.drafting_oracle import vehicle,encode as encode_draft
from tools.native_oracle import DynoOracle


def cases():
    for speed,code,angle,mask,disabled,transfer in itertools.product(
            (-20,0,20),(-1,3,4,6),(-.3,0,.3),(0,5,15),(False,True),(False,True)):
        yield BodyResistanceState(speed,-1 if mask==0 else 0,.4,mask!=0,mask!=5,.2,code,angle,
            2.2,1.225,-4 if code==3 else 4,3,.75,disabled,.03,2,.7,transfer,1.2,1.5,
            -.3,.2,(-100,100,1000,2000),tuple(bool(mask&(1<<i)) for i in range(4)))


OWNER_FIELDS=((0xa2c,'speed'),(0xa44,'longitudinal_speed'),(0xd38,'drag_adjustment'),(0xbc8,'secondary_angle'),
    (0x18c0,'area_parameter'),(0xbf4,'pitch_angle'),(0x18b8,'front_lever'),(0x18bc,'rear_lever'),(0x18f8,'downforce_parameter'))
CONFIG_FIELDS=((0,'drag_parameter'),(0x2c,'length_parameter'),(0x38,'height_parameter'),(0x10,'configuration_downforce'))


def connected_cases():
    """Same owner cases with recovered altitude/weather density handoff."""
    for count,s in enumerate(cases()):
        altitude=(-500,0,500,2000,5499)[count%5]
        cold,enabled=bool(count%2),bool((count//2)%2)
        weather=(count//4)%4
        yield replace(s,density=calculate_air_density(altitude,cold,enabled,weather)),altitude,cold,enabled,weather


def environment_case(count,state):
    """Authentic producer shapes with explicit observed track/mode/vehicle data."""
    own=vehicle(1)
    peer=vehicle(2,((-1.,0.,2.)[count%3],0.,(-8.,-4.,4.,8.)[count%4]),(.0,.1,.3)[count%3])
    wind=WindState(count*37-4096,count-123,(.3,.2,-.7),
                   (1.,0.,0.,0.,1.,0.,0.,0.,1.),count%3==0)
    result=calculate_wind(wind)
    draft=calculate_drafting(1,(own,peer))
    return replace(state,wind_lateral=result.body_velocity[0],wind_longitudinal=result.body_velocity[2],
                   drafting_factor=draft.factor),wind,(own,peer),draft


def verify(executable, actual_density=False, actual_environment=False):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner,config,values=o.inputs,o.inputs+0x3000,o.inputs+0x5000
    track,interface,vtable,peer_address=o.inputs+0x6000,o.inputs+0x7000,o.inputs+0x7100,o.inputs+0x8000
    query=o.stub+0x300
    if actual_environment:
        actual_density=True
        cpu.mem_write(interface,struct.pack('<I',vtable));cpu.mem_write(vtable+0x10,struct.pack('<I',query))
        cpu.mem_write(0xa65bd0,struct.pack('<I',interface));cpu.mem_write(0x97c38c,struct.pack('<I',track))
        cpu.mem_write(0x9aaa78,struct.pack('<i',0))
    density_stub,draft_stub,wind_stub=o.stub+0x200,o.stub+0x220,o.stub+0x240
    cpu.mem_write(density_stub,b'\xd9\x05'+struct.pack('<I',values)+b'\xc3')
    cpu.mem_write(draft_stub,b'\xd9\x05'+struct.pack('<I',values+4)+b'\xc3')
    cpu.mem_write(wind_stub,b'\xc3')
    calls=[];query_calls=[];wind=None
    def mode(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        ret,operation,argument=struct.unpack('<III',cpu.mem_read(stack,12))
        if operation!=1 or argument!=0 or cpu.reg_read(reg.UC_X86_REG_ECX)!=interface:
            raise AssertionError('environment mode query arguments')
        query_calls.append((operation,argument))
        cpu.reg_write(reg.UC_X86_REG_EAX,int(wind.disabled));cpu.reg_write(reg.UC_X86_REG_ESP,stack+12)
        cpu.reg_write(reg.UC_X86_REG_EIP,ret)
    if actual_environment:cpu.hook_add(UC_HOOK_CODE,mode,begin=query,end=query)
    def supply(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        if address==0x536fb0:
            ret,out,argument=struct.unpack('<III',cpu.mem_read(stack,12))
            if argument!=owner: raise AssertionError('wind receiver')
            if actual_environment:
                calls.append(address);return
            wx,wz=struct.unpack('<ff',cpu.mem_read(values+8,8))
            cpu.mem_write(out,struct.pack('<fff',wx,0,wz));target=wind_stub
        else:
            ret,argument=struct.unpack('<II',cpu.mem_read(stack,8))
            if argument!=owner: raise AssertionError('producer receiver')
            target=density_stub if address==0x535ed0 else draft_stub
        calls.append(address)
        if not actual_environment and not (actual_density and address==0x535ed0): cpu.reg_write(reg.UC_X86_REG_EIP,target)
    for address in (0x535ed0,0x536fb0,0x536960): cpu.hook_add(UC_HOOK_CODE,supply,begin=address,end=address)
    maximum,count=0.0,0
    corpus=connected_cases() if actual_density else ((s,None,None,None,None) for s in cases())
    for s,altitude,cold,enabled,weather in corpus:
        o._reset();calls.clear();query_calls.clear()
        image,configuration=bytearray([0xa5])*0x1d00,bytearray([0x5a])*0x500
        if actual_density:
            struct.pack_into('<f',image,0x34c,altitude)
            for address,value in ((0x9aaa5c,int(cold)),(0x9aaa60,int(enabled)),(0xb12958,weather)):
                cpu.mem_write(address,struct.pack('<I',value))
        if actual_environment:
            s,wind,cars,draft=environment_case(count,s)
            source=encode_draft(cars[0])
            for offset,size in ((8,12),(0x78,36),(0xcc,12),(0xb8c,60)):
                image[offset:offset+size]=source[offset:offset+size]
            struct.pack_into('<9f',image,0x9c,*wind.world_to_body)
            cpu.mem_write(peer_address,bytes(encode_draft(cars[1])))
            cpu.mem_write(track+0x18,struct.pack('<3f',*wind.track_direction))
            cpu.mem_write(0xaa456c,struct.pack('<i',wind.simulation_counter))
            cpu.mem_write(0x9aa9ac,struct.pack('<i',wind.weather_seed))
            cpu.mem_write(0x9aaab8,struct.pack('<i',2))
            cpu.mem_write(0x98c1e8,struct.pack('<II',owner,peer_address))
        struct.pack_into('<I',image,0x1c94,config)
        for off,name in OWNER_FIELDS: struct.pack_into('<f',image,off,getattr(s,name))
        for off,name in CONFIG_FIELDS: struct.pack_into('<f',configuration,off,getattr(s,name))
        struct.pack_into('<I',configuration,0xc,int(s.accessory_parameter))
        struct.pack_into('<i',configuration,0x48,s.vehicle_code)
        struct.pack_into('<I',image,0xf3c,int(s.accessory_enabled))
        struct.pack_into('<I',image,0x474,0x200 if s.resistance_disabled else 0)
        struct.pack_into('<h',image,0x3bc,int(s.load_transfer_disabled))
        offsets=(0x6d0,0x7dc,0x8e8,0x9f4)
        for off,value,contact in zip(offsets,s.wheel_loads,s.contacts):
            struct.pack_into('<f',image,off,value);image[off+0x18]=int(contact)
        cpu.mem_write(owner,bytes(image));cpu.mem_write(config,bytes(configuration))
        cpu.mem_write(values,struct.pack('<4f',s.density,s.drafting_factor,s.wind_lateral,s.wind_longitudinal))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x536480,o.stop,count=20000)
        actual=bytes(cpu.mem_read(owner,len(image)))
        expected=(calculate_body_environment(s,BodyEnvironment(altitude,cold,enabled,weather,wind,1,cars)).body
                  if actual_environment else calculate_body_resistance(s))
        targets=(expected.longitudinal_drag,expected.yaw_contribution,expected.pitch_contribution,*expected.wheel_loads)
        for off,target in zip((0xbd4,0xbcc,0xbd8,*offsets),targets):
            value=struct.unpack_from('<f',actual,off)[0];error=abs(value-target)
            if not math.isfinite(value) or error>max(.0005,abs(value)*3e-7): raise AssertionError((count,hex(off),value,target,s))
            maximum=max(maximum,error);image[off:off+4]=actual[off:off+4]
        if actual!=image or bytes(cpu.mem_read(config,len(configuration)))!=configuration: raise AssertionError('unexpected writes')
        if actual_environment:
            if bytes(cpu.mem_read(peer_address,0x1d00))!=encode_draft(draft.vehicles[1]):
                raise AssertionError('connected wake geometry writes')
            if query_calls!=[(1,0)] or bytes(cpu.mem_read(0x98c1e8,8))!=struct.pack('<II',owner,peer_address):
                raise AssertionError('connected environment query or vehicle list')
        if calls!=[0x535ed0,0x536fb0,0x536960]: raise AssertionError('producer call order')
        count+=1
    scope=('complete536480 with actual density/weather/wind/drafting and all numeric helpers; only virtual mode query supplied'
           if actual_environment else 'complete0x536480 and actual535ed0/594030/69a630 density/weather/floor, actual sine; wind/drafting supplied'
           if actual_density else 'complete0x536480 numeric stage, actual sine; density/wind/drafting producers supplied')
    return {'cases':count,'maximum_absolute_error':maximum,'scope':scope}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable');p.add_argument('--actual-density',action='store_true')
    p.add_argument('--actual-environment',action='store_true')
    args=p.parse_args();print(json.dumps(verify(args.executable,args.actual_density,args.actual_environment)))
