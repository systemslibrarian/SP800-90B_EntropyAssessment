#!/usr/bin/env python3
"""x2_stuck_lsb_chain.py -- X2: a constant (stuck) LSB padding a PREDICTABLE bit stream, where the
spec-literal n x H_bitstring term can exceed the true conditional min-entropy (intake.md E2 / S2).

Two bit-level sources, each a stream of 7,000,000 "real" bits r_0, r_1, ... :

  A  lag-1 chain   r_0 uniform; P(r_t = r_{t-1}) = 9/10 exactly (the task's chain), the chain
                   running ACROSS symbol boundaries (bit 7 of sample t+1 follows bit 1 of sample t).
  B  lag-20 chain  r_0..r_19 uniform; P(r_t = r_{t-20}) = 9/10 exactly.  Same per-bit
                   predictability, but the dependence is 20 real bits back -- see "why B" below.

Each source is written two ways (1,000,000 samples each; the SAME 7,000,000 bits):
  *-packed7-1000000.bin   sample t = r_{7t} .. r_{7t+6} in bits 6..0 (MSB-first); bit 7 never set.
                          Run with width omitted -> the tool infers n = 7 and the bitstring is the
                          real bit stream.  Also run declared 8 (the F02 pair arm: pad bit FIRST).
  *-lsbpad-8bit-1000000.bin   the same byte << 1: real bits in 7..1, bit 0 = 0 (stuck LSB).  n = 8
                          whether inferred or declared; the bitstring is the real stream with a
                          constant 0 after every 7th real bit.
plus 20,000-sample prefixes of each for the light probes (non-compliant, EA_ALLOW_SHORT_DATASET=1).

THE TRUTH (stated here, computed below, written to x2-truth.json):
  per real bit, conditional on the past, the most likely value has probability 9/10 in both
  sources:  h_bit = -log2(0.9) = 0.1520031 bit.  A sample holds 7 real bits, so the conditional
  min-entropy per 7-bit (or padded 8-bit) sample is
        H_true = -log2(0.9^7) = 7 x 0.1520031 = 1.0640217 bits/sample
  (the padding bit is constant: it adds nothing).  The UNCONDITIONAL per-sample min-entropy is
  1.912 for A (p_max = 0.5 x 0.9^6, the all-equal byte) and 7.000 for B (the 7 bits of one sample
  sit in 7 different residue classes mod 20 and are marginally independent uniform).  The figure
  an entropy source assessment must not exceed is the CONDITIONAL one, 1.064: an attacker who
  knows the model and the past predicts each sample with probability 0.478.

WHY B ("a variant where H_original cannot bind"):
  For A the symbol-level estimators see the structure directly: P(byte_t = f(byte_{t-1})) =
  0.9^7 = 0.478 for the "continue the run" byte, so the Literal Lag-1 / MultiMMC depth-1 / MCV
  (p(0x00|0xFE) = 0.266) estimates all land at or below 1.06-1.9, and H_original binds the final
  figure at about the truth whatever the bitstring term does.  For B the dependence is on bits
  20 real positions back, i.e. on bits of samples t-3 and t-2 in SHIFTED positions: no symbol
  equals an earlier symbol more often than chance (Lag, MultiMCW), the depth-3 MMC/LZ78Y context
  space (128^3 = 2.1M contexts) cannot be learned from 1e6 samples before the 100,000-entry cap,
  and no tuple repeats (t-Tuple, LRS), so every Literal estimator sees near-uniform 7-bit bytes
  and H_original stays near 6.5-7.  The bit-level picture:
    - packed7 (bitstring = real stream): the Lag predictor's lag 20 is right 90 % of the time
      -> H_bitstring ~ 0.152, x7 = 1.06 = the truth.
    - lsbpad (one pad after every 7 real bits): a real-lag-20 pair sits 23 bitstring positions
      apart for 6 of every 7 real bits and 22 apart for the 7th (derivation below), so the best
      single lag (23) is right on 6/8 of all positions at 0.9 and guesses the rest at 0.5:
      accuracy 0.80 -> H_bitstring ~ 0.32, x8 = 2.57.  The depth-16 predictors (MultiMMC, LZ78Y)
      cannot reach 22-23 bits back; they learn only the pad phase ((1 + 7x0.5)/8 = 0.5625 ->
      0.83 x 8 = 6.6); MCV/Markov/Collision/Compression see a 56 % zero-heavy near-IID stream.
    So the expected (DERIVED, not measured) padded figure is min(H_original ~ 6.5, 8 x 0.32)
    ~ 2.57 > 1.064 = truth, while the 7-bit run gives ~ 1.06 <= truth.
  If measured so, the padded figure overstates the true min-entropy by ~2.4x on a construction
  that follows SP 800-90B 3.1.3 literally (n = 8, bitstring of the samples as stored) -- a
  property of the standard's n x H_bitstring term on a padded capture, NOT of the code; the
  py90b reference must agree with the tool on it (if it does not, THAT is the code finding).
  For A the derivation predicts the padded figure (MultiMMC/LZ78Y learn the pad phase and the
  lag-1 structure: (7x0.9 + 1)/8 = 0.9125 -> 0.1321 x 8 = 1.0567) stays just BELOW the truth by
  Jensen's inequality (-8 log2((7p+1)/8) <= -7 log2 p), with the 7-bit run binding lower
  (Collision on a 0.9-persistent stream, ~0.55): the decision there is the exact comparison.

Where the 23/22 comes from (lsbpad, MSB-first within the byte, pad last; utils.h builds the
bitstring MSB-first from word_size bits): real bit i = 7q + s (0 <= s <= 6) sits at padded
index 8q + s.  Its lag-20 partner i-20 = 7(q-3) + (s+1) for s <= 5 -> padded index 8(q-3)+s+1,
distance 23; for s = 6, i-20 = 7(q-2) -> padded index 8(q-2), distance 22.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X2"
N = common.N_COMPLIANT
NBITS = 7 * N
P_NUM, P_DEN = 225, 250          # P(same) = 225/250 = 9/10 exactly
PROBE = 20_000


def chain_lag1(label: str) -> np.ndarray:
    same = common.rational_bernoulli(label + "/same", NBITS, P_NUM, P_DEN)
    first = int(common.keystream_bits(label + "/init", 1)[0])
    # r_t = r_{t-1} XOR (not same_t)  => r_t = first XOR (number of flips among 1..t) mod 2
    flips = (~same).astype(np.uint8)
    flips[0] = 0
    r = (np.cumsum(flips, dtype=np.int64) & 1).astype(np.uint8) ^ first
    return r


def chain_lag20(label: str, lag: int = 20) -> np.ndarray:
    same = common.rational_bernoulli(label + "/same", NBITS, P_NUM, P_DEN)
    init = common.keystream_bits(label + "/init", lag)
    r = np.empty(NBITS, dtype=np.uint8)
    r[:lag] = init
    flips = (~same).astype(np.uint8)
    # each residue class mod `lag` is an independent lag-1 chain
    for c in range(lag):
        idx = np.arange(c, NBITS, lag)
        f = flips[idx].copy()
        f[0] = 0
        r[idx] = (np.cumsum(f, dtype=np.int64) & 1).astype(np.uint8) ^ int(init[c])
    return r


def pack7(bits: np.ndarray) -> np.ndarray:
    b = bits.reshape(-1, 7).astype(np.uint8)
    w = np.zeros(b.shape[0], dtype=np.uint8)
    for j in range(7):
        w |= (b[:, j] << (6 - j)).astype(np.uint8)
    return w


def truth() -> dict:
    p = P_NUM / P_DEN
    h_bit = -math.log2(p)
    h_true = 7 * h_bit
    ideal_padded = -8 * math.log2((7 * p + 1) / 8)
    lagB_acc = 0.75 * p + 0.25 * 0.5
    return {
        "P_same": p,
        "h_bit_conditional": h_bit,
        "H_true_conditional_per_sample": h_true,
        "H_marginal_per_sample_A_lag1": -math.log2(0.5 * p ** 6),
        "H_marginal_per_sample_B_lag20": 7.0,
        "ideal_phase_aware_predictor_on_padded_x8": ideal_padded,
        "jensen_check_ideal_padded_le_truth": ideal_padded <= h_true,
        "B_padded_best_single_lag": 23,
        "B_padded_lag23_accuracy": lagB_acc,
        "B_padded_lag23_entropy_x8_DERIVED": -8 * math.log2(lagB_acc),
        "B_packed7_lag20_entropy_x7_DERIVED": -7 * math.log2(p),
        "note": "DERIVED expectations, not measurements; the decision is the measured 'Assessed min entropy' "
                "of each run against H_true_conditional_per_sample and against the packed7 run.",
    }


def generate() -> None:
    rows = common.read_manifest()
    t = truth()
    with open(os.path.join(common.HERE, "x2-truth.json"), "w", encoding="utf-8") as f:
        json.dump(t, f, indent=1)
    print("truth:", json.dumps(t, indent=1))

    for tag, fn, desc in (("a-chain-lag1", chain_lag1, "lag-1 chain P(r_t = r_{t-1}) = 9/10 exactly"),
                          ("b-chain-lag20", chain_lag20, "lag-20 chain P(r_t = r_{t-20}) = 9/10 exactly")):
        bits = fn(f"x2{tag}")
        assert bits.shape[0] == NBITS
        same_frac = float((bits[1:] == bits[:-1]).mean()) if tag.startswith("a") else float((bits[20:] == bits[:-20]).mean())
        print(f"{tag}: measured P(same at its lag) = {same_frac:.6f}")
        w = pack7(bits)                       # 0..127, bit 7 never set
        assert w.max() <= 127
        common.write_data_file(
            f"x2{tag}-p09-packed7-1000000.bin", w, 0, EXPERIMENT,
            f"{desc}; 7 real bits per byte in bits 6..0 (MSB-first), bit 7 never set; truth (conditional) "
            f"{t['H_true_conditional_per_sample']:.7f} bits/sample; run width omitted (infers 7) and declared 8",
            __file__, rows)
        common.write_data_file(
            f"x2{tag}-p09-lsbpad-8bit-1000000.bin", (w.astype(np.uint16) << 1).astype(np.uint8), 8, EXPERIMENT,
            f"{desc}; the same bits in 7..1, bit 0 constant 0 (stuck LSB); n = 8 inferred or declared; "
            f"truth (conditional) {t['H_true_conditional_per_sample']:.7f} bits/sample",
            __file__, rows)
        common.write_data_file(
            f"x2{tag}-p09-packed7-prefix{PROBE}.bin", w[:PROBE], 0, EXPERIMENT,
            f"first {PROBE} samples of the packed7 file (light probe, non-compliant)", __file__, rows)
        common.write_data_file(
            f"x2{tag}-p09-lsbpad-8bit-prefix{PROBE}.bin", (w[:PROBE].astype(np.uint16) << 1).astype(np.uint8), 8,
            EXPERIMENT, f"first {PROBE} samples of the lsbpad file (light probe, non-compliant)", __file__, rows)


if __name__ == "__main__":
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
