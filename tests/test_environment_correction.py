import struct
import unittest

from client.environment_correction import correct_surface_collision


class EnvironmentCorrectionTests(unittest.TestCase):
    def test_adjustment_selects_full_or_half_step_before_reset(self):
        for status, expected in ((0, 12.0), (1, 11.0)):
            record = bytearray(0x4F8)
            struct.pack_into('<f', record, 0x0C, 10.0)
            struct.pack_into('<i', record, 0x36C, status)
            calls = []

            def adjust(owner, index):
                calls.append(('adjust', index))

            def reset(owner):
                calls.append(('reset',))

            correct_surface_collision(record, 7, vertical_step=2.0,
                                      adjust_contact=adjust,
                                      reset_vehicle_state=reset)
            self.assertEqual(struct.unpack_from('<f', record, 0x0C)[0], expected)
            self.assertEqual(calls, [('adjust', 7), ('reset',)])

    def test_child_updated_status_controls_offset(self):
        record = bytearray(0x4F8)
        struct.pack_into('<f', record, 0x0C, -4.0)

        def adjust(owner, _index):
            struct.pack_into('<i', owner, 0x36C, 9)

        correct_surface_collision(record, 0, vertical_step=6.0,
                                  adjust_contact=adjust,
                                  reset_vehicle_state=lambda _: None)
        self.assertEqual(struct.unpack_from('<f', record, 0x0C)[0], -1.0)


if __name__ == '__main__':
    unittest.main()
