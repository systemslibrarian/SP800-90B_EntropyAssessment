#!/usr/bin/env python3
"""gen_inputs.py -- deterministic generated inputs for the sanitizer phase.

Writes, into <out>/ (default: <san-dir>/inputs, see run.sh):

  random-source-1MiB.bin             1 MiB keystream.  Pointed at by EA_TEST_RANDOM_SOURCE.
                                     NOTE (measured by reading cpp/, 2026-11-07): that variable
                                     reaches ONLY shared/TestRunUtils.h:129/478, the 8-byte read
                                     that names the temporary file beside a -o JSON report.  The
                                     permutation-test seed in shared/utils.h:794-811 opens
                                     "/dev/urandom" unconditionally, so ea_iid's battery is NOT
                                     made reproducible by this file; only the -o path is.
  restart-1bit-1000x1000.bin         1,000 restarts x 1,000 samples, one bit per byte (0/1),
                                     keystream bits MSB-first.  Row-dataset layout (3.1.4.1).
  restart-8bit-1000x1000.bin         1,000 x 1,000 keystream bytes.
  iid-lag32copy-q030-1bit-50000.bin  1-bit, x[i] = x[i-32] with probability 0.30, else a fresh
                                     keystream bit.  MEASURED at n = 20,000 on the production
                                     ea_iid (logs/sanitizers-calibration-ea_iid-cand-c6-lag32copy-1bit.log):
                                     chi-square and LRS pass, the permutation battery runs the
                                     full 10,000 rounds and fails -- the only known input that
                                     keeps every thread inside permutation_tests.h's parallel
                                     region for the whole battery.  The first 20,000 symbols of
                                     this file are that probe's file (index-keyed keystream).

All randomness is SHA-256 in counter mode under a fixed key, the same convention as
harness/gen_corpus.py (key || label || 8-byte big-endian block counter), so the bytes do not
depend on any library version.  Files are written whole and hashed FROM DISK; the recorded
sha256 is of the bytes on disk (guide rule 17).  EXPECTED holds the sha256 each file had when
this script was first run (2026-11-07); a mismatch is a refusal (exit 2), because a changed
generator would silently change what every later log was measured against.

Also computed, for the restart matrices: X_max over rows and over columns (the 3.1.4.3
statistic), so the orchestrator can compare with the X_cutoff the tool prints at -v and know
whether the sanity check will pass (if it fails, the estimators are never exercised).

Usage: gen_inputs.py [--out DIR] [--check]
Writes <out>/INPUTS.txt with one labelled `key=value ...` line per file.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
import time

KEY = b"sanitizers-2026-11-07/"

# sha256 of each generated file, recorded on first generation (2026-11-07, this host).
# hashlib is platform-independent; a mismatch means THIS SCRIPT changed, not the platform.
EXPECTED = {
    "random-source-1MiB.bin": "086ffa536e219367d6d24bdb65276f387defca619590acb93674db149d190ce8",
    "restart-1bit-1000x1000.bin": "d11f7dbe2a62b83c7697138a4b96d46f31566958fa75ee15ae0708ba0cb549b0",
    "restart-8bit-1000x1000.bin": "c1cd45a57ea9d72a43316ea022c6329922a1fcdf2b81c2410033f172bfda88d0",
    "iid-lag32copy-q030-1bit-50000.bin": "b7e5528391e691cbf37dd39562b7fae450b4403df58d228f05b550764afc5b45",
}

# Recommended H_I per restart matrix (why: see README.md "stage e").  For 1-bit a bare number is
# accepted; wider symbols must state the scale (C16 repair).
RESTART_HI = {
    "restart-1bit-1000x1000.bin": "0.9",
    "restart-8bit-1000x1000.bin": "7.0/symbol",
}


def keystream(label: str, nbytes: int) -> bytes:
    key = KEY + label.encode("ascii")
    nblocks = (nbytes + 31) // 32
    out = bytearray(nblocks * 32)
    for i in range(nblocks):
        out[i * 32:(i + 1) * 32] = hashlib.sha256(key + struct.pack(">Q", i)).digest()
    return bytes(out[:nbytes])


def keystream_bits(label: str, nbits: int) -> bytes:
    """One bit per byte, MSB-first within each keystream byte."""
    raw = keystream(label, (nbits + 7) // 8)
    out = bytearray(nbits)
    for i in range(nbits):
        out[i] = (raw[i >> 3] >> (7 - (i & 7))) & 1
    return bytes(out)


def unit(label: str, n: int):
    """n floats in [0, 1), 4 keystream bytes each (index-keyed, so prefixes are stable)."""
    raw = keystream(label, 4 * n)
    return [int.from_bytes(raw[4 * k:4 * k + 4], "big") / 2 ** 32 for k in range(n)]


def lag32copy_1bit(n: int, q: float = 0.30, lag: int = 32) -> bytes:
    # Labels "c6"/"c6fresh" are the calibration probe's labels on purpose: the 50,000-sample
    # file's first 20,000 symbols are byte-identical to the measured 20,000-sample probe.
    u = unit("c6", n)
    fresh = keystream("c6fresh", n)
    out = bytearray(n)
    for i in range(n):
        out[i] = out[i - lag] if (i >= lag and u[i] < q) else (fresh[i] & 1)
    return bytes(out)


def restart_xmax(data: bytes, r: int = 1000, c: int = 1000):
    """X_max over rows and over columns, as restart_main.cpp forms them (row i = data[i*c:(i+1)*c])."""
    xr = 0
    for i in range(r):
        counts = [0] * 256
        for b in data[i * c:(i + 1) * c]:
            counts[b] += 1
        xr = max(xr, max(counts))
    xc = 0
    for j in range(c):
        counts = [0] * 256
        for i in range(r):
            counts[data[i * c + j]] += 1
        xc = max(xc, max(counts))
    return xr, xc


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true", help="only verify files on disk against EXPECTED")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    specs = [
        ("random-source-1MiB.bin", lambda: keystream("random-source", 1 << 20), 0),
        ("restart-1bit-1000x1000.bin", lambda: keystream_bits("restart-1bit", 1_000_000), 1),
        ("restart-8bit-1000x1000.bin", lambda: keystream("restart-8bit", 1_000_000), 8),
        ("iid-lag32copy-q030-1bit-50000.bin", lambda: lag32copy_1bit(50_000), 1),
    ]

    bad = 0
    lines = [
        "# generated inputs for the sanitizer phase -- gen_inputs.py sha256=%s" % sha256_file(os.path.abspath(__file__)),
        "# written: %s" % time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "# one labelled line per file: name= sha256= bytes= width= [H_I=] [X_max_rows= X_max_cols=] expected_match=",
    ]
    for name, make, width in specs:
        path = os.path.join(args.out, name)
        if not args.check:
            data = make()
            with open(path, "wb") as f:
                f.write(data)
        if not os.path.exists(path):
            print("MISSING %s" % path, file=sys.stderr)
            bad += 1
            continue
        got = sha256_file(path)
        exp = EXPECTED.get(name)
        match = "yes" if got == exp else ("unrecorded" if exp is None else "NO")
        if match == "NO":
            bad += 1
        extra = ""
        if name in RESTART_HI:
            with open(path, "rb") as f:
                d = f.read()
            xr, xc = restart_xmax(d)
            extra = " H_I=%s X_max_rows=%d X_max_cols=%d" % (RESTART_HI[name], xr, xc)
        size = os.path.getsize(path)
        lines.append("name=%s sha256=%s bytes=%d width=%d%s expected_match=%s" % (name, got, size, width, extra, match))
        print("%-36s %s %9d bytes%s match=%s" % (name, got, size, extra, match))

    with open(os.path.join(args.out, "INPUTS.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    if bad:
        print("REFUSING: %d generated file(s) do not match EXPECTED -- the generator changed, or a file is missing. "
              "Nothing measured against these inputs is comparable to the recorded run." % bad, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
