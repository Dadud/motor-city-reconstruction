"""Controller/force integration regressions; numeric fidelity uses the oracle."""
from copy import deepcopy
from dataclasses import replace
import unittest
from client.driving_pipeline import DrivingForces, ForceInputs
from client.body_moments import BodyMomentState, MomentWheel, accumulate_body_moments
from client.vehicle_update import VehicleUpdateState, UpdateCall, apply_linear_update, update_vehicle
from client.wheel_spin import SpinWheel, WheelSpinState
from tools.tire_update_oracle import cases


def inputs():
    tire = replace(next(cases()), raw_control=127, mode_observations=(True,)*4)
    spin = WheelSpinState(tuple(SpinWheel(0, 4, .3, 10, 2500, 1, .5, .1, True, True)
        for _ in range(4)), 2, False, 3000, .002, .3, .35, .02, .03, -2, 3,
        .7, .8, .05, 1.2, 1.5, .03, .2)
    moment = BodyMomentState(tuple(MomentWheel(0, 0, 0, 0, True) for _ in range(4)),
        10, 1.2, 1.5, 1.6, 1.7, .7, 1300, .003, .002, .004, .8, 300, 400, 53)
    return ForceInputs(tire, spin, moment, 1, 0, True, .3, -.2)


def state():
    s = VehicleUpdateState(local_linear=(.2, 0, 10), linear_velocity=(.2, 0, 10),
        angular_velocity=(0, .03, 0), mass=1300, inverse_mass=1/1300,
        front_lever=1.2, rear_lever=1.5, angular_scale=.003,
        front_moment=300, rear_moment=400, maximum_steering=.08, support_count=4)
    for w in s.wheels:
        w.contact=True; w.force=(0, 2500, 500); w.spin=30; w.projected_speed=10
    return s


def external(call, s, p):
    if call.stage in ('global_mode', 'followup_enabled'): return False
    if call.stage == 'vehicle_gate': return True
    if call.stage == 'linear_update': apply_linear_update(s, True)
    # Explicit supplied children only for this integration fixture.
    return 0


class DrivingPipelineTests(unittest.TestCase):
    def test_real_controller_consumes_cleared_forces_before_moments(self):
        p=inputs(); s=state(); s.wheels[0].clear_threshold=-1
        driver=DrivingForces(p, external, lambda *args: None)
        output=update_vehicle(s, driver)
        self.assertEqual(output.branch, 'supported')
        self.assertEqual(output.state.wheels[0].force, (0., 0., 0.))
        self.assertEqual(p.moments.wheels[0].longitudinal_force, 0.)
        self.assertEqual(output.state.local_angular_acceleration, accumulate_body_moments(p.moments))
        self.assertNotEqual(output.state.linear_velocity, s.linear_velocity)
        self.assertEqual(s.wheels[0].force, (0, 2500, 500))

    def test_repeated_ticks_retain_wheel_history_and_use_new_controller_inputs(self):
        p=inputs(); driver=DrivingForces(p, external, lambda *args: None)
        first=update_vehicle(state(), driver)
        phase=first.state.wheels[0].phase
        first.state.wheels[0].spin=50
        first.state.wheels[0].force=(0, 500, 200)
        second=update_vehicle(first.state, driver)
        self.assertNotEqual(second.state.wheels[0].phase, phase)
        self.assertEqual(p.spin.wheels[0].normal_load, 500.)
        self.assertEqual(p.tire.mass_parameter, second.state.mass)

    def test_independent_gate_skips_spin_and_combined_effects(self):
        p=inputs(); before=deepcopy(p.spin); effects=[]; gates=iter((True, False))
        def supplied(call, s, p):
            if call.stage=='vehicle_gate': return next(gates)
            return external(call, s, p)
        out=update_vehicle(state(), DrivingForces(p, supplied, lambda *args: effects.append(args)))
        self.assertNotIn('wheel_spin', [c.stage for c in out.calls])
        self.assertEqual(effects, [])
        self.assertEqual(p.spin.wheels[0].phase, before.wheels[0].phase)

    def test_effect_mutation_is_visible_to_next_stage(self):
        p=inputs(); s=state(); delivered=[]
        def effects(kind, events, current, supplied):
            delivered.append(kind)
            if kind=='wheel_spin': current.wheels[0].contact=False
        out=update_vehicle(s, DrivingForces(p, external, effects))
        self.assertEqual(delivered, ['wheel_spin', 'combined_slip'])
        self.assertFalse(out.state.wheels[0].contact)
        self.assertFalse(p.moments.wheels[0].contact)

    def test_unbound_stages_and_missing_effect_delivery_fail_explicitly(self):
        def missing(call, s, p): raise NotImplementedError(call.stage)
        driver=DrivingForces(inputs(), missing, lambda *args: None)
        with self.assertRaisesRegex(NotImplementedError, 'global_mode'):
            update_vehicle(state(), driver)
        with self.assertRaises(ValueError): DrivingForces(inputs(), external, None)

    def test_moment_config_mass_is_not_overwritten_by_dynamic_mass(self):
        p=inputs(); s=state(); s.mass=900; s.angular_scale=.012
        driver=DrivingForces(p, external, lambda *args: None)
        driver(UpdateCall('body_moments'), s)
        self.assertEqual(p.moments.mass_parameter, 1300)
        self.assertEqual(p.moments.inverse_pitch, .012)


if __name__=='__main__': unittest.main()
