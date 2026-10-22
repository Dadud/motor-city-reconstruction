import tempfile
import unittest
from pathlib import Path

from client.track_lighting import (read_object_color_percentages,
                                   track_lighting_ini)


class TrackLightingTests(unittest.TestCase):
    def test_ini_variant_matches_native_flag_selection(self):
        base = Path('tracks') / 'Example'
        self.assertEqual(track_lighting_ini(base).name, 'Tr.ini')
        self.assertEqual(track_lighting_ini(base, night=True).name, 'TrN.ini')
        self.assertEqual(track_lighting_ini(base, weather=True).name, 'TrW.ini')
        self.assertEqual(track_lighting_ini(base, night=True, weather=True).name,
                         'TrNW.ini')

    def test_reads_and_clamps_native_ambient_rgb_percentages(self):
        source = '''[other]\nAmbientRed=10\n[light]\nAmbientRed=240
AmbientGreen=-3\nAmbientBlue=71\n[other]\nAmbientRed=20\n'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Tr.ini'
            path.write_text(source, encoding='latin-1')
            self.assertEqual(read_object_color_percentages(path), (200, 0, 71))

    def test_missing_color_keys_keep_neutral_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Tr.ini'
            path.write_text('[light]\nAmbientRed=120\n', encoding='latin-1')
            self.assertEqual(read_object_color_percentages(path), (120, 100, 100))


if __name__ == '__main__':
    unittest.main()
