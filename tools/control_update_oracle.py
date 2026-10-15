"""Full original control routine; remote/gear child effects and external queries supplied."""
import argparse
from dataclasses import replace
import itertools
import json
import struct
from client.control_update import ControlState,update_controls
from tools.native_oracle import DynoOracle

BYTES={0xa60:'target_throttle',0xa61:'target_brake',0xa62:'target_gear',0xa63:'smooth_throttle',
    0xa64:'smooth_steering',0xa65:'smooth_brake',0xa66:'throttle',0xa67:'brake',0xa69:'output_gear',
    0xa6a:'auxiliary_control',0xa6b:'reverse_control',0xa6c:'slow_steering',0xa87:'emergency'}
FLOATS={0xa8c:'steering_output',0xa90:'brake_output',0xa94:'throttle_output'}
INTS={0xa78:'target_steering',0xa7c:'steering',0xae4:'flags'}

def cases():
    for mode,smooth,local,target,old in itertools.product((False,True),(False,True),(False,True),
            (-127,-1,0,1,127),(-127,-97,-96,-65,-64,-33,-32,-1,0,1,32,33,64,65,96,97,127)):
        n=old+127
        yield ControlState(target_throttle=(0,31,32,33,127,255)[n%6],throttle=(0,30,32,127,224,255)[n%6],
            target_brake=(0,64,192,255)[n%4],brake=(192,0,255,64)[n%4],
            smooth_throttle=smooth,smooth_brake=smooth,smooth_steering=smooth,target_steering=target,steering=old,
            local_player=local,new_steering_mode=mode,steering_setting=(0,128,256,0xffffffff)[n%4],
            throttle_setting=(0,1,128,256)[n%4],brake_setting=(0,128,256,0xffffffff)[n%4],
            brake_limit=(0,80,255,300)[n%4],steering_return_rate=7.5,steering_attack_rate=8.5,
            flags=0xa5,throttle_output=.5,assisted_gears=bool(n%2)),(False,False,True)
    for difference,old,mode,slow in itertools.product((-33,-32,-31,-2,-1,0,1,2,31,32,33),(64,128,192),(False,True),(0,1)):
        yield ControlState(target_throttle=old+difference,throttle=old,target_brake=255,brake=80,
            target_steering=0,steering=-40,slow_steering=slow,new_steering_mode=mode), (False,False,True)
    for emergency,stopped,override,gate,remote in itertools.product((False,True),repeat=5):
        yield ControlState(target_throttle=100,throttle=200,target_brake=200,brake=100,
            target_steering=-20,steering=20,emergency=emergency,remote_controls=remote), (stopped,override,gate)

class Executor:
    def __init__(self,observations):self.observations=observations
    def __call__(self,call,s):
        if call.stage=='remote_controls':s.target_throttle=240;s.target_steering=80
        if call.stage in ('manual_gears','assisted_gears'):
            s.output_gear=3;s.brake=128
        if call.stage=='stopped_query':return self.observations[0]
        if call.stage=='override_query':return self.observations[1]
        if call.stage=='vehicle_gate':return self.observations[2]

def encode(s,config):
    image=bytearray(b'\x5a'*0x2000)
    for off,name in BYTES.items():image[off]=int(getattr(s,name))
    for off,name in FLOATS.items():struct.pack_into('<f',image,off,getattr(s,name))
    for off,name in INTS.items():struct.pack_into('<I',image,off,getattr(s,name)&0xffffffff)
    struct.pack_into('<I',image,0x474,0x200 if s.remote_controls else 0)
    struct.pack_into('<I',image,0x464,1 if s.local_player else 2)
    struct.pack_into('<I',image,0x1c94,config)
    return image

