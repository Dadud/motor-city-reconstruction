"""Recovered lobby send selection and encrypted wrapper construction.

The native send thread encrypts most application messages with caller-managed
padding that completes the final eight-byte block. Heartbeats 0x207 and 0x217
remain plaintext and must not advance the CBC chain.
"""
from client.lobby_envelope import encrypt_envelope, native_encrypts_message
from client.nps_framing import Frame


def prepare_outgoing_frame(frame, ciphers, *, padding):
    """Return the wire frame to send, or the original frame when plaintext."""
    if not isinstance(frame, Frame):
        raise TypeError('expected a lobby frame')
    if native_encrypts_message(frame.message_id):
        return encrypt_envelope(frame, ciphers.send, padding=padding)
    if padding != b'':
        raise ValueError('plaintext heartbeat must not have cipher padding')
    return frame

