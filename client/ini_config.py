"""Byte-oriented model of MCO's section/key configuration loader."""

from dataclasses import dataclass, field

from .string_compare import compare_config_names


@dataclass
class ConfigEntry:
    key: bytes
    value: bytearray


@dataclass
class ConfigSection:
    name: bytes
    entries: list[ConfigEntry] = field(default_factory=list)


@dataclass
class IniConfig:
    """Parsed ordered sections and entries; values retain lookup truncation."""

    sections: list[ConfigSection] = field(default_factory=list)
    root_entries: list[ConfigEntry] = field(default_factory=list)

    @classmethod
    def from_bytes(cls, data):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError('configuration file bytes required')
        raw = bytes(data).split(b'\0', 1)[0]
        result = cls()
        current = None
        cursor = 0
        while True:
            newline = raw.find(b'\n', cursor)
            if newline < 0:
                line_end = len(raw)
                next_cursor = len(raw)
                final = True
            else:
                # 0x409d00 subtracts one byte from the LF location to drop CR.
                if newline == cursor:
                    raise ValueError('empty LF-only line is outside the mapped parser domain')
                line_end = newline - 1
                next_cursor = newline + 1
                final = False
            line = raw[cursor:line_end]
            if len(line) > 511:
                raise ValueError('line exceeds the original 512-byte local buffer')
            current = _parse_line(line, result.sections, current, result.root_entries)
            if final:
                break
            cursor = next_cursor
        return result

    def lookup(self, section, key, maximum_bytes):
        """Return (found, value), applying 0x409b60's in-place truncation.

        Section and key inputs are NUL-terminated bytes, as at the original
        function boundary. A zero maximum truncates a found nonempty value to
        empty; this mirrors the strict comparison and subsequent length update.
        """
        if not isinstance(section, (bytes, bytearray, memoryview)) or not isinstance(
                key, (bytes, bytearray, memoryview)):
            raise TypeError('section and key names must be byte strings')
        section, key = bytes(section), bytes(key)
        if b'\0' not in section or b'\0' not in key:
            raise ValueError('NUL-terminated section and key names required')
        if type(maximum_bytes) is not int or not 0 <= maximum_bytes <= 0xffffffff:
            raise ValueError('maximum byte count must be uint32')

        for candidate in self.sections:
            if compare_config_names(candidate.name + b'\0', section) != 0:
                continue
            for entry in candidate.entries:
                if compare_config_names(entry.key + b'\0', key) == 0:
                    if maximum_bytes < len(entry.value):
                        del entry.value[maximum_bytes:]
                    return True, bytes(entry.value)
            return False, b''
        return False, b''


def _first_token(text, delimiters):
    position = 0
    while position < len(text) and text[position] in delimiters:
        position += 1
    if position == len(text):
        return None
    end = position
    while end < len(text) and text[end] not in delimiters:
        end += 1
    return text[position:end]


def _parse_line(line, sections, current, root_entries):
    equal = line.find(b'=')
    if equal >= 0:
        # FUN_0069a3d5 behaves like strtok: leading delimiters are skipped,
        # the first token is appended as a key, and the next token is the value.
        key = _first_token(line, b'=')
        if key is None:
            return current
        delimiter = line.find(b'=', line.find(key) + len(key))
        if delimiter < 0:
            return current
        value = _first_token(line[delimiter + 1:], b'\n')
        if value is None:
            # The original removes the just-added key when no value token exists.
            return current
        entry = ConfigEntry(key, bytearray(value))
        (current.entries if current is not None else root_entries).append(entry)
        return current

    if b'[' not in line or b']' not in line:
        return current
    name = _first_token(line, b'[]')
    if name is None:
        return current
    current = ConfigSection(name)
    sections.append(current)
    return current
