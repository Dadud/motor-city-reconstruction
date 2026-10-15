from pathlib import Path
import struct
import tempfile
import unittest
from tools.binary_inventory import executable_format


class BinaryInventoryTests(unittest.TestCase):
    def test_extension_does_not_make_data_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'misleading.exe';path.write_bytes(b'authored data')
            self.assertEqual(executable_format(path), 'unrecognized-data')

    def test_pe_and_legacy_signatures(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fixture.dll'
            header=bytearray(64);header[:2]=b'MZ';struct.pack_into('<I',header,60,64)
            for signature,expected in ((b'PE\0\0','pe'),(b'NE\0\0','ne'),(b'xxxx','dos-mz')):
                path.write_bytes(header+signature)
                self.assertEqual(executable_format(path),expected)


if __name__=='__main__': unittest.main()
