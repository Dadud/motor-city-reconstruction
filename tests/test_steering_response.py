import unittest
from client.steering_response import steering_response


class SteeringResponseTests(unittest.TestCase):
    def test_control_signs_and_saturation(self):
        self.assertEqual(steering_response(0,0),0)
        self.assertEqual(steering_response(127,0),1)
        self.assertEqual(steering_response(-128,100),-1)
        self.assertEqual(steering_response(-0x80000000,0),-1)
        self.assertEqual(steering_response(0x7fffffff,100),1)

    def test_speed_blends_magnitude_toward_square(self):
        low=steering_response(63,0)
        middle=steering_response(63,20)
        high=steering_response(63,100)
        self.assertGreater(low,middle)
        self.assertGreater(middle,high)
        self.assertAlmostEqual(high,low*low,places=7)
        self.assertEqual(high,steering_response(63,-100))
        self.assertEqual(-middle,steering_response(-63,20))

    def test_full_control_does_not_weaken_at_speed(self):
        for speed in (0,20,44.703,100):
            self.assertEqual(steering_response(127,speed),1)

    def test_invalid_observations(self):
        for raw,speed in ((True,0),(1.5,0),(0x80000000,0),(0,float('nan')),(0,1e100)):
            with self.assertRaises(ValueError):
                steering_response(raw,speed)


if __name__=='__main__':
    unittest.main()
