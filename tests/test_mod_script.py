import contextlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

from client.mod_script import ModError, load_script_package, run_script_package
from tools.modkit import main
from client.mod_registry import package_archive


class ModScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = {
            'schema_version': 1, 'api_version': 'script-alpha-1', 'id': 'example.script',
            'version': '1.0.0', 'license': 'MIT', 'resources': [
                {'id': 'example.script:body', 'kind': 'vehicle', 'label': 'Authored body'}],
            'script': 'scripts/init.lua'}
        (self.root / 'scripts').mkdir()
        self.source = """
mco.register_resource('ui', 'example.script:title', 'Authored title')
mco.on('inspect', function(e)
    assert(e.offline and e.package_id == 'example.script')
    mco.emit_note('Inspected title')
end)
mco.on('preview', function(e) mco.emit_note('Preview title') end)
"""

    def write(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')
        (self.root / 'scripts/init.lua').write_bytes(self.source.encode('utf-8'))
        return load_script_package(self.root)

    def test_directory_and_zip_select_explicit_script(self):
        directory = self.write()
        (self.root / 'other.lua').write_text('error("wrong file")')
        archive = self.root / 'package.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for path in ('manifest.json', 'scripts/init.lua', 'other.lua'):
                output.write(self.root / path, path)
        self.assertEqual(load_script_package(archive), directory)
        self.assertEqual(directory.source, self.source)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['script', str(archive)]), 0)
        self.assertIn('source_bytes', output.getvalue())

    def test_malformed_manifest_and_namespace_rejected(self):
        for field, value in [('schema_version', True), ('version', '01.0.0'),
                             ('script', '../outside.lua'), ('script', 'missing.lua'),
                             ('resources', [{'id': 'elsewhere:body', 'kind': 'vehicle', 'label': 'Body'}]),
                             ('resources', [{'id': 'example.script:body', 'kind': [], 'label': 'Body'}])]:
            with self.subTest(field=field, value=value):
                original = self.manifest[field]
                self.manifest[field] = value
                with self.assertRaises(ModError):
                    self.write()
                self.manifest[field] = original

    def test_reproducible_script_archive_and_no_overwrite(self):
        package = self.write()
        first, second = self.root / 'first.zip', self.root / 'second.zip'
        package_archive(package, first)
        package_archive(package, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(load_script_package(first), package)
        with self.assertRaises(FileExistsError):
            package_archive(package, first)

    def test_duplicate_keys_invalid_json_and_source_limit(self):
        self.write()
        for raw in (b'{', b'\xff', b'{"id":1,"id":2}'):
            (self.root / 'manifest.json').write_bytes(raw)
            with self.assertRaises(ModError):
                load_script_package(self.root)
        self.write()
        (self.root / 'scripts/init.lua').write_bytes(b'x' * (1024 * 1024 + 1))
        with self.assertRaisesRegex(ModError, '1 MiB'):
            load_script_package(self.root)


@unittest.skipUnless(os.environ.get('MCO_SCRIPT_RUNNER'), 'set MCO_SCRIPT_RUNNER for native Lua integration')
class NativeScriptTests(ModScriptTests):
    @property
    def runner(self):
        return os.environ['MCO_SCRIPT_RUNNER']

    def test_real_lua_registration_and_event_isolation(self):
        package = self.write()
        result = run_script_package(package, self.runner)
        self.assertEqual([r['id'] for r in result['resources']],
                         ['example.script:body', 'example.script:title'])
        self.assertEqual(result['notes'], ['Inspected title'])
        preview = run_script_package(package, self.runner, event='preview')
        self.assertEqual(preview['notes'], ['Preview title'])

    def test_sandbox_budget_duplicate_and_failure_atomicity(self):
        for source in ('while true do end', 'os.execute("anything")',
                       "mco.register_resource('vehicle','example.script:body','Duplicate')",
                       "mco.register_resource('ui','example.script:temporary','Temp'); error('stop')"):
            with self.subTest(source=source):
                self.source = source
                with self.assertRaisesRegex(ModError, 'script execution failed'):
                    run_script_package(self.write(), self.runner)

    def test_native_bridge_rejects_truncated_and_oversized_input(self):
        for payload in (b'', b'MCOS1' + struct.pack('<I', 0xffffffff)):
            result = subprocess.run([self.runner, 'inspect'], input=payload,
                                    capture_output=True, timeout=10)
            report = json.loads(result.stdout)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report['success'])
            self.assertEqual(report['resources'], [])
