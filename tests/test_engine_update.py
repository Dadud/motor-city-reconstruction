from dataclasses import replace
import unittest

from client.engine_update import curve_torque_at_rpm, signed_counter, update_engine
from client.tire_response import f32
from tools.engine_update_oracle import cases, SuppliedEngineStages


class EngineUpdateTests(unittest.TestCase):
    def state(self, **changes):
        return replace(next(cases())[0], engine_flags=1, vehicle_flags=4, **changes)

    def test_normal_path_retains_original_child_order(self):
        state = self.state()
        output = update_engine(state, SuppliedEngineStages({}))
        self.assertEqual([c.stage for c in output.calls], [
            'engine_setup', 'engine_control', 'gear_link', 'drivetrain_loads',
            'engagement_inputs', 'torque_update', 'wheel_drive', 'engine_finalize'])
        self.assertEqual(state.vehicle_flags, 4)
        self.assertEqual(output.state.engine_flags, 1)

    def test_startup_delay_wraps_before_signed_comparison(self):
        state = replace(self.state(), engine_flags=0, current_counter=-0x80000000,
                        activation_delays=(0,)*8)
        output = update_engine(state, SuppliedEngineStages(
            {'query_8': 1, 'activation_counter': 0x7fffffff}))
        self.assertEqual(output.state.engine_flags, 0)
        self.assertEqual(signed_counter(0x7fffffff+1), -0x80000000)
        output = update_engine(replace(state, current_counter=0x7fffffff),
            SuppliedEngineStages({'query_8': 1, 'activation_counter': -0x80000000}))
        self.assertEqual(output.state.engine_flags, 1)
        self.assertIn('enable_signal', [c.stage for c in output.calls])

    def test_override_sets_fixed_rpm_without_rpm_child(self):
        state = replace(self.state(), vehicle_flags=7, override_value=1.)
        output = update_engine(state, SuppliedEngineStages({}))
        self.assertEqual(output.state.rpm_state.rpm, 5950)
        self.assertNotIn('rpm_update', [c.stage for c in output.calls])
        self.assertEqual([c.stage for c in output.calls],
                         ['curve_lookup', 'gear_link', 'drivetrain_loads'])

    def test_curve_uses_supplied_adjacent_knots_and_unstored_result(self):
        table = (10., 30., 25.)
        self.assertEqual(curve_torque_at_rpm(table, 0), 10.)
        self.assertEqual(curve_torque_at_rpm(table, 250), 10.+20.*250*f32(.002))
        self.assertNotEqual(curve_torque_at_rpm(table, 250), f32(curve_torque_at_rpm(table, 250)))
        for rpm in (-1, 1000):
            with self.assertRaises(ValueError): curve_torque_at_rpm(table, rpm)

    def test_missing_child_is_explicit_and_inputs_are_not_mutated(self):
        state = self.state()
        with self.assertRaises(ValueError): update_engine(state, None)
        before = replace(state)
        def execute(call, current):
            current.engagement = .123456789
            return 0
        output = update_engine(state, execute)
        self.assertEqual(state, before)
        self.assertEqual(output.state.engagement, f32(.123456789))

    def test_child_writes_change_final_dispatch_and_rounding(self):
        state = replace(self.state(), vehicle_flags=6, override_value=0.)
        def execute(call, current):
            if call.stage == 'torque_update':
                current.vehicle_flags = 3
                current.rpm_state = replace(current.rpm_state, rpm=250)
            return 0
        output = update_engine(state, execute)
        self.assertEqual([c.stage for c in output.calls],
                         ['torque_update', 'curve_lookup', 'gear_link', 'drivetrain_loads'])
        self.assertEqual(output.state.rpm_state.normalized_rpm, f32(250/6800))
