"""Complete combined-slip and wear-dispatch comparisons against original code."""
import argparse
import itertools
import json
import math
import struct
from client.combined_slip import CombinedSlipState,CombinedSlipWheel,limit_combined_slip,SlipEffect
from tools.native_oracle import DynoOracle


def cases():
    for slip,force,speed,parking,alternate,mask in itertools.product(
            (-2,-1,-.200001,-.2,-.05000001,-.05,0,.15,.150001,1,8,8.0001),
            (-5000,0,5000),(-20,1,1.0001),(False,True),(False,True),(0,5,15)):
        wheels=tuple(CombinedSlipWheel(slip+(i-1)*.000001,(i-1)*force,force*(i-1),111+i*17,
            0 if i==0 else 1000+i*100,.7+i*.1,.5+i*.1,(i-1)*30,.25+i*.1,
            speed,bool(mask&(1<<i)),(0,6,20,1)[i],1) for i in range(4))
        yield CombinedSlipState(wheels,speed,parking,alternate,.2,.4,0)


FIELDS=((0xc,'slip_ratio'),(0xd0,'lateral_force'),(0xd8,'longitudinal_force'),(0xe0,'secondary_response'),
    (0xd4,'normal_load'),(0x5c,'primary_coefficient'),(0x60,'secondary_coefficient'),
    (0x7c,'spin_value'),(0xbc,'spin_scale'),(0x10,'projected_speed'))


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o=DynoOracle(executable);cpu,reg=o.cpu,o.reg
    owner=o.inputs;events=[];current=[]
    update_return=o.stub+0x400;secondary_return=o.stub+0x410
    cpu.mem_write(update_return,b'\xd9\xee\xc2\x14\x00');cpu.mem_write(secondary_return,b'\xc2\x08\x00')
    def observe(cpu,address,size,user):
        stack=cpu.reg_read(reg.UC_X86_REG_ESP)
        if address==0x53fe40:
            ret,argument,slot,loss=struct.unpack('<IIif',cpu.mem_read(stack,16))
            if argument!=owner or not 0<=slot<4:raise AssertionError('unexpected loss helper arguments')
            current[:]=[slot]
        elif address in (0x591500,0x591180):
            if cpu.reg_read(reg.UC_X86_REG_ECX)!=owner+0xcc8:raise AssertionError('unexpected component receiver')
            ret,operation,amount=struct.unpack('<IIf',cpu.mem_read(stack,12))
            if operation!=(1 if current[0]<2 else 2):raise AssertionError('unexpected component operation')
            if address==0x591500:
                a,b,c=struct.unpack('<3f',cpu.mem_read(stack+12,12))
                events.append(SlipEffect(0,current[0],amount,a,b,c));cpu.reg_write(reg.UC_X86_REG_EIP,update_return)
            else:
                events.append(SlipEffect(1,current[0],amount));cpu.reg_write(reg.UC_X86_REG_EIP,secondary_return)
    for address in (0x53fe40,0x591500,0x591180):cpu.hook_add(UC_HOOK_CODE,observe,begin=address,end=address)
    count,maximum=0,0.0
    for s in cases():
        o._reset();events.clear();current.clear();image=bytearray([0xa5])*0x1d00
        for off,value in ((0xa2c,s.speed),(0xd00,s.front_quality),(0xd04,s.rear_quality)):
            struct.pack_into('<f',image,off,value)
        image[0xa6b]=int(s.parking_control);struct.pack_into('<i',image,0x354,s.vehicle_code)
        for i,w in enumerate(s.wheels):
            start=0x5fc+i*0x10c
            for off,name in FIELDS:struct.pack_into('<f',image,start+off,getattr(w,name))
            image[start+0xec]=int(w.contact)
            struct.pack_into('<i',image,start+0x58,w.component_code);struct.pack_into('<i',image,start+0xc8,w.wear_mode)
        cpu.mem_write(owner,bytes(image));cpu.mem_write(0xa384c8,struct.pack('<I',int(s.alternate_mode)))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x53fb30,o.stop,count=100000)
        actual=bytes(cpu.mem_read(owner,len(image)));expected,expected_events=limit_combined_slip(s)
        for i,w in enumerate(expected.wheels):
            for off,name in ((0xd0,'lateral_force'),(0xd8,'longitudinal_force'),(0xe0,'secondary_response')):
                pos=0x5fc+i*0x10c+off;value=struct.unpack_from('<f',actual,pos)[0];target=getattr(w,name);error=abs(value-target)
                if not math.isfinite(value) or error>max(.0005,abs(value)*3e-7):raise AssertionError((count,i,name,value,target,error,s))
                maximum=max(maximum,error);image[pos:pos+4]=actual[pos:pos+4]
        if actual!=image:raise AssertionError('unexpected owner writes')
        if tuple(events)!=expected_events:raise AssertionError((count,events,expected_events))
        count+=1
    return {'cases':count,'maximum_absolute_error':maximum,
        'scope':'complete0x53fb30 with actual slip curve/sqrt/53fe40; component update and secondary effect delivery supplied'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
