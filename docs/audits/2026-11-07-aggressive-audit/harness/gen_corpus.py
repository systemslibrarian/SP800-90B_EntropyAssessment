#!/usr/bin/env python3
"""gen_corpus.py -- deterministic input corpus for the 2026-11-07 differential audit.

Writes  <audit>/corpus/<family>-<bps>bit-<n>.bin  (one symbol per byte, the low
`bps` bits are the symbol) and  <audit>/corpus/MANIFEST.txt  (name, declared
bps, n, sha256, construction).  Every byte is a deterministic function of the
constants in this file: all randomness is SHA-256 in counter mode under a fixed
key, so the corpus does not depend on numpy's RNG stream or on any library
version.  Re-running regenerates byte-identical files; `--check` verifies the
files on disk against the manifest.

Families (task list), each at declared widths 1 and 8 bits, each at n =
1,000,000 (the SP 800-90B 3.1.1 minimum), 999,999 (just below) and 50,000
(quick); the smaller sizes are PREFIXES of the 1,000,000-sample stream so the
999,999 file is the legal-minimum file minus its last symbol:

  onesym0, onesymmax     all one symbol (0, and 2^bps-1)
  two9010, two5050       two symbols {0, 2^bps-1}, P(0) = 0.9 exactly / 0.5
  alternating            0, 2^bps-1, 0, 2^bps-1, ...
  period<P>              minimal period exactly P, P in 2,3,7,16,255,256,1000,1023,4095,4096
  runs<L>                symbol changes every L samples (counter mod 2^bps held L times)
  counter, counter3      i mod 2^bps, and (3 i) mod 2^bps
  lfsr16-tap1/-tap8      16-bit Fibonacci LFSR x^16+x^14+x^13+x^11+1 (period 65535)
  lfsr32-tap1/-tap8      32-bit Fibonacci LFSR x^32+x^22+x^2+x+1 (period 2^32-1)
                         tap1: one output bit per clock (packed MSB-first at width 8)
                         tap8: the low 8 state bits per clock (overlapping windows;
                               unpacked MSB-first at width 1)
  csprng                 SHA-256 counter-mode keystream -- the 'good' control
                         (also written at n = 5,000 for the harness smoke test)
  overwidth              symbols that exceed the declared width: declared 1 bit with
                         values in {0,1,2,3}; and, because a byte cannot exceed 8 bits,
                         the 8-bit counterpart is DECLARED 7 bits with values 0..255
                         (named overwidth-7bit).  Recorded in the manifest.

Degenerate coincidences at width 1 are kept on purpose and recorded in the
construction column: period2, alternating, counter and counter3 are the same
bit sequence 0,1,0,1,... at width 1.

Usage:
  gen_corpus.py [--out DIR] [--families a,b,...] [--widths 1,8] [--sizes n,n,...]
                [--no-smoke] [--list] [--check] [--dry-run]

The manifest is MERGED: lines for files this run did not generate are kept, so
other agents' corpus entries survive.  Files are written whole and then hashed
from disk, so the recorded sha256 is of the bytes actually on disk (guide
rule 17: the artifact is a file, and the consumer reads the file).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(AUDIT_DIR, "corpus")
MANIFEST_NAME = "MANIFEST.txt"

KEY_PREFIX = b"py90b-corpus-2026-11-07/"   # fixed; the whole corpus derives from it
NMAX = 1_000_000
SIZES = (1_000_000, 999_999, 50_000)
SMOKE_SIZE = 5_000
WIDTHS = (1, 8)
PERIODS = (2, 3, 7, 16, 255, 256, 1000, 1023, 4095, 4096)
RUN_LENGTHS = (10, 100, 10_000)

# Fibonacci LFSRs, right-shifting, output bit = state & 1 before the shift.
# `shifts` are the positions XORed to form the feedback bit: for the polynomial
# x^16+x^14+x^13+x^11+1 the tapped bits are 16-16, 16-14, 16-13, 16-11 = 0,2,3,5.
LFSRS = {
    "lfsr16": dict(nbits=16, shifts=(0, 2, 3, 5), seed=0xACE1,
                   poly="x^16+x^14+x^13+x^11+1", period=65535),
    "lfsr32": dict(nbits=32, shifts=(0, 10, 30, 31), seed=0xACE1ACE1,
                   poly="x^32+x^22+x^2+x+1", period=2**32 - 1),
}


# ----------------------------------------------------------------------------
# deterministic randomness
# ----------------------------------------------------------------------------

def keystream(label: str, nbytes: int) -> np.ndarray:
    """SHA-256 counter mode: block_i = SHA256(KEY_PREFIX || label || i as 8-byte big-endian).

    Returns the first `nbytes` bytes of the concatenated blocks as uint8.
    """
    key = KEY_PREFIX + label.encode("ascii")
    nblocks = (nbytes + 31) // 32
    out = bytearray(nblocks * 32)
    for i in range(nblocks):
        out[i * 32:(i + 1) * 32] = hashlib.sha256(key + i.to_bytes(8, "big")).digest()
    return np.frombuffer(bytes(out[:nbytes]), dtype=np.uint8)


def keystream_bits(label: str, nbits: int) -> np.ndarray:
    """Keystream unpacked to bits, MSB-first within each byte."""
    return np.unpackbits(keystream(label, (nbits + 7) // 8))[:nbits]


def minimal_period(pattern: np.ndarray) -> int:
    """Smallest d dividing len(pattern) such that pattern == pattern rolled by d."""
    p = len(pattern)
    for d in range(1, p + 1):
        if p % d == 0 and np.array_equal(pattern, np.roll(pattern, d)):
            return d
    return p  # unreachable: d = p always matches


def lfsr_run(cfg: dict, clocks: int) -> tuple[np.ndarray, np.ndarray]:
    """Clock a Fibonacci LFSR `clocks` times.

    Returns (output_bits, low_bytes): output_bits[t] = state & 1 before the shift
    at clock t; low_bytes[t] = state & 0xFF before the shift at clock t.
    Written as the plain per-clock loop so a reader can check it is an LFSR.
    """
    nbits, shifts, state = cfg["nbits"], cfg["shifts"], cfg["seed"]
    assert state != 0, "an all-zero LFSR state never changes"
    top = nbits - 1
    bits = np.empty(clocks, dtype=np.uint8)
    lows = np.empty(clocks, dtype=np.uint8)
    for t in range(clocks):
        bits[t] = state & 1
        lows[t] = state & 0xFF
        fb = 0
        for s in shifts:
            fb ^= (state >> s) & 1
        state = (state >> 1) | (fb << top)
    return bits, lows


# ----------------------------------------------------------------------------
# families: each returns (symbols uint8 of length NMAX, declared bps, construction text)
# ----------------------------------------------------------------------------

def fam_onesym0(w):
    return np.zeros(NMAX, np.uint8), w, "all symbols 0"


def fam_onesymmax(w):
    return np.full(NMAX, (1 << w) - 1, np.uint8), w, f"all symbols {(1 << w) - 1} (= 2^{w}-1)"


def fam_two9010(w):
    # exact P(0) = 0.9: keystream bytes in [0,250) are accepted (bytes >= 250 discarded);
    # accepted byte < 225 -> symbol 0 (225/250 = 0.9), else symbol 2^w-1.
    label = f"two9010-{w}bit"
    need = NMAX
    ks = keystream(label, int(NMAX * 1.1) + 4096)
    acc = ks[ks < 250]
    while len(acc) < need:  # practically unreachable; keeps the construction total
        ks = keystream(label, len(ks) * 2)
        acc = ks[ks < 250]
    acc = acc[:need]
    sym = np.where(acc < 225, 0, (1 << w) - 1).astype(np.uint8)
    return sym, w, (f"two symbols {{0, {(1 << w) - 1}}}, P(0) = 225/250 = 0.9 exactly: keystream '{label}' "
                    f"bytes >= 250 rejected, byte < 225 -> 0")


def fam_two5050(w):
    label = f"two5050-{w}bit"
    b = keystream_bits(label, NMAX)
    sym = np.where(b == 0, 0, (1 << w) - 1).astype(np.uint8)
    return sym, w, f"two symbols {{0, {(1 << w) - 1}}}, P(0) = 0.5: keystream '{label}' bits"


def fam_alternating(w):
    i = np.arange(NMAX)
    sym = np.where(i % 2 == 0, 0, (1 << w) - 1).astype(np.uint8)
    note = "" if w > 1 else " (at width 1 identical to period2, counter, counter3)"
    return sym, w, f"alternating 0, {(1 << w) - 1}, 0, ...{note}"


def make_periodic(p: int, w: int):
    """A pattern of minimal period exactly p over the w-bit alphabet, tiled to NMAX."""
    if w == 8 and p <= 256:
        pat = np.arange(p, dtype=np.uint8)
        how = f"pattern 0,1,...,{p - 1} (distinct symbols)"
    elif w == 1 and p == 2:
        pat = np.array([0, 1], np.uint8)
        how = "pattern 0,1 (at width 1 identical to alternating, counter, counter3)"
    else:
        label = f"period{p}-{w}bit"
        chunk = 0
        while True:
            if w == 1:
                pat = keystream_bits(label, p * (chunk + 1))[p * chunk:]
            else:
                pat = keystream(label, p * (chunk + 1))[p * chunk:]
            if minimal_period(pat) == p:
                break
            chunk += 1
        how = f"keystream '{label}' chunk {chunk} of length {p}, minimal period checked = {p}"
    sym = np.tile(pat, NMAX // p + 1)[:NMAX].astype(np.uint8)
    return sym, w, f"periodic, period {p}: {how}"


def fam_runs(L: int, w: int):
    i = np.arange(NMAX)
    sym = ((i // L) % (1 << w)).astype(np.uint8)
    return sym, w, f"runs of length {L}: symbol = floor(i/{L}) mod 2^{w}"


def fam_counter(w):
    sym = (np.arange(NMAX) % (1 << w)).astype(np.uint8)
    note = "" if w > 1 else " (at width 1 identical to alternating)"
    return sym, w, f"counter: i mod 2^{w}{note}"


def fam_counter3(w):
    sym = ((3 * np.arange(NMAX)) % (1 << w)).astype(np.uint8)
    note = "" if w > 1 else " (at width 1 identical to alternating)"
    return sym, w, f"counter stepping by 3: (3 i) mod 2^{w}{note}"


_LFSR_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def lfsr_streams(name: str) -> tuple[np.ndarray, np.ndarray]:
    """8*NMAX clocks of the named LFSR, computed once and sliced by every family."""
    if name not in _LFSR_CACHE:
        _LFSR_CACHE[name] = lfsr_run(LFSRS[name], 8 * NMAX)
    return _LFSR_CACHE[name]


def fam_lfsr(name: str, tap: str, w: int):
    cfg = LFSRS[name]
    bits, lows = lfsr_streams(name)
    base = f"{name}: Fibonacci LFSR {cfg['poly']}, seed 0x{cfg['seed']:X}, period {cfg['period']}"
    if tap == "tap1":
        if w == 1:
            sym = bits[:NMAX]
            how = "one output bit (state & 1) per clock, one clock per symbol"
        else:
            sym = np.packbits(bits[:8 * NMAX])
            how = "one output bit per clock, 8 clocks packed MSB-first per byte"
    else:  # tap8
        if w == 8:
            sym = lows[:NMAX]
            how = "low 8 bits of the state per clock (overlapping windows), one clock per byte"
        else:
            sym = np.unpackbits(lows[:NMAX // 8])
            how = "low 8 bits of the state per clock, unpacked MSB-first to 8 one-bit symbols"
    return sym.astype(np.uint8), w, f"{base}; {how}"


def fam_csprng(w):
    label = f"csprng-{w}bit"
    if w == 8:
        sym = keystream(label, NMAX)
        how = "keystream bytes"
    else:
        sym = keystream_bits(label, NMAX)
        how = "keystream bits, MSB-first"
    return sym.astype(np.uint8), w, f"SHA-256 counter-mode keystream '{label}' ({how}); the 'good' control"


def fam_overwidth(w):
    if w == 1:
        b = keystream_bits("overwidth-1bit", 2 * NMAX)
        sym = (2 * b[0::2] + b[1::2]).astype(np.uint8)
        return sym, 1, ("DECLARED 1 bit; values in {0,1,2,3} uniform (two keystream 'overwidth-1bit' bits "
                        "per symbol) -- symbols exceed the declared width")
    # the 8-bit counterpart: a byte cannot exceed 8 bits, so declare 7 and fill 0..255
    sym = keystream("overwidth-7bit", NMAX)
    return sym, 7, ("DECLARED 7 bits; values 0..255 from keystream 'overwidth-7bit' -- symbols exceed the "
                    "declared width.  Stands in for the impossible 'declared 8, values > 255' file")


def family_table(widths):
    """Ordered list of (family_name, width, callable) for the requested widths."""
    out = []
    for w in widths:
        out.append(("onesym0", w, lambda w=w: fam_onesym0(w)))
        out.append(("onesymmax", w, lambda w=w: fam_onesymmax(w)))
        out.append(("two9010", w, lambda w=w: fam_two9010(w)))
        out.append(("two5050", w, lambda w=w: fam_two5050(w)))
        out.append(("alternating", w, lambda w=w: fam_alternating(w)))
        for p in PERIODS:
            out.append((f"period{p}", w, lambda p=p, w=w: make_periodic(p, w)))
        for L in RUN_LENGTHS:
            out.append((f"runs{L}", w, lambda L=L, w=w: fam_runs(L, w)))
        out.append(("counter", w, lambda w=w: fam_counter(w)))
        out.append(("counter3", w, lambda w=w: fam_counter3(w)))
        for name in ("lfsr16", "lfsr32"):
            for tap in ("tap1", "tap8"):
                out.append((f"{name}-{tap}", w, lambda name=name, tap=tap, w=w: fam_lfsr(name, tap, w)))
        out.append(("csprng", w, lambda w=w: fam_csprng(w)))
        out.append(("overwidth", w, lambda w=w: fam_overwidth(w)))
    return out


# ----------------------------------------------------------------------------
# manifest
# ----------------------------------------------------------------------------

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_manifest(path: str) -> dict[str, dict]:
    """name -> {'bps','n','sha256','construction'}; '#' lines ignored."""
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            name, bps, n, sha = parts[:4]
            construction = parts[4] if len(parts) > 4 else ""
            rows[name] = dict(bps=int(bps), n=int(n), sha256=sha, construction=construction)
    return rows


def write_manifest(path: str, rows: dict[str, dict], generator_sha: str) -> None:
    lines = [
        "# py90b differential corpus manifest -- written by harness/gen_corpus.py",
        f"# generator sha256: {generator_sha}",
        f"# key prefix: {KEY_PREFIX.decode()}  (all randomness is SHA-256 counter mode under this key;",
        "#   no numpy RNG is used, so the bytes do not depend on any library version)",
        f"# written: {time.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "# columns (tab-separated): name\tbps\tn\tsha256\tconstruction",
        "# 'bps' is the DECLARED width the driver passes to the tool; 'n' is the file size in bytes",
        "# (one symbol per byte).  Files with n < 1000000 need EA_ALLOW_SHORT_DATASET=1 (non-compliant).",
    ]
    for name in sorted(rows):
        r = rows[name]
        lines.append(f"{name}\t{r['bps']}\t{r['n']}\t{r['sha256']}\t{r['construction']}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def plan(families_filter, widths, sizes, smoke):
    """List of (name, width, generator, size) in generation order."""
    items = []
    for fam, w, gen in family_table(widths):
        if families_filter and fam not in families_filter:
            continue
        for n in sizes:
            items.append((fam, w, gen, n))
        if smoke and fam == "csprng" and SMOKE_SIZE not in sizes:
            items.append((fam, w, gen, SMOKE_SIZE))
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT, help="corpus directory (default: <audit>/corpus)")
    ap.add_argument("--families", default="", help="comma-separated family names (default: all)")
    ap.add_argument("--widths", default="1,8", help="comma-separated declared widths (default: 1,8)")
    ap.add_argument("--sizes", default=",".join(str(s) for s in SIZES), help="comma-separated sizes")
    ap.add_argument("--no-smoke", action="store_true", help="do not write the 5,000-sample csprng smoke files")
    ap.add_argument("--list", action="store_true", help="print the plan and exit")
    ap.add_argument("--check", action="store_true", help="verify files on disk against the manifest and exit")
    ap.add_argument("--dry-run", action="store_true", help="generate in memory and print hashes; write nothing")
    args = ap.parse_args(argv)

    out_dir = os.path.abspath(args.out)
    manifest_path = os.path.join(out_dir, MANIFEST_NAME)
    generator_sha = sha256_file(os.path.abspath(__file__))

    if args.check:
        rows = read_manifest(manifest_path)
        if not rows:
            print(f"CHECK: no manifest at {manifest_path}", file=sys.stderr)
            return 2
        bad = 0
        for name, r in sorted(rows.items()):
            p = os.path.join(out_dir, name)
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
                print(f"OK       {name}")
        print(f"CHECK: {len(rows) - bad} ok, {bad} bad, of {len(rows)} manifest rows")
        return 0 if bad == 0 else 1

    families_filter = set(x for x in args.families.split(",") if x)
    widths = tuple(int(x) for x in args.widths.split(",") if x)
    sizes = tuple(int(x) for x in args.sizes.split(",") if x)
    for n in sizes:
        if n > NMAX:
            ap.error(f"size {n} exceeds NMAX {NMAX} (each file must stay <= 1 MB)")
    items = plan(families_filter, widths, sizes, smoke=not args.no_smoke)

    if args.list:
        for fam, w, _gen, n in items:
            print(f"{fam}\t{w}\t{n}")
        print(f"# {len(items)} files")
        return 0

    if not args.dry_run:
        os.makedirs(out_dir, exist_ok=True)
    rows = read_manifest(manifest_path)
    generated = 0
    t0 = time.time()
    cache: dict[tuple[str, int], tuple[np.ndarray, int, str]] = {}
    for fam, w, gen, n in items:
        if (fam, w) not in cache:
            cache[(fam, w)] = gen()
        sym, bps, construction = cache[(fam, w)]
        assert len(sym) == NMAX and sym.dtype == np.uint8
        name = f"{fam}-{bps}bit-{n}.bin"
        data = sym[:n].tobytes()
        assert len(data) == n
        if args.dry_run:
            sha = hashlib.sha256(data).hexdigest()
        else:
            path = os.path.join(out_dir, name)
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
            sha = sha256_file(path)  # hash what is on disk, not what was meant to be written
            if os.path.getsize(path) != n:
                raise RuntimeError(f"{name}: wrote {os.path.getsize(path)} bytes, expected {n}")
        rows[name] = dict(bps=bps, n=n, sha256=sha, construction=construction)
        generated += 1
        print(f"{name}\t{bps}\t{n}\t{sha}")
    if not args.dry_run:
        write_manifest(manifest_path, rows, generator_sha)
        print(f"# wrote {generated} files and {manifest_path} ({len(rows)} rows) in {time.time() - t0:.1f}s")
    else:
        print(f"# dry run: {generated} files hashed, nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
