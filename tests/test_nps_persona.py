import unittest
from client.nps_persona import (encode_persona_maps_request,
    encode_persona_activation_request, native_persona_activation_result)


class PersonaRequestTests(unittest.TestCase):
    def test_exact_account_id_request(self):
        self.assertEqual(encode_persona_maps_request(0x12345678),
                         bytes.fromhex('05320010000000000000001012345678'))
        self.assertEqual(encode_persona_maps_request(0xffffffff)[12:], b'\xff'*4)

    def test_invalid_account_identity(self):
        for value in (0, -1, 2**32, True, '42'):
            with self.assertRaises(ValueError):
                encode_persona_maps_request(value)

    def test_activation_identity_order_and_header(self):
        self.assertEqual(encode_persona_activation_request(0x12345678, 42, 44),
            bytes.fromhex('050300180101000000000018123456780000002a0000002c'))
        self.assertEqual(encode_persona_activation_request(0, 0, 0)[12:], bytes(12))
        for position in range(3):
            for invalid in (-1, 2**32, True, '42'):
                values = [1, 42, 44]
                values[position] = invalid
                with self.assertRaises(ValueError):
                    encode_persona_activation_request(*values)

    def test_activation_reply_context(self):
        self.assertEqual(native_persona_activation_result(0x207), 0)
        self.assertEqual(native_persona_activation_result(0x612), -11)
        for opcode in (0x601, 0x607, 0x120, 0x308, 0xffff):
            self.assertEqual(native_persona_activation_result(opcode), -1)
        for invalid in (-1, 65536, True, '519'):
            with self.assertRaises(ValueError):
                native_persona_activation_result(invalid)
