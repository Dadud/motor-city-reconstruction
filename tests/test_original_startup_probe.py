"""Process ownership checks use disposable Python children, never the game."""
import subprocess
import sys
import unittest
from tools.original_startup_probe import OwnedWindowsProcess


@unittest.skipUnless(sys.platform == 'win32', 'Windows process-handle semantics')
class OwnedProcessTests(unittest.TestCase):
    def test_preserves_actual_exit_code(self):
        child=subprocess.Popen([sys.executable,'-c','raise SystemExit(17)'])
        owner=OwnedWindowsProcess(child.pid)
        try:
            self.assertEqual(child.wait(timeout=10),17)
            self.assertEqual(owner.stop(),{'already_exited':True,'exit_code':17})
            self.assertIsNone(owner.handle)
        finally:
            if owner.handle:owner.stop()
            if child.poll() is None:child.kill();child.wait()

    def test_terminates_only_retained_child(self):
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
        owner=OwnedWindowsProcess(child.pid)
        try:
            self.assertEqual(owner.stop(),{'terminated_owned_copy':True,'exit_confirmed':True})
            child.wait(timeout=10)
            self.assertIsNone(owner.handle)
        finally:
            if owner.handle:owner.stop()
            if child.poll() is None:child.kill();child.wait()

    def test_rejects_invalid_pid(self):
        with self.assertRaises(OSError):OwnedWindowsProcess(0)
