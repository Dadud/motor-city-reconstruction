"""Original controller with connected loads, environment and tire-force stages."""
import argparse
from dataclasses import replace
import json
import struct
from client.body_environment import BodyEnvironment
from client.body_resistance import BodyResistanceState
from client.body_vertical_load import BodyVerticalLoadState
from client.driving_environment import EnvironmentInputs, DrivingEnvironment
from client.wind import WindState
from tools.drafting_oracle import vehicle, encode as encode_draft
from tools.driving_loads_pipeline_oracle import LoadExtension
from tools.driving_pipeline_oracle import verify as verify_pipeline


class EnvironmentExtension(LoadExtension):
    stages = LoadExtension.stages | DrivingEnvironment.stages

    def install(self, oracle, owner, config, interface, query):
        # Support descriptor fixtures occupy +0x8000. Keep complete peer-owner
        # records separate so terrain-query writes cannot corrupt a nearby car.
        self.owner, self.track, self.peer = owner, owner+0x6000, owner+0xc000
        self.actual_wind_queries = 0
        self.environment_calls = 0

    def prepare(self, oracle, owner, config, surfaces, state, inputs, observations, image, data):
        super().prepare(oracle, owner, config, surfaces, state, inputs, observations, image, data)
        p = self.parameters
        wind = WindState(5, -123, (.3, .2, -.7),
            (.8, 0., -.6, 0., 1., 0., .6, 0., .8), observations['resistance_mode'])
        cars = (vehicle(1), vehicle(2, (1., 0., -4.), .1))
        environment = BodyEnvironment(500., False, True, 2, wind, 1, cars)
        body = BodyResistanceState(state.speed, state.local_linear[2], .4, True, True,
            .2, 3, state.secondary_angle, 2.2, 0., 0., 0., 1., False,
            p.suspension_pitch, p.wheelbase, p.height_parameter, False,
            state.front_lever, state.rear_lever, -.3, .2,
            tuple(w.force[1] for w in state.wheels), tuple(w.contact for w in state.wheels))
        vertical = BodyVerticalLoadState(state.speed, state.local_linear[2], 2., 3., .3, -.4,
            .1, -.2, inputs.spin.front_quality, inputs.spin.rear_quality, body.wheel_loads)
        self.environment_inputs = EnvironmentInputs(body, vertical, environment)
        self.actual_wind_queries = 0
        for off, value in ((0x34c, environment.altitude), (0xd38, body.drag_adjustment),
                (0x18c0, body.area_parameter), (0x18f8, body.downforce_parameter),
                (0xd30, vertical.front_adjustment), (0xd34, vertical.rear_adjustment)):
            struct.pack_into('<f', image, off, value)
        struct.pack_into('<9f', image, 0x9c, *wind.world_to_body)
        struct.pack_into('<I', image, 0xf3c, int(body.accessory_enabled))
        struct.pack_into('<h', image, 0x3bc, int(body.load_transfer_disabled))
        for off, value in ((0, body.drag_parameter), (4, vertical.front_parameter),
                (8, vertical.rear_parameter), (0x10, body.configuration_downforce),
                (0x410, vertical.front_speed_parameter), (0x420, vertical.rear_speed_parameter)):
            struct.pack_into('<f', data, off, value)
        struct.pack_into('<I', data, 0xc, int(body.accessory_parameter))
        struct.pack_into('<i', data, 0x48, body.vehicle_code)
        own = encode_draft(cars[0])
        for off, size in ((8, 12), (0x78, 36), (0xcc, 12), (0xb8c, 60)):
            image[off:off+size] = own[off:off+size]
        cpu = oracle.cpu
        cpu.mem_write(self.peer, bytes(encode_draft(cars[1])))
        cpu.mem_write(0x97c38c, struct.pack('<I', self.track))
        cpu.mem_write(self.track+0x18, struct.pack('<3f', *wind.track_direction))
        for address, value in ((0xaa456c, wind.simulation_counter), (0x9aa9ac, wind.weather_seed),
                (0x9aaa78, 0), (0x9aaab8, 2), (0x9aaa5c, int(environment.cold_environment)),
                (0x9aaa60, int(environment.weather_enabled)), (0xb12958, environment.weather_code)):
            cpu.mem_write(address, struct.pack('<i', value))
        cpu.mem_write(0x98c1e8, struct.pack('<II', owner, self.peer))

    def wrap(self, external):
        self.environment_driver = DrivingEnvironment(self.environment_inputs, super().wrap(external))
        return self.environment_driver

    def ready(self, image, data):
        environment = self.environment_inputs.environment
        cars = tuple(replace(car, position=struct.unpack_from('<3f', image, 8),
            basis=struct.unpack_from('<9f', image, 0x78),
            half_extents=struct.unpack_from('<3f', image, 0xcc))
            if car.identifier == environment.current_vehicle else car for car in environment.vehicles)
        self.environment_inputs.environment = replace(environment, vehicles=cars)

    def mode(self, cpu, reg, operation, argument, interface):
        if operation != 1 or argument != 0:
            return False
        if cpu.reg_read(reg.UC_X86_REG_ECX) != interface:
            raise AssertionError('wind query receiver')
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        cpu.reg_write(reg.UC_X86_REG_EAX, int(self.environment_inputs.environment.wind.disabled))
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+12)
        cpu.reg_write(reg.UC_X86_REG_EIP, ret)
        self.actual_wind_queries += 1
        return True

    def check(self, oracle):
        super().check(oracle)
        if self.actual_wind_queries != 1:
            raise AssertionError(('wind query count', self.actual_wind_queries))
        self.actual_wind_queries = 0
        self.environment_calls += 1
        expected = encode_draft(self.environment_inputs.environment.vehicles[1])
        if bytes(oracle.cpu.mem_read(self.peer, len(expected))) != expected:
            raise AssertionError('peer drafting wake state')
        if bytes(oracle.cpu.mem_read(0x98c1e8, 8)) != struct.pack('<II', self.owner, self.peer):
            raise AssertionError('nearby vehicle list mutation')


def verify(executable, actual_support=False):
    extension = EnvironmentExtension()
    result = verify_pipeline(executable, actual_support=actual_support, extension=extension)
    result['environment_calls'] = extension.environment_calls
    result['scope'] = ('original controller with load producers, body vertical loads, actual density/weather/wind/drafting, '
        'six tire-force stages and linear update; '
        + ('actual support prediction with supplied terrain projection; ' if actual_support else 'support prediction supplied; ')
        + 'control/engine/brakes/remaining preparation, mode observations and component delivery supplied; '
        'full owner/configuration and peer wake checked')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('executable')
    p.add_argument('--actual-support', action='store_true')
    args = p.parse_args()
    print(json.dumps(verify(args.executable, args.actual_support)))
