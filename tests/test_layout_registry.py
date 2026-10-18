import json
import tempfile
import unittest
from pathlib import Path

from tools.layout_registry import (HEADER, check, consumers, non_offsets, render,
                                   registry, registered, scan)

DOCUMENT = {'images': {
    'sample': {'size': '0x200', 'fields': {
        '0x040': {'name': 'mass', 'type': 'float32', 'units': 'kg'},
        '0x080': {'name': 'stride_target', 'type': 'float32', 'units': ''}},
        'strides': {'0x10': 'record stride'},
        'minimum_size': '0x180',
        'consumers': ['native/src/startup_record.cpp']}}}


class LayoutRegistryTests(unittest.TestCase):
    def test_packed_fields_fit_their_actual_width(self):
        image = {'size': '0x1c', 'fields': {
            '0x1a': {'name': 'flags', 'type': 'uint16', 'width': 2},
            '0x19': {'name': 'value', 'type': 'uint8', 'width': 1}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'layouts.json'
            path.write_text(json.dumps({'images': {'packed': image}}), encoding='utf-8')
            self.assertIn('flags = 0x01a', render(registry(path)))
            image['fields']['0x1a']['width'] = 4
            path.write_text(json.dumps({'images': {'packed': image}}), encoding='utf-8')
            with self.assertRaises(ValueError):
                registry(path)

    def test_invalid_field_widths_are_rejected(self):
        for width in (0, -1, 3, True, '2'):
            document = {'images': {'sample': {'size': '0x20', 'fields': {
                '0x0': {'name': 'value', 'type': 'uint16', 'width': width}}}}}
            with self.subTest(width=width), self.assertRaises(ValueError):
                render(document)

    def test_registry_rejects_fields_without_names_or_past_the_image(self):
        for image in ({'size': '0x200', 'fields': {'0x040': {}}},
                      {'size': '0x200', 'fields': {'0x400': {'name': 'x'}}},
                      {'size': '0x200', 'fields': {'0xzz': {'name': 'x'}}}):
            with self.subTest(image=image), self.assertRaises(ValueError):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / 'layouts.json'
                    path.write_text(json.dumps({'images': {'sample': image}}), encoding='utf-8')
                    registry(path)

    def test_render_names_every_offset_and_the_size(self):
        header = render(DOCUMENT)
        self.assertIn('inline constexpr std::size_t size = 0x200;', header)
        self.assertIn('inline constexpr std::size_t mass = 0x040;', header)
        self.assertIn('inline constexpr std::size_t stride_target = 0x080;', header)
        self.assertIn('namespace sample {', header)

    def test_strides_and_guards_count_as_known_constants(self):
        known = registered(DOCUMENT) | non_offsets(DOCUMENT)
        self.assertEqual(known, {0x40, 0x80, 0x10, 0x180})

    def test_consumer_must_name_an_image_it_owns(self):
        document = json.loads(json.dumps(DOCUMENT))
        document['consumers'] = {'native/src/startup_record.cpp': ['absent']}
        with self.assertRaises(ValueError):
            scan(document)
        document['consumers'] = {'native/src/startup_record.cpp': []}
        with self.assertRaises(ValueError):
            consumers(document)

    def test_checked_in_header_cannot_drift(self):
        self.assertTrue(HEADER.is_file(), 'generated layouts header is missing')
        document = registry()
        self.assertEqual(HEADER.read_text(encoding='utf-8'), render(document))
        self.assertTrue(check(document)['header_current'])

    def test_missing_consumer_is_rejected(self):
        document = json.loads(json.dumps(DOCUMENT))
        document['consumers'] = {'native/src/absent.cpp': ['sample']}
        with self.assertRaises(ValueError):
            scan(document)


if __name__ == '__main__':
    unittest.main()
