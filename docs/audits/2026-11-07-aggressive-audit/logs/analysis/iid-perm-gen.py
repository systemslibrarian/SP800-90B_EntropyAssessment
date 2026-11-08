#!/usr/bin/env python3
"""Deterministic probe inputs for the IID permutation analysis (<= 20,000
samples each, run only with EA_ALLOW_SHORT_DATASET=1).  Writes into the
directory given as argv[1] and prints name, size and sha256 for the record."""
import hashlib, random, sys
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)

files = {}
# P1: 20,000 fair bits, width 1 -> binary path, every conversion exercised.
r = random.Random(20261107)
files["perm-p1-bits20000.bin"] = bytes(r.randrange(2) for _ in range(20000))
# P2: 20,000 uniform 3-bit symbols (k = 8), width 3 -> non-binary path.
r = random.Random(20261108)
files["perm-p2-k8-20000.bin"] = bytes(r.randrange(8) for _ in range(20000))
# P3: 20,000 samples over the two byte values {3, 200}, width 8 -> k = 2 with
# raw values that are not {0,1}: the binary path on translated symbols while
# excursion/compression see the raw values.
r = random.Random(20261109)
files["perm-p3-two-values-3-200.bin"] = bytes(r.choice((3, 200)) for _ in range(20000))

for name, data in files.items():
    (out / name).write_bytes(data)
    print(f"{name} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}")
