"""Original controls, loads and environment feeding the full force controller."""
import argparse
import json
import struct
from client.control_update import ControlState
from client.driving_controls import DrivingControls
from tools.control_update_oracle import BYTES, FLOATS, INTS, Executor
from tools.driving_environment_oracle import EnvironmentExtension
from tools.driving_pipeline_oracle import verify as verify_pipeline


class ControlExtension(EnvironmentExtension):
    stages = EnvironmentExtension.stages | DrivingControls.stages

    def install(self, oracle, owner, config, interface, query):
        super().install(oracle, owner, config, interface, query)
        from unicorn import UC_HOOK_CODE
        self.control_actions = []
        self.queries = (False, False, True)
        hooks = {0x548670: 'remote_controls', 0x548b70: 'assisted_gears',
                 0x548e30: 'manual_gears', 0x584fc0: 'stopped_query', 0x4400d0: 'trace_controls'}
        def hook(cpu, address, size, user):
            stage = hooks[address]
            stack = cpu.reg_read(oracle.reg.UC_X86_REG_ESP)
            ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
            values = ()
            if stage == 'trace_controls':
                if struct.unpack('<5I', cpu.mem_read(stack+4, 20)) != (14, 1, 0, 4, 0x89878c):
                    raise AssertionError('control trace prefix')
                values = struct.unpack('<dd', cpu.mem_read(stack+24, 16))
            elif struct.unpack('<I', cpu.mem_read(stack+4, 4))[0] != owner:
                raise AssertionError('control child receiver')
            self.control_actions.append((stage, values))
            if stage == 'remote_controls':
                cpu.mem_write(owner+0xa60, bytes([240]))
                cpu.mem_write(owner+0xa78, struct.pack('<i', 80))
            if stage in ('manual_gears', 'assisted_gears'):
                cpu.mem_write(owner+0xa69, bytes([3]))
                cpu.mem_write(owner+0xa67, bytes([128]))
            cpu.reg_write(oracle.reg.UC_X86_REG_EAX, int(self.queries[0]) if stage=='stopped_query' else 0)
            cpu.reg_write(oracle.reg.UC_X86_REG_ESP, stack+4)
            cpu.reg_write(oracle.reg.UC_X86_REG_EIP, ret)
        for address in hooks:
            oracle.cpu.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)

    def prepare(self, oracle, owner, config, surfaces, state, inputs, observations, image, data):
        super().prepare(oracle, owner, config, surfaces, state, inputs, observations, image, data)
        self.control_actions.clear()
        control = ControlState(target_throttle=210, target_brake=10, target_steering=-127,
            throttle=80, brake=20, steering=inputs.tire.raw_control, local_player=True,
            steering_return_rate=7.5, steering_attack_rate=8.5, flags=0xa5, throttle_output=.5)
        self.control = control
        for off, name in BYTES.items(): image[off] = int(getattr(control, name))
        for off, name in FLOATS.items(): struct.pack_into('<f', image, off, getattr(control, name))
        for off, name in INTS.items(): struct.pack_into('<I', image, off, getattr(control, name)&0xffffffff)
        struct.pack_into('<I', image, 0x464, 1)
        # The supplied gear service selects gear 3. Its two observed tables are
        # explicit inputs, not assumed gearbox mechanics.
        struct.pack_into('<f', image, 0x183c, inputs.spin.gear_multiplier)
        struct.pack_into('<f', data, 0x340, self.parameters.gear_factor)
        struct.pack_into('<f', data, 0xf0, control.steering_return_rate)
        struct.pack_into('<f', data, 0xf4, control.steering_attack_rate)
        struct.pack_into('<I', data, 0x68c, int(control.assisted_gears))
        for address, value in ((0x9aa9a0, 1), (0x9abb0c, control.steering_setting),
                (0x9abb10, control.throttle_setting), (0x9abb14, control.brake_setting),
                (0x9abb18, control.brake_limit), (0xa38494, int(control.new_steering_mode))):
            oracle.cpu.mem_write(address, struct.pack('<I', value&0xffffffff))

    def wrap(self, external):
        # Engine/brake producers remain supplied in this corpus. The retained
        # control view owns their shared output/flag observations for byte checks.
        self.control_driver = DrivingControls(self.control, Executor(self.queries),
            super().wrap(external), lambda *args: None)
        return self.control_driver

    def nested(self, cpu, reg, stage, ret):
        if stage == 'vehicle_gate' and (0x540fd0 <= ret < 0x541400 or 0x541880 <= ret < 0x541930):
            self.control_actions.append(('vehicle_gate', ()))
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.reg_write(reg.UC_X86_REG_EAX, int(self.queries[2]))
            cpu.reg_write(reg.UC_X86_REG_ESP, stack+4)
            cpu.reg_write(reg.UC_X86_REG_EIP, ret)
        else:
            super().nested(cpu, reg, stage, ret)

    def expected(self, image, state, inputs):
        c = self.control_driver.controls
        for off, name in BYTES.items(): image[off] = int(getattr(c, name))
        for off, name in FLOATS.items(): struct.pack_into('<f', image, off, getattr(c, name))
        for off, name in INTS.items(): struct.pack_into('<I', image, off, getattr(c, name)&0xffffffff)

    def float_offsets(self):
        return tuple(FLOATS)

    def check(self, oracle):
        super().check(oracle)
        expected = [(c.stage, c.values) for c in self.control_driver.calls]
        if self.control_actions != expected:
            raise AssertionError(('nested control calls', self.control_actions, expected))
        self.control_actions.clear()


def verify(executable, actual_support=False):
    result = verify_pipeline(executable, actual_support=actual_support, extension=ControlExtension())
    result['scope'] = ('original controller with actual input smoothing, load producers, environment, '
        'six force stages and linear update; '
        + ('actual support prediction with supplied terrain projection; ' if actual_support else 'support prediction supplied; ')
        + 'gear/remote services, queries, engine/brakes/remaining preparation and component delivery supplied; '
        'complete owner/configuration and peer wake checked')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    p.add_argument('--actual-support', action='store_true')
    args = p.parse_args()
    print(json.dumps(verify(args.executable, args.actual_support)))
