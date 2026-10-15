import unittest
from dataclasses import replace
from client.body_vertical_load import BodyVerticalLoadState, adjust_body_vertical_load


class BodyVerticalLoadTests(unittest.TestCase):
    def setUp(self):
        self.state=BodyVerticalLoadState(0,2,1,2,.5,.25,0,0,0,0,(0,0,0,0))

    def test_reverse_does_not_enable_speed_parameters(self):
        base=adjust_body_vertical_load(self.state)
        reverse=adjust_body_vertical_load(replace(self.state,speed=-30))
        forward=adjust_body_vertical_load(replace(self.state,speed=30))
        self.assertEqual(base,reverse)
        self.assertGreater(forward.total_vertical,base.total_vertical)

    def test_negative_contributions_clamp_wheel_loads(self):
        out=adjust_body_vertical_load(replace(self.state,front_parameter=-1))
        self.assertLess(out.front_vertical,0)
        self.assertEqual(out.wheel_loads[:2],(0,0))

    def test_quality_one_preserves_loads(self):
        out=adjust_body_vertical_load(replace(self.state,front_quality=1,rear_quality=1,wheel_loads=(1,2,3,4)))
        self.assertEqual(out.wheel_loads,(1,2,3,4))

    def test_longitudinal_speed_sign_is_discarded(self):
        self.assertEqual(adjust_body_vertical_load(self.state),adjust_body_vertical_load(replace(self.state,longitudinal_speed=-2)))

    def test_rejects_invalid_load_count(self):
        with self.assertRaises(ValueError): adjust_body_vertical_load(replace(self.state,wheel_loads=()))
