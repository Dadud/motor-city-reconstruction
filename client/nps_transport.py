"""Portable TCP transport for recovered NPS frames.

No automatic authentication, heartbeat handling, or reply interpretation.
Original boundaries: connect 0x72ea50, send 0x72fd50, receive 0x72f600.
"""
import math
import socket
import struct
import time

from client.nps_framing import Frame


def _timeout(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('network timeout must be a positive finite number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError('network timeout must be a positive finite number')
    return value


def _validate_wire(wire):
    if not isinstance(wire, bytes) or not 4 <= len(wire) <= 65535:
        raise ValueError('expected one encoded NPS frame')
    if struct.unpack_from('>H', wire, 2)[0] != len(wire):
        raise ValueError('NPS frame length does not match its bytes')


class NPSConnection:
    """One TCP stream; each receive consumes exactly one declared frame.

    A failed send/receive closes the stream: partial messages cannot be retried
    on the same connection. Callers decide whether and when to reconnect.
    """
    def __init__(self, connected_socket):
        self._socket = connected_socket
        self._closed = False

    @classmethod
    def connect(cls, endpoint, *, timeout=30):
        timeout = _timeout(timeout)
        if (not isinstance(endpoint.host, str) or not endpoint.host or
                any(ord(c) <= 32 or ord(c) == 127 for c in endpoint.host) or
                type(endpoint.port) is not int or not 1 <= endpoint.port <= 65535):
            raise ValueError('invalid NPS endpoint')
        return cls(socket.create_connection((endpoint.host, endpoint.port), timeout))

    def _require_open(self):
        if self._closed:
            raise ValueError('NPS connection is closed')

    def send(self, wire, *, timeout=30):
        """Send one complete encoded frame without changing its payload."""
        self._require_open()
        timeout = _timeout(timeout)
        _validate_wire(wire)
        try:
            self._socket.settimeout(timeout)
            self._socket.sendall(wire)
        except OSError:
            self.close()
            raise

    def receive(self, *, timeout=120):
        """Read one frame under a deadline covering prefix and body.

        The native wait applies before reading; the portable client also
        bounds the complete read so a peer cannot stall after its prefix.
        """
        self._require_open()
        deadline = time.monotonic()+_timeout(timeout)

        def read_exact(size):
            data = bytearray()
            while len(data) < size:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('NPS frame receive timed out')
                self._socket.settimeout(remaining)
                part = self._socket.recv(size-len(data))
                if not part:
                    raise EOFError('NPS connection ended before a complete frame')
                data.extend(part)
            return bytes(data)

        try:
            message_id, length = struct.unpack('>HH', read_exact(4))
            if length < 4:
                raise ValueError('NPS frame length is smaller than its prefix')
            return Frame(message_id, read_exact(length-4))
        except (OSError, EOFError, ValueError):
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            self._socket.close()

    def __enter__(self):
        self._require_open()
        return self

    def __exit__(self, *unused):
        self.close()


def query(endpoint, wire, *, connect_timeout=30, send_timeout=30, receive_timeout=120):
    """One request and reply on a fresh TCP connection, then close.

    This performs network I/O when explicitly called. It does not infer
    authentication or success from a reply and never retries the request.
    """
    _validate_wire(wire)
    for timeout in (connect_timeout, send_timeout, receive_timeout):
        _timeout(timeout)
    with NPSConnection.connect(endpoint, timeout=connect_timeout) as connection:
        connection.send(wire, timeout=send_timeout)
        return connection.receive(timeout=receive_timeout)
