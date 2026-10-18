import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.cell_corpus import DEFAULT, cases_for, load_cases, shard_corpus, verify
from tools.function_cell import ROOT, artifacts, load_manifest, manifests


class CellCorpusTests(unittest.TestCase):
    def test_shards_preserve_cases_and_reject_tampering(self):
        manifest = load_manifest(ROOT / 'docs/recovery/cells/counter_mod4.json')
        document = dict(schema=1, target_sha256=manifest['roots'][0]['target_sha256'],
                        cells={'counter_mod4': dict(address=manifest['roots'][0]['address'],
                               cases=[dict(input=[0xffffffff], output=[3])])})
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.json'
            source.write_text(json.dumps(document), encoding='utf-8')
            shards = Path(directory) / 'shards'
            index = shard_corpus(source, shards)
            # Loading a shard must not need the original large corpus.
            source.unlink()
            self.assertEqual(load_cases('counter_mod4', shards),
                             document['cells']['counter_mod4']['cases'])
            shard = shards / (index['cells']['counter_mod4']['sha256'] + '.json')
            shard.write_bytes(shard.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                load_cases('counter_mod4', shards)

    def test_every_implemented_cell_has_cases_and_generated_runners(self):
        corpus = json.loads(DEFAULT.read_text(encoding='utf-8'))
        for path in manifests():
            manifest = load_manifest(path)
            if manifest.get('status') != 'implemented':
                continue
            with self.subTest(cell=manifest['id']):
                self.assertTrue(cases_for(manifest['id'], corpus))
                self.assertTrue(manifest.get('comparison', {}).get('body'))
                for target, content in artifacts(manifest).items():
                    if target.name.endswith(('_compare.cpp', '_compare.py')):
                        self.assertEqual(target.read_text(encoding='utf-8'), content,
                                         target.relative_to(ROOT))

    def test_empty_cases_are_rejected_before_launch(self):
        with patch('tools.cell_corpus.subprocess.run') as run:
            with self.assertRaisesRegex(ValueError, 'nonempty'):
                verify('unused', [], 'sample')
            run.assert_not_called()

    def test_missing_truncated_extra_and_wrong_outputs_fail(self):
        cases = [dict(input=[1], output=[2, 3]), dict(input=[], output=[4])]
        for output in ('', '2 3\n', '2\n4\n', '2 3\n4\n5\n', '2 9\n4\n'):
            with self.subTest(output=output), patch(
                    'tools.cell_corpus.subprocess.run',
                    return_value=subprocess.CompletedProcess([], 0, output, '')):
                with self.assertRaises(AssertionError):
                    verify('runner', cases, 'sample')

    def test_case_markers_preserve_zero_argument_calls(self):
        cases = [dict(input=[], output=[0xffffffff])]
        with patch('tools.cell_corpus.subprocess.run', return_value=
                   subprocess.CompletedProcess([], 0, '4294967295\n', '')) as run:
            result = verify('runner', cases, 'sample')
        self.assertEqual(run.call_args.kwargs['input'], '0\n')
        self.assertEqual(result['cases'], 1)
        self.assertTrue(result['exact_output_bits'])

    def test_invalid_words_and_missing_observations_fail(self):
        for case in (dict(input=[-1], output=[0]),
                     dict(input=[1 << 32], output=[0]),
                     dict(input=[True], output=[0]),
                     dict(input=[], output=[])):
            with self.subTest(case=case), self.assertRaises(ValueError):
                verify('unused', [case], 'sample')

    def test_corpus_is_bound_to_target_and_routine(self):
        document = json.loads(DEFAULT.read_text(encoding='utf-8'))
        # This path reads one cell only. Keep its real observations without
        # repeatedly copying unrelated images and connected lifecycle traces.
        corpus = dict(schema=document['schema'], target_sha256=document['target_sha256'],
                      cells={'counter_mod4': document['cells']['counter_mod4']})
        for change in ('target', 'address', 'empty', 'schema'):
            damaged = copy.deepcopy(corpus)
            if change == 'target':
                damaged['target_sha256'] = '0' * 64
            elif change == 'address':
                damaged['cells']['counter_mod4']['address'] = '0x405900'
            elif change == 'schema':
                damaged['schema'] = 99
            else:
                damaged['cells']['counter_mod4']['cases'] = []
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'corpus.json'
                path.write_text(json.dumps(damaged), encoding='utf-8')
                with self.subTest(change=change), self.assertRaises(ValueError):
                    load_cases('counter_mod4', path)


if __name__ == '__main__':
    unittest.main()
