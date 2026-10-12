import unittest

from client.auth_protocol import (MAX_AUTH_BYTES, encode_password,
                                   parse_ticket_response, ticket_request_target)


class AuthProtocolTests(unittest.TestCase):
    def test_native_password_escape_set(self):
        self.assertEqual(encode_password('a b+&%~'), 'a%20b%2B%26%25%7E')
        self.assertEqual(encode_password("AZaz09-_.()'"), "AZaz09-_.()'")
        self.assertEqual(encode_password('=[]{}/'), '%3D%5B%5D%7B%7D%2F')

    def test_password_limit_and_encoding(self):
        for value in ('a\n', 'é', 'x'*1025, None):
            with self.assertRaises(ValueError):
                encode_password(value)

    def test_core_request_query_order(self):
        self.assertEqual(ticket_request_target('AuthLogin', 'synthetic', 'a b', 'TEST'),
                         '/AuthLogin?username=synthetic&password=a%20b&serviceID=TEST&version=2.5')
        self.assertNotIn('password=', ticket_request_target('/AuthLogin', 'synthetic', '', 'TEST'))

    def test_query_injection_rejected(self):
        for username in ('test&serviceID=other', 'test?password=other', 'test\r\n'):
            with self.assertRaises(ValueError):
                ticket_request_target('AuthLogin', username, 'test', 'TEST')

    def test_ticket_and_diagnostic_are_not_in_repr(self):
        result = parse_ticket_response(b'Valid=TRUE\r\nTicket=synthetic-secret\r\n'
                                       b'reasoncode=0\r\nreasontext=private detail\r\n')
        self.assertTrue(result.valid)
        self.assertEqual(result.ticket, 'synthetic-secret')
        self.assertNotIn('synthetic-secret', repr(result))
        self.assertNotIn('private detail', repr(result))

    def test_denial_and_separator_variants(self):
        for separator in (b'=', b' ', b'\t', b','):
            result = parse_ticket_response(b'#comment\nValid'+separator+b'FALSE\n'
                                           b'reasoncode'+separator+b'1\n')
            self.assertFalse(result.valid)
            self.assertEqual(result.reason_code, '1')

    def test_first_duplicate_value_retained(self):
        self.assertFalse(parse_ticket_response(b'Valid=FALSE\nValid=TRUE\n').valid)

    def test_malformed_and_missing_success_ticket(self):
        for data in (b'Valid=TRUE\n', b'Valid=true\n', b'<html>error</html>',
                     b'Valid=FALSE\x00\n', b'\xff', b'x'*(MAX_AUTH_BYTES+1)):
            with self.assertRaises(ValueError):
                parse_ticket_response(data)
