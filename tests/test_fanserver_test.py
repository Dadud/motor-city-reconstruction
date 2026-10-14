import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from client.fanserver_test import FanServerSetupError, prepare_context, run_test
from client.server_discovery import AuthSettings, DiscoverySource, Endpoint, Shard


class FanServerTestTests(unittest.TestCase):
    shard = Shard('MotorCity Revival', '', 44, Endpoint('host', 1), Endpoint('host', 2),
                  Endpoint('host', 3), None, ())

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
            fetch_garage=True, catalogue=None, text_encoding='cp1252')
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

    def test_run_test_records_last_stage(self):
        context = SimpleNamespace(
            root='external', shard=self.shard, auth=AuthSettings('host', 'AuthLogin'),
            certificate_sha1='A' * 40, hostname=b'host', ip_address=b'127.0.0.1',
            fetch_garage=False, catalogue=None, text_encoding='cp1252')
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
            fetch_garage=False, catalogue=None, text_encoding='cp1252')
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
            fetch_garage=False, catalogue=None, text_encoding='cp1252')
        with patch('client.fanserver_test.prepare_context', return_value=context):
            with patch('client.fanserver_test.authenticate') as authenticate:
                result = run_test('external', 'user', 'password', cancelled=lambda: True)
        self.assertTrue(result['cancelled'])
        self.assertEqual(result['last_stage'], 'preflight')
        authenticate.assert_not_called()
