#!/usr/bin/env python3
"""x4_degenerate.py -- X4: inputs built to drive an estimator to a degenerate value at the
compliant size (1,000,000 samples), for the NaN / inf / -0 / silent-drop hunt.

Files (one symbol per byte):
  x4-alternating-1bit-1000000.bin        0,1,0,1,...  (width 1).  Every collision takes exactly
                                         two samples: Collision v = 500,000, X-bar = 2 exactly,
                                         sigma-hat = 0 exactly -> the 6.3.2 step-6 term is 0/sqrt(v)
                                         and X-bar' = 2.  Byte-identical to corpus/alternating-1bit.
  x4-alternating-0-255-8bit-1000000.bin  0,255,0,255,... (width 8).  Two-valued 8-bit data: the
                                         tool translates to {0,1} and takes the BINARY branch
                                         (alph_size == 2), so Collision/Markov/Compression run on
                                         the translated symbols and no Bitstring block exists.
                                         Byte-identical to corpus/alternating-8bit.
  x4-two-symbol-0-255-random-8bit-1000000.bin   {0,255} with P(0) = 1/2 exactly (keystream bits):
                                         the same binary-path-through-translation with a
                                         non-degenerate sequence (control for the previous file).
  x4-one-symbol-once-1bit-1000000.bin    999,999 zeros and a single 1 at index 500,000 (width 1).
                                         MCV: p-hat = 0.999999, p_u = min(1, p-hat + 2.576*sqrt(...))
                                         = 1 -> min entropy = -log2(1) = -0 (printed "-0").  Markov:
                                         P_1 = 1e-6, C_11 = 0 so P_{1,1} = 0 (the 6.3.3 -log2 of a
                                         zero transition).  t-Tuple/LRS: u and v near 500,000.
  x4-one-symbol-once-8bit-1000000.bin    uniform on 0..254 with the value 255 at index 500,000
                                         ONLY (width 8): a 256-symbol alphabet with one count-1
                                         symbol; exercises the translation table and the
                                         symbol-level estimators' rare-symbol paths.
  x4-counter-mod256-8bit-1000000.bin     i mod 256 (width 8): period 256, every 8-bit tuple of
                                         any length is deterministic; every predictor reaches
                                         P_global = 1 (P_global' = min(1, 1 + 0) = 1 -> -0),
                                         t-Tuple's u is ~991,296.  Byte-identical to corpus/counter-8bit.

Decision (PLAN.md X4): for every run, the -vv text must contain exactly the expected number of
"min entropy =" lines per block, none of them 'nan'/'inf', '-0' is recorded where it occurs
(it is a legitimate zero -- the question is whether the Assessed figure is also 0), and the
JSON must carry no literalEstimateNotRun / bitstringEstimateNotRun flag EXCEPT where a decline
is expected and explained (none of these files is a de Bruijn-type LRS decline).  A NaN at an
unguarded fold (MCV, Markov -- aggregation.md 2.2) would REPLACE the running minimum: the
assessed figure must equal the minimum of the printed estimates, recomputed by check_run.py.
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X4"
N = common.N_COMPLIANT


def generate() -> None:
    rows = common.read_manifest()

    alt1 = (np.arange(N, dtype=np.int64) & 1).astype(np.uint8)
    common.write_data_file("x4-alternating-1bit-1000000.bin", alt1, 1, EXPERIMENT,
                           "0,1,0,1,... (width 1): Collision sigma-hat = 0 exactly; byte-identical to "
                           "corpus/alternating-1bit-1000000.bin", __file__, rows)

    alt8 = (alt1 * 255).astype(np.uint8)
    common.write_data_file("x4-alternating-0-255-8bit-1000000.bin", alt8, 8, EXPERIMENT,
                           "0,255,0,255,... (width 8): two-valued, translated to {0,1}, binary branch; "
                           "byte-identical to corpus/alternating-8bit-1000000.bin", __file__, rows)

    bits = common.keystream_bits("x4-two-symbol", N)
    two = (bits * 255).astype(np.uint8)
    common.write_data_file("x4-two-symbol-0-255-random-8bit-1000000.bin", two, 8, EXPERIMENT,
                           "{0,255} from keystream bits 'x4-two-symbol' (P(0) = 1/2 exactly), width 8: "
                           "binary path through translation, non-degenerate control", __file__, rows)

    one1 = np.zeros(N, dtype=np.uint8)
    one1[500_000] = 1
    common.write_data_file("x4-one-symbol-once-1bit-1000000.bin", one1, 1, EXPERIMENT,
                           "999,999 zeros and one 1 at index 500000 (width 1): MCV p_u -> 1 (-0), "
                           "Markov P_{1,1} = 0, t-Tuple/LRS u,v ~ 500,000", __file__, rows)

    u = common.uniform_below("x4-one-symbol-once-8bit", N, 255)      # 0..254 exactly uniform
    assert u.max() <= 254
    u[500_000] = 255
    assert int((u == 255).sum()) == 1
    common.write_data_file("x4-one-symbol-once-8bit-1000000.bin", u, 8, EXPERIMENT,
                           "uniform on 0..254 (SHA-256 CTR 'x4-one-symbol-once-8bit', rejection of 255) with "
                           "255 at index 500000 only (width 8): 256 symbols, one of count 1", __file__, rows)

    ctr = (np.arange(N, dtype=np.int64) & 0xFF).astype(np.uint8)
    common.write_data_file("x4-counter-mod256-8bit-1000000.bin", ctr, 8, EXPERIMENT,
                           "i mod 256 (width 8): period 256, every tuple deterministic, predictors "
                           "P_global = 1; byte-identical to corpus/counter-8bit-1000000.bin", __file__, rows)


if __name__ == "__main__":
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
