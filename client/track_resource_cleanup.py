"""Bounded translation of the native track-resource teardown path.

The addresses here are observed global slots, not semantic field names. The
original allocator and the ownership history that populates these slots remain
external inputs to this adapter.
"""
from collections.abc import Callable, MutableMapping
from typing import Any


TRACK_RESOURCE_COUNT = '0x0097c414'
TRACK_RESOURCE_A = '0x0097c3fc'
TRACK_RESOURCE_B = '0x0097c410'
TRACK_BASE_POINTER = '0x0097c408'
TRACK_MODE_FLAG = '0x00988e28'
AUXILIARY_RESOURCE = '0x00988e98'


def _release_slot(globals_: MutableMapping[str, Any], address: str,
                  release: Callable[[Any], None]) -> None:
    pointer = globals_.get(address, 0)
    if pointer != 0 and pointer is not None:
        release(pointer)
        globals_[address] = 0


def release_track_loader_globals(globals_: MutableMapping[str, Any],
                                 release: Callable[[Any], None]) -> None:
    """Translate 0x4287a0's ordered stores and two conditional releases."""
    globals_[TRACK_RESOURCE_COUNT] = 0
    _release_slot(globals_, TRACK_RESOURCE_A, release)
    _release_slot(globals_, TRACK_RESOURCE_B, release)
    # 0x590b40, called between the releases and this store, is an observed
    # one-byte RET body and has no state effect in the analyzed executable.
    globals_[TRACK_BASE_POINTER] = 0


def close_track_loader_globals(globals_: MutableMapping[str, Any],
                               release: Callable[[Any], None]) -> None:
    """Translate 0x42ce30 -> 0x4287a0 -> 0x42e3d0 state cleanup."""
    globals_[TRACK_MODE_FLAG] = 0
    release_track_loader_globals(globals_, release)
    _release_slot(globals_, AUXILIARY_RESOURCE, release)
