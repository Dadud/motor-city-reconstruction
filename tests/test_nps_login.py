import unittest

from client.nps_login import LoginPayload


class LoginPayloadTests(unittest.TestCase):
    def test_observed_serialization_order(self):
        value = LoginPayload(b'T', 1, b'K', b'S', 0x12345678)
        wire = bytes.fromhex('000154000100014b00015312345678')
        self.assertEqual(value.encode(), wire)
        self.assertEqual(LoginPayload.decode(wire), value)

    def test_original_capacity_limits(self):
        value = LoginPayload(b't'*128, 0, b'k'*512, b's'*64, 0xffffffff)
        self.assertEqual(len(value.encode()), 716)
        self.assertEqual(LoginPayload.decode(value.encode()), value)
        for args in ((b't'*129, 0, b'', b'', 0),
                     (b'', 0, b'k'*513, b'', 0),
                     (b'', 0, b'', b's'*65, 0),
                     (b't\0', 0, b'', b'', 0)):
            with self.assertRaises(ValueError):
                LoginPayload(*args).encode()

    def test_every_truncation_and_trailing_data(self):
        wire = LoginPayload(b'ticket', 0, b'opaque', b'service', 1).encode()
        for size in range(len(wire)):
            with self.assertRaises(ValueError):
                LoginPayload.decode(wire[:size])
        with self.assertRaises(ValueError):
            LoginPayload.decode(wire + b'x')

    def test_bad_integer_ranges_and_sensitive_repr(self):
        for mode, caller in ((-1, 0), (65536, 0), (0, -1), (0, 2**32)):
            with self.assertRaises(ValueError):
                LoginPayload(b'', mode, b'', b'', caller).encode()
        representation = repr(LoginPayload(b'secret-ticket', 0, b'secret-key', b'S', 0))
        self.assertNotIn('secret', representation)
