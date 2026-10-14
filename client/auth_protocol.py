"""Recovered authlogin.dll request encoding and ticket-response fields.

Source SHA256 b4822e997cd86c0890fafb6a395013d61daa413f70880d3e26e8b660a24635f6.
Static ranges 0x10001fa0, 0x100027d0, 0x10004090 and 0x10007010.
These helpers do not establish an authenticated NPS or MCOTS session.
"""
from dataclasses import dataclass, field
import re

MAX_AUTH_BYTES = 64*1024
_ESCAPED = frozenset(b' !"#$%&*+,/:;<=>?@[\\]^`{|}~')


def encode_password(password):
    """Native selective byte escaping, not urllib's general query encoding.

    Original narrow-character encoding of non-ASCII passwords is unresolved.
    The portable interface therefore currently accepts printable ASCII only.
    """
    if not isinstance(password, str) or not all(32 <= ord(c) <= 126 for c in password):
        raise ValueError('password encoding currently requires printable ASCII')
    if len(password) > 1024:
        raise ValueError('password exceeds supported size')
    return ''.join(f'%{ord(c):02X}' if ord(c) in _ESCAPED else c for c in password)


def ticket_request_target(base_service, username, password, service_id):
    """Recovered core GET query, excluding optional clientIP/igrID fields.

    Return value contains credentials and must never be logged. The caller
    supplies the recovered service ID; no default game ID is guessed here.
    Native username/service fields are appended without password-style escaping.
    Limit them to unambiguous ASCII query tokens in this initial interface.
    """
    for value in (username, service_id):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}', value):
            raise ValueError('unsupported authentication query token')
    if not isinstance(base_service, str) or not re.fullmatch(r'/?[A-Za-z0-9_/-]{1,128}', base_service):
        raise ValueError('invalid authentication service path')
    if any(part in ('.', '..', '') for part in base_service.lstrip('/').split('/')):
        raise ValueError('invalid authentication service path')
    target = '/'+base_service.lstrip('/')+'?username='+username
    if password:
        target += '&password='+encode_password(password)
    elif not isinstance(password, str):
        raise ValueError('expected password text')
    return target+'&serviceID='+service_id+'&version=2.5'


@dataclass(frozen=True)
class TicketResponse:
    valid: bool
    reason_code: str
    reason_text: str = field(repr=False)
    ticket: str = field(repr=False)


def parse_ticket_response(data):
    """Parse line responses and the observed Revival hash-pair envelope.

    Native keys: Valid, reasoncode, reasontext and Ticket. Other ping/URL fields
    are not acted upon. Duplicate keys retain the first parsed value. This is
    a bounded portable decoder; malformed success responses are rejected.
    """
    if len(data) > MAX_AUTH_BYTES:
        raise ValueError('authentication response exceeds size limit')
    try:
        text = data.decode('ascii')
    except UnicodeError as error:
        raise ValueError('unsupported authentication response encoding') from error
    if '\0' in text:
        raise ValueError('invalid authentication response')
    fields = {}
    compact = text.strip()
    # Live Revival returns #key#value pairs, including empty Ticket on denial.
    # This is an observed server envelope, not a claim about the DLL's line
    # decoder. Do not translate hashes in values or reinterpret line comments.
    if compact.startswith('#') and compact.split('#', 2)[1] in (
            'Valid', 'Ticket', 'reasoncode', 'reasontext', 'reasonurl',
            'pingHost', 'pingPath', 'pingtime', 'pingPort', 'igrID'):
        if not compact.endswith('#') or '\n' in compact or '\r' in compact:
            raise ValueError('invalid hash-pair authentication envelope')
        tokens = compact[1:-1].split('#')
        if len(tokens) % 2:
            raise ValueError('incomplete hash-pair authentication field')
        for key, value in zip(tokens[::2], tokens[1::2]):
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', key):
                raise ValueError('invalid hash-pair authentication key')
            fields.setdefault(key, value)
    else:
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            for separator in ('=', ' ', '\t', ','):
                if separator in line:
                    key, value = line.split(separator, 1)
                    fields.setdefault(key.strip(), value.strip())
                    break
    if fields.get('Valid') not in ('TRUE', 'FALSE'):
        raise ValueError('authentication response missing supported Valid field')
    valid = fields['Valid'] == 'TRUE'
    ticket = fields.get('Ticket', '')
    if valid and not ticket:
        raise ValueError('authentication success response lacks ticket')
    return TicketResponse(valid, fields.get('reasoncode', ''),
                          fields.get('reasontext', ''), ticket)
