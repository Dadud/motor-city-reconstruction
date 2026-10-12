"""Recovered lobby DES-CBC block chaining; message lifecycle is not integrated.

0x7cefc0 XORs plaintext with the prior ciphertext before DES. 0x7cf140 XORs
decrypted bytes with the prior ciphertext and then retains the incoming block.
The caller supplies complete blocks; framing/padding/reconnect remain separate.
"""


class DESChaining:
    def __init__(self, key, *, decrypt=False, iv=bytes(8)):
        if not isinstance(key, bytes) or len(key) != 8:
            raise ValueError('recovered DES key must contain exactly eight bytes')
        if not isinstance(iv, bytes) or len(iv) != 8:
            raise ValueError('DES IV must contain eight bytes')
        from cryptography.hazmat.primitives.ciphers import Cipher, modes
        from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
        self._cipher = Cipher(TripleDES(key*3), modes.CBC(iv))
        self._context = self._cipher.decryptor() if decrypt else self._cipher.encryptor()
        self._closed = False

    def update(self, blocks):
        if self._closed:
            raise ValueError('cipher has been closed')
        if not isinstance(blocks, bytes) or len(blocks) % 8:
            raise ValueError('cipher input must contain complete eight-byte blocks')
        if len(blocks) > 65536:
            raise ValueError('cipher input exceeds supported message bound')
        return self._context.update(blocks)

    def finish(self):
        if self._closed:
            raise ValueError('cipher has been closed')
        self._closed = True
        return self._context.finalize()
