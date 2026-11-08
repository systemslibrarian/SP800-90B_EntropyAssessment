"""
Tests for py90b.permutation -- SP 800-90B section 5.1, Permutation Testing.

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_permutation.py -v
(or   <venv>/bin/python reference/py90b/tests/test_permutation.py)

Every expected value below is either QUOTED from the standard (with the PDF
page) or derived BY HAND in the comment beside it.  Nothing is taken from the
C++ tool's output.  The module is imported as the package module
py90b.permutation (reference/ is put on sys.path) so that the worker pool can
unpickle its functions in a child process.
"""

from __future__ import annotations

import importlib
import itertools
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from fractions import Fraction

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
PKG_DIR = HERE.parent                    # .../reference/py90b
REFERENCE_DIR = PKG_DIR.parent           # .../reference
MOD_PATH = PKG_DIR / "permutation.py"

if str(REFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(REFERENCE_DIR))
perm = importlib.import_module("py90b.permutation")
bz2 = perm.bz2          # the stdlib bz2 the module itself resolved (see _import_bz2)


# --------------------------------------------------------------------------
# Deliberately un-vectorised transcriptions of sections 5.1.1 - 5.1.11, used
# to cross-check the numpy code.  Same definitions, written the slow way.
# --------------------------------------------------------------------------

def plain_excursion(S):
    """5.1.1 with exact rational arithmetic (returns a Fraction)."""
    L = len(S)
    xbar = Fraction(sum(S), L)
    running = 0
    best = Fraction(0)
    for i, s in enumerate(S, 1):
        running += s
        best = max(best, abs(running - i * xbar))
    return best


def plain_directional(S):
    return [-1 if S[i] > S[i + 1] else 1 for i in range(len(S) - 1)]


def plain_runs(seq):
    if not seq:
        return []
    runs = [1]
    for a, b in zip(seq, seq[1:]):
        if a == b:
            runs[-1] += 1
        else:
            runs.append(1)
    return runs


