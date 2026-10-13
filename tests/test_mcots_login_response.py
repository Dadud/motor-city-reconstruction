import struct
import unittest
from client.mcots_framing import MCOTSFrame
from client.mcots_login_response import MCOTSLoginSuccess


class MCOTSLoginResponseTests(unittest.TestCase):
    def payload(self):
        payload = bytearray(range(173))
        struct.pack_into('<HI', payload, 0, 0xd5, 0x12345678)
        payload[6] = 0xfd
        for index in range(4):
            struct.pack_into('<I', payload, 0x21+index*26, (10, 0xff, 20, 30)[index])
        return bytes(payload)

    def test_unaligned_fields_and_service_boundaries(self):
        payload = self.payload()
        result = MCOTSLoginSuccess.from_frame(MCOTSFrame(17, 0, payload), transaction_value=17)
        self.assertEqual(result.session_value, 0x12345678)
        self.assertEqual(result.native_feature_bits, (True, False, True))
        self.assertEqual(result.opaque_07, payload[7:9])
        self.assertEqual(result.values_09, struct.unpack_from('<6I', payload, 9))
        self.assertEqual(result.values_89, struct.unpack_from('<9I', payload, 137))
        self.assertEqual([service.service_id for service in result.services], [10, 255, 20, 30])
        self.assertTrue(result.services[1].unused)
        self.assertEqual(result.services[3].opaque, payload[115:137])

    def test_extension_preserved_without_assigning_meaning(self):
        self.assertEqual(MCOTSLoginSuccess.decode(self.payload()+b'extra').extension, b'extra')

    def test_truncated_wrong_operation_and_transaction(self):
        for payload in (self.payload()[:-1], b'e\0'+self.payload()[2:], bytes(65527), 'x'):
            with self.assertRaises(ValueError):
                MCOTSLoginSuccess.decode(payload)
        with self.assertRaises(ValueError):
            MCOTSLoginSuccess.from_frame(MCOTSFrame(18, 0, self.payload()), transaction_value=17)
