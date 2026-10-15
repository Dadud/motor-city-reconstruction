"""Actual controller load production connected to six actual force stages."""
import argparse
from dataclasses import replace
import json
import struct
from client.driving_loads import DrivingLoads, LoadParameters
from tools.driving_pipeline_oracle import cases as force_cases, verify as verify_pipeline


class LoadExtension:
    stages = DrivingLoads.stages

    def __init__(self):
        self.parameters = None
        self.mode_value = False
        self.actual_modes = 0
        self.expected_modes = 0
        self.mode_queries = 0

    def cases(self):
        for index, (state, inputs, observations) in enumerate(force_cases()):
            inputs.moments = replace(inputs.moments, wheels=tuple(replace(w,
                support_correction=9.8+i*.1) for i, w in enumerate(inputs.moments.wheels)))
            observations['load_parameters'] = LoadParameters(1300., 2.7, 1.6, 1.7, .7,
                -.03 if index % 2 else .03, .05, -.06, 100., .45, .55,
                -2.3, -400. if index % 3 else 400., index % 2, 1.2, .8)
            observations['resistance_mode'] = bool(index % 3 == 1)
            yield state, inputs, observations

    def install(self, oracle, owner, config, interface, query):
        pass

    def prepare(self, oracle, owner, config, surfaces, state, inputs, observations, image, data):
        self.parameters = observations['load_parameters']
        self.mode_value = observations['resistance_mode']
        self.actual_modes = self.expected_modes = 0
        p = self.parameters
        for off, value in ((0xc00, p.pitch), (0xc04, p.bank), (0xbf4, p.suspension_pitch), (0xaa0, p.torque)):
            struct.pack_into('<f', image, off, value)
        for off, value in ((0x20, p.configuration_mass), (0x28, p.mass_offset), (0x2c, p.wheelbase),
                (0x30, p.front_track), (0x34, p.rear_track), (0x38, p.height_parameter),
                (0x104, p.front_weight_parameter), (0xfc, p.rear_weight_parameter),
                (0x334+4*inputs.spin.direction_mode, p.gear_factor),
                (0x13c, p.front_resistance), (0x240, p.rear_resistance)):
            struct.pack_into('<f', data, off, value)
        struct.pack_into('<i', data, 0x6ec, p.component_mode)

    def wrap(self, external):
        def mode(state, inputs, parameters):
            self.expected_modes += 1
            return self.mode_value
        return DrivingLoads(self.parameters, external, mode)

    def ready(self, image, data):
        """Final initialization hook, after optional support-record setup."""
        pass

    def nested(self, cpu, reg, stage, ret):
        if stage == 'global_mode' and 0x53e3d0 <= ret < 0x53e680:
            self.actual_modes += 1
            stack = cpu.reg_read(reg.UC_X86_REG_ESP)
            cpu.reg_write(reg.UC_X86_REG_EAX, int(self.mode_value))
            cpu.reg_write(reg.UC_X86_REG_ESP, stack+4)
            cpu.reg_write(reg.UC_X86_REG_EIP, ret)

    def mode(self, cpu, reg, operation, argument, interface):
        return False

    def expected(self, image, state, inputs):
        pass

    def float_offsets(self):
        return ()

    def check(self, oracle):
        if self.actual_modes != self.expected_modes:
            raise AssertionError(('resistance predicate count', self.actual_modes, self.expected_modes))
        self.mode_queries += self.actual_modes
        self.actual_modes = self.expected_modes = 0


def verify(executable, actual_support=False):
    extension = LoadExtension()
    result = verify_pipeline(executable, actual_support=actual_support, extension=extension)
    result['resistance_mode_queries'] = extension.mode_queries
    result['scope'] = ('actual original controller plus normal loads, wheel-speed projection, acceleration load transfer, '
        'suspension load correction, rolling resistance, six force stages and linear update; '
        + ('actual support prediction with supplied terrain projection; ' if actual_support else '')
        + 'remaining children, mode observations and component delivery supplied; full owner/configuration checked')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--actual-support', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.actual_support)))
