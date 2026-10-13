"""Explicit persona RPCs for an already authenticated account.

No account discovery, implicit authentication, retries, or persistent session
state. Network requests occur only when these functions are called.
"""
from client.nps_persona import (PersonaMaps, encode_persona_maps_request,
    encode_persona_activation_request, native_persona_activation_result)
from client.nps_transport import query
from client.server_discovery import Endpoint


class PersonaRequestError(RuntimeError):
    def __init__(self, operation, message_id, native_result):
        self.message_id = message_id
        self.native_result = native_result
        super().__init__(f'{operation} rejected: reply 0x{message_id:03x}, result {native_result}')


def persona_endpoint(login_endpoint):
    """Native persona request routines use the login host and port plus two."""
    if type(login_endpoint.port) is not int or not 1 <= login_endpoint.port <= 65533:
        raise ValueError('login port cannot produce a valid persona endpoint')
    return Endpoint(login_endpoint.host, login_endpoint.port+2)


def fetch_personas(login_endpoint, account_user_id):
    """Download the 0x607 list for the explicitly supplied account identity."""
    wire = encode_persona_maps_request(account_user_id)
    reply = query(persona_endpoint(login_endpoint), wire)
    if reply.message_id != 0x607:
        # Native NPSGetPersonaMaps handles 0x602 as -11, other replies as -1.
        raise PersonaRequestError('persona list', reply.message_id,
                                  -11 if reply.message_id == 0x602 else -1)
    return PersonaMaps.from_frame(reply)


def activate_persona(login_endpoint, account_user_id, persona_id, shard_id):
    """Activate a persona; return only after its explicit success reply.

    Account identity remains caller supplied, matching the original game worker
    which overwrites the map record's account field with the authenticated ID.
    This does not open a lobby connection or mark a multiplayer session ready.
    """
    wire = encode_persona_activation_request(account_user_id, persona_id, shard_id)
    reply = query(persona_endpoint(login_endpoint), wire)
    result = native_persona_activation_result(reply.message_id)
    if result != 0:
        raise PersonaRequestError('persona activation', reply.message_id, result)
