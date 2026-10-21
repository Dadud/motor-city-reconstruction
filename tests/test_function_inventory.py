import unittest
from unittest.mock import patch
from tools.function_inventory import TARGET, canonical, generate, records


class FunctionInventoryTests(unittest.TestCase):
    def test_external_address_space_does_not_alias_default_space(self):
        self.assertEqual(canonical('EXTERNAL:0x0001'), 'EXTERNAL:0x1')
        self.assertNotEqual(canonical('EXTERNAL:0x0001'), canonical('0x1'))

    def enumeration(self):
        return dict(target_sha256=TARGET, procedure_count=2,
                    functions=[dict(address='0x00400000', name='FUN_00400000'),
                               dict(address='0x400010', name='FUN_00400010')])

    def test_rejects_wrong_artifact_and_incomplete_enumeration(self):
        for changes in (dict(target_sha256='wrong'), dict(procedure_count=3)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                generate(None, self.enumeration() | changes, None, {})

    @patch('tools.function_inventory.source_references')
    def test_address_mentions_do_not_certify_translation(self, refs):
        from collections import defaultdict
        refs.return_value = defaultdict(dict, {'0x400000': {'python': {'client/example.py:3'}}})
        rows = generate(None, self.enumeration(), None, {})
        self.assertEqual(rows[0]['translation'], 'unreviewed')
        self.assertEqual(rows[0]['decompilation'], 'not-indexed')
        self.assertEqual(rows[0]['python_refs'], ['client/example.py:3'])
        self.assertEqual(rows[1]['python_refs'], [])

    @patch('tools.function_inventory.source_references')
    def test_triage_classifies_and_absence_stays_unclassified(self, refs):
        from collections import defaultdict
        refs.return_value = defaultdict(dict)
        triage = {'0x400000': {'class': 'thunk', 'rule': 'thunk-flag-or-prefix'}}
        rows = generate(None, self.enumeration(), None, {}, triage)
        self.assertEqual(rows[0]['class'], 'thunk')
        self.assertEqual(rows[0]['triage_rule'], 'thunk-flag-or-prefix')
        self.assertEqual(rows[1]['class'], 'unclassified')
        self.assertEqual(rows[1]['triage_rule'], '')

    @patch('tools.function_inventory.source_references')
    def test_review_for_nonexistent_function_is_rejected(self, refs):
        with self.assertRaises(ValueError):
            generate(None, self.enumeration(), None, {'0x500000': {}})

    def test_saved_mcp_metadata_unwraps_without_exporting_code(self):
        import json
        item = dict(operation='analyze_function', normalized_result='private pseudocode')
        wrapper = dict(content=[dict(type='text', text=json.dumps(item))])
        self.assertEqual(list(records(wrapper)), [item])
        self.assertEqual(list(records(dict(content=[dict(type='text', text='bad json')]))), [])

    def test_exported_evidence_bundle_records_are_indexable(self):
        item = dict(operation='analyze_function', normalized_result={'pseudocode': 'void f(){}'})
        self.assertEqual(list(records({'records': [item]})), [item])


if __name__ == '__main__':
    unittest.main()
