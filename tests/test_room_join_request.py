import struct
import unittest

from client.room_join_request import RoomJoinInputs, build_room_join_argument


class RoomJoinRequestTests(unittest.TestCase):
    def test_observed_fields_and_no_password_defaults(self):
        inputs = RoomJoinInputs(44, 0x42, 0x12345678, b'LOBBY', 16, bytes(range(256)))
        raw = build_room_join_argument(inputs)
        self.assertEqual(len(raw), 0x15c)
        self.assertEqual(struct.unpack_from('<4I', raw), (44,0x42,0x12345678,2))
        self.assertEqual(raw[0x10:0x34], b'LOBBY' + bytes(31))
        self.assertEqual(raw[0x34:0x50], bytes(28))
        self.assertEqual(raw[0x50:0x150], bytes(range(256)))
        self.assertEqual(struct.unpack_from('<HHII', raw, 0x150), (16,2,0,0))
        self.assertEqual(raw[0x30:0x34], bytes(4))

    def test_password_flags_wait_callback_and_explicit_owner(self):
        inputs = RoomJoinInputs(0xffffffff, 0x21, 1, b'n' * 31, 65535, bytes(256))
        raw = build_room_join_argument(inputs, password=b'p' * 16, flag_0x20=True,
                                       wait_for_completion=True, owner_token=0x71000000)
        self.assertEqual(struct.unpack_from('<I', raw, 0xc)[0], 0x21)
        self.assertEqual(raw[0x10:0x30], b'n' * 31 + b'\0')
        self.assertEqual(raw[0x34:0x45], b'p' * 16 + b'\0')
        self.assertEqual(struct.unpack_from('<HHII', raw, 0x150), (65535,1,0x44d740,0x71000000))

    def test_room_image_source_offsets(self):
        image = bytearray(b'\xa5' * 0x3b8)
        struct.pack_into('<I', image, 0x39c, 44)
        struct.pack_into('<I', image, 0xcc, 0x42)
        struct.pack_into('<I', image, 0xc0, 9)
        image[0xa0:0xc0] = b'name\0' + b'\xa5' * 27
        struct.pack_into('<H', image, 0xe6, 7)
        image[0xf4:0x1f4] = bytes(range(256))
        self.assertEqual(RoomJoinInputs.from_room_image(bytes(image)),
                         RoomJoinInputs(44,0x42,9,b'name',7,bytes(range(256))))
        image[0xa0:0xc0] = b'x' * 32
        with self.assertRaises(ValueError): RoomJoinInputs.from_room_image(bytes(image))

    def test_bounds_and_owner_are_not_inferred(self):
        valid = RoomJoinInputs(1,0x21,0,b'',0,bytes(256))
        for password in (b'x' * 17,b'a\0b','password'):
            with self.assertRaises(ValueError): build_room_join_argument(valid,password=password)
        with self.assertRaises(ValueError): build_room_join_argument(valid,wait_for_completion=True)
        with self.assertRaises(ValueError): build_room_join_argument(valid,owner_token=1)
        with self.assertRaises(TypeError): build_room_join_argument(valid,flag_0x20=1)
        for size in (0,0x39f,65537):
            with self.assertRaises(ValueError): RoomJoinInputs.from_room_image(bytes(size))
        with self.assertRaises(ValueError): RoomJoinInputs(1,0x21,0,b'x' * 32,0,bytes(256))
        with self.assertRaises(ValueError): RoomJoinInputs(-1,0x21,0,b'',0,bytes(256))
        with self.assertRaises(ValueError): RoomJoinInputs(1,0x21,0,b'',65536,bytes(256))
        with self.assertRaises(ValueError): RoomJoinInputs(1,0x21,0,b'',0,bytes(255))


if __name__ == '__main__': unittest.main()
