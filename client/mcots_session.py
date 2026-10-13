"""Recovered MCOTS payload transforms and keepalive dispatch on one stream."""
import struct
import time
from client.mcots_cipher import MCOTSCipher
from client.mcots_framing import MCOTSFrame
from client.nps_transport import _timeout
from client.pkware_dcl import decompress_mcots_payload


class MCOTSSession:
    """Own one transport and independent persistent incoming/outgoing ciphers.

    Key scheduling is prepared without advancing either stream. Attachment
    completion calls enable_encryption; incoming flag 8 also enables it.
    The instance expects serial use, like the underlying socket transport.
    """
    def __init__(self, connection, session_material):
        if not isinstance(session_material, bytes) or len(session_material) != 32:
            raise ValueError('expected 32 retained client session bytes')
        self._connection = connection
        self._incoming = MCOTSCipher(session_material[:16])
        self._outgoing = MCOTSCipher(session_material[:16])
        self._encrypted = False
        self._closed = False

    def _require_open(self):
        if self._closed:
            raise ValueError('MCOTS session is closed')

    def enable_encryption(self):
        self._require_open()
        self._encrypted = True

    def send(self, frame, *, timeout=30):
        """Send plaintext application/control payload, with encryption if active.

        Outgoing compression is a separate unfinished encoder. Callers cannot
        supply transform flags here and accidentally encrypt a payload twice.
        """
        self._require_open()
        timeout = _timeout(timeout)
        if not isinstance(frame, MCOTSFrame):
            raise ValueError('expected MCOTS frame')
        frame.encode()
        if frame.flags & 0x0b:
            raise ValueError('MCOTS session manages transform flags')
        payload, flags = frame.payload, frame.flags
        if self._encrypted and not flags & 0x80:
            payload = self._outgoing.transform(payload)
            flags |= 8
        try:
            self._connection.send(MCOTSFrame(frame.transaction_value, flags, payload).encode(), timeout=timeout)
        except (OSError, EOFError, ValueError):
            self.close()
            raise

    def receive(self, *, timeout=120):
        """Return one decoded application frame, consuming control keepalives."""
        self._require_open()
        deadline = time.monotonic()+_timeout(timeout)
        try:
            while True:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('MCOTS application receive timed out')
                frame = self._connection.receive(timeout=remaining)
                payload, flags = frame.payload, frame.flags
                if flags & 8:
                    self._encrypted = True
                if self._encrypted and not flags & 0x80:
                    payload = self._incoming.transform(payload)
                if flags & 2:
                    payload = decompress_mcots_payload(payload)
                flags &= ~0x0a
                control = struct.unpack_from('<I', payload)[0] if len(payload) >= 4 else None
                if control == 0xf216:
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('MCOTS keepalive reply timed out')
                    self.send(MCOTSFrame(frame.transaction_value, flags | 0x80,
                                         struct.pack('<I', 0xf207)+payload[4:]), timeout=remaining)
                    continue
                if control == 0xf207 or flags & 0x80:
                    continue
                return MCOTSFrame(frame.transaction_value, flags, payload)
        except (OSError, EOFError, ValueError):
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            self._incoming.close()
            self._outgoing.close()
            self._connection.close()

    def __enter__(self):
        self._require_open()
        return self

    def __exit__(self, *unused):
        self.close()
