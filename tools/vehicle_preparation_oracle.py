"""Bounded full preparation/support routines; all original numeric helpers execute."""
import argparse
from dataclasses import replace
import itertools
import json
import math
import struct
from client.vehicle_preparation import PreparationState,SupportState,SupportWheel,prepare_vehicle,update_support_disturbance
from tools.native_oracle import DynoOracle

SCALARS={0xa38:'local_vertical_acceleration',0xd28:'front_observation',0xd2c:'rear_observation',
  0xcc:'pitch_extent',0xd4:'roll_extent',0x88:'orientation_scale',0x7c:'pitch_reference',0x94:'roll_reference',
  0x18fc:'minimum_pitch',0x1900:'maximum_pitch',0x1904:'maximum_roll',0x18f4:'pitch_offset',
  0xbf4:'pitch',0xbf8:'roll',0xbfc:'extent',0xc0c:'damping',0xc00:'pitch_target',0xc04:'roll_target'}
CONFIG={0x108:'front_factor',0x10c:'rear_factor',0x11c:'pitch_limit',0x120:'roll_limit'}
VECTORS={0x328:'source_vector',0x78:'source_matrix',0x9c:'motion_matrix',0xc58:'angle_delta',
  0xc64:'auxiliary',0xc10:'to_world',0xc34:'to_local'}
OUTPUTS=tuple([0xc0c,0xc00,0xc04,0xbf4,0xbf8,0xbfc]+[0xc58+i*4 for i in range(9)]+[0xc10+i*4 for i in range(18)])

def preparation_cases():
    for n,(support,accel,scale,old) in enumerate(itertools.product(range(5),(-3.,0.,4.),(-.5,0.,.5,1.,1.5),(-.2,0.,.2))):
        matrix=(.8,.1,0.,-.1,scale,.3,0.,-.3,.9)
        yield PreparationState(local_vertical_acceleration=accel,front_observation=.4,rear_observation=2.5,
            front_factor=1.3,rear_factor=.7,support_count=support,pitch_extent=1.2,roll_extent=.7,
            pitch_limit=.2,roll_limit=.3,orientation_scale=scale,pitch_reference=.1,roll_reference=-.3,
            minimum_pitch=.06,maximum_pitch=.08,maximum_roll=.09,pitch_offset=.013,
            pitch=old,roll=-old*.7,extent=old*.3,source_vector=(.02+n*.001,.2,-.3),
            source_matrix=matrix,motion_matrix=(.8,0.,-.6,0.,1.,0.,.6,0.,.8),
            pitch_target=9.,roll_target=-9.,auxiliary=(1.,2.,3.,4.,5.,6.))
    for pitch,roll in itertools.product((-.060001,-.06,0.,.08,.080001),(-.090001,-.09,0.,.09,.090001)):
        yield replace(next(preparation_cases()),pitch=pitch,roll=roll)
    # Precision regression: reloading +0xc58 rather than retaining ST(0)
    # changes the final pitch by one float32 ULP.
    yield replace(next(preparation_cases()),pitch=-.0020816968753933907,
        orientation_scale=1.,roll_reference=-1.,
        source_matrix=(.8,.1,0.,-.1,1.,.3,0.,-1.,.9))

def support_cases():
    noise=tuple((i*73+29)&255 for i in range(256))
    for phase,speed,mask in itertools.product((-.5,-.25,0.,.125,.25,.5,128.,256.),(-20.,0.,20.),range(16)):
        yield SupportState(tuple(SupportWheel(bool(mask&(1<<i)),200+i*100,.15+i*.05,
            1+i*.25,(-1 if i%2 else 1)*.7,9.) for i in range(4)),phase,speed,noise)

def encode(s,config):
    image=bytearray(b'\x5a'*0x2000)
    for off,name in VECTORS.items():struct.pack_into('<'+'f'*len(getattr(s,name)),image,off,*getattr(s,name))
    for off,name in SCALARS.items():struct.pack_into('<f',image,off,getattr(s,name))
    struct.pack_into('<i',image,0xc08,s.support_count);struct.pack_into('<I',image,0x1c94,config)
    return image

def check(actual,expected,positions,label):
    maximum=0
    for off in positions:
        a,b=struct.unpack_from('<f',actual,off)[0],struct.unpack_from('<f',expected,off)[0]
        error=abs(a-b)
        if not math.isfinite(a) or error>max(3e-6,abs(a)*4e-7):raise AssertionError((label,hex(off),a,b,error))
        maximum=max(maximum,error);expected[off:off+4]=actual[off:off+4]
    if actual!=expected:
        off=next(i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b)
        raise AssertionError((label,'unexpected mutation',hex(off),actual[off:off+8],expected[off:off+8]))
    return maximum

def verify(executable):
    o=DynoOracle(executable);cpu=o.cpu;owner=o.inputs;config=owner+0x3000
    maximum=0;counts=[0,0]
    for s in preparation_cases():
        o._reset();image=encode(s,config);cpu.mem_write(owner,bytes(image))
        configuration=bytearray(b'\x6b'*0x400)
        for off,name in CONFIG.items():struct.pack_into('<f',configuration,off,getattr(s,name))
        cpu.mem_write(config,bytes(configuration))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(o.reg.UC_X86_REG_ESP,stack)
        o._run(0x54ebe0,o.stop,count=10000)
        actual=bytes(cpu.mem_read(owner,len(image)));expected=encode(prepare_vehicle(s),config)
        maximum=max(maximum,check(actual,expected,OUTPUTS,('preparation',counts[0])))
        if bytes(cpu.mem_read(config,len(configuration)))!=configuration:raise AssertionError('configuration modified')
        counts[0]+=1
    for s in support_cases():
        o._reset();image=bytearray(b'\x5a'*0x2000)
        struct.pack_into('<f',image,0x5f8,s.phase);struct.pack_into('<f',image,0xa44,s.local_longitudinal_speed)
        for i,w in enumerate(s.wheels):
            start=0x5fc+i*0x10c
            struct.pack_into('<i',image,start+0x58,i);image[start+0xec]=int(w.contact)
            for off,v in ((0xb8,w.bound_parameter),(0xf0,w.displacement),(0x74,w.correction)):struct.pack_into('<f',image,start+off,v)
            cpu.mem_write(0x97c238+8*i,struct.pack('<ff',w.amplitude,w.frequency))
        cpu.mem_write(0x890724,bytes(s.noise));cpu.mem_write(owner,bytes(image))
        stack=o.frame-0x1000;cpu.mem_write(stack,struct.pack('<II',o.stop,owner));cpu.reg_write(o.reg.UC_X86_REG_ESP,stack)
        o._run(0x427da0,o.stop,count=10000)
        expected=image[:];output=update_support_disturbance(s);positions=[]
        for i,w in enumerate(output.wheels):
            for off,v in ((0xf0,w.displacement),(0x74,w.correction)):
                pos=0x5fc+i*0x10c+off;positions.append(pos);struct.pack_into('<f',expected,pos,v)
        maximum=max(maximum,check(bytes(cpu.mem_read(owner,len(image))),expected,positions,('support',counts[1])))
        if bytes(cpu.mem_read(0x890724,256))!=bytes(s.noise):raise AssertionError('lookup table modified')
        counts[1]+=1
    return {'preparation_cases':counts[0],'support_cases':counts[1],'maximum_absolute_error':maximum,
        'scope':'complete original functions and numeric helpers; owner configuration/contact/surface coefficients/noise table supplied; full owner-byte checks'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('executable')
    print(json.dumps(verify(p.parse_args().executable)))
