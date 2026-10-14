"""Complete bounded original RPM helper comparison, no replaced calls."""
from dataclasses import asdict
import argparse
import itertools
import json
import struct
from client.driving_engine_rpm import DrivingEngineRPM, update_driving_engine_rpm
from tools.native_oracle import DynoOracle


FIELDS = {'throttle': 0xa94, 'normalized_rpm': 0xabc, 'target_rpm': 0xac4,
          'inertia_factor': 0xb28, 'acceleration_input': 0xaa8,
          'angular_speed': 0xab0, 'rpm': 0xab4, 'limiter_rpm': 0xac0,
          'gear_index': 0xb54, 'longitudinal_speed': 0xa44,
          'acceleration_output': 0xab8}
INTS = {'target_rpm', 'rpm', 'limiter_rpm', 'gear_index'}


class DrivingRPMOracle(DynoOracle):
    def update(self, state, minimum):
        self._reset()
        owner, config = self.inputs, self.inputs+0x3000
        before = bytearray(b'\xa5'*0x1d00)
        for name, offset in FIELDS.items():
            struct.pack_into('<i' if name in INTS else '<f', before, offset,
                             getattr(state, name))
        struct.pack_into('<I', before, 0xae4, 1 if state.enabled else 0)
        struct.pack_into('<I', before, 0x1c94, config)
        struct.pack_into('<f', before, 0x1810+state.gear_index*4, state.gear_speed_factor)
        self.cpu.mem_write(owner, bytes(before))
        config_before = bytearray(0x100)
        struct.pack_into('<ii', config_before, 0x6c, state.idle_rpm, state.configured_max_rpm)
        self.cpu.mem_write(config, bytes(config_before))
        stack = self.frame-0x1000
        self.cpu.mem_write(stack, struct.pack('<IIi', self.stop, owner, minimum))
        self._run(0x546e70, self.stop, count=10000)
        after = bytes(self.cpu.mem_read(owner, len(before)))
        changes = {'target_rpm': 0xac4, 'rpm': 0xab4,
                   'angular_speed': 0xab0, 'acceleration_output': 0xab8}
        expected = bytearray(before)
        result = {}
        for name, offset in changes.items():
            expected[offset:offset+4] = after[offset:offset+4]
            result[name] = struct.unpack_from('<i' if name in INTS else '<f', after, offset)[0]
        if bytes(expected) != after:
            raise AssertionError('original RPM helper changed an unmodelled owner field')
        if bytes(self.cpu.mem_read(config,len(config_before))) != bytes(config_before):
            raise AssertionError('original RPM helper changed its read-only configuration')
        return result


def scenarios():
    for enabled, normalized, throttle, acceleration, rpm, gear, speed in itertools.product(
            (False, True), (0., .5, 1., 1.2), (-.1, 0., .5, 1.),
            (-120., 0., 150.), (500, 3000, 6500), (0, 1, 2), (-30., 0., 30.)):
        yield DrivingEngineRPM(600, 7000, throttle, normalized, 2400, enabled,
                               .7, acceleration, rpm*.10471976, rpm, 6800,
                               gear, -170.25 if gear == 0 else 175.5, speed), 600


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable')
    args = parser.parse_args()
    oracle = DrivingRPMOracle(args.executable)
    count, errors = 0, {name: 0. for name in ('angular_speed', 'acceleration_output')}
    for state, minimum in scenarios():
        actual = oracle.update(state, minimum)
        expected = asdict(update_driving_engine_rpm(state, minimum))
        for name, value in actual.items():
            error = abs(value-expected[name])
            if name in INTS and error:
                raise AssertionError((name, value, expected[name], state))
            if name not in INTS:
                errors[name] = max(errors[name], error)
                if error > max(1e-5, abs(value)*3e-7):
                    raise AssertionError((name, value, expected[name], state))
        count += 1
    print(json.dumps({'entry': '0x546e70', 'cases': count, 'maximum_error': errors,
                      'replaced_calls': [], 'unmodelled_owner_writes': 0}))


if __name__ == '__main__':
    main()
