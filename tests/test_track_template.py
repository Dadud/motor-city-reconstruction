import unittest

from client.track_template import TRACK_TEMPLATE_BYTES, initialize_track_template


class TrackTemplateTests(unittest.TestCase):
    def test_copies_exact_template_prefix_and_preserves_tail(self):
        destination = bytearray(b'\xaa' * (len(TRACK_TEMPLATE_BYTES) + 8))
        result = initialize_track_template(destination)
        self.assertIs(result, destination)
        self.assertEqual(destination[:len(TRACK_TEMPLATE_BYTES)], TRACK_TEMPLATE_BYTES)
        self.assertEqual(destination[len(TRACK_TEMPLATE_BYTES):], b'\xaa' * 8)

    def test_rejects_read_only_or_short_destinations(self):
        with self.assertRaises(TypeError):
            initialize_track_template(bytes(len(TRACK_TEMPLATE_BYTES)))
        with self.assertRaises(ValueError):
            initialize_track_template(bytearray(len(TRACK_TEMPLATE_BYTES) - 1))


if __name__ == '__main__':
    unittest.main()
