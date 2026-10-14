import unittest
from unittest.mock import patch, MagicMock
from client.auth_protocol import TicketResponse
from client.nps_persona import PersonaMaps, PersonaMapEntry
from client.nps_session_request import PreparedLogin
from client.online_account import authenticate, OnlineAccount, AuthorizationDenied
from client.server_discovery import Endpoint, Shard, AuthSettings


class OnlineAccountTests(unittest.TestCase):
    shard = Shard('fixture', '', 44, Endpoint('host', 8226), Endpoint('host', 7003),
                  Endpoint('host', 43300), 0, ())
    settings = AuthSettings('host', 'AuthLogin')

    def test_authorization_denial_stops_before_binary_login(self):
        with patch('client.online_account.installed_public_key'), \
             patch('client.online_account.installed_executable_checksum'), \
             patch('client.online_account.authorize', return_value=TicketResponse(False, '1', 'private', '')), \
             patch('client.online_account.prepare_login') as prepare:
            with self.assertRaises(AuthorizationDenied) as context:
                authenticate('fixture', self.shard, self.settings, 'A'*40, 'user', 'password', key_record_value=9)
            self.assertEqual(context.exception.reason_code, '1')
            self.assertNotIn('private', str(context.exception))
            prepare.assert_not_called()

    def test_success_handoff_preserves_ticket_account_and_request_material(self):
        stages = []
        prepared = PreparedLogin(b'fixture', b'c'*32)
        account = MagicMock(user_id=123, prepared_login=prepared)
        maps = PersonaMaps((PersonaMapEntry(99, 42, 44, 0, b'name'),), 1)
        with patch('client.online_account.installed_public_key'), \
             patch('client.online_account.installed_executable_checksum'), \
             patch('client.online_account.authorize', return_value=TicketResponse(True, '0', '', 'private-ticket')) as authorize, \
             patch('client.online_account.prepare_login', return_value=prepared) as prepare, \
             patch('client.online_account.login', return_value=account) as login, \
             patch('client.online_account.fetch_personas', return_value=maps) as fetch:
            result = authenticate('fixture', self.shard, self.settings, 'A'*40, 'user', 'password', key_record_value=9, on_stage=stages.append)
            self.assertEqual(stages, ['login', 'personas'])
            self.assertIs(result.account, account)
            self.assertIs(result.personas, maps)
            prepare.assert_called_once_with('fixture', b'private-ticket', key_record_value=9)
            login.assert_called_once_with(self.shard.login, prepared)
            fetch.assert_called_once_with(self.shard.login, 123)
            self.assertEqual(authorize.call_args.args[-1], '2176')
            self.assertNotIn('private-ticket', repr(result))

    def test_selected_shard_activation_uses_login_account_not_map_account(self):
        prepared = PreparedLogin(b'', b'c'*32)
        account = MagicMock(user_id=123, prepared_login=prepared)
        maps = PersonaMaps((PersonaMapEntry(99, 42, 45, 0, b'wrong'),
                            PersonaMapEntry(99, 42, 44, 0, b'name')), 1)
        online = OnlineAccount(self.shard, account, maps)
        with patch('client.online_account.activate_persona') as activate, \
             patch('client.online_account.connect_lobby') as connect:
            result = online.enter_lobby(42, hostname=b'host', ip_address=b'127.0.0.1')
            self.assertIs(result, connect.return_value)
            activate.assert_called_once_with(self.shard.login, 123, 42, 44)
            payload = connect.call_args.args[1]
            self.assertEqual((payload.user_id, payload.username, payload.value_200), (42, b'name', 123))
            self.assertIs(connect.call_args.args[2], prepared)
        with patch('client.online_account.activate_persona') as activate:
            with self.assertRaises(ValueError):
                online.enter_lobby(7, hostname=b'host', ip_address=b'127.0.0.1')
            with self.assertRaises(ValueError):
                online.enter_lobby(42, hostname=b'x'*64, ip_address=b'127.0.0.1')
            activate.assert_not_called()

    def test_primary_handoff_order_identity_key_and_owned_cleanup(self):
        prepared = PreparedLogin(b'', b'c'*32)
        online = OnlineAccount(self.shard, MagicMock(user_id=123, prepared_login=prepared),
            PersonaMaps((PersonaMapEntry(99, 42, 44, 0, b'name'),), 1))
        calls = MagicMock()
        with patch.object(OnlineAccount, 'enter_lobby', return_value=MagicMock()) as lobby, \
             patch('client.online_account.connect_primary', return_value=MagicMock()) as primary:
            calls.attach_mock(lobby, 'lobby')
            calls.attach_mock(primary, 'primary')
            with online.enter_connections(42, hostname=b'host', ip_address=b'127.0.0.1') as joined:
                self.assertEqual([call[0] for call in calls.mock_calls], ['lobby', 'primary'])
                endpoint, record, material = primary.call_args.args
                self.assertEqual(endpoint, self.shard.transactions)
                self.assertEqual((record.account_user_id, record.persona_id, record.persona_name),
                                 (123, 42, b'name'))
                self.assertEqual((record.value_120, record.value_124, record.value_128), (0, 0, 0))
                self.assertEqual(material, prepared.session_material)
                self.assertIs(joined.lobby, lobby.return_value)
            primary.return_value.close.assert_called_once_with()
            lobby.return_value.close.assert_called_once_with()
        with patch.object(OnlineAccount, 'enter_lobby', return_value=MagicMock()) as lobby, \
             patch('client.online_account.connect_primary', side_effect=ValueError('rejected')):
            stages = []
            with self.assertRaisesRegex(ValueError, 'rejected'):
                online.enter_connections(42, hostname=b'host', ip_address=b'127.0.0.1', on_stage=stages.append)
            self.assertEqual(stages, ['primary'])
            lobby.return_value.close.assert_called_once_with()

    def test_invalid_primary_inputs_do_not_activate_persona(self):
        online = OnlineAccount(self.shard,
            MagicMock(user_id=123, prepared_login=PreparedLogin(b'', b'c'*31)),
            PersonaMaps((PersonaMapEntry(99, 42, 44, 0, b'name'),), 1))
        with patch('client.online_account.activate_persona') as activate:
            with self.assertRaises(ValueError):
                online.enter_connections(42, hostname=b'host', ip_address=b'127.0.0.1')
            activate.assert_not_called()
