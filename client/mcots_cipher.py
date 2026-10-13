"""Persistent RC4 state used by the original MCOTS connection.

This is the recovered legacy protocol primitive, with no keystream drop.
Attachment initializes independent directions from the first 16 retained
client session bytes. The surrounding handshake is implemented separately.
"""


class MCOTSCipher:
    def __init__(self, key):
        if not isinstance(key, bytes) or len(key) != 16:
            raise ValueError('MCOTS cipher requires 16 key bytes')
        self._state = bytearray(range(256))
        j = 0
        for i in range(256):
            j = (j+self._state[i]+key[i % 16]) & 255
            self._state[i], self._state[j] = self._state[j], self._state[i]
        self._i = self._j = 0
        self._closed = False

    def transform(self, payload):
        if self._closed:
            raise ValueError('MCOTS cipher is closed')
        if not isinstance(payload, bytes) or len(payload) > 65526:
            raise ValueError('expected at most 65526 MCOTS payload bytes')
        output = bytearray(payload)
        state = self._state
        for offset in range(len(output)):
            self._i = (self._i+1) & 255
            self._j = (self._j+state[self._i]) & 255
            state[self._i], state[self._j] = state[self._j], state[self._i]
            output[offset] ^= state[(state[self._i]+state[self._j]) & 255]
        return bytes(output)

    def close(self):
        self._state[:] = bytes(256)
        self._i = self._j = 0
        self._closed = True
