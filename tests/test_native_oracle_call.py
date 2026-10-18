import struct
import unittest

from tools.native_oracle import DynoOracle


class CallStubTests(unittest.TestCase):
    """Encoding-level checks that need no original binary.

    The stub bytes are the whole contract: which argument lands where, and
    where the call points. Both have been wrong in practice, so both are
    pinned here rather than discovered through a wrong oracle.
    """

    def stub(self, entry, arguments=(), tail=b'', **options):
        oracle = DynoOracle.__new__(DynoOracle)
        oracle.stub = 0x70000000
        oracle.stop = oracle.stub+0xfff0
        oracle.frame = 0x72008000
        oracle.cpu = None
        captured = {}
        oracle._reset = lambda: captured.setdefault('reset', True)
        def run(*a, **k):
            captured['run']=a
            captured['run_options']=k
        oracle._run = run
        oracle.reg = self.Registers()
        oracle.cpu = self.Recorder()
        oracle.call(entry, arguments, tail=tail, **options)
        return oracle.cpu.written, captured

    class Recorder:
        def __init__(self):
            self.written = {}

        def mem_write(self, address, data):
            self.written[address] = data

        def reg_write(self, register, value):
            pass

    class Registers:
        UC_X86_REG_ESP = 1
        UC_X86_REG_EBP = 2

    def test_arguments_are_pushed_in_reverse_so_the_first_lands_at_ebp8(self):
        written, _ = self.stub(0x403200, (0x71001000, 0x71001004))
        code = written[0x70000000]
        # The first source argument is pushed last, so it sits in the upper
        # push slot and lands at [EBP+8] once the callee builds its frame.
        first_source = struct.unpack('<I', code[6:10])[0]
        last_source = struct.unpack('<I', code[1:5])[0]
        self.assertEqual(first_source, 0x71001000)
        self.assertEqual(last_source, 0x71001004)

    def test_call_displacement_is_relative_to_the_instruction_end(self):
        written, _ = self.stub(0x403d40, (100,))
        code = written[0x70000000]
        displacement = struct.unpack('<i', code[6:10])[0]
        target = 0x70000000+5+5+displacement
        self.assertEqual(target, 0x403d40)

    def test_cleanup_drops_every_pushed_argument(self):
        written, _ = self.stub(0x405910, (1, 2))
        code = written[0x70000000]
        self.assertIn(b'\x83\xc4\x08', code, 'two dword arguments need add esp,8')

    def test_no_arguments_emit_no_cleanup(self):
        written, _ = self.stub(0x405900)
        self.assertNotIn(b'\x83\xc4', written[0x70000000])

    def test_reset_and_run_are_driven_through_the_oracle(self):
        _, captured = self.stub(0x405900)
        self.assertTrue(captured.get('reset'))
        self.assertEqual(captured['run'][1], 0x7000fff0)

    def test_instruction_budget_is_explicit_and_bounded(self):
        _, default=self.stub(0x405900)
        _, longer=self.stub(0x582e40,(1,2),cleanup=b'',instruction_limit=1_000_000)
        self.assertEqual(default['run_options']['count'],4096)
        self.assertEqual(longer['run_options']['count'],1_000_000)
        for limit in (0,-1,True,1_000_001,1.5):
            with self.subTest(limit=limit),self.assertRaises(ValueError):
                DynoOracle.__new__(DynoOracle).call(0x405900,instruction_limit=limit)

    def test_callee_cleanup_does_not_drop_arguments_twice(self):
        written,_=self.stub(0x582e40,(1,2),cleanup=b'')
        self.assertNotIn(b'\x83\xc4',written[0x70000000])


if __name__ == '__main__':
    unittest.main()
