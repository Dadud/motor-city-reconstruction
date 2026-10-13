"""Exercise authorization against a local TLS peer with synthetic credentials.

Requires the network extra. Generates temporary keys; no external service or
original assets are used, and no private material is printed or retained.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import socket
import ssl
import tempfile
import threading
from unittest.mock import patch

from client.auth_service import authorize, _TicketConnection, AuthenticationTransportError
from client.server_discovery import AuthSettings


def verify():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), False)
        .sign(key, hashes.SHA256()))
    pin = hashlib.sha1(certificate.public_bytes(serialization.Encoding.DER)).hexdigest()
    report = {}
    with tempfile.TemporaryDirectory(prefix='mco-auth-smoke-') as directory:
        cert_path, key_path = Path(directory)/'cert.pem', Path(directory)/'key.pem'
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert_path, key_path)
        for correct_pin in (True, False):
            observed, errors = [], []
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                listener.listen(1)
                listener.settimeout(5)
                port = listener.getsockname()[1]

                def peer():
                    data = bytearray()
                    try:
                        raw, _ = listener.accept()
                        with raw:
                            raw.settimeout(5)
                            with context.wrap_socket(raw, server_side=True) as stream:
                                while b'\r\n\r\n' not in data:
                                    try:
                                        part = stream.recv(4096)
                                    except (ssl.SSLEOFError, ConnectionResetError, ConnectionAbortedError):
                                        if correct_pin:
                                            raise
                                        break
                                    if not part:
                                        break
                                    data.extend(part)
                                    if len(data) > 8192:
                                        raise ValueError('synthetic request exceeds smoke limit')
                                observed.append(bytes(data))
                                if data:
                                    body = b'Valid=TRUE\nTicket=synthetic-ticket\n'
                                    stream.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: '+
                                        str(len(body)).encode()+b'\r\n\r\n'+body)
                    except (ssl.SSLEOFError, ConnectionResetError, ConnectionAbortedError) as error:
                        if correct_pin:
                            errors.append(type(error).__name__)
                        else:
                            observed.append(bytes(data))
                    except Exception as error:
                        errors.append(type(error).__name__)

                thread = threading.Thread(target=peer, daemon=True)
                thread.start()

                class LoopbackConnection(_TicketConnection):
                    def __init__(self, host, certificate_sha1, *, timeout):
                        super().__init__(host, certificate_sha1, port=port, timeout=timeout)

                with patch('client.auth_service._TicketConnection', LoopbackConnection):
                    try:
                        result = authorize(AuthSettings('127.0.0.1', 'AuthLogin'),
                            pin if correct_pin else '0'*40, 'synthetic', 'a b', '2176', timeout=5)
                        if not correct_pin or not result.valid or result.ticket != 'synthetic-ticket':
                            raise ValueError('authorization smoke returned unexpected result')
                    except AuthenticationTransportError:
                        if correct_pin:
                            raise
                thread.join(6)
                if thread.is_alive() or errors or len(observed) != 1:
                    raise ValueError(f'local TLS peer failed: {errors}, observations {len(observed)}')
                if correct_pin:
                    request = observed[0]
                    expected = (b'GET /AuthLogin?username=synthetic&password=a%20b&'
                                b'serviceID=2176&version=2.5 HTTP/1.0\r\n')
                    if not request.startswith(expected) or b'User-Agent: AuthLogin\r\n' not in request:
                        raise ValueError('actual HTTP authorization request differs')
                    report['pinned_request_and_ticket'] = True
                else:
                    if observed[0]:
                        raise ValueError('credentials sent despite a mismatched certificate')
                    report['wrong_pin_sent_no_http_bytes'] = True
    report['scope'] = 'local TLS peer, synthetic credentials; no fan-server account test'
    return report


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
