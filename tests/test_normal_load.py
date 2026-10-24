import unittest
from dataclasses import replace
from client.normal_load import NormalLoadInput, normal_force_vectors, normal_load


class NormalLoadTests(unittest.TestCase):
    def setUp(self):
        self.state=NormalLoadInput((True,)*4,0,0,1000,2,1.5,1.5,0.5,1,1,0,40,0,(10,)*4)

    def test_all_masks_and_axle_redistribution(self):
        for mask in range(16):
            support=tuple(bool(mask & (1<<i)) for i in range(4))
            loads=normal_load(replace(self.state,support=support))
            self.assertTrue(all(load>=0 for load in loads))
            if sum(support)<2:
                self.assertEqual(loads,(0,)*4)
            else:
                self.assertEqual(sum(loads),10000)
                self.assertTrue(all(load==0 for load,flag in zip(loads,support) if not flag))
        self.assertEqual(normal_load(replace(self.state,support=(False,False,True,True))), (0,0,5000,5000))

    def test_pitch_gate_and_vertical_clamping(self):
        self.assertEqual(normal_load(replace(self.state,pitch=0.25001)),(0,)*4)
        self.assertTrue(any(normal_load(replace(self.state,pitch=0.25))))
        self.assertEqual(normal_load(replace(self.state,vertical_correction=11)),(0,)*4)

    def test_bank_centripetal_cap(self):
        moderate=normal_load(replace(self.state,bank=0.1,speed=50))
        very_fast=normal_load(replace(self.state,bank=0.1,speed=500))
        self.assertEqual(moderate,very_fast)
        self.assertGreater(moderate[0],moderate[1])

    def test_invalid_observations(self):
        for changes in ({'support':(1,1,1,1)},{'wheel_scales':(1,2,3)},
                        {'curvature_scale':0},{'mass':0},{'pitch':float('nan')}):
            with self.assertRaises(ValueError):
                normal_load(replace(self.state,**changes))

    def test_opposite_turn_radius_is_valid(self):
        positive=normal_load(replace(self.state,bank=.07,speed=18,curvature_scale=40))
        negative=normal_load(replace(self.state,bank=.07,speed=18,curvature_scale=-40))
        self.assertEqual(negative,positive)

    def test_force_vectors_clear_non_load_components(self):
        forces = normal_force_vectors(self.state)
        self.assertEqual(len(forces), 4)
        self.assertTrue(all(len(force) == 3 for force in forces))
        self.assertTrue(all(force[0] == 0 and force[2] == 0 for force in forces))
        self.assertEqual(tuple(force[1] for force in forces), normal_load(self.state))


if __name__ == '__main__':
    unittest.main()
