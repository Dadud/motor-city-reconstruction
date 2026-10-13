"""Explicit pinned-HTTPS ticket authorization using the recovered DLL query."""
import math
from http.client import HTTPException

from client.auth_protocol import MAX_AUTH_BYTES, parse_ticket_response, ticket_request_target
from client.legacy_https import PinnedHTTPSConnection


class AuthenticationTransportError(RuntimeError):
    """Transport failure without credential-bearing request diagnostics."""


class AuthenticationHTTPError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'authorization server returned HTTP {status}')


class _TicketConnection(PinnedHTTPSConnection):
    # authlogin.dll 0x10001fa0 explicitly requests HTTP/1.0.
    _http_vsn = 10
    _http_vsn_str = 'HTTP/1.0'


def authorize(auth_settings, certificate_sha1, username, password, service_id, *, timeout=30):
    """Perform one HTTPS GET and return the parsed authorization decision.

    Credentials are sent only to the explicitly supplied, certificate-pinned
    host. Redirects and retries are not followed. A valid ticket is not an NPS
    login or lobby session. The return object's ticket is hidden in its repr.
    """
    target = ticket_request_target(auth_settings.base_service, username, password, service_id)
    host = auth_settings.host
    if (not isinstance(host, str) or not host or
            any(ord(c) <= 32 or ord(c) == 127 or c in '/?#@:' for c in host)):
        raise ValueError('authorization requires a hostname without a URL or port')
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or
            not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('authorization timeout must be positive and finite')
    connection = _TicketConnection(host, certificate_sha1, timeout=timeout)
    try:
        # connect verifies the installed pin before request() writes credentials.
        connection.connect()
        connection.request('GET', target, headers={
            'User-Agent': 'AuthLogin', 'Host': host, 'Connection': 'close'})
        response = connection.getresponse()
        if not 200 <= response.status <= 299:
            raise AuthenticationHTTPError(response.status)
        body = response.read(MAX_AUTH_BYTES+1)
        return parse_ticket_response(body)
    except (OSError, HTTPException):
        # Do not expose exception text: HTTP diagnostics can contain the URL.
        raise AuthenticationTransportError('authorization connection failed') from None
    finally:
        connection.close()
