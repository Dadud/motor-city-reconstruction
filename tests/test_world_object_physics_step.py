import struct
import unittest

from client.world_object_physics_step import step_world_object_physics


class WorldObjectPhysicsStepTests(unittest.TestCase):
    def make_record(self):
        record = bytearray(0x4f8)
        record[4] = 1
        struct.pack_into('<3f', record, 0x14, 1.25, -2.5, .75)
        struct.pack_into('<3f', record, 0x38, .125, -.25, .5)
        struct.pack_into('<9f', record, 0x31c,
                         .75, .125, -.25, .5, 1, .25, -.125, .375, .875)
        struct.pack_into('<f', record, 0x50, 4)
        struct.pack_into('<3f', record, 0x2f0, 2, .75, 1.5)
        return record

    def test_owned_force_and_energy_updates(self):
        record = self.make_record()
        calls = []
        step_world_object_physics(record, mode_active=False, mode_number=0,
                                  environment_step=lambda _: calls.append('environment'),
                                  contact_force_step=lambda _: calls.append('contact'))
        self.assertEqual(calls, ['environment', 'contact'])
        self.assertNotEqual(struct.unpack_from('<f', record, 0x14)[0], 1.25)
        self.assertGreater(struct.unpack_from('<f', record, 0x3c0)[0], 0)

    def test_special_mode_runs_environment_but_skips_force_child(self):
        record = self.make_record()
        record[6] = 1
        before_velocity = bytes(record[0x14:0x20])
        calls = []
        step_world_object_physics(record, mode_active=True, mode_number=1,
                                  environment_step=lambda _: calls.append('environment'),
                                  contact_force_step=lambda _: calls.append('contact'))
        self.assertEqual(calls, ['environment'])
        self.assertEqual(bytes(record[0x14:0x20]), before_velocity)

    def test_requires_both_children_and_mutable_complete_record(self):
        with self.assertRaisesRegex(ValueError, 'both original'):
            step_world_object_physics(bytearray(0x4f8), mode_active=False,
                mode_number=0, environment_step=lambda _: None, contact_force_step=None)
        with self.assertRaises(ValueError):
            step_world_object_physics(bytes(0x4f8), mode_active=False,
                mode_number=0, environment_step=lambda _: None,
                contact_force_step=lambda _: None)


if __name__ == '__main__':
    unittest.main()
