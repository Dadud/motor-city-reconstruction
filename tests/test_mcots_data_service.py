import socket
import struct
import threading
import unittest
from unittest.mock import MagicMock
from client.mcots_data_service import MCOTSDataClient, MCOTSDataRejected, encode_data_request
from client.mcots_framing import MCOTSFrame
from client.mcots_session import MCOTSSession
from client.mcots_transport import MCOTSConnection
from client.server_discovery import Endpoint


class DataServiceTests(unittest.TestCase):
    def exchange(self, server, client):
        key = bytes(range(32))
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(('127.0.0.1',0))
        listener.listen(1)
        listener.settimeout(3)
        errors = []
        def serve():
            try:
                sock,_ = listener.accept()
                with MCOTSSession(MCOTSConnection(sock),key) as session:
                    session.enable_encryption()
                    server(session)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=serve)
        thread.start()
        try:
            endpoint = Endpoint('127.0.0.1',listener.getsockname()[1])
            with MCOTSSession(MCOTSConnection.connect(endpoint,timeout=3),key) as session:
                session.enable_encryption()
                client(session)
        finally:
            thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors,[])

    def test_paged_encrypted_requests_keepalive_unrelated_frames_and_wrap(self):
        def server(session):
            request = session.receive(timeout=3)
            self.assertEqual((request.transaction_value,request.payload),
                             (0xffffffff,struct.pack('<HI',0x142,9)+bytes(4)))
            session.send(MCOTSFrame(81,0,b'other'))
            session.send(MCOTSFrame(request.transaction_value,0,struct.pack('<HHB',0x198,0,0)))
            session.send(MCOTSFrame(90,0x80,struct.pack('<I',0xf216)))
            session.send(MCOTSFrame(request.transaction_value,0,
                struct.pack('<HHB',0x143,1,255)+b'abcdefgh'))
            session.send(MCOTSFrame(request.transaction_value,0,
                struct.pack('<HHB',0x143,1,0)+b'12345678'))
            request = session.receive(timeout=3)
            self.assertEqual((request.transaction_value,request.payload),
                             (0,struct.pack('<H',0x185)+bytes(8)))
            session.send(MCOTSFrame(0,0,struct.pack('<H',0x186)+bytes(116)))
        def client(session):
            data = MCOTSDataClient(session,first_transaction=0xffffffff)
            result = data.fetch(0x142,argument=9,timeout=3)
            self.assertEqual(result.records,(b'abcdefgh',b'12345678'))
            self.assertEqual(data.pop_pending().payload,b'other')
            self.assertEqual(data.pop_pending().payload,struct.pack('<HHB',0x198,0,0))
            self.assertIsNone(data.pop_pending())
            self.assertEqual(len(data.fetch(0x185,timeout=3).records[0]),118)
        self.exchange(server,client)

    def test_correlated_rejection_keeps_stream_usable(self):
        def server(session):
            request = session.receive(timeout=3)
            session.send(MCOTSFrame(request.transaction_value,0,struct.pack('<HHI',0x66,0x142,0x83)))
            request = session.receive(timeout=3)
            session.send(MCOTSFrame(request.transaction_value,0,struct.pack('<HHB',0x143,0,0)))
        def client(session):
            data = MCOTSDataClient(session,first_transaction=2)
            with self.assertRaises(MCOTSDataRejected) as error:
                data.fetch(0x142,timeout=3)
            self.assertEqual(error.exception.result_code,0x83)
            self.assertEqual(data.fetch(0x142,timeout=3).records,())
        self.exchange(server,client)

    def test_prevalidation_and_pending_capacity(self):
        session = MagicMock()
        data = MCOTSDataClient(session,first_transaction=2,max_pending_bytes=12)
        with self.assertRaises(ValueError):
            data.fetch(0x144,argument=1)
        with self.assertRaises(ValueError):
            data.fetch(0x142,timeout=0)
        session.send.assert_not_called()
        session.receive.return_value = MCOTSFrame(99,0,b'ab')
        with self.assertRaises(ValueError):
            data.fetch(0x142)
        session.close.assert_called_once_with()
        self.assertIsNone(data.pop_pending())
        for op in (0x144,0x142,0x16b,0x185):
            self.assertEqual(encode_data_request(op),struct.pack('<H',op)+bytes(8))
