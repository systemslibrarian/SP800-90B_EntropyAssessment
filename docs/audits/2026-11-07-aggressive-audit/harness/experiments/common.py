#!/usr/bin/env python3
"""common.py -- shared helpers for the execution-phase overstatement experiments (X1..X7).

Every input file the experiments use is a deterministic function of the constants in the
generator that writes it: all randomness is SHA-256 in counter mode under a fixed key
(KEY_PREFIX + a per-stream label), never numpy's or Python's RNG, so the bytes do not depend
on any library version.  Files are written whole, then hashed FROM DISK, and the digest is
recorded in harness/experiments/MANIFEST.txt (the manifest is merged: rows for files a run
did not touch are kept).  `check_manifest()` re-hashes what is on disk against the manifest.

Data files live in corpus/experiments/ (gitignored: each is up to 1,000,001 bytes and is
regenerated from the generator).  Nothing here runs a tool.

Manifest row (tab-separated):
  name  bps  n  sha256  generator_sha256  experiment  construction
`bps` is the declared width a plan step passes to the tool (0 = "omitted, let the tool infer");
`n` is the file size in bytes (one symbol per byte, low `bps` bits are the symbol).
"""
from __future__ import annotations

import hashlib
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(AUDIT_DIR)))
DATA_DIR = os.path.join(AUDIT_DIR, "corpus", "experiments")
LOG_DIR = os.path.join(AUDIT_DIR, "logs", "experiments")
MANIFEST = os.path.join(HERE, "MANIFEST.txt")
REFERENCE_DIR = os.path.join(AUDIT_DIR, "reference")

KEY_PREFIX = b"aa-experiments-2026-11-07/"   # fixed; every stream derives from it + its label
N_COMPLIANT = 1_000_000                       # SP 800-90B 3.1.1 minimum (utils.h MIN_SIZE)


# ----------------------------------------------------------------------------------------
# deterministic randomness
# ----------------------------------------------------------------------------------------
def keystream(label: str, nbytes: int) -> np.ndarray:
    """SHA-256(KEY_PREFIX || label || counter_be64) for counter = 0, 1, ...; first nbytes."""
    key = KEY_PREFIX + label.encode("utf-8")
    nblocks = (nbytes + 31) // 32
    out = np.empty(nblocks * 32, dtype=np.uint8)
    for i in range(nblocks):
        out[i * 32:(i + 1) * 32] = np.frombuffer(hashlib.sha256(key + i.to_bytes(8, "big")).digest(),
                                                 dtype=np.uint8)
    return out[:nbytes]


