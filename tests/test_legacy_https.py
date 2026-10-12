import hashlib
from http.client import HTTPSConnection
import ssl
import unittest
from unittest.mock import Mock, patch

from client.legacy_https import PinnedHTTPSConnection


class PinnedHTTPSTests(unittest.TestCase):
    def test_missing_or_invalid_pin_is_rejected(self):
        for value in (None, '', 'A'*39, 'G'*40):
            with self.assertRaises(ValueError):
                PinnedHTTPSConnection('localhost', value)

    def test_matching_certificate(self):
        certificate = b'synthetic certificate bytes'
        pin = hashlib.sha1(certificate).hexdigest()
        connection = PinnedHTTPSConnection('localhost', pin)
        socket = Mock()
        socket.getpeercert.return_value = certificate
        def connect(instance):
            instance.sock = socket
        with patch.object(HTTPSConnection, 'connect', connect):
            connection.connect()
            self.assertEqual(connection.certificate_sha1, pin.upper())
            socket.sendall.assert_not_called()
        connection.close()

    def test_mismatch_closes_before_http_request(self):
        connection = PinnedHTTPSConnection('localhost', 'AB'*20)
        socket = Mock()
        socket.getpeercert.return_value = b'wrong certificate'
        def connect(instance):
            instance.sock = socket
        with patch.object(HTTPSConnection, 'connect', connect):
            with self.assertRaises(ssl.CertificateError):
                connection.request('POST', '/synthetic-login', body=b'sensitive payload')
        socket.sendall.assert_not_called()
        socket.close.assert_called_once()
        self.assertIsNone(connection.sock)
        self.assertIsNone(connection.certificate_sha1)

    def test_context_does_not_change_platform_default(self):
        connection = PinnedHTTPSConnection('localhost', 'AB'*20)
        self.assertEqual(connection._context.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(ssl.create_default_context().verify_mode, ssl.CERT_REQUIRED)
