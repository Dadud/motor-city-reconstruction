import json
from pathlib import Path
import tempfile
import unittest

from tools.function_cell import (ROOT, artifacts, load_manifest, planned,
                                 review_batch, signature, workflow_steps,
                                 write_all)

MANIFEST = dict(
    id='sample_cell',
    roots=[dict(target_sha256='a' * 64, address='0x483450')],
    brief='Original sample routine.',
    decl='float sample_value(std::span<const std::byte> owner);',
    notes=['Supplied surface area is an explicit input.'],
    bookkeeping=dict(translation='missing', verification='unreviewed',
                     subsystem='sample', owner='sample-owner', scope='Scaffold.',
                     supported_domain='None yet.',
                     unresolved=['Everything.'],
                     acceptance='Not yet.'))


class FunctionCellTests(unittest.TestCase):
    def write(self, directory, manifest=None):
        path = Path(directory) / 'cell.json'
        path.write_text(json.dumps(manifest or MANIFEST), encoding='utf-8')
        return load_manifest(path)

    def test_manifest_validation_rejects_unusable_cells(self):
        import copy
        with tempfile.TemporaryDirectory() as directory:
            self.write(directory)
            for changes in (dict(id='Bad'), dict(brief=''), dict(roots=[]),
                            dict(decl='void'), dict(bookkeeping={})):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    self.write(directory, copy.deepcopy(MANIFEST) | changes)

    def test_scaffold_declares_and_defines_the_same_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write(directory)
            parsed = signature(manifest)
            self.assertEqual(parsed['name'], 'sample_value')
            self.assertEqual(parsed['return'].strip(), 'float')
            self.assertIn('float sample_value(std::span<const std::byte> owner)',
                          artifacts(manifest)[ROOT / 'native' / 'src'
                                               / 'sample_cell.cpp'])

    def test_scaffold_cannot_pass_by_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write(directory)
            generated = artifacts(manifest)
            test = generated[ROOT / 'native' / 'tests' / 'sample_cell_test.cpp']
            self.assertIn('throw', test)
            self.assertIn('scaffolded', test)
            source = generated[ROOT / 'native' / 'src' / 'sample_cell.cpp']
            self.assertIn('std::logic_error', source)

    def test_review_record_lists_every_generated_source(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write(directory)
            batch = review_batch(manifest)
            record = batch['functions']['0x483450']
            self.assertEqual(batch['target_sha256'], 'a' * 64)
            self.assertTrue(record['sources'])
            for source in record['sources']:
                self.assertIn(source.split('/')[0],
                              ('native', 'tools'))
            self.assertEqual(record['dependencies'], [])

    def test_shared_dependency_does_not_become_a_second_reviewed_root(self):
        manifest = dict(MANIFEST, shared_sources=['native/include/mco/layouts.hpp'],
                        depends_on=['0x403370'])
        batch = review_batch(manifest)
        self.assertEqual(set(batch['functions']), {'0x483450'})
        record = batch['functions']['0x483450']
        self.assertIn('native/include/mco/layouts.hpp', record['sources'])
        self.assertEqual(record['dependencies'], ['0x403370'])

    def test_typed_context_dependencies_travel_with_the_manifest(self):
        manifest = dict(MANIFEST, decl='void sample_value(RecordMachine &machine);',
                        header_includes=['mco/record_machine.hpp'],
                        comparison=dict(includes=['record_machine_cases.hpp'],
                                        body='        auto fixture = record_cases::Fixture::read(input);'))
        generated = artifacts(manifest)
        header = generated[ROOT / 'native/include/mco/sample_cell.hpp']
        self.assertLess(header.index('#include "mco/record_machine.hpp"'),
                        header.index('namespace mco'))
        comparison = generated[ROOT / 'native/tests/sample_cell_compare.cpp']
        self.assertLess(comparison.index('#include "record_machine_cases.hpp"'),
                        comparison.index('record_cases::Fixture::read(input)'))

    def test_authored_files_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write(directory)
            written, refused = write_all(manifest, dry_run=True)
            self.assertTrue(written)
            self.assertEqual(refused, [])
            self.assertEqual(len(written), len(planned(manifest)))

    def test_first_generation_preserves_existing_untracked_authored_file(self):
        from tools import function_cell
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=root / 'authored.cpp'
            target.write_bytes(b'// authored before factory registration\n')
            with patch.object(function_cell,'ROOT',root), \
                 patch.object(function_cell,'planned',return_value={target:'// scaffold\n'}), \
                 patch.object(function_cell,'_provenance',return_value={}), \
                 patch.object(function_cell,'_record'):
                written,refused=function_cell.write_all(MANIFEST)
            self.assertEqual(written,[])
            self.assertEqual(refused,['authored.cpp'])
            self.assertEqual(target.read_bytes(),b'// authored before factory registration\n')

    def test_scaffold_is_not_registered_and_implementation_is(self):
        import copy
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write(directory)
            fragment = artifacts(manifest)[ROOT / 'native' / 'cmds' / 'sample_cell.cmake']
            self.assertIn('add_executable(mco_sample_cell_test', fragment)
            self.assertNotIn('add_test', fragment)
            self.assertIn('scaffolded', fragment)
            implemented = copy.deepcopy(MANIFEST) | dict(status='implemented')
            fragment = artifacts(self.write(directory, implemented))[
                ROOT / 'native' / 'cmds' / 'sample_cell.cmake']
            self.assertIn('add_test(NAME sample_cell', fragment)
            path = Path(directory) / 'cell.json'
            path.write_text(json.dumps(MANIFEST | dict(status='halfway')),
                            encoding='utf-8')
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_provenance_lets_manifest_edits_regenerate_but_protects_edits(self):
        from tools import function_cell
        artifacts = (ROOT / 'native' / 'src' / 'sample_cell.cpp',
                     ROOT / 'native' / 'include' / 'mco' / 'sample_cell.hpp',
                     ROOT / 'native' / 'tests' / 'sample_cell_test.cpp',
                     ROOT / 'native' / 'tests' / 'sample_cell_compare.cpp',
                     ROOT / 'native' / 'cmds' / 'sample_cell.cmake',
                     ROOT / 'tools' / 'native_sample_cell_compare.py',
                     ROOT / 'docs' / 'recovery' / 'review-batches'
                     / 'sample_cell.json')
        with tempfile.TemporaryDirectory() as directory:
            for path in artifacts:
                if path.exists():
                    path.unlink()
            self.write(directory)
            original = function_cell.GENERATED
            function_cell.GENERATED = Path(directory) / 'generated.json'
            try:
                target = ROOT / 'native' / 'include' / 'mco' / 'sample_cell.hpp'
                written, refused = function_cell.write_all(
                    load_manifest(Path(directory) / 'cell.json'))
                self.assertEqual(refused, [])
                content = target.read_text(encoding='utf-8')
                self.write(directory, dict(MANIFEST, brief='Revised brief.'))
                written, refused = function_cell.write_all(
                    load_manifest(Path(directory) / 'cell.json'))
                self.assertEqual(refused, [], 'manifest edit must regenerate')
                self.assertNotEqual(target.read_text(encoding='utf-8'), content)
                target.write_bytes(b'// hand written\n')
                written, refused = function_cell.write_all(
                    load_manifest(Path(directory) / 'cell.json'))
                self.assertEqual(refused, ['native/include/mco/sample_cell.hpp'])
                self.assertEqual(target.read_text(encoding='utf-8'),
                                 '// hand written\n')
            finally:
                function_cell.GENERATED = original
                for path in artifacts:
                    if path.exists():
                        path.unlink()

    def test_ci_steps_name_both_platforms(self):
        steps = ''.join(workflow_steps('sample_cell'))
        self.assertIn("runner.os == 'Linux'", steps)
        self.assertIn('tools.native_sample_cell_compare', steps)
        self.assertIn('Release/mco_sample_cell_compare.exe', steps)


if __name__ == '__main__':
    unittest.main()
