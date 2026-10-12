import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from viv import inventory, read_member


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'sample.viv'
        self.valid = struct.pack('>4sIII', b'BIGF', 29, 1, 26) + struct.pack('>II', 26, 3) + b'a\0xyz'
        self.path.write_bytes(self.valid)

    def test_member(self):
        self.assertEqual(inventory(self.path)[0]['name'], 'a')
        self.assertEqual(read_member(self.path, 'a'), b'xyz')

    def test_bounds(self):
        value = bytearray(self.valid)
        struct.pack_into('>I', value, 16, 27)
        self.path.write_bytes(value)
        with self.assertRaises(ValueError):
            inventory(self.path)

    def test_truncated(self):
        self.path.write_bytes(self.valid[:12])
        with self.assertRaises(ValueError):
            inventory(self.path)

    def test_missing_and_budget(self):
        with self.assertRaises(KeyError):
            read_member(self.path, 'missing')
        with self.assertRaises(ValueError):
            read_member(self.path, 'a', max_bytes=2)
