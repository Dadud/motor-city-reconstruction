from dataclasses import replace
import unittest
from client.vehicle_update import VehicleUpdateState,update_vehicle,apply_linear_update
from tools.vehicle_update_oracle import SuppliedStages,mutation_cases


class VehicleUpdateTests(unittest.TestCase):
    def state(self):
        s=VehicleUpdateState()
        for w in s.wheels:w.contact=True;w.force=(1.,100.,2.)
        return s

    def observations(self,**values):
        return {'global_mode':(0,0,0,0,0),'vehicle_gate':(True,True),
                'followup_enabled':False,**values}

    def test_inactive_has_no_child_side_effects(self):
        s=self.state();s.active=False
        out=update_vehicle(s,SuppliedStages(self.observations()))
        self.assertEqual(out.branch,'inactive')
        self.assertEqual([c.stage for c in out.calls],['global_mode'])

    def test_child_mutations_affect_branches_and_consumers(self):
        for s,observations,branch in mutation_cases():
            with self.subTest(branch=branch,mutations=observations['mutations']):
                out=update_vehicle(s,SuppliedStages(observations))
                self.assertEqual(out.branch,branch)
                if 'linear_update' in observations['mutations']:
                    self.assertEqual(out.state.linear_velocity,(11.,-12.,13.))

    def test_successive_gates_are_independent(self):
        for first,second in ((False,True),(True,False)):
            out=update_vehicle(self.state(),SuppliedStages(self.observations(vehicle_gate=(first,second))))
            stages=[c.stage for c in out.calls]
            self.assertEqual('wheel_spin' in stages,second)
            self.assertEqual('combined_slip' in stages,second)

    def test_force_clearing_occurs_before_moments(self):
        s=self.state();s.wheels[0].clear_reference=.5;s.wheels[0].clear_threshold=-.501
        driver=SuppliedStages(self.observations());observed=[]
        def execute(call,state):
            if call.stage=='body_moments':observed.append(state.wheels[0].force)
            return driver(call,state)
        out=update_vehicle(s,execute)
        self.assertEqual(observed,[(0.,0.,0.)])
        self.assertEqual(s.wheels[0].force,(1.,100.,2.))
        self.assertEqual(out.state.wheels[0].force,(0.,0.,0.))

    def test_alternate_skips_normal_and_tail_stages(self):
        out=update_vehicle(self.state(),SuppliedStages(self.observations(global_mode=(1,))))
        stages=[c.stage for c in out.calls]
        self.assertEqual(out.branch,'alternate')
        self.assertEqual(stages[-1],'engine')
        self.assertNotIn('post_vehicle',stages)
        self.assertNotIn('tires',stages)

    def test_followup_short_circuits(self):
        for enabled,ready in ((False,True),(True,False),(True,True)):
            out=update_vehicle(self.state(),SuppliedStages(self.observations(followup_enabled=enabled,followup_ready=ready)))
            stages=[c.stage for c in out.calls]
            self.assertEqual('followup_ready' in stages,enabled)
            self.assertEqual('followup' in stages,enabled and ready)

    def test_tilt_boundary_and_flagged_return(self):
        for attitude,flags,branch in ((.8499999,2,'tilted'),(.85,2,'flagged'),(.8500001,0,'supported')):
            s=self.state();s.attitude=attitude;s.flags=flags
            out=update_vehicle(s,SuppliedStages(self.observations()))
            self.assertEqual(out.branch,branch)
            if branch=='flagged':self.assertEqual(out.calls[-1].stage,'flagged_motion')

    def test_missing_child_behavior_is_not_silently_replaced(self):
        with self.assertRaises(ValueError):update_vehicle(self.state(),None)
        def missing(call,state):raise NotImplementedError(call.stage)
        with self.assertRaises(NotImplementedError):update_vehicle(self.state(),missing)
        for s in (replace(self.state(),wheels=[]),replace(self.state(),surface_coefficients=(1.,))):
            with self.assertRaises(ValueError):update_vehicle(s,SuppliedStages(self.observations()))

    def test_linear_update_active_and_inactive_modes(self):
        s=self.state();s.linear_velocity=(1.,2.,3.);s.linear_acceleration=(32.,64.,96.)
        apply_linear_update(s,True)
        self.assertEqual(s.linear_velocity,(2.,4.,6.))
        s.angular_velocity=(1.,2.,3.);s.angular_acceleration=(4.,5.,6.)
        apply_linear_update(s,False)
        self.assertEqual(s.linear_velocity,(0.,4.,0.))
        self.assertEqual(s.angular_velocity,(1.,0.,3.))
        self.assertEqual(s.linear_acceleration,(0.,0.,0.))
        self.assertEqual(s.angular_acceleration,(0.,0.,0.))

    def test_child_write_rounds_before_attitude_branch(self):
        def execute(call,state):
            if call.stage=='prepare_vehicle':state.attitude=.849999999
            return 0
        out=update_vehicle(self.state(),execute)
        # The supplied value rounds up to the original float32 0.85 threshold.
        self.assertEqual(out.branch,'supported')
