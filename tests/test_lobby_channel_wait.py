import unittest

from client.lobby_channel_codec import ChannelReplyMailbox
from client.lobby_channel_wait import wait_for_channel_reply


class ChannelWaitTests(unittest.TestCase):
    def run_case(self, *, reply_at=None, null_reply=False, cancel_value=None,
                 disconnect_at=None, uncompleted_reply=False):
        mailbox = ChannelReplyMailbox()
        events = []
        reply = object()
        polls = 0

        def sleep(value):
            nonlocal polls
            polls += 1
            events.append(('sleep', value))
            if polls == reply_at:
                mailbox.reply = None if null_reply else reply
                mailbox.completed = not uncompleted_reply

        def connected():
            events.append(('connected', polls))
            return disconnect_at is None or polls < disconnect_at

        def cancel():
            events.append(('cancel', polls))
            return cancel_value(polls)

        result = wait_for_channel_reply(mailbox, sleep_microseconds=sleep,
            is_connected=connected, cancel=cancel if cancel_value else None,
            release_reply=lambda value: events.append(('release', value)))
        return result, mailbox, events, reply

    def test_success_is_checked_after_sleep_cancel_and_registry(self):
        result, mailbox, events, reply = self.run_case(reply_at=1, cancel_value=lambda _: 0)
        self.assertEqual((result.code, result.polls), (0, 1))
        self.assertEqual(events, [('sleep', 250000), ('cancel', 1), ('connected', 1)])
        self.assertIs(mailbox.reply, reply)
        self.assertFalse(mailbox.waiting)
        self.assertTrue(mailbox.completed)

    def test_completed_null_reply_is_critical_error(self):
        result, mailbox, _, _ = self.run_case(reply_at=1, null_reply=True)
        self.assertEqual(result.code, -1)
        self.assertTrue(mailbox.completed)
        self.assertFalse(mailbox.waiting)

    def test_timeout_boundary_precedes_callback_and_last_tick_reply(self):
        result, mailbox, events, reply = self.run_case(reply_at=81, cancel_value=lambda _: 0)
        self.assertEqual((result.code, result.polls), (-2, 81))
        self.assertEqual(sum(kind == 'cancel' for kind, _ in events), 80)
        self.assertEqual(sum(kind == 'connected' for kind, _ in events), 81)
        self.assertEqual(events[-2:], [('connected', 81), ('release', reply)])
        self.assertIsNone(mailbox.reply)
        self.assertTrue(mailbox.completed)
        self.assertFalse(mailbox.waiting)

    def test_only_callback_value_one_cancels_and_beats_tick_reply(self):
        for value in (0, 2, -1):
            result, _, _, _ = self.run_case(reply_at=2, cancel_value=lambda _, v=value: v)
            self.assertEqual(result.code, 0)
        result, mailbox, events, reply = self.run_case(reply_at=1, cancel_value=lambda _: 1)
        self.assertEqual((result.code, result.polls), (-51, 1))
        self.assertEqual(events[-1], ('release', reply))
        self.assertIsNone(mailbox.reply)
        self.assertFalse(mailbox.waiting)

    def test_disconnect_overrides_reply_cancel_and_timeout_without_cleanup(self):
        for tick, cancellation in ((1, None), (1, lambda _: 1), (81, None)):
            result, mailbox, events, reply = self.run_case(reply_at=tick,
                disconnect_at=tick, cancel_value=cancellation)
            self.assertEqual((result.code, result.polls), (-6, tick))
            self.assertIs(mailbox.reply, reply)
            self.assertTrue(mailbox.waiting)
            self.assertTrue(mailbox.completed)
            self.assertFalse(any(kind == 'release' for kind, _ in events))

    def test_timeout_cleans_uncompleted_reply_too(self):
        result, mailbox, events, reply = self.run_case(reply_at=1, uncompleted_reply=True)
        self.assertEqual(result.code, -2)
        self.assertEqual(events[-1], ('release', reply))
        self.assertFalse(mailbox.completed)
        self.assertIsNone(mailbox.reply)

    def test_original_wait_entry_resets_old_fields(self):
        mailbox = ChannelReplyMailbox()
        mailbox.reply = object()
        mailbox.waiting = mailbox.completed = True
        result = wait_for_channel_reply(mailbox, sleep_microseconds=lambda _: None,
            is_connected=lambda: True, cancel=lambda: 1)
        self.assertEqual(result.code, -51)
        self.assertIsNone(mailbox.reply)
        self.assertFalse(mailbox.completed)
