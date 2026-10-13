import struct
import unittest
from client.nps_persona import PersonaMaps


def entry(name):
    data = struct.pack('>4IH', 1, 2, 3, 4, len(name))+name
    return struct.pack('>H', len(data))+data


class PersonaMapTests(unittest.TestCase):
    def test_counted_records_and_opaque_final_byte(self):
        decoded = PersonaMaps.decode(b'\0\2'+entry(b'Motor City')+entry(b'n'*32)+b'\xff')
        self.assertEqual(len(decoded.entries), 2)
        self.assertEqual(decoded.entries[0].name, b'Motor City')
        self.assertEqual(decoded.entries[0].value_4, 4)
        self.assertEqual(decoded.trailing_value, 255)
        self.assertEqual(PersonaMaps.decode(b'\0\0\x01').entries, ())
        self.assertNotIn('Motor City', repr(decoded))

    def test_truncation_and_invalid_record_bounds(self):
        wire = b'\0\1'+entry(b'name')+b'\0'
        for data in (b'', wire[:-1], wire+b'x', b'\xff\xff\0',
                     b'\0\1'+entry(b'x'*33)+b'\0',
                     b'\0\1\0\1x\0'):
            with self.assertRaises(ValueError):
                PersonaMaps.decode(data)
