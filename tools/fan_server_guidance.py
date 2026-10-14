"""Fixed local troubleshooting guidance; never interpolates server data."""


def failure_guidance(report: dict) -> str:
    if report.get('cancelled') is True:
        return 'The test was cancelled. Start a new test when ready.'
    code = report.get('failure_code')
    stage = report.get('last_stage')
    if code == 'authorization_denied':
        return 'Re-enter your fan-server account details and check that the original client can sign in.'
    if stage == 'preflight':
        return 'Check the selected original installation and its fan-server configuration. Run the setup launcher if dependencies are missing.'
    if stage == 'persona' and code == 'setup_failed':
        return 'Choose an available persona for this shard. In the terminal, use the numbered prompt or an existing persona ID.'
    if code in ('timeout', 'connection_failed', 'network_or_file_error'):
        return 'Check whether the original client reaches this server from the same computer. Retry once, then save the report if the failure repeats.'
    if code == 'protocol_or_data_error':
        return 'Save the report with its failed stage. This may indicate a reconstruction incompatibility; the test does not establish that your account is invalid.'
    return 'Save the report and note whether the original client can connect from the same computer.'
