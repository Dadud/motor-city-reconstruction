import unittest

from client.collision_pair_gate import (PairCandidateRecord,
                                        accepts_pair_candidate,
                                        objects_share_contact_table)


class CollisionPairGateTests(unittest.TestCase):
    def setUp(self):
        self.record = PairCandidateRecord(7, 3, 0,
                                          ((0., 1., 0.), (1., 2., 0.),
                                           (1., 3., 1.), (0., 2., 1.)),
                                          1.5)

    def test_identity_match_and_eight_contact_links(self):
        links = (3, 4, 5, 6, 7, 8, 9, 10)
        self.assertTrue(objects_share_contact_table(links, 2, 7))
        self.assertTrue(objects_share_contact_table(links, 7, 7))
        self.assertFalse(objects_share_contact_table((0,) * 8, 2, 7))

    def test_conditional_material_requires_vertical_overlap(self):
        links = (7,) + (0,) * 7
        self.assertTrue(accepts_pair_candidate(2, links, self.record))
        low = PairCandidateRecord(7, 3, 0, ((0., 1., 0.),) * 4, 1.5)
        self.assertFalse(accepts_pair_candidate(2, links, low))

    def test_material_exemptions_skip_vertical_gate(self):
        for material in (0, 0x0e):
            low = PairCandidateRecord(7, material, 0,
                                      ((0., 1., 0.),) * 4, 1.5)
            self.assertTrue(accepts_pair_candidate(2, (7,) + (0,) * 7, low))

    def test_zero_object_and_nonzero_gate_skip_vertical_gate(self):
        low_vertices = ((0., 0., 0.),) * 4
        self.assertTrue(accepts_pair_candidate(
            2, (0,) * 8, PairCandidateRecord(0, 3, 0, low_vertices, 1.)))
        self.assertTrue(accepts_pair_candidate(
            2, (0,) * 8, PairCandidateRecord(7, 3, 1, low_vertices, 1.)))

    def test_equal_height_is_rejected(self):
        equal = PairCandidateRecord(7, 3, 0,
                                    ((0., 1.5, 0.),) * 4, 1.5)
        self.assertFalse(accepts_pair_candidate(2, (7,) + (0,) * 7, equal))


if __name__ == '__main__':
    unittest.main()
