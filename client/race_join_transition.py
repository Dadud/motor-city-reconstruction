"""Bounded original 5e7ba0 UI callback decisions; no network execution.

Numeric dialog results are preserved without assigning race/session semantics.
All setup and join results must come from actual caller observations.
"""
from dataclasses import dataclass


def _result(value):
    if type(value) is not int or not -0x80000000 <= value <= 0x7fffffff:
        raise ValueError('expected signed int32 observed result')
    return value


@dataclass(frozen=True)
class RaceJoinTransition:
    actions: tuple[str, ...]
    dialog_result: int
    reported_error: int | None


def derive_race_join_transition(*, selected_record_present, setup_result=None, join_result=None):
    """Recover ordering after supplied selected-record/setup/join observations."""
    if type(selected_record_present) is not bool:
        raise ValueError('selected-record presence must be boolean')
    actions = ['set_callback_state_3']
    if not selected_record_present:
        if setup_result is not None or join_result is not None:
            raise ValueError('missing selected record does not run setup or join')
        return RaceJoinTransition(tuple(actions + ['finish_dialog']), 7, None)
    actions += ['activate_callback_context', 'connect_selected_event_server']
    setup_result = _result(setup_result)
    if setup_result < 0:
        if join_result is not None:
            raise ValueError('failed setup does not run join')
        return RaceJoinTransition(tuple(actions + ['report_setup_error', 'finish_dialog']), 7, setup_result)
    join_result = _result(join_result)
    actions += ['select_secondary_lobby', 'join_secondary_lobby']
    if join_result < 0:
        actions.append('disconnect_secondary_server')
        if join_result == -51:
            return RaceJoinTransition(tuple(actions + ['finish_dialog']), 3, None)
        return RaceJoinTransition(tuple(actions + ['report_join_error', 'finish_dialog']), 7, join_result)
    return RaceJoinTransition(tuple(actions + ['apply_selected_event_globals', 'finish_dialog']), 4, None)
