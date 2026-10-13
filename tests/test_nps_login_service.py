import struct
import unittest
from unittest.mock import patch, call
from client.nps_framing import Frame, encode_message
from client.nps_login_service import login, LoginRequestError
from client.nps_session_request import PreparedLogin
from client.server_discovery import Endpoint


def success_frame():
    auth = struct.pack('>3I3H', 0, 1, 0, 0, 0, 0)
    key = struct.pack('>H', 32)+b'r'*32+struct.pack('>I', 9)
    payload = struct.pack('>2IB', 123, 456, 1)
    for record in (auth, auth, key):
        payload += struct.pack('>H', len(record))+record
    payload += struct.pack('>IH', 0, 0)
    return Frame(0x601, encode_message(0x601, payload)[4:])


class LoginServiceTests(unittest.TestCase):
    endpoint = Endpoint('configured.example', 8226)
    prepared = PreparedLogin(encode_message(0x501, b'fixture'), b'c'*32)

    def test_acknowledgement_then_success_retains_request_key(self):
        with patch('client.nps_login_service.NPSConnection.connect') as connect:
            connection = connect.return_value.__enter__.return_value
            connection.receive.side_effect = [Frame(0xdead, b'ack'), success_frame()]
            account = login(self.endpoint, self.prepared)
            self.assertEqual(account.user_id, 123)
            self.assertEqual(account.acknowledgement_id, 0xdead)
            self.assertIs(account.prepared_login, self.prepared)
            self.assertEqual(account.response.session.material, b'r'*32)
            connection.receive.assert_has_calls([call(timeout=30), call(timeout=120)])
            connection.send.assert_called_once_with(self.prepared.wire)
            connect.return_value.__exit__.assert_called_once()
            self.assertNotIn('cccc', repr(account))
            self.assertNotIn('rrrr', repr(account))

    def test_rejections_never_return_an_authenticated_account(self):
        for opcode, result in ((0x602, -11), (0x610, -106), (0x623, -142),
                               (0x626, -127), (0x637, -141), (0x207, -1)):
            with patch('client.nps_login_service.NPSConnection.connect') as connect:
                connection = connect.return_value.__enter__.return_value
                connection.receive.side_effect = [Frame(0x207, b''), Frame(opcode, b'secret')]
                with self.assertRaises(LoginRequestError) as context:
                    login(self.endpoint, self.prepared)
                self.assertEqual(context.exception.native_result, result)
                self.assertNotIn('secret', str(context.exception))
                connect.return_value.__exit__.assert_called_once()

    def test_missing_second_reply_and_bad_preparation_fail(self):
        with patch('client.nps_login_service.NPSConnection.connect') as connect:
            connection = connect.return_value.__enter__.return_value
            connection.receive.side_effect = [Frame(0x601, b''), EOFError('closed')]
            with self.assertRaises(EOFError):
                login(self.endpoint, self.prepared)
            connect.return_value.__exit__.assert_called_once()
        with patch('client.nps_login_service.NPSConnection.connect') as connect:
            for prepared in (PreparedLogin(b'bad', b'c'*32),
                             PreparedLogin(encode_message(0x503), b'c'*32),
                             PreparedLogin(self.prepared.wire, b'r'*8)):
                with self.assertRaises(ValueError):
                    login(self.endpoint, prepared)
            connect.assert_not_called()
