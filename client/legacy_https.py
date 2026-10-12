"""Explicit certificate-pinned HTTPS for the installed fan-server policy.

The supplied patch pins a legacy SHA1 certificate fingerprint. This connection
checks that exact certificate before HTTP bytes are sent, rather than changing
the process-wide TLS policy or accepting arbitrary untrusted certificates.
"""
import hashlib
import hmac
from http.client import HTTPSConnection
import re
import ssl


class PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, host, certificate_sha1, *, port=443, timeout=10):
        if not isinstance(certificate_sha1, str) or not re.fullmatch(
                '[0-9a-fA-F]{40}', certificate_sha1):
            raise ValueError('explicit 40-digit certificate SHA1 required')
        self._expected_pin = certificate_sha1.upper()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        # The observed server's certificate is rejected by the default policy.
        # Restrict this exception to this explicit pinned connection, TLS 1.2+.
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('DEFAULT:@SECLEVEL=0')
        super().__init__(host, port=port, timeout=timeout, context=context)
        self.certificate_sha1 = None

    def connect(self):
        try:
            super().connect()
            certificate = self.sock.getpeercert(binary_form=True)
            if not certificate:
                raise ssl.CertificateError('server supplied no certificate')
            digest = hashlib.sha1(certificate).hexdigest().upper()
            if not hmac.compare_digest(digest, self._expected_pin):
                raise ssl.CertificateError('server certificate does not match installed pin')
            self.certificate_sha1 = digest
        except Exception:
            self.close()
            self.certificate_sha1 = None
            raise
