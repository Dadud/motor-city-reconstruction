import unittest
from client.collision_response import tangential_response


class CollisionResponseTests(unittest.TestCase):
    def test_separating_and_tangent_inputs_have_no_response(self):
        self.assertEqual(tangential_response((1,1,0),(0,1,0),1,0.5).status,0)
        self.assertEqual(tangential_response((1,0,0),(0,1,0),1,0.5).vector,(0,0,0))

    def test_original_projection_sign_is_preserved(self):
        result=tangential_response((0,-1,0),(0,1,0),2,0.5)
        self.assertEqual(result.status,1)
        self.assertEqual(result.vector,(-0.0,2.0,-0.0))

    def test_sliding_threshold_is_strict(self):
        v,n=(0,-1,0),(0,1,0)
        self.assertEqual(tangential_response(v,n,2,0.5).status,1)
        result=tangential_response(v,n,1.9999998807907104,0.5)
        self.assertEqual(result.status,2)
        self.assertEqual(result.vector,(-0.0,0.5,-0.0))

    def test_normal_consumed_without_normalization(self):
        result=tangential_response((0,-1,0),(0,2,0),4,0.5)
        self.assertEqual(result.status,1)
        self.assertEqual(result.vector,(-0.0,5.0,-0.0))

    def test_malformed_and_nonfinite_inputs_rejected(self):
        for vector in ((0,0),(float('nan'),0,0),(float('inf'),0,0)):
            with self.assertRaises(ValueError): tangential_response(vector,(0,1,0),1,0.5)


if __name__=='__main__': unittest.main()
