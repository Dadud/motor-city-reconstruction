from dataclasses import replace
import unittest
from client.wind import WindState, calculate_wind, signed_remainder
from client.drafting import calculate_drafting
from client.body_environment import BodyEnvironment, calculate_body_environment
from client.tire_response import f32
from tools.drafting_oracle import vehicle, encode
from tools.body_resistance_oracle import connected_cases, environment_case

IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)


class EnvironmentTests(unittest.TestCase):
    def test_disabled_wind_returns_clear_vector_and_false(self):
        state = WindState(123, 456, (1., 2., 3.), IDENTITY, True)
        output = calculate_wind(state)
        self.assertEqual(output.body_velocity, (0., 0., 0.))
        self.assertFalse(output.present)

    def test_zero_counter_wind_has_original_minimum_strength(self):
        output = calculate_wind(WindState(0, 0, (0., 0., 1.), IDENTITY))
        self.assertEqual(output.body_velocity, (0., 0., f32(3*f32(.44703))))
        self.assertTrue(output.present)

    def test_signed_weather_remainder_preserves_original_negative_branch(self):
        self.assertEqual(signed_remainder(-361, 360), -1)
        self.assertEqual(signed_remainder(-16, 15), -1)
        negative = calculate_wind(WindState(0, -1, (0., 0., 1.), IDENTITY))
        positive = calculate_wind(WindState(0, 359, (0., 0., 1.), IDENTITY))
        self.assertLess(negative.body_velocity[2], positive.body_velocity[2])

    def test_wind_transform_can_produce_vertical_component(self):
        matrix = (0., 1., 0., 1., 0., 0., 0., 1., 0.)
        output = calculate_wind(WindState(0, 0, (0., 0., 1.), matrix))
        self.assertEqual(output.body_velocity, (0., f32(3*f32(.44703)), 0.))

    def test_drafting_chooses_first_eligible_vehicle(self):
        own, first, closer = vehicle(1), vehicle(2, (0., 0., 8.)), vehicle(3, (0., 0., 4.))
        output = calculate_drafting(1, (own, first, closer))
        self.assertEqual(output.selected_vehicle, 2)
        self.assertEqual(encode(output.vehicles[0]), encode(own))
        self.assertEqual(encode(output.vehicles[2]), encode(closer))
        self.assertNotEqual(output.vehicles[1].wake_origin, first.wake_origin)
        self.assertEqual(first.wake_origin, (11., 12., 13.))
        self.assertEqual(calculate_drafting(1, (own, closer, first)).selected_vehicle, 3)

    def test_coincident_horizontal_positions_use_original_clamped_infinity(self):
        output = calculate_drafting(1, (vehicle(1), vehicle(2, (0., 20., 0.))))
        self.assertFalse(output.inside_wake)
        self.assertEqual(output.factor, 1.25)

    def test_far_or_misaligned_cars_do_not_receive_wake_writes(self):
        cars = (vehicle(1), vehicle(2, (0., 0., 13.)), vehicle(3, (0., 0., 4.), 3.14))
        output = calculate_drafting(1, cars)
        self.assertEqual(output.factor, 1.)
        self.assertEqual(tuple(map(encode, output.vehicles)), tuple(map(encode, cars)))
        self.assertIsNone(output.selected_vehicle)

    def test_connected_environment_overrides_stale_supplied_force_inputs(self):
        state, altitude, cold, enabled, weather = next(connected_cases())
        state, wind, cars, _ = environment_case(0, state)
        environment = BodyEnvironment(altitude, cold, enabled, weather, wind, 1, cars)
        expected = calculate_body_environment(state, environment)
        stale = replace(state, density=999., wind_lateral=999., wind_longitudinal=999., drafting_factor=999.)
        self.assertEqual(calculate_body_environment(stale, environment), expected)
        repeated = calculate_body_environment(state, replace(environment, vehicles=expected.drafting.vehicles))
        self.assertEqual(repeated, expected)

    def test_missing_or_ambiguous_vehicle_and_invalid_time_are_rejected(self):
        for identifier, cars in ((1, (vehicle(2),)), (1, (vehicle(1), vehicle(1)))):
            with self.assertRaises(ValueError): calculate_drafting(identifier, cars)
        with self.assertRaises(ValueError):
            calculate_wind(WindState(0x80000000, 0, (0., 0., 1.), IDENTITY))
