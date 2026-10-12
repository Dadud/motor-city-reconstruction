import unittest
from client.assembly import PROFILES, body_groups, select_body, stock_body_flags
from client.fce import Model, Part
from client.catalogue import StockPart


def model(*names):
    return Model(tuple(Part(n, (0, 0, 0), (), (), ()) for n in names), 0x101015)


def component(kind, filename='', attachment=0):
    return StockPart(1, 1, kind, attachment, '', '', filename, 0, 0)


class AssemblyTests(unittest.TestCase):
    def test_stock_top_and_axle_components_use_installed_identities(self):
        source = model(':Hbody', ':Hhood', ':Htop', ':Htopchop', ':Hconvertible',
                       ':Hffender', ':Hrfender', ':Hrmirror')
        parts = [component(31001, '.chopped'), component(34001, attachment=11)]
        flags = stock_body_flags(source, parts)
        self.assertEqual(flags, 0x40000 | 0x40 | 0x2000 | 0x100 | 0x10000)
        self.assertNotIn(':Htop', [p.name for p in select_body(source, flags).parts])

    def test_scoop_choice_uses_first_supported_combination(self):
        parts = [component(40001, '.large')]
        self.assertEqual(stock_body_flags(model(':Hhood', ':Hhoodhole', ':Hscooplarge'), parts),
                         0x40000 | 6)
        self.assertEqual(stock_body_flags(model(':Hhood', ':Hscooplarge'), parts), 0x40000 | 5)

    def test_blower_forces_hood_hole_and_firewall(self):
        source = model(':Hhood', ':Hhoodhole')
        parts = [component(40001, '.bodymod'), component(340333, 'blower')]
        self.assertEqual(stock_body_flags(source, parts), 0x40000 | 2 | 0x10000)

    def test_unavailable_option_falls_back_and_missing_part_is_absent(self):
        source = model(':Htop', ':Hbumper', ':Hhood')
        flags = stock_body_flags(source, [component(31001, '.convert'), component(40001)])
        self.assertEqual(flags, 0x40000 | 0x20 | 1)
        self.assertFalse(flags & 0x800)

    def test_roof_profiles_exclude_alternative_glass_and_markers(self):
        source = model(':Hbody', ':Htop', ':Htopchop', ':Hconvertible',
                       ':Hshield', ':Hshieldchop', ':PPengine')
        expected = {'standard': {':Hbody', ':Htop', ':Hshield'},
                    'chopped': {':Hbody', ':Htopchop', ':Hshieldchop'},
                    'convertible': {':Hbody', ':Hconvertible', ':Hshield'}}
        for style, flags in PROFILES.items():
            self.assertEqual({p.name for p in select_body(source, flags).parts}, expected[style])

    def test_lod_falls_back_by_group_with_exact_case(self):
        source = model(':Hbody', ':Mbody', ':Hhood', ':Shood', ':MHOOD')
        result = select_body(source, PROFILES['standard'], lod=1)
        self.assertEqual([p.name for p in result.parts], [':Mbody', ':Hhood'])

    def test_interior_required_for_interior_children_and_omitted_at_lowest_lod(self):
        source = model(':Hbody', ':Hsteer', ':Hdashlight')
        self.assertEqual(len(select_body(source, 0).parts), 1)
        source = model(':Hbody', ':Hinterior', ':Hsteer', ':Hdashlight')
        self.assertEqual(len(select_body(source, 0).parts), 4)
        self.assertEqual(len(select_body(source, 0, lod=3).parts), 1)

    def test_configuration_gate_cage_and_fender_choices(self):
        self.assertEqual(body_groups(0xffff), ('body', 'headlight', 'interior', 'dashlight', 'steer'))
        groups = body_groups(0x40000 | 0x20000 | 0x40 | 0x1000)
        self.assertIn('cagechop', groups)
        self.assertIn('ffender', groups)
        self.assertNotIn('fenderlight', groups)
        self.assertNotIn('shield', groups)
        with self.assertRaises(ValueError):
            select_body(model(), 0, lod=4)
