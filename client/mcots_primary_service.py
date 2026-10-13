"""Primary MCOTS attachment and login exchange; follow-up services are separate."""
from dataclasses import dataclass, field
import struct
from client.mcots_attachment import MCOTSAttachment
from client.mcots_framing import MCOTSFrame
from client.mcots_login import MCOTSLoginRecord
from client.mcots_login_response import MCOTSLoginSuccess
from client.mcots_response import decode_completion, attachment_status
from client.mcots_session import MCOTSSession
from client.mcots_transport import MCOTSConnection
from client.nps_transport import _timeout


class MCOTSPrimaryRejected(ValueError):
    def __init__(self, stage, result_code):
        self.stage, self.result_code = stage, result_code
        super().__init__('MCOTS primary '+stage+' was rejected')


@dataclass
class MCOTSPrimaryLogin:
    session: MCOTSSession = field(repr=False)
    response: MCOTSLoginSuccess = field(repr=False)

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


def connect_primary(endpoint, record, session_material, *, first_transaction=0,
                    connect_timeout=30, attachment_timeout=20, login_timeout=120):
    """Attach plaintext, activate RC4, send login and require its rich 0xd5 reply.

    Return the accepted primary record and open session. This does not complete
    the additional services advertised in the reply or authenticate a game UI.
    No retries are made; every failure closes the connection and cipher states.
    """
    if not isinstance(record, MCOTSLoginRecord):
        raise ValueError('expected MCOTS login record')
    login_payload = record.encode_native_record()
    attachment_payload = MCOTSAttachment(record.account_user_id, record.persona_id,
                                         record.persona_name).encode()
    if not isinstance(session_material, bytes) or len(session_material) != 32:
        raise ValueError('expected 32 retained client session bytes')
    if type(first_transaction) is not int or not 0 <= first_transaction <= 0xffffffff:
        raise ValueError('expected uint32 first transaction')
    for timeout in (connect_timeout, attachment_timeout, login_timeout):
        _timeout(timeout)
    session = MCOTSSession(MCOTSConnection.connect(endpoint, timeout=connect_timeout), session_material)
    try:
        session.send(MCOTSFrame(first_transaction, 0, attachment_payload))
        reply = session.receive(timeout=attachment_timeout)
        completion = decode_completion(reply, transaction_value=first_transaction, operation=0x1b6)
        if attachment_status(completion) != 1:
            raise MCOTSPrimaryRejected('attachment', completion.result_code)
        session.enable_encryption()
        login_transaction = (first_transaction+1) & 0xffffffff
        session.send(MCOTSFrame(login_transaction, 0, login_payload))
        reply = session.receive(timeout=login_timeout)
        if len(reply.payload) >= 2 and struct.unpack_from('<H', reply.payload)[0] == 0xd5:
            response = MCOTSLoginSuccess.from_frame(reply, transaction_value=login_transaction)
            return MCOTSPrimaryLogin(session, response)
        completion = decode_completion(reply, transaction_value=login_transaction, operation=0x69)
        if not completion.successful:
            raise MCOTSPrimaryRejected('login', completion.result_code)
        raise ValueError('MCOTS login acknowledgement lacks the recovered rich success record')
    except Exception:
        session.close()
        raise
