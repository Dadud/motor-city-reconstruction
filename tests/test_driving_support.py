import unittest
from dataclasses import replace
from client.driving_support import DrivingSupport
from client.support_prediction import (SupportPredictionState, PredictionWheel,
    SupportProjection, SupportRecord)
from client.driving_pipeline import DrivingForces
from client.vehicle_update import update_vehicle
from tests.test_driving_pipeline import state, inputs, external


class DrivingSupportTests(unittest.TestCase):
    def prediction(self):
        return SupportPredictionState(tuple(PredictionWheel((i-1, 0, 0), (0, 0, 0), 0)
            for i in range(4)), (10, 2, -1), (999, 999, 999))

    def test_real_contact_results_choose_controller_branch(self):
        for count, branch in ((0, 'low_support'), (1, 'low_support'), (2, 'supported'), (4, 'supported')):
            queries=[]
            def project(query):
                queries.append(query)
                point=(query.point[0], query.point[1] + (0 if query.slot<count else -1), query.point[2])
                return SupportProjection(point, query.point, SupportRecord(surface_id=1, surface_code=0xa6))
            driver=DrivingSupport(self.prediction(), project, external)
            out=update_vehicle(state(), DrivingForces(inputs(), driver, lambda *args: None))
            self.assertEqual(out.branch, branch)
            self.assertEqual(out.state.support_count, count)
            self.assertEqual([w.contact for w in out.state.wheels], [i<count for i in range(4)])
            self.assertTrue(all(w.surface_record==0xa6 and w.surface_class==6 for w in out.state.wheels))
            self.assertEqual(len(queries), 4)
            self.assertLess(queries[0].point[0], 10)  # Actual controller speed, not stale 999 template.

    def test_preparation_writes_reach_predictor_and_records_persist(self):
        queries=[]
        def project(query):
            queries.append(query)
            return SupportProjection(query.point, query.point, SupportRecord(sector=17))
        def supplied(call, current, p):
            if call.stage=='prepare_vehicle':
                current.wheels[0].clear_reference=.75
                support.prediction=replace(support.prediction, position=(20, 0, 0))
            return external(call, current, p)
        support=DrivingSupport(self.prediction(), project, supplied)
        driver=DrivingForces(inputs(), support, lambda *args: None)
        first=update_vehicle(state(), driver)
        self.assertEqual(support.prediction.wheels[0].clear_reference, .75)
        self.assertGreater(queries[0].point[0], 18)
        second=update_vehicle(first.state, driver)
        self.assertEqual(queries[4].previous_world, queries[0].point)
        self.assertEqual(support.prediction.wheels[0].record.sector, 17)

    def test_projection_cannot_be_silently_omitted(self):
        with self.assertRaises(ValueError): DrivingSupport(self.prediction(), None, external)


if __name__=='__main__': unittest.main()
