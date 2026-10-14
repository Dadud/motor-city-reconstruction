import unittest

from client.lobby_channel_close import ChannelCloseRequest, native_close_arguments


class ChannelCloseTests(unittest.TestCase):
    def test_selector_stays_in_local_arguments(self):
        self.assertEqual(native_close_arguments(0x12345678,0x87654321),
                         bytes.fromhex('7856341221436587'))
        self.assertEqual(ChannelCloseRequest(0x87654321).frame().encode(),
                         bytes.fromhex('0105000887654321'))
        self.assertEqual(ChannelCloseRequest(0xffffffff).payload(),b'\xff' * 4)

    def test_raw_zero_encoding_does_not_select_interface_behavior(self):
        self.assertEqual(native_close_arguments(44,0),bytes.fromhex('2c00000000000000'))
        self.assertEqual(ChannelCloseRequest(0).frame().encode(),bytes.fromhex('0105000800000000'))

    def test_argument_bounds(self):
        for value in (-1,0x100000000,True,1.0,None):
            with self.assertRaises(ValueError): ChannelCloseRequest(value)
            with self.assertRaises(ValueError): native_close_arguments(value,1)
            with self.assertRaises(ValueError): native_close_arguments(1,value)


if __name__ == '__main__': unittest.main()
