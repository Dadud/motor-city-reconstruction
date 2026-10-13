"""Recovered binary login exchange, following external HTTPS authorization.

Callers supply a PreparedLogin. This module does not acquire credentials or
guess the unresolved key-record value required by prepare_login.
"""
from dataclasses import dataclass, field
import struct
from client.nps_response import LoginSuccess
from client.nps_session_request import PreparedLogin
from client.nps_transport import NPSConnection


class LoginRequestError(RuntimeError):
    def __init__(self, message_id):
        self.message_id = message_id
        self.native_result = {0x602: -11, 0x610: -106, 0x623: -142,
                              0x626: -127, 0x637: -141}.get(message_id, -1)
        super().__init__(f'binary login rejected: reply 0x{message_id:03x}, result {self.native_result}')


@dataclass(frozen=True)
class AuthenticatedAccount:
    response: LoginSuccess = field(repr=False)
    prepared_login: PreparedLogin = field(repr=False)
    acknowledgement_id: int

    @property
    def user_id(self):
        return self.response.user_id


def login(login_endpoint, prepared_login):
    """Send 0x501, consume an acknowledgement, then require success 0x601.

    Original 0x72a8f0 does not inspect the first reply's opcode. It waits
    30 seconds for that frame, then 120 for the result on the same stream.
    The request material is retained separately from the response key record.
    No retry or lobby connection occurs here.
    """
    if not isinstance(prepared_login, PreparedLogin):
        raise TypeError('binary login requires a PreparedLogin')
    wire, material = prepared_login.wire, prepared_login.session_material
    if (not isinstance(wire, bytes) or not 12 <= len(wire) <= 65535 or
            struct.unpack_from('>HH', wire) != (0x501, len(wire)) or
            not isinstance(material, bytes) or len(material) != 32):
        raise ValueError('invalid prepared binary login')
    with NPSConnection.connect(login_endpoint) as connection:
        connection.send(wire)
        acknowledgement = connection.receive(timeout=30)
        reply = connection.receive(timeout=120)
        if reply.message_id != 0x601:
            raise LoginRequestError(reply.message_id)
        response = LoginSuccess.from_frame(reply)
        return AuthenticatedAccount(response, prepared_login, acknowledgement.message_id)
