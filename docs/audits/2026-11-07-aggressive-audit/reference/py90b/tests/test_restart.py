"""
Tests for py90b.restart -- SP 800-90B sections 3.1.4.1-3.1.4.3, the Restart Tests.

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_restart.py -v
(or   <venv>/bin/python reference/py90b/tests/test_restart.py)

The standard gives NO worked example for section 3.1.4 (PDF p. 20-22 carry
the procedure only), so every expected value below is derived BY HAND in the
comment beside it, from the printed formulas.  Nothing is taken from the C++
tool's output; no file under cpp/ was opened.

Two hand-derived inputs are the core (as the task asked): a 4x4 two-bit
matrix, and a degenerate all-one-symbol matrix (two sizes, one of which
makes the sanity check fail).
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from collections import Counter
from fractions import Fraction

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
RESTART_PATH = HERE.parent / "restart.py"


def _load_restart():
    """Load restart.py straight from its file so this test does not depend on
    whatever else the py90b package may import."""
    spec = importlib.util.spec_from_file_location("py90b_restart_under_test", RESTART_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load_restart()


def _mcv_by_hand(symbols):
    """Section 6.3.1 as printed, written again here independently of the module."""
    L = len(symbols)
    p_hat = max(Counter(symbols).values()) / L
    p_u = min(1.0, p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / (L - 1)))
    return -math.log2(p_u)


# ---------------------------------------------------------------------------
# Hand-derived example 1: a 4x4 matrix of 2-bit samples
# ---------------------------------------------------------------------------
#
#   M = [[0, 1, 2, 3],
#        [1, 1, 2, 3],
#        [2, 3, 0, 0],
#        [3, 0, 0, 0]]
#
# Step 2, rows:    row 1: every value once        -> XR1 = 1
#                  row 2: '1' twice               -> XR2 = 2
#                  row 3: '0' twice               -> XR3 = 2
#                  row 4: '0' three times         -> XR4 = 3     XR = 3
# Step 3, columns: col 1 = (0,1,2,3)              -> XC1 = 1
#                  col 2 = (1,1,3,0): '1' twice   -> XC2 = 2
#                  col 3 = (2,2,0,0): twice       -> XC3 = 2
#                  col 4 = (3,3,0,0): twice       -> XC4 = 2     XC = 2
# Step 4: Xmax = max(XC, XR) = 3.
# Step 5 with HI = 2 (p = 1/4), n = 4 trials:
#     P(X >= 3) = C(4,3)(1/4)^3(3/4) + C(4,4)(1/4)^4 = 12/256 + 1/256 = 13/256
#               = 0.05078125  >= 0.000005  -> sanity check PASSES.
#   with HI = 1 (p = 1/2):
#     P(X >= 3) = C(4,3)(1/2)^4 + C(4,4)(1/2)^4 = 4/16 + 1/16 = 5/16 = 0.3125 -> PASSES.
#
# Row dataset  (rows concatenated):    0,1,2,3, 1,1,2,3, 2,3,0,0, 3,0,0,0
# Column dataset (columns concatenated): 0,1,2,3, 1,1,3,0, 2,2,0,0, 3,3,0,0
# Both have counts {0:6, 1:3, 2:3, 3:4}; L = 16.
# 6.3.1 (IID track): p-hat = 6/16 = 0.375;
#     p_u = 0.375 + 2.576*sqrt(0.375*0.625/15) = 0.375 + 2.576*sqrt(0.015625)
#         = 0.375 + 2.576*0.125 = 0.375 + 0.322 = 0.697
#     Hr = Hc = -log2(0.697) = 0.52077 (5 d.p.)
# 3.1.4.2 with HI = 2:  min(Hr,Hc) = 0.52077 < HI/2 = 1.0  -> validation FAILS, no estimate.
#            with HI = 1:  0.52077 >= 0.5 -> passes; H = min(0.52077, 0.52077, 1) = 0.52077.

M_2BIT = np.array([[0, 1, 2, 3],
                   [1, 1, 2, 3],
                   [2, 3, 0, 0],
                   [3, 0, 0, 0]], dtype=np.uint8)
ROW_DATASET_2BIT = [0, 1, 2, 3, 1, 1, 2, 3, 2, 3, 0, 0, 3, 0, 0, 0]
COL_DATASET_2BIT = [0, 1, 2, 3, 1, 1, 3, 0, 2, 2, 0, 0, 3, 3, 0, 0]
H_RC_2BIT = -math.log2(0.375 + 2.576 * 0.125)     # = -log2(0.697)


class HandDerivedTwoBitMatrix(unittest.TestCase):

    def test_row_and_column_datasets_follow_3_1_4_1(self):
        self.assertEqual(R.row_dataset(M_2BIT).tolist(), ROW_DATASET_2BIT)
        self.assertEqual(R.column_dataset(M_2BIT).tolist(), COL_DATASET_2BIT)

    def test_steps_2_to_4_counts(self):
        self.assertEqual(R.max_count_per_row(M_2BIT, 2).tolist(), [1, 2, 2, 3])
        self.assertEqual(R.max_count_per_column(M_2BIT, 2).tolist(), [1, 2, 2, 2])
        sc = R.sanity_check(M_2BIT, 2.0, 2)
        self.assertEqual((sc["X_R"], sc["X_C"], sc["X_max"]), (3, 2, 3))
        self.assertEqual(sc["X_max_from"], "row")

    def test_step_5_tail_HI_2(self):
        sc = R.sanity_check(M_2BIT, 2.0, 2)
        self.assertEqual(sc["p"], 0.25)
        self.assertEqual(Fraction(sc["P(X >= X_max) exact (40 digits)"]), Fraction(13, 256))
        self.assertEqual(sc["P(X >= X_max)"], 13 / 256)
        self.assertTrue(sc["sanity_check_passed"])
        self.assertTrue(sc["passedRestartSanityCheck"])

    def test_step_5_tail_HI_1(self):
        sc = R.sanity_check(M_2BIT, 1.0, 2)
        self.assertEqual(sc["P(X >= X_max)"], 5 / 16)
        self.assertTrue(sc["sanity_check_passed"])

    def test_iid_track_estimates_and_HI_over_2_rule(self):
        res2 = R.check(M_2BIT, 2.0, 2, estimation_track="iid")
        self.assertAlmostEqual(res2["H_r"], H_RC_2BIT, places=12)
        self.assertAlmostEqual(res2["H_c"], H_RC_2BIT, places=12)
        self.assertAlmostEqual(res2["H_r"], _mcv_by_hand(ROW_DATASET_2BIT), places=12)
        self.assertAlmostEqual(res2["H_r"], 0.52077, places=5)
        self.assertEqual(res2["H_I/2"], 1.0)
        self.assertIs(res2["validation_passed"], False)
        self.assertTrue(math.isnan(res2["min_entropy"]))          # "no entropy estimate is awarded"

        res1 = R.check(M_2BIT, 1.0, 2, estimation_track="iid")
        self.assertIs(res1["validation_passed"], True)
        self.assertAlmostEqual(res1["min_entropy"], H_RC_2BIT, places=12)   # min(Hr, Hc, HI) = Hr
        self.assertAlmostEqual(res1["min_entropy_per_sample"], H_RC_2BIT, places=12)  # literal track: same

    def test_flat_row_major_input_equals_matrix_input(self):
        flat = M_2BIT.reshape(-1)
        a = R.check(flat, 1.0, 2, r=4, c=4, estimation_track="iid")
        b = R.check(M_2BIT, 1.0, 2, estimation_track="iid")
        for k in ("X_R", "X_C", "X_max", "P(X >= X_max)", "H_r", "H_c", "min_entropy"):
            self.assertEqual(a[k], b[k], k)
        e = R.estimate(flat, 2, H_I=1.0, r=4, c=4, estimation_track="iid")
        self.assertAlmostEqual(e["min_entropy"], H_RC_2BIT, places=12)


# ---------------------------------------------------------------------------
# Hand-derived example 2 (degenerate): every sample the same symbol
# ---------------------------------------------------------------------------
#
# (a) 4x4 of zeros, 1-bit symbols, HI = 1 (p = 1/2):
#     every row and column is 0,0,0,0 -> XR = XC = Xmax = 4.
#     P(X >= 4) = C(4,4)(1/2)^4 = 1/16 = 0.0625 >= 0.000005 -> the sanity check
#     PASSES (the test has no power at n = 4; that is what the formula says).
#     Row/column datasets are 16 zeros: p-hat = 1, p_u = min(1, 1 + 0) = 1,
#     Hr = Hc = -log2(1) = 0.  0 < HI/2 = 0.5 -> validation FAILS, no estimate.
#
# (b) 8x8 of zeros, 4-bit symbols, HI = 4 (p = 1/16):
#     Xmax = 8.  P(X >= 8) = C(8,8)(1/16)^8 = 16^-8 = 1/4294967296 = 2.3283e-10
#     < 0.000005 -> the sanity check FAILS; by 3.1.4.2 the estimators are not
#     run and no estimate is awarded.

class DegenerateAllOneSymbol(unittest.TestCase):

    def test_4x4_zeros_sanity_passes_but_validation_fails(self):
        Z = np.zeros((4, 4), dtype=np.uint8)
        res = R.check(Z, 1.0, 1, estimation_track="iid")
        self.assertEqual((res["X_R"], res["X_C"], res["X_max"]), (4, 4, 4))
        self.assertEqual(res["P(X >= X_max)"], 1 / 16)
        self.assertTrue(res["sanity_check_passed"])
        self.assertEqual(res["H_r"], 0.0)
        self.assertEqual(res["H_c"], 0.0)
        self.assertFalse(math.copysign(1.0, res["H_r"]) < 0, "-0.0 should be normalised to 0.0")
        self.assertIs(res["validation_passed"], False)
        self.assertIn("HI/2", res["validation_reason"])
        self.assertTrue(math.isnan(res["min_entropy"]))

    def test_8x8_zeros_4bit_sanity_fails_and_estimators_are_not_run(self):
        Z = np.zeros((8, 8), dtype=np.uint8)
        res = R.check(Z, 4.0, 4, estimation_track="iid")
        self.assertEqual(res["X_max"], 8)
        self.assertEqual(Fraction(res["P(X >= X_max) exact (40 digits)"]), Fraction(1, 16 ** 8))
        self.assertFalse(res["sanity_check_passed"])
        self.assertTrue(math.isnan(res["H_r"]) and math.isnan(res["H_c"]))   # not performed
        self.assertIs(res["validation_passed"], False)
        self.assertIn("sanity", res["validation_reason"])
        self.assertTrue(math.isnan(res["min_entropy"]))
        # always_estimate=True computes them anyway (driver convenience); verdict unchanged
        res2 = R.check(Z, 4.0, 4, estimation_track="iid", always_estimate=True)
        self.assertEqual(res2["H_r"], 0.0)
        self.assertIs(res2["validation_passed"], False)
        self.assertTrue(math.isnan(res2["min_entropy"]))

    def test_cutoff_threshold_matches_tail_verdict_on_degenerate(self):
        Z = np.zeros((8, 8), dtype=np.uint8)
        res = R.check(Z, 4.0, 4, estimation_track="iid")
        # smallest failing X at n = 8, p = 1/16: find it by hand with the tail function
        xf = R.sanity_cutoff(1 / 16, R.ALPHA_PRINTED, 8)
        self.assertEqual(res["X_cutoff_fail"], xf)
        self.assertEqual(res["X_cutoff_pass"], xf - 1)
        self.assertEqual(res["restartXcutoff"], xf - 1)
        self.assertGreaterEqual(res["X_max"], xf)       # failed  <=> Xmax >= X_cutoff_fail


# ---------------------------------------------------------------------------
# The dataset construction of 3.1.4.1 on a non-square matrix
# ---------------------------------------------------------------------------
#   M = [[a, b, c],        row dataset    = a b c d e f
#        [d, e, f]]        column dataset = a d b e c f

class DatasetConstruction(unittest.TestCase):

    def test_2x3(self):
        a, b, c, d, e, f = 10, 11, 12, 13, 14, 15
        M = np.array([[a, b, c], [d, e, f]], dtype=np.uint8)
        self.assertEqual(R.row_dataset(M).tolist(), [a, b, c, d, e, f])
        self.assertEqual(R.column_dataset(M).tolist(), [a, d, b, e, c, f])

    def test_as_matrix_shapes_and_refusals(self):
        with self.assertRaises(ValueError):
            R.as_matrix(np.zeros(999_999, dtype=np.uint8), 8)        # not 1000*1000
        with self.assertRaises(ValueError):
            R.as_matrix(np.zeros(15, dtype=np.uint8), 2, r=4, c=4)   # not r*c
        with self.assertRaises(ValueError):
            R.as_matrix(np.zeros(16, dtype=np.uint8), 2, r=4)        # r without c
        with self.assertRaises(ValueError):
            R.as_matrix(np.array([[0, 4]], dtype=np.uint8), 2)       # 4 is out of width 2
        M = R.as_matrix(bytes(range(16)), 4, r=4, c=4)
        self.assertEqual(M.shape, (4, 4))
        self.assertEqual(M[1][2], 6)         # row-major: M[i][j] = jth sample of restart i


# ---------------------------------------------------------------------------
# Step 5's formula and the alpha of step 1
# ---------------------------------------------------------------------------

class PrintedBinomialTail(unittest.TestCase):

    def test_alpha_printed_equals_alpha_derived(self):
        # Step 1 prints 0.000 005; the narrative says 0.01 over 2000 experiments.
        self.assertEqual(R.ALPHA_PRINTED, 0.000005)
        self.assertEqual(R.ALPHA_DERIVED, 0.01 / 2000)
        self.assertEqual(R.ALPHA_PRINTED, R.ALPHA_DERIVED)                       # same binary64
        self.assertEqual(R._alpha_as_fraction(R.ALPHA_PRINTED), Fraction(1, 200000))
        self.assertEqual(Fraction("0.01") / 2000, Fraction(1, 200000))           # same exact decimal

    def test_small_tails_by_hand(self):
        # n = 4, p = 1/4: P(X >= 3) = 13/256 (worked above); P(X >= 0) = 1; P(X >= 5) = 0
        self.assertEqual(R.binomial_upper_tail(3, 4, Fraction(1, 4)), Fraction(13, 256))
        self.assertEqual(R.binomial_upper_tail(0, 4, Fraction(1, 4)), 1)
        self.assertEqual(R.binomial_upper_tail(-2, 4, Fraction(1, 4)), 1)
        self.assertEqual(R.binomial_upper_tail(5, 4, Fraction(1, 4)), 0)
        # n = 4, p = 1/2: P(X >= 2) = (6 + 4 + 1)/16 = 11/16
        self.assertEqual(R.binomial_upper_tail(2, 4, 0.5), Fraction(11, 16))
        # P(X >= n) = p^n
        self.assertEqual(R.binomial_upper_tail(8, 8, Fraction(1, 16)), Fraction(1, 16 ** 8))
        # p = 1: the sum is 1 for every x <= n (0^0 = 1); p = 0: only x <= 0 gives 1
        self.assertEqual(R.binomial_upper_tail(7, 10, 1), 1)
        self.assertEqual(R.binomial_upper_tail(1, 10, 0), 0)
        self.assertEqual(R.binomial_upper_tail(0, 10, 0), 1)

    def test_terms_sum_to_one_and_tail_is_suffix_sum(self):
        for p in (Fraction(1, 3), 0.123, 2.0 ** -0.696):
            terms = R.binomial_terms(12, p)
            self.assertEqual(sum(terms), 1)
            for x in range(0, 14):
                self.assertEqual(R.binomial_upper_tail(x, 12, p), sum(terms[max(x, 0):]))

    def test_exact_matches_naive_float_closely_at_n_1000(self):
        p = 2.0 ** -0.696
        for x in (600, 684, 685, 700):
            exact = float(R.binomial_upper_tail(x, 1000, p))
            naive = R.binomial_upper_tail_float(x, 1000, p)
            self.assertAlmostEqual(exact, naive, delta=1e-12 * max(exact, 1e-300))

    def test_tail_is_non_increasing_in_x(self):
        p = 0.37
        prev = Fraction(2)
        for x in range(0, 41):
            t = R.binomial_upper_tail(x, 40, p)
            self.assertLessEqual(t, prev)
            prev = t

    def test_p_from_H_I_and_refusals(self):
        self.assertEqual(R._p_from_H_I(1.0), 0.5)
        self.assertEqual(R._p_from_H_I(2.0), 0.25)
        for bad in (0.0, -1.0, float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                R._p_from_H_I(bad)
        with self.assertRaises(ValueError):
            R.check(M_2BIT, 0.0, 2)
        with self.assertRaises(ValueError):
            R.check(M_2BIT, float("nan"), 2)
        with self.assertRaises(ValueError):
            R.check(M_2BIT, -0.5, 2)


class SanityCutoff(unittest.TestCase):

    def _check_cutoff_props(self, p, alpha, n):
        xf = R.sanity_cutoff(p, alpha, n)
        fa = R._alpha_as_fraction(alpha)
        self.assertTrue(0 <= xf <= n + 1)
        if xf <= n:
            self.assertLess(R.binomial_upper_tail(xf, n, p), fa)          # xf fails
        if xf >= 1:
            self.assertGreaterEqual(R.binomial_upper_tail(xf - 1, n, p), fa)   # xf - 1 passes
        self.assertEqual(R.sanity_cutoff_pass(p, alpha, n), xf - 1)
        return xf

    def test_properties_small(self):
        for p, n in ((Fraction(1, 2), 4), (Fraction(1, 16), 8), (0.9, 10), (0.001, 50), (1, 7), (0, 7)):
            self._check_cutoff_props(p, R.ALPHA_PRINTED, n)
        # p = 1: nothing fails -> n + 1
        self.assertEqual(R.sanity_cutoff(1, R.ALPHA_PRINTED, 7), 8)
        # p = 0: P(X >= 1) = 0 < alpha, P(X >= 0) = 1 -> smallest failing is 1
        self.assertEqual(R.sanity_cutoff(0, R.ALPHA_PRINTED, 7), 1)

    def test_n_1000_at_the_forks_documented_point(self):
        # FORK-DIVERGENCE-AND-TRUST.md C23: at H_I = 0.696 (width 1) "both
        # cutoffs give 684".  The printed formula here gives largest passing
        # 684 and smallest failing 685, which is how this module maps
        # 'restartXcutoff' := X_cutoff_pass.  Values recorded, not assumed:
        # tail(684) = 6.472e-06 >= 5e-06 (passes), tail(685) = 4.757e-06 < 5e-06 (fails).
        p = 2.0 ** -0.696
        t0 = time.perf_counter()
        xf = self._check_cutoff_props(p, R.ALPHA_PRINTED, 1000)
        dt = time.perf_counter() - t0
        self.assertEqual(xf, 685)
        self.assertEqual(R.sanity_cutoff_pass(p, R.ALPHA_PRINTED, 1000), 684)
        self.assertLess(float(R.binomial_upper_tail(685, 1000, p)), 5e-6)
        self.assertGreaterEqual(float(R.binomial_upper_tail(684, 1000, p)), 5e-6)
        print(f"\n[timing] sanity_cutoff + two tails at n=1000: {dt*1000:.1f} ms", file=sys.stderr)

    def test_n_1000_p_half(self):
        # p = 1/2 (HI = 1 bit): mean 500, sd sqrt(250) = 15.81; alpha = 5e-6 is
        # about z = 4.42, so the threshold is near 500 + 4.42*15.8 = 570.
        xf = self._check_cutoff_props(0.5, R.ALPHA_PRINTED, 1000)
        self.assertTrue(565 <= xf <= 575, xf)

    def test_alpha_as_decimal_string(self):
        self.assertEqual(R.sanity_cutoff(0.5, "0.000005", 1000), R.sanity_cutoff(0.5, 0.000005, 1000))
        self.assertEqual(R.sanity_cutoff(0.5, Fraction(1, 200000), 1000), R.sanity_cutoff(0.5, 0.000005, 1000))


# ---------------------------------------------------------------------------
# The counting (steps 2-3) against plain Python, all code paths
# ---------------------------------------------------------------------------

class Counting(unittest.TestCase):

    def test_three_methods_agree_on_random_matrices(self):
        rng = np.random.default_rng(20261107)
        for bps, shape in ((1, (37, 53)), (2, (20, 20)), (8, (100, 100)), (8, (3, 1)), (16, (30, 40))):
            dtype = np.uint16 if bps > 8 else np.uint8
            M = rng.integers(0, 1 << bps, size=shape, dtype=dtype)
            py_rows = R.max_count_per_row(M, bps, "python")
            py_cols = R.max_count_per_column(M, bps, "python")
            self.assertTrue(np.array_equal(R.max_count_per_row(M, bps, "sorted"), py_rows), (bps, shape))
            self.assertTrue(np.array_equal(R.max_count_per_column(M, bps, "sorted"), py_cols), (bps, shape))
            if bps <= 12:
                self.assertTrue(np.array_equal(R.max_count_per_row(M, bps, "bincount"), py_rows), (bps, shape))
                self.assertTrue(np.array_equal(R.max_count_per_column(M, bps, "bincount"), py_cols), (bps, shape))
            self.assertTrue(np.array_equal(R.max_count_per_row(M, bps, "auto"), py_rows), (bps, shape))

    def test_skewed_matrix_hits_both_axes(self):
        # row 0 is all 7s (XR = 5); column 2 is all 3s except row 0 (XC = 4)
        M = np.array([[7, 7, 7, 7, 7],
                      [0, 1, 3, 2, 4],
                      [1, 2, 3, 4, 0],
                      [2, 4, 3, 0, 1],
                      [4, 0, 3, 1, 2]], dtype=np.uint8)
        self.assertEqual(R.max_count_per_row(M, 3).tolist(), [5, 1, 1, 1, 1])
        self.assertEqual(R.max_count_per_column(M, 3).tolist(), [1, 1, 4, 1, 1])
        sc = R.sanity_check(M, 3.0, 3, include_per_line=True)
        self.assertEqual(sc["X_R"], 5)
        self.assertEqual(sc["X_C"], 4)
        self.assertEqual(sc["X_max"], 5)
        self.assertEqual(sc["X_R_i"], [5, 1, 1, 1, 1])
        self.assertEqual(sc["X_C_i"], [1, 1, 4, 1, 1])
        # P(X >= 5) at n = 5, p = 1/8: (1/8)^5 = 1/32768 = 3.05e-5 >= 5e-6 -> passes
        self.assertEqual(sc["P(X >= X_max)"], (1 / 8) ** 5)
        self.assertTrue(sc["sanity_check_passed"])
        # X_max came from a row; the column tail is the larger one
        self.assertEqual(sc["X_max_from"], "row")
        self.assertGreater(sc["P(X >= X_C)"], sc["P(X >= X_R)"])
        self.assertEqual(sc["P(X >= X_R)"], sc["P(X >= X_max)"])


# ---------------------------------------------------------------------------
# 3.1.4.2: the HI/2 rule read exactly, with a caller-supplied estimator
# ---------------------------------------------------------------------------

class ValidationRule(unittest.TestCase):

    def _const(self, hr, hc):
        calls = []
        def est(symbols, bps):
            calls.append(len(symbols))
            return hr if len(calls) == 1 else hc     # first call = row dataset, second = column
        return est

    def test_equal_to_half_passes_strictly_less_fails(self):
        M = M_2BIT
        # min(Hr, Hc) == HI/2 exactly: "less than half" is false -> passes, H = min(Hr, Hc, HI) = 0.5
        res = R.check(M, 1.0, 2, estimator=self._const(0.5, 0.75))
        self.assertIs(res["validation_passed"], True)
        self.assertEqual(res["min_entropy"], 0.5)
        # just below half -> fails
        res = R.check(M, 1.0, 2, estimator=self._const(0.5 - 1e-12, 0.75))
        self.assertIs(res["validation_passed"], False)
        self.assertTrue(math.isnan(res["min_entropy"]))
        # the column estimate can be the one that fails
        res = R.check(M, 1.0, 2, estimator=self._const(0.9, 0.49))
        self.assertIs(res["validation_passed"], False)
        self.assertEqual(res["min(H_r, H_c)"], 0.49)

    def test_result_is_min_of_row_column_and_initial(self):
        M = M_2BIT
        res = R.check(M, 1.0, 2, estimator=self._const(1.3, 1.6))      # both above HI -> HI wins
        self.assertEqual(res["min_entropy"], 1.0)
        res = R.check(M, 1.0, 2, estimator=self._const(0.8, 0.6))      # Hc wins
        self.assertEqual(res["min_entropy"], 0.6)
        self.assertEqual(res["estimation_track"], "custom")

    def test_H_I_scale_strings(self):
        self.assertEqual(R.parse_H_I("0.5/bit"), (0.5, "bit"))
        self.assertEqual(R.parse_H_I("3.2/symbol"), (3.2, "symbol"))
        self.assertEqual(R.parse_H_I("3.2"), (3.2, "symbol"))
        self.assertEqual(R.parse_H_I(3.2, "bit"), (3.2, "bit"))
        with self.assertRaises(ValueError):
            R.parse_H_I("abc")
        # literal track, 2-bit symbols: '0.5/bit' means HI = 1.0 per symbol for step 1
        res = R.check(M_2BIT, "0.5/bit", 2, estimation_track="iid")
        self.assertEqual(res["H_I"], 1.0)
        self.assertEqual(res["H_I_per_bit"], 0.5)
        self.assertEqual(res["p"], 0.5)

    def test_iid_track_row_and_column_estimates_coincide(self):
        # Observation about the standard, not a defect: the 6.3.1 estimator
        # depends only on symbol counts, and the row and column datasets are
        # permutations of each other, so under the IID track Hr == Hc always.
        rng = np.random.default_rng(7)
        M = rng.integers(0, 256, size=(40, 40), dtype=np.uint8)
        res = R.check(M, 7.0, 8, estimation_track="iid", always_estimate=True)
        self.assertEqual(res["H_r"], res["H_c"])


# ---------------------------------------------------------------------------
# Bitstring handling (extension beyond the text; see module docstring)
# ---------------------------------------------------------------------------
#   M = [[1, 2],      2-bit samples, MSB first:  1 -> 0 1,  2 -> 1 0
#        [3, 0]]                                  3 -> 1 1,  0 -> 0 0
#   full:          [[0,1,1,0],[1,1,0,0]]  (2 x 4)
#   truncate_rows: [[0,1],[1,1]]          (2 x 2)

class Bitstring(unittest.TestCase):
    M = np.array([[1, 2], [3, 0]], dtype=np.uint8)

    def test_expansion(self):
        self.assertEqual(R.to_bit_matrix(self.M, 2).tolist(), [[0, 1, 1, 0], [1, 1, 0, 0]])
        self.assertEqual(R.to_bit_matrix(self.M, 2, "lsb").tolist(), [[1, 0, 0, 1], [1, 1, 0, 0]])

    def test_full_mode_is_non_square_and_tests_both_axes(self):
        res = R.check(self.M, 1.0, 2, track="bitstring", estimation_track="iid")
        self.assertEqual((res["r"], res["c"]), (2, 4))
        self.assertFalse(res["square"])
        self.assertEqual(res["H_I"], 0.5)                  # per bit: 1.0 per 2-bit sample / 2
        self.assertEqual(res["X_R"], 2)                   # rows [0,1,1,0] and [1,1,0,0]: two of each
        self.assertEqual(res["X_C"], 2)                   # column 2 = (1,0)? no: columns (0,1),(1,1),(1,0),(0,0) -> max 2
        self.assertEqual(res["n_trials_rows"], 4)
        self.assertEqual(res["n_trials_columns"], 2)
        self.assertIsNone(res["X_cutoff_fail"])           # no single cutoff for a non-square matrix
        self.assertTrue(res["sanity_check_passed"])
        self.assertEqual(res["bits_per_matrix_symbol"], 1)
        if math.isfinite(res["min_entropy"]):
            self.assertAlmostEqual(res["min_entropy_per_sample"], 2 * res["min_entropy"])

    def test_truncate_rows_mode(self):
        res = R.check(self.M, 1.0, 2, track="bitstring", bitstring_mode="truncate_rows", estimation_track="iid")
        self.assertEqual((res["r"], res["c"]), (2, 2))
        self.assertTrue(res["square"])
        # matrix [[0,1],[1,1]]: rows -> 1, 2 ; columns (0,1) -> 1, (1,1) -> 2 ; Xmax = 2
        self.assertEqual((res["X_R"], res["X_C"], res["X_max"]), (2, 2, 2))
        # P(X >= 2) at n = 2, p = 2^-0.5 = 0.7071: p^2 = 0.5 exactly? (2^-0.5)^2 in binary64 -> ~0.5
        self.assertAlmostEqual(res["P(X >= X_max)"], 0.5, places=12)

    def test_one_bit_symbols_bitstring_is_literal(self):
        Z = np.array([[0, 1], [1, 0]], dtype=np.uint8)
        a = R.check(Z, 1.0, 1, track="bitstring", estimation_track="iid")
        b = R.check(Z, 1.0, 1, track="literal", estimation_track="iid")
        self.assertEqual(a["track"], "literal")
        self.assertEqual(a["X_max"], b["X_max"])


# ---------------------------------------------------------------------------
# estimate() without HI, and the non-IID composite's bookkeeping
# ---------------------------------------------------------------------------

class EstimateWrapper(unittest.TestCase):

    def test_without_H_I_no_verdict(self):
        res = R.estimate(M_2BIT.reshape(-1), 2, r=4, c=4, estimation_track="iid")
        self.assertTrue(math.isnan(res["min_entropy"]))
        self.assertIsNone(res["validation_passed"])
        self.assertIsNone(res["sanity_check_passed"])
        self.assertEqual((res["X_R"], res["X_C"], res["X_max"]), (3, 2, 3))
        self.assertAlmostEqual(res["H_r"], H_RC_2BIT, places=12)

    def test_non_iid_composite_bookkeeping(self):
        # Whatever siblings are present, the composite must be the minimum of
        # the finite per-estimator values it reports, and must list what it
        # could not run.  (10x10 random bits; EA_ALLOW_SHORT_DATASET-sized.)
        rng = np.random.default_rng(3)
        M = rng.integers(0, 2, size=(10, 10), dtype=np.uint8)
        comp = R.non_iid_estimate(R.row_dataset(M), 1)
        self.assertIn("estimators_used", comp)
        self.assertIn("estimators_missing", comp)
        finite = [v for k, v in comp["per_estimator"].items() if math.isfinite(v)]
        if finite:
            self.assertEqual(comp["min_entropy"], min(finite))
            self.assertEqual(sorted(comp["estimators_used"]),
                             sorted(k for k, v in comp["per_estimator"].items() if math.isfinite(v)))
        else:
            self.assertTrue(math.isnan(comp["min_entropy"]))
        all_labels = {lbl for lbl, _, _ in R.NON_IID_BATTERY}
        accounted = (set(comp["estimators_used"]) | set(comp["estimators_missing"])
                     | set(comp["estimators_failed"]) | set(comp["estimators_skipped_binary_only"])
                     | {k for k, v in comp["per_estimator"].items() if not math.isfinite(v)})
        self.assertEqual(accounted, all_labels)
        # for 8-bit input the three binary-only estimators are skipped, per 6.2
        comp8 = R.non_iid_estimate(rng.integers(0, 256, size=100, dtype=np.uint8), 8)
        self.assertEqual(sorted(comp8["estimators_skipped_binary_only"]),
                         sorted(["Collision", "Markov", "Compression"]))
        print(f"\n[composite] used={comp['estimators_used']} missing={comp['estimators_missing']} "
              f"failed={list(comp['estimators_failed'])}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

class CommandLine(unittest.TestCase):

    def test_cli_iid_on_hand_example(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "m.bin")
            with open(path, "wb") as fh:
                fh.write(bytes(ROW_DATASET_2BIT))          # 16 bytes, row-major 4x4
            cmd = [sys.executable, str(RESTART_PATH), path, "2", "--literal", "--H_I", "1",
                   "--shape", "4x4", "--iid"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual((out["X_R"], out["X_C"], out["X_max"]), (3, 2, 3))
            self.assertEqual(out["P(X >= X_max)"], 5 / 16)
            self.assertTrue(out["passedRestartSanityCheck"])
            self.assertIs(out["validation_passed"], True)
            self.assertAlmostEqual(out["min_entropy"], H_RC_2BIT, places=12)
            self.assertEqual(out["restartCutoffMethod"], R.CUTOFF_METHOD)
            self.assertEqual(out["input_bytes"], 16)
            self.assertEqual(len(out["input_sha256"]), 64)
            self.assertEqual(out["out_of_width_bytes_masked"], 0)

    def test_cli_masks_high_bits_and_warns(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "m.bin")
            with open(path, "wb") as fh:
                fh.write(bytes([v | 0x80 for v in ROW_DATASET_2BIT]))   # high bit set everywhere
            cmd = [sys.executable, str(RESTART_PATH), path, "2", "--H_I", "1", "--shape", "4x4",
                   "--iid", "--no-estimators"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("warning", proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["out_of_width_bytes_masked"], 16)
            self.assertEqual(out["X_max"], 3)
            self.assertTrue(math.isnan(out["H_r"]))
            self.assertIsNone(out["validation_passed"])

    def test_cli_rejects_wrong_length_and_bad_options(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "m.bin")
            with open(path, "wb") as fh:
                fh.write(bytes(15))
            proc = subprocess.run([sys.executable, str(RESTART_PATH), path, "2", "--H_I", "1", "--shape", "4x4"],
                                  capture_output=True, text=True, timeout=120)
            self.assertNotEqual(proc.returncode, 0)
            proc = subprocess.run([sys.executable, str(RESTART_PATH), path, "2", "--bogus"],
                                  capture_output=True, text=True, timeout=120)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("unknown option", proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
