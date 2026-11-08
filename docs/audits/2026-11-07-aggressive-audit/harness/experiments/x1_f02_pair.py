#!/usr/bin/env python3
"""x1_f02_pair.py -- X1: the F02 width-inference pair on uniform 7-bit data.

Inputs (1,000,000 samples each, one per byte):
  x1-uniform7-msbdead-8bit-1000000.bin   v, v exactly uniform on 0..127 (bit 7 never set)
  x1-uniform7-lsbdead-8bit-1000000.bin   v << 1 (bit 0 never set) -- the SAME symbol sequence
                                         under an order-preserving relabelling, so every
                                         symbol-level ("Literal") estimate is identical by
                                         construction; only the bitstring and n differ.

Truth: the samples are IID uniform on 128 values, so the min-entropy is exactly 7 bits per
sample, in every sense (marginal, conditional, per-bit x 7).

What the pair separates (SP 800-90B 3.1.3, PDF p. 20: "L samples (each having n bits)";
H_I = min(H_original, n x H_bitstring)):
  * msbdead, width OMITTED  -> the tool infers n = 7 (utils.h: highest set bit) and builds
                               the bitstring from 7 bits per sample;
  * msbdead, width 8        -> n = 8, the constant top bit enters the bitstring as every
                               8th bit (the spec's computation at the submitter's width);
  * lsbdead, omitted or 8   -> n = 8 either way (bit 7 is in use): the negative control --
                               the same constant bit, now non-leading, is NOT removed by
                               inference, so the two runs must be identical.
The analysis phase measured inferred/declared = 1.219 at 20,000 samples (aggregation.md 2.6,
intake.md 2.4); both figures were below the truth (5.396 and 4.389 vs 7).  X1 re-measures at
the compliant size and pins the direction against the truth.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X1"
N = common.N_COMPLIANT


def generate() -> None:
    rows = common.read_manifest()
    v = common.uniform_below("x1-uniform7", N, 128)          # exactly uniform on 0..127
    assert v.max() <= 127 and v.min() >= 0
    common.write_data_file(
        "x1-uniform7-msbdead-8bit-1000000.bin", v, 0, EXPERIMENT,
        "uniform on 0..127 (SHA-256 CTR 'x1-uniform7', byte & 0x7F); bit 7 never set (MSB dead); "
        "truth 7 bits/sample; run with width omitted (infers 7) AND with 8",
        __file__, rows)
    common.write_data_file(
        "x1-uniform7-lsbdead-8bit-1000000.bin", (v.astype('uint16') << 1).astype('uint8'), 8, EXPERIMENT,
        "the same values << 1: bit 0 never set (LSB dead), bit 7 in use so inference gives 8; "
        "same symbol sequence as msbdead under an order-preserving relabelling; truth 7 bits/sample; "
        "negative control (omitted == declared 8)",
        __file__, rows)


if __name__ == "__main__":
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
