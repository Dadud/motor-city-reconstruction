"""Full original controller with six actual connected force stages and linear update.

Unrecovered child stages and service/component delivery are explicit supplied
observations. This validates shared-state adapters, not stock initialization.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import itertools
import json
import math
import struct

from client.body_moments import BodyMomentState, MomentWheel
from client.driving_pipeline import DrivingForces, ForceInputs
from client.driving_support import DrivingSupport
from client.support_prediction import SupportQuery
from client.vehicle_update import update_vehicle, apply_linear_update
from client.wheel_spin import SpinWheel, WheelSpinState
from client.tire_response import f32
from tools.native_oracle import DynoOracle
from tools.tire_update_oracle import cases as tire_cases
from tools.vehicle_update_oracle import (cases as controller_cases, encode, STAGES,
    SCALARS, VECTORS, WHEEL_SCALARS, SuppliedStages)
from tools.wheel_spin_oracle import WHEEL_FIELDS as SPIN_FIELDS
from tools.support_prediction_oracle import (cases as support_cases, projection,
    encode as encode_support, record_bytes, _address)


def cases():
    base = next(s for s, _, branch in controller_cases()
                if branch == 'supported' and all(w.contact for w in s.wheels))
    tire_base = next(tire_cases())
    for speed, mask, gates, orientation, clear in itertools.product(
            (.25, 3., 20.), (3, 5, 15), itertools.product((False, True), repeat=2),
            (False, True), (False, True)):
        s = deepcopy(base)
        s.mass = 1300.; s.inverse_mass = 1/1300.; s.angular_scale = .003
        s.linear_velocity = (.2, -.1, speed); s.local_linear = (.2, .7, speed)
        s.angular_velocity = (.02, -.03, .04); s.orientation_disabled = orientation
        s.support_count = mask.bit_count(); s.maximum_steering = .08
        for i, w in enumerate(s.wheels):
            w.contact = bool(mask & (1 << i)); w.force = (123., 2000.+500*i, 211.+i)
            w.projected_speed = speed; w.spin = (i-1)*3.; w.spin_scale = .25+i*.1
            w.phase = .125; w.primary_angle = .1; w.local_lateral = .1*i
            w.clear_reference = .5; w.clear_threshold = -.6 if clear and i == 1 else -.4
        tire = replace(tire_base, raw_control=127, wheels=tuple(replace(w,
            contact=s.wheels[i].contact, normal_load=s.wheels[i].force[1], projected_speed=speed,
            surface_multiplier=s.wheels[i].quality, secondary_response=321.)
            for i, w in enumerate(tire_base.wheels)), front_track=1.6, wheelbase=2.7,
            rear_steering=False, mode_observations=(True,)*4)
        spin = WheelSpinState(tuple(SpinWheel(w.spin, 25-i*20., w.spin_scale, w.projected_speed,
            w.force[1], 1+i*.1, .5+i*.1, w.phase, True, w.contact,
            secondary_angle=(i-1)*.003, local_lateral=w.local_lateral)
            for i, w in enumerate(s.wheels)), 2, False, 3000, .002,
            .3, .35, .02, .03, -2., 3., .7, .8, .05, 1.2, 1.5, .03, .2)
        moments = BodyMomentState(tuple(MomentWheel(w.force[0], w.force[2], 321.,
            (i-1)*.2, w.contact) for i, w in enumerate(s.wheels)), speed,
            1.2, 1.5, 1.6, 1.7, .7, 1300., .003, .002, .004, .8, 300., 400., 53., orientation)
        inputs = ForceInputs(tire, spin, moments, 1., 0., True, .3, -.2)
        observations = dict(global_mode=(0,)*5, vehicle_gate=gates, airborne_mode=0,
            followup_enabled=True, followup_ready=True, steering_angle=.03125,
            grip_observation=.6, execute_linear=True, linear_gate=not clear)
        observations['component_mutation'] = clear and mask == 15
        yield s, inputs, observations


def initialize(s, inputs, owner, config, surfaces):
    image = encode(s, owner, surfaces)
    data = bytearray([0x5a])*0x700
    struct.pack_into('<I', image, 0x1c94, config)
    struct.pack_into('<i', image, 0xa7c, inputs.tire.raw_control)
    image[0xa6b] = int(inputs.parking_control); image[0xa69] = inputs.spin.direction_mode
    image[0xa88] = int(inputs.spin.override_control)
    struct.pack_into('<i', image, 0xab4, inputs.spin.rpm)
    struct.pack_into('<f', image, 0x1830+4*inputs.spin.direction_mode, inputs.spin.gear_multiplier)
    for off, value in ((0xd08, inputs.orientation_front), (0xd0c, inputs.orientation_rear),
            (0x18e4, inputs.moments.inverse_yaw), (0x18e8, inputs.moments.inverse_roll),
            (0xc0c, inputs.moments.pitch_multiplier), (0x18ec, inputs.spin.front_scale),
            (0x18f0, inputs.spin.rear_scale), (0xd18, inputs.spin.front_quality),
            (0xd1c, inputs.spin.rear_quality), (0xbf8, inputs.spin.body_secondary_angle),
            (0xa90, inputs.service_control), (0xa94, inputs.other_control)):
        struct.pack_into('<f', image, off, value)
    for i, w in enumerate(inputs.spin.wheels):
        start = 0x5fc+i*0x10c
        for off, name in SPIN_FIELDS:
            if off not in (0x7c, 0xbc, 0x10, 0xd4, 0xf4, 0x64):
                struct.pack_into('<f', image, start+off, getattr(w, name))
        struct.pack_into('<f', image, start+4, inputs.tire.wheels[i].slip_angle)
        struct.pack_into('<f', image, start+0xe0, inputs.tire.wheels[i].secondary_response)
        struct.pack_into('<f', image, start+0x74, inputs.moments.wheels[i].support_correction)
        image[start+0xc5] = int(w.correction_enabled)
    for off, value in ((0x20, inputs.moments.mass_parameter), (0x2c, inputs.tire.wheelbase),
            (0x30, inputs.tire.front_track), (0x34, inputs.moments.rear_track),
            (0x38, inputs.moments.height_parameter), (0x14c, inputs.spin.front_compliance),
            (0x250, inputs.spin.rear_compliance), (0x138, inputs.spin.front_secondary_angle),
            (0x23c, inputs.spin.rear_secondary_angle)):
        struct.pack_into('<f', data, off, value)
    data[0xe4] = int(inputs.tire.rear_steering)
    for axle, off in ((inputs.tire.front_curves, 0x148), (inputs.tire.rear_curves, 0x24c)):
        struct.pack_into('<f', data, off, axle.angle_coefficient)
        struct.pack_into('<26f', data, off+8, *axle.primary)
        struct.pack_into('<26f', data, off+0x70, *axle.secondary)
    return image, data


def expected_image(previous, state, inputs, owner, surfaces):
    target = bytearray(previous)
    view = encode(state, owner, surfaces)
    spans = [(4, 2), *((off, 4) for off in SCALARS),
             *((off, len(getattr(state, name))*4) for off, name in VECTORS.items()),
             *((off, 4) for off in (0x474, 0x354, 0x404, 0xc08))]
    for i in range(4):
        start = 0x5fc+i*0x10c
        spans.extend((start+off, size) for off, size in
            (*((off, 4) for off in WHEEL_SCALARS), (0xec, 1), (0xd0, 12),
             (0xc8, 4), (0xcc, 4), (0x20, 4)))
    for off, size in spans:
        target[off:off+size] = view[off:off+size]
    for i in range(4):
        start = 0x5fc+i*0x10c
        struct.pack_into('<f', target, start+4, inputs.tire.wheels[i].slip_angle)
        struct.pack_into('<f', target, start+0xe0, inputs.tire.wheels[i].secondary_response)
        for off, name in SPIN_FIELDS:
            if off not in (0x7c, 0xbc, 0x10, 0xd4, 0xf4, 0x64):
                struct.pack_into('<f', target, start+off, getattr(inputs.spin.wheels[i], name))
    return target


def verify(executable, actual_support=False, extension=None):
    """Compare the controller; optional research extension binds more children.

    Extension methods prepare/install/wrap/expected/check/nested/mode supply
    subsystem-specific memory and observations. Runtime executors remain separate.
    """
    from unicorn import UC_HOOK_CODE
    o = DynoOracle(executable); cpu, reg = o.cpu, o.reg
    owner, config, interface, vtable, surfaces = (o.inputs+off for off in (0, 0x3000, 0x4000, 0x4100, 0x5000))
    query, float_return, value_address = o.stub+0x100, o.stub+0x200, o.inputs+0x4200
    component_return, secondary_return = o.stub+0x400, o.stub+0x410
    cpu.mem_write(interface, struct.pack('<I', vtable)); cpu.mem_write(vtable+0x10, struct.pack('<I', query))
    cpu.mem_write(0xa65bd0, struct.pack('<I', interface)); cpu.mem_write(0xaa456c, struct.pack('<i', 5))
    cpu.mem_write(float_return, b'\xd9\x05'+struct.pack('<I', value_address)+b'\xc3')
    cpu.mem_write(component_return, b'\xd9\xee\xc2\x14\x00'); cpu.mem_write(secondary_return, b'\xc2\x08\x00')
    actual_calls, actual_effects, query_calls, projection_queries = [], [], [], []
    driver = None; current_stage = None; effect_mutated = False
    actual_stages = DrivingForces.stages | {'linear_update'}
    if extension is not None:
        actual_stages = actual_stages | extension.stages
        extension.install(o, owner, config, interface, query)
    if actual_support:
        actual_stages = actual_stages | {'predict_support'}
        cpu.mem_write(0x8c4674, b'\0'); cpu.mem_write(0x8c465c, b'\0')
    def child(cpu, address, size, user):
        nonlocal current_stage
        stage = STAGES[address]
        stack = cpu.reg_read(reg.UC_X86_REG_ESP); ret = struct.unpack('<I', cpu.mem_read(stack, 4))[0]
        internal = stage == 'vehicle_gate' and 0x540c30 <= ret < 0x540f00
        # The tire stage calls the same query and steering helpers internally.
        # Their real bodies must run; only direct controller children are supplied.
        if not internal and not 0x53c140 <= ret < 0x53d320:
            if extension is not None:
                extension.nested(cpu, reg, stage, ret)
            return
        slot = None
        if stage not in ('global_mode', 'followup_enabled', 'followup_ready'):
            if struct.unpack('<I', cpu.mem_read(stack+4, 4))[0] != owner:
                raise AssertionError(('child receiver', stage))
            if stage == 'grip_observation': slot = struct.unpack('<I', cpu.mem_read(stack+8, 4))[0]
        if not internal:
            actual_calls.append((stage, slot)); current_stage = stage
        if stage in actual_stages:
            return
        try:
            value = driver.observations['linear_gate'] if internal else driver.result(stage)
        except IndexError as error:
            raise AssertionError((stage, hex(ret), driver.counts, actual_calls)) from error
        if stage in ('steering_angle', 'grip_observation', 'engine'):
            cpu.mem_write(value_address, struct.pack('<f', value)); cpu.reg_write(reg.UC_X86_REG_EIP, float_return)
        else:
            cpu.reg_write(reg.UC_X86_REG_EAX, int(value)); cpu.reg_write(reg.UC_X86_REG_ESP, stack+4)
            cpu.reg_write(reg.UC_X86_REG_EIP, ret)
    for address in STAGES: cpu.hook_add(UC_HOOK_CODE, child, begin=address, end=address)
    def mode(cpu, address, size, user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        ret, operation, argument = struct.unpack('<III', cpu.mem_read(stack, 12))
        if extension is not None and extension.mode(cpu, reg, operation, argument, interface):
            return
        if operation not in (5, 16) or argument != owner or cpu.reg_read(reg.UC_X86_REG_ECX) != interface:
            raise AssertionError('tire mode query arguments')
        if operation == 16:
            actual_calls.append(('airborne_mode', None)); value = driver.result('airborne_mode')
        else:
            query_calls.append((operation, argument)); value = 4
        cpu.reg_write(reg.UC_X86_REG_EAX, value)
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+12); cpu.reg_write(reg.UC_X86_REG_EIP, ret)
    cpu.hook_add(UC_HOOK_CODE, mode, begin=query, end=query)
    support_observations = None
    def terrain(cpu, address, size, user):
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        record, point, context = struct.unpack('<IIi', cpu.mem_read(stack+4, 12))
        slot = (record-owner-0x610)//0x10c
        if not 0 <= slot < 4 or record != owner+0x610+slot*0x10c:
            raise AssertionError('terrain projection receiver')
        p = struct.unpack('<3f', cpu.mem_read(point, 12))
        previous = struct.unpack('<3f', cpu.mem_read(record+0x20, 12))
        query_value = SupportQuery(slot, p, context, previous)
        projection_queries.append(query_value)
        result = projection(query_value, support_observations)
        cpu.mem_write(record, record_bytes(result.record)+struct.pack('<3f', *result.reference_position))
        cpu.mem_write(point, struct.pack('<3f', *result.point))
        if result.record.surface_id is not None:
            cpu.mem_write(_address(result.record.surface_id)+4, bytes([result.record.surface_code]))
        cpu.reg_write(reg.UC_X86_REG_EAX, int(result.record.surface_id is not None))
        cpu.reg_write(reg.UC_X86_REG_EIP, struct.unpack('<I', cpu.mem_read(stack, 4))[0])
        cpu.reg_write(reg.UC_X86_REG_ESP, stack+4)
    if actual_support:
        cpu.hook_add(UC_HOOK_CODE, terrain, begin=0x42e010, end=0x42e010)
    def effect(cpu, address, size, user):
        nonlocal effect_mutated
        if extension is not None and getattr(extension, 'effect', lambda *args: False)(cpu, reg, address):
            return
        stack = cpu.reg_read(reg.UC_X86_REG_ESP)
        _, operation, amount = struct.unpack('<IIf', cpu.mem_read(stack, 12))
        if cpu.reg_read(reg.UC_X86_REG_ECX) != owner+0xcc8 or operation not in (1, 2):
            raise AssertionError('component receiver or axle operation')
        if address == 0x591500:
            a, b, c = struct.unpack('<3f', cpu.mem_read(stack+12, 12)); kind = 0; target = component_return
        else: a, b, c, kind, target = 0., 0., 0., 1, secondary_return
        actual_effects.append((current_stage, kind, operation, amount, a, b, c))
        if current_stage == 'wheel_spin' and driver.observations['component_mutation'] and not effect_mutated:
            cpu.mem_write(owner+0x5fc+0xd0, struct.pack('<3f', .125, 333., -.375))
            effect_mutated = True
        cpu.reg_write(reg.UC_X86_REG_EIP, target)
    for address in (0x591500, 0x591180): cpu.hook_add(UC_HOOK_CODE, effect, begin=address, end=address)
    count, ticks, maximum, event_maximum, stage_total, mutation_ticks = 0, 0, 0., 0., 0, 0
    branches = {}; projection_count = 0; radius_error = 0.; conditioned_effect_error = 0.
    corpus = cases() if extension is None else extension.cases()
    for state, inputs, observations in corpus:
        image, data = initialize(state, inputs, owner, config, surfaces)
        if extension is not None:
            extension.prepare(o, owner, config, surfaces, state, inputs, observations, image, data)
        prediction = None
        if actual_support:
            prediction, _ = next(support_cases())
            prediction = replace(prediction, position=(120.25, .5, -90.75),
                velocity=state.linear_velocity, to_world=state.to_world,
                fallback_surface=state.fallback_surface)
            support_observations = (sum(1 << i for i, w in enumerate(state.wheels) if w.contact),
                                    observations['component_mutation'])
            support_image = encode_support(prediction)
            for off, size in ((8, 12), (0x370, 4)):
                image[off:off+size] = support_image[off:off+size]
            for i, wheel in enumerate(prediction.wheels):
                start = 0x5fc+i*0x10c
                for off, size in ((0x14, 32), (0x34, 12), (0x100, 12)):
                    image[start+off:start+off+size] = support_image[start+off:start+off+size]
                state.wheels[i].surface_record = wheel.record.surface_code
                cpu.mem_write(_address(wheel.record.surface_id)+4, bytes([wheel.record.surface_code]))
        if extension is not None:
            extension.ready(image, data)
        cpu.mem_write(owner, bytes(image)); cpu.mem_write(config, bytes(data))
        cpu.mem_write(0xa384c8, struct.pack('<I', int(state.orientation_disabled)))
        cpu.mem_write(0xa65bce, bytes([int(state.grip_boost)]))
        for i, w in enumerate(state.wheels): cpu.mem_write(surfaces+i*16+4, bytes([w.surface_record or 0]))
        for i, coefficient in enumerate(state.surface_coefficients): cpu.mem_write(0x89bf70+i*8, struct.pack('<f', coefficient))
        expected_effects = []; expected_effect_slots = []
        py_driver = None
        def external(call, s, supplied): return py_driver(call, s)
        def effects(kind, events, s, supplied):
            if kind == 'wheel_spin':
                expected_effects.extend((kind, 0, 1 if slot < 2 else 2, amount, 0., 1., .25) for slot, amount in events)
                expected_effect_slots.extend(slot for slot, amount in events)
                if events and observations['component_mutation']:
                    s.wheels[0].force = (.125, 333., -.375)
            else:
                expected_effects.extend((kind, e.operation, 1 if e.slot < 2 else 2, e.amount,
                                        e.parameter_a, e.parameter_b, e.parameter_c) for e in events)
                expected_effect_slots.extend(e.slot for e in events)
        support = None
        python_projection_queries = []
        def py_project(query_value):
            python_projection_queries.append(query_value)
            return projection(query_value, support_observations)
        if actual_support:
            support = DrivingSupport(prediction, py_project, external)
        pipeline = DrivingForces(inputs, support if support is not None else external, effects)
        if extension is not None:
            pipeline.external = extension.wrap(pipeline.external)
        for tick in range(2):
            o._reset(); actual_calls.clear(); actual_effects.clear(); query_calls.clear(); expected_effects.clear();expected_effect_slots.clear()
            projection_queries.clear(); python_projection_queries.clear()
            effect_mutated = False
            driver = SuppliedStages(observations); py_driver = SuppliedStages(observations)
            stack = o.frame-0x1000; cpu.mem_write(stack, struct.pack('<II', o.stop, owner))
            cpu.reg_write(reg.UC_X86_REG_ESP, stack); o._run(0x53c140, o.stop, count=250000)
            result = update_vehicle(state, pipeline)
            expected_calls = [(c.stage, c.slot) for c in result.calls]
            if result.branch not in ('supported', 'low_support') or actual_calls != expected_calls:
                raise AssertionError((count, tick, 'controller calls', actual_calls, expected_calls))
            if len(actual_effects) != len(expected_effects):
                raise AssertionError((count, tick, 'ordered component effects', actual_effects, expected_effects))
            for event, expected_event, slot in zip(actual_effects, expected_effects, expected_effect_slots):
                if event[:3] != expected_event[:3]:
                    raise AssertionError((count, tick, 'component delivery order', event, expected_event))
                for argument, (a, b) in enumerate(zip(event[3:], expected_event[3:])):
                    error = abs(a-b)
                    if (event[:2]==('combined_slip',1) and argument==0 and math.isfinite(a)
                            and error>max(3e-10,abs(a)*4e-7)
                            and getattr(extension,'conditioned_secondary',lambda *args:False)(slot,a,b)):
                        conditioned_effect_error=max(conditioned_effect_error,error)
                        continue
                    if not math.isfinite(a) or error > max(3e-10, abs(a)*4e-7):
                        raise AssertionError((count, tick, 'component argument', event, expected_event,
                            getattr(extension,'failure_detail',lambda:None)()))
                    event_maximum = max(event_maximum, error)
            if len(query_calls) != (4 if result.branch == 'supported' else 0):
                raise AssertionError(('tire mode observation count differs', count, tick,
                    result.branch, len(query_calls), actual_calls))
            target = expected_image(image, result.state, pipeline.inputs, owner, surfaces)
            if extension is not None:
                extension.expected(target, result.state, pipeline.inputs)
            if actual_support:
                if projection_queries != python_projection_queries or len(projection_queries) != 4:
                    raise AssertionError((count, tick, 'support query points/context/order', projection_queries,
                                          python_projection_queries))
                support_image = encode_support(support.prediction)
                for i in range(4):
                    start = 0x5fc+i*0x10c
                    for off, size in ((0x14, 32), (0x34, 12), (0x100, 12)):
                        target[start+off:start+off+size] = support_image[start+off:start+off+size]
                projection_count += len(projection_queries)
            actual = bytes(cpu.mem_read(owner, len(image)))
            positions = set(SCALARS)
            if extension is not None:
                positions.update(extension.float_offsets())
            for off, name in VECTORS.items(): positions.update(off+4*i for i in range(len(getattr(state, name))))
            for i in range(4):
                start = 0x5fc+i*0x10c
                positions.update(start+off for off, name in WHEEL_SCALARS.items() if name != 'surface_class')
                positions.update(start+off for off, _ in SPIN_FIELDS)
                positions.update(start+off for off in (4, 0xd0, 0xd4, 0xd8, 0xe0))
            for off in positions:
                a, b = struct.unpack_from('<f', actual, off)[0], struct.unpack_from('<f', target, off)[0]
                error = abs(a-b)
                if off in (0xbe8, 0xbec) and error > max(.0005, abs(a)*4e-7):
                    # Reciprocal yaw near zero amplifies tiny, already checked
                    # carried angular differences. Verify each controller's
                    # radius exactly against ITS input motion, rather than
                    # relaxing tolerances on any simulated force or velocity.
                    axis = 1 if off == 0xbe8 else 0
                    previous_angular = struct.unpack_from('<3f', image, 0x38)[axis]
                    previous_forward = struct.unpack_from('<f', image, 0x1c)[0]
                    def radius(forward, angular):
                        return 4000000. if angular == 0 else f32(forward/(angular*f32(6.2831855)))
                    if a == radius(previous_forward, previous_angular) and b == radius(state.linear_velocity[2], state.angular_velocity[axis]):
                        radius_error = max(radius_error, error)
                        target[off:off+4] = actual[off:off+4]
                        continue
                if not math.isfinite(a) or error > max(.0005, abs(a)*4e-7):
                    raise AssertionError((count, tick, hex(off), a, b, error, observations,
                        'prior motion', struct.unpack_from('<3f',image,0x14), state.linear_velocity,
                        struct.unpack_from('<3f',image,0x38), state.angular_velocity))
                maximum = max(maximum, error); target[off:off+4] = actual[off:off+4]
            if actual != target or bytes(cpu.mem_read(config, len(data))) != data:
                off = next((i for i, (a, b) in enumerate(zip(actual, target)) if a != b), None)
                raise AssertionError((count, tick, 'unexpected owner/configuration write', off,
                    None if off is None else (actual[off:off+8].hex(), target[off:off+8].hex())))
            if extension is not None:
                extension.check(o)
            stage_total += sum(c.stage in DrivingForces.stages for c in result.calls)
            image = bytearray(actual); state = result.state; ticks += 1
            mutation_ticks += int(effect_mutated)
            branches[result.branch] = branches.get(result.branch, 0)+1
        count += 1
    return dict(scenarios=count, repeated_ticks=ticks, recovered_force_calls=stage_total,
        component_mutation_ticks=mutation_ticks,
        branches=branches, support_projection_queries=projection_count,
        maximum_absolute_error=maximum, maximum_effect_argument_error=event_maximum,
        maximum_conditioned_radius_error=radius_error,
        maximum_conditioned_component_argument_error=conditioned_effect_error,
        scope=('complete original 53c140 controller, actual support predictor/scalar transforms, six actual force stages and actual 540c30; terrain projection, other stages and service/component delivery supplied; ordered queries/calls/effects and full owner bytes checked'
               if actual_support else 'complete original 53c140 controller with six actual force stages and actual 540c30; other stages and service/component delivery supplied; ordered calls/effects and full owner bytes checked'))


def verify_support(executable):
    return verify(executable, actual_support=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable')
    parser.add_argument('--actual-support', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.executable, args.actual_support)))
