import struct
import unittest
from unittest.mock import patch
from client.nps_framing import Frame, encode_message
from client.nps_persona_service import (fetch_personas, activate_persona,
                                      persona_endpoint, PersonaRequestError)
from client.server_discovery import Endpoint


class PersonaServiceTests(unittest.TestCase):
    login = Endpoint('configured.example', 8226)

    def test_retrieval_routes_request_and_decodes_header(self):
        record = struct.pack('>4IH', 99, 42, 44, 0, 4)+b'name'
        payload = b'\0\1'+struct.pack('>H', len(record))+record+b'\1'
        wire = encode_message(0x607, payload, auxiliary=len(payload)+12)
        with patch('client.nps_persona_service.query', return_value=Frame(0x607, wire[4:])) as query:
            maps = fetch_personas(self.login, 123)
            endpoint, request = query.call_args.args
            self.assertEqual(endpoint, Endpoint('configured.example', 8228))
            self.assertEqual(request[12:], struct.pack('>I', 123))
            self.assertEqual(maps.find(42, 44).account_user_id, 99)
            self.assertEqual(maps.trailing_value, 1)

    def test_activation_uses_authenticated_identity_and_explicit_success(self):
        with patch('client.nps_persona_service.query', return_value=Frame(0x207, b'')) as query:
            self.assertIsNone(activate_persona(self.login, 123, 42, 44))
            self.assertEqual(query.call_args.args[1][12:], struct.pack('>3I', 123, 42, 44))
        for opcode, result in ((0x612, -11), (0x607, -1), (0x120, -1)):
            with patch('client.nps_persona_service.query', return_value=Frame(opcode, b'secret')):
                with self.assertRaises(PersonaRequestError) as context:
                    activate_persona(self.login, 123, 42, 44)
                self.assertEqual(context.exception.native_result, result)
                self.assertNotIn('secret', str(context.exception))

    def test_failed_retrieval_never_parses_as_success(self):
        for opcode, result in ((0x602, -11), (0x207, -1)):
            with patch('client.nps_persona_service.query', return_value=Frame(opcode, b'')):
                with self.assertRaises(PersonaRequestError) as context:
                    fetch_personas(self.login, 123)
                self.assertEqual(context.exception.native_result, result)
        with patch('client.nps_persona_service.query') as query:
            with self.assertRaises(ValueError):
                fetch_personas(self.login, 0)
            query.assert_not_called()

    def test_port_derivation_bounds(self):
        self.assertEqual(persona_endpoint(Endpoint('host', 65533)).port, 65535)
        for port in (0, 65534, 65535, True):
            with self.assertRaises(ValueError):
                persona_endpoint(Endpoint('host', port))
