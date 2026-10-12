import struct
import unittest

from client.nps_response import AuthorizationRecord, LoginSuccess


def counted(value):
    return struct.pack('>H', len(value)) + value


def synthetic_success():
    first = struct.pack('>III', 7, 1, 1234) + counted(b'name') + counted(b'a') + counted(b'b')
    second = struct.pack('>III', 9, 0, 0) + counted(b'')*3
    session = counted(bytes(range(32))) + struct.pack('>I', 0x12345678)
    return (struct.pack('>IIB', 42, 99, 2) + counted(first) + counted(second)
            + counted(session) + struct.pack('>I', 88) + counted(b'final'))


class SuccessTests(unittest.TestCase):
    def test_recovered_fields(self):
        reply = LoginSuccess.decode(synthetic_success())
        self.assertEqual((reply.user_id, reply.value_2, reply.flag, reply.value_3),
                         (42, 99, True, 88))
        self.assertEqual(reply.authorization_1,
                         AuthorizationRecord(7, 1, 1234, b'name', b'a', b'b'))
        self.assertEqual(reply.session.material, bytes(range(32)))
        self.assertEqual(reply.session.value, 0x12345678)
        self.assertEqual(reply.text, b'final')

    def test_each_truncation_and_trailing_bytes(self):
        wire = synthetic_success()
        for size in range(len(wire)):
            with self.assertRaises(ValueError):
                LoginSuccess.decode(wire[:size])
        with self.assertRaises(ValueError):
            LoginSuccess.decode(wire + b'x')

    def test_nested_lengths_are_enforced(self):
        wire = bytearray(synthetic_success())
        wire[9:11] = b'\x00\x01'
        with self.assertRaises(ValueError):
            LoginSuccess.decode(bytes(wire))
        wire = bytearray(synthetic_success())
        wire[23:25] = b'\x00\x41'  # first record name exceeds native 64-byte limit
        with self.assertRaises(ValueError):
            LoginSuccess.decode(bytes(wire))

    def test_expiry_matches_native_signed_comparison(self):
        for enabled, expiry, now, expected in ((0, 0, 1, False), (2, 0, 1, True),
                                               (1, 10, 9, True), (1, 10, 10, False),
                                               (1, 0xffffffff, 1, False)):
            record = AuthorizationRecord(0, enabled, expiry, b'', b'', b'')
            self.assertEqual(record.active_at(now), expected)

    def test_sensitive_fields_excluded_from_repr(self):
        representation = repr(LoginSuccess.decode(synthetic_success()))
        self.assertNotIn("b'name'", representation)
        self.assertNotIn("b'final'", representation)
        self.assertNotIn('material=', representation)
