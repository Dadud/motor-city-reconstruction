import struct
import unittest

from client.race_room_selection import prepare_race_room_selection
from client.room_join_request import build_room_join_argument


class RaceRoomSelectionTests(unittest.TestCase):
    def prepare(self, **updates):
        values = dict(game_mode=0,room_name=b'old-room',channel_id=0,ready_value=7,password=b'p',
                      value_0x78=0x12345678,value_0x90=0x87654321,value_0xa8=0xffffffff)
        values.update(updates)
        return prepare_race_room_selection(bytes(range(204)),**values)

    def test_metadata_mask_and_fields_preserve_other_bytes(self):
        selected = self.prepare()
        expected = bytearray(range(204))
        expected[0x64] &= 0xe1
        for offset,value in ((0x78,0x12345678),(0x90,0x87654321),(0xa8,0xffffffff)):
            struct.pack_into('<I',expected,offset,value)
        self.assertEqual(selected.metadata,bytes(expected))
        self.assertEqual(selected.name,b'old-room')
        self.assertNotIn("b'p'",repr(selected))

    def test_name_override_is_unsigned_and_metadata_not_rebuilt(self):
        for mode in (0x13,0x19):
            selected = self.prepare(game_mode=mode,channel_id=0xffffffff,ready_value=0x12345678)
            self.assertEqual(selected.name,b'4294967295')
            self.assertEqual(selected.max_ready,0x5678)
            self.assertEqual(selected.metadata,self.prepare().metadata)
            self.assertEqual(self.prepare(game_mode=mode,channel_id=0).name,b'old-room')
        self.assertEqual(self.prepare(game_mode=0x14,channel_id=999).name,b'old-room')

    def test_composition_preserves_verified_settings_padding(self):
        selected = self.prepare(game_mode=0x13,channel_id=9)
        fields = selected.room_inputs(0x12345678)
        self.assertEqual(fields.protocol,0x21)
        self.assertEqual(fields.opaque_data,selected.metadata + bytes(52))
        request = build_room_join_argument(fields,password=selected.password)
        self.assertEqual(request[0x50:0x150],selected.metadata + bytes(52))
        self.assertEqual(request[0x10:0x12],b'9\0')
        self.assertEqual(struct.unpack_from('<I',request,0)[0],0x12345678)

    def test_invalid_source_values_and_explicit_bounds(self):
        for values in (dict(channel_id=-1),dict(ready_value=0x100000000),dict(value_0x78=True),
                       dict(room_name=b'x' * 32),dict(password=b'x' * 17),dict(password=b'a\0b')):
            with self.assertRaises(ValueError): self.prepare(**values)
        with self.assertRaises(ValueError):
            prepare_race_room_selection(bytes(203),game_mode=0,room_name=b'',channel_id=0,
                ready_value=0,password=b'',value_0x78=0,value_0x90=0,value_0xa8=0)


if __name__ == '__main__': unittest.main()
