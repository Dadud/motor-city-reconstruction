import unittest
from unittest.mock import patch
from http.client import HTTPException
from client.auth_protocol import MAX_AUTH_BYTES
from client.auth_service import (authorize, AuthenticationHTTPError,
                                 AuthenticationTransportError, _TicketConnection)
from client.server_discovery import AuthSettings


class AuthServiceTests(unittest.TestCase):
    settings = AuthSettings('configured.example', 'AuthLogin')
    pin = 'A'*40

    def invoke(self):
        return authorize(self.settings, self.pin, 'synthetic', 'a b', '2176')

    def test_verification_precedes_request_and_native_query_is_preserved(self):
        with patch('client.auth_service._TicketConnection') as factory:
            connection = factory.return_value
            response = connection.getresponse.return_value
            response.status = 200
            response.read.return_value = b'Valid=TRUE\nTicket=private-ticket\n'
            result = self.invoke()
            self.assertTrue(result.valid)
            self.assertEqual(result.ticket, 'private-ticket')
            calls = [c[0] for c in connection.mock_calls]
            self.assertLess(calls.index('connect'), calls.index('request'))
            self.assertEqual(connection.request.call_args.args,
                ('GET', '/AuthLogin?username=synthetic&password=a%20b&serviceID=2176&version=2.5'))
            self.assertEqual(connection.request.call_args.kwargs['headers']['User-Agent'], 'AuthLogin')
            response.read.assert_called_once_with(MAX_AUTH_BYTES+1)
            connection.close.assert_called_once()
            self.assertNotIn('private-ticket', repr(result))
        self.assertEqual(_TicketConnection._http_vsn_str, 'HTTP/1.0')

    def test_certificate_failure_never_sends_credentials(self):
        with patch('client.auth_service._TicketConnection') as factory:
            connection = factory.return_value
            connection.connect.side_effect = OSError('private-password')
            with self.assertRaises(AuthenticationTransportError) as context:
                self.invoke()
            connection.request.assert_not_called()
            connection.close.assert_called_once()
            self.assertNotIn('private-password', str(context.exception))

    def test_compact_revival_response_reaches_decision_and_closes_transport(self):
        for body, valid in ((b'#Valid#FALSE#Ticket##reasoncode#7#reasontext#synthetic denial#', False),
                            (b'#Valid#TRUE#Ticket#synthetic-ticket#reasoncode#0#', True)):
            with patch('client.auth_service._TicketConnection') as factory:
                connection = factory.return_value
                response = connection.getresponse.return_value
                response.status = 200
                response.read.return_value = body
                result = self.invoke()
                self.assertEqual(result.valid, valid)
                self.assertNotIn('synthetic-ticket', repr(result))
                self.assertNotIn('synthetic denial', repr(result))
                connection.close.assert_called_once()

    def test_non_success_http_is_not_followed(self):
        for status in (301, 401, 500):
            with patch('client.auth_service._TicketConnection') as factory:
                connection = factory.return_value
                response = connection.getresponse.return_value
                response.status = status
                with self.assertRaises(AuthenticationHTTPError) as context:
                    self.invoke()
                self.assertEqual(context.exception.status, status)
                response.read.assert_not_called()
                connection.request.assert_called_once()
                connection.close.assert_called_once()

    def test_denial_size_limit_and_sanitized_http_errors(self):
        with patch('client.auth_service._TicketConnection') as factory:
            connection = factory.return_value
            response = connection.getresponse.return_value
            response.status = 204
            response.read.return_value = b'Valid=FALSE\nreasoncode=1\n'
            self.assertFalse(self.invoke().valid)
            response.read.return_value = b'x'*(MAX_AUTH_BYTES+1)
            with self.assertRaises(ValueError):
                self.invoke()
            connection.getresponse.side_effect = HTTPException('password=a%20b')
            with self.assertRaises(AuthenticationTransportError) as context:
                self.invoke()
            self.assertNotIn('password', str(context.exception))

    def test_invalid_configuration_precedes_connection(self):
        with patch('client.auth_service._TicketConnection') as factory:
            for host in ('https://host', 'host:443', 'host\n', 'user@host'):
                with self.assertRaises(ValueError):
                    authorize(AuthSettings(host, 'AuthLogin'), self.pin, 'user', 'pass', '2176')
            with self.assertRaises(ValueError):
                authorize(self.settings, self.pin, 'user', 'pass', '2176', timeout=0)
            factory.assert_not_called()
