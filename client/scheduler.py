"""Recovered callback-list ordering/execution, not a game-loop clock.

Entries use stable IDs rather than pointers. Execution snapshots the count but
reads each entry immediately before calling it, preserving original mutation
visibility. Callbacks and storage allocation are supplied by the caller.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ScheduledCall:
    priority: int
    callback: int
    payload: int

    def __post_init__(self):
        if type(self.priority) is not int or not -(1 << 31) <= self.priority < (1 << 31):
            raise ValueError('priority must be signed int32')
        for value in (self.callback, self.payload):
            if type(value) is not int or not 0 <= value < (1 << 32):
                raise ValueError('callback and payload must be uint32')


def insert_callback(entries: list[ScheduledCall], entry: ScheduledCall) -> None:
    """Original 0x565d20: ascending signed priority, stable equal priorities."""
    index = next((i for i, current in enumerate(entries)
                  if entry.priority < current.priority), len(entries))
    entries.insert(index, entry)


def execute_callbacks(entries: list[ScheduledCall], dispatch: Callable[[int, int], None]) -> None:
    """Original 0x565e40: one argument; return ignored; no priority/rate test.

    The original assumes count entries stay addressable throughout execution.
    The reconstructed boundary rejects shortening storage rather than reading
    beyond it. Replacing later entries and appending entries remain supported.
    """
    count = len(entries)
    for index in range(count):
        if index >= len(entries):
            raise ValueError('callback storage shortened during execution')
        entry = entries[index]
        if entry.callback:
            dispatch(entry.callback, entry.payload)


def selected_iterations(adjustment_enabled: bool, adjustment_mode: int, frame_counter: int) -> int:
    """0x568519–0x56857b selector; mode meanings remain external."""
    if (type(adjustment_enabled) is not bool or type(adjustment_mode) is not int
            or not -(1 << 31) <= adjustment_mode < (1 << 31)):
        raise ValueError('selector requires bool and integer mode')
    if type(frame_counter) is not int or not -(1 << 31) <= frame_counter < (1 << 31):
        raise ValueError('frame counter must be signed int32')
    if not adjustment_enabled:
        return 1
    if adjustment_mode == 0:
        return int(frame_counter % 4 == 0)
    if adjustment_mode == 1:
        return int(frame_counter % 2 == 0)
    return 2 if adjustment_mode == 3 else 1


def pending_iterations(clock_counter: int, processed_counter: int) -> int:
    """0x568863–0x5688a0 signed wrapping delta, maximum sixteen updates."""
    for value in (clock_counter, processed_counter):
        if type(value) is not int or not 0 <= value < (1 << 32):
            raise ValueError('clock counters must be uint32')
    delta = (clock_counter - processed_counter) & 0xffffffff
    if delta & 0x80000000:
        delta -= 1 << 32
    return max(0, min(16, delta))


def execute_batch(counter: int, iterations: int, inhibited: bool,
                  first: Callable[[], None], second: Callable[[], None],
                  after: Callable[[], None]) -> int:
    """Original 0x56857b–0x5685c5, supplied lists and post-iteration callback."""
    if type(counter) is not int or not 0 <= counter < (1 << 32):
        raise ValueError('counter must be uint32')
    if type(iterations) is not int or not 0 <= iterations <= 2:
        raise ValueError('selected iterations must be 0, 1 or 2')
    if type(inhibited) is not bool:
        raise ValueError('inhibited must be bool')
    if inhibited:
        return counter
    for _ in range(iterations):
        if not counter & 1:
            first()
        second()
        after()
        counter = (counter + 1) & 0xffffffff
    return counter
