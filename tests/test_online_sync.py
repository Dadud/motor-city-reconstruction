import tempfile
import unittest
from pathlib import Path

from client.online_sync import load_online_sync_settings, summarize_online_sync


class OnlineSyncTests(unittest.TestCase):
    def test_reads_declared_position_update_rate(self):
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory) / 'Scripts'
            scripts.mkdir()
            (scripts / 'MCOExOps.ini').write_text(
                '[Netcode]\nFast Join=1 // TCP\nPositional Updates=2 // 32Hz\n'
                '[Install]\nServer Certificate=' + ('AB' * 20) + '\n'
            )
            settings = load_online_sync_settings(directory)
            summary = summarize_online_sync(settings)
            self.assertTrue(summary['fast_join_tcp_preferred'])
            self.assertEqual(summary['positional_updates_hz'], 32)
            self.assertAlmostEqual(summary['update_interval_seconds'], 1 / 32)


if __name__ == '__main__':
    unittest.main()

