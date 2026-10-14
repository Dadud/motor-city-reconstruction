"""Private fan-server connection orchestration for GUI and CLI testers.

Runs configured discovery, account login, persona selection, lobby and primary
MCOTS attachment, then optional persona garage startup requests. Output is a
fixed safe summary without credentials, tickets or raw payloads.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Callable, Iterable

from client.assets import Assets
from client.catalogue import Catalogue
from client.mcots_data_service import (
    MCOTSDataClient,
    fetch_persona_startup,
    fetch_valuation_data,
)
from client.nps_crypto import installed_public_key
from client.nps_identity import installed_executable_checksum
from client.nps_persona import PersonaMapEntry
from client.online_account import authenticate
from client.server_discovery import (
    AuthSettings,
    Shard,
    fetch_shard_list,
    installed_patch_settings,
    installed_sources,
    windows_auth_settings,
)

STAGES = (
    'preflight',
    'authorization',
    'login',
    'personas',
    'persona',
    'lobby',
    'primary',
    'garage',
    'complete',
)


class FanServerSetupError(ValueError):
    """Public setup errors with fixed, non-sensitive messages."""


@dataclass(frozen=True)
class FanServerContext:
    root: str
    shard: Shard
    auth: AuthSettings
    certificate_sha1: str
    hostname: bytes
    ip_address: bytes
    fetch_garage: bool
    catalogue: Catalogue | None
    text_encoding: str | None


def _emit(on_stage, stage: str) -> None:
    if on_stage is not None:
        on_stage(stage)


def _set_stage(report: dict, stage: str, on_stage) -> None:
    report['last_stage'] = stage
    _emit(on_stage, stage)


def _cancelled(cancelled) -> bool:
    return bool(cancelled()) if callable(cancelled) else bool(cancelled)


def _default_hostname(hostname: str | None) -> bytes:
    if hostname is None:
        value = socket.gethostname().encode('ascii', 'ignore')[:63]
        return value or b'localhost'
    encoded = hostname.encode('ascii', 'ignore')
    if not encoded or bytes([0]) in encoded or len(encoded) >= 64:
        raise FanServerSetupError('hostname must fit the native lobby buffer')
    return encoded


def _default_ip_address(ip_address: str | None) -> bytes:
    if ip_address is None:
        return socket.gethostbyname('localhost').encode('ascii')
    encoded = ip_address.encode('ascii', 'ignore')
    if not encoded or bytes([0]) in encoded or len(encoded) >= 16:
        raise FanServerSetupError('ip address must fit the native lobby buffer')
    return encoded


def _persona_summaries(entries: Iterable[PersonaMapEntry], shard_id: int):
    summaries = []
    for entry in entries:
        if entry.shard_id != shard_id:
            continue
        name = entry.name.split(bytes([0]), 1)[0].decode('cp1252', 'replace')
        summaries.append({'persona_id': entry.persona_id, 'name': name})
    return summaries


def _select_persona(personas, shard_id: int, persona_id: int | None, on_personas, cancelled):
    candidates = _persona_summaries(personas.entries, shard_id)
    if not candidates:
        raise FanServerSetupError('no personas are advertised for the selected shard')
    if persona_id is not None:
        if personas.find(persona_id, shard_id) is None:
            raise FanServerSetupError('requested persona is not on the selected shard')
        return persona_id
    if on_personas is None:
        raise FanServerSetupError('persona selection requires --persona-id or an interactive picker')
    if _cancelled(cancelled):
        return None
    chosen = on_personas(candidates)
    if chosen is None:
        return None
    if type(chosen) is not int or personas.find(chosen, shard_id) is None:
        raise FanServerSetupError('selected persona is not on the selected shard')
    return chosen


def prepare_context(
    root,
    *,
    shard_id: int,
    source: str | None = None,
    auth_host: str | None = None,
    auth_service: str | None = None,
    hostname: str | None = None,
    ip_address: str | None = None,
    fetch_garage: bool = False,
    use_catalogue: bool = False,
    text_encoding: str | None = 'cp1252',
):
    sources = installed_sources(root)
    if source:
        selected = [item for item in sources if item.path == source]
        if len(selected) != 1:
            raise FanServerSetupError('unknown installed discovery source')
        discovery = selected[0]
    elif len({item.url for item in sources}) == 1:
        discovery = sources[0]
    else:
        raise FanServerSetupError('select an installed discovery source')
    shards = [item for item in fetch_shard_list(discovery.url) if item.identifier == shard_id]
    if len(shards) != 1:
        raise FanServerSetupError('requested shard is not uniquely advertised')
    settings = installed_patch_settings(root)
    if not settings or not settings.certificate_sha1:
        raise FanServerSetupError('installed certificate pin is required')
    if bool(auth_host) != bool(auth_service):
        raise FanServerSetupError('supply both explicit authentication settings')
    auth = AuthSettings(auth_host, auth_service) if auth_host else windows_auth_settings()
    if auth is None:
        raise FanServerSetupError('configured authentication settings are required')
    installed_public_key(root)
    installed_executable_checksum(root)
    catalogue = None
    if use_catalogue:
        assets = Assets(root)
        database = assets.paths.get('data/db/online.mdb')
        if database is None:
            raise FanServerSetupError('catalogue enrichment requires Data/DB/Online.mdb')
        catalogue = Catalogue.load(database)
        if text_encoding is None:
            raise FanServerSetupError('catalogue enrichment requires an explicit text encoding')
    return FanServerContext(
        root=root,
        shard=shards[0],
        auth=auth,
        certificate_sha1=settings.certificate_sha1,
        hostname=_default_hostname(hostname),
        ip_address=_default_ip_address(ip_address),
        fetch_garage=fetch_garage,
        catalogue=catalogue,
        text_encoding=text_encoding,
    )


def run_test(
    root,
    username,
    password,
    *,
    shard_id: int = 44,
    source: str | None = 'nps/shardlistip.ini',
    auth_host: str | None = None,
    auth_service: str | None = None,
    persona_id: int | None = None,
    hostname: str | None = None,
    ip_address: str | None = None,
    fetch_garage: bool = True,
    use_catalogue: bool = False,
    text_encoding: str | None = 'cp1252',
    on_stage: Callable[[str], None] | None = None,
    on_personas: Callable[[list[dict]], int | None] | None = None,
    cancelled=None,
):
    report = {
        'scope': 'account, lobby, primary MCOTS and optional persona garage startup',
        'server_version': 'not reported',
        'success': False,
        'cancelled': False,
        'preflight_passed': False,
        'account_authenticated': False,
        'lobby_connected': False,
        'primary_connected': False,
        'garage_loaded': False,
        'persona_count': 0,
        'garage_record_count': 0,
        'part_seed_count': 0,
        'part_slot_count': 0,
        'selected_persona_id': None,
        'shard_name': None,
        'shard_id': shard_id,
    }
    context = prepare_context(
        root,
        shard_id=shard_id,
        source=source,
        auth_host=auth_host,
        auth_service=auth_service,
        hostname=hostname,
        ip_address=ip_address,
        fetch_garage=fetch_garage,
        use_catalogue=use_catalogue,
        text_encoding=text_encoding,
    )
    report['shard_name'] = context.shard.name
    report['shard_id'] = context.shard.identifier
    report['preflight_passed'] = True
    _set_stage(report, 'preflight', on_stage)
    if _cancelled(cancelled):
        report['cancelled'] = True
        return report
    _set_stage(report, 'authorization', on_stage)
    account = authenticate(
        context.root,
        context.shard,
        context.auth,
        context.certificate_sha1,
        username,
        password,
    )
    report['account_authenticated'] = True
    _set_stage(report, 'login', on_stage)
    _set_stage(report, 'personas', on_stage)
    report['persona_count'] = len(account.personas.entries)
    if _cancelled(cancelled):
        report['cancelled'] = True
        return report
    _set_stage(report, 'persona', on_stage)
    selected = _select_persona(
        account.personas,
        context.shard.identifier,
        persona_id,
        on_personas,
        cancelled,
    )
    if selected is None:
        report['cancelled'] = True
        return report
    report['selected_persona_id'] = selected
    _set_stage(report, 'lobby', on_stage)
    with account.enter_connections(
        selected,
        hostname=context.hostname,
        ip_address=context.ip_address,
    ) as connections:
        report['lobby_connected'] = True
        _set_stage(report, 'primary', on_stage)
        report['primary_connected'] = True
        if context.fetch_garage:
            _set_stage(report, 'garage', on_stage)
            client = MCOTSDataClient(connections.primary.session, first_transaction=2)
            valuation_rates = None
            if context.catalogue is not None:
                valuation_rates = fetch_valuation_data(client).rates
            startup = fetch_persona_startup(
                client,
                selected,
                catalogue=context.catalogue,
                text_encoding=context.text_encoding,
                valuation_rates=valuation_rates,
            )
            report['garage_loaded'] = True
            report['garage_record_count'] = len(startup.car_pairs)
            report['part_seed_count'] = len(startup.part_seeds)
            report['part_slot_count'] = len(startup.part_slots)
    report['success'] = True
    _set_stage(report, 'complete', on_stage)
    return report
