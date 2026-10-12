import unittest
from unittest.mock import Mock, patch

from client.nps_framing import FrameDecoder, MessageHeader
from client.nps_login import LoginPayload
from client.nps_session_request import prepare_login


class PreparedLoginTests(unittest.TestCase):
    def test_assembles_recovered_fields_and_retains_private_material(self):
        key = Mock()
        key.encrypt_hex.return_value = b'AB'*128
        with patch('client.nps_session_request.installed_public_key', return_value=key), \
             patch('client.nps_session_request.installed_executable_checksum', return_value=0x12345678), \
             patch('client.nps_session_request.secrets.token_bytes', side_effect=[bytes(range(32)), bytes(20)]) as entropy:
            prepared = prepare_login('external', b'synthetic-ticket', key_record_value=3)
        self.assertEqual(entropy.call_args_list[0].args, (32,))
        key.encrypt_hex.assert_called_once_with(
            b'\x00\x20'+bytes(range(32))+b'\x00\x00\x00\x03', bytes(20))
        frame = FrameDecoder().feed(prepared.wire)[0]
        self.assertEqual(frame.message_id, 0x501)
        self.assertEqual(MessageHeader.from_frame(frame).auxiliary, len(prepared.wire))
        payload = LoginPayload.decode(frame.body[8:])
        self.assertEqual((payload.ticket, payload.authorization_mode, payload.service_id,
                          payload.caller_value), (b'synthetic-ticket', 0, b'2176', 0x12345678))
        self.assertEqual(prepared.session_material, bytes(range(32)))
        self.assertNotIn('ticket', repr(prepared))
        self.assertNotIn('wire=', repr(prepared))

    def test_invalid_fields_rejected_before_entropy(self):
        with patch('client.nps_session_request.installed_public_key'), \
             patch('client.nps_session_request.installed_executable_checksum', return_value=1), \
             patch('client.nps_session_request.secrets.token_bytes') as entropy:
            with self.assertRaises(ValueError):
                prepare_login('external', b'ticket', key_record_value=-1)
            entropy.assert_not_called()
