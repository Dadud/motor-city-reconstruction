"""Compare native reply-wait state and complete boundary ordering to Python.

Synthetic scenarios only; original function comparison remains a separate
evidence source. No credentials, host sleeping, socket activity or live joining.
"""
import argparse
import itertools
import json
from pathlib import Path
import random
import subprocess

from client.lobby_channel_codec import ChannelReplyMailbox
from client.lobby_channel_wait import wait_for_channel_reply


def _expected(scenario):
    reply_at, null_reply, incomplete, cancel_at, cancel_value, disconnect_at, has_cancel = scenario
    mailbox = ChannelReplyMailbox()
    mailbox.waiting = mailbox.completed = True
    mailbox.reply = 0x9999
    events = []
    polls = 0

    def sleep(value):
        nonlocal polls
        polls += 1
        events.append([0, value])
        if polls == reply_at:
            mailbox.reply = None if null_reply else 0x1234
            mailbox.completed = not incomplete

    def connected():
        events.append([2, polls])
        return disconnect_at < 0 or polls < disconnect_at

    def cancel():
        events.append([1, polls])
        return cancel_value if polls == cancel_at else 0

    result = wait_for_channel_reply(mailbox, sleep_microseconds=sleep,
        is_connected=connected, cancel=cancel if has_cancel else None,
        release_reply=lambda value: events.append([3, value]))
    return dict(code=result.code, polls=result.polls, waiting=mailbox.waiting,
                completed=mailbox.completed, reply=mailbox.reply or 0, events=events)


def verify(runner):
    runner = str(Path(runner).resolve())
    scenarios = set()
    for reply_at, cancel_at, cancel_value, disconnect_at, state in itertools.product(
        (-1, 1, 80, 81), (1, 80), (-1, 0, 1, 2), (-1, 1, 81), ((0, 0), (1, 0), (0, 1))):
        scenarios.add((reply_at, *state, cancel_at, cancel_value, disconnect_at, 1))
    for reply_at, disconnect_at in itertools.product((-1, 1, 80, 81), (-1, 1, 81)):
        scenarios.add((reply_at, 0, 0, 1, 1, disconnect_at, 0))
    rng = random.Random(0x73a360)
    for _ in range(128):
        scenarios.add((rng.randint(-1, 81), rng.randrange(2), rng.randrange(2),
            rng.randint(-1, 81), rng.choice((-0x80000000, -1, 0, 1, 2, 0x7fffffff)),
            rng.randint(-1, 81), rng.randrange(2)))
    for scenario in sorted(scenarios):
        result = subprocess.run([runner], input=(' '.join(map(str, scenario)) + '\n').encode('ascii'),
                                capture_output=True, timeout=10)
        if result.returncode or json.loads(result.stdout) != _expected(scenario):
            raise AssertionError(f'native channel wait differs for synthetic scenario {scenario}')
    invalid = ('', '1 0 0 1 1 -1', '1 0 0 1 1 -1 1 trailing', '82 0 0 1 1 -1 1',
               '1 2 0 1 1 -1 1', '1 0 0 1 2147483648 -1 1')
    for data in invalid:
        result = subprocess.run([runner], input=data.encode('ascii'), capture_output=True, timeout=10)
        if result.returncode != 2 or result.stdout:
            raise AssertionError('native channel-wait runner accepted malformed input')
    return dict(matched_wait_scenarios=len(scenarios), invalid_runner_inputs_rejected=len(invalid),
                compared_boundary_order=True, original_binary_executed=False, live_server_tested=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runner')
    print(json.dumps(verify(parser.parse_args().runner), indent=2))