def plain_median(S):
    srt = sorted(S)
    L = len(S)
    return (srt[(L - 1) // 2] + srt[L // 2]) / 2


def plain_median_seq(S, med):
    return [-1 if s < med else 1 for s in S]


def plain_collisions(S):
    """5.1.7 step 3, literally: scan windows from i until a duplicate appears."""
    L = len(S)
    C = []
    i = 1
    while i < L:
        j = None
        for jj in range(2, L - i + 2):          # window (s_i .. s_{i+jj-1}) must fit in S
            window = S[i - 1 : i - 1 + jj]
            if len(set(window)) < len(window):
                j = jj
                break
        if j is None:
            break
        C.append(j)
        i += j
    return C


def plain_periodicity(S, p):
    return sum(1 for i in range(len(S) - p) if S[i] == S[i + p])


def plain_covariance(S, p):
    return sum(S[i] * S[i + p] for i in range(len(S) - p))


def plain_encode(S):
    return " ".join(str(s) for s in S).encode()


def plain_conv1(bits):
    b = list(bits) + [0] * ((-len(bits)) % 8)
    return [sum(b[k : k + 8]) for k in range(0, len(b), 8)]


def plain_conv2(bits):
    b = list(bits) + [0] * ((-len(bits)) % 8)
    return [int("".join(map(str, b[k : k + 8])), 2) for k in range(0, len(b), 8)]


class EnumeratingRNG:
    """An injectable 'RNG' whose successive shuffles are a fixed list of
    arrangements, so the counters can be checked against brute force."""

    def __init__(self, arrangements):
        self._it = iter(arrangements)

    def shuffle(self, arr):
        arr[:] = np.asarray(next(self._it), dtype=arr.dtype)


# ==========================================================================
# Conversions I and II -- section 5.1 (PDF p. 38)
# ==========================================================================

class TestConversions(unittest.TestCase):

    # "let the 20-bit input be (1,0,0,0,1,1,1,0,1,1,0,1,1,0,1,1,0,0,1,1)"
    BITS20 = [1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1]

    def test_conversion_I_spec_example(self):
        # "The first and the second eight-bit blocks include four and six ones,
        #  respectively.  The last block, which is not complete, includes two
        #  ones.  The output sequence is (4, 6, 2)."
        self.assertEqual(perm.conversion_I(self.BITS20).tolist(), [4, 6, 2])

    def test_conversion_II_spec_example(self):
        # "The integer values of the first two blocks are 142, and 219. ... the
        #  last block becomes (0,0,1,1,0,0,0,0) with an integer value of 48.
        #  The output sequence is (142, 219, 48)."
        self.assertEqual(perm.conversion_II(self.BITS20).tolist(), [142, 219, 48])
        # 142 = 1000 1110 read first-bit-most-significant: the block is big-endian.
        self.assertEqual(perm.conversion_II([1, 0, 0, 0, 0, 0, 0, 0]).tolist(), [128])
        self.assertEqual(perm.conversion_II([0, 0, 0, 0, 0, 0, 0, 1]).tolist(), [1])

    def test_padding_and_edges(self):
        # exactly 8 bits: one block, no padding
        self.assertEqual(perm.conversion_I([1] * 8).tolist(), [8])
        self.assertEqual(perm.conversion_II([1] * 8).tolist(), [255])
        # 9 bits: second block is (1,0,0,0,0,0,0,0) after zero padding
        self.assertEqual(perm.conversion_I([1] * 9).tolist(), [8, 1])
        self.assertEqual(perm.conversion_II([1] * 9).tolist(), [255, 128])
        # empty input: no blocks
        self.assertEqual(perm.conversion_I([]).tolist(), [])
        self.assertEqual(perm.conversion_II([]).tolist(), [])

    def test_only_bits_accepted(self):
        with self.assertRaises(ValueError):
            perm.conversion_I([0, 1, 2])
        with self.assertRaises(ValueError):
            perm.conversion_II([0, 1, 2])

    def test_against_plain_transcription(self):
        rng = random.Random(5)
        for _ in range(30):
            bits = [rng.randrange(2) for _ in range(rng.randrange(0, 70))]
            self.assertEqual(perm.conversion_I(bits).tolist(), plain_conv1(bits))
            self.assertEqual(perm.conversion_II(bits).tolist(), plain_conv2(bits))


# ==========================================================================
# The spec's worked examples, sections 5.1.1 - 5.1.10 (PDF pp. 39-43)
# ==========================================================================

class TestWorkedExamples(unittest.TestCase):

    def test_example_1_excursion(self):
        # "Let the input sequence be S = (2, 15, 4, 10, 9). The average of the
        #  sample values is 8, and d1 = |2-8| = 6; d2 = |(2+15) - (2x8)| = 1;
        #  d3 = |(2+15+4) - (3x8)| = 3; d4 = |(2+15+4+10) - (4x8)| = 1; and
        #  d5 = |(2+15+4+10+9) - (5x8)| = 0. Then, T = max(6, 1, 3, 1, 0) = 6."
        S = [2, 15, 4, 10, 9]
        self.assertEqual(sum(S) / len(S), 8)
        self.assertEqual(perm.excursion(S), 6)
        self.assertEqual(plain_excursion(S), Fraction(6))

    S_EX2 = [2, 2, 2, 5, 7, 7, 9, 3, 1, 4, 4]
    # "then S' = (+1, +1, +1, +1, +1, +1, -1, -1, +1, +1)"
    S_PRIME = [1, 1, 1, 1, 1, 1, -1, -1, 1, 1]

    def test_directional_sequence_of_examples_2_to_4(self):
        self.assertEqual(perm._directional_sequence(self.S_EX2).tolist(), self.S_PRIME)
        self.assertEqual(plain_directional(self.S_EX2), self.S_PRIME)

    def test_example_2_number_of_directional_runs(self):
        # "There are three runs: (+1, +1, +1, +1, +1, +1), (-1, -1) and (+1, +1), so T = 3."
        self.assertEqual(perm.num_directional_runs(self.S_EX2), 3)

    def test_example_3_length_of_directional_runs(self):
        # same runs; "so T = 6"
        self.assertEqual(perm.len_directional_runs(self.S_EX2), 6)

    def test_example_4_increases_and_decreases(self):
        # "There are eight +1's and two -1's in S', so T = max (8, 2) = 8."
        self.assertEqual(perm.num_increases_decreases(self.S_EX2), 8)

    S_EX5 = [5, 15, 12, 1, 13, 9, 4]

    def test_example_5_number_of_runs_based_on_median(self):
        # "The median of the input sequence is 9. Then, S' = (-1, +1, +1, -1, +1,
        #  +1, -1). The runs are (-1), (+1, +1), (-1), (+1, +1), and (-1). There
        #  are five runs, hence T = 5."
        self.assertEqual(perm.median_of(self.S_EX5), 9)
        self.assertEqual(perm._median_sequence(self.S_EX5, 9).tolist(), [-1, 1, 1, -1, 1, 1, -1])
        self.assertEqual(perm.num_runs_median(self.S_EX5), 5)
        for rule in ("mean", "lower", "upper"):        # odd L: every median rule gives 9
            self.assertEqual(perm.median_of(self.S_EX5, rule), 9)

    def test_example_6_length_of_runs_based_on_median(self):
        # "The longest run has a length of 2; hence, T = 2."
        self.assertEqual(perm.len_runs_median(self.S_EX5), 2)

    S_EX7 = [2, 1, 1, 2, 0, 1, 0, 1, 1, 2]

    def test_example_7_average_collision(self):
        # "The first collision occurs for j = 3 ... Then, the first three samples
        #  are discarded, and the next sequence to be examined is (2, 0, 1, 0, 1,
        #  1, 2). The collision occurs for j = 4. The third sequence to be examined
        #  is (1,1,2), and the collision occurs for j = 2. There are no collisions
        #  in the final sequence (2). Hence, C = [3,4,2]. The average of the
        #  values in C is T = 3."
        self.assertEqual(perm.collision_list(self.S_EX7), [3, 4, 2])
        self.assertEqual(plain_collisions(self.S_EX7), [3, 4, 2])
        self.assertEqual(perm.avg_collision(self.S_EX7), 3)

    def test_example_8_maximum_collision(self):
        # "C = [3,4,2] is computed as in Example 7. T = max(3,4,2) = 4."
        self.assertEqual(perm.max_collision(self.S_EX7), 4)

    def test_example_9_periodicity(self):
        # "Let the input data be (2, 1, 2, 1, 0, 1, 0, 1, 1, 2), and let p = 2.
        #  Since si = si+p for five values of i (1, 2, 4, 5 and 6), T = 5."
        S = [2, 1, 2, 1, 0, 1, 0, 1, 1, 2]
        self.assertEqual(perm.periodicity(S, 2), 5)
        self.assertEqual([i for i in range(1, 9) if S[i - 1] == S[i + 1]], [1, 2, 4, 5, 6])

    def test_example_10_covariance(self):
        # "Let the input data be (5, 2, 6, 10, 12, 3, 1), and let p be 2. T is
        #  calculated as (5x6) + (2x10) + (6x12) + (10x3) + (12x1) = 164."
        self.assertEqual(perm.covariance([5, 2, 6, 10, 12, 3, 1], 2), 164)
        self.assertEqual(5 * 6 + 2 * 10 + 6 * 12 + 10 * 3 + 12 * 1, 164)

    def test_compression_encoding_example(self):
        # 5.1.11 step 1: "'S = (144, 21, 139, 0, 0, 15)' becomes '144 21 139 0 0 15'"
        S = [144, 21, 139, 0, 0, 15]
        self.assertEqual(perm.encode_for_compression(S), b"144 21 139 0 0 15")
        self.assertEqual(perm.encode_for_compression(np.array(S, dtype=np.uint8)), b"144 21 139 0 0 15")
        # Step 2/3: bzip2 of that string, length in bytes -- the definition itself.
        self.assertEqual(perm.compression(S), len(bz2.compress(b"144 21 139 0 0 15", 9)))
        # bzip2 streams start with the magic "BZh" + level digit
        self.assertTrue(bz2.compress(b"144 21 139 0 0 15", 9).startswith(b"BZh9"))


# ==========================================================================
# Hand-derived cases, including the degenerate one-symbol input
# ==========================================================================

class TestDegenerateAllOneSymbol(unittest.TestCase):

    def test_statistics_of_a_constant_sequence(self):
        # S = (5, 5, ..., 5), L = 100, bits_per_symbol = 3; k = 1 so NOT binary.
        L, v = 100, 5
        S = [v] * L
        # 5.1.1: X-bar = 5, every partial sum is 5i, so every d_i = 0 -> T = 0
        self.assertEqual(perm.excursion(S), 0)
        # 5.1.2-5.1.4: s_i <= s_{i+1} always, S' = 99 times +1 -> 1 run, longest 99, max(0, 99) = 99
        self.assertEqual(perm.num_directional_runs(S), 1)
        self.assertEqual(perm.len_directional_runs(S), 99)
        self.assertEqual(perm.num_increases_decreases(S), 99)
        # 5.1.5-5.1.6: median 5, every s_i >= 5 -> S' = 100 times +1 -> 1 run of length 100
        self.assertEqual(perm.median_of(S), 5)
        self.assertEqual(perm.num_runs_median(S), 1)
        self.assertEqual(perm.len_runs_median(S), 100)
        # 5.1.7-5.1.8: from i = 1 the window (5, 5) already repeats, j = 2; i -> 3, 5, ..., 99;
        # at i = 99 < 100 the window (s99, s100) gives j = 2; then i = 101 ends the loop.
        # C = [2] * 50 -> average 2, maximum 2
        self.assertEqual(perm.collision_list(S), [2] * 50)
        self.assertEqual(perm.avg_collision(S), 2)
        self.assertEqual(perm.max_collision(S), 2)
        # 5.1.9: every pair (s_i, s_{i+p}) matches: T = L - p
        for p in perm.LAGS:
            self.assertEqual(perm.periodicity(S, p), L - p)
            # 5.1.10: (L - p) products of 5*5 = 25
            self.assertEqual(perm.covariance(S, p), (L - p) * 25)
        # 5.1.11: by definition
        self.assertEqual(perm.compression(S), len(bz2.compress(b" ".join([b"5"] * L), 9)))

    def test_constant_sequence_passes_the_battery_by_ties(self):
        # Every permutation of a constant sequence IS the sequence, so for every
        # statistic T = Ti on every shuffle: Ci,0 = 0 and Ci,1 = shuffles.
        # Figure 4 step 3 with 40 shuffles (cutoffs (0, 40)): 0 + 40 <= 0 is false,
        # 0 >= 40 is false -> no test rejects -> "assume that the noise source
        # outputs are IID".  (A constant source is trivially IID; the chi-square
        # tests of 5.2, not this module, are what would fail it.)
        r = perm.permutation_test([5] * 100, 3, shuffles=40, seed=0)
        self.assertFalse(r["binary"])
        self.assertEqual(r["k"], 1)
        self.assertEqual(r["undefined_statistics"], [])
        for name, t in r["tests"].items():
            self.assertEqual((t["C0"], t["C1"]), (0, 40), name)
            self.assertTrue(t["passed"], name)
            self.assertEqual(t["perm_min"], t["T"], name)
            self.assertEqual(t["perm_max"], t["T"], name)
        self.assertTrue(r["iid_assumption"])
        self.assertEqual(r["failed_tests"], [])
        self.assertTrue(math.isnan(r["min_entropy"]))
        # and at the normative 10 000 the same counters (0, 10000) pass too:
        self.assertFalse(perm.test_rejects(0, 10000))

    def test_short_constant_sequence_has_undefined_lags_and_is_rejected(self):
        # L = 10 < 16: periodicity/covariance at p = 16 and 32 have no value
        # (the definition needs p < L), so those statistics are nan on the
        # original AND on every permutation.  nan compares False both ways, the
        # counters stay (0, 0), 0 + 0 <= 5 holds, and Figure 4 step 3 rejects.
        # This is the literal consequence of the text for an input far below
        # the 1 000 000 samples section 3.1.1 requires; it is recorded, not fudged.
        r = perm.permutation_test([5] * 10, 3, shuffles=20, seed=0)
        self.assertEqual(
            r["undefined_statistics"],
            ["periodicity(16)", "periodicity(32)", "covariance(16)", "covariance(32)"],
        )
        for name in r["undefined_statistics"]:
            self.assertTrue(math.isnan(r[name]))
            self.assertEqual((r["tests"][name]["C0"], r["tests"][name]["C1"]), (0, 0))
            self.assertFalse(r["tests"][name]["passed"])
        self.assertFalse(r["iid_assumption"])
        self.assertEqual(sorted(r["failed_tests"]), sorted(r["undefined_statistics"]))

    def test_all_ones_bits_under_both_binary_readings(self):
        # 64 one-bits, bits_per_symbol = 1.  k = 1, so the literal "binary, i.e.,
        # k = 2" says NOT binary; binary_mode='width' says binary.
        S = [1] * 64
        a = perm.permutation_test(S, 1, shuffles=5, seed=0, binary_mode="alphabet")
        w = perm.permutation_test(S, 1, shuffles=5, seed=0, binary_mode="width")
        self.assertFalse(a["binary"])
        self.assertTrue(w["binary"])
        self.assertIsNone(w["bit_one_value"])                # the data already is 0/1
        # alphabet reading, on the 64 raw bits: S' = 63 times +1 -> 1 run of length 63
        self.assertEqual(a["numDirectionalRuns"], 1)
        self.assertEqual(a["lenDirectionalRuns"], 63)
        # width reading, on Conversion I = eight blocks of 8 ones = (8,8,8,8,8,8,8,8):
        # S' = 7 times +1 -> 1 run of length 7; Conversion II = eight 255s -> collisions [2,2,2,2]
        self.assertEqual(w["numDirectionalRuns"], 1)
        self.assertEqual(w["lenDirectionalRuns"], 7)
        self.assertEqual(w["conversion_I_blocks"], 8)
        self.assertEqual(w["avgCollision"], 2)
        self.assertEqual(w["maxCollision"], 2)
        # alphabet reading collisions on raw bits: 32 windows of (1,1) -> [2]*32
        self.assertEqual(a["avgCollision"], 2)
        # periodicity(1): width -> 7 matching block pairs; alphabet -> 63 matching bit pairs
        self.assertEqual(w["periodicity(1)"], 7)
        self.assertEqual(a["periodicity(1)"], 63)
        # median runs: binary rule (0.5) on the bits vs computed median 1 on raw bits --
        # both give one run of 64 here
        self.assertEqual(w["numRunsMedian"], 1)
        self.assertEqual(a["numRunsMedian"], 1)
        self.assertEqual(w["lenRunsMedian"], 64)
        self.assertEqual(a["lenRunsMedian"], 64)


class TestHandDerivedSmallInputs(unittest.TestCase):

    def test_two_bit_sequence(self):
        # S = (3, 0, 2, 2, 1, 3, 0, 1), bits_per_symbol = 2, L = 8, k = 4 (not binary)
        S = [3, 0, 2, 2, 1, 3, 0, 1]
        # 5.1.1: sum = 12, X-bar = 1.5; partial sums 3,3,5,7,8,11,11,12;
        #        i*X-bar = 1.5,3,4.5,6,7.5,9,10.5,12; |diff| = 1.5,0,0.5,1,0.5,2,0.5,0 -> T = 2
        self.assertEqual(perm.excursion(S), 2.0)
        # 5.1.2-4: pairs (3,0)-,(0,2)+,(2,2)+,(2,1)-,(1,3)+,(3,0)-,(0,1)+ -> S' = (-,+,+,-,+,-,+)
        #        runs: (-),(+,+),(-),(+),(-),(+) = 6 runs; longest 2; #+ = 4, #- = 3 -> 4
        self.assertEqual(perm._directional_sequence(S).tolist(), [-1, 1, 1, -1, 1, -1, 1])
        self.assertEqual(perm.num_directional_runs(S), 6)
        self.assertEqual(perm.len_directional_runs(S), 2)
        self.assertEqual(perm.num_increases_decreases(S), 4)
        # 5.1.5-6: sorted 0,0,1,1,2,2,3,3 -> median (1+2)/2 = 1.5;
        #        S' = (3>=1.5 +, 0 -, 2 +, 2 +, 1 -, 3 +, 0 -, 1 -) = (+,-,+,+,-,+,-,-)
        #        runs (+),(-),(+,+),(-),(+),(-,-) = 6; longest 2
        self.assertEqual(perm.median_of(S), 1.5)
        self.assertEqual(perm.num_runs_median(S), 6)
        self.assertEqual(perm.len_runs_median(S), 2)
        # 5.1.7-8: i=1: (3),(3,0),(3,0,2),(3,0,2,2) -> j=4; i=5: (1),(1,3),(1,3,0),(1,3,0,1) -> j=4;
        #        i=9: 9 < 8 false -> C = [4, 4] -> avg 4, max 4
        self.assertEqual(perm.collision_list(S), [4, 4])
        self.assertEqual(perm.avg_collision(S), 4)
        self.assertEqual(perm.max_collision(S), 4)
        # 5.1.9: p=1: pairs (3,0),(0,2),(2,2)*,(2,1),(1,3),(3,0),(0,1) -> 1
        #        p=2: (3,2),(0,2),(2,1),(2,3),(1,0),(3,1) -> 0;  p=8: p < L fails -> nan
        self.assertEqual(perm.periodicity(S, 1), 1)
        self.assertEqual(perm.periodicity(S, 2), 0)
        self.assertTrue(math.isnan(perm.periodicity(S, 8)))
        # 5.1.10: p=1: 0+0+4+2+3+0+0 = 9 ; p=2: 6+0+2+6+0+3 = 17
        self.assertEqual(perm.covariance(S, 1), 9)
        self.assertEqual(perm.covariance(S, 2), 17)

    def test_even_length_median_rules_differ_materially(self):
        # S = (1, 3, 5, 7): mean rule -> (3+5)/2 = 4 -> S' = (-,-,+,+): 2 runs, longest 2
        #                   lower rule -> 3         -> S' = (-,+,+,+): 2 runs, longest 3
        #                   upper rule -> 5         -> S' = (-,-,+,+): 2 runs, longest 2
        S = [1, 3, 5, 7]
        self.assertEqual(perm.median_of(S, "mean"), 4)
        self.assertEqual(perm.median_of(S, "lower"), 3)
        self.assertEqual(perm.median_of(S, "upper"), 5)
        self.assertEqual(perm.len_runs_median(S, median_rule="mean"), 2)
        self.assertEqual(perm.len_runs_median(S, median_rule="lower"), 3)
        self.assertEqual(perm.len_runs_median(S, median_rule="upper"), 2)
        with self.assertRaises(ValueError):
            perm.median_of(S, "mode")

    def test_no_collision_gives_no_value(self):
        # all distinct: step 3a finds no j at i = 1 -> break -> C empty -> no average / maximum
        S = [4, 1, 7, 2]
        self.assertEqual(perm.collision_list(S), [])
        self.assertTrue(math.isnan(perm.avg_collision(S)))
        self.assertTrue(math.isnan(perm.max_collision(S)))
        # a collision only at the very end: (4,1,7,2,7): i=1 -> window of 5 holds 7 twice, j = 5
        self.assertEqual(perm.collision_list([4, 1, 7, 2, 7]), [5])
        # a trailing distinct tail after a collision: (1,1,2,3): i=1 -> j=2; i=3 < 4 -> (2,3) no j -> break
        self.assertEqual(perm.collision_list([1, 1, 2, 3]), [2])

    def test_empty_and_single_sample(self):
        self.assertTrue(math.isnan(perm.excursion([])))
        self.assertEqual(perm.excursion([9]), 0)              # d1 = |9 - 1*9| = 0
        self.assertEqual(perm.num_directional_runs([9]), 0)   # S' empty
        self.assertTrue(math.isnan(perm.len_directional_runs([9])))
        self.assertEqual(perm.num_increases_decreases([9]), 0)
        self.assertEqual(perm.num_runs_median([9]), 1)        # S' = (+1)
        self.assertEqual(perm.len_runs_median([9]), 1)
        self.assertEqual(perm.collision_list([9]), [])
        self.assertTrue(math.isnan(perm.periodicity([9], 1)))
        self.assertTrue(math.isnan(perm.covariance([9], 1)))
        self.assertEqual(perm.encode_for_compression([]), b"")


# ==========================================================================
# The counting / ranking rule -- Figure 4 steps 2.2.2 and 3 (PDF p. 37)
# ==========================================================================

class TestCountingRule(unittest.TestCase):

    def test_cutoffs(self):
        # "If ((Ci,0+Ci,1 <= 5) or (Ci,0 >= 9995)) for any i, reject"
        self.assertEqual(perm.cutoffs(10000), (5, 9995))
        self.assertEqual(perm.SHUFFLES, 10000)
        # scaled convenience for short runs (not normative): 5/10000 of N, floored
        self.assertEqual(perm.cutoffs(40), (0, 40))
        self.assertEqual(perm.cutoffs(2000), (1, 1999))
        self.assertEqual(perm.cutoffs(20000), (10, 19990))
        with self.assertRaises(ValueError):
            perm.cutoffs(0)

    def test_counter_update(self):
        # "If (T > Ti), increment Ci,0. If (T = Ti), increment Ci,1."
        self.assertEqual(perm.counter_update(3, 5, 0, 0), (1, 0))      # T > Ti
        self.assertEqual(perm.counter_update(3, 3, 1, 0), (1, 1))      # T = Ti
        self.assertEqual(perm.counter_update(3, 1, 1, 1), (1, 1))      # T < Ti: nothing
        self.assertEqual(perm.counter_update(3.0, 3, 0, 0), (0, 1))    # int/float equality
        nan = float("nan")
        self.assertEqual(perm.counter_update(nan, 3, 0, 0), (0, 0))    # undefined original
        self.assertEqual(perm.counter_update(3, nan, 0, 0), (0, 0))    # undefined permuted
        self.assertEqual(perm.counter_update(nan, nan, 0, 0), (0, 0))  # both undefined

    def test_figure4_rule_at_the_boundaries(self):
        rej = perm.test_rejects
        self.assertTrue(rej(0, 5))        # 0 + 5 <= 5
        self.assertTrue(rej(5, 0))        # 5 + 0 <= 5
        self.assertTrue(rej(3, 2))        # 3 + 2 <= 5
        self.assertFalse(rej(0, 6))       # 6 > 5 and 0 < 9995
        self.assertFalse(rej(3, 3))
        self.assertTrue(rej(9995, 0))     # 9995 >= 9995
        self.assertTrue(rej(9995, 5))
        self.assertTrue(rej(10000, 0))
        self.assertFalse(rej(9994, 0))    # 9994 > 5 and 9994 < 9995
        self.assertFalse(rej(9994, 6))    # sum 10000, C0 below the cutoff
        self.assertFalse(rej(5000, 0))

    def test_prose_rule_differs_only_at_equality(self):
        # p. 38: "If the sum of Ci,0 and Ci,1 is less than 5 ... if Ci,0 is greater than 9995"
        rej = perm.test_rejects
        self.assertFalse(rej(0, 5, rule="prose"))      # 5 is not "less than 5"
        self.assertTrue(rej(0, 4, rule="prose"))
        self.assertFalse(rej(9995, 0, rule="prose"))   # 9995 is not "greater than 9995"
        self.assertTrue(rej(9996, 0, rule="prose"))
        # everywhere else the two readings agree
        for c0 in (0, 1, 4, 6, 100, 9000, 9994, 9996, 10000):
            for c1 in (0, 1, 3, 6, 50):
                if c0 + c1 != 5 and c0 != 9995:
                    self.assertEqual(rej(c0, c1), rej(c0, c1, rule="prose"), (c0, c1))
        with self.assertRaises(ValueError):
            rej(0, 0, rule="figure5")

    def test_iid_decision_any_test_rejects(self):
        counters = {"a": (100, 3), "b": (0, 6), "c": (9994, 0)}
        iid, passed = perm.iid_decision(counters)
        self.assertTrue(iid)
        self.assertEqual(passed, {"a": True, "b": True, "c": True})
        counters["b"] = (0, 5)                                  # one test at the cutoff
        iid, passed = perm.iid_decision(counters)
        self.assertFalse(iid)
        self.assertEqual(passed, {"a": True, "b": False, "c": True})
        self.assertTrue(perm.iid_decision(counters, rule="prose")[0])   # prose: 5 is not < 5
        self.assertTrue(perm.iid_decision({}, 10000)[0])        # vacuous: no test rejects


# ==========================================================================
# The Fisher-Yates shuffle -- Figure 5 (PDF p. 38)
# ==========================================================================

class TestFisherYates(unittest.TestCase):

    def test_figure5_transcription_is_a_bijection_onto_the_permutations(self):
        # Figure 5 draws j_i in [1, i] for i = L..1.  Over ALL choice sequences
        # (L! of them) the transcription must produce every permutation exactly
        # once -- that is what makes the shuffle uniform when the j are uniform.
        for L in (1, 2, 3, 4, 5):
            seen = Counter()
            for choices in itertools.product(*[range(1, i + 1) for i in range(L, 0, -1)]):
                it = iter(choices)
                out = perm.fisher_yates_shuffle(list(range(L)), lambda i: next(it))
                seen[tuple(out)] += 1
            self.assertEqual(len(seen), math.factorial(L))
            self.assertEqual(set(seen.values()), {1})
            self.assertEqual(set(seen), set(itertools.permutations(range(L))))

    def test_figure5_rejects_an_out_of_range_j(self):
        with self.assertRaises(ValueError):
            perm.fisher_yates_shuffle([1, 2, 3], lambda i: i + 1)
        with self.assertRaises(ValueError):
            perm.fisher_yates_shuffle([1, 2, 3], lambda i: 0)

    def test_python_fisher_yates_is_a_permutation_and_is_seeded(self):
        a = np.arange(50)
        x = a.copy()
        perm.PythonFisherYates(3).shuffle(x)
        self.assertEqual(sorted(x.tolist()), list(range(50)))
        self.assertNotEqual(x.tolist(), list(range(50)))
        y = a.copy()
        perm.PythonFisherYates(3).shuffle(y)
        self.assertEqual(x.tolist(), y.tolist())

    def test_numpy_generator_shuffle_is_uniform_over_S4(self):
        # The production shuffle.  24 000 shuffles of (0,1,2,3) with a fixed seed:
        # each of the 24 permutations is expected 1000 times (sd ~ 31).  A biased
        # or non-Fisher-Yates shuffle (e.g. the classic "swap with any index"
        # error) shows deviations of several hundred here.
        g = np.random.default_rng(12345)
        seen = Counter()
        base = np.arange(4)
        for _ in range(24_000):
            x = base.copy()
            g.shuffle(x)
            seen[tuple(x.tolist())] += 1
        self.assertEqual(len(seen), 24)
        chi2 = sum((n - 1000) ** 2 / 1000 for n in seen.values())
        self.assertLess(chi2, 70)                       # df = 23; 99.99th percentile ~ 55
        self.assertLess(max(abs(n - 1000) for n in seen.values()), 150)

    def test_per_shuffle_streams_are_deterministic_and_distinct(self):
        g0 = perm._generator_for_shuffle(42, 0)
        g0b = perm._generator_for_shuffle(42, 0)
        g1 = perm._generator_for_shuffle(42, 1)
        a, b, c = (np.arange(20) for _ in range(3))
        g0.shuffle(a)
        g0b.shuffle(b)
        g1.shuffle(c)
        self.assertEqual(a.tolist(), b.tolist())
        self.assertNotEqual(a.tolist(), c.tolist())


# ==========================================================================
# The counters, checked exhaustively against brute force
# ==========================================================================

class TestCountersExhaustive(unittest.TestCase):

    def test_four_distinct_symbols_all_24_permutations(self):
        # S = (3, 1, 4, 2), 3-bit symbols, k = 4 (not binary).  Feed the driver
        # every permutation once as its 24 "shuffles" and check every counter
        # against a brute-force count over the same 24 arrangements computed
        # with the plain transcriptions.
        S = [3, 1, 4, 2]
        arrangements = list(itertools.permutations(S))
        r = perm.permutation_test(S, 3, shuffles=24, rng=EnumeratingRNG(arrangements))
        self.assertEqual(r["rng"], "injected")
        self.assertIsNone(r["seed_entropy"])
        med = plain_median(S)

        def stats(X):
            X = list(X)
            C = plain_collisions(X)
            d = plain_directional(X)
            m = plain_median_seq(X, med)
            out = {
                "excursion": plain_excursion(X),
                "numDirectionalRuns": len(plain_runs(d)),
                "lenDirectionalRuns": max(plain_runs(d)),
                "numIncreasesDecreases": max(d.count(-1), d.count(1)),
                "numRunsMedian": len(plain_runs(m)),
                "lenRunsMedian": max(plain_runs(m)),
                "avgCollision": Fraction(sum(C), len(C)) if C else None,
                "maxCollision": max(C) if C else None,
                "compression": len(bz2.compress(plain_encode(X), 9)),
            }
            for p in perm.LAGS:
                out[f"periodicity({p})"] = plain_periodicity(X, p) if p < len(X) else None
                out[f"covariance({p})"] = plain_covariance(X, p) if p < len(X) else None
            return out

        orig = stats(S)
        for name in perm.statistic_names():
            t = r["tests"][name]
            if orig[name] is None:                      # lags 8, 16, 32 have no value at L = 4
                self.assertFalse(t["defined"], name)
                self.assertEqual((t["C0"], t["C1"]), (0, 0), name)
                continue
            c0 = sum(1 for X in arrangements if stats(X)[name] > orig[name])
            c1 = sum(1 for X in arrangements if stats(X)[name] == orig[name])
            self.assertEqual((t["C0"], t["C1"]), (c0, c1), name)
            self.assertGreaterEqual(c1, 1, name)        # the identity permutation is among the 24
            # the original statistic agrees with the plain transcription
            if isinstance(orig[name], Fraction):
                self.assertEqual(t["T"], float(orig[name]), name)
            else:
                self.assertEqual(t["T"], orig[name], name)

    def test_binary_twelve_bits_all_distinct_arrangements(self):
        # bits with six ones and six zeros (k = 2 -> binary, conversions apply).
        # All C(12,6) = 924 distinct arrangements are fed as the shuffles.  The
        # brute force applies Conversion I / II with the plain transcriptions,
        # the median rule 0.5 to the raw bits, and compression to the raw bits.
        S = [1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1]
        arrangements = []
        for ones in itertools.combinations(range(12), 6):
            arrangements.append(tuple(1 if i in ones else 0 for i in range(12)))
        self.assertEqual(len(arrangements), 924)
        self.assertIn(tuple(S), arrangements)
        r = perm.permutation_test(S, 1, shuffles=924, rng=EnumeratingRNG(arrangements))
        self.assertTrue(r["binary"])
        self.assertEqual(r["k"], 2)
        self.assertEqual(r["conversion_I_blocks"], 2)

        def stats(X):
            X = list(X)
            c1 = plain_conv1(X)
            c2 = plain_conv2(X)
            C = plain_collisions(c2)
            d = plain_directional(c1)
            m = plain_median_seq(X, 0.5)
            out = {
                "excursion": plain_excursion(X),
                "numDirectionalRuns": len(plain_runs(d)),
                "lenDirectionalRuns": max(plain_runs(d)) if d else None,
                "numIncreasesDecreases": max(d.count(-1), d.count(1)),
                "numRunsMedian": len(plain_runs(m)),
                "lenRunsMedian": max(plain_runs(m)),
                "avgCollision": Fraction(sum(C), len(C)) if C else None,
                "maxCollision": max(C) if C else None,
                "compression": len(bz2.compress(plain_encode(X), 9)),
            }
            for p in perm.LAGS:
                out[f"periodicity({p})"] = plain_periodicity(c1, p) if p < len(c1) else None
                out[f"covariance({p})"] = plain_covariance(c1, p) if p < len(c1) else None
            return out

        orig = stats(S)
        # two blocks: only lag 1 is defined for the conversion-I tests; no block repeats
        # unless the two 8-bit values coincide, so collisions are usually undefined
        self.assertIsNone(orig["periodicity(2)"])
        for name in perm.statistic_names():
            t = r["tests"][name]
            if orig[name] is None:
                self.assertFalse(t["defined"], name)
                self.assertEqual((t["C0"], t["C1"]), (0, 0), name)
                continue
            c0 = c1 = 0
            for X in arrangements:
                v = stats(X)[name]
                if v is None:
                    continue
                if v > orig[name]:
                    c0 += 1
                elif v == orig[name]:
                    c1 += 1
            self.assertEqual((t["C0"], t["C1"]), (c0, c1), name)
            if isinstance(orig[name], Fraction):
                self.assertEqual(t["T"], float(orig[name]), name)
            else:
                self.assertEqual(t["T"], orig[name], name)


# ==========================================================================
# Vectorised code against the plain transcriptions, random inputs
# ==========================================================================

class TestVectorisedAgainstPlain(unittest.TestCase):

    def test_statistics_match_plain_transcriptions(self):
        rng = random.Random(2026_11_07)
        for trial in range(60):
            bps = rng.choice([1, 2, 3, 4, 8])
            L = rng.randrange(2, 300)
            skew = rng.choice([0.0, 0.5, 0.9])
            S = [0 if rng.random() < skew else rng.randrange(1 << bps) for _ in range(L)]
            with self.subTest(trial=trial, bps=bps, L=L):
                # 5.1.1: our int-scaled maximum / L is the correctly rounded exact value,
                # and float(Fraction) is also correctly rounded -> bit-for-bit equal
                self.assertEqual(perm.excursion(S), float(plain_excursion(S)))
                d = plain_directional(S)
                self.assertEqual(perm.num_directional_runs(S), len(plain_runs(d)))
                self.assertEqual(perm.len_directional_runs(S), max(plain_runs(d)))
                self.assertEqual(perm.num_increases_decreases(S), max(d.count(-1), d.count(1)))
                med = plain_median(S)
                self.assertEqual(perm.median_of(S), med)
                m = plain_median_seq(S, med)
                self.assertEqual(perm.num_runs_median(S), len(plain_runs(m)))
                self.assertEqual(perm.len_runs_median(S), max(plain_runs(m)))
                C = plain_collisions(S)
                self.assertEqual(perm.collision_list(S), C)
                if C:
                    self.assertEqual(perm.avg_collision(S), float(Fraction(sum(C), len(C))))
                    self.assertEqual(perm.max_collision(S), max(C))
                else:
                    self.assertTrue(math.isnan(perm.avg_collision(S)))
                for p in perm.LAGS:
                    if p < L:
                        self.assertEqual(perm.periodicity(S, p), plain_periodicity(S, p))
                        self.assertEqual(perm.covariance(S, p), plain_covariance(S, p))
                    else:
                        self.assertTrue(math.isnan(perm.periodicity(S, p)))
                        self.assertTrue(math.isnan(perm.covariance(S, p)))
                self.assertEqual(perm.encode_for_compression(S), plain_encode(S))
                self.assertEqual(perm.compression(S), len(bz2.compress(plain_encode(S), 9)))

    def test_encoding_fast_path_equals_generic_path(self):
        rng = random.Random(9)
        vals = [rng.randrange(256) for _ in range(5000)]
        fast = perm.encode_for_compression(np.array(vals, dtype=np.uint8))
        generic = perm.encode_for_compression(np.array(vals, dtype=np.int64))
        self.assertEqual(fast, generic)
        self.assertEqual(fast, plain_encode(vals))
        self.assertFalse(fast.startswith(b" "))
        self.assertFalse(fast.endswith(b" "))
        self.assertNotIn(b"\0", fast)
        self.assertNotIn(b"  ", fast)

    def test_bz2_level_changes_only_the_compression_statistic(self):
        rng = random.Random(10)
        S = [rng.randrange(256) for _ in range(3000)]
        for level in (1, 9):
            self.assertEqual(perm.compression(S, level), len(bz2.compress(plain_encode(S), level)))
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 8, shuffles=2, seed=0, bz2_level=0)

    def test_input_types_agree(self):
        vals = [5, 5, 1, 0, 5, 7, 2, 2, 6, 1]
        for f in (perm.excursion, perm.num_directional_runs, perm.len_directional_runs,
                  perm.num_increases_decreases, perm.num_runs_median, perm.len_runs_median,
                  perm.avg_collision, perm.max_collision, perm.compression):
            a = f(vals)
            self.assertEqual(a, f(tuple(vals)))
            self.assertEqual(a, f(np.array(vals, dtype=np.int64)))
            self.assertEqual(a, f(bytes(vals)))
        self.assertEqual(perm.periodicity(vals, 1), perm.periodicity(bytes(vals), 1))
        self.assertEqual(perm.covariance(vals, 3), perm.covariance(np.array(vals), 3))


# ==========================================================================
# Binary handling: which reading of "binary", which conversion where
# ==========================================================================

class TestBinaryHandling(unittest.TestCase):

    def test_binary_input_table_matches_the_handling_paragraphs(self):
        # Each section's "Handling binary data" paragraph (PDF pp. 39-43).
        self.assertEqual(perm.BINARY_INPUT["excursion"], "raw")             # 5.1.1 no conversion
        for n in ("numDirectionalRuns", "lenDirectionalRuns", "numIncreasesDecreases",
                  "periodicity", "covariance"):
            self.assertEqual(perm.BINARY_INPUT[n], "conv1", n)                # Conversion I
        for n in ("avgCollision", "maxCollision"):
            self.assertEqual(perm.BINARY_INPUT[n], "conv2", n)                # Conversion II
        for n in ("numRunsMedian", "lenRunsMedian"):
            self.assertEqual(perm.BINARY_INPUT[n], "bits", n)                 # median 0.5, no conversion
        self.assertEqual(perm.BINARY_INPUT["compression"], "raw")           # 5.1.11 no conversion
        self.assertEqual(len(perm.statistic_names()), 19)                    # 8 + 5 + 5 + 1

    def test_binary_statistics_are_computed_on_the_converted_data(self):
        rng = random.Random(4)
        bits = [rng.randrange(2) for _ in range(500)]
        r = perm.permutation_test(bits, 1, shuffles=3, seed=0)
        self.assertTrue(r["binary"])
        c1 = perm.conversion_I(bits)
        c2 = perm.conversion_II(bits)
        self.assertEqual(r["excursion"], perm.excursion(bits))
        self.assertEqual(r["numDirectionalRuns"], perm.num_directional_runs(c1))
        self.assertEqual(r["lenDirectionalRuns"], perm.len_directional_runs(c1))
        self.assertEqual(r["numIncreasesDecreases"], perm.num_increases_decreases(c1))
        self.assertEqual(r["numRunsMedian"], perm.num_runs_median(bits, 0.5))
        self.assertEqual(r["lenRunsMedian"], perm.len_runs_median(bits, 0.5))
        self.assertEqual(r["avgCollision"], perm.avg_collision(c2))
        self.assertEqual(r["maxCollision"], perm.max_collision(c2))
        for p in perm.LAGS:
            self.assertEqual(r[f"periodicity({p})"], perm.periodicity(c1, p))
            self.assertEqual(r[f"covariance({p})"], perm.covariance(c1, p))
        self.assertEqual(r["compression"], perm.compression(bits))
        self.assertEqual(r["median_rule"], "assumed 0.5 (binary)")
        self.assertTrue(math.isnan(r["median"]))

    def test_two_valued_eight_bit_data_under_each_binary_mode(self):
        # 8-bit symbols that happen to take only the values {0, 255}: k = 2.
        rng = random.Random(8)
        S = [rng.choice([0, 255]) for _ in range(400)]
        a = perm.permutation_test(S, 8, shuffles=3, seed=0, binary_mode="alphabet")
        w = perm.permutation_test(S, 8, shuffles=3, seed=0, binary_mode="width")
        n = perm.permutation_test(S, 8, shuffles=3, seed=0, binary_mode="never")
        self.assertTrue(a["binary"])                   # literal "binary, i.e., k = 2"
        self.assertEqual(a["bit_one_value"], 255)      # 255 -> 1, 0 -> 0
        self.assertFalse(w["binary"])                  # width 8 is not 1
        self.assertFalse(n["binary"])
        bits = [1 if s == 255 else 0 for s in S]
        self.assertEqual(a["numDirectionalRuns"], perm.num_directional_runs(perm.conversion_I(bits)))
        self.assertEqual(a["avgCollision"], perm.avg_collision(perm.conversion_II(bits)))
        self.assertEqual(a["numRunsMedian"], perm.num_runs_median(bits, 0.5))
        self.assertEqual(a["compression"], perm.compression(S))        # raw values, no conversion
        self.assertEqual(w["numDirectionalRuns"], perm.num_directional_runs(S))
        self.assertEqual(w["avgCollision"], perm.avg_collision(S))
        self.assertEqual(w["numRunsMedian"], perm.num_runs_median(S))
        # the median rule on the raw values: sorted middle pair; 400 draws are not
        # exactly balanced, so this is whatever the data gives (255 for this seed)
        self.assertEqual(w["median"], plain_median(S))
        self.assertIn(w["median"], (0, 127.5, 255))
        self.assertNotEqual(a["numDirectionalRuns"], w["numDirectionalRuns"])   # the readings differ materially
        for key in perm.statistic_names():
            self.assertEqual(w[key], n[key], key)      # 'width' and 'never' coincide at width 8
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 8, shuffles=2, binary_mode="sometimes")

    def test_conversion_timing_readings(self):
        # Reading A (default, literal Figure 4): permute the bits, then block them
        # inside each statistic.  Reading B: block first, then permute the blocked
        # sequences.  With a deterministic injected "shuffle" that REVERSES its
        # argument and a single shuffle, each reading's permuted statistic is
        # known exactly, so the plumbing of both can be pinned.
        class Reverse:
            def shuffle(self, arr):
                arr[:] = arr[::-1].copy()

        rng = random.Random(6)
        bits = [rng.randrange(2) for _ in range(160)]            # 20 whole blocks, no padding
        after = perm.permutation_test(bits, 1, shuffles=1, rng=Reverse())
        before = perm.permutation_test(bits, 1, shuffles=1, rng=Reverse(),
                                       conversion_timing="before_shuffle")
        self.assertEqual(after["conversion_timing"], "after_shuffle")
        self.assertEqual(before["conversion_timing"], "before_shuffle")
        for name in perm.statistic_names():          # the ORIGINAL statistics do not depend on the reading
            if isinstance(after[name], float) and math.isnan(after[name]):
                self.assertTrue(math.isnan(before[name]), name)     # lags 32 > 20 blocks: undefined in both
            else:
                self.assertEqual(after[name], before[name], name)
        # Reading A: Conversion II of the reversed bits -- blocks in reverse order AND
        # bit-reversed within each block.  Reading B: the original Conversion II
        # sequence reversed -- blocks in reverse order only.
        T_after = perm.max_collision(perm.conversion_II(bits[::-1]))
        T_before = perm.max_collision(perm.conversion_II(bits)[::-1])
        T0 = after["maxCollision"]
        ta, tb = after["tests"]["maxCollision"], before["tests"]["maxCollision"]
        self.assertEqual((ta["C0"], ta["C1"]), perm.counter_update(T0, T_after, 0, 0))
        self.assertEqual((tb["C0"], tb["C1"]), perm.counter_update(T0, T_before, 0, 0))
        self.assertEqual(ta["perm_max"], T_after)
        self.assertEqual(tb["perm_max"], T_before)
        self.assertNotEqual(perm.conversion_II(bits[::-1]).tolist(),
                            perm.conversion_II(bits).tolist()[::-1])   # the two readings see different data
        # Conversion I is a popcount, blind to the within-block bit reversal, so the
        # two readings coincide for the Conversion-I statistics under THIS shuffle:
        self.assertEqual(perm.conversion_I(bits[::-1]).tolist(), perm.conversion_I(bits).tolist()[::-1])
        for name in ("numDirectionalRuns", "covariance(1)", "periodicity(1)"):
            self.assertEqual(after["tests"][name]["perm_max"], before["tests"][name]["perm_max"], name)
        # With a real RNG the counters of the converted statistics generally differ
        # between the readings, while the raw-data statistics (same bit shuffle) agree.
        a = perm.permutation_test(bits * 4, 1, shuffles=30, seed=2)
        b = perm.permutation_test(bits * 4, 1, shuffles=30, seed=2, conversion_timing="before_shuffle")
        for name in ("excursion", "numRunsMedian", "lenRunsMedian", "compression"):
            self.assertEqual(a["tests"][name], b["tests"][name], name)
        # Non-binary data: the option changes nothing and is reported as None.
        S = [rng.randrange(8) for _ in range(100)]
        a = perm.permutation_test(S, 3, shuffles=5, seed=1)
        b = perm.permutation_test(S, 3, shuffles=5, seed=1, conversion_timing="before_shuffle")
        self.assertIsNone(a["conversion_timing"])
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        with self.assertRaises(ValueError):
            perm.permutation_test(bits, 1, shuffles=1, conversion_timing="during")

    def test_bitstring_track(self):
        S = [0xA5, 0x0F, 0xF0]
        r = perm.estimate(S, 8, shuffles=2, seed=0, track="bitstring")
        self.assertEqual(r["track"], "bitstring")
        self.assertEqual(r["declared_bits_per_symbol"], 8)
        self.assertEqual(r["bits_per_symbol"], 1)
        self.assertEqual(r["L"], 24)
        self.assertTrue(r["binary"])
        bits = perm.to_bitstring(S, 8)
        self.assertEqual(bits.tolist(), [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0])
        self.assertEqual(r["excursion"], perm.excursion(bits))
        self.assertEqual(perm.conversion_II(bits).tolist(), [0xA5, 0x0F, 0xF0])   # MSB-first round trip
        with self.assertRaises(ValueError):
            perm.estimate(S, 8, shuffles=2, track="columns")


