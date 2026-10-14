import unittest
from dataclasses import replace
from client.suspension_load_correction import SuspensionLoadInput, correct_suspension_load


class SuspensionLoadTests(unittest.TestCase):
    def setUp(self):
        self.state=SuspensionLoadInput((1000,)*4,(True,)*4,0,True,6,0.08,-0.06,
            1450,100,0.45,0.55,1.2,1.5,2.7,1.7,2,500,0,False)

    def test_outer_gates_and_exact_speed_gate(self):
        self.assertEqual(correct_suspension_load(replace(self.state,enabled=False)),self.state.loads)
        self.assertEqual(correct_suspension_load(replace(self.state,attitude=0.25001)),self.state.loads)
        self.assertNotEqual(correct_suspension_load(replace(self.state,attitude=0.25)),self.state.loads)
        no_torque=replace(self.state,disable_torque=True)
        self.assertEqual(correct_suspension_load(no_torque),self.state.loads)
        self.assertNotEqual(correct_suspension_load(replace(no_torque,speed=6.001)),self.state.loads)

    def test_torque_is_absolute_and_independent_of_support(self):
        no_support=replace(self.state,support=(False,)*4)
        result=correct_suspension_load(no_support)
        self.assertEqual(result[:2],self.state.loads[:2])
        self.assertGreater(result[2],1000)
        self.assertLess(result[3],1000)
        self.assertEqual(result,correct_suspension_load(replace(no_support,torque=-500)))
        self.assertEqual(correct_suspension_load(replace(no_support,component_mode=1)),self.state.loads)

    def test_high_speed_support_mask_and_clamps(self):
        state=replace(self.state,speed=20,disable_torque=True,support=(False,True,False,True))
        result=correct_suspension_load(state)
        self.assertEqual(result[0],1000)
        self.assertEqual(result[2],1000)
        self.assertNotEqual(result[1],1000)
        large=correct_suspension_load(replace(state,loads=(1,)*4,bank_angle=-0.1,pitch_angle=0.1,support=(True,)*4))
        self.assertTrue(all(load>=0 for load in large))
        self.assertTrue(any(load==0 for load in large))

    def test_invalid_observations(self):
        for changes in ({'loads':(-1,1,1,1)},{'support':(1,1,1,1)},
                        {'rear_track':0},{'mass_offset':2000},{'torque':float('inf')}):
            with self.assertRaises(ValueError):
                correct_suspension_load(replace(self.state,**changes))


if __name__ == '__main__':
    unittest.main()
