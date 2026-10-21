import unittest

from client.input_device_state import read_input_device_state


class InputDeviceStateTests(unittest.TestCase):
    def test_acquire_precedes_successful_read_and_preserves_sample(self):
        output = bytearray(b'?' * 16)
        calls = []

        def acquire(device):
            calls.append(('acquire', device))

        def read(device, size, view):
            calls.append(('read', device, size))
            view[:] = bytes(range(size))
            return 0

        self.assertEqual(read_input_device_state(
            0x1234, output, 16, ensure_acquired=acquire, get_state=read), 0)
        self.assertEqual(output, bytes(range(16)))
        self.assertEqual(calls, [('acquire', 0x1234), ('read', 0x1234, 16)])

    def test_failed_read_clears_only_requested_output_bytes(self):
        output = bytearray(b'\xaa' * 20)
        result = read_input_device_state(
            1, output, 16, ensure_acquired=lambda _device: None,
            get_state=lambda _device, _size, view: view.__setitem__(slice(None), b'X' * 16) or 0x80004005)
        self.assertEqual(result, 0x80004005)
        self.assertEqual(output, bytes(16) + b'\xaa' * 4)

    def test_invalid_inputs_are_rejected_before_calls(self):
        calls = []
        for device, size in ((-1, 4), (1, 9)):
            with self.assertRaises(ValueError):
                read_input_device_state(
                    device, bytearray(8), size,
                    ensure_acquired=lambda *_: calls.append('acquire'),
                    get_state=lambda *_: 0)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
