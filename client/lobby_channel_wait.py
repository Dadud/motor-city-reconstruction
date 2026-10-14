"""Recovered single-slot reply wait ordering (original function 0x73a360).

Inject polling boundaries for comparison or a listener-owned connection. This
does not send a request or make original opaque room arguments valid.
"""
from dataclasses import dataclass
from typing import Callable

from client.lobby_channel_codec import ChannelReplyMailbox

POLL_MICROSECONDS = 250000
MAX_CALLBACK_POLLS = 80


@dataclass(frozen=True)
class ChannelWaitResult:
    code: int
    polls: int


def wait_for_channel_reply(
    mailbox: ChannelReplyMailbox, *,
    sleep_microseconds: Callable[[int], None],
    is_connected: Callable[[], bool],
    cancel: Callable[[], int] | None = None,
    release_reply: Callable[[object], None] | None = None,
) -> ChannelWaitResult:
    """Run the original poll-count/order rules with explicit host boundaries.

    Calls reset the slot as the original does. This is a single-owner research
    boundary: callers must serialize requests and retire disconnected slots.
    Callback exceptions propagate; their behavior is not original return-code
    evidence. A disconnect deliberately retains the original pending fields.
    """
    mailbox.reply = None
    mailbox.completed = False
    mailbox.waiting = True
    polls = 0
    while True:
        if mailbox.completed:
            mailbox.waiting = False
            return ChannelWaitResult(0 if mailbox.reply is not None else -1, polls)
        sleep_microseconds(POLL_MICROSECONDS)
        polls += 1
        if polls > MAX_CALLBACK_POLLS:
            code = -2
        elif cancel is not None and cancel() == 1:
            code = -51
        else:
            if not is_connected():
                return ChannelWaitResult(-6, polls)
            continue
        # The terminal registry check wins over timeout/cancellation and leaves
        # the disconnected object's pending fields intact in the original.
        if not is_connected():
            return ChannelWaitResult(-6, polls)
        if mailbox.reply is not None:
            mailbox.waiting = False
            if release_reply is not None:
                release_reply(mailbox.reply)
            mailbox.reply = None
        mailbox.waiting = False
        return ChannelWaitResult(code, polls)
