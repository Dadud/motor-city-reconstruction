"""Native/Python connected density, wind, drafting and body-resistance handoffs."""
import argparse
from dataclasses import fields
import json
import math
import subprocess
from client.body_environment import BodyEnvironment, calculate_body_environment
from tools.body_resistance_oracle import connected_cases, environment_case
from tools.native_drafting_compare import flatten


def verify(runner):
    lines, expected = [], []
    for index, (state, altitude, cold, enabled, weather) in enumerate(connected_cases()):
        _, wind, cars, _ = environment_case(index, state)
        environment = BodyEnvironment(altitude, cold, enabled, weather, wind, 1, cars)
        values = [getattr(state, field.name) for field in fields(state)
                  if field.name not in ('wheel_loads', 'contacts')]
        values.extend((*state.wheel_loads, *state.contacts, altitude, cold, enabled, weather,
                       wind.simulation_counter, wind.weather_seed, *wind.track_direction,
                       *wind.world_to_body, wind.disabled, 1, len(cars)))
        values.extend(v for car in cars for v in flatten(car))
        lines.append(' '.join(format(int(v) if isinstance(v, bool) else v, '.17g') for v in values))
        out = calculate_body_environment(state, environment)
        expected.append((out.body.longitudinal_drag, out.body.yaw_contribution, out.body.pitch_contribution,
            *out.body.wheel_loads, out.density, *out.wind.body_velocity, int(out.wind.present),
            out.drafting.factor, -1 if out.drafting.selected_vehicle is None else out.drafting.selected_vehicle,
            int(out.drafting.inside_wake), *(v for car in out.drafting.vehicles for v in flatten(car))))
    result = subprocess.run([str(runner)], input='\n'.join(lines)+'\n', capture_output=True,
                            text=True, check=True, timeout=30)
    output = result.stdout.splitlines()
    if len(output) != len(expected):
        raise AssertionError('environment output count differs')
    maximum = 0.
    for index, (line, target) in enumerate(zip(output, expected)):
        actual = tuple(map(float, line.split()))
        if len(actual) != len(target) or any(actual[i] != target[i] for i in (11, 13, 14)):
            raise AssertionError(('environment output shape or branch differs', index, actual, target))
        for offset, (a, b) in enumerate(zip(actual, target)):
            error = abs(a-b)
            if not math.isfinite(a) or error > max(.0005 if offset < 7 else 3e-6, abs(b)*4e-7):
                raise AssertionError((index, offset, a, b, error))
            maximum = max(maximum, error)
    return {'cases': len(expected), 'maximum_absolute_error': maximum,
            'scope': 'native/Python connected environment, resistance outputs and complete drafting state'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner)))