def keystream_bits(label: str, nbits: int) -> np.ndarray:
    """nbits bits of the keystream, MSB-first within each byte, as a uint8 array of 0/1."""
    b = keystream(label, (nbits + 7) // 8)
    return np.unpackbits(b)[:nbits].astype(np.uint8)


def uniform_below(label: str, n: int, m: int) -> np.ndarray:
    """n values exactly uniform on [0, m), 2 <= m <= 256, by rejection on keystream bytes
    (a byte is accepted iff it is below floor(256/m)*m; the value is byte mod m)."""
    if not 2 <= m <= 256:
        raise ValueError("m must be in 2..256")
    limit = (256 // m) * m
    out = np.empty(0, dtype=np.uint8)
    need = n
    chunk = 0
    while out.shape[0] < n:
        # draw a chunk at a time, continuing the counter through the label suffix
        raw = keystream(f"{label}/chunk{chunk}", max(1024, int(need * 1.1) + 64))
        acc = raw[raw < limit] % m
        out = np.concatenate([out, acc.astype(np.uint8)])
        need = n - out.shape[0]
        chunk += 1
    return out[:n]


def rational_bernoulli(label: str, n: int, num: int, den: int) -> np.ndarray:
    """n Boolean draws with P(True) = num/den EXACTLY (den <= 256), by rejection on bytes:
    bytes >= floor(256/den)*den are rejected; the event is (byte mod den) < num."""
    if not (1 <= den <= 256 and 0 <= num <= den):
        raise ValueError("need 1 <= den <= 256 and 0 <= num <= den")
    limit = (256 // den) * den
    out = np.empty(0, dtype=bool)
    need = n
    chunk = 0
    while out.shape[0] < n:
        raw = keystream(f"{label}/chunk{chunk}", max(1024, int(need * 1.1) + 64))
        acc = (raw[raw < limit] % den) < num
        out = np.concatenate([out, acc])
        need = n - out.shape[0]
        chunk += 1
    return out[:n]


# ----------------------------------------------------------------------------------------
# files and the manifest
# ----------------------------------------------------------------------------------------
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest(path: str = MANIFEST) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            name, bps, n, sha, gsha, exp = parts[:6]
            construction = "\t".join(parts[6:])
            rows[name] = dict(bps=int(bps), n=int(n), sha256=sha, generator_sha256=gsha,
                              experiment=exp, construction=construction)
    return rows


def write_manifest(rows: dict[str, dict], path: str = MANIFEST) -> None:
    lines = [
        "# execution-phase experiment inputs -- written by harness/experiments/*.py (see PLAN.md)",
        f"# key prefix: {KEY_PREFIX.decode()}  (all randomness is SHA-256 counter mode under this key + a",
        "#   per-stream label; no numpy/Python RNG is used, so the bytes do not depend on any library version)",
        f"# written: {time.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "# columns (tab-separated): name\tbps\tn\tsha256\tgenerator_sha256\texperiment\tconstruction",
        "# 'bps' is the declared width the plan passes to the tool (0 = omitted: the tool infers it);",
        "# 'n' is the file size in bytes (one symbol per byte, low bps bits are the symbol).",
        "# Files live in corpus/experiments/ and are NOT committed; regenerate with the named generator",
        "# and verify with `<generator>.py --check` (re-hashes what is on disk).",
    ]
    for name in sorted(rows):
        r = rows[name]
        lines.append(f"{name}\t{r['bps']}\t{r['n']}\t{r['sha256']}\t{r['generator_sha256']}\t"
                     f"{r['experiment']}\t{r['construction']}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def write_data_file(name: str, data, bps: int, experiment: str, construction: str,
                    generator_file: str, manifest_rows: dict | None = None) -> dict:
    """Write corpus/experiments/<name>, hash it from disk, record/merge the manifest row.
    `data` is bytes or a uint8 array.  Returns the manifest row."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if isinstance(data, np.ndarray):
        if data.dtype != np.uint8:
            if data.min() < 0 or data.max() > 255:
                raise ValueError(f"{name}: values outside 0..255")
            data = data.astype(np.uint8)
        payload = data.tobytes()
    else:
        payload = bytes(data)
    path = os.path.join(DATA_DIR, name)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(payload)
    os.replace(tmp, path)
    sha = sha256_file(path)                     # hash what is on disk, not what was meant
    if sha != sha256_bytes(payload):
        raise RuntimeError(f"{name}: on-disk sha256 differs from the bytes written")
    row = dict(bps=int(bps), n=len(payload), sha256=sha,
               generator_sha256=sha256_file(os.path.abspath(generator_file)),
               experiment=experiment, construction=construction.replace("\t", " ").replace("\n", " "))
    rows = manifest_rows if manifest_rows is not None else read_manifest()
    rows[name] = row
    write_manifest(rows)
    print(f"wrote {path}  n={row['n']}  sha256={sha}")
    return row


def check_manifest(experiment: str | None = None) -> int:
    """Re-hash the files on disk against the manifest.  Returns the number of mismatches
    (a missing file counts as a mismatch); prints one line per file."""
    rows = read_manifest()
    bad = 0
    for name in sorted(rows):
        r = rows[name]
        if experiment and r["experiment"] != experiment:
            continue
        p = os.path.join(DATA_DIR, name)
        if not os.path.exists(p):
            print(f"MISSING  {name}")
            bad += 1
            continue
        size = os.path.getsize(p)
        sha = sha256_file(p)
        if size != r["n"] or sha != r["sha256"]:
            print(f"MISMATCH {name}: size {size} (manifest {r['n']}), sha256 {sha} (manifest {r['sha256']})")
            bad += 1
        else:
            print(f"ok       {name}  n={size}  sha256={sha}")
    return bad


def standard_main(argv, experiment: str, generate_fn) -> int:
    """`gen.py` writes the files; `gen.py --check` verifies them against the manifest."""
    if "--check" in argv:
        bad = check_manifest(experiment)
        print(f"{experiment}: {'OK' if bad == 0 else str(bad) + ' MISMATCH(ES)'}")
        return 0 if bad == 0 else 1
    generate_fn()
    return 0
