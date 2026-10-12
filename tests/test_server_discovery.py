from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from client.server_discovery import (MAX_DISCOVERY_BYTES, fetch_shard_list,
                                     installed_sources, installed_patch_settings,
                                     parse_shard_list, validate_url, windows_auth_settings)


FIXTURE = b'''[Synthetic shard]
Description=Asset-free protocol fixture
ShardId=44
LoginServerIP=localhost
LoginServerPort=8226
LobbyServerIP=localhost
LobbyServerPort=7003
MCOTSServerIP=localhost
MCOTSServerPort=43300
StatusId=0
Status_Reason=
UnknownFutureField=preserved
'''


class Response:
    status = 200
    url = 'http://localhost/ShardList'

    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data[:size]


class DiscoveryTests(unittest.TestCase):
    def test_windows_auth_reads_only_explicit_original_keys(self):
        reads = []
        class Key:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        def query(key, name):
            reads.append(name)
            return {'AuthLoginServer': ('localhost', 1),
                    'AuthLoginBaseService': ('AuthLogin', 1)}[name]
        registry = SimpleNamespace(HKEY_LOCAL_MACHINE=0x80000002, KEY_READ=1,
                                   KEY_WOW64_32KEY=0x200, REG_SZ=1,
                                   OpenKey=lambda *args: Key(), QueryValueEx=query)
        with patch.dict('sys.modules', {'winreg': registry}):
            settings = windows_auth_settings()
        self.assertEqual(settings.host, 'localhost')
        self.assertEqual(reads, ['AuthLoginServer', 'AuthLoginBaseService'])

    def test_missing_windows_auth_key(self):
        def missing(*args):
            raise FileNotFoundError()
        registry = SimpleNamespace(HKEY_LOCAL_MACHINE=0x80000002, KEY_READ=1,
                                   KEY_WOW64_32KEY=0x200, OpenKey=missing)
        with patch.dict('sys.modules', {'winreg': registry}):
            self.assertIsNone(windows_auth_settings())

    def test_patch_settings_and_inline_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory)/'Scripts'
            scripts.mkdir()
            path = scripts/'MCOExOps.INI'
            path.write_text('[Netcode]\nFast Join=1 // TCP\nPositional Updates=2 // 32Hz\n'
                            '[Install]\nServer Certificate='+'AB'*20+' // pin\n')
            settings = installed_patch_settings(directory)
            self.assertTrue(settings.fast_join)
            self.assertEqual(settings.positional_updates_hz, 32)
            self.assertEqual(settings.certificate_sha1, 'AB'*20)
            path.write_text('[Netcode]\nPositional Updates=0\n')
            settings = installed_patch_settings(directory)
            self.assertIsNone(settings.fast_join)
            self.assertIsNone(settings.positional_updates_hz)
            path.write_text('[Install]\nServer Certificate=wrong\n')
            with self.assertRaises(ValueError):
                installed_patch_settings(directory)

    def test_no_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(installed_patch_settings(directory))

    def test_observed_structure_and_unknown_fields(self):
        shard, = parse_shard_list(FIXTURE)
        self.assertEqual(shard.identifier, 44)
        self.assertEqual(shard.login.port, 8226)
        self.assertEqual(shard.lobby.port, 7003)
        self.assertEqual(shard.transactions.port, 43300)
        self.assertEqual(dict(shard.fields)['unknownfuturefield'], 'preserved')
        self.assertEqual(dict(shard.fields)['status_reason'], '')

    def test_multiple_shards(self):
        second = FIXTURE.replace(b'Synthetic shard', b'Second').replace(b'ShardId=44', b'ShardId=45')
        self.assertEqual(len(parse_shard_list(FIXTURE+second)), 2)

    def test_duplicate_ids_and_fields_rejected(self):
        for data in (FIXTURE+FIXTURE.replace(b'Synthetic shard', b'Second'),
                     FIXTURE+b'LoginServerPort=10\n'):
            with self.assertRaises(ValueError):
                parse_shard_list(data)

    def test_bounds_and_missing_fields(self):
        for value in (b'0', b'65536', b'-1', b'abc'):
            with self.assertRaises(ValueError):
                parse_shard_list(FIXTURE.replace(b'8226', value))
        with self.assertRaises(ValueError):
            parse_shard_list(FIXTURE.replace(b'LoginServerIP=localhost\n', b''))

    def test_bad_documents(self):
        for data in (b'', b'<html>bad gateway</html>', b'\xff',
                     b'x'*(MAX_DISCOVERY_BYTES+1), b'[DEFAULT]\nport=80\n'+FIXTURE):
            with self.assertRaises(ValueError):
                parse_shard_list(data)

    def test_urls_reject_credentials_and_invalid_schemes(self):
        for url in ('file:///tmp/test', 'http://user:password@localhost/list',
                    'http://localhost:0/list', 'http://localhost:70000/list',
                    'http://localhost/list#fragment', 'http://local host/list',
                    'http:///list', 'http://localhost/\nlist'):
            with self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url('https://localhost:8443/ShardList'),
                         'https://localhost:8443/ShardList')

    def test_installed_config_retains_both_sources_without_precedence_guess(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'NPS').mkdir()
            for name, host in (('ShardListIP.INI', 'first'), ('NPS/SHARDLISTIP.ini', 'second')):
                (root/name).write_text(f'[SHARDLISTS]\nshardlist=http://{host}/ShardList\n')
            sources = installed_sources(root)
            self.assertEqual([source.url for source in sources],
                             ['http://first/ShardList', 'http://second/ShardList'])

    def test_missing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                installed_sources(directory)

    def test_fetch_has_bounded_read_and_no_login(self):
        with patch('client.server_discovery.urlopen', return_value=Response(FIXTURE)) as opened:
            self.assertEqual(fetch_shard_list('http://localhost/ShardList')[0].identifier, 44)
            request = opened.call_args.args[0]
            self.assertEqual(request.get_method(), 'GET')
            self.assertIsNone(request.data)
            self.assertEqual(opened.call_args.kwargs['timeout'], 10)

    def test_oversize_response_and_invalid_timeout(self):
        with patch('client.server_discovery.urlopen',
                   return_value=Response(b'x'*(MAX_DISCOVERY_BYTES+1))):
            with self.assertRaises(ValueError):
                fetch_shard_list('http://localhost/ShardList')
        for timeout in (0, 61, float('nan')):
            with self.assertRaises(ValueError):
                fetch_shard_list('http://localhost/ShardList', timeout=timeout)

    def test_https_downgrade_rejected(self):
        with patch('client.server_discovery.urlopen', return_value=Response(FIXTURE)):
            with self.assertRaises(ValueError):
                fetch_shard_list('https://localhost/ShardList')
