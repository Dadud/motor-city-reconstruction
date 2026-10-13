import struct
import unittest
from client.nps_persona import PersonaMaps
from client.nps_framing import Frame, encode_message


def entry(name):
    data = struct.pack('>4IH', 1, 2, 3, 4, len(name))+name
    return struct.pack('>H', len(data))+data


class PersonaMapTests(unittest.TestCase):
    def test_counted_records_and_opaque_final_byte(self):
        decoded = PersonaMaps.decode(b'\0\2'+entry(b'Motor City')+entry(b'n'*32)+b'\xff')
        self.assertEqual(len(decoded.entries), 2)
        self.assertEqual(decoded.entries[0].name, b'Motor City')
        self.assertEqual(decoded.entries[0].value_4, 4)
        self.assertEqual(decoded.entries[0].account_user_id, 1)
        self.assertEqual(decoded.entries[0].persona_id, 2)
        self.assertEqual(decoded.entries[0].shard_id, 3)
        self.assertEqual(decoded.trailing_value, 255)
        self.assertEqual(PersonaMaps.decode(b'\0\0\x01').entries, ())
        self.assertNotIn('Motor City', repr(decoded))

    def test_full_response_and_selection_require_shard(self):
        payload = b'\0\1'+entry(b'name')+b'\0'
        wire = encode_message(0x607, payload, auxiliary=len(payload)+12)
        maps = PersonaMaps.from_frame(Frame(0x607, wire[4:]))
        self.assertEqual(maps.find(2, 3).name, b'name')
        self.assertIsNone(maps.find(2, 44))
        self.assertIsNone(maps.find(1, 3))
        for bad in (Frame(0x601, wire[4:]), Frame(0x607, b'\0\0\0')):
            with self.assertRaises(ValueError):
                PersonaMaps.from_frame(bad)
        with self.assertRaises(ValueError):
            maps.find(True, 3)

    def test_truncation_and_invalid_record_bounds(self):
        wire = b'\0\1'+entry(b'name')+b'\0'
        for data in (b'', wire[:-1], wire+b'x', b'\xff\xff\0',
                     b'\0\1'+entry(b'x'*33)+b'\0',
                     b'\0\1\0\1x\0'):
            with self.assertRaises(ValueError):
                PersonaMaps.decode(data)
