import unittest

from client.ini_config import IniConfig


class IniConfigTests(unittest.TestCase):
    def test_sections_and_keys_are_ordered_and_case_insensitive(self):
        config = IniConfig.from_bytes(
            b'[Garage]\r\nMake=Buick\r\nModel=GSX\r\n[Race]\r\nLimit=150\r\n')
        self.assertEqual(config.section_names, [b'Garage', b'Race'])
        self.assertEqual(config.section_key_starts, [0, 2])
        self.assertEqual(config.section_key_counts, [2, 1])
        self.assertEqual(config.keys, [b'Make', b'Model', b'Limit'])
        self.assertEqual(config.lookup(b'garage\0', b'make\0', 32), (True, b'Buick'))
        self.assertEqual(config.lookup(b'RACE\0', b'Limit\0', 8), (True, b'150'))
        self.assertEqual(config.lookup(b'Garage\0', b'missing\0', 32), (False, b''))

    def test_values_are_not_trimmed_and_lookup_truncation_persists(self):
        config = IniConfig.from_bytes(b'[ S ]\r\n Key = value  \r\n')
        self.assertEqual(config.section_names[0], b' S ')
        self.assertEqual(config.lookup(b' S \0', b' Key \0', 6), (True, b' value'))
        self.assertEqual(config.lookup(b' S \0', b' Key \0', 100), (True, b' value'))

    def test_empty_values_are_discarded_and_duplicate_section_lookup_stops_first(self):
        config = IniConfig.from_bytes(
            b'[A]\r\nEmpty=\r\nOne=1\r\nOne=2\r\n[A]\r\nTwo=2\r\n')
        self.assertEqual(config.section_key_starts, [0, 2])
        self.assertEqual(config.section_key_counts, [2, 1])
        self.assertEqual(config.lookup(b'A\0', b'Empty\0', 8), (False, b''))
        self.assertEqual(config.lookup(b'A\0', b'Two\0', 8), (False, b''))
        self.assertEqual(config.lookup(b'A\0', b'One\0', 8), (True, b'1'))

    def test_zero_maximum_truncates_found_value_persistently(self):
        config = IniConfig.from_bytes(b'[A]\r\nValue=nonempty\r\n')
        self.assertEqual(config.lookup(b'A\0', b'Value\0', 0), (True, b''))
        self.assertEqual(config.lookup(b'A\0', b'Value\0', 20), (True, b''))

    def test_final_unterminated_line_is_preserved_and_lf_only_drops_preceding_byte(self):
        config = IniConfig.from_bytes(b'[A]\r\nKey=final')
        self.assertEqual(config.lookup(b'A\0', b'Key\0', 20), (True, b'final'))
        lf_only = IniConfig.from_bytes(b'[A]\r\nKey=Value\n')
        self.assertEqual(lf_only.lookup(b'A\0', b'Key\0', 20), (True, b'Valu'))

    def test_root_keys_remain_in_flat_storage_before_section_start(self):
        config = IniConfig.from_bytes(b'Loose=yes\r\n[A]\r\nInside=ok\r\n')
        self.assertEqual(config.keys, [b'Loose', b'Inside'])
        self.assertEqual(config.section_key_starts, [1])
        self.assertEqual(config.section_key_counts, [2])
        self.assertEqual(config.lookup(b'A\0', b'Inside\0', 8), (True, b'ok'))

    def test_rejects_unterminated_lookup_names_and_oversized_lines(self):
        config = IniConfig.from_bytes(b'[A]\r\nK=V\r\n')
        with self.assertRaises(ValueError):
            config.lookup(b'A', b'K\0', 8)
        with self.assertRaises(ValueError):
            IniConfig.from_bytes(b'[A]\r\n' + b'K' * 512 + b'=v\r\n')


if __name__ == '__main__':
    unittest.main()