# ==========================================================================
# The procedure end to end: a sequence that must be rejected, and its control
# ==========================================================================

class TestProcedure(unittest.TestCase):

    def test_alternating_bits_are_rejected(self):
        # S = (0,1,0,1,...), L = 2000.  Number of runs based on the median (5.1.5)
        # is 2000, the largest value any arrangement of these bits can take, so
        # no permutation can exceed it (C0 = 0) and only the two alternating
        # arrangements tie: probability 2 / C(2000, 1000) ~ 1e-600 per shuffle.
        # Hence C0 + C1 = 0 <= cutoff and the test rejects; with it the battery.
        S = [0, 1] * 1000
        r = perm.permutation_test(S, 1, shuffles=200, seed=7)
        self.assertTrue(r["binary"])
        self.assertEqual(r["numRunsMedian"], 2000)
        self.assertEqual(r["lenRunsMedian"], 1)
        t = r["tests"]["numRunsMedian"]
        self.assertEqual((t["C0"], t["C1"]), (0, 0))
        self.assertFalse(t["passed"])
        self.assertLess(t["perm_max"], 2000)
        self.assertFalse(r["iid_assumption"])
        self.assertIn("numRunsMedian", r["failed_tests"])
        # Conversion I of the alternating bits is (4,4,4,...,4): periodicity(1) = 249
        # blocks, again the maximum, so that statistic rejects too.
        self.assertEqual(r["periodicity(1)"], 249)
        self.assertIn("periodicity(1)", r["failed_tests"])

    def test_negative_control_the_same_bits_in_a_random_order_pass(self):
        # Mutation of the case above (rule 7): the SAME multiset of bits, put in
        # one fixed-seed random order, is what an IID source could produce.  At
        # 1000 shuffles the scaled cutoffs are (0, 1000): a test rejects only if
        # no permutation reaches the original statistic or every one exceeds it,
        # so a false rejection here has probability well under 1% per test.
        # The seed is fixed (7) and recorded; the outcome is deterministic.
        S = [0, 1] * 1000
        random.Random(1).shuffle(S)
        r = perm.permutation_test(S, 1, shuffles=1000, seed=7)
        t = r["tests"]["numRunsMedian"]
        self.assertTrue(t["passed"], (t["C0"], t["C1"]))       # the statistic that caught the original
        self.assertGreater(t["C0"] + t["C1"], 0)
        self.assertLess(t["C0"], 1000)
        self.assertTrue(r["iid_assumption"], r["failed_tests"])
        self.assertEqual(r["failed_tests"], [])

    def test_result_structure_and_determinism(self):
        rng = random.Random(3)
        S = [rng.randrange(16) for _ in range(300)]
        a = perm.estimate(S, 4, shuffles=25, seed=99)
        b = perm.estimate(S, 4, shuffles=25, seed=99)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertTrue(math.isnan(a["min_entropy"]))
        self.assertEqual(a["seed_entropy"], 99)
        self.assertEqual(a["shuffles"], 25)
        self.assertEqual(a["cutoffs"], [0, 25])
        self.assertEqual(a["L"], 300)
        self.assertEqual(a["k"], len(set(S)))
        self.assertEqual(set(a["tests"]), set(perm.statistic_names()))
        for name, t in a["tests"].items():
            self.assertEqual(set(t), {"T", "C0", "C1", "passed", "defined", "perm_min", "perm_max"})
            self.assertEqual(a[name], t["T"])
            self.assertLessEqual(t["C0"] + t["C1"], 25)
            self.assertTrue(t["defined"])
            self.assertEqual(t["passed"], not perm.test_rejects(t["C0"], t["C1"], 25))
            if t["defined"]:
                self.assertLessEqual(t["perm_min"], t["perm_max"])
        self.assertEqual(a["iid_assumption"], all(t["passed"] for t in a["tests"].values()))
        # a fresh seed is drawn and reported when none is given
        c = perm.estimate(S, 4, shuffles=3)
        self.assertIsInstance(c["seed_entropy"], int)

    def test_workers_do_not_change_the_result(self):
        rng = random.Random(21)
        S = [rng.randrange(256) for _ in range(400)]
        one = perm.permutation_test(S, 8, shuffles=24, seed=5, workers=1)
        two = perm.permutation_test(S, 8, shuffles=24, seed=5, workers=2)
        self.assertEqual(json.dumps(one, sort_keys=True), json.dumps(two, sort_keys=True))
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 8, shuffles=4, rng=perm.PythonFisherYates(1), workers=2)

    def test_injected_literal_fisher_yates(self):
        rng = random.Random(21)
        S = [rng.randrange(4) for _ in range(60)]
        r = perm.permutation_test(S, 2, shuffles=10, rng=perm.PythonFisherYates(2))
        self.assertEqual(r["rng"], "injected")
        for t in r["tests"].values():
            self.assertLessEqual(t["C0"] + t["C1"], 10)

    def test_tests_subset_and_validation(self):
        S = [1, 2, 3, 0, 2, 2, 1, 3] * 10
        r = perm.permutation_test(S, 2, shuffles=5, seed=0, tests=("excursion", "covariance(2)"))
        self.assertEqual(list(r["tests"]), ["excursion", "covariance(2)"])
        self.assertEqual(r["excursion"], perm.excursion(S))
        self.assertNotIn("compression", r)
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 2, shuffles=5, tests=("excursion", "excursion"))
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 2, shuffles=5, tests=("runsTest",))
        with self.assertRaises(ValueError):
            perm.permutation_test([4], 2, shuffles=5)                       # out of range for width 2
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 0, shuffles=5)
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 2, shuffles=0)
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 2, shuffles=5, median_rule="middle")
        with self.assertRaises(ValueError):
            perm.permutation_test(S, 2, shuffles=5, counter_rule="table")
        perm.permutation_test([7, 7, 9], 2, shuffles=2, seed=0, validate=False)    # caller's responsibility


