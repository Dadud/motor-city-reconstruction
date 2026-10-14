"""Portable alpha data package boundary. No original game or script execution."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILES = 512
MAX_ARCHIVE = MAX_TOTAL + 1024 * 1024
MAX_RATIO = 1000
KINDS = {"vehicle", "component", "track", "material", "sound", "ui"}
ID = re.compile(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*\Z")
VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")


class ModError(ValueError):
    """Actionable package validation failure."""


def require(condition, message):
    if not condition:
        raise ModError(message)


def safe_path(name):
    require(isinstance(name, str) and name, "path must be a nonempty string")
    require(not any(0xD800 <= ord(c) <= 0xDFFF for c in name), "package path contains invalid Unicode surrogate")
    path = PurePosixPath(name)
    require(len(name.encode("utf-8")) <= 1024 and all(len(p.encode("utf-8")) <= 255 for p in path.parts),
            "package paths must fit 1024 UTF-8 bytes with segments at most 255 bytes")
    require(not path.is_absolute() and "\\" not in name and ":" not in name
            and all(p not in {"", ".", ".."} for p in name.split("/")),
            f"unsafe package path: {name!r}; use relative forward-slash paths")
    require(all(not p.endswith((".", " ")) and not any(ord(c) < 32 for c in p)
                and not any(c in '<>"|?*' for c in p)
                and p.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
                for p in path.parts), f"nonportable package path: {name!r}")
    return name


def read_files(source):
    """Read bounded files without extracting an archive or following symlinks."""
    source = Path(source)
    def junction(path):
        # Python 3.11 lacks Path.is_junction; Windows exposes reparse attributes.
        try:
            return bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
        except OSError:
            return False

    def bounded_read(opener):
        with opener() as stream:
            return stream.read(MAX_FILE + 1)

    require(not source.is_symlink() and not junction(source), f"package source is a symlink/junction: {source}")
    files = {}
    folded = set()
    total = 0

    def add(name, size, read):
        nonlocal total
        safe_path(name)
        require(name.casefold() not in folded, f"duplicate or case-colliding package path: {name}")
        require(len(files) < MAX_FILES, f"package exceeds {MAX_FILES} files")
        require(0 <= size <= MAX_FILE, f"{name}: exceeds {MAX_FILE} byte limit")
        total += size
        require(total <= MAX_TOTAL, f"package exceeds {MAX_TOTAL} total bytes")
        data = read()
        require(len(data) == size, f"{name}: changed while reading")
        files[name] = data
        folded.add(name.casefold())

    try:
        if source.is_dir():
            # rglob does not traverse symlink directories; reject them explicitly.
            entry_count = 0
            for path in source.rglob("*"):
                entry_count += 1
                require(entry_count <= MAX_FILES, f"directory exceeds {MAX_FILES} entries including directories")
                require(not path.is_symlink() and not junction(path), f"symlink/junction forbidden: {path}")
                if path.is_file():
                    require(stat.S_ISREG(path.stat().st_mode), f"not a regular file: {path}")
                    add(path.relative_to(source).as_posix(), path.stat().st_size,
                        lambda p=path: bounded_read(lambda: p.open("rb")))
                else:
                    require(path.is_dir(), f"unsupported package entry: {path}")
        else:
            require(stat.S_ISREG(source.stat().st_mode), f"package archive is not a regular file: {source}")
            require(source.stat().st_size <= MAX_ARCHIVE, f"archive exceeds {MAX_ARCHIVE} compressed bytes")
            with zipfile.ZipFile(source) as archive:
                require(len(archive.infolist()) <= MAX_FILES, f"archive exceeds {MAX_FILES} entries")
                for entry in archive.infolist():
                    mode = entry.external_attr >> 16
                    require(not stat.S_ISLNK(mode), f"archive symlink forbidden: {entry.filename}")
                    require(not (entry.flag_bits & 1), f"encrypted entry forbidden: {entry.filename}")
                    if entry.is_dir():
                        safe_path(entry.filename.rstrip("/"))
                        continue
                    require(stat.S_IFMT(mode) in {0, stat.S_IFREG}, f"nonregular archive entry: {entry.filename}")
                    require(entry.file_size <= MAX_FILE, f"{entry.filename}: exceeds {MAX_FILE} byte limit")
                    require(entry.file_size <= max(entry.compress_size, 1) * MAX_RATIO,
                            f"{entry.filename}: ZIP expansion ratio exceeds {MAX_RATIO}:1")
                    add(entry.filename, entry.file_size,
                        lambda e=entry: bounded_read(lambda: archive.open(e)))
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise ModError(f"cannot read package {source}: {exc}") from exc
    require("manifest.json" in files, "missing exact-case manifest.json at package root")
    # Also reject case collisions in parent segments and file/directory aliases.
    segments = {}
    for name in files:
        parts = name.split("/")
        for i in range(1, len(parts) + 1):
            segment = "/".join(parts[:i])
            folded_segment = segment.casefold()
            require(folded_segment not in segments or segments[folded_segment] == segment,
                    f"case-colliding parent path: {segment}")
            segments[folded_segment] = segment
            if i < len(parts):
                require(folded_segment not in folded, f"file/directory collision: {segment}")
    return files


def decode(data, label):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"{label}: duplicate JSON key {key}")
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_constant=lambda x: (_ for _ in ()).throw(ModError(f"{label}: nonfinite number {x}")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ModError(f"{label}: invalid UTF-8 JSON: {exc}") from exc
    except ValueError as exc:
        if isinstance(exc, ModError):
            raise
        raise ModError(f"{label}: invalid JSON number: {exc}") from exc


def fields(value, required, optional, label):
    require(isinstance(value, dict), f"{label}: expected object")
    require(set(required) <= value.keys(), f"{label}: missing fields {sorted(set(required) - value.keys())}")
    require(value.keys() <= set(required) | set(optional), f"{label}: unknown fields {sorted(value.keys() - set(required) - set(optional))}")


def text(value, label):
    require(isinstance(value, str) and 0 < len(value) <= 1024, f"{label}: expected nonempty text (maximum 1024 characters)")
    require(all((ord(c) >= 32 or c in "\t\n\r") and not 0xD800 <= ord(c) <= 0xDFFF and ord(c) not in {0xFFFE, 0xFFFF} for c in value),
            f"{label}: invalid control or Unicode character")


def ident(value, label):
    require(isinstance(value, str) and ID.fullmatch(value) and len(value) <= 80, f"{label}: use a lowercase ID such as example.garage")


def version(value, label):
    require(isinstance(value, str) and VERSION.fullmatch(value), f"{label}: expected exact major.minor.patch version")


def resource_id(value):
    require(isinstance(value, str) and value.count(":") == 1, f"resource ID {value!r}: expected package:name")
    for part in value.split(":"):
        ident(part, "resource ID")


def finite_tree(value, label, depth=0):
    require(depth <= 64, f"{label}: JSON nesting exceeds 64 levels")
    if isinstance(value, float):
        require(math.isfinite(value), f"{label}: nonfinite number")
    elif isinstance(value, dict):
        for child in value.values():
            finite_tree(child, label, depth + 1)
    elif isinstance(value, list):
        for child in value:
            finite_tree(child, label, depth + 1)


def validate_data(data, kind, label):
    fields(data, {"schema_version", "label"}, {"mesh", "color", "metadata", "references"}, label)
    require(type(data["schema_version"]) is int and data["schema_version"] == 1, f"{label}: resource schema_version must be 1")
    text(data["label"], label + " label")
    finite_tree(data, label)
    if "metadata" in data:
        require(isinstance(data["metadata"], dict), f"{label}: metadata must be an object; it has no runtime semantics")
    references = data.get("references", [])
    require(isinstance(references, list), f"{label}: references must be a list")
    for ref in references:
        resource_id(ref)
    if "color" in data:
        require(isinstance(data["color"], str) and re.fullmatch(r"#[0-9a-fA-F]{6}", data["color"]), f"{label}: color must be #RRGGBB")
    if "mesh" in data:
        require(kind in {"vehicle", "track"}, f"{label}: mesh only supported for vehicle/track")
        mesh = data["mesh"]
        fields(mesh, {"vertices", "triangles"}, set(), label + " mesh")
        vertices, triangles = mesh["vertices"], mesh["triangles"]
        require(isinstance(vertices, list) and 3 <= len(vertices) <= 10000, f"{label}: mesh requires 3..10000 vertices")
        for vertex in vertices:
            require(isinstance(vertex, list) and len(vertex) == 3 and all(type(x) in {int, float} and abs(x) <= 100000 and math.isfinite(x) for x in vertex), f"{label}: vertices require three finite coordinates within +/-100000 author units")
        require(isinstance(triangles, list) and 1 <= len(triangles) <= 20000, f"{label}: mesh requires 1..20000 triangles")
        for triangle in triangles:
            require(isinstance(triangle, list) and len(triangle) == 3 and all(type(x) is int and 0 <= x < len(vertices) for x in triangle) and len(set(triangle)) == 3, f"{label}: triangle indices must be three distinct valid vertex indices")
    return data


@dataclass(frozen=True)
class Package:
    manifest: dict
    files: dict[str, bytes]
    resources: dict[str, dict]
    digest: str

    @property
    def id(self):
        return self.manifest["id"]


def load_package(source):
    files = read_files(source)
    manifest = decode(files["manifest.json"], "manifest.json")
    fields(manifest, {"schema_version", "api_version", "id", "version", "license", "author", "dependencies", "resources"}, set(), "manifest")
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1, "unsupported manifest schema_version; supported: 1")
    require(manifest["api_version"] == "data-alpha-1", "unsupported api_version; supported: data-alpha-1")
    ident(manifest["id"], "package id")
    version(manifest["version"], "package version")
    text(manifest["license"], "license declaration")
    text(manifest["author"], "author")
    dependencies = manifest["dependencies"]
    require(isinstance(dependencies, dict), "dependencies must map package IDs to exact versions")
    for key, value in dependencies.items():
        ident(key, "dependency ID")
        version(value, f"dependency {key} version")
        require(key != manifest["id"], f"{key}: cannot depend on itself")
    declarations = manifest["resources"]
    require(isinstance(declarations, list) and len(declarations) <= 256, "resources must be a list of at most 256 declarations")
    resources = {}
    for declaration in declarations:
        fields(declaration, {"id", "kind", "path"}, {"replaces"}, "resource declaration")
        rid = declaration["id"]
        resource_id(rid)
        require(rid.startswith(manifest["id"] + ":"), f"{rid}: resource must belong to namespace {manifest['id']}")
        require(rid not in resources, f"duplicate resource ID: {rid}")
        require(isinstance(declaration["kind"], str) and declaration["kind"] in KINDS, f"{rid}: unsupported kind; supported: {sorted(KINDS)}")
        path = safe_path(declaration["path"])
        require(path in files, f"{rid}: missing exact-case resource path {path}")
        if "replaces" in declaration:
            replacement = declaration["replaces"]
            fields(replacement, {"id", "version"}, set(), f"{rid} replaces")
            resource_id(replacement["id"])
            version(replacement["version"], f"{rid} replacement version")
            target_package = replacement["id"].split(":")[0]
            require(dependencies.get(target_package) == replacement["version"], f"{rid}: replacement needs exact dependency {target_package} {replacement['version']}")
        resources[rid] = validate_data(decode(files[path], path), declaration["kind"], rid)
    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode() + b"\0" + len(data).to_bytes(8, "big") + data)
    return Package(manifest, files, resources, digest.hexdigest())


@dataclass(frozen=True)
class Resource:
    id: str
    kind: str
    provider: str
    data: dict


def build_registry(packages):
    """Topological package order and explicit single-writer replacement overlay."""
    by_id = {}
    for package in packages:
        require(package.id not in by_id, f"duplicate package ID: {package.id}; select one version")
        by_id[package.id] = package
    ordered, active, done = [], [], set()

    def visit(pid):
        require(pid not in active, "dependency cycle: " + " -> ".join(active + [pid]))
        if pid in done:
            return
        active.append(pid)
        package = by_id[pid]
        for dep, expected in sorted(package.manifest["dependencies"].items()):
            require(dep in by_id, f"{pid}: missing dependency {dep} {expected}; supply that package")
            require(by_id[dep].manifest["version"] == expected, f"{pid}: dependency {dep} requires {expected}, found {by_id[dep].manifest['version']}")
            visit(dep)
        active.pop()
        done.add(pid)
        ordered.append(package)

    for pid in sorted(by_id):
        visit(pid)
    registry, replaced = {}, {}
    for package in ordered:
        for declaration in package.manifest["resources"]:
            rid = declaration["id"]
            item = Resource(rid, declaration["kind"], package.id, package.resources[rid])
            registry[rid] = item
            if "replaces" in declaration:
                target = declaration["replaces"]["id"]
                require(target in registry, f"{rid}: replacement target {target} does not exist")
                require(target not in replaced, f"replacement conflict for {target}: {replaced.get(target)} and {rid}; remove one replacement")
                require(registry[target].kind == item.kind, f"{rid}: replacement kind differs from {target}")
                replaced[target] = rid
                registry[target] = item
    # Validate every declaration, including an original hidden by a replacement.
    for package in ordered:
        for rid, data in package.resources.items():
            for reference in data.get("references", []):
                require(reference in registry, f"{rid}: missing resource reference {reference}")
                owner = reference.split(":")[0]
                require(owner == package.id or owner in package.manifest["dependencies"], f"{rid}: reference {reference} requires declared direct dependency {owner}")
    return ordered, dict(sorted(registry.items()))


def package_archive(package, output):
    """Reproducible ZIP with original authored bytes; refuses existing outputs."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"archive output already exists: {output}")
    descriptor, temporary = tempfile.mkstemp(prefix=".modkit-", suffix=".zip", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(package.files.items()):
                    entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    entry.create_system = 3
                    entry.external_attr = (stat.S_IFREG | 0o644) << 16
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(entry, data)
            stream.flush()
            os.fsync(stream.fileno())
        # An atomic no-replace hard link prevents a check/write race on both OSes.
        # Failure (including filesystems without hard links) leaves output absent.
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
