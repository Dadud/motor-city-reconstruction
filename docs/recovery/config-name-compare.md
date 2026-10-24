# Configuration-name comparison

`0x6aa840` compares the section and key names used by `0x409b60`, the
configuration lookup routine. Its default mode compares NUL-terminated bytes
after a wrapped ASCII case fold and returns the sign of the first differing
folded byte. The byte transform was ported directly, including its behavior on
high-bit values.

Python and C++ agree over 512 deterministic cases. The Python port also matched
1,024 direct executions of the installed original with the binary's locale
mode flag set to its observed default value of zero. Inputs included high-bit
bytes and names up to 299 bytes.

When the global locale-mode flag is nonzero, the binary delegates case
conversion to CRT locale helpers and enters additional shared lock/state
handling. That branch is not represented by this port. The primary evidence is
Ghidra analysis `ev_91c327c017e00626be20f24dbfed8419cc9ec288951e040126366df943f3974a`.
Its use by configuration lookup and file loading is visible in
`ev_57e7b0d4f6f6f282320cbdb4d42ab6ca2063df541aa0a5964e5d55cdf7552b1f` and
`ev_337162f0381b81e0b2e8c99085eef7cadfb832dbe1ca45630b4087076c11d666`.