def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu=o.cpu;reg=o.reg;owner=o.inputs;config=owner+0x3000
    virtual=o.stub+0x200;object=owner+0x4000;vtable=object+0x100
    cpu.mem_write(0xa65bd0,struct.pack('<I',object));cpu.mem_write(object,struct.pack('<I',vtable));cpu.mem_write(vtable+0x10,struct.pack('<I',virtual))
    hooks={0x548670:'remote_controls',0x548b70:'assisted_gears',0x548e30:'manual_gears',
        0x584fc0:'stopped_query',0x55cfc0:'vehicle_gate',virtual:'override_query',0x4400d0:'trace_controls'}
    actual_calls=[];actual_boundaries=[];current=None;maximum=0
    def hook(cpu,address,size,user):
        if address not in hooks:return
        stage=hooks[address];stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        values=()
        if stage=='override_query':
            operation,receiver=struct.unpack('<II',cpu.mem_read(stack+4,8))
            if operation!=1 or receiver!=owner or cpu.reg_read(reg.UC_X86_REG_ECX)!=object:raise AssertionError('virtual query receiver/arguments differ')
            values=(1,)
        elif stage=='trace_controls':
            prefix=struct.unpack('<5I',cpu.mem_read(stack+4,20))
            if prefix!=(14,1,0,4,0x89878c):raise AssertionError('trace prefix differs')
            values=struct.unpack('<dd',cpu.mem_read(stack+24,16))
        elif struct.unpack('<I',cpu.mem_read(stack+4,4))[0]!=owner:raise AssertionError('child owner differs')
        actual_calls.append((stage,values))
        actual_boundaries.append(bytes(cpu.mem_read(owner,0x2000)))
        if stage=='remote_controls':
            cpu.mem_write(owner+0xa60,bytes([240]));cpu.mem_write(owner+0xa78,struct.pack('<i',80))
        if stage in ('manual_gears','assisted_gears'):
            cpu.mem_write(owner+0xa69,bytes([3]));cpu.mem_write(owner+0xa67,bytes([128]))
        query={'stopped_query':0,'override_query':1,'vehicle_gate':2}.get(stage)
        cpu.reg_write(reg.UC_X86_REG_EAX,int(current[query]) if query is not None else 0)
        target=struct.unpack('<I',cpu.mem_read(stack,4))[0]
        cpu.reg_write(reg.UC_X86_REG_ESP,stack+4+(8 if stage=='override_query' else 0));cpu.reg_write(reg.UC_X86_REG_EIP,target)
    cpu.hook_add(UC_HOOK_CODE,hook)
    count=0
    for s,current in cases():
        o._reset();image=encode(s,config);cpu.mem_write(owner,bytes(image))
        configuration=bytearray(b'\x6b'*0x800)
        struct.pack_into('<f',configuration,0xf0,s.steering_return_rate);struct.pack_into('<f',configuration,0xf4,s.steering_attack_rate)
        struct.pack_into('<I',configuration,0x68c,int(s.assisted_gears));cpu.mem_write(config,bytes(configuration))
        for address,value in ((0x9aa9a0,1),(0x9abb0c,s.steering_setting),(0x9abb10,s.throttle_setting),(0x9abb14,s.brake_setting),(0x9abb18,s.brake_limit),(0xa38494,int(s.new_steering_mode))):
            cpu.mem_write(address,struct.pack('<I',value&0xffffffff))
        actual_calls.clear();actual_boundaries.clear();stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x540fd0,o.stop,count=10000)
        boundary_index=0;driver=Executor(current)
        def execute(call,state):
            nonlocal boundary_index
            expected_boundary=encode(state,config)
            if actual_boundaries[boundary_index]!=expected_boundary:
                original=actual_boundaries[boundary_index]
                off=next(i for i,(a,b) in enumerate(zip(original,expected_boundary)) if a!=b)
                raise AssertionError(('child boundary owner',count,call.stage,hex(off),original[off:off+8],expected_boundary[off:off+8]))
            boundary_index+=1
            return driver(call,state)
        out=update_controls(s,execute);expected=encode(out.state,config)
        if actual_calls!=[(x.stage,x.values) for x in out.calls]:raise AssertionError(('calls',count,actual_calls,out.calls))
        actual=bytes(cpu.mem_read(owner,len(image)))
        for off in FLOATS:
            a,b=struct.unpack_from('<f',actual,off)[0],struct.unpack_from('<f',expected,off)[0]
            if a!=b:raise AssertionError(('float',count,hex(off),a,b))
            maximum=max(maximum,abs(a-b))
        if actual!=expected:
            off=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b);raise AssertionError(('owner',count,hex(off),s,actual[off:off+8],expected[off:off+8]))
        if bytes(cpu.mem_read(config,len(configuration)))!=configuration:raise AssertionError('configuration modified')
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,'scope':'complete control owner arithmetic, original rate/steering/override helpers; external queries, remote and gear child effects and trace delivery supplied; exact calls and full owner/config bytes'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
