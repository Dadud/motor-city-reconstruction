"""Bounded original torque-to-engagement tail, real environment helper."""
import argparse
from dataclasses import asdict
import itertools
import json
import struct
from client.drivetrain_coupling import DrivetrainCoupling, couple_drivetrain
from tools.native_oracle import DynoOracle


class CouplingOracle(DynoOracle):
    def update(self, state):
        self._reset()
        owner = self.inputs
        before = bytearray(b'\xa5'*0x1d00)
        for offset, value, fmt in ((0xab4,state.rpm,'i'),(0xaa0,state.curve_torque,'f'),
                (0xaa4,state.effective_torque,'f'),(0xb24,state.drag_factor,'f'),
                (0xb6c,state.drag_speed,'f'),(0xb54,state.gear_index,'i'),
                (0xb2c,state.engagement,'f'),(0xb3c,state.coupling_resistance,'f'),
                (0x34c,state.environment_field,'f')):
            struct.pack_into('<'+fmt, before, offset, value)
        self.cpu.mem_write(owner, bytes(before))
        for address, value in ((0x9aaa5c,int(state.environment_override)),
                               (0x9aaa60,int(state.environment_selector_enabled)),
                               (0xb12958,state.environment_selector)):
            self.cpu.mem_write(address, struct.pack('<i',value))
        self.cpu.reg_write(self.reg.UC_X86_REG_ESI,owner)
        self._run(0x547932,0x5479fe,count=10000)
        after = bytes(self.cpu.mem_read(owner,len(before)))
        offsets = {'power':0xaac,'drag':0xb70,'corrected_torque':0xaa4,'acceleration_input':0xaa8}
        expected = bytearray(before)
        result = {}
        for name, offset in offsets.items():
            expected[offset:offset+4] = after[offset:offset+4]
            result[name] = struct.unpack_from('<f',after,offset)[0]
        if expected != after: raise AssertionError('unmodelled coupling owner write')
        return result


def scenarios():
    for rpm, torque, gear, engagement, mode in itertools.product((0,600,3000,6800),
            (-300.,0.,275.), (0,1,2), (-.25,0.,.5,.99999994,1.,1.25),
            ((False,False,2),(False,True,1),(False,True,2),(True,True,0))):
        yield DrivetrainCoupling(rpm,torque,torque,3.25,-2.5,gear,engagement,
                                12.75,1250,*mode)
    for field in (-100000.,-500.,0.,100000.):
        yield DrivetrainCoupling(3000,275,200,2,30,2,.5,10,field,False,False,0)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('executable')
    oracle = CouplingOracle(parser.parse_args().executable)
    maximum, count = 0.,0
    for state in scenarios():
        actual, expected = oracle.update(state), asdict(couple_drivetrain(state))
        for name,value in actual.items():
            error = abs(value-expected[name]); maximum=max(maximum,error)
            if error > max(1e-5,abs(value)*3e-7): raise AssertionError((name,value,expected[name],state))
        count+=1
    print(json.dumps({'cases':count,'maximum_absolute_error':maximum,'replaced_calls':[],
                      'entry':'0x547932','stop_before':'0x5479fe','unmodelled_owner_writes':0}))


if __name__ == '__main__': main()
