import unittest
from client.nps_persona import encode_persona_maps_request


class PersonaRequestTests(unittest.TestCase):
    def test_exact_account_id_request(self):
        self.assertEqual(encode_persona_maps_request(0x12345678),
                         bytes.fromhex('05320010000000000000001012345678'))
        self.assertEqual(encode_persona_maps_request(0xffffffff)[12:], b'\xff'*4)

    def test_invalid_account_identity(self):
        for value in (0, -1, 2**32, True, '42'):
            with self.assertRaises(ValueError):
                encode_persona_maps_request(value)
