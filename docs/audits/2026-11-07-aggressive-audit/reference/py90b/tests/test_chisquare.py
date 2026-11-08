"""Tests for py90b.chisquare -- SP 800-90B Section 5.2 (PDF p. 43-47).

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_chisquare.py
  or: <venv>/bin/python reference/py90b/tests/test_chisquare.py

Every expected value here is either (a) printed in the standard, (b) a closed
form or a standard table value, or (c) derived BY HAND in the comment above
the assertion.  Nothing is taken from the C++ tool except the names of its
verbose labels and, in one end-to-end test, the values it printed for
bin/rand8_short.bin (reference/cpp-verbose-labels-iid.txt) -- that test
records a discrepancy, it does not fit to it.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE_DIR = os.path.dirname(os.path.dirname(HERE))       # .../reference
AUDIT_DIR = os.path.dirname(REFERENCE_DIR)                   # .../2026-11-07-aggressive-audit
if REFERENCE_DIR not in sys.path:
    sys.path.insert(0, REFERENCE_DIR)

from py90b import chisquare as cs  # noqa: E402

MODULE = os.path.join(REFERENCE_DIR, "py90b", "chisquare.py")


# ==========================================================================
# The chi-square survival function (implemented, not imported)
# ==========================================================================

class Chi2SurvivalFunction(unittest.TestCase):
    """Closed forms and standard table values that do not come from this code."""

    def test_df2_is_exponential(self):
        # chi-square(2) is Exp(mean 2): Pr[X >= x] = exp(-x/2)
        for x in (0.1, 1.0, 3.7, 13.8155, 60.0, 300.0):
            self.assertAlmostEqual(cs.chi2_sf(x, 2), math.exp(-x / 2), delta=1e-15 * max(1, math.exp(-x / 2)) + 1e-300)
        self.assertAlmostEqual(cs.chi2_sf(3.7, 2), 0.15723716631362761, places=15)

    def test_df1_is_folded_normal(self):
        # Pr[Z^2 >= x] = 2 Pr[Z >= sqrt(x)] = erfc(sqrt(x/2))
        for x in (0.01, 1.0, 3.841, 10.828, 30.0):
            self.assertAlmostEqual(cs.chi2_sf(x, 1), math.erfc(math.sqrt(x / 2)), places=14)
        self.assertAlmostEqual(cs.chi2_sf(1.0, 1), 0.31731050786291410, places=14)

    def test_df4_closed_form(self):
        # Pr[X >= x] = exp(-x/2) (1 + x/2)
        for x in (0.5, 7.3, 18.467):
            self.assertAlmostEqual(cs.chi2_sf(x, 4), math.exp(-x / 2) * (1 + x / 2), places=14)

    def test_tabulated_quantiles(self):
        # Standard chi-square tables (0.999 quantile unless stated).  Example 11 of
        # the standard (PDF p. 44) prints "the critical value 16.266" for df = 3.
        table = [(16.266, 3, 0.001), (27.877, 9, 0.001), (10.828, 1, 0.001),
                 (149.449, 100, 0.001), (3.841, 1, 0.05), (23.209, 10, 0.01), (18.307, 10, 0.05)]
        for x, df, alpha in table:
            # the tables are rounded to 3 decimals; the slope of sf there is < 0.3/unit
            self.assertAlmostEqual(cs.chi2_sf(x, df), alpha, delta=alpha * 2e-3, msg=f"sf({x},{df})")

    def test_critical_values_by_bisection(self):
        self.assertAlmostEqual(cs.chi2_critical_value(0.001, 3), 16.266, delta=5e-4)
        self.assertAlmostEqual(cs.chi2_critical_value(0.001, 9), 27.877, delta=5e-4)
        self.assertAlmostEqual(cs.chi2_critical_value(0.001, 2), -2 * math.log(0.001), places=10)

    def test_R5_the_printed_27_887_is_not_the_0_999_quantile(self):
        # 5.2.4 (PDF p. 47): "the critical value at 0.001, which is 27.887".
        # The 0.999 quantile of chi-square(9) is 27.877; 27.887 sits beyond it.
        self.assertEqual(cs.BINARY_GOF_CRITICAL_PRINTED, 27.887)
        self.assertLess(cs.chi2_sf(27.887, 9), 0.001)
        self.assertGreater(cs.chi2_sf(27.877, 9), 0.001)
        self.assertLess(cs.chi2_critical_value(0.001, 9), 27.887)

    def test_edges_and_large_df(self):
        self.assertEqual(cs.chi2_sf(0.0, 5), 1.0)
        self.assertEqual(cs.chi2_sf(float("inf"), 5), 0.0)
        self.assertTrue(math.isnan(cs.chi2_sf(float("nan"), 5)))
        with self.assertRaises(ValueError):
            cs.chi2_sf(1.0, 0)
        # mean of chi-square(df) is df: the median is just below it, sf ~ 0.5
        self.assertAlmostEqual(cs.chi2_sf(50000.0, 50000), 0.5, delta=0.002)
        self.assertLess(cs.chi2_sf(51000.0, 50000), 0.001)
        self.assertGreater(cs.chi2_sf(49000.0, 50000), 0.999)


# ==========================================================================
# 5.2.1  Example 11 (PDF p. 44)
# ==========================================================================

# "Let S be (2, 2, 3, 1, 3, 2, 3, 2, 1, 3, 1, 1, 2, 3, 1, 1, 2, 2, 2, 3, 3, 2, 3, 2,
#  3, 1, 2, 2, 3, 3, 2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 3, 2, 3, 1, 2, 2, 3, 1, 1, 3,
#  2, 3, 2, 3, 1, 2, 2, 3, 3, 2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 2, 2, 3, 3, 3, 2, 3,
#  2, 1, 2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 3, 2, 3, 1, 2, 2, 3, 1, 1)."
EX11 = [2, 2, 3, 1, 3, 2, 3, 2, 1, 3, 1, 1, 2, 3, 1, 1, 2, 2, 2, 3, 3, 2, 3, 2, 3, 1, 2, 2, 3, 3,
        2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 3, 2, 3, 1, 2, 2, 3, 1, 1, 3, 2, 3, 2, 3, 1, 2, 2, 3, 3,
        2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 2, 2, 3, 3, 3, 2, 3, 2, 1, 2, 2, 2, 1, 3, 3, 3, 2, 3, 2,
        1, 3, 2, 3, 1, 2, 2, 3, 1, 1]


class Example11Independence(unittest.TestCase):
    """"The alphabet consists of k = 3 values {1, 2, 3}; and p1, p2, and p3 are
    0.21, 0.41 and 0.38, respectively.  With L = 100, the sorted expected values
    are calculated as:
      (zi,zj) (1,1) (1,3) (3,1) (1,2) (2,1) (3,3) (2,3) (3,2) (2,2)
      e_ij    2.21  3.99  3.99  4.31  4.31  7.22  7.79  7.79  8.41
    The pairs can be allocated into nbin = 6 bins.
      Bin 1 (1,1),(1,3) 6.2 | 2 (3,1),(1,2) 8.3 | 3 (2,1),(3,3) 11.53 |
      4 (2,3) 7.79 | 5 (3,2) 7.79 | 6 (2,2) 8.41
    The frequencies for the bins are calculated as 7, 6, 10, 8, 12, and 7
    respectively, and the test statistic is calculated as 3.46.  The value of
    the degrees of freedom is 3 (= 6-3).  The hypothesis is not rejected, since
    the test statistic is less than the critical value 16.266."

    Hand check of T from the exact expectations (c = 21, 41, 38, L = 100,
    e_ij = c_i c_j / 200):  E = 6.195, 8.295, 11.525, 7.79, 7.79, 8.405;
      (7-6.195)^2/6.195   = 0.10462
      (6-8.295)^2/8.295   = 0.63496
      (10-11.525)^2/11.525= 0.20179
      (8-7.79)^2/7.79     = 0.00566
      (12-7.79)^2/7.79    = 2.27523
      (7-8.405)^2/8.405   = 0.23486     sum = 3.4571  -> "3.46"."""

    def setUp(self):
        self.assertEqual(len(EX11), 100)
        self.r = cs.independence_non_binary(np.array(EX11), 2)

    def test_alphabet_and_proportions(self):
        self.assertEqual(self.r["L"], 100)
        self.assertEqual(self.r["k"], 3)

    def test_bins_match_the_table(self):
        bins = self.r["bins"]
        self.assertEqual(self.r["nbin"], 6)
        self.assertEqual([b["pairs"] for b in bins],
                         [[(1, 1), (1, 3)], [(3, 1), (1, 2)], [(2, 1), (3, 3)], [(2, 3)], [(3, 2)], [(2, 2)]])
        for b, printed in zip(bins, (6.2, 8.3, 11.53, 7.79, 7.79, 8.41)):
            self.assertAlmostEqual(b["E"], printed, delta=0.006)
        self.assertEqual([b["E"] for b in bins], [6.195, 8.295, 11.525, 7.79, 7.79, 8.405])

    def test_frequencies_statistic_and_decision(self):
        self.assertEqual([b["o"] for b in self.r["bins"]], [7, 6, 10, 8, 12, 7])
        self.assertEqual(self.r["npairs"], 50)
        self.assertAlmostEqual(self.r["T"], 3.46, delta=0.005)
        self.assertAlmostEqual(self.r["T"], 3.4571197, places=6)
        self.assertEqual(self.r["df"], 3)
        self.assertAlmostEqual(self.r["critical_value"], 16.266, delta=5e-4)
        self.assertTrue(self.r["applied"])
        self.assertFalse(self.r["failed"])
        self.assertFalse(self.r["fail_by_pvalue"])
        self.assertFalse(self.r["exact_boundary"])
        self.assertFalse(self.r["merged_last_two"])

    def test_R1_declared_alphabet_changes_only_k(self):
        # At 2 bits the value 0 is declared but absent: it adds 7 zero-expectation
        # pairs to the first bin and raises k to 4, so df = 6 - 4 = 2; T unchanged.
        d = cs.independence_non_binary(np.array(EX11), 2, alphabet="declared")
        self.assertEqual(d["k"], 4)
        self.assertEqual(d["nbin"], 6)
        self.assertEqual(d["df"], 2)
        self.assertAlmostEqual(d["T"], self.r["T"], places=12)
        first = d["bins"][0]["pairs"]
        self.assertEqual(len(first), 7 + 2)                      # 7 zero-expectation pairs with 0, then (1,1),(1,3)
        self.assertEqual(first[-2:], [(1, 1), (1, 3)])
        self.assertTrue(all(0 in pr for pr in first[:7]))

    def test_through_estimate_and_flat_labels(self):
        e = cs.estimate(EX11, 2)
        self.assertTrue(math.isnan(e["min_entropy"]))
        self.assertFalse(e["binary"])
        self.assertAlmostEqual(e["Chi square independence: T"], 3.4571197, places=6)
        self.assertEqual(e["Chi square independence: df"], 3)
        self.assertAlmostEqual(e["Chi square independence: P-value"], cs.chi2_sf(e["Chi square independence: T"], 3))


# ==========================================================================
# 5.2.2  Example 12 (PDF p. 45)
# ==========================================================================

class Example12GoodnessOfFitBinning(unittest.TestCase):
    """"Let the number of distinct sample values k be 4; and let c1 = 43, c2 = 55,
    c3 = 52 and c4 = 10. ... e1 = 4.3, e2 = 5.5, e3 = 5.2 and e4 = 1.  The sample
    list starting with the smallest expected value is formed as List = [4, 1, 3,
    2].  The first bin contains sample 4 and 1, and the expected value of Bin 1
    becomes 5.3 (= e4+e1).  The second bin contains sample 3, and the last bin
    contains sample 2.  Since the expected value of the last bin is greater than
    five, no additional merging is necessary."

    The example gives counts only, so any sequence with those counts tests the
    binning.  Symbol x_i is encoded as the value i-1 (x4 -> 3).  L = 160."""

    def setUp(self):
        self.S = np.array([0] * 43 + [1] * 55 + [2] * 52 + [3] * 10)
        self.r = cs.goodness_of_fit_non_binary(self.S, 2)

    def test_bins(self):
        self.assertEqual(self.r["k"], 4)
        self.assertEqual(self.r["nbin"], 3)
        self.assertEqual([b["values"] for b in self.r["bins"]], [[3, 0], [2], [1]])
        self.assertEqual([round(b["E"], 10) for b in self.r["bins"]], [5.3, 5.2, 5.5])
        self.assertFalse(self.r["merged_last_two"])
        self.assertEqual(self.r["df"], 9 * (3 - 1))

    def test_statistic_by_hand_on_the_sorted_sequence(self):
        # L = 160, subsets of 16.  Bin membership along the sorted sequence:
        #   S_0, S_1: 16 of value 0 (bin 1)                    o = (16, 0, 0)
        #   S_2: 11 of value 0 (bin 1) + 5 of value 1 (bin 3)  o = (11, 0, 5)
        #   S_3..S_5: 16 of value 1 (bin 3)                    o = (0, 0, 16)
        #   S_6: 2 of value 1 (bin 3) + 14 of value 2 (bin 2)  o = (0, 14, 2)
        #   S_7, S_8: 16 of value 2 (bin 2)                    o = (0, 16, 0)
        #   S_9: 6 of value 2 (bin 2) + 10 of value 3 (bin 1)  o = (10, 6, 0)
        # E = (5.3, 5.2, 5.5).  Summing (o-E)^2/E over the ten subsets:
        E = (5.3, 5.2, 5.5)
        rows = [(16, 0, 0)] * 2 + [(11, 0, 5)] + [(0, 0, 16)] * 3 + [(0, 14, 2)] + [(0, 16, 0)] * 2 + [(10, 6, 0)]
        T_hand = sum((o - e) ** 2 / e for row in rows for o, e in zip(row, E))
        self.assertEqual([b["o"] for b in self.r["bins"]], [list(c) for c in zip(*rows)])
        self.assertAlmostEqual(self.r["T"], T_hand, places=9)
        self.assertTrue(self.r["failed"])          # a sorted sequence is not identically distributed over time

    def test_remainder_is_not_used_but_counts_are_from_all_of_S(self):
        # L = 163: three trailing samples are not in any S_d, yet E_i = c_i/10 counts them.
        S = np.concatenate([self.S, [3, 3, 3]])
        r = cs.goodness_of_fit_non_binary(S, 2)
        self.assertEqual(r["subset_length"], 16)
        self.assertAlmostEqual(sum(b["E"] for b in r["bins"]), 16.3, places=12)


# ==========================================================================
# 5.2.3  Binary independence (PDF p. 45-46)
# ==========================================================================

class BinaryIndependence(unittest.TestCase):

    def test_spec_example_m(self):
        # "for p0 = 0.14, p1 = 0.86, and L = 1000, m = 2":
        #   m=2: 0.14^2 * 500 = 9.8 >= 5;  m=3: 0.14^3 * 333 = 0.914 < 5.
        self.assertEqual(cs.binary_tuple_length_m(860, 140, 1000)["m"], 2)

    def test_cap_at_11(self):
        # uniform 10^6 bits: 0.5^13 * 76923 = 9.39 >= 5, 0.5^14 * 71428 = 4.36 < 5 -> 13, capped to 11
        r = cs.binary_tuple_length_m(500000, 500000, 1000000)
        self.assertEqual((r["m"], r["m_uncapped_floor"]), (11, 13))

    def test_exact_boundary_3162_3163(self):
        # m = 2 needs c^2 * 500000 >= 5 * 10^12, i.e. c^2 >= 10^7, c >= 3162.28 -> 3163.
        self.assertEqual(cs.binary_tuple_length_m(1000000 - 3162, 3162, 1000000)["m"], 1)
        self.assertEqual(cs.binary_tuple_length_m(1000000 - 3163, 3163, 1000000)["m"], 2)

    def test_R4_no_m_at_all(self):
        # fewer than five minority bits: not even m = 1 satisfies c_min * L >= 5 L
        r = cs.binary_tuple_length_m(996, 4, 1000)
        self.assertEqual((r["m"], r["m_found"]), (0, False))
        self.assertEqual(cs.binary_tuple_length_m(1000, 0, 1000)["m"], 0)

    def test_m1_fails_the_test(self):
        # 20 alternating bits: m=1: 0.5*20 = 10 >= 5; m=2: 0.25*10 = 2.5 < 5 -> m = 1 -> "the test fails"
        r = cs.independence_binary(np.array([0, 1] * 10))
        self.assertEqual(r["m"], 1)
        self.assertTrue(r["failed"])
        self.assertFalse(r["applied"])
        self.assertTrue(math.isnan(r["T"]))

    def test_alternating_40_by_hand(self):
        # L = 40, p0 = p1 = 0.5.  m = 2 exactly at the boundary: 0.25 * 20 = 5 >= 5;
        # m = 3: 0.125 * 13 = 1.625 < 5.  Twenty blocks, all "01".  e = 0.25 * 20 = 5
        # for each of the four tuples.  T = (0-5)^2/5 + (20-5)^2/5 + (0-5)^2/5 + (0-5)^2/5
        #   = 5 + 45 + 5 + 5 = 60.  df = 2^2 - 2 = 2.  P = exp(-30) = 9.36e-14 -> fails.
        r = cs.independence_binary(np.array([0, 1] * 20))
        self.assertEqual(r["m"], 2)
        self.assertEqual(r["nblocks"], 20)
        self.assertEqual(r["T"], 60.0)
        self.assertEqual(r["df"], 2)
        self.assertAlmostEqual(r["P-value"], math.exp(-30), delta=1e-27)
        self.assertTrue(r["failed"])

    def test_uniform_random_bits_pass(self):
        rng = np.random.default_rng(3)
        r = cs.independence_binary(rng.integers(0, 2, 20000))
        self.assertGreaterEqual(r["m"], 2)
        self.assertEqual(r["df"], (1 << r["m"]) - 2)
        self.assertFalse(r["failed"])


# ==========================================================================
# 5.2.4  Binary goodness of fit (PDF p. 46-47)
# ==========================================================================

class BinaryGoodnessOfFit(unittest.TestCase):

    def test_alternating_40_is_perfectly_fitted(self):
        # q = 4, e0 = e1 = 2; every S_d = 0101 has o0 = o1 = 2 -> T = 0 -> passes
        r = cs.goodness_of_fit_binary(np.array([0, 1] * 20))
        self.assertEqual((r["subset_length"], r["e0"], r["e1"], r["T"]), (4, 2.0, 2.0, 0.0))
        self.assertEqual(r["df"], 9)
        self.assertEqual(r["P-value"], 1.0)
        self.assertFalse(r["failed"])

    def test_ten_ones_then_ten_zeros_by_hand(self):
        # p = 0.5, q = 2, e0 = e1 = 1.  d = 0..4: S_d = 11 -> (0-1)^2/1 + (2-1)^2/1 = 2;
        # d = 5..9: S_d = 00 -> 2.  T = 10 * 2 = 20, df = 9: sf(20, 9) = 0.0179 -> passes
        r = cs.goodness_of_fit_binary(np.array([1] * 10 + [0] * 10))
        self.assertEqual(r["T"], 20.0)
        self.assertAlmostEqual(r["P-value"], 0.0179, delta=1e-4)
        self.assertFalse(r["failed"])
        self.assertFalse(r["fail_by_printed_critical_value"])

    def test_R6_constant_bits_not_applied(self):
        r = cs.goodness_of_fit_binary(np.zeros(100, dtype=int))
        self.assertTrue(math.isnan(r["T"]))
        self.assertFalse(r["applied"])
        self.assertFalse(r["failed"])
        self.assertIn("0/0", r["not_applied_reason"])

    def test_R5_both_decisions_reported(self):
        r = cs.goodness_of_fit_binary(np.array([1] * 10 + [0] * 10))
        self.assertIn("fail_by_pvalue", r)
        self.assertIn("fail_by_printed_critical_value", r)
        self.assertEqual(r["printed_critical_value"], 27.887)
        p = cs.goodness_of_fit_binary(np.array([1] * 10 + [0] * 10), variant="pvalue")
        self.assertEqual(p["failed"], p["fail_by_pvalue"])

    def test_strongly_drifting_bits_fail(self):
        # 1000 bits: first half 90 % ones, second half 10 % ones
        rng = np.random.default_rng(5)
        S = np.concatenate([(rng.random(500) < 0.9).astype(int), (rng.random(500) < 0.1).astype(int)])
        r = cs.goodness_of_fit_binary(S)
        self.assertTrue(r["failed"])
        self.assertTrue(r["fail_by_pvalue"])
        self.assertTrue(r["fail_by_printed_critical_value"])


# ==========================================================================
# 5.2.5  Length of the longest repeated substring test (PDF p. 47)
# ==========================================================================

class LongestRepeatedSubstring(unittest.TestCase):

    def test_W_suffix_equals_direct_on_random_inputs(self):
        rng = np.random.default_rng(11)
        for n in list(range(1, 25)) + [40, 60, 97]:
            for k in (2, 3, 4, 16):
                S = rng.integers(0, k, n)
                self.assertEqual(cs.longest_repeated_substring_suffix(S),
                                 cs.longest_repeated_substring_direct(S), msg=f"n={n} k={k} S={S.tolist()}")

    def test_W_edge_cases(self):
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([5])), 0)
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([5, 5])), 1)
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([5, 6])), 0)
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([7, 7, 7, 7])), 3)   # overlapping (R8)
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([0, 1, 2, 3, 0, 1, 2])), 3)
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([0, 1, 2, 3, 4, 5, 6, 7])), 0)
        self.assertEqual(cs.longest_repeated_substring_suffix(np.array([1, 0, 1, 0, 1])), 3)   # "101" at 0 and 2

    def test_hand_example_01011(self):
        # S = (0,1,0,1,1), L = 5: counts 2, 3 -> p_col = (4 + 9)/25 = 13/25 = 0.52.
        # Repeats: "01" at positions 1 and 3; no 3-repeat ("010" vs "011") -> W = 2.
        # L-W+1 = 4 subsequences, N = C(4,2) = 6.
        # Pr(X >= 1) = 1 - (1 - 0.52^2)^6 = 1 - (1 - 0.2704)^6 = 1 - (456/625)^6.
        r = cs.lrs_length_test(np.array([0, 1, 0, 1, 1]), 1)
        self.assertEqual(r["P_col"], 0.52)
        self.assertEqual((r["W"], r["N"]), (2, 6))
        exact = 1 - Fraction(456, 625) ** 6
        self.assertAlmostEqual(r["Pr(X >= 1)"], float(exact), places=14)
        self.assertTrue(r["passed"])
        self.assertEqual((r["W_suffix"], r["W_direct"]), (2, 2))

    def test_alternating_40_by_hand(self):
        # p_col = 0.5.  "0101...": the suffixes at 0 and 2 agree for 38 symbols -> W = 38.
        # N = C(40-38+1, 2) = C(3,2) = 3.  Pr = 1 - (1 - 2^-38)^3 ~= 3 * 2^-38 = 1.09e-11 -> fails.
        r = cs.lrs_length_test(np.array([0, 1] * 20), 1)
        self.assertEqual((r["P_col"], r["W"], r["N"]), (0.5, 38, 3))
        self.assertAlmostEqual(r["Pr(X >= 1)"], float(1 - (1 - Fraction(1, 2 ** 38)) ** 3), delta=1e-22)
        self.assertFalse(r["passed"])

    def test_degenerate_constant_sequence_passes(self):
        # (7,7,7,7): k = 1, p_col = 1, W = 3, N = C(2,2) = 1, Pr = 1 - (1-1)^1 = 1 -> passes
        r = cs.lrs_length_test(np.array([7, 7, 7, 7]), 8)
        self.assertEqual((r["k"], r["P_col"], r["W"], r["N"], r["Pr(X >= 1)"]), (1, 1.0, 3, 1, 1.0))
        self.assertTrue(r["passed"])

    def test_underflow_path(self):
        # p_col = 1/256 (every byte value equally often), with a repeat so long that
        # p_col^W underflows: W >= 135 gives 2^-1080.  The sequence 0..255 repeated
        # eight times (L = 2048): the suffix at 256 is a prefix of the suffix at 0, so
        # the longest repeat is 2048 - 256 = 7*256 = 1792.
        S = np.tile(np.arange(256), 8)
        r = cs.lrs_length_test(S, 8, method="suffix")
        self.assertEqual(r["P_col"], 1 / 256)
        self.assertEqual(r["W"], 7 * 256)             # suffix at 0 vs suffix at 256: 1792 symbols in common
        self.assertTrue(r["p_col^W underflowed"])
        self.assertEqual(r["Pr(X >= 1)"], 0.0)       # first-order term N p^W also underflows
        self.assertFalse(r["passed"])

    def test_auto_cross_checks_and_method_choice(self):
        S = np.random.default_rng(2).integers(0, 4, 300)
        a = cs.lrs_length_test(S, 2, method="auto")
        self.assertIsNotNone(a["W_direct"])
        self.assertEqual(a["W_suffix"], a["W_direct"])
        s = cs.lrs_length_test(S, 2, method="suffix")
        self.assertIsNone(s["W_direct"])
        self.assertEqual(s["W"], a["W"])


# ==========================================================================
# Degenerate whole-battery cases and estimate() plumbing
# ==========================================================================

class Degenerate(unittest.TestCase):

    def test_all_one_symbol_8bit(self):
        # (7,7,7,7) at 8 bits.  Independence: one pair type, e = L/2 = 2 < 5, a single
        # bin that cannot be merged, nbin = 1, df = 1 - 1 = 0 -> "do not apply".
        # GoF: c = 4, e = 0.4, one bin, E = 0.4; floor(4/10) = 0 so every S_d is empty,
        # o = 0 and T = 10 * (0 - 0.4)^2 / 0.4 = 4.0; df = 9 * 0 = 0 -> not applied (R3
        # default) / fails under the degenerate reading.  LRS: passes (above).
        e = cs.estimate([7, 7, 7, 7], 8)
        ind, gof = e["chi_square_independence"], e["chi_square_goodness_of_fit"]
        self.assertEqual((ind["nbin"], ind["df"], ind["applied"], ind["failed"]), (1, 0, False, False))
        self.assertEqual(ind["bins"], [{"pairs": [(7, 7)], "E": 2.0, "o": 2}])
        self.assertEqual((gof["nbin"], gof["df"], gof["applied"], gof["failed"]), (1, 0, False, False))
        self.assertAlmostEqual(gof["T"], 4.0, places=12)
        self.assertTrue(gof["failed_if_df_zero_degenerate"])
        self.assertEqual(e["Chi square tests"], "Passed")
        self.assertEqual(e["Length of longest repeated substring test"], "Passed")
        self.assertTrue(e["section_5_2_passed"])
        d = cs.estimate([7, 7, 7, 7], 8, gof_df_zero="degenerate")
        self.assertTrue(d["chi_square_goodness_of_fit"]["failed"])
        self.assertEqual(d["Chi square tests"], "Failed")

    def test_all_zero_bits(self):
        e = cs.estimate(np.zeros(100, dtype=int), 1)
        self.assertTrue(e["binary"])
        self.assertEqual(e["chi_square_independence"]["m"], 0)
        self.assertTrue(e["chi_square_independence"]["failed"])
        self.assertFalse(e["chi_square_goodness_of_fit"]["applied"])
        self.assertEqual(e["Chi square tests"], "Failed")
        self.assertEqual(e["lrs_length_test"]["P_col"], 1.0)
        self.assertEqual(e["Length of longest repeated substring test"], "Passed")

    def test_single_symbol(self):
        e = cs.estimate([3], 2)
        self.assertFalse(e["chi_square_independence"]["applied"])
        self.assertFalse(e["chi_square_goodness_of_fit"]["applied"])
        self.assertEqual(e["lrs_length_test"]["W"], 0)
        self.assertEqual(e["lrs_length_test"]["Pr(X >= 1)"], 1.0)

    def test_R7_binary_is_the_declared_width(self):
        # bytes that happen to be only 0/1 are NON-binary data at 8 bits (k = 2), binary when told so
        S = np.random.default_rng(9).integers(0, 2, 2000)
        nb = cs.estimate(S, 8)
        self.assertFalse(nb["binary"])
        self.assertEqual(nb["chi_square_independence"]["k"], 2)
        self.assertIn("nbin", nb["chi_square_independence"])
        b = cs.estimate(S, 8, binary=True)
        self.assertTrue(b["binary"])
        self.assertIn("m", b["chi_square_independence"])
        same = cs.estimate(S, 1)
        self.assertEqual(b["Chi square independence: T"], same["Chi square independence: T"])

    def test_odd_length_uses_floor_pairs(self):
        S = np.random.default_rng(4).integers(0, 4, 1001)
        r = cs.independence_non_binary(S, 2)
        self.assertEqual(r["npairs"], 500)
        self.assertEqual(sum(b["o"] for b in r["bins"]), 500)

    def test_bitstring_track(self):
        raw = np.random.default_rng(21).integers(0, 256, 300)
        e = cs.estimate(raw, 8, track="bitstring")
        self.assertEqual(e["L"], 2400)
        self.assertTrue(e["binary"])
        bits = cs.to_bitstring(raw, 8)
        self.assertEqual(bits[:8].tolist(), [int(c) for c in format(int(raw[0]), "08b")])
        direct = cs.estimate(bits, 1)
        self.assertEqual(e["Chi square independence: T"], direct["Chi square independence: T"])
        self.assertIn("Bitstring Longest Repeated Substring results: W", e)
        lim = cs.estimate(raw, 8, track="bitstring", bitstring_limit=1000)
        self.assertEqual(lim["L"], 1000)

    def test_unknown_option_and_bad_symbols(self):
        with self.assertRaises(TypeError):
            cs.estimate([0, 1], 1, nonsense=1)
        with self.assertRaises(ValueError):
            cs.estimate([0, 2], 1)
        with self.assertRaises(ValueError):
            cs.estimate([0, 1], 1, variant="x")

    def test_flat_labels_present(self):
        e = cs.estimate(EX11, 2)
        for key in ("Chi square independence: T", "Chi square independence: df",
                    "Chi square independence: P-value", "Chi square goodness of fit: T",
                    "Chi square goodness of fit: df", "Chi square goodness of fit: P-value",
                    "Chi square tests", "Literal Longest Repeated Substring results: P_col",
                    "Literal Longest Repeated Substring results: W",
                    "Literal Longest Repeated Substring results: Pr(X >= 1)",
                    "Length of longest repeated substring test", "min_entropy"):
            self.assertIn(key, e)


# ==========================================================================
# __main__
# ==========================================================================

class CommandLine(unittest.TestCase):

    def run_cli(self, data: bytes, *args):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
            fh.write(data)
            path = fh.name
        try:
            proc = subprocess.run([sys.executable, MODULE, path, *args], capture_output=True, text=True)
        finally:
            os.unlink(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_example_11_through_the_cli(self):
        out = self.run_cli(bytes(EX11), "2")
        self.assertAlmostEqual(out["Chi square independence: T"], 3.4571197, places=6)
        self.assertEqual(out["Chi square independence: df"], 3)
        self.assertEqual(out["Chi square tests"], "Passed")
        self.assertTrue(math.isnan(out["min_entropy"]))
        self.assertEqual(out["track"], "literal")

    def test_low_bits_are_the_symbol(self):
        # 0xF2 at 2 bits is the symbol 2
        out = self.run_cli(bytes([0xF2, 0xF1, 0xF3, 0xF0] * 30), "2")
        self.assertEqual(out["chi_square_independence"]["k"], 4)

    def test_bitstring_cli_matches_estimate(self):
        raw = np.random.default_rng(23).integers(0, 256, 200).astype(np.uint8)
        out = self.run_cli(raw.tobytes(), "8", "--bitstring")
        ref = cs.estimate(raw.astype(int), 8, track="bitstring")
        self.assertEqual(out["L"], 1600)
        self.assertEqual(out["Chi square independence: T"], ref["Chi square independence: T"])
        self.assertEqual(out["Bitstring Longest Repeated Substring results: W"],
                         ref["Bitstring Longest Repeated Substring results: W"])

    def test_variant_and_usage(self):
        out = self.run_cli(bytes(EX11), "2", "--variant", "pvalue", "--alphabet", "declared")
        self.assertEqual((out["variant"], out["alphabet"]), ("pvalue", "declared"))
        proc = subprocess.run([sys.executable, MODULE], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage", proc.stderr)


# ==========================================================================
# End to end against the captured C++ labels (the input lives outside cpp/)
# ==========================================================================

class CapturedLabelsRand8Short(unittest.TestCase):
    """reference/cpp-verbose-labels-iid.txt was produced on bin/rand8_short.bin
    (10000 8-bit samples, sha256 17d2eaf9...).  Its lines:
        Chi square independence: T = 1026.2423761301056  df = 735  P-value = 5.5143772576210119e-12
        Chi square goodness of fit: T = 1288.2367907397536  df = 1206  P-value = 0.049333049713476802
        Literal Longest Repeated Substring results: P_col = 0.004008299999999994159272  W = 3
        Literal Longest Repeated Substring results: Pr(X >= 1) = 0.9599790286591446397679
    This reading reproduces the goodness-of-fit and LRS values to 14-15 digits and
    the independence df (hence nbin = 991), but NOT the independence T: it gives
    1057.337...  Thirteen tie-order / boundary readings of 5.2.1 step 2 were tried
    (logs/analysis-chisquare-ref-tieorder-probe.log); they span 991..1057 and none
    gives 1026.24.  The text does not fix the tie order (R2), so the test asserts
    only what the text does fix, and that the verdict agrees.  Not fitted."""

    PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(AUDIT_DIR))), "bin", "rand8_short.bin")

    def setUp(self):
        if not os.path.exists(self.PATH):
            self.skipTest(f"{self.PATH} not present")
        with open(self.PATH, "rb") as fh:
            raw = np.frombuffer(fh.read(), dtype=np.uint8)
        if raw.size != 10000:
            self.skipTest("unexpected file size")
        self.e = cs.estimate(raw.astype(int), 8)

    def test_goodness_of_fit_matches(self):
        g = self.e["chi_square_goodness_of_fit"]
        self.assertEqual(g["df"], 1206)
        self.assertAlmostEqual(g["T"], 1288.2367907397536, delta=1e-9)
        self.assertAlmostEqual(g["P-value"], 0.049333049713476802, delta=1e-12)

    def test_lrs_matches(self):
        l = self.e["lrs_length_test"]
        self.assertEqual(l["W"], 3)
        self.assertAlmostEqual(l["P_col"], 0.0040083, places=15)
        self.assertAlmostEqual(l["Pr(X >= 1)"], 0.9599790286591446, delta=2e-15)
        self.assertEqual(self.e["Length of longest repeated substring test"], "Passed")

    def test_independence_df_and_verdict_match_T_does_not(self):
        i = self.e["chi_square_independence"]
        self.assertEqual((i["df"], i["nbin"], i["k"]), (735, 991, 256))
        self.assertTrue(i["failed"])
        self.assertEqual(self.e["Chi square tests"], "Failed")
        # Recorded, not fitted: the captured T is 1026.2423761301056.
        self.assertNotAlmostEqual(i["T"], 1026.2423761301056, delta=1e-6)
        self.assertAlmostEqual(i["T"], 1057.3373111061478, delta=1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
