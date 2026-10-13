"""Recovered persona-map request; response and activation remain separate."""
import struct
from client.nps_framing import encode_message


def encode_persona_maps_request(account_user_id):
    """Native 0x71dab0 request 0x532, serializer 0x71e340.

    Uses the account ID from authenticated login success, not a persona ID.
    This only prepares bytes and never sends an account request.
    """
    if type(account_user_id) is not int or not 1 <= account_user_id <= 0xffffffff:
        raise ValueError('persona-map account ID must be a nonzero uint32')
    return encode_message(0x532, struct.pack('>I', account_user_id), auxiliary=16)
