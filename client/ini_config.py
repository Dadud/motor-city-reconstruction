"""Byte-oriented model of MCO's section/key configuration tables."""

from dataclasses import dataclass, field

from .string_compare import compare_config_names


@dataclass
class IniConfig:
    """Parallel string vectors plus per-section start/count vectors.

    The original keeps section names, flat keys, and flat values in separate
    vectors. ``section_key_starts`` and ``section_key_counts`` index the flat
    key/value vectors; lookups retain source order and truncate stored values.
    """

    section_names: list[bytes] = field(default_factory=list)
    section_key_starts: list[int] = field(default_factory=list)
    section_key_counts: list[int] = field(default_factory=list)
    keys: list[bytes] = field(default_factory=list)
    values: list[bytearray] = field(default_factory=list)
    _pending_key_count: int = 0

    @classmethod
    def from_bytes(cls, data):
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError('configuration file bytes required')
        raw = bytes(data).split(b'\0', 1)[0]
        result = cls()
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
            result._parse_line(line)
            if final:
                break
            cursor = next_cursor
        # 0x409d00 publishes the final section's key count after line scanning.
        if result.section_names:
            result.section_key_counts.append(result._pending_key_count)
        return result

    def _parse_line(self, line):
        equal = line.find(b'=')
        if equal >= 0:
            # FUN_0069a3d5 behaves like strtok: leading delimiters are skipped,
            # the first token is a key, and the continuation token is its value.
            key = _first_token(line, b'=')
            if key is None:
                return
            delimiter = line.find(b'=', line.find(key) + len(key))
            if delimiter < 0:
                return
            value = _first_token(line[delimiter + 1:], b'\n')
            if value is None:
                # The original removes the just-appended key if no value exists.
                return
            self.keys.append(key)
            self.values.append(bytearray(value))
            self._pending_key_count += 1
            return

        if b'[' not in line or b']' not in line:
            return
        name = _first_token(line, b'[]')
        if name is None:
            return
        # On subsequent section headers, publish the preceding group's count.
        if self.section_names:
            self.section_key_counts.append(self._pending_key_count)
            self._pending_key_count = 0
        self.section_names.append(name)
        self.section_key_starts.append(len(self.keys))

    def lookup(self, section, key, maximum_bytes):
        """Return (found, value), applying 0x409b60's in-place truncation.

        Section and key inputs are NUL-terminated bytes, as at the original
        function boundary. A zero maximum truncates a found nonempty value to
        empty; the mutation persists for later calls.
        """
        if not isinstance(section, (bytes, bytearray, memoryview)) or not isinstance(
                key, (bytes, bytearray, memoryview)):
            raise TypeError('section and key names must be byte strings')
        section, key = bytes(section), bytes(key)
        if b'\0' not in section or b'\0' not in key:
            raise ValueError('NUL-terminated section and key names required')
        if type(maximum_bytes) is not int or not 0 <= maximum_bytes <= 0xffffffff:
            raise ValueError('maximum byte count must be uint32')

        for section_index, name in enumerate(self.section_names):
            if compare_config_names(name + b'\0', section) != 0:
                continue
            if section_index >= len(self.section_key_counts):
                return False, b''
            start = self.section_key_starts[section_index]
            stop = min(start + self.section_key_counts[section_index], len(self.keys))
            for entry_index in range(start, stop):
                if compare_config_names(self.keys[entry_index] + b'\0', key) == 0:
                    value = self.values[entry_index]
                    if maximum_bytes < len(value):
                        del value[maximum_bytes:]
                    return True, bytes(value)
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
