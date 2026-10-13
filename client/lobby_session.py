"""Connection-local lobby ciphers from retained client login material.

Native login 0x72a8f0 retains its generated key separately from the 0x601
response. Connection constructor 0x73f050 copies the supplied key record;
0x73f470 creates separate zero-IV encryption and decryption contexts.
"""
from dataclasses import dataclass, field

from client.lobby_cipher import DESChaining
from client.nps_session_request import PreparedLogin


@dataclass(frozen=True)
class LobbyCiphers:
    send: DESChaining = field(repr=False)
    receive: DESChaining = field(repr=False)

    @classmethod
    def from_login(cls, prepared):
        """Create fresh TCP chains for a connection using retained request key.

        This accepts a prepared request, not a decoded server key record. It
        does not establish authentication or reuse a previous connection chain.
        UDP contexts remain separate and are not constructed here.
        """
        if not isinstance(prepared, PreparedLogin):
            raise TypeError('expected a prepared client login')
        material = prepared.session_material
        if not isinstance(material, bytes) or len(material) != 32:
            raise ValueError('prepared login must retain its 32-byte client key')
        key = material[:8]
        return cls(DESChaining(key), DESChaining(key, decrypt=True))
