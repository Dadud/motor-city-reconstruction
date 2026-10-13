"""Recovered generic MCOTS transaction completion dispatch.

Frames supplied here must contain the decoded plaintext payload. Compression
and encryption flags are handled by the connection before dispatch.
"""
from dataclasses import dataclass
import struct
from client.mcots_framing import MCOTSFrame


@dataclass(frozen=True)
class MCOTSCompletion:
    operation: int
    successful: bool
    reply_opcode: int
    result_code: int | None


def decode_completion(frame, *, transaction_value, operation):
    """Resolve a known generic reply against an explicit pending request.

Native 0x65dcd0 resolves the pending operation by transaction before dispatch.
The wrapper's operation is additionally checked here to reject conflicting
identities. A direct operation-specific response needs its own parser.
"""
    if not isinstance(frame, MCOTSFrame):
        raise ValueError('expected MCOTS frame')
    frame.encode()  # Validate fields before interpreting a synthetic frame.
    if type(transaction_value) is not int or not 0 <= transaction_value <= 0xffffffff:
        raise ValueError('expected uint32 pending transaction')
    if type(operation) is not int or not 0 <= operation <= 65535:
        raise ValueError('expected uint16 pending operation')
    if frame.transaction_value != transaction_value:
        raise ValueError('MCOTS reply does not match pending transaction')
    payload = frame.payload
    if len(payload) < 2:
        raise ValueError('truncated MCOTS reply opcode')
    opcode = struct.unpack_from('<H', payload)[0]
    if opcode == 0x65:
        # Native generic success does not read an embedded original operation.
        return MCOTSCompletion(operation, True, opcode, None)
    if opcode not in (0x66, 0x107, 0x67):
        raise ValueError('operation-specific MCOTS reply requires its own parser')
    if len(payload) < 8:
        raise ValueError('truncated MCOTS result record')
    embedded_operation, result = struct.unpack_from('<HI', payload, 2)
    if opcode == 0x67 and embedded_operation != operation:
        raise ValueError('MCOTS wrapper operation conflicts with pending request')
    return MCOTSCompletion(operation, opcode == 0x67 and result == 0x65,
                           opcode, result)


def attachment_status(completion):
    """Native 0x681d30 status mapping, after correlation for operation 0x1b6."""
    if not isinstance(completion, MCOTSCompletion) or completion.operation != 0x1b6:
        raise ValueError('expected attachment completion')
    if completion.successful:
        return 1
    return {0x6b: 0x60, 0x7c: 0x5d, 0x82: 7, 0x83: 0x5e,
            0xba: 0x5f, 0xbb: 0x5a, 0xbc: 0x5c, 0x1b4: 0x5a}.get(completion.result_code, 3)
