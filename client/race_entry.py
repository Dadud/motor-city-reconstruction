"""Recovered race-entry orchestration without live room joining.

Builds and validates the local game-network task sequence observed on the
path toward server connect, game start, channel add and mini-room list.
This does not transmit room packets or synchronize race positions.
"""
from __future__ import annotations

from dataclasses import dataclass

from client.game_network import GameNetworkTask, race_entry_task_kinds
from client.lobby_channels import (
    CHANNEL_PROTOCOL_TCP_A,
    CHANNEL_PROTOCOL_TCP_B,
    ChannelAddRequest,
    GAME_NETWORK_TASK_CHANNEL_ADD,
    GAME_NETWORK_TASK_GAME_START,
    GAME_NETWORK_TASK_MINI_ROOM_LIST,
    GAME_NETWORK_TASK_SERVER_CONNECT,
)
from client.server_discovery import PatchNetworkSettings
from client.online_sync import OnlineSyncSettings
from client.lobby_room import probe_room_channel_path

_FAST_JOIN_TCP_PROTOCOLS = (CHANNEL_PROTOCOL_TCP_A, CHANNEL_PROTOCOL_TCP_B)


@dataclass(frozen=True)
class RaceEntryPlan:
    """Validated local task envelopes for the recovered race-entry path."""

    tasks: tuple[GameNetworkTask, ...]
    fast_join_tcp_preferred: bool | None
    positional_updates_hz: int | None
    update_interval_seconds: float | None
    channel_protocol: int | None

    @property
    def task_kinds(self) -> tuple[int, ...]:
        return tuple(task.kind for task in self.tasks)


def _preferred_channel_protocol(settings: PatchNetworkSettings | None) -> int:
    if settings is None or settings.fast_join is None:
        return CHANNEL_PROTOCOL_TCP_A
    if settings.fast_join:
        return CHANNEL_PROTOCOL_TCP_A
    return CHANNEL_PROTOCOL_TCP_B


def build_race_entry_plan(
    settings: PatchNetworkSettings | None,
    *,
    server_connected: bool = True,
    requested_channel_id: int = 0,
    requested_port: int = 0,
) -> RaceEntryPlan:
    """Construct recovered task envelopes and validate channel-add inputs."""
    protocol = _preferred_channel_protocol(settings)
    channel_request = ChannelAddRequest(
        protocol,
        requested_channel_id,
        requested_port,
        server_connected,
    )
    channel_error = channel_request.validate()
    if channel_error is not None:
        raise ValueError(f'channel-add inputs rejected with native code {channel_error}')
    tasks = tuple(
        GameNetworkTask(kind, b'')
        for kind in race_entry_task_kinds()
    )
    return RaceEntryPlan(
        tasks=tasks,
        fast_join_tcp_preferred=(None if settings is None else bool(settings.fast_join)),
        positional_updates_hz=(None if settings is None else settings.positional_updates_hz),
        update_interval_seconds=OnlineSyncSettings.from_patch(settings).update_interval_seconds,
        channel_protocol=protocol,
    )


def probe_race_entry_path(settings: PatchNetworkSettings | None) -> dict:
    """Return a safe summary of recovered race-entry construction."""
    plan = build_race_entry_plan(settings)
    encoded = [task.encode() for task in plan.tasks]
    for payload in encoded:
        decoded = GameNetworkTask.decode(payload)
        if decoded.kind == GAME_NETWORK_TASK_CHANNEL_ADD:
            if decoded.normalized_result(1) != 0:
                raise ValueError('channel-add success normalization failed')
    room_probe = probe_room_channel_path(settings)
    return {
        'race_entry_probe_passed': True,
        'fast_join_tcp_preferred': plan.fast_join_tcp_preferred,
        'positional_updates_hz': plan.positional_updates_hz,
        'update_interval_seconds': plan.update_interval_seconds,
        'channel_protocol': plan.channel_protocol,
        'recovered_task_kinds': list(plan.task_kinds),
        'expects_server_connect': GAME_NETWORK_TASK_SERVER_CONNECT in plan.task_kinds,
        'expects_game_start': GAME_NETWORK_TASK_GAME_START in plan.task_kinds,
        'expects_channel_add': GAME_NETWORK_TASK_CHANNEL_ADD in plan.task_kinds,
        'expects_mini_room_list': GAME_NETWORK_TASK_MINI_ROOM_LIST in plan.task_kinds,
        'room_channel_probe_passed': room_probe['room_channel_probe_passed'],
        'expects_room_channel_add': room_probe['expects_channel_add'],
    }

