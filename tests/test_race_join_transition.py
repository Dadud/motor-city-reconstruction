import unittest
from client.race_join_transition import derive_race_join_transition


class RaceJoinTransitionTests(unittest.TestCase):
    def test_missing_record_and_setup_failure_do_not_join(self):
        result = derive_race_join_transition(selected_record_present=False)
        self.assertEqual((result.dialog_result, result.reported_error), (7, None))
        self.assertNotIn('connect_selected_event_server', result.actions)
        result = derive_race_join_transition(selected_record_present=True, setup_result=-51)
        self.assertEqual((result.dialog_result, result.reported_error), (7, -51))
        self.assertNotIn('join_secondary_lobby', result.actions)

    def test_join_abort_and_other_errors_are_distinct(self):
        abort = derive_race_join_transition(selected_record_present=True, setup_result=0, join_result=-51)
        self.assertEqual((abort.dialog_result, abort.reported_error), (3, None))
        failure = derive_race_join_transition(selected_record_present=True, setup_result=7, join_result=-7)
        self.assertEqual((failure.dialog_result, failure.reported_error), (7, -7))
        self.assertLess(failure.actions.index('disconnect_secondary_server'), failure.actions.index('report_join_error'))

    def test_success_applies_event_globals_after_join(self):
        result = derive_race_join_transition(selected_record_present=True, setup_result=7, join_result=0)
        self.assertEqual((result.dialog_result, result.reported_error), (4, None))
        self.assertLess(result.actions.index('join_secondary_lobby'), result.actions.index('apply_selected_event_globals'))
        with self.assertRaises(ValueError):
            derive_race_join_transition(selected_record_present=False, setup_result=0)
        with self.assertRaises(ValueError):
            derive_race_join_transition(selected_record_present=True, setup_result=-1, join_result=0)
