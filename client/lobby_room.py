"""Validate explicit room research inputs without selecting a live transport.

Task 7 at 0x454d50 supplies opaque values -1 and 1 to channel-add. Their
storage does not establish callable callback types or task execution order.
"""
from __future__ import annotations

from dataclasses import dataclass
from client.lobby_channels import ChannelAddRequest
from client.server_discovery import PatchNetworkSettings


@dataclass(frozen=True)
class RoomCallerValues:
    """Opaque 32-bit native values, with task 7's observed defaults.

    Signed negatives and unsigned bit patterns are accepted. No function
    invocation or pointer dereference is permitted by this research model.
    """

    primary: int = -1
    secondary: int = 1

    def validate(self) -> None:
        for label, value in ('primary', self.primary), ('secondary', self.secondary):
            if type(value) is not int or not -(1 << 31) <= value <= 0xffffffff:
                raise ValueError(f'{label} room caller value must fit 32 bits')


@dataclass(frozen=True)
class RoomChannelPlan:
    """Explicit admissible channel request; no execution or live join proof."""

    channel_request: ChannelAddRequest
    caller_values: RoomCallerValues
    channel_protocol: int


def build_room_channel_plan(
    *,
    channel_protocol: int,
    server_connected: bool = True,
    requested_channel_id: int = 0,
    requested_port: int = 0,
    existing_channel_id: int = 0,
    existing_udp_port: int | None = None,
    caller_values: RoomCallerValues | None = None,
) -> RoomChannelPlan:
    """Validate room channel inputs against recovered channel-add rules."""
    caller_values = caller_values if caller_values is not None else RoomCallerValues()
    caller_values.validate()
    channel_request = ChannelAddRequest(
        channel_protocol,
        requested_channel_id,
        requested_port,
        server_connected,
        existing_channel_id,
        existing_udp_port,
    )
    channel_error = channel_request.validate()
    if channel_error is not None:
        raise ValueError(f'room channel inputs rejected with native code {channel_error}')
    return RoomChannelPlan(
        channel_request=channel_request,
        caller_values=caller_values,
        channel_protocol=channel_protocol,
    )


def probe_room_channel_path(settings: PatchNetworkSettings | None) -> dict:
    """Report static knowledge without fabricating a room request."""
    return {
        'room_channel_probe_passed': False,
        'room_join_implemented': False,
        'channel_protocol': None,
        'channel_add_task_kind': 7,
        'channel_add_caller_values': [-1, 1],
        'configured_fast_join': None if settings is None else settings.fast_join,
        'missing_authenticated_arguments': True,
        'protocol_selection_unverified': True,
    }

