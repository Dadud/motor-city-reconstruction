from pathlib import Path
import tempfile
import unittest

from client.assets import Assets


class TrackFileResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.track_dir = self.root / 'Data' / 'Tracks' / 'Drag'
        self.track_dir.mkdir(parents=True)

    def touch(self, name):
        path = self.track_dir / name
        path.touch()
        return path

    def test_native_night_wet_priority_and_fallback(self):
        candidates = [self.touch(name) for name in
                      ('Tr.frd', 'Trw.frd', 'Trn.frd', 'Trnw.frd')]
        assets = Assets(self.root)
        self.assertEqual(assets.track_file('Drag', '.frd', True, True), candidates[3])
        self.assertEqual(assets.track_file('Drag', '.frd', True, False), candidates[2])
        self.assertEqual(assets.track_file('Drag', '.frd', False, True), candidates[1])
        self.assertEqual(assets.track_file('Drag', '.frd', False, False), candidates[0])

    def test_missing_combined_variant_uses_next_enabled_variant(self):
        night = self.touch('trn0.fsh')
        assets = Assets(self.root)
        self.assertEqual(assets.track_file('drag', '0.fsh', True, True), night)

    def test_no_existing_candidate_returns_base_path(self):
        assets = Assets(self.root)
        self.assertEqual(assets.track_file('Drag', '.frd'),
                         self.track_dir / 'Tr.frd')

    def test_rejects_paths_in_track_or_suffix(self):
        assets = Assets(self.root)
        for track, suffix in (('../Drag', '.frd'), ('Drag', '../x'),
                              ('Drag\\Other', '.frd'), ('Drag', 'x/y')):
            with self.subTest(track=track, suffix=suffix), self.assertRaises(ValueError):
                assets.track_file(track, suffix)


if __name__ == '__main__':
    unittest.main()
