"""Disk adapter for the native offline script-alpha-1 registry.

Manifest validation does not certify Lua behavior. Execution uses the existing
native sandbox with its memory and instruction budgets.
"""
from dataclasses import dataclass, field
import json
from pathlib import Path
import struct
import subprocess

from client.mod_registry import ID, KINDS, VERSION, ModError, read_files, require, safe_path


@dataclass(frozen=True)
class ScriptResource:
    id: str
    kind: str
    label: str


@dataclass(frozen=True)
class ModScriptPackage:
    id: str
    version: str
    license: str
    resources: tuple[ScriptResource, ...]
    source: str
    files: dict[str, bytes] = field(repr=False, compare=False)


def _text(value, label, limit):
    require(isinstance(value, str) and 1 <= len(value) <= limit
            and all(32 <= ord(c) <= 126 for c in value),
            f'{label}: requires 1..{limit} printable ASCII bytes')
    return value


def load_script_package(source):
    files = read_files(source)
    require('manifest.json' in files, 'script package requires manifest.json')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate manifest key: {key}')
            result[key] = value
        return result
    try:
        manifest = json.loads(files['manifest.json'].decode('utf-8'), object_pairs_hook=unique)
    except (UnicodeError, ValueError) as error:
        raise ModError('invalid script manifest JSON') from error
    require(isinstance(manifest, dict), 'script manifest must be an object')
    fields = {'schema_version', 'api_version', 'id', 'version', 'license', 'resources', 'script'}
    require(set(manifest) == fields, 'script manifest requires exactly: ' + ', '.join(sorted(fields)))
    require(type(manifest['schema_version']) is int and manifest['schema_version'] == 1,
            'unsupported script schema_version')
    require(manifest['api_version'] == 'script-alpha-1', 'unsupported script API')
    pid = _text(manifest['id'], 'package id', 80)
    require(ID.fullmatch(pid), 'invalid package id')
    version = _text(manifest['version'], 'version', 64)
    require(VERSION.fullmatch(version), 'invalid exact version')
    license = _text(manifest['license'], 'license', 1024)
    definitions = manifest['resources']
    require(isinstance(definitions, list) and len(definitions) <= 256,
            'resources must be an array of at most 256 entries')
    resources, seen = [], set()
    for entry in definitions:
        require(isinstance(entry, dict) and set(entry) == {'id', 'kind', 'label'},
                'script resource requires exactly id, kind, label')
        rid = entry['id']
        require(isinstance(rid, str) and rid.startswith(pid + ':'), 'resource must use package namespace')
        suffix = rid[len(pid) + 1:]
        require(len(suffix) <= 80 and ID.fullmatch(suffix), 'invalid resource suffix')
        require(rid not in seen, 'duplicate resource id: ' + rid)
        require(isinstance(entry['kind'], str) and entry['kind'] in KINDS, 'unsupported resource kind')
        resources.append(ScriptResource(rid, entry['kind'], _text(entry['label'], 'label', 1024)))
        seen.add(rid)
    script = safe_path(manifest['script'])
    require(script in files, 'missing script file: ' + script)
    raw = files[script]
    require(len(raw) <= 1024 * 1024, 'Lua source exceeds 1 MiB')
    try:
        lua = raw.decode('utf-8')
    except UnicodeError as error:
        raise ModError('Lua source must be UTF-8') from error
    return ModScriptPackage(pid, version, license, tuple(resources), lua, files)


def summarize_script_package(package):
    return {'api_version': 'script-alpha-1', 'id': package.id, 'version': package.version,
            'license': package.license, 'resource_count': len(package.resources),
            'source_bytes': len(package.source.encode('utf-8')),
            'supported_events': ['inspect', 'preview']}


def run_script_package(package, runner, *, event='inspect'):
    """Send bounded package content to a native child; never use a shell.

    This private length-prefixed bridge is not a game or server protocol.
    Native execution always selects offline mode.
    """
    require(event in {'inspect', 'preview'}, 'unsupported script event')
    def field(value):
        raw = value.encode('utf-8')
        return struct.pack('<I', len(raw)) + raw
    payload = b'MCOS1' + field(package.id) + field(package.version)
    payload += struct.pack('<I', len(package.resources))
    for resource in package.resources:
        payload += field(resource.id) + field(resource.kind) + field(resource.label)
    payload += field(package.source)
    try:
        result = subprocess.run([str(Path(runner).resolve()), event], input=payload,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ModError('native script runner unavailable or timed out') from error
    try:
        output = json.loads(result.stdout)
    except (UnicodeError, ValueError) as error:
        raise ModError('native script runner returned invalid output') from error
    require(isinstance(output, dict) and type(output.get('success')) is bool,
            'invalid native script result')
    require(result.returncode == 0 and output['success'],
            'script execution failed: ' + str(output.get('error', 'unknown failure')))
    return output
