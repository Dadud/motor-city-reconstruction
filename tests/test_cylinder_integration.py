"""Regression boundaries for the recovered crank integrator."""
from dataclasses import replace
import unittest
from client.dyno_solver import _f32
from client.cylinder_integration import (IntegrationInputs, IntegrationState,
    integrate_crank_step, crank_step_size, carry_cycle_pressure)

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.state = IntegrationState(44.1, 2000, .001)
        self.inputs = IntegrationInputs(710, .6, 2000, 1.75, 5.67, 3.24,
            12.56, 5.49, 4, 25.12, 0, 0, 14.7, 30, 140, .002, 12.5, 19000)

    def test_zero_transfer_keeps_mass(self):
        result = integrate_crank_step(self.state,self.inputs)
        self.assertEqual(result.state.mass,_f32(self.state.mass))
        self.assertEqual(result.mass_rate,0)
        self.assertEqual(result.state.intake_energy,0)
        self.assertEqual(result.state.exhaust_energy,0)

    def test_derivative_history_changes_next_step(self):
        baseline = integrate_crank_step(self.state,self.inputs)
        history = integrate_crank_step(replace(self.state,previous_pressure_rate=2),self.inputs)
        self.assertLess(history.state.pressure,baseline.state.pressure)

    def test_reverse_flow_selects_boundary_energy(self):
        result = integrate_crank_step(self.state,replace(self.inputs,intake_pressure=50,exhaust_pressure=50))
        self.assertEqual(result.intake_specific_energy,140)
        self.assertEqual(result.exhaust_specific_energy,506.7442626953125)

    def test_pulse_exact_boundaries(self):
        for angle in (710,770):
            low = integrate_crank_step(self.state,replace(self.inputs,angle=angle,fuel_energy=0))
            high = integrate_crank_step(self.state,replace(self.inputs,angle=angle,fuel_energy=30000))
            self.assertEqual(low,high)
        low = integrate_crank_step(self.state,replace(self.inputs,angle=740,fuel_energy=0))
        high = integrate_crank_step(self.state,replace(self.inputs,angle=740,fuel_energy=30000))
        self.assertGreater(high.state.pressure,low.state.pressure)

    def test_invalid_domain(self):
        for state in (replace(self.state,mass=0),replace(self.state,temperature=float('nan'))):
            with self.assertRaises(ValueError):
                integrate_crank_step(state,self.inputs)

    def test_knot_carryover(self):
        self.assertEqual(carry_cycle_pressure(0,40,42),44.099998474121094)
        self.assertEqual(carry_cycle_pressure(1,40,42),40)
        self.assertEqual(carry_cycle_pressure(2,40,42),42)
        self.assertEqual(crank_step_size(2000),.6000000238418579)
        self.assertEqual(crank_step_size(11000),3.3000001907348633)
