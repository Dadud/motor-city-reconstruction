import unittest

from client.nps_framing import Frame, FrameDecoder, MessageHeader, encode_message, native_flags


class NPSFramingTests(unittest.TestCase):
    def test_recovered_header_offsets(self):
        wire = encode_message(0x501, b'\x00\xff', auxiliary=0x12345678)
        self.assertEqual(wire, bytes.fromhex('0501000e010100001234567800ff'))
        frame = FrameDecoder().feed(wire)[0]
        self.assertEqual(MessageHeader.from_frame(frame),
                         MessageHeader(0x501, 14, 0x101, 0, 0x12345678))

    def test_native_flag_range_edges(self):
        for value in (0x501, 0x51a, 0x521, 0x526):
            self.assertEqual(native_flags(value), 0x101)
        for value in (0x500, 0x51b, 0x520, 0x527, 0x601):
            self.assertEqual(native_flags(value), 0)

    def test_every_split_and_coalesced_frames(self):
        expected = [Frame(0xffff, b'\x00\xff'), Frame(1, b''), Frame(0x601, b'abc')]
        wire = b''.join(f.encode() for f in expected)
        for split in range(len(wire) + 1):
            decoder = FrameDecoder()
            self.assertEqual(decoder.feed(wire[:split]) + decoder.feed(wire[split:]), expected)
            decoder.finish()

    def test_single_byte_fragments(self):
        frame = Frame(0x601, bytes(range(256)))
        decoder = FrameDecoder()
        decoded = []
        for byte in frame.encode():
            decoded.extend(decoder.feed(bytes([byte])))
        self.assertEqual(decoded, [frame])
        decoder.finish()

    def test_short_frame_requires_explicit_header(self):
        frame = FrameDecoder().feed(bytes.fromhex('00010004'))[0]
        self.assertEqual(frame, Frame(1, b''))
        with self.assertRaises(ValueError):
            MessageHeader.from_frame(frame)

    def test_invalid_lengths_poison_decoder(self):
        for length in range(4):
            decoder = FrameDecoder()
            with self.assertRaises(ValueError):
                decoder.feed(bytes([0, 1, 0, length]))
            with self.assertRaises(ValueError):
                decoder.feed(Frame(1, b'').encode())

    def test_eof_detects_truncated_prefix_and_body(self):
        for data in (b'\x00', bytes.fromhex('06010008'), bytes.fromhex('0601000801')):
            decoder = FrameDecoder()
            decoder.feed(data)
            with self.assertRaises(ValueError):
                decoder.finish()

    def test_wire_size_boundary_and_sensitive_repr(self):
        frame = Frame(0xffff, b'x' * 65531)
        self.assertEqual(FrameDecoder().feed(frame.encode()), [frame])
        with self.assertRaises(ValueError):
            Frame(1, b'x' * 65532).encode()
        self.assertNotIn('secret', repr(Frame(1, b'secret')))


if __name__ == '__main__':
    unittest.main()
