#!/usr/bin/env python3
"""seeds.py -- seed corpora and AFL++ dictionaries for the fuzzing phase of the
2026-11-07 aggressive audit.

Every byte is a deterministic function of the constants in this file (SHA-256 in
counter mode under a fixed key), so re-running regenerates byte-identical files and
`--check` verifies the files on disk against MANIFEST.txt (sha256 of the bytes on
disk, hashed after writing: the artefact is a file and the consumer reads the file).

Layout under --out (default <scratchpad>/fuzz/seeds):

  w1/ w2/ w4/ w7/ w8/   raw-sample seeds for declared/inferred width w, one symbol
                        per byte in the low w bits (utils.h read_file_subset):
      rnd-NNNNN.bin     pseudo-random symbols, N in 1,2,3,4,5,7,8,9,15,16,17,31,32,
                        33,63,64 (the "tiny" set) and 4200, 8192 (past MultiMCW's
                        4096-sample gate and the compression test's 1002 six-bit
                        blocks at width 1: 8192 bits -> 1365 blocks)
      allzero-64        one symbol (0)            -> inferred width 0, alphabet 1, refused
      allmax-64         one symbol (2^w-1)        -> alphabet 1, refused
      alternating-64    0,max,0,max              -> period 2, two symbols
      counter-64        i mod 2^w                 -> full alphabet, period 2^w
      runs8-64          each symbol held 8 times
      period3-63 / period7-63
      two-02            the 2-byte file (0, max)  -> the smallest file that assesses
      one-01            a 1-byte file             -> alphabet 1, refused
      lowbit0-64        (w >= 2) random symbols with the low bit forced to 0
      highbit-64        (w == 8) random bytes with bit 7 forced on
      WIDE seeds (data that does NOT fit the directory's declared width, so the
      declared-width targets exercise the refusal and the inferred-width targets
      exercise widening):
      w1/ff-in-1bit-64  63 bytes in {0,1} plus one 0xFF at index 17
      w4/one80-in-4bit-64   4-bit values plus one 0x80 at index 17
      w7/full8-in-7bit-64   8-bit values (bit 7 set at index 5)
  edge/empty.bin        0 bytes.  afl-fuzz silently SKIPS empty seeds, so run.sh
                        runs it once directly and records the outcome.
  fixture/              bits-2000.bin ({0,1}: fits every declared width), bytes-2000.bin
                        (0..255), empty.bin, random-source-64k.bin (EA_TEST_RANDOM_SOURCE
                        target for T6; see run.sh for what that variable does NOT reach)
  argv/*.txt            T7 seeds: one argv token per line, optional first line N|I|R
                        selecting ea_non_iid | ea_iid | ea_restart, placeholders
                        @F @G @E @X @D @O (see argv_driver.sh)
  dict/bytes.dict       structurally relevant byte tokens for the file-input targets
  dict/argv.dict        option letters, unit suffixes, boundary numerals for T7
  MANIFEST.txt          sha256  size  relative-path  construction

WHAT MATTERS ON THE FILE-INPUT PATH (read from cpp/shared/utils.h read_file_subset,
lines 319-547, and its duplicate read_file 549-735):
  * the file length L (ftell) sizes two malloc(L) buffers and, for width n > 1, a
    malloc(L*n) bitstring; L == 0 is refused;
  * with -l index,size the loaded count is min(L - index*size, size), so the
    interesting lengths are around the offset (T5: 17): L <= 17 refused past-end,
    L in 18..34 loads a short block, L >= 34 loads 17;
  * the OR of all bytes decides the inferred width (highest set bit), so a single
    high byte anywhere widens every symbol; a declared width is checked against the
    same OR and the file is REFUSED if any byte exceeds it (D-6) -- there is no
    masking path left to reach;
  * the alphabet is the set of distinct values (<= 256), translated to dense indices
    when sparse; alphabet 1 is refused in main before any estimator;
  * the bitstring unpacks each symbol MSB-first into n bits, so byte patterns with
    period 3 (24 bits = four 6-bit compression blocks) and runs of identical bytes
    are the structurally special inputs for the bit-level estimators.
Hence the seed families: lengths 1..64 dense around the -l offset; one-symbol,
two-symbol, full-alphabet, periodic and run-structured content; and wide bytes.

Usage:
  seeds.py [--out DIR] [--check] [--list]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCHPAD = "/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad"
DEFAULT_OUT = os.path.join(SCRATCHPAD, "fuzz", "seeds")

KEY = b"sp800-90b-aggressive-audit-2026-11-07-fuzz-seeds"
WIDTHS = (1, 2, 4, 7, 8)
TINY_SIZES = (1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64)
MID_SIZES = (4200, 8192)


def ctr_stream(n: int, label: str) -> bytes:
    """SHA-256 counter-mode keystream, n bytes, keyed on KEY and the label."""
    out = bytearray()
    counter = 0
    lab = label.encode()
    while len(out) < n:
        out += hashlib.sha256(KEY + b"|" + lab + b"|" + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:n])


def masked(n: int, width: int, label: str) -> bytes:
    mask = (1 << width) - 1
    return bytes(b & mask for b in ctr_stream(n, label))


def build_files() -> dict[str, tuple[bytes, str]]:
    """relative path -> (bytes, construction)."""
    files: dict[str, tuple[bytes, str]] = {}

    for w in WIDTHS:
        d = f"w{w}"
        mx = (1 << w) - 1
        for n in TINY_SIZES + MID_SIZES:
            files[f"{d}/rnd-{n:05d}.bin"] = (masked(n, w, f"rnd-w{w}-{n}"),
                                             f"SHA-256 CTR masked to {w} bits, {n} symbols")
        files[f"{d}/allzero-64.bin"] = (bytes(64), "64 x 0x00 (one symbol; inferred width 0)")
        files[f"{d}/allmax-64.bin"] = (bytes([mx] * 64), f"64 x {mx:#04x} (one symbol)")
        files[f"{d}/alternating-64.bin"] = (bytes([0, mx] * 32), f"0,{mx:#04x} alternating (period 2)")
        files[f"{d}/counter-64.bin"] = (bytes(i % (1 << w) for i in range(64)), f"i mod 2^{w}")
        files[f"{d}/runs8-64.bin"] = (bytes((i // 8) % (1 << w) for i in range(64)), f"(i div 8) mod 2^{w}: runs of 8")
        if w == 1:
            p3 = [0, 0, 1]
            p7 = [0, 0, 0, 1, 0, 1, 1]
        else:
            p3 = [0, 1, 2]
            p7 = [0, 1, 2, 3, 2, 1, mx]
        files[f"{d}/period3-63.bin"] = (bytes(p3[i % 3] for i in range(63)), f"period 3 pattern {p3}")
        files[f"{d}/period7-63.bin"] = (bytes(p7[i % 7] for i in range(63)), f"period 7 pattern {p7}")
        files[f"{d}/two-02.bin"] = (bytes([0, mx]), f"the 2-byte file: 0x00, {mx:#04x}")
        files[f"{d}/one-01.bin"] = (bytes([mx]), f"the 1-byte file: {mx:#04x}")
        if w >= 2:
            files[f"{d}/lowbit0-64.bin"] = (bytes(b & ~1 for b in masked(64, w, f"lowbit-w{w}")),
                                            f"{w}-bit random with bit 0 forced to 0 (constant non-leading bit)")
        if w == 8:
            files[f"{d}/highbit-64.bin"] = (bytes(b | 0x80 for b in ctr_stream(64, "highbit")),
                                            "random bytes with bit 7 forced on")

    # wide seeds: data that does not fit the directory's declared width
    b = bytearray(masked(64, 1, "ff-in-1bit")); b[17] = 0xFF
    files["w1/ff-in-1bit-64.bin"] = (bytes(b), "63 bytes in {0,1} + 0xFF at index 17 (declared 1: refused; inferred: width 8)")
    b = bytearray(masked(64, 4, "one80-in-4bit")); b[17] = 0x80
    files["w4/one80-in-4bit-64.bin"] = (bytes(b), "4-bit values + 0x80 at index 17 (declared 4: refused; inferred: width 8, 17 symbols)")
    b = bytearray(ctr_stream(64, "full8-in-7bit")); b[5] |= 0x80
    files["w7/full8-in-7bit-64.bin"] = (bytes(b), "8-bit values, bit 7 set at index 5 (declared 7: refused)")

    files["edge/empty.bin"] = (b"", "0 bytes (afl-fuzz skips it; run.sh runs it once)")

    files["fixture/bits-2000.bin"] = (masked(2000, 1, "fixture-bits"), "2000 bytes in {0,1}: fits every declared width 1..8")
    files["fixture/bytes-2000.bin"] = (ctr_stream(2000, "fixture-bytes"), "2000 bytes 0..255")
    files["fixture/empty.bin"] = (b"", "0 bytes")
    files["fixture/random-source-64k.bin"] = (ctr_stream(65536, "random-source"),
                                             "65536 bytes for EA_TEST_RANDOM_SOURCE (reaches writeJsonReport's temp suffix only, NOT seed())")

    for name, lines in argv_seeds().items():
        files[f"argv/{name}.txt"] = ("\n".join(lines).encode() + b"\n", "argv tokens: " + " ".join(lines))

    files["dict/bytes.dict"] = (BYTES_DICT.encode(), "AFL dictionary: structurally relevant bytes")
    files["dict/argv.dict"] = (argv_dict().encode(), "AFL dictionary: option tokens, unit suffixes, boundary numerals")
    return files


def argv_seeds() -> dict[str, list[str]]:
    return {
        # ea_non_iid (default tool)
        "basic-i-a-8": ["-i", "-a", "@F", "8"],
        "basic-inferred": ["-i", "-a", "@F"],
        "cond-t-1": ["-c", "-t", "@F", "1"],
        "subset-1-17": ["-l", "1,17", "-i", "@F"],
        "subset-glued": ["-l1,17", "@F", "8"],
        "subset-ulongmax": ["-l", "0,18446744073709551615", "@F", "8"],
        "subset-wrap": ["-l", "4294967296,1", "@F", "8"],
        "subset-zero-size": ["-l", "5,0", "@F"],
        "subset-malformed": ["-l", ",5", "@F"],
        "json-out": ["-o", "@O", "-i", "@F", "8"],
        "json-out-glued": ["-o@O", "-vv", "@F", "8"],
        "json-alias-input": ["-o", "@F", "-i", "@F", "8"],
        "json-repeated": ["-o", "@O", "-o", "@O", "@F", "8"],
        "version": ["--version"],
        "version-after-o": ["-o", "--version", "@F", "1"],
        "version-cluster": ["-vo", "--version", "@F", "1"],
        "version-after-bad": ["-Z", "--version", "@F", "1"],
        "dashdash": ["--", "@F", "1"],
        "dashdash-then-option": ["--", "@F", "1", "-q"],
        "late-option": ["-i", "@F", "1", "-q"],
        "late-numeric": ["@F", "1", "-1"],
        "cluster-vvq": ["-vvq", "@F", "8"],
        "width-9": ["@F", "9"],
        "width-0": ["@F", "0"],
        "width-08": ["@F", "08"],
        "width-plus8": ["@F", "+8"],
        "width-hex": ["@F", "0x8"],
        "no-operand": ["-i", "-a"],
        "too-many-operands": ["@F", "8", "8"],
        "missing-file": ["-i", "@X", "8"],
        "empty-file": ["-i", "@E", "8"],
        "directory": ["-i", "@D", "8"],
        "bytes-declared-1": ["-i", "@G", "1"],
        "bytes-inferred": ["-i", "@G"],
        "unknown-option": ["-h", "@F"],
        "colon-cluster": ["-:", "@F"],
        # ea_iid
        "iid-basic": ["I", "-i", "-a", "@F", "4"],
        "iid-cond": ["I", "-c", "-t", "@G", "8"],
        "iid-subset": ["I", "-l", "1,500", "@F"],
        "iid-json": ["I", "-o", "@O", "-q", "@F", "1"],
        # ea_restart: argv and H_I grammar only (the estimators need a 1,000,000-byte matrix)
        "restart-symbol": ["R", "-n", "@G", "8", "0.5/symbol"],
        "restart-bit": ["R", "-n", "@G", "8", "0.5/bit"],
        "restart-bare-1bit": ["R", "-i", "@F", "1", "0.9"],
        "restart-bare-8bit": ["R", "-n", "@G", "8", "4.0"],
        "restart-tiny-hi": ["R", "-n", "@F", "1", "1e-300"],
        "restart-underflow": ["R", "-n", "@F", "1", "1e-400"],
        "restart-overflow": ["R", "-n", "@F", "1", "1e400"],
        "restart-bad-hi": ["R", "-n", "@G", "8", "abc"],
        "restart-neg-hi": ["R", "-n", "@F", "1", "-0.5"],
        "restart-inf": ["R", "-n", "@F", "1", "-inf"],
        "restart-nan": ["R", "-n", "@F", "1", "nan"],
        "restart-hex": ["R", "-n", "@F", "1", "0x1p-1"],
        "restart-exp": ["R", "-n", "@F", "1", "5e-1/symbol"],
        "restart-exp-bad": ["R", "-n", "@F", "1", "5e/symbol"],
        "restart-dot": ["R", "-n", "@F", "1", "."],
        "restart-unit-only": ["R", "-n", "@F", "1", "/symbol"],
        "restart-unit-typo": ["R", "-n", "@F", "1", "0.5/bits"],
        "restart-unit-case": ["R", "-n", "@G", "8", "0.5/Symbol"],
        "restart-unit-space": ["R", "-n", "@F", "1", "0.5 /bit"],
        "restart-sim": ["R", "-s", "5000000", "-n", "@G", "8", "1/symbol"],
        "restart-sim-small": ["R", "-s", "10", "-n", "@F", "1", "0.5"],
        "restart-json": ["R", "-o", "@O", "-n", "@G", "8", "2/symbol"],
        "restart-two-operands": ["R", "@F", "0.5"],
        "restart-width-9": ["R", "@F", "9", "0.5"],
        "restart-no-hi": ["R", "-n", "@F", "1"],
        "restart-late-option": ["R", "-n", "@F", "1", "0.5", "-q"],
    }


BYTES_DICT = """\
# bytes.dict -- structurally relevant bytes for the raw-sample file path
# (cpp/shared/utils.h read_file_subset).  Generated by seeds.py.
zero="\\x00"
one="\\x01"
two="\\x02"
three="\\x03"
seven="\\x07"
fifteen="\\x0f"
thirtyone="\\x1f"
sixtythree="\\x3f"
onetwentyseven="\\x7f"
highbit="\\x80"
allones="\\xff"
alt55="\\x55"
altaa="\\xaa"
pair01="\\x00\\x01"
pair10="\\x01\\x00"
pairff00="\\xff\\x00"
run0x8="\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"
run1x8="\\x01\\x01\\x01\\x01\\x01\\x01\\x01\\x01"
runffx8="\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff"
blocks6_zero="\\x00\\x00\\x00"
blocks6_ones="\\xff\\xff\\xff"
blocks6_100000="\\x82\\x08\\x20"
blocks6_000001="\\x04\\x10\\x41"
alt3="\\x00\\x01\\x02"
alt17="\\x00\\x11\\x22\\x33\\x44\\x55\\x66\\x77\\x88\\x99\\xaa\\xbb\\xcc\\xdd\\xee\\xff\\x00"
"""


def argv_dict() -> str:
    toks = [
        ("opt_i", "-i\\x0a"), ("opt_c", "-c\\x0a"), ("opt_a", "-a\\x0a"), ("opt_t", "-t\\x0a"),
        ("opt_v", "-v\\x0a"), ("opt_q", "-q\\x0a"), ("opt_l", "-l\\x0a"), ("opt_o", "-o\\x0a"),
        ("opt_s", "-s\\x0a"), ("opt_n", "-n\\x0a"), ("opt_h", "-h\\x0a"), ("opt_colon", "-:\\x0a"),
        ("opt_vo", "-vo\\x0a"), ("opt_qo", "-qo\\x0a"), ("opt_vvq", "-vvq\\x0a"),
        ("dashdash", "--\\x0a"), ("version", "--version\\x0a"), ("longopt", "--help\\x0a"),
        ("unit_symbol", "/symbol"), ("unit_bit", "/bit"),
        ("exp_e", "e"), ("exp_E", "E+"), ("exp_minus", "e-"), ("inf", "inf"), ("nan", "nan"),
        ("hex", "0x"), ("hexfloat", "0x1p-1"),
        ("comma1", "1,"), ("comma2", ",1"), ("zero_zero", "0,0"), ("one_seventeen", "1,17"),
        ("ulong_max", "18446744073709551615"), ("ulong_max_plus", "18446744073709551616"),
        ("u32_max", "4294967295"), ("u32_max_plus", "4294967296"), ("i64_min_abs", "9223372036854775808"),
        ("big_exp", "1e308"), ("tiny_exp", "1e-300"), ("under_exp", "1e-400"), ("over_exp", "1e400"),
        ("neg_zero", "-0"), ("neg_one", "-1"), ("dot", "."), ("dotdot", ".."), ("plus8", "+8"),
        ("width8", "8\\x0a"), ("width1", "1\\x0a"), ("width9", "9\\x0a"), ("width0", "0\\x0a"), ("width08", "08\\x0a"),
        ("ph_F", "@F\\x0a"), ("ph_G", "@G\\x0a"), ("ph_E", "@E\\x0a"), ("ph_X", "@X\\x0a"),
        ("ph_D", "@D\\x0a"), ("ph_O", "@O\\x0a"),
        ("tool_N", "N\\x0a"), ("tool_I", "I\\x0a"), ("tool_R", "R\\x0a"),
        ("newline", "\\x0a"), ("sim_5m", "5000000\\x0a"), ("hi_half", "0.5\\x0a"),
    ]
    lines = ["# argv.dict -- tokens for the T7 argv fuzzer (argv_driver.sh grammar).  Generated by seeds.py."]
    lines += [f'{k}="{v}"' for k, v in toks]
    return "\n".join(lines) + "\n"


def write_all(out: str) -> int:
    files = build_files()
    rows = []
    for rel, (data, how) in sorted(files.items()):
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        with open(path, "rb") as fh:   # hash what is on disk, not what was intended
            digest = hashlib.sha256(fh.read()).hexdigest()
        rows.append((digest, os.path.getsize(path), rel, how))
    with open(os.path.join(out, "MANIFEST.txt"), "w") as fh:
        fh.write("# sha256  size  path  construction   (seeds.py, deterministic; verify with --check)\n")
        for digest, size, rel, how in rows:
            fh.write(f"{digest}  {size:7d}  {rel}  {how}\n")
    print(f"wrote {len(rows)} files under {out}")
    for sub in sorted({r[2].split('/')[0] for r in rows}):
        n = sum(1 for r in rows if r[2].startswith(sub + "/"))
        print(f"  {sub:8s} {n:3d} files")
    return 0


def check_all(out: str) -> int:
    man = os.path.join(out, "MANIFEST.txt")
    if not os.path.exists(man):
        print(f"CHECK FAILED: no manifest at {man}")
        return 1
    bad = 0
    n = 0
    expected = build_files()
    seen = set()
    with open(man) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            digest, size, rel = line.split()[:3]
            n += 1
            seen.add(rel)
            path = os.path.join(out, rel)
            if not os.path.exists(path):
                print(f"MISSING  {rel}"); bad += 1; continue
            with open(path, "rb") as fh2:
                actual = hashlib.sha256(fh2.read()).hexdigest()
            if actual != digest:
                print(f"CHANGED  {rel}  manifest {digest[:16]}.. disk {actual[:16]}.."); bad += 1
            if rel in expected:
                gen = hashlib.sha256(expected[rel][0]).hexdigest()
                if gen != digest:
                    print(f"STALE    {rel}  manifest {digest[:16]}.. generator {gen[:16]}.."); bad += 1
    for rel in expected:
        if rel not in seen:
            print(f"UNLISTED {rel} (generator knows it, manifest does not)"); bad += 1
    print(f"checked {n} manifest rows against disk and generator: {bad} problem(s)")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="verify files on disk against MANIFEST.txt and the generator")
    ap.add_argument("--list", action="store_true", help="list what would be written")
    a = ap.parse_args(argv)
    if a.list:
        for rel, (data, how) in sorted(build_files().items()):
            print(f"{len(data):7d}  {rel}  {how}")
        return 0
    if a.check:
        return check_all(a.out)
    return write_all(a.out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
