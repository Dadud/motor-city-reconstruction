import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from client.fanserver_test import (FanServerSetupError, prepare_context, run_test,
                                 run_test_report, shareable_report)
from client.server_discovery import AuthSettings, DiscoverySource, Endpoint, Shard


class FanServerTestTests(unittest.TestCase):
    shard = Shard('MotorCity Revival', '', 44, Endpoint('host', 1), Endpoint('host', 2),
                  Endpoint('host', 3), None, ())

    def test_failure_report_retains_real_stage_without_exception_details(self):
        def fail(*args, on_stage, **kwargs):
            on_stage('authorization')
            on_stage('login')
            raise TimeoutError('password=private ticket=secret https://private')
        with patch('client.fanserver_test.run_test', side_effect=fail):
            result = run_test_report('external', 'private-user', 'private-password')
        self.assertFalse(result['success'])
        self.assertEqual(result['last_stage'], 'login')
        self.assertEqual(result['failure_code'], 'timeout')
        self.assertNotIn('private', repr(result))
        self.assertNotIn('secret', repr(result))

    def test_authorization_rejection_has_fixed_failure_code(self):
        from client.online_account import AuthorizationDenied
        with patch('client.fanserver_test.run_test', side_effect=AuthorizationDenied(42)):
            result = run_test_report('external', 'user', 'password')
        self.assertEqual(result['failure_code'], 'authorization_denied')
        self.assertNotIn('42', repr(result))

    def test_shared_report_excludes_persona_and_arbitrary_payloads(self):
        result = shareable_report({'success': True, 'last_stage': 'complete',
            'persona_count': 2, 'garage_record_count': 'private', 'password': 'secret',
            'shard_name': 'private server', 'selected_persona_id': 9,
            'failure_code': 'secret', 'account_authenticated': 'secret',
            'server_version': 'private', 'scope': 'secret'})
        self.assertEqual(result['persona_count'], 2)
        self.assertFalse(result['live_race_tested'])
        self.assertNotIn('private', repr(result))
        self.assertNotIn('secret', repr(result))
        self.assertNotIn('selected_persona_id', result)

    def test_prepare_context_requires_explicit_source_when_urls_differ(self):
        with patch('client.fanserver_test.installed_sources', return_value=(
                DiscoverySource('a.ini', 'https://one'),
                DiscoverySource('b.ini', 'https://two'),
        )):
            with self.assertRaises(FanServerSetupError):
                prepare_context('external', shard_id=44)

    def test_run_test_reports_garage_counts(self):
        entry = SimpleNamespace(persona_id=9, shard_id=44, name=b'Racer' + bytes([0]))
        personas = SimpleNamespace(entries=(entry,), find=lambda persona_id, shard_id: entry)
        account = MagicMock()
        account.personas = personas
        connections = MagicMock()
        connections.__enter__.return_value = SimpleNamespace(primary=SimpleNamespace(session=object()))
        account.enter_connections.return_value = connections
        startup = SimpleNamespace(car_pairs=(b'one', b'two'), part_seeds=(b'seed',),
                                  part_slots=(b'slot', b'slot2'))
        context = SimpleNamespace(
            root='external', shard=self.shard, auth=AuthSettings('host', 'AuthLogin'),
            certificate_sha1='A' * 40, hostname=b'host', ip_address=b'127.0.0.1',
            fetch_garage=True, catalogue=None, text_encoding='cp1252', probe_race_entry=False)
        with patch('client.fanserver_test.prepare_context', return_value=context):
            with patch('client.fanserver_test.authenticate', return_value=account):
                with patch('client.fanserver_test.MCOTSDataClient') as client_cls:
                    with patch('client.fanserver_test.fetch_persona_startup', return_value=startup):
                        client_cls.return_value = object()
                        result = run_test('external', 'user', 'password', persona_id=9)
        self.assertTrue(result['success'])
        self.assertEqual(result['garage_record_count'], 2)
        self.assertEqual(result['part_seed_count'], 1)
        self.assertEqual(result['part_slot_count'], 2)
        account.enter_connections.assert_called_once()

    def test_run_test_reports_race_entry_probe(self):
        entry = SimpleNamespace(persona_id=9, shard_id=44, name=b'Racer' + bytes([0]))
        personas = SimpleNamespace(entries=(entry,), find=lambda persona_id, shard_id: entry)
        account = MagicMock()
        account.personas = personas
        connections = MagicMock()
        connections.__enter__.return_value = SimpleNamespace(primary=SimpleNamespace(session=object()))
        account.enter_connections.return_value = connections
        context = SimpleNamespace(
            root='external', shard=self.shard, auth=AuthSettings('host', 'AuthLogin'),
            certificate_sha1='A' * 40, hostname=b'host', ip_address=b'127.0.0.1',
            fetch_garage=False, catalogue=None, text_encoding='cp1252', probe_race_entry=True)
        with patch('client.fanserver_test.prepare_context', return_value=context):
            with patch('client.fanserver_test.authenticate', return_value=account):
                with patch('client.fanserver_test.installed_patch_settings', return_value=object()):
                    with patch('client.fanserver_test.probe_race_entry_path', return_value={
                        'race_entry_probe_passed': False,
                        'fast_join_tcp_preferred': None,
                        'positional_updates_hz': 32,
                        'update_interval_seconds': None,
                        'recovered_task_kinds': [],
                        'room_channel_probe_passed': False,
                        'race_entry_implemented': False,
                        'missing_task_order': True,
                        'missing_authenticated_arguments': True,
                        'protocol_selection_unverified': True,
                    }):
                        result = run_test('external', 'user', 'password', persona_id=9, probe_race_entry=True)
        self.assertTrue(result['success'])
        self.assertFalse(result['race_entry_probe_passed'])
        self.assertEqual(result['positional_updates_hz'], 32)
        self.assertFalse(result['room_channel_probe_passed'])
        self.assertIsNone(result['update_interval_seconds'])
        self.assertTrue(result['missing_authenticated_arguments'])

    def test_run_test_records_last_stage(self):
        context = SimpleNamespace(
            root='external', shard=self.shard, auth=AuthSettings('host', 'AuthLogin'),
            certificate_sha1='A' * 40, hostname=b'host', ip_address=b'127.0.0.1',
            fetch_garage=False, catalogue=None, text_encoding='cp1252', probe_race_entry=False)
        with patch('client.fanserver_test.prepare_context', return_value=context):
            with patch('client.fanserver_test.authenticate') as authenticate:
                authenticate.side_effect = RuntimeError('stop')
                with self.assertRaises(RuntimeError):
                    run_test('external', 'user', 'password', persona_id=9)
        # authenticate is called after authorization stage is recorded
        authenticate.assert_called_once()

    def test_cancelled_before_authorization(self):
        context = SimpleNamespace(
            root='external', shard=self.shard, auth=AuthSettings('host', 'AuthLogin'),
            certificate_sha1='A' * 40, hostname=b'host', ip_address=b'127.0.0.1',
            fetch_garage=False, catalogue=None, text_encoding='cp1252', probe_race_entry=False)
        with patch('client.fanserver_test.prepare_context', return_value=context):
            with patch('client.fanserver_test.authenticate') as authenticate:
                result = run_test('external', 'user', 'password', cancelled=lambda: True)
        self.assertTrue(result['cancelled'])
        self.assertFalse(result['success'])
        authenticate.assert_not_called()

    def test_cancelled_after_preflight_records_last_stage(self):
        context = SimpleNamespace(
            root='external', shard=self.shard, auth=AuthSettings('host', 'AuthLogin'),
            certificate_sha1='A' * 40, hostname=b'host', ip_address=b'127.0.0.1',
            fetch_garage=False, catalogue=None, text_encoding='cp1252', probe_race_entry=False)
        with patch('client.fanserver_test.prepare_context', return_value=context):
            with patch('client.fanserver_test.authenticate') as authenticate:
                result = run_test('external', 'user', 'password', cancelled=lambda: True)
        self.assertTrue(result['cancelled'])
        self.assertEqual(result['last_stage'], 'preflight')
        authenticate.assert_not_called()
