#!/usr/bin/env python3
"""gen_inputs.py -- deterministic inputs for the determinism / platform phase.

Writes, under <audit>/logs/determinism/inputs/ (a .gitignore there excludes *.bin;
the manifest inputs.sha256 is what the record keeps):

  restart-csprng-1bit-1000x1000.bin   1,000,000 one-bit symbols (one per byte) for
                                      ea_restart: a 1000 x 1000 restart matrix in the
                                      row-dataset layout of SP 800-90B 3.1.4.1
  restart-csprng-8bit-1000x1000.bin   1,000,000 eight-bit symbols, same layout
  fixed-random-source-1MiB.bin        1,048,576 bytes, the file EA_TEST_RANDOM_SOURCE
                                      points at in the ea_iid arm (b).  Its first 32
                                      bytes are asserted non-zero so that neither a
                                      32-byte seed read nor the 8-byte temp-suffix read
                                      (TestRunUtils.h writeJsonReport) can be zero.
  --smoke adds:
  smoke-csprng-1bit-20000.bin         the first 20,000 bytes of corpus/csprng-1bit-50000.bin
  smoke-csprng-8bit-20000.bin         the first 20,000 bytes of corpus/csprng-8bit-50000.bin
                                      (gen_corpus.py documents the smaller corpus files
                                      as PREFIXES of one stream, and the 50,000-byte
                                      source is verified against corpus/MANIFEST.txt
                                      before it is cut)

Every byte of the first three is a deterministic function of the constants here:
SHA-256 in counter mode under a fixed key prefix that differs from gen_corpus.py's,
so these streams are distinct from every corpus stream.  Re-running regenerates
byte-identical files; --check verifies the files on disk against the manifest and
exits 1 on any mismatch (rule 17: the artefact is a file, hashed from disk after
writing).

Usage: gen_inputs.py [--out DIR] [--smoke] [--check] [--corpus DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(os.path.dirname(HERE))
DEFAULT_OUT = os.path.join(AUDIT_DIR, "logs", "determinism", "inputs")
DEFAULT_CORPUS = os.path.join(AUDIT_DIR, "corpus")
MANIFEST = "inputs.sha256"

KEY_PREFIX = b"determinism-2026-11-07/"   # distinct from gen_corpus.py's py90b-corpus-2026-11-07/
R, C = 1000, 1000                           # SP 800-90B 3.1.4.1: 1000 restarts x 1000 samples
MIB = 1 << 20
SMOKE_N = 20_000
SMOKE_SOURCES = {
    "smoke-csprng-1bit-20000.bin": "csprng-1bit-50000.bin",
    "smoke-csprng-8bit-20000.bin": "csprng-8bit-50000.bin",
}


def keystream(label: str, nbytes: int) -> bytes:
    key = KEY_PREFIX + label.encode("ascii")
    out = bytearray()
    i = 0
    while len(out) < nbytes:
        out += hashlib.sha256(key + i.to_bytes(8, "big")).digest()
        i += 1
    return bytes(out[:nbytes])


def keystream_bits(label: str, nbits: int) -> bytes:
    raw = keystream(label, (nbits + 7) // 8)
    bits = bytearray(nbits)
    for i in range(nbits):
        bits[i] = (raw[i >> 3] >> (7 - (i & 7))) & 1      # MSB-first, as gen_corpus.py
    return bytes(bits)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_manifest(path: str) -> dict:
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            rows[parts[0]] = dict(n=int(parts[1]), sha256=parts[2],
                                  construction=parts[3] if len(parts) > 3 else "")
    return rows


def write_manifest(path: str, rows: dict) -> None:
    lines = [
        "# determinism-phase inputs -- written by harness/determinism/gen_inputs.py",
        f"# generator sha256: {sha256_file(os.path.abspath(__file__))}",
        f"# key prefix: {KEY_PREFIX.decode()}  (SHA-256 counter mode; no library RNG)",
        f"# written: {time.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "# columns (tab-separated): name\tn\tsha256\tconstruction",
    ]
    for name in sorted(rows):
        r = rows[name]
        lines.append(f"{name}\t{r['n']}\t{r['sha256']}\t{r['construction']}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def corpus_row(corpus_dir: str, name: str) -> dict | None:
    man = os.path.join(corpus_dir, "MANIFEST.txt")
    if not os.path.exists(man):
        return None
    with open(man, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if p[0] == name and len(p) >= 4:
                return dict(bps=int(p[1]), n=int(p[2]), sha256=p[3])
    return None


def plan(smoke: bool, corpus_dir: str):
    """List of (name, bytes-producer, construction)."""
    items = [
        ("restart-csprng-1bit-1000x1000.bin",
         lambda: keystream_bits("restart-1bit", R * C),
         f"{R}x{C} restart matrix, row-dataset layout; 1-bit symbols (one per byte) = keystream "
         f"'restart-1bit' bits MSB-first"),
        ("restart-csprng-8bit-1000x1000.bin",
         lambda: keystream("restart-8bit", R * C),
         f"{R}x{C} restart matrix, row-dataset layout; 8-bit symbols = keystream 'restart-8bit' bytes"),
        ("fixed-random-source-1MiB.bin",
         lambda: keystream("fixed-random-source", MIB),
         "1 MiB keystream 'fixed-random-source'; target of EA_TEST_RANDOM_SOURCE in the ea_iid arm (b); "
         "first 32 bytes asserted non-zero"),
    ]
    if smoke:
        for name, src in SMOKE_SOURCES.items():
            def make(src=src):
                row = corpus_row(corpus_dir, src)
                p = os.path.join(corpus_dir, src)
                if row is None:
                    raise SystemExit(f"REFUSED: {src} has no row in {corpus_dir}/MANIFEST.txt")
                if not os.path.exists(p):
                    raise SystemExit(f"REFUSED: {p} is absent (run gen_corpus.py)")
                got = sha256_file(p)
                if got != row["sha256"] or os.path.getsize(p) != row["n"]:
                    raise SystemExit(f"REFUSED: {src} on disk ({got}, {os.path.getsize(p)} bytes) does not "
                                     f"match its manifest row ({row['sha256']}, {row['n']} bytes)")
                with open(p, "rb") as f:
                    data = f.read(SMOKE_N)
                if len(data) != SMOKE_N:
                    raise SystemExit(f"REFUSED: {src} shorter than {SMOKE_N} bytes")
                return data
            items.append((name, make,
                          f"first {SMOKE_N} bytes of corpus/{src} (prefix of the same stream; "
                          f"source verified against corpus/MANIFEST.txt); NON-COMPLIANT size, smoke only"))
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--smoke", action="store_true", help="also write the two 20,000-byte smoke prefixes")
    ap.add_argument("--check", action="store_true", help="verify files on disk against the manifest; write nothing")
    args = ap.parse_args(argv)

    out = os.path.abspath(args.out)
    man_path = os.path.join(out, MANIFEST)

    if args.check:
        rows = read_manifest(man_path)
        if not rows:
            print(f"CHECK: no manifest at {man_path}")
            return 2
        bad = 0
        for name, r in sorted(rows.items()):
            p = os.path.join(out, name)
            if not os.path.exists(p):
                print(f"MISSING  {name}"); bad += 1; continue
            size, sha = os.path.getsize(p), sha256_file(p)
            if size != r["n"] or sha != r["sha256"]:
                print(f"MISMATCH {name}: size {size} (manifest {r['n']}), sha256 {sha} (manifest {r['sha256']})")
                bad += 1
            else:
                print(f"OK       {name}")
        print(f"CHECK: {len(rows) - bad} ok, {bad} bad, of {len(rows)} manifest rows")
        return 0 if bad == 0 else 1

    os.makedirs(out, exist_ok=True)
    gi = os.path.join(out, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w") as f:
            f.write("# generated, deterministic (harness/determinism/gen_inputs.py); inputs.sha256 is the record\n*.bin\n")
    rows = read_manifest(man_path)
    for name, make, construction in plan(args.smoke, os.path.abspath(args.corpus)):
        data = make()
        if name.startswith("fixed-random-source"):
            if data[:32] == b"\0" * 32 or data[:8] == b"\0" * 8:
                raise SystemExit("REFUSED: the fixed random source begins with zero bytes")
        path = os.path.join(out, name)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        sha = sha256_file(path)                      # hash what is on disk
        n = os.path.getsize(path)
        if n != len(data):
            raise RuntimeError(f"{name}: wrote {n} bytes, expected {len(data)}")
        rows[name] = dict(n=n, sha256=sha, construction=construction)
        print(f"{name}\t{n}\t{sha}")
    write_manifest(man_path, rows)
    print(f"# wrote {man_path} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
