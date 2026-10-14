import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from client.mod_registry import ModError, build_registry, load_package, package_archive, read_files
from tools.modkit import main, preview_svg

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/mods/garage"
RED = ROOT / "examples/mods/garage-red"


class ModRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def authored(self, pid="test.base", dependencies=None, replaces=None):
        directory = self.root / pid
        directory.mkdir()
        manifest = {"schema_version": 1, "api_version": "data-alpha-1", "id": pid,
                    "version": "1.0.0", "author": "Tester", "license": "MIT",
                    "dependencies": dependencies or {},
                    "resources": [{"id": pid + ":body", "kind": "vehicle", "path": "body.json"}]}
        if replaces:
            manifest["resources"][0]["replaces"] = {"id": replaces, "version": "1.0.0"}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        (directory / "body.json").write_text(json.dumps({"schema_version": 1, "label": pid}))
        return directory

    def test_example_round_trip_registry_and_actual_preview(self):
        original = load_package(EXAMPLE)
        red = load_package(RED)
        first, second = self.root / "first.zip", self.root / "second.zip"
        package_archive(original, first)
        package_archive(original, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(load_package(first).digest, original.digest)
        order, registry = build_registry([red, load_package(first)])
        reverse_order, reverse_registry = build_registry([original, red])
        self.assertEqual([p.id for p in order], [p.id for p in reverse_order])
        self.assertEqual(registry, reverse_registry)
        self.assertEqual(registry["example.garage:body"].provider, "example.red")
        svg = preview_svg(registry["example.garage:body"])
        self.assertIn('<polygon points="', svg)
        self.assertIn('fill="#ef4444"', svg)
        with self.assertRaises(FileExistsError):
            package_archive(original, first)

    def test_cli_end_to_end_and_failure(self):
        archive, preview = self.root / "mod.zip", self.root / "preview.svg"
        self.assertEqual(main(["package", str(EXAMPLE), "--output", str(archive)]), 0)
        self.assertEqual(main(["validate", str(archive)]), 0)
        self.assertEqual(main(["preview", str(archive), "--resource", "example.garage:body", "--output", str(preview)]), 0)
        self.assertIn("polygon", preview.read_text())
        self.assertEqual(main(["validate", str(RED)]), 2)

    def test_missing_wrong_version_and_cycle(self):
        a = self.authored("test.a", {"test.b": "1.0.0"})
        with self.assertRaisesRegex(ModError, "missing dependency test.b"):
            build_registry([load_package(a)])
        b = self.authored("test.b", {"test.a": "1.0.0"})
        with self.assertRaisesRegex(ModError, "dependency cycle"):
            build_registry([load_package(a), load_package(b)])
        manifest = json.loads((b / "manifest.json").read_text())
        manifest["dependencies"] = {}
        manifest["version"] = "2.0.0"
        (b / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ModError, "requires 1.0.0, found 2.0.0"):
            build_registry([load_package(a), load_package(b)])

    def test_replacement_conflict_and_missing_target(self):
        base = load_package(self.authored())
        a = load_package(self.authored("test.a", {"test.base": "1.0.0"}, "test.base:body"))
        b = load_package(self.authored("test.b", {"test.base": "1.0.0"}, "test.base:body"))
        with self.assertRaisesRegex(ModError, "replacement conflict"):
            build_registry([base, a, b])
        wrong = load_package(self.authored("test.wrong", {"test.base": "1.0.0"}, "test.base:absent"))
        with self.assertRaisesRegex(ModError, "does not exist"):
            build_registry([base, wrong])
        with self.assertRaisesRegex(ModError, "duplicate package ID"):
            build_registry([base, base])

    def test_zip_traversal_collision_symlink_and_size(self):
        for index, name in enumerate(("../escape", "/escape", "C:/escape", "folder\\escape", "CON.json", "file. ")):
            archive = self.root / f"bad{index}.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr(name, b"{}")
            with self.assertRaises(ModError):
                read_files(archive)
        archive = self.root / "collision.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("manifest.json", b"{}")
            z.writestr("MANIFEST.JSON", b"{}")
        with self.assertRaisesRegex(ModError, "case-colliding"):
            read_files(archive)
        archive = self.root / "link.zip"
        with zipfile.ZipFile(archive, "w") as z:
            entry = zipfile.ZipInfo("link")
            entry.create_system = 3
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(entry, "../outside")
        with self.assertRaisesRegex(ModError, "symlink"):
            read_files(archive)
        archive = self.root / "big.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("big", b"x" * (8 * 1024 * 1024 + 1))
        with self.assertRaisesRegex(ModError, "byte limit"):
            read_files(archive)

    def test_exact_case_nonfinite_duplicate_json_and_invalid_mesh(self):
        directory = self.authored()
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["resources"][0]["path"] = "Body.json"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ModError, "exact-case"):
            load_package(directory)
        manifest["resources"][0]["path"] = "body.json"
        manifest_path.write_text(json.dumps(manifest))
        for body, expected in [('{"schema_version":1,"label":"a","label":"b"}', "duplicate JSON"),
                               ('{"schema_version":1,"label":"a","metadata":{"x":1e999}}', "nonfinite"),
                               ('{"schema_version":1,"label":"a","metadata":{"x":NaN}}', "nonfinite")]:
            (directory / "body.json").write_text(body)
            with self.assertRaisesRegex(ModError, expected):
                load_package(directory)
        data = {"schema_version": 1, "label": "a", "mesh": {"vertices": [[0,0,0],[1,0,0],[0,0,1]], "triangles": [[0,1,[]]]}}
        (directory / "body.json").write_text(json.dumps(data))
        with self.assertRaisesRegex(ModError, "triangle indices"):
            load_package(directory)

    def test_reference_dependency_and_html_escaping(self):
        directory = self.authored()
        data = {"schema_version": 1, "label": "<script>unsafe</script>", "references": ["other.mod:paint"]}
        (directory / "body.json").write_text(json.dumps(data))
        package = load_package(directory)
        with self.assertRaisesRegex(ModError, "missing resource reference"):
            build_registry([package])
        data["references"] = []
        (directory / "body.json").write_text(json.dumps(data))
        _, registry = build_registry([load_package(directory)])
        self.assertNotIn("<script>", preview_svg(registry["test.base:body"]))

    def test_directory_symlink_and_zip_parent_collisions(self):
        directory = self.authored()
        try:
            (directory / "linked.json").symlink_to(directory / "body.json")
        except (OSError, NotImplementedError):
            pass  # Windows without symlink privilege; ZIP symlink case is unconditional.
        else:
            with self.assertRaisesRegex(ModError, "symlink"):
                read_files(directory)
        for index, names in enumerate((("Folder/a", "folder/b"), ("node", "node/child"))):
            archive = self.root / f"parent{index}.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("manifest.json", "{}")
                for name in names:
                    z.writestr(name, "{}")
            with self.assertRaisesRegex(ModError, "collision|colliding"):
                read_files(archive)

    def test_undeclared_cross_package_reference_and_wrong_replacement_kind(self):
        base_path = self.authored()
        other_path = self.authored("test.other")
        (other_path / "body.json").write_text(json.dumps({"schema_version": 1, "label": "Other", "references": ["test.base:body"]}))
        with self.assertRaisesRegex(ModError, "declared direct dependency"):
            build_registry([load_package(base_path), load_package(other_path)])
        replacement_path = self.authored("test.replacement", {"test.base": "1.0.0"}, "test.base:body")
        manifest_path = replacement_path / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["resources"][0]["kind"] = "component"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ModError, "replacement kind differs"):
            build_registry([load_package(base_path), load_package(replacement_path)])

    def test_schema_unknown_fields_and_nested_metadata(self):
        directory = self.authored()
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["api_version"] = "future"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ModError, "unsupported api_version"):
            load_package(directory)
        manifest["api_version"] = "data-alpha-1"
        manifest["unknown"] = True
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ModError, "unknown fields"):
            load_package(directory)
        del manifest["unknown"]
        manifest_path.write_text(json.dumps(manifest))
        metadata = {}
        for _ in range(70):
            metadata = {"nested": metadata}
        (directory / "body.json").write_text(json.dumps({"schema_version": 1, "label": "Nested", "metadata": metadata}))
        with self.assertRaisesRegex(ModError, "nesting exceeds"):
            load_package(directory)

    def test_archive_atomic_failure_leaves_no_output_or_temporary(self):
        output = self.root / "failure.zip"
        with patch("client.mod_registry.os.link", side_effect=OSError("cannot publish")):
            with self.assertRaisesRegex(OSError, "cannot publish"):
                package_archive(load_package(EXAMPLE), output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.iterdir()), [])
        with patch("client.mod_registry.zipfile.ZipFile.writestr", side_effect=OSError("write failed")):
            with self.assertRaisesRegex(OSError, "write failed"):
                package_archive(load_package(EXAMPLE), output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_zip_ratio_bound(self):
        archive = self.root / "ratio.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("repetitive", b"x" * (4 * 1024 * 1024))
        with self.assertRaisesRegex(ModError, "expansion ratio"):
            read_files(archive)

    def test_replacement_cannot_hide_invalid_base_reference(self):
        base_path = self.authored()
        (base_path / "body.json").write_text(json.dumps({"schema_version": 1, "label": "Base", "references": ["missing.mod:entry"]}))
        replacement_path = self.authored("test.replacement", {"test.base": "1.0.0"}, "test.base:body")
        with self.assertRaisesRegex(ModError, "missing resource reference"):
            build_registry([load_package(base_path), load_package(replacement_path)])


if __name__ == "__main__":
    unittest.main()
