import unittest
from client.vehicle_gate import vehicle_gate_result


class VehicleGateTests(unittest.TestCase):
    def test_null_owner_requires_no_interface_observation(self):
        self.assertFalse(vehicle_gate_result(False,0))

    def test_signed_order_and_equality(self):
        self.assertTrue(vehicle_gate_result(True,-1,-1))
        self.assertFalse(vehicle_gate_result(True,-1,0))
        self.assertTrue(vehicle_gate_result(True,0,-1))
        self.assertTrue(vehicle_gate_result(True,0x7fffffff,-0x80000000))
        self.assertFalse(vehicle_gate_result(True,-0x80000000,0x7fffffff))

    def test_repeat_observations_need_not_be_invariant(self):
        self.assertEqual([vehicle_gate_result(True,10,value) for value in (11,10,9,12)],
                         [False,True,True,False])

    def test_validation(self):
        for args in ((True,0,None),(1,0,0),(True,True,0),(True,0,0x80000000)):
            with self.assertRaises(ValueError):vehicle_gate_result(*args)
