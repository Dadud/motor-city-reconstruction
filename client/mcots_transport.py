"""TCP transport for MCOTS envelopes, without automatic login or encryption.

Shared socket lifecycle comes from NPSConnection; MCOTS framing is entirely
separate and little endian. Callers supply already transformed payloads.
"""
import struct
import time
from client.mcots_framing import MCOTSFrame, MARKER
from client.nps_transport import NPSConnection, _timeout


class MCOTSConnection(NPSConnection):
    """Persistent MCOTS stream; failed I/O closes it without retrying."""
    def _require_open(self):
        if self._closed:
            raise ValueError('MCOTS connection is closed')

    def send(self, wire, *, timeout=30):
        self._require_open()
        timeout = _timeout(timeout)
        MCOTSFrame.decode(wire)
        try:
            self._socket.settimeout(timeout)
            self._socket.sendall(wire)
        except OSError:
            self.close()
            raise

    def receive(self, *, timeout=120):
        self._require_open()
        deadline = time.monotonic()+_timeout(timeout)

        def read_exact(size):
            data = bytearray()
            while len(data) < size:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('MCOTS frame receive timed out')
                self._socket.settimeout(remaining)
                part = self._socket.recv(size-len(data))
                if not part:
                    raise EOFError('MCOTS connection ended before a complete frame')
                data.extend(part)
            return bytes(data)

        try:
            prefix = read_exact(2)
            length = struct.unpack('<H', prefix)[0]
            if length < 10:
                raise ValueError('MCOTS frame has no complete header and payload')
            header = read_exact(9)
            if struct.unpack_from('<I', header)[0] != MARKER:
                raise ValueError('invalid MCOTS frame marker')
            return MCOTSFrame.decode(prefix+header+read_exact(length-9))
        except (OSError, EOFError, ValueError):
            self.close()
            raise
