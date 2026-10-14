import contextlib
import io
import getpass
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from client.server_discovery import AuthSettings, DiscoverySource, Endpoint, Shard
from tools.account_check import main


class AccountCheckTests(unittest.TestCase):
    def run_check(self, *extra, failure=None, terminal=True, prompt_failure=None):
        shard = Shard('synthetic', '', 44, Endpoint('host', 1), Endpoint('host', 2),
                      Endpoint('host', 3), None, ())
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            for name, value in {
                'installed_sources': (DiscoverySource('shardlistip.ini', 'https://host/list'),),
                'fetch_shard_list': (shard,),
                'installed_patch_settings': SimpleNamespace(certificate_sha1='A'*40),
                'windows_auth_settings': AuthSettings('host', 'AuthLogin'),
                'installed_public_key': None, 'installed_executable_checksum': 1,
            }.items():
                stack.enter_context(patch('tools.account_check.'+name, return_value=value))
            prompt = stack.enter_context(patch('tools.account_check.getpass.getpass',
                side_effect=prompt_failure or ['private-user', 'private-password']))
            auth = stack.enter_context(patch('tools.account_check.authenticate',
                return_value=SimpleNamespace(personas=SimpleNamespace(entries=(1, 2))),
                side_effect=failure))
            stack.enter_context(patch('tools.account_check.sys.stdin.isatty', return_value=terminal))
            stack.enter_context(contextlib.redirect_stdout(output))
            stack.enter_context(contextlib.redirect_stderr(errors))
            status = main(['external', '--shard-id', '44', *extra])
        return status, output.getvalue(), errors.getvalue(), prompt, auth

    def test_preflight_never_prompts_or_authenticates(self):
        status, output, errors, prompt, auth = self.run_check()
        self.assertEqual(status, 0)
        self.assertIn('"live_account_tested": false', output)
        prompt.assert_not_called()
        auth.assert_not_called()

    def test_explicit_login_uses_hidden_input_and_summarizes_only(self):
        status, output, errors, prompt, auth = self.run_check('--login')
        self.assertEqual(status, 0)
        self.assertEqual(auth.call_args.args[-2:], ('private-user', 'private-password'))
        self.assertIn('"persona_count": 2', output)
        self.assertNotIn('private-', output+errors)

    def test_redirected_input_is_rejected_before_credentials(self):
        status, output, errors, prompt, auth = self.run_check('--login', terminal=False)
        self.assertEqual(status, 1)
        prompt.assert_not_called()
        auth.assert_not_called()

    def test_private_transport_diagnostics_never_print(self):
        status, output, errors, prompt, auth = self.run_check('--login',
            failure=RuntimeError('https://host/?password=private-password&ticket=secret'))
        self.assertEqual(status, 1)
        self.assertIn('RuntimeError', errors)
        self.assertNotIn('secret', output+errors)
        self.assertNotIn('private-', output+errors)

    def test_cancel_stops_before_authentication(self):
        with patch('tools.account_check.installed_sources', side_effect=KeyboardInterrupt):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['external', '--shard-id', '44']), 2)

    def test_echoing_input_fallback_stops_before_authentication(self):
        status, output, errors, prompt, auth = self.run_check('--login',
            prompt_failure=getpass.GetPassWarning('fallback refused'))
        self.assertEqual(status, 1)
        auth.assert_not_called()

    def test_accidental_credential_arguments_are_not_echoed(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), self.assertRaises(SystemExit):
            main(['external', '--shard-id', '44', '--password', 'private-password'])
        self.assertNotIn('private-password', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
