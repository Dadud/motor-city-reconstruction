"""Recovered lobby room channel argument validation.

Game room operation 0x44eba0 dispatches channel-add with a room argument
structure and two caller callbacks. This module validates those inputs only;
it does not open sockets or join live rooms.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from client.lobby_channels import (
    CHANNEL_PROTOCOL_TCP_A,
    ChannelAddRequest,
)
from client.race_entry import build_race_entry_plan
from client.server_discovery import PatchNetworkSettings


@dataclass(frozen=True)
class RoomCallbacks:
    """Two callback slots stored at channel offsets 0x2c and 0x30."""

    primary: Callable[[], None] | None = None
    secondary: Callable[[], None] | None = None

    def validate(self) -> None:
        for label, callback in ('primary', self.primary), ('secondary', self.secondary):
            if callback is not None and not callable(callback):
                raise TypeError(f'{label} room callback must be callable')


@dataclass(frozen=True)
class RoomChannelPlan:
    """Validated channel-add request plus recovered race-entry task order."""

    channel_request: ChannelAddRequest
    callbacks: RoomCallbacks
    race_entry_task_kinds: tuple[int, ...]
    channel_protocol: int


def build_room_channel_plan(
    settings: PatchNetworkSettings | None,
    *,
    server_connected: bool = True,
    requested_channel_id: int = 0,
    requested_port: int = 0,
    callbacks: RoomCallbacks | None = None,
) -> RoomChannelPlan:
    """Validate room channel inputs against recovered channel-add rules."""
    callbacks = callbacks or RoomCallbacks()
    callbacks.validate()
    race_plan = build_race_entry_plan(
        settings,
        server_connected=server_connected,
        requested_channel_id=requested_channel_id,
        requested_port=requested_port,
    )
    protocol = race_plan.channel_protocol or CHANNEL_PROTOCOL_TCP_A
    channel_request = ChannelAddRequest(
        protocol,
        requested_channel_id,
        requested_port,
        server_connected,
    )
    channel_error = channel_request.validate()
    if channel_error is not None:
        raise ValueError(f'room channel inputs rejected with native code {channel_error}')
    return RoomChannelPlan(
        channel_request=channel_request,
        callbacks=callbacks,
        race_entry_task_kinds=race_plan.task_kinds,
        channel_protocol=protocol,
    )


def probe_room_channel_path(settings: PatchNetworkSettings | None) -> dict:
    """Return a safe summary of recovered room channel construction."""
    plan = build_room_channel_plan(settings)
    return {
        'room_channel_probe_passed': True,
        'channel_protocol': plan.channel_protocol,
        'race_entry_task_kinds': list(plan.race_entry_task_kinds),
        'expects_channel_add': 7 in plan.race_entry_task_kinds,
        'expects_game_start': 5 in plan.race_entry_task_kinds,
    }

