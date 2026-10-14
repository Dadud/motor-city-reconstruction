"""Recovered online synchronization settings from installed patch configuration.

This module does not exchange race positions. It exposes the declared update
rate and transport preference used by the installed fan-server patch.
"""
from dataclasses import dataclass

from client.server_discovery import PatchNetworkSettings, installed_patch_settings


@dataclass(frozen=True)
class OnlineSyncSettings:
    fast_join_tcp_preferred: bool | None
    positional_update_code: int | None
    positional_updates_hz: int | None
    update_interval_seconds: float | None

    @classmethod
    def from_patch(cls, settings: PatchNetworkSettings | None):
        hz = None if settings is None else settings.positional_updates_hz
        interval = None if hz in (None, 0) else 1.0 / hz
        return cls(
            None if settings is None else settings.fast_join,
            None if settings is None else settings.positional_update_code,
            hz,
            interval,
        )


def load_online_sync_settings(root) -> OnlineSyncSettings:
    return OnlineSyncSettings.from_patch(installed_patch_settings(root))


def summarize_online_sync(settings: OnlineSyncSettings) -> dict:
    return {
        'fast_join_tcp_preferred': settings.fast_join_tcp_preferred,
        'positional_update_code': settings.positional_update_code,
        'positional_updates_hz': settings.positional_updates_hz,
        'update_interval_seconds': settings.update_interval_seconds,
    }

