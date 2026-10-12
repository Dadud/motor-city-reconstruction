"""Read installed shard-list settings and the observed INI discovery format.

Discovery is separate from authentication and the NPS/MCOTS binary protocols.
No credentials, account operations or game-state messages are sent here.
"""
import configparser
from dataclasses import dataclass
import math
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .assets import Assets

MAX_DISCOVERY_BYTES = 64*1024


def _ini(data):
    if len(data) > MAX_DISCOVERY_BYTES:
        raise ValueError('discovery document exceeds size limit')
    try:
        text = data.decode('utf-8-sig')
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.read_string(text)
    except (UnicodeError, configparser.Error) as error:
        raise ValueError('invalid discovery INI') from error
    if parser.defaults():
        raise ValueError('discovery INI defaults are unsupported')
    return parser


def validate_url(url):
    if any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise ValueError('invalid shard-list URL')
    try:
        parsed = urlsplit(url)
        port = parsed.port
        host = parsed.hostname
    except ValueError as error:
        raise ValueError('invalid shard-list URL') from error
    if (parsed.scheme not in ('http', 'https') or not host or
            parsed.username is not None or parsed.password is not None or
            parsed.fragment or (port is not None and not 1 <= port <= 65535)):
        raise ValueError('expected HTTP(S) shard-list URL without credentials')
    return url


@dataclass(frozen=True)
class DiscoverySource:
    path: str
    url: str


@dataclass(frozen=True)
class PatchNetworkSettings:
    """Declared MCOExOps settings, not proof of patch execution or wire behavior."""
    fast_join: bool | None
    positional_update_code: int | None
    positional_updates_hz: int | None
    certificate_sha1: str | None


def installed_patch_settings(root):
    assets = Assets(root)
    path = assets.paths.get('scripts/mcoexops.ini')
    if path is None:
        return None
    with path.open('rb') as stream:
        parser = _ini(stream.read(MAX_DISCOVERY_BYTES+1))
    def option(section, name):
        sections = [s for s in parser.sections() if s.casefold() == section.casefold()]
        if not sections or not parser.has_option(sections[0], name):
            return None
        # The shipped patch settings use trailing // comments.
        return parser[sections[0]][name].split('//', 1)[0].strip()
    def code(section, name, maximum):
        value = option(section, name)
        if value is None:
            return None
        return _integer({name.casefold(): value}, name, 0, maximum)
    join = code('Netcode', 'Fast Join', 1)
    position = code('Netcode', 'Positional Updates', 3)
    pin = option('Install', 'Server Certificate')
    if pin and not re.fullmatch('[a-fA-F0-9]{40}', pin):
        raise ValueError('invalid MCOExOps certificate SHA1')
    return PatchNetworkSettings(None if join is None else bool(join), position,
                                {1: 16, 2: 32, 3: 64}.get(position),
                                pin.upper() if pin else None)


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int


@dataclass(frozen=True)
class AuthSettings:
    host: str
    base_service: str


def windows_auth_settings():
    """Read only the two original auth settings from the 32-bit registry view.

    No username, password, session ticket or unrelated registry keys are read.
    On non-Windows platforms this returns None; do not guess an auth host from
    the shard's separate binary login endpoint.
    """
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r'SOFTWARE\Electronic Arts\Motor City\AuthAuth',
                            0, winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
            host, host_type = winreg.QueryValueEx(key, 'AuthLoginServer')
            service, service_type = winreg.QueryValueEx(key, 'AuthLoginBaseService')
    except FileNotFoundError:
        return None
    if host_type != winreg.REG_SZ or service_type != winreg.REG_SZ:
        raise ValueError('unsupported original authentication registry types')
    if not isinstance(host, str) or not re.fullmatch(r'[A-Za-z0-9.-]{1,253}', host):
        raise ValueError('invalid configured authentication host')
    if not isinstance(service, str) or not re.fullmatch(r'/?[A-Za-z0-9_/-]{1,128}', service):
        raise ValueError('invalid configured authentication base service')
    return AuthSettings(host, service)


@dataclass(frozen=True)
class Shard:
    name: str
    description: str
    identifier: int
    login: Endpoint
    lobby: Endpoint
    transactions: Endpoint
    status_id: int | None
    fields: tuple[tuple[str, str], ...]


def installed_sources(root):
    """Return each explicitly configured source; do not guess native precedence."""
    assets = Assets(root)
    sources = []
    for name in ('shardlistip.ini', 'nps/shardlistip.ini'):
        path = assets.paths.get(name)
        if path is None:
            continue
        with path.open('rb') as stream:
            parser = _ini(stream.read(MAX_DISCOVERY_BYTES+1))
        sections = [s for s in parser.sections() if s.casefold() == 'shardlists']
        if len(sections) != 1 or not parser.has_option(sections[0], 'shardlist'):
            raise ValueError(f'missing SHARDLISTS/shardlist in {name}')
        sources.append(DiscoverySource(name, validate_url(parser[sections[0]]['shardlist'])))
    if not sources:
        raise ValueError('no installed shard-list configuration found')
    return tuple(sources)


def _integer(fields, name, minimum, maximum):
    value = fields.get(name.casefold(), '')
    if not re.fullmatch(r'[0-9]+', value):
        raise ValueError(f'invalid shard field {name}')
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f'shard field outside range: {name}')
    return number


def _endpoint(fields, prefix):
    host = fields.get((prefix+'IP').casefold(), '')
    # Preserve host spelling, accepting DNS names or IPv4/IPv6 literals.
    if not host or len(host) > 253 or not re.fullmatch(r'[A-Za-z0-9.:-]+', host):
        raise ValueError(f'invalid shard host: {prefix}')
    return Endpoint(host, _integer(fields, prefix+'Port', 1, 65535))


def parse_shard_list(data):
    parser = _ini(data)
    if not parser.sections():
        raise ValueError('empty shard list')
    shards = []
    identifiers = set()
    for name in parser.sections():
        fields = dict(parser.items(name))
        identifier = _integer(fields, 'ShardId', 0, 0xffffffff)
        if identifier in identifiers:
            raise ValueError('duplicate shard identifier')
        identifiers.add(identifier)
        status = (_integer(fields, 'StatusId', 0, 0xffffffff)
                  if 'statusid' in fields else None)
        shards.append(Shard(name, fields.get('description', ''), identifier,
                            _endpoint(fields, 'LoginServer'),
                            _endpoint(fields, 'LobbyServer'),
                            _endpoint(fields, 'MCOTSServer'), status,
                            tuple(fields.items())))
    return tuple(shards)


def fetch_shard_list(url, *, timeout=10):
    """One bounded public discovery GET, with normal platform TLS validation."""
    validate_url(url)
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError('discovery timeout must be within (0, 60] seconds')
    request = Request(url, headers={'User-Agent': 'MotorCityReconstruction/0.1'})
    with urlopen(request, timeout=timeout) as response:
        validate_url(response.url)
        if urlsplit(url).scheme == 'https' and urlsplit(response.url).scheme != 'https':
            raise ValueError('shard-list redirect downgraded HTTPS')
        if response.status != 200:
            raise ValueError(f'shard-list HTTP status {response.status}')
        data = response.read(MAX_DISCOVERY_BYTES+1)
    return parse_shard_list(data)
