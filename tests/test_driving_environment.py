from dataclasses import replace
import unittest
from client.body_environment import BodyEnvironment
from client.driving_environment import DrivingEnvironment, EnvironmentInputs
from client.vehicle_update import UpdateCall
from client.wind import WindState
from tools.body_resistance_oracle import cases as body_cases
from tools.body_vertical_load_oracle import cases as vertical_cases
from tools.drafting_oracle import vehicle
from tests.test_driving_pipeline import state, inputs, external


def environment_inputs():
    body=replace(next(body_cases()),resistance_disabled=False,load_transfer_disabled=False)
    env=BodyEnvironment(500,False,True,2,WindState(5,-123,(.3,.2,-.7),
        (1.,0.,0.,0.,1.,0.,0.,0.,1.),False),1,(vehicle(1),vehicle(2,(1.,0.,-4.),.1)))
    return EnvironmentInputs(body,next(vertical_cases()),env)


class DrivingEnvironmentTests(unittest.TestCase):
    def test_body_uses_current_loads_and_retains_cross_car_writes(self):
        s=state(); p=inputs(); env=environment_inputs(); peer=env.environment.vehicles[1]
        driver=DrivingEnvironment(env,external)
        driver(UpdateCall('body_moment_inputs'),s,p)
        self.assertNotEqual(env.environment.vehicles[1].wake_normals,peer.wake_normals)
        self.assertEqual(env.body.speed,s.speed)
        self.assertEqual(env.body.longitudinal_speed,s.local_linear[2])
        self.assertEqual(env.body.height_parameter,p.moments.height_parameter)
        self.assertEqual(s.longitudinal_contribution,driver.last_environment.body.longitudinal_drag)
        s.wheels[0].force=(12.,700.,13.)
        driver(UpdateCall('body_moment_inputs'),s,p)
        self.assertEqual(env.body.wheel_loads[0],700.)
        self.assertEqual(s.wheels[0].force[0::2],(12.,13.))

    def test_vertical_qualities_share_spin_fields_and_write_original_accumulators(self):
        s=state(); p=inputs(); env=environment_inputs()
        p.spin=replace(p.spin,front_quality=.125,rear_quality=.875)
        env.vertical=replace(env.vertical,front_parameter=2,rear_parameter=3,
            front_adjustment=0,rear_adjustment=0)
        driver=DrivingEnvironment(env,external)
        driver(UpdateCall('body_forces'),s,p)
        self.assertEqual((env.vertical.front_quality,env.vertical.rear_quality),(.125,.875))
        self.assertEqual(s.gravity_force,s.front_moment+s.rear_moment)
        self.assertGreater(s.wheels[0].force[1]-2500,s.wheels[2].force[1]-2500)

    def test_unbound_producer_and_missing_context_raise(self):
        def missing(call,*args): raise NotImplementedError(call.stage)
        driver=DrivingEnvironment(environment_inputs(),missing)
        with self.assertRaisesRegex(NotImplementedError,'engine'):
            driver(UpdateCall('engine'),state(),inputs())
        with self.assertRaises(ValueError): DrivingEnvironment(None,external)


if __name__=='__main__': unittest.main()
