import contextlib
import getpass
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.fan_server_check import main
from client.server_discovery import AuthSettings, Endpoint, Shard


class FanServerCheckTests(unittest.TestCase):
    shard = Shard('MotorCity Revival', '', 44, Endpoint('host', 1), Endpoint('host', 2),
                  Endpoint('host', 3), None, ())
    context = SimpleNamespace(shard=shard, auth=AuthSettings('host', 'AuthLogin'))

    def test_failed_live_report_returns_failure_status(self):
        with patch('tools.fan_server_check.prepare_context', return_value=self.context), \
             patch('tools.fan_server_check.run_test', return_value={
                 'success': False, 'last_stage': 'primary', 'failure_code': 'timeout'}), \
             patch('tools.fan_server_check.getpass.getpass', side_effect=['user', 'password']), \
             patch('tools.fan_server_check.sys.stdin.isatty', return_value=True), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            status = main(['external', '--shard-id', '44', '--login', '--persona-id', '9'])
        self.assertEqual(status, 1)
        self.assertIn('"failure_code": "timeout"', output.getvalue())
        self.assertIn('"last_stage": "primary"', output.getvalue())

    def test_preflight_only(self):
        with patch('tools.fan_server_check.prepare_context', return_value=self.context) as prepare:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                status = main(['external', '--shard-id', '44'])
        self.assertEqual(status, 0)
        prepare.assert_called_once()
        self.assertIn('"preflight_passed": true', output.getvalue())
        self.assertIn('"live_fan_server_tested": false', output.getvalue())

    def test_login_summarizes_without_secrets(self):
        with patch('tools.fan_server_check.prepare_context', return_value=self.context):
            with patch('tools.fan_server_check.run_test', return_value={
                'success': True, 'cancelled': False, 'account_authenticated': True,
                'lobby_connected': True, 'primary_connected': True, 'garage_loaded': True,
                'persona_count': 1, 'garage_record_count': 2, 'part_seed_count': 2,
                'part_slot_count': 2, 'selected_persona_id': 9,
            }) as run_test:
                with patch('tools.fan_server_check.getpass.getpass',
                           side_effect=['private-user', 'private-password']):
                    with patch('tools.fan_server_check.sys.stdin.isatty', return_value=True):
                        with contextlib.redirect_stdout(io.StringIO()) as output:
                            status = main(['external', '--shard-id', '44', '--login',
                                           '--persona-id', '9', '--fetch-garage'])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn('"live_fan_server_tested": true', text)
        self.assertIn('"garage_record_count": 2', text)
        self.assertNotIn('private-', text)
        self.assertEqual(run_test.call_args.args[1:3], ('private-user', 'private-password'))

    def test_probe_race_entry_flag_is_forwarded(self):
        with patch('tools.fan_server_check.prepare_context', return_value=self.context):
            with patch('tools.fan_server_check.run_test', return_value={
                'success': True, 'cancelled': False, 'account_authenticated': True,
                'lobby_connected': True, 'primary_connected': True, 'garage_loaded': False,
                'race_entry_probe_passed': True, 'fast_join_tcp_preferred': True,
                'positional_updates_hz': 32, 'update_interval_seconds': 1 / 32,
                'recovered_task_kinds': [0, 5, 7, 8],
            }) as run_test:
                with patch('tools.fan_server_check.getpass.getpass',
                           side_effect=['private-user', 'private-password']):
                    with patch('tools.fan_server_check.sys.stdin.isatty', return_value=True):
                        with contextlib.redirect_stdout(io.StringIO()) as output:
                            status = main(['external', '--shard-id', '44', '--login',
                                           '--persona-id', '9', '--probe-race-entry'])
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn('"probe_race_entry_requested": true', text)
        self.assertIn('"race_entry_probe_passed": true', text)
        self.assertIn('"update_interval_seconds"', text)
        self.assertTrue(run_test.call_args.kwargs.get('probe_race_entry'))

    def test_private_transport_diagnostics_never_print(self):
        with patch('tools.fan_server_check.prepare_context',
                   side_effect=RuntimeError('https://host/?ticket=secret')):
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                status = main(['external', '--shard-id', '44', '--login'])
        self.assertEqual(status, 1)
        self.assertIn('RuntimeError', errors.getvalue())
        self.assertNotIn('secret', errors.getvalue())

    def test_echoing_input_fallback_stops_before_authentication(self):
        with patch('tools.fan_server_check.prepare_context', return_value=self.context):
            with patch('tools.fan_server_check.getpass.getpass',
                       side_effect=getpass.GetPassWarning('fallback refused')):
                with patch('tools.fan_server_check.sys.stdin.isatty', return_value=True):
                    with patch('tools.fan_server_check.run_test') as run_test:
                        with contextlib.redirect_stderr(io.StringIO()):
                            status = main(['external', '--shard-id', '44', '--login'])
        self.assertEqual(status, 1)
        run_test.assert_not_called()
