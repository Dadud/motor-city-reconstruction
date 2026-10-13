"""Recovered plaintext lobby handshake followed by connection-local CBC frames."""
import time
from client.lobby_envelope import (encrypt_envelope, decrypt_envelope,
                                   native_encrypts_message)
from client.lobby_login import LobbyLogin
from client.lobby_response import (LobbyLoginSuccess, LobbyQueuePosition,
                                    native_connection_rejection)
from client.lobby_session import LobbyCiphers
from client.nps_transport import NPSConnection, _timeout
from client.nps_framing import Frame


class LobbyRequestError(RuntimeError):
    def __init__(self, message_id):
        self.message_id = message_id
        result = native_connection_rejection(message_id)
        self.native_result = -1 if result is None else result
        super().__init__(f'lobby connection rejected: reply 0x{message_id:03x}, result {self.native_result}')


class LobbyConnection:
    """An accepted lobby stream; cipher chains persist until it closes.

    receive() exposes raw inner frames; receive_message() handles server
    heartbeats before delivering application messages. Room dispatch and
    reconnect policy remain separate.
    """
    def __init__(self, connection, ciphers, success):
        self._connection, self._ciphers = connection, ciphers
        self.success = success
        self._closed = False

    def send(self, frame, *, padding, timeout=30):
        if self._closed:
            raise ValueError('lobby connection is closed')
        _timeout(timeout)
        if len(frame.encode()) > 60000:
            raise ValueError('lobby frame exceeds native receive limit')
        if native_encrypts_message(frame.message_id):
            outgoing = encrypt_envelope(frame, self._ciphers.send, padding=padding)
        else:
            if padding != b'':
                raise ValueError('plaintext heartbeat must not have cipher padding')
            outgoing = frame
        try:
            self._connection.send(outgoing.encode(), timeout=timeout)
        except (OSError, ValueError):
            self.close()
            raise

    def receive(self, *, timeout=120):
        if self._closed:
            raise ValueError('lobby connection is closed')
        try:
            frame = self._connection.receive(timeout=timeout)
            if len(frame.encode()) > 60000:
                raise ValueError('lobby frame exceeds native receive limit')
            return (decrypt_envelope(frame, self._ciphers.receive).inner
                    if frame.message_id == 0x1101 else frame)
        except (OSError, EOFError, ValueError):
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            self._connection.close()
            self._ciphers.send.finish()
            self._ciphers.receive.finish()

    def receive_message(self, *, timeout=120):
        """Native 0x7414b0: discard 0x207, answer 0x217 with empty 0x207.

        Replies bypass encryption and do not advance either CBC chain. The
        deadline covers heartbeat traffic too, so it cannot extend the wait
        indefinitely. No unsolicited heartbeat schedule is inferred here.
        """
        deadline = time.monotonic()+_timeout(timeout)
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                self.close()
                raise TimeoutError('lobby message receive timed out')
            frame = self.receive(timeout=remaining)
            if frame.message_id == 0x207:
                continue
            if frame.message_id == 0x217:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    self.close()
                    raise TimeoutError('lobby heartbeat reply timed out')
                self.send(Frame(0x207, b''), padding=b'', timeout=min(30, remaining))
                continue
            return frame

    def __enter__(self):
        if self._closed:
            raise ValueError('lobby connection is closed')
        return self

    def __exit__(self, *unused):
        self.close()


def connect_lobby(endpoint, login, prepared_login, *, queue_enabled=True,
                  queue_timeout=120, on_queue_position=None):
    """Wait for 0x230, send plaintext 0x100, require 0x120/0x308.

    Cipher contexts use the retained request material and are never applied to
    the queue or login exchange. queue_timeout bounds the entire queue phase;
    the native code instead repeats waits and supports a cancellation callback.
    The returned stream owns the connection until the caller closes it.
    """
    if not isinstance(login, LobbyLogin):
        raise TypeError('expected a lobby login payload')
    if type(queue_enabled) is not bool:
        raise ValueError('queue_enabled must be boolean')
    _timeout(queue_timeout)
    if on_queue_position is not None and not callable(on_queue_position):
        raise TypeError('queue callback must be callable')
    wire = login.frame().encode()
    ciphers = LobbyCiphers.from_login(prepared_login)
    connection = None
    try:
        connection = NPSConnection.connect(endpoint)
        if queue_enabled:
            deadline = time.monotonic()+queue_timeout
            while True:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('lobby queue timed out')
                reply = connection.receive(timeout=min(30, remaining))
                if reply.message_id == 0x230:
                    if reply.body:
                        raise ValueError('login permission reply has unexpected body')
                    break
                if reply.message_id == 0x231:
                    position = LobbyQueuePosition.from_frame(reply)
                    if on_queue_position is not None:
                        on_queue_position(position)
                else:
                    raise LobbyRequestError(reply.message_id)
        connection.send(wire)
        deadline = time.monotonic()+30
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('lobby login timed out')
            reply = connection.receive(timeout=remaining)
            if reply.message_id == 0x230 and not reply.body:
                continue
            if reply.message_id not in (0x120, 0x308):
                raise LobbyRequestError(reply.message_id)
            success = LobbyLoginSuccess.from_frame(reply)
            return LobbyConnection(connection, ciphers, success)
    except BaseException:
        if connection is not None:
            connection.close()
        ciphers.send.finish()
        ciphers.receive.finish()
        raise
