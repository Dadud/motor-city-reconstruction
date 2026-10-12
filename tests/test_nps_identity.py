import unittest

from client.nps_identity import SERVICE_ID, executable_checksum


class IdentityTests(unittest.TestCase):
    def test_recovered_service_and_raw_crc(self):
        self.assertEqual(SERVICE_ID, '2176')
        self.assertEqual(executable_checksum(b''), 0xffffffff)
        self.assertEqual(executable_checksum(b'123456789'), 0x340bc6d9)

    def test_binary_input_changes_checksum(self):
        self.assertNotEqual(executable_checksum(b'\0\xff'), executable_checksum(b'\xff\0'))
        with self.assertRaises(TypeError):
            executable_checksum('text')
