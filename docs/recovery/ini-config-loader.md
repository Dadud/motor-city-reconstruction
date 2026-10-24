# INI-style configuration loader

`0x409d00` resets several process-global arrays, records the selected path,
opens the file through `CreateFileA`, reads its bytes, and builds parallel
ordered tables. Section names and keys/values are 16-byte string records;
keys and values occupy parallel flat vectors, while per-section start and
count vectors delimit each section's range. `0x409b60` reloads when the
requested path differs, then searches the first matching section and first
matching key with `0x6aa840`. A found value is shortened in place when its
length exceeds the caller's `param_5`, copied to the caller's output with
`lstrcpyA`, and reported as found.

The insertion helpers `0x4156a0` and `0x415950` operate on vectors whose
begin/end/capacity pointers are at offsets `+4/+8/+0xc`. String-vector growth
copies 16-byte records through `0x415c80`; dword-vector growth copies 4-byte
elements. Both growth paths reserve old size plus the larger of old size and
requested insertion count. `0x415100` assigns a string-record range and
`0x4153e0` copies a dword range. `0x415c80` releases the prior destination,
shares strings with a reference count below `0xfe`, and otherwise performs a
deep copy. These observations establish container mechanics, not allocator
failure behavior or the exact ownership semantics of every mutation path.

`client.ini_config.IniConfig` models the ordered table shape and reconstructs
the byte parsing and lookup core:

- LF separates lines; the byte immediately before LF is removed, which strips
  CR from CRLF input. A final unterminated line is retained.
- A line containing `=` is treated as a key/value line. It splits at the first
  delimiter, skips leading `=` delimiters as the original tokenizer does, does
  not trim whitespace, and discards entries with no value token.
- Other lines containing both `[` and `]` create a section from the first
  token separated by either bracket. Duplicate sections and entries retain
  source order.
- Lookup is ASCII case-insensitive in the observed default locale mode and
  stops at the first matching section. A successful bounded read truncates
  the stored value in place, affecting later lookups.
- Parsed sections, starts, counts, keys, and values are held in parallel
  vectors. The start/count vectors are published at section boundaries. Root
  keys remain in the flat key/value vectors; decompiler control flow suggests
  their count can carry into the first section count, but this edge case is
  only an inference and has not been checked against an original parser call.

The parser core has 7 focused behavior tests. Its interpretation is derived
from the observed decompilation, not directly compared with an original parser
call. File handles, Win32 error returns, allocation and exception cleanup,
path-triggered reload, exact shared-string ownership, and byte-for-byte vector
layouts remain open. The vector insertion and assignment mechanics have been
recovered statically, but the Python model does not reproduce allocator
capacity or pointer relocation. The 512-byte local line buffer is bounded to
lines of at most 511 bytes; the original performs unchecked copies for longer
lines.

Primary analysis evidence: loader `ev_337162f0381b81e0b2e8c99085eef7cadfb832dbe1ca45630b4087076c11d666`,
lookup `ev_57e7b0d4f6f6f282320cbdb4d42ab6ca2063df541aa0a5964e5d55cdf7552b1f`,
default name comparator `ev_91c327c017e00626be20f24dbfed8419cc9ec288951e040126366df943f3974a`,
destructive token scanner `ev_9a1600aa15c91c9d3ddfd693d338de812a2851f5a0c252eb62077563b9aa20cf`,
string-vector insertion `ev_a03dc18d607b14d2e8a67997de2870f3862824895cb5284991c751709c85ec36`,
and dword-vector insertion `ev_0618a2eb973e6f64b8e55fae8e7a6b77de335f1945187a22ee256bdd43508975`.
