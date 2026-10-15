from dataclasses import replace
import unittest
from client.support_prediction import (PredictionWheel,SupportRecord,SupportPredictionState,
    SupportProjection,predict_support)
from client.tire_response import f32
from tools.support_prediction_oracle import cases,projection

def flat(height,code=0xe7):
    def project(q):
        return SupportProjection((q.point[0],height,q.point[2]),q.point,
            SupportRecord(q.context,q.context>>3,0,17,(1,2,3,4),code))
    return project

class SupportPredictionTests(unittest.TestCase):
    def state(self):
        return SupportPredictionState(tuple(PredictionWheel((i,0,0),(9,100+i,9),.5) for i in range(4)),
            (0,0,0),(0,0,0),context=-17,fallback_surface=12)

    def test_inclusive_contact_threshold(self):
        out=predict_support(self.state(),flat(-.5)).state
        self.assertEqual(out.support_count,4)
        self.assertTrue(all(w.contact for w in out.wheels))
        out=predict_support(self.state(),flat(f32(-.5000001))).state
        self.assertEqual(out.support_count,0)

    def test_query_alias_defines_delta_instead_of_previous_tick(self):
        out=predict_support(self.state(),flat(-.25)).state
        self.assertTrue(all(w.support_delta==-.25 for w in out.wheels))
        self.assertEqual(out.wheels[0].world_point,(0,-.25,0))

    def test_explicit_missing_surface_is_independent_from_contact(self):
        def missing(q):return SupportProjection(q.point,q.point,SupportRecord(q.context,q.context>>3,3))
        out=predict_support(self.state(),missing).state
        self.assertEqual(out.support_count,4)
        self.assertTrue(all(w.record.surface_id is None and w.surface_class==12 for w in out.wheels))

    def test_descriptor_byte_masks_to_five_bits(self):
        out=predict_support(self.state(),flat(0,0xe7)).state
        self.assertTrue(all(w.surface_class==7 for w in out.wheels))

    def test_ordered_queries_and_lookahead(self):
        s=replace(self.state(),velocity=(48,0,-48));out=predict_support(s,flat(0))
        self.assertEqual([q.slot for q in out.queries],[0,1,2,3])
        self.assertEqual(out.queries[0].point,(1,0,-1))
        self.assertEqual(out.queries[0].context,-17)
        self.assertEqual(out.queries[0].previous_world,(9,100,9))

    def test_supplied_reference_write_changes_contact(self):
        def project(q):return SupportProjection(q.point,(q.point[0],1.,q.point[2]),SupportRecord())
        out=predict_support(self.state(),project).state
        self.assertEqual(out.support_count,0)
        self.assertTrue(all(w.support_delta==-1 for w in out.wheels))

    def test_stored_world_point_reaches_next_query(self):
        first=predict_support(self.state(),flat(.1)).state
        second=predict_support(first,flat(.2))
        self.assertEqual(second.queries[0].previous_world,first.wheels[0].world_point)

    def test_transform_rounds_each_operation_at_original_24_bit_precision(self):
        s,observations=list(cases())[2]
        out=predict_support(s,lambda q:projection(q,observations))
        self.assertEqual(out.queries[3].point[1],-.07811832427978516)
        # Keeping all matrix products extended until the last store instead
        # gives -.07811833173036575 for this original comparison case.
        self.assertNotEqual(out.queries[3].point[1],-.07811833173036575)

    def test_invalid_or_missing_boundary_rejected(self):
        with self.assertRaises(ValueError):predict_support(self.state(),None)
        with self.assertRaises(ValueError):predict_support(self.state(),lambda q:None)
        with self.assertRaises(ValueError):predict_support(replace(self.state(),fallback_surface=32),flat(0))
        with self.assertRaises(ValueError):predict_support(self.state(),lambda q:SupportProjection(q.point,q.point,SupportRecord(surface_id=1)))

if __name__=='__main__':unittest.main()
