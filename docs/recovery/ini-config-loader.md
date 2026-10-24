# INI-style configuration loader

`0x409d00` resets several process-global arrays, records the selected path,
opens the file through `CreateFileA`, reads its bytes, and builds parallel
ordered tables of section names, keys and values. `0x409b60` reloads when the
requested path differs, then searches the first matching section and first
matching key with `0x6aa840`. A found value is shortened in place when its
length exceeds the caller's `param_5`, copied to the caller's output with
`lstrcpyA`, and reported as found.

`client.ini_config.IniConfig` reconstructs the byte parsing and lookup core:

- LF separates lines; the byte immediately before LF is removed, which strips
  CR from CRLF input. A final unterminated line is retained.
- A line containing `=` is treated as a key/value line. It splits at the first
  delimiter, skips leading `=` delimiters as the original tokenizer does, does
  not trim whitespace, and discards entries with no value token.
- Other lines containing both `[` and `]` create a section from the first
  token separated by either bracket. Duplicate sections and entries retain
  source order.
- Lookup is ASCII case-insensitive in the observed default locale mode and
  stops at the first matching section. A successful bounded read truncates the
  stored value in place, affecting later lookups.

The parser core has 6 focused behavior tests. Its interpretation is derived
from the observed decompilation, not directly compared with an original parser
call. File handles, Win32 error returns, allocation, global array growth,
exception cleanup, path-triggered reload, root-level keys, and exact shared
string/vector object layouts remain open. The 512-byte local line buffer is
bounded to lines of at most 511 bytes; the original performs unchecked copies
for longer lines.

Primary analysis evidence: loader `ev_337162f0381b81e0b2e8c99085eef7cadfb832dbe1ca45630b4087076c11d666`,
lookup `ev_57e7b0d4f6f6f282320cbdb4d42ab6ca2063df541aa0a5964e5d55cdf7552b1f`,
default name comparator `ev_91c327c017e00626be20f24dbfed8419cc9ec288951e040126366df943f3974a`,
and destructive token scanner `ev_9a1600aa15c91c9d3ddfd693d338de812a2851f5a0c252eb62077563b9aa20cf`.
