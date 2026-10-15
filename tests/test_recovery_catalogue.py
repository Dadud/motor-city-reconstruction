import json
from pathlib import Path
import tempfile
import unittest
from tools.recovery_catalogue import module_metadata
from tools.recovery_export import private_output


class RecoveryCatalogueTests(unittest.TestCase):
    def fixture(self, directory):
        (directory/'analysis.json').write_text(json.dumps(dict(target_sha256='abc', function_count=2,
            ghidra_version='test', language='x86', analysis='authored fixture')))
        rows = [dict(address='00401000', name='example', external=False, thunk=False,
            body_bytes=12, direct_callees=['EXTERNAL:00000001']),
            dict(address='EXTERNAL:00000001', name='library::example', external=True,
                 thunk=False, body_bytes=0, direct_callees=[])]
        (directory/'functions.jsonl').write_text('\n'.join(json.dumps(row) for row in rows))

    def test_missing_code_cannot_count_as_exported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            (root/'decompilation.jsonl').write_text(json.dumps(dict(address='00401000', status='success')))
            result = module_metadata(root, 'abc')
            self.assertEqual(result['summary']['decompilation'], {'output-missing': 1, 'external': 1})
            (root/'pseudocode').mkdir(); (root/'pseudocode/00401000.c').write_text('authored fixture')
            self.assertEqual(module_metadata(root, 'abc')['summary']['decompilation']['success'], 1)

    def test_digest_mismatch_and_unknown_journal_entry_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            with self.assertRaises(ValueError): module_metadata(root, 'different')
            (root/'decompilation.jsonl').write_text(json.dumps(dict(address='00402000', status='success')))
            with self.assertRaises(ValueError): module_metadata(root, 'abc')

    def test_latest_attempt_replaces_prior_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            (root/'decompilation.jsonl').write_text('\n'.join(json.dumps(dict(address='00401000', status=s))
                for s in ('timeout', 'failed')))
            self.assertEqual(module_metadata(root, 'abc')['summary']['decompilation']['failed'], 1)
            self.assertEqual(module_metadata(root, 'abc')['summary']['export_pass'], 'all-internal-attempted')

    def test_enumeration_alone_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.fixture(root)
            summary = module_metadata(root, 'abc')['summary']
            self.assertEqual(summary['internal_entries'], 1)
            self.assertEqual(summary['export_pass'], 'incomplete')
            self.assertEqual(summary['decompilation']['not-attempted'], 1)

    def test_raw_output_outside_private_directory_rejected(self):
        with self.assertRaises(ValueError): private_output(Path('docs/recovery/raw'))


if __name__ == '__main__':
    unittest.main()
