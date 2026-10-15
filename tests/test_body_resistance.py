import unittest
from dataclasses import replace
from client.body_resistance import calculate_body_resistance
from tools.body_resistance_oracle import cases


class BodyResistanceTests(unittest.TestCase):
    def setUp(self): self.state=next(cases())

    def test_disable_resistance_preserves_wind_yaw(self):
        out=calculate_body_resistance(replace(self.state,resistance_disabled=True))
        self.assertEqual(out.longitudinal_drag,0)
        self.assertEqual(out.pitch_contribution,0)
        self.assertNotEqual(out.yaw_contribution,0)

    def test_drag_sign_uses_vertical_field(self):
        positive=calculate_body_resistance(replace(self.state,longitudinal_speed=1))
        negative=calculate_body_resistance(replace(self.state,longitudinal_speed=-1))
        self.assertEqual(positive.longitudinal_drag,-negative.longitudinal_drag)
        self.assertEqual(positive.pitch_contribution,negative.pitch_contribution)

    def test_disabled_transfer_preserves_wheel_loads(self):
        state=replace(self.state,load_transfer_disabled=True)
        self.assertEqual(calculate_body_resistance(state).wheel_loads,state.wheel_loads)

    def test_rejects_zero_lever(self):
        with self.assertRaises(ValueError): calculate_body_resistance(replace(self.state,front_lever=0))
