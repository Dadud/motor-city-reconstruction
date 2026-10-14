"""Recovered lobby channel protocol values and game-network task kinds.

Static evidence from docs/lobby-channels.md; no live room join is implemented.
"""
from dataclasses import dataclass

CHANNEL_PROTOCOL_TCP_A = 0x21
CHANNEL_PROTOCOL_UDP_A = 0x2c
CHANNEL_PROTOCOL_UDP_B = 0x37
CHANNEL_PROTOCOL_TCP_B = 0x42

ACCEPTED_CHANNEL_PROTOCOLS = frozenset({
    CHANNEL_PROTOCOL_TCP_A,
    CHANNEL_PROTOCOL_UDP_A,
    CHANNEL_PROTOCOL_UDP_B,
    CHANNEL_PROTOCOL_TCP_B,
})

UDP_CHANNEL_PROTOCOLS = frozenset({CHANNEL_PROTOCOL_UDP_A, CHANNEL_PROTOCOL_UDP_B})
TCP_CHANNEL_PROTOCOLS = frozenset({CHANNEL_PROTOCOL_TCP_A, CHANNEL_PROTOCOL_TCP_B})

# Native channel-add results referenced in recovery notes.
CHANNEL_ERROR_ALREADY_OPEN = -5
CHANNEL_ERROR_NOT_CONNECTED = -6
CHANNEL_ERROR_UDP_PORT_MISMATCH = -59
CHANNEL_ERROR_SOCKET_CREATE = -31

GAME_NETWORK_TASK_SERVER_CONNECT = 0
GAME_NETWORK_TASK_UNKNOWN_1 = 1
GAME_NETWORK_TASK_RETAINED_SERVER = 2
GAME_NETWORK_TASK_SERVER_INFO = 3
GAME_NETWORK_TASK_UNKNOWN_4 = 4
GAME_NETWORK_TASK_GAME_START = 5
GAME_NETWORK_TASK_UNKNOWN_6 = 6
GAME_NETWORK_TASK_CHANNEL_ADD = 7
GAME_NETWORK_TASK_MINI_ROOM_LIST = 8
GAME_NETWORK_TASK_UNKNOWN_9 = 9

KNOWN_GAME_NETWORK_TASKS = frozenset(range(10))


@dataclass(frozen=True)
class ChannelAddRequest:
    """Pre-wire validation for a recovered channel-add argument."""

    protocol: int
    requested_channel_id: int
    requested_port: int
    server_connected: bool
    existing_channel_id: int = 0
    existing_udp_port: int | None = None

    def validate(self) -> int | None:
        """Return a native-style error code, or None if inputs are admissible."""
        if self.protocol not in ACCEPTED_CHANNEL_PROTOCOLS:
            raise ValueError('unsupported channel protocol')
        if type(self.requested_channel_id) is not int or not 0 <= self.requested_channel_id <= 0xffffffff:
            raise ValueError('channel id must be uint32')
        if type(self.requested_port) is not int or not 0 <= self.requested_port <= 0xffff:
            raise ValueError('requested port must be uint16')
        if not self.server_connected:
            return CHANNEL_ERROR_NOT_CONNECTED
        if self.requested_channel_id != 0 and self.existing_channel_id == self.requested_channel_id:
            return CHANNEL_ERROR_ALREADY_OPEN
        if self.protocol in UDP_CHANNEL_PROTOCOLS:
            if self.existing_udp_port is not None and self.requested_port not in (0, self.existing_udp_port):
                return CHANNEL_ERROR_UDP_PORT_MISMATCH
        return None


def uses_udp(protocol: int) -> bool:
    if protocol not in ACCEPTED_CHANNEL_PROTOCOLS:
        raise ValueError('unsupported channel protocol')
    return protocol in UDP_CHANNEL_PROTOCOLS


def normalize_task_result(task_kind: int, native_result: int) -> int:
    """Apply dispatcher 0x454d50 special case for channel-add task 7."""
    if task_kind not in KNOWN_GAME_NETWORK_TASKS:
        raise ValueError('unknown game network task kind')
    if task_kind == GAME_NETWORK_TASK_CHANNEL_ADD and native_result == 1:
        return 0
    return native_result

