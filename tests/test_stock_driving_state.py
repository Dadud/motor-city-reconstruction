import unittest
from dataclasses import fields
from types import SimpleNamespace
from client.contact import Pose, WheelRig
from client.engine import EngineBlock
from client.stock_driving_state import (MissingDrivingInputs, build_stock_driving_bindings,
                                       construct_observed_state)
from client.suspension import Spring, Shock
from client.tires import TireDimensions
from client.vehicle_update import VehicleUpdateState


class StockDrivingBindingTests(unittest.TestCase):
    def test_component_values_do_not_become_guessed_controller_inputs(self):
        vehicle = SimpleNamespace(branded_id=101, name='Test stock')
        tire = TireDimensions(205, 60, 15)
        catalogue = SimpleNamespace(
            tire_dimensions=lambda _: dict.fromkeys(('LF','RF','LR','RR'), tire),
            suspension=lambda _: dict.fromkeys(('LF','RF','LR','RR'),
                (Spring(45000, 0, 5), Shock(.3, .2, 3))),
            engine_block=lambda _: EngineBlock(.1, .1, 5., 8, 120.))
        world = SimpleNamespace(rig=WheelRig(((-.7,0,1.3),(.7,0,1.3),(-.7,0,-1.3),(.7,0,-1.3))),
                                pose=Pose((0.,0.,0.)), contacts=tuple(SimpleNamespace(wheel=key,
                                    center=(0.,0.,0.),height=0.,normal=(0.,1.,0.),gap=.02,surface=None)
                                    for key in ('LF','RF','LR','RR')))
        bindings = build_stock_driving_bindings(catalogue, vehicle, world)
        self.assertEqual(bindings.components['wheels']['LF']['tire_radius_m'], tire.radius)
        self.assertEqual(bindings.components['engine_block']['mass'], 120.)
        self.assertEqual(bindings.decoded_geometry['marker_wheelbase_m'], 2.6)
        self.assertFalse(bindings.authored_placement['original_spawn_verified'])
        self.assertFalse(bindings.ready_for_recovered_driving)
        with self.assertRaises(MissingDrivingInputs):
            bindings.require_recovered_driving()
        self.assertIn('mass', bindings.report()['required_explicit_fields']['controller'])

    def test_research_defaults_cannot_silently_initialize_a_car(self):
        with self.assertRaises(MissingDrivingInputs) as raised:
            construct_observed_state('controller', {'active': True})
        self.assertIn('mass', raised.exception.missing)
        self.assertIn('wheels', raised.exception.missing)
        # Explicitly supplied observations are accepted, with no claim of provenance.
        state = VehicleUpdateState()
        supplied = {item.name: getattr(state, item.name) for item in fields(state)}
        supplied['mass'] = 1732.
        result = construct_observed_state('controller', supplied)
        self.assertEqual(result.mass, 1732.)
        with self.assertRaisesRegex(ValueError, 'constructed controller_wheel'):
            construct_observed_state('controller', dict(supplied, wheels=[{}]*4))
        with self.assertRaisesRegex(ValueError, 'unknown observation'):
            construct_observed_state('controller', dict(supplied, invented=True))


    def test_drivetrain_requires_complete_explicit_nested_observations(self):
        from client.drivetrain_stages import DriveState
        with self.assertRaises(MissingDrivingInputs):
            construct_observed_state('drivetrain',{})
        state = DriveState()
        observed = {item.name:getattr(state,item.name) for item in fields(state)}
        self.assertEqual(construct_observed_state('drivetrain',observed),state)
        with self.assertRaisesRegex(ValueError,'constructed drivetrain_wheel'):
            construct_observed_state('drivetrain',dict(observed,wheels=[{}]*4))


if __name__ == '__main__':
    unittest.main()
