"""Bounded full original tire update; only external virtual operation 5 is supplied."""
import argparse
import itertools
import json
import math
import struct
from dataclasses import replace
from client.tire_update import TireCurves, TireWheel, TireUpdateState, update_tires
from tools.native_oracle import DynoOracle


def cases():
    front = TireCurves(tuple(i*37.25 for i in range(26)), tuple(i*19.5 for i in range(26)), .021)
    rear = TireCurves(tuple((i%5-2)*123.5 for i in range(26)), tuple(i*27.5 for i in range(26)), .033)
    for speed, control, mask, rear_steering, alternate in itertools.product(
            (0, .24999, .25, .25001, 3, 5.9999, 6, 6.0001, 8.94059, 8.9406, 8.94061, -20),
            (-127, -1, 0, 1, 127), range(16), (False, True), (False, True)):
        n = mask + control
        lateral = (-.25, -.249, 0, .249, .25)[n%5]
        modes = ((True,)*4, (False,)*4, (True,False,True,False), (False,True,False,True))[n%4]
        wheels = tuple(TireWheel(.1, .2, (i-1)*.003, (-1 if i%2 else 1)*abs(speed),
            (0, 1000, 4000, 14000)[(i+mask)%4], bool(mask & (1<<i)), .8+i*.05,
            123, 211+i, 321) for i in range(4))
        state = TireUpdateState(wheels, front, rear, control, speed, 1300, 1.2, 1.5, 1.6, 2.7,
            (.001, .08)[mask%2], speed, lateral, .7, (-.3,0,.3)[n%3], .017,
            rear_steering, modes, alternate)
        yield state
    # Exercise steering/slip clamps and near-zero force cutoffs independently
    # of contact masks, using fully loaded wheels and both curve load modes.
    for speed, maximum, body, control, alternate in itertools.product(
            (3,6,20), (.001,.32,1.2), (-1.5,0,1.5), (-127,127), (False,True)):
        wheels=tuple(replace(w,normal_load=4000,contact=True,secondary_angle=0,
                             projected_speed=speed) for w in state.wheels)
        yield replace(state,wheels=wheels,speed=speed,longitudinal_velocity=speed,
            maximum_steering=maximum,body_slip=body,raw_control=control,
            lateral_velocity=0,yaw_rate=0,mode_observations=(True,)*4,alternate_load=alternate)


OWNER_FIELDS = ((0xa2c,'speed'), (0x50,'mass_parameter'), (0x18b8,'front_lever'),
    (0x18bc,'rear_lever'), (0x18b4,'maximum_steering'), (0xa44,'longitudinal_velocity'),
    (0xa3c,'lateral_velocity'), (0xa30,'lateral_acceleration'), (0xa58,'yaw_rate'), (0xbc8,'body_slip'))
WHEEL_FIELDS = ((0,'steering_angle'), (4,'slip_angle'), (8,'secondary_angle'),
    (0x10,'projected_speed'), (0xd4,'normal_load'), (0xf8,'surface_multiplier'),
    (0xd0,'lateral_force'), (0xd8,'longitudinal_force'), (0xe0,'secondary_response'))


def verify(executable):
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable)
    cpu, reg = o.cpu, o.reg
    owner, config = o.inputs, o.inputs+0x3000
    interface, vtable, query = o.inputs+0x4000, o.inputs+0x4100, o.stub+0x100
    cpu.mem_write(interface,struct.pack('<I',vtable))
    cpu.mem_write(vtable+0x10,struct.pack('<I',query))
    cpu.mem_write(0xa65bd0,struct.pack('<I',interface))
    cpu.mem_write(0xaa456c,struct.pack('<i',5))
    observations, calls = [], []
    def mode_query(uc, address, size, data):
        if address != query:
            return
        stack = uc.reg_read(reg.UC_X86_REG_ESP)
        destination, operation, argument = struct.unpack('<III', uc.mem_read(stack, 12))
        if (operation != 5 or argument != owner or len(calls)>=4
                or uc.reg_read(reg.UC_X86_REG_ECX)!=interface):
            raise AssertionError('unexpected mode query arguments/count')
        uc.reg_write(reg.UC_X86_REG_EAX, 4 if observations[len(calls)] else 6)
        calls.append(argument)
        uc.reg_write(reg.UC_X86_REG_ESP, stack+12)
        uc.reg_write(reg.UC_X86_REG_EIP, destination)
    cpu.hook_add(UC_HOOK_CODE, mode_query, begin=query, end=query)
    count, maximum_error = 0, 0.0
    for state in cases():
        o._reset()
        observations[:] = state.mode_observations
        calls.clear()
        image = bytearray([0xa5])*0x1d00
        struct.pack_into('<I', image, 0x1c94, config)
        struct.pack_into('<i', image, 0xa7c, state.raw_control)
        for offset, name in OWNER_FIELDS:
            struct.pack_into('<f', image, offset, getattr(state,name))
        for i, wheel in enumerate(state.wheels):
            base = 0x5fc+i*0x10c
            for offset, name in WHEEL_FIELDS:
                struct.pack_into('<f', image, base+offset, getattr(wheel,name))
            image[base+0xec] = int(wheel.contact)
        configuration = bytearray([0x5a])*0x700
        configuration[0xe4] = int(state.rear_steering)
        for offset, value in ((0x30,state.front_track),(0x2c,state.wheelbase)):
            struct.pack_into('<f', configuration, offset, value)
        for axle, base in ((state.front_curves,0x148),(state.rear_curves,0x24c)):
            struct.pack_into('<f', configuration, base, axle.angle_coefficient)
            struct.pack_into('<26f', configuration, base+8, *axle.primary)
            struct.pack_into('<26f', configuration, base+0x70, *axle.secondary)
        cpu.mem_write(owner,bytes(image))
        cpu.mem_write(config,bytes(configuration))
        cpu.mem_write(0xa384c8,struct.pack('<I',int(state.alternate_load)))
        stack = o.frame-0x1000
        cpu.mem_write(stack,struct.pack('<II',o.stop,owner))
        cpu.reg_write(reg.UC_X86_REG_ESP,stack)
        o._run(0x53ecf0,o.stop,count=100000)
        actual = bytes(cpu.mem_read(owner,len(image)))
        expected = update_tires(state)
        outputs = [(offset,getattr(expected,name),name) for offset,name in OWNER_FIELDS
                   if name in ('yaw_rate','lateral_velocity','lateral_acceleration')]
        for i,wheel in enumerate(expected.wheels):
            outputs.extend((0x5fc+i*0x10c+offset,getattr(wheel,name),f'{i}:{name}')
                for offset,name in WHEEL_FIELDS if name in
                ('steering_angle','slip_angle','lateral_force','longitudinal_force','secondary_response'))
        for offset,value,name in outputs:
            original = struct.unpack_from('<f',actual,offset)[0]
            error = abs(original-value)
            if not math.isfinite(original) or error>max(.00025,abs(original)*3e-7):
                raise AssertionError((count,name,original,value,error,state))
            maximum_error = max(maximum_error,error)
            image[offset:offset+4] = actual[offset:offset+4]
        if (len(calls)!=4 or actual!=image or bytes(cpu.mem_read(config,len(configuration)))!=configuration
                or bytes(cpu.mem_read(0xaa456c,4))!=struct.pack('<i',5)):
            raise AssertionError('unexpected mode count or owner/configuration mutation')
        count += 1
    return {'cases':count,'maximum_absolute_error':maximum_error,
        'scope':'complete 0x53ecf0 with original steering/trigonometry/curves/predicate; only virtual operation 5 supplied'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    print(json.dumps(verify(parser.parse_args().executable)))
