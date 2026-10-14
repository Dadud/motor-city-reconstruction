"""Research records for caller-selected local tasks, never a join recipe.

The dispatcher establishes independent task cases, not their order or argument
construction. Patch FastJoin does not establish a channel protocol mapping.
"""
from __future__ import annotations

from dataclasses import dataclass

from client.game_network import GameNetworkTask, dispatched_task_kinds
from client.lobby_channels import ChannelAddRequest
from client.server_discovery import PatchNetworkSettings


@dataclass(frozen=True)
class RaceEntryPlan:
    """Caller-selected research tasks; their order is not recovered behavior."""

    tasks: tuple[GameNetworkTask, ...]
    configured_fast_join: bool | None
    positional_updates_hz: int | None
    channel_protocol: int

    @property
    def task_kinds(self) -> tuple[int, ...]:
        return tuple(task.kind for task in self.tasks)


def build_race_entry_plan(
    settings: PatchNetworkSettings | None,
    *,
    tasks: tuple[GameNetworkTask, ...],
    channel_protocol: int,
    server_connected: bool = True,
    requested_channel_id: int = 0,
    requested_port: int = 0,
) -> RaceEntryPlan:
    """Validate explicit research choices, with no inferred order or transport.

    Tasks are retained byte-for-byte. This does not validate their operation
    arguments, execute them, or establish whether the sequence can enter a race.
    """
    if not isinstance(tasks, tuple) or not all(isinstance(task, GameNetworkTask) for task in tasks):
        raise ValueError('research tasks must be a tuple of GameNetworkTask values')
    for task in tasks:
        task.encode()
    channel_request = ChannelAddRequest(
        channel_protocol,
        requested_channel_id,
        requested_port,
        server_connected,
    )
    channel_error = channel_request.validate()
    if channel_error is not None:
        raise ValueError(f'channel-add inputs rejected with native code {channel_error}')
    return RaceEntryPlan(
        tasks=tasks,
        configured_fast_join=(None if settings is None else settings.fast_join),
        positional_updates_hz=(None if settings is None else settings.positional_updates_hz),
        channel_protocol=channel_protocol,
    )


def probe_race_entry_path(settings: PatchNetworkSettings | None) -> dict:
    """Report recovery gaps; a local envelope round trip cannot prove joining."""
    from client.lobby_room import probe_room_channel_path
    room_probe = probe_room_channel_path(settings)
    return {
        'race_entry_probe_passed': False,
        'race_entry_implemented': False,
        'configured_fast_join': None if settings is None else settings.fast_join,
        'fast_join_tcp_preferred': None,
        'positional_updates_hz': None if settings is None else settings.positional_updates_hz,
        'update_interval_seconds': None,
        'channel_protocol': None,
        'dispatched_task_kinds': sorted(dispatched_task_kinds()),
        'recovered_task_kinds': [],
        'missing_task_order': True,
        'missing_authenticated_arguments': True,
        'protocol_selection_unverified': True,
        'room_channel_probe_passed': room_probe['room_channel_probe_passed'],
    }


