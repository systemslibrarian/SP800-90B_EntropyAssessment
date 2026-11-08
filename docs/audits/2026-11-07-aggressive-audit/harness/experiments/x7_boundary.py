#!/usr/bin/env python3
"""x7_boundary.py -- X7: the 999,999 / 1,000,000 / 1,000,001 intake boundary, both tools, both
widths, with `-l` subsets.

Files (prefixes of ONE keystream per width, so the 999,999-sample file is the 1,000,000-sample
file minus its last symbol and the 1,000,001-sample file is it plus one):
  x7-csprng-1bit-{999999,1000000,1000001}.bin   keystream bits 'x7-csprng-1bit', MSB-first, one
                                                bit per byte
  x7-csprng-8bit-{999999,1000000,1000001}.bin   keystream bytes 'x7-csprng-8bit'

SP 800-90B 3.1.1 (PDF p. 17): "at least 1 000 000 sample values".  utils.h
dataset_meets_minimum(): `if (dp->len >= MIN_SIZE) return true;` on the LOADED count, so a
`-l index,samples` subset is judged by what it loads.  ea_restart requires EXACTLY 1,000,000
(restart_main.cpp `data.len != MIN_SIZE`), and EA_ALLOW_SHORT_DATASET does not apply there.

Decision (PLAN.md X7): refusal exactness --
  999,999   -> refused by ea_non_iid and ea_iid (exit 255, JSON errorLevel -1, errorClass
               "input", message names 999999 and 1000000); refused by ea_restart;
  1,000,000 -> accepted by all three ("Loaded 1000000 samples");
  1,000,001 -> accepted by ea_non_iid / ea_iid ("Loaded 1000001 samples"); REFUSED by ea_restart;
  -l 0,1000000 on the 1,000,001 file -> accepted (loads exactly 1,000,000; JSON subset fields);
  -l 1,1000000 on the 1,000,001 file -> loads 1 sample -> refused by the minimum check (which
               precedes the one-symbol-alphabet check);
  -l 0,999999 on the 1,000,000 file  -> refused;
  -l 1,500000 on the 1,000,000 file  -> loads 500,000 -> refused.
Any acceptance of < 1,000,000 loaded samples without the escape, or any refusal of >= 1,000,000,
is a MEDIUM (wrong refusal) finding.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X7"
N = common.N_COMPLIANT
SIZES = (N - 1, N, N + 1)


def generate() -> None:
    rows = common.read_manifest()
    bits = common.keystream_bits("x7-csprng-1bit", N + 1)
    for n in SIZES:
        common.write_data_file(f"x7-csprng-1bit-{n}.bin", bits[:n], 1, EXPERIMENT,
                               "keystream bits 'x7-csprng-1bit' (MSB-first), one per byte; prefix of the "
                               "1,000,001-bit stream", __file__, rows)
    by = common.keystream("x7-csprng-8bit", N + 1)
    for n in SIZES:
        common.write_data_file(f"x7-csprng-8bit-{n}.bin", by[:n], 8, EXPERIMENT,
                               "keystream bytes 'x7-csprng-8bit'; prefix of the 1,000,001-byte stream",
                               __file__, rows)


if __name__ == "__main__":
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