# ==========================================================================
# Command line
# ==========================================================================

class TestCommandLine(unittest.TestCase):

    def _run(self, *args):
        return subprocess.run([sys.executable, str(MOD_PATH), *args],
                              capture_output=True, text=True, timeout=600)

    def test_cli_matches_the_api_and_survives_the_compression_py_shadow(self):
        # Running permutation.py as a script puts py90b/ at sys.path[0], where the
        # sibling compression.py shadows the stdlib package `compression` that
        # Python 3.14's bz2 imports; the module's _import_bz2 must get past that.
        rng = random.Random(1234)
        raw = bytes(rng.randrange(256) for _ in range(600))
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "rand8.bin")
            with open(path, "wb") as fh:
                fh.write(raw)

            p = self._run(path, "8", "--shuffles", "30", "--seed", "5")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            ref = perm.estimate(raw, 8, shuffles=30, seed=5)
            for name in perm.statistic_names():
                self.assertEqual(out[name], ref[name], name)
                self.assertEqual(out["tests"][name]["C0"], ref["tests"][name]["C0"], name)
                self.assertEqual(out["tests"][name]["C1"], ref["tests"][name]["C1"], name)
            self.assertEqual(out["iid_assumption"], ref["iid_assumption"])
            self.assertEqual(out["track"], "literal")
            self.assertEqual(out["input_bytes"], 600)
            self.assertEqual(out["out_of_width_bytes_masked"], 0)
            self.assertEqual(len(out["input_sha256"]), 64)
            self.assertTrue(math.isnan(out["min_entropy"]))

            p = self._run(path, "8", "--bitstring", "--shuffles", "30", "--seed", "5")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["L"], 4800)
            self.assertEqual(out["k"], 2)
            self.assertTrue(out["binary"])
            ref = perm.estimate(raw, 8, shuffles=30, seed=5, track="bitstring")
            for name in perm.statistic_names():
                self.assertEqual(out[name], ref[name], name)

            # workers must not change the output
            p1 = self._run(path, "8", "--shuffles", "24", "--seed", "5", "--workers", "1")
            p2 = self._run(path, "8", "--shuffles", "24", "--seed", "5", "--workers", "2")
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertEqual(p2.returncode, 0, p2.stderr)
            self.assertEqual(json.loads(p1.stdout), json.loads(p2.stdout))

            # option variants are honoured
            p = self._run(path, "8", "--shuffles", "4", "--seed", "1", "--counter-rule", "prose",
                          "--median-rule", "lower", "--bz2-level", "1", "--tests", "excursion,compression",
                          "--conversion-timing", "before_shuffle")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["counter_rule"], "prose")
            self.assertIsNone(out["conversion_timing"])            # 8-bit data is not binary
            p = self._run(path, "8", "--bitstring", "--shuffles", "4", "--seed", "1",
                          "--conversion-timing", "before_shuffle", "--tests", "maxCollision")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["conversion_timing"], "before_shuffle")
            self.assertEqual(out["median_rule"], "lower")
            self.assertEqual(out["bz2_level"], 1)
            self.assertEqual(list(out["tests"]), ["excursion", "compression"])

    def test_low_bits_are_the_symbol(self):
        raw = bytes([0xA3, 0x53, 0x03, 0xF3, 0x1C, 0x20, 0x31, 0x02, 0x11, 0x0E])
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "nibbles.bin")
            with open(path, "wb") as fh:
                fh.write(raw)
            p = self._run(path, "4", "--shuffles", "3", "--seed", "0")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            # bytes above 0x0F: A3, 53, F3, 1C, 20, 31, 11 = 7 (0x03, 0x02, 0x0E fit)
            self.assertEqual(out["out_of_width_bytes_masked"], 7)
            self.assertIn("warning", p.stderr)
            nibbles = [b & 0xF for b in raw]
            self.assertEqual(out["excursion"], perm.excursion(nibbles))
            self.assertEqual(out["k"], len(set(nibbles)))

    def test_usage_errors(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "x.bin")
            with open(path, "wb") as fh:
                fh.write(bytes(range(16)))
            for args in ([path], [path, "9"], [path, "0"], [path, "eight"],
                         [path, "8", "--bogus"], [path, "8", "--shuffles"],
                         [path, "8", "--shuffles", "2", "--binary-mode", "maybe"]):
                with self.subTest(args=args):
                    p = self._run(*args)
                    self.assertNotEqual(p.returncode, 0)
                    self.assertEqual(p.stdout, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
