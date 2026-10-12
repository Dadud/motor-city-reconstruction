"""Assemble recovered login fields without opening a connection.

Original 0x72a8f0 selects 32-byte session material; 0x72c3f0 serializes its
header-free key record, encrypts it, and formats uppercase hex. Callers supply
the unresolved key-record value explicitly. Full native RSA equivalence and
server acceptance remain unverified.
"""
from dataclasses import dataclass, field
import secrets

from client.nps_crypto import installed_public_key
from client.nps_framing import encode_message
from client.nps_identity import SERVICE_ID, installed_executable_checksum
from client.nps_login import LoginPayload
from client.nps_response import SessionKeyRecord


@dataclass(frozen=True)
class PreparedLogin:
    wire: bytes = field(repr=False)
    session_material: bytes = field(repr=False)


def prepare_login(root, ticket, *, key_record_value):
    """Prepare HTTPS-mode login with fresh OS entropy; never log its contents.

    The explicit key-record value prevents treating an unresolved field as a
    known constant. No account requests, socket writes, or state mutations occur.
    """
    key = installed_public_key(root)
    checksum = installed_executable_checksum(root)
    # Validate ticket/caller value before creating session material.
    LoginPayload(ticket, 0, b'', SERVICE_ID.encode('ascii'), checksum).encode()
    SessionKeyRecord(b'', key_record_value).encode()
    material = secrets.token_bytes(32)
    plaintext = SessionKeyRecord(material, key_record_value).encode()
    encrypted = key.encrypt_hex(plaintext, secrets.token_bytes(20))
    payload = LoginPayload(ticket, 0, encrypted, SERVICE_ID.encode('ascii'), checksum)
    encoded = payload.encode()
    # 0x7e0800 computes the default auxiliary through 0x71be60 before writing
    # header flags. The zeroed flags make that value equal total message length.
    return PreparedLogin(encode_message(0x501, encoded, auxiliary=len(encoded)+12), material)
