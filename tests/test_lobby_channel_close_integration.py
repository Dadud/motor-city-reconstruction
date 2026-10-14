import struct
import unittest

from client.lobby_channel_close import ChannelCloseRequest, native_close_arguments
from client.lobby_cipher import DESChaining
from client.lobby_envelope import decrypt_envelope
from client.lobby_send import prepare_outgoing_frame
from client.lobby_session import LobbyCiphers
from client.room_disconnect_flow import RoomDisconnectFlow


class ChannelCloseIntegrationTests(unittest.TestCase):
    def test_room_flow_local_routing_is_separate_from_encrypted_payload(self):
        image = bytearray(0x3c0)
        struct.pack_into('<H', image, 0xec, 1)
        struct.pack_into('<I', image, 0x39c, 44)
        struct.pack_into('<I', image, 0xc0, 0x87654321)
        flow = RoomDisconnectFlow(bytes(image), wait_for_completion=True)
        flow.container_reset(flow.room_image)
        flow.container_reset(flow.room_image)
        self.assertEqual(flow.action.argument, native_close_arguments(44, 0x87654321))
        selector, channel = struct.unpack('<II', flow.action.argument)
        self.assertEqual(selector, 44)
        inner = ChannelCloseRequest(channel).frame()
        self.assertEqual(inner.body, b'\x87\x65\x43\x21')
        ciphers = LobbyCiphers(DESChaining(b'12345678'), DESChaining(b'12345678', decrypt=True))
        try:
            wire = prepare_outgoing_frame(inner, ciphers, padding=b'')
            self.assertEqual(wire.message_id, 0x1101)
            self.assertEqual(decrypt_envelope(wire, ciphers.receive).inner, inner)
        finally:
            ciphers.send.finish()
            ciphers.receive.finish()

    def test_two_close_frames_share_one_cipher_chain(self):
        ciphers = LobbyCiphers(DESChaining(b'12345678'), DESChaining(b'12345678', decrypt=True))
        try:
            for channel in (7, 0xffffffff):
                inner = ChannelCloseRequest(channel).frame()
                wire = prepare_outgoing_frame(inner, ciphers, padding=b'')
                self.assertEqual(decrypt_envelope(wire, ciphers.receive).inner, inner)
        finally:
            ciphers.send.finish()
            ciphers.receive.finish()
