import unittest

from tools.fan_server_guidance import failure_guidance


class FanServerGuidanceTests(unittest.TestCase):
    def test_fixed_suggestions_never_copy_private_report_content(self):
        for stage in ('preflight', 'authorization', 'persona', 'lobby', 'primary', 'garage', 'secret-stage'):
            for code in ('authorization_denied', 'setup_failed', 'timeout', 'connection_failed',
                         'network_or_file_error', 'protocol_or_data_error', 'secret-code'):
                text = failure_guidance({'last_stage': stage, 'failure_code': code, 'password': 'secret-password'})
                self.assertNotIn('secret', text)
                self.assertTrue(text)

    def test_protocol_failure_is_actionable_without_blame_on_account(self):
        text = failure_guidance({'last_stage': 'garage', 'failure_code': 'protocol_or_data_error'})
        self.assertIn('Save the report', text)
        self.assertIn('reconstruction incompatibility', text)

    def test_cancel_has_retry_guidance(self):
        self.assertIn('Start a new test', failure_guidance({'cancelled': True}))
