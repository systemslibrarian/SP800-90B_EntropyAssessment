#!/usr/bin/env python3
"""Fixtures for the ea_conditioning width-inference recheck (audit 2026-10-11).

low7.bin   1,000,000 bytes, MSB always 0  -> ea_conditioning infers width 7
msbset.bin 1,000,000 bytes, identical low 7 bits, MSB always 1 -> infers width 8

Both files carry exactly the same information: seven pseudorandom bits per byte
plus one constant bit. Any correct per-output-bit entropy rate must be the same
for both, and h_out must not exceed 7 bits for either.

sha256 low7.bin   92e3e6060a67db94e0c8c887a8c11ed3def08ac15c661ea06dee56cfeaf3d014
sha256 msbset.bin 9f437ffa7628d4817a187585e75af62d6aaa78428cf380d0a16878bf03ee4561
"""
import hashlib, sys
TAG = b'orchestrator-ct2-recheck-2026-10-12'
N = 1000000
buf = bytearray(); i = 0
while len(buf) < N:
    buf += hashlib.sha256(TAG + i.to_bytes(8, 'big')).digest(); i += 1
buf = bytes(buf[:N])
low7 = bytes(b & 0x7F for b in buf)
msbset = bytes(b | 0x80 for b in low7)
out = sys.argv[1] if len(sys.argv) > 1 else '.'
for name, d in (('low7.bin', low7), ('msbset.bin', msbset)):
    open(f'{out}/{name}', 'wb').write(d)
    print(name, len(d), hashlib.sha256(d).hexdigest())
