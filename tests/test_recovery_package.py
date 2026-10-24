from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.recovery_package import check_commands, load_packages, runner_path
from tools.function_inventory import ROOT


class RecoveryPackageTests(unittest.TestCase):
    def test_public_manifest_roots_and_runner_modules_exist(self):
        packages = load_packages(ROOT)
        self.assertIn('startup-force-tables', packages)
        self.assertIn('model-preparation', packages)

    def test_original_checks_are_explicitly_skipped_and_never_faked(self):
        package = dict(comparisons=[dict(module='tools.example', original=True)])
        commands, skipped = check_commands(package, Path('unused'), 'Release')
        self.assertEqual(commands, [])
        self.assertEqual(skipped, ['tools.example'])
        commands, skipped = check_commands(package, Path('unused'), 'Release', Path('original.exe'))
        self.assertEqual(commands[0][-1], 'original.exe')
        self.assertEqual(skipped, [])

    def test_native_runner_lookup_handles_multi_config_and_missing_targets(self):
        with tempfile.TemporaryDirectory() as temporary, patch('tools.recovery_package.sys.platform', 'win32'):
            directory = Path(temporary)
            (directory/'Release').mkdir()
            target = directory/'Release/mco_fixture_compare.exe'
            target.touch()
            self.assertEqual(runner_path(directory, 'Release', 'mco_fixture_compare'), target)
            with self.assertRaises(ValueError):
                runner_path(directory, 'Release', 'mco_missing_compare')

    def test_reviewed_comparison_arguments_reach_original_and_native_runners(self):
        package = dict(comparisons=[
            dict(module='tools.original', original=True, arguments=['--vehicle-system']),
            dict(module='tools.native', runner='mco_engine_update_compare',
                 arguments=['--vehicle-system'])], targets=['mco_engine_update_compare'])
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);(directory/'Release').mkdir()
            (directory/'Release/mco_engine_update_compare.exe').touch()
            with patch('tools.recovery_package.sys.platform', 'win32'):
                commands, skipped = check_commands(package, directory, 'Release', Path('mcity.exe'))
        self.assertEqual(skipped, [])
        self.assertEqual(commands[0][-2:], ['mcity.exe', '--vehicle-system'])
        self.assertEqual(commands[1][-1], '--vehicle-system')


if __name__ == '__main__':
    unittest.main()
