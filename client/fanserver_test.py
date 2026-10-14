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
from client.race_entry import probe_race_entry_path
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
    'race_entry',
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
    probe_race_entry: bool


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
    probe_race_entry: bool = False,
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
        probe_race_entry=probe_race_entry,
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
    probe_race_entry: bool = False,
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
        'race_entry_probe_passed': False,
        'fast_join_tcp_preferred': None,
        'positional_updates_hz': None,
        'update_interval_seconds': None,
        'recovered_task_kinds': [],
        'room_channel_probe_passed': False,
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
        probe_race_entry=probe_race_entry,
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
        on_stage=lambda stage: _set_stage(report, stage, on_stage),
    )
    report['account_authenticated'] = True
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
    if _cancelled(cancelled):
        report['cancelled'] = True
        return report
    _set_stage(report, 'lobby', on_stage)
    with account.enter_connections(
        selected,
        hostname=context.hostname,
        ip_address=context.ip_address,
        on_stage=lambda stage: _set_stage(report, stage, on_stage),
    ) as connections:
        report['lobby_connected'] = True
        report['primary_connected'] = True
        if _cancelled(cancelled):
            report['cancelled'] = True
            return report
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
        if context.probe_race_entry:
            _set_stage(report, 'race_entry', on_stage)
            probe = probe_race_entry_path(installed_patch_settings(context.root))
            report['race_entry_probe_passed'] = probe['race_entry_probe_passed']
            report['fast_join_tcp_preferred'] = probe['fast_join_tcp_preferred']
            report['positional_updates_hz'] = probe['positional_updates_hz']
            report['update_interval_seconds'] = probe['update_interval_seconds']
            report['recovered_task_kinds'] = probe['recovered_task_kinds']
            report['room_channel_probe_passed'] = probe['room_channel_probe_passed']
    report['success'] = True
    _set_stage(report, 'complete', on_stage)
    return report


def run_test_report(root, username, password, *, on_stage=None, **options):
    """Return a shareable failure summary without exception text or account data.

    The raising developer API remains available as run_test. Failed tests retain
    the last attempted stage, rather than falsely implying later stages passed.
    """
    stage = 'preflight'

    def progress(value):
        nonlocal stage
        if value in STAGES:
            stage = value
            _emit(on_stage, value)

    try:
        return run_test(root, username, password, on_stage=progress, **options)
    except Exception as error:
        from client.online_account import AuthorizationDenied
        if isinstance(error, AuthorizationDenied):
            code = 'authorization_denied'
        elif isinstance(error, FanServerSetupError):
            code = 'setup_failed'
        elif isinstance(error, TimeoutError):
            code = 'timeout'
        elif isinstance(error, ConnectionError):
            code = 'connection_failed'
        elif isinstance(error, OSError):
            code = 'network_or_file_error'
        else:
            code = 'protocol_or_data_error'
        return {'success': False, 'cancelled': _cancelled(options.get('cancelled')),
                'last_stage': stage, 'failure_code': code,
                'server_version': 'not reported'}


def shareable_report(result):
    """Strict allowlist for reports that may leave this machine."""
    output = {'report_schema': 1, 'scope': 'account/lobby/primary/garage connection test',
              'server_version': 'not reported', 'live_race_tested': False}
    for key in ('success', 'cancelled', 'preflight_passed', 'account_authenticated',
                'lobby_connected', 'primary_connected', 'garage_loaded'):
        if type(result.get(key)) is bool:
            output[key] = result[key]
    for key in ('persona_count', 'garage_record_count', 'part_seed_count', 'part_slot_count'):
        if type(result.get(key)) is int and result[key] >= 0:
            output[key] = result[key]
    if result.get('last_stage') in STAGES:
        output['last_stage'] = result['last_stage']
    if result.get('failure_code') in ('authorization_denied', 'setup_failed', 'timeout',
            'connection_failed', 'network_or_file_error', 'protocol_or_data_error'):
        output['failure_code'] = result['failure_code']
    return output
