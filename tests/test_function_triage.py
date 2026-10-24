import unittest
from tools.function_triage import classify, linker_shape, regions, triage_module


class FakeOperation:
    def __init__(self, mnemonic):
        self.mnemonic = mnemonic
        self.op_str = ''


class FunctionTriageTests(unittest.TestCase):
    def test_structural_rules_precede_the_residual_candidate(self):
        self.assertEqual(classify(dict(name='FUN_1', external=True, thunk=False,
                                       body_bytes=8))[:1], ('import',))
        self.assertEqual(classify(dict(name='thunk_FUN_2', external=False,
                                       thunk=True, body_bytes=5))[:1],
                         ('thunk',))
        self.assertEqual(classify(dict(name='Catch@00438640', external=False,
                                       thunk=False, body_bytes=20))[:1],
                         ('eh-artifact',))
        self.assertEqual(classify(dict(name='switchD_00438486::caseD_4',
                                       external=False, thunk=False,
                                       body_bytes=9))[:1], ('tool-artifact',))
        self.assertEqual(classify(dict(name='FUN_3', external=False, thunk=False,
                                       body_bytes=64))[0], 'game-candidate')

    def test_linker_shapes_match_only_behaviorless_bodies(self):
        self.assertEqual(linker_shape([FakeOperation('ret')]), 'empty-stub')
        self.assertEqual(linker_shape([FakeOperation('mov'),
                                       FakeOperation('ret')]),
                         'constant-getter')
        self.assertEqual(linker_shape([FakeOperation('lea'),
                                       FakeOperation('jmp')]), 'jump-thunk')
        self.assertIsNone(linker_shape([FakeOperation('mov'),
                                        FakeOperation('add'),
                                        FakeOperation('jmp')]))
        self.assertIsNone(linker_shape([FakeOperation('call'),
                                        FakeOperation('ret')]))
        self.assertEqual(linker_shape([]), 'empty-body')

    def test_review_signals_never_mix_into_class_counts(self):
        document = dict(functions=[
            dict(address='0x400000', name='FUN_00400000', external=False,
                 thunk=False, body_bytes=200, direct_callees=[]),
            dict(address='0x401000', name='FUN_00401000', external=False,
                 thunk=False, body_bytes=200, direct_callees=['0x400000'])])
        rows, totals, review = triage_module(document)
        self.assertEqual(totals['game-candidate'], 2)
        self.assertNotIn('no_direct_callers', totals)
        self.assertEqual(review['no_direct_callers'], 1)
        self.assertEqual(rows[0]['direct_callers'], 1)
        self.assertEqual(rows[1]['direct_callers'], 0)

    def test_evidenced_supplement_remains_in_required_candidate_set(self):
        document = dict(functions=[dict(
            address='0x6f1d60', name='render_position_callback_mode8',
            external=False, thunk=False, body_bytes=0x87, direct_callees=[],
            boundary_origin='supplement', boundary_evidence='native callback table')])
        rows, totals, review = triage_module(
            document, region_dispositions={'0x6c0000':
                dict(disposition='library')})
        self.assertEqual(rows[0]['class'], 'game-candidate')
        self.assertEqual(rows[0]['rule'], 'evidenced-callable-supplement')
        self.assertTrue(rows[0]['required'])
        self.assertEqual(rows[0]['disposition'], 'evidenced-game-callback')
        self.assertEqual(totals['game-candidate'], 1)
        self.assertEqual(review['required_entries'], 1)

    def test_dispositions_decide_what_counts_as_work(self):
        document = dict(functions=[
            dict(address='0x401000', name='FUN_00401000', external=False,
                 thunk=False, body_bytes=200, direct_callees=[])])
        regions = {'0x400000': dict(block='0x400000', disposition='game'),
                   '0x680000': dict(block='0x680000', disposition='library')}
        rows, _, review = triage_module(document)
        self.assertTrue(rows[0]['required'])
        rows, _, review = triage_module(
            document, module_disposition=dict(disposition='client-region',
                                              counts_toward_required=True),
            region_dispositions=regions)
        self.assertTrue(rows[0]['required'])
        self.assertEqual(rows[0]['disposition'], 'game')
        library = dict(document)
        library['functions'] = [dict(document['functions'][0], address='0x6800b0')]
        rows, _, review = triage_module(
            library, module_disposition=dict(disposition='client-region',
                                            counts_toward_required=True),
            region_dispositions=regions)
        self.assertFalse(rows[0]['required'])
        self.assertEqual(rows[0]['disposition'], 'library-region')
        rows, _, review = triage_module(
            document, module_disposition=dict(disposition='replaceable-library',
                                              counts_toward_required=False),
            region_dispositions=regions)
        self.assertFalse(rows[0]['required'])
        self.assertEqual(rows[0]['disposition'], 'replaceable-library')

    def test_density_anomaly_is_flagged_not_decided(self):
        rows = [dict(address=f'{0x800000 + i * 8:#08x}', required=True)
                for i in range(2500)]
        rows.append(dict(address='0x430000', required=True))
        found = {row['block']: row for row in regions(rows)}
        self.assertTrue(found['0x800000']['density_anomaly'])
        self.assertEqual(found['0x800000']['entries'], 2500)
        self.assertFalse(found['0x400000']['density_anomaly'])


if __name__ == '__main__':
    unittest.main()
