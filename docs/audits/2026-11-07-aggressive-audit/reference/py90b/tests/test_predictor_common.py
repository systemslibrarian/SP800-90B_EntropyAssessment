"""Tests for py90b.predictor_common -- the finish shared by SP 800-90B sections 6.3.7-6.3.10
(steps 4-7 of 6.3.7, PDF pp. 57-58, and their copies in 6.3.8-6.3.10).

Oracles, in order of authority:
  1. the standard's four worked examples (6.3.7 PDF p. 59, 6.3.8 PDF p. 60, 6.3.9 PDF p. 63,
     6.3.10 PDF p. 65), each of which prints `correct`, P_global, P'_global, P_local and the
     min-entropy;
  2. Appendix G.2 Table 3 (PDF p. 84), "P_local values for different r values when
     L = 1 000 000" -- 136 rows;
  3. closed forms derived by hand (in comments) for the degenerate inputs;
  4. the module's own decimal-arithmetic solve, which owes nothing to binary64.
Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_predictor_common.py -v
No C++ tool is run by these tests.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_REFERENCE = os.path.dirname(os.path.dirname(_HERE))                  # .../reference
sys.path.insert(0, _REFERENCE)

import numpy as np                                                    # noqa: E402

from py90b import predictor_common as pc                              # noqa: E402

LN_099 = math.log(0.99)


def _nan(v):
    return isinstance(v, float) and math.isnan(v)


# ==========================================================================================
# 1. The standard's worked examples.
# ==========================================================================================
class SpecWorkedExamples(unittest.TestCase):
    """Each example prints `correct` and the four figures.  k = 3 in all four: the alphabets
    are {0, 1, 2} (6.3.7) and {1, 2, 3} (6.3.8-6.3.10).  The printed figures are rounded to
    the digits shown, so each is checked at that rounding."""

    # (section, PDF page, correct, P_global, P'_global, P_local, min-entropy) as printed.
    EXAMPLES = [
        ("6.3.7",  59, [0, 0, 0, 1, 0, 1, 0, 0, 1], "0.3333", "0.7627", "0.036",  "0.3908"),
        ("6.3.8",  60, [0, 0, 0, 1, 1, 0, 0, 0, 0], "0.2222", "0.6008", "0.1167", "0.735"),
        ("6.3.9",  63, [0, 0, 1, 1, 0, 1, 0],       "0.4286", "0.9490", "0.1307", "0.0755"),
        ("6.3.10", 65, [0, 0, 1, 1, 0, 1, 1, 0],    "0.5",    "0.9868", "0.1229", "0.0191"),
    ]

    @staticmethod
    def _agrees_to_printed(value, printed):
        """Within one unit in the last printed place.  Not round-half-up, because the
        standard's own figures are not (ambiguity A8): 6.3.8 prints P'_global = 0.6008 for
        0.600859 (truncated), and 6.3.7 prints min-entropy 0.3908 for 0.390875, which is
        -log2 of the already-rounded 0.7627."""
        digits = len(printed.split(".")[1]) if "." in printed else 0
        return abs(value - float(printed)) < 10.0 ** (-digits)

    def test_examples_via_finish(self):
        for sec, page, correct, Pg, Pgp, Pl, H in self.EXAMPLES:
            with self.subTest(section=sec):
                N = len(correct)
                C = sum(correct)
                r = pc.run_parameter_r(correct)
                res = pc.finish(C, N, r, None, k=3)
                self.assertEqual(res["N"], N)
                self.assertEqual(res["C"], C)
                self.assertTrue(self._agrees_to_printed(res["P_global"], Pg), (sec, res["P_global"], Pg))
                self.assertTrue(self._agrees_to_printed(res["P_global'"], Pgp), (sec, res["P_global'"], Pgp))
                self.assertTrue(self._agrees_to_printed(res["P_local"], Pl), (sec, res["P_local"], Pl))
                self.assertTrue(self._agrees_to_printed(res["min_entropy"], H), (sec, res["min_entropy"], H))
                self.assertEqual(res["binding"], "P_global'")      # in all four, P'_global decides

    def test_examples_via_estimate_correct_array(self):
        for sec, page, correct, Pg, Pgp, Pl, H in self.EXAMPLES:
            with self.subTest(section=sec):
                res = pc.estimate(correct, 2, k=3)
                self.assertEqual(res["mode"], "correct-array")
                self.assertTrue(self._agrees_to_printed(res["min_entropy"], H))

    def test_example_r_values(self):
        # 6.3.7: longest run of ones in (0,0,0,1,0,1,0,0,1) is 1 -> r = 2
        # 6.3.8: (0,0,0,1,1,0,0,0,0) -> run 2 -> r = 3;  6.3.9: (0,0,1,1,0,1,0) -> r = 3
        # 6.3.10: (0,0,1,1,0,1,1,0) -> r = 3
        self.assertEqual([pc.run_parameter_r(e[2]) for e in self.EXAMPLES], [2, 3, 3, 3])

    def test_example_6_3_8_arithmetic_by_hand(self):
        # P_global = 2/9 = 0.2222222;  P_global (1 - P_global) / (N - 1) = 0.2222222 * 0.7777778 / 8
        # = 0.1728395 / 8 = 0.02160494;  sqrt = 0.14698619;  2.576 * 0.14698619 = 0.37863642;
        # P' = 0.2222222 + 0.37863642 = 0.60085864 -> printed "0.6008" (a truncation; A8).
        Pgp = pc.p_global_prime(2 / 9, 9)
        self.assertAlmostEqual(Pgp, 2 / 9 + 2.576 * math.sqrt((2 / 9) * (7 / 9) / 8), places=15)
        self.assertAlmostEqual(Pgp, 0.60085864, places=7)
        # min-entropy = -log2(max(0.60085864, 0.1167, 1/3)) = -log2(0.60085864) = 0.7349025 -> "0.735"
        self.assertAlmostEqual(-math.log2(Pgp), 0.7349025, places=6)

    def test_examples_exact_solve_agrees(self):
        """The decimal-arithmetic solve prints the same four decimals as the standard."""
        for sec, page, correct, Pg, Pgp, Pl, H in self.EXAMPLES:
            with self.subTest(section=sec):
                r = pc.run_parameter_r(correct)
                exact = pc.solve_p_local_exact(r, len(correct), digits=30)
                self.assertTrue(self._agrees_to_printed(float(exact), Pl), (sec, str(exact), Pl))


# ==========================================================================================
# 2. Appendix G.2 Table 3.
# ==========================================================================================
TABLE_3 = {
    1: 0.0000, 2: 0.0001, 3: 0.0022, 4: 0.0100, 5: 0.0253, 6: 0.0468, 7: 0.0728, 8: 0.1014,
    9: 0.1313, 10: 0.1614, 11: 0.1911, 12: 0.2200, 13: 0.2479, 14: 0.2746, 15: 0.3000,
    16: 0.3242, 17: 0.3471, 18: 0.3688, 19: 0.3893, 20: 0.4088, 21: 0.4272, 22: 0.4447,
    23: 0.4613, 24: 0.4770, 25: 0.4919, 26: 0.5060, 27: 0.5195, 28: 0.5323, 29: 0.5445,
    30: 0.5561, 31: 0.5672, 32: 0.5778, 33: 0.5879, 34: 0.5976, 35: 0.6068, 36: 0.6157,
    37: 0.6242, 38: 0.6324, 39: 0.6402, 40: 0.6477, 41: 0.6549, 42: 0.6619, 43: 0.6686,
    44: 0.6750, 45: 0.6812, 46: 0.6872, 47: 0.6930, 48: 0.6986, 49: 0.7040,
    # --- the 21 rows printed as r = 55 ... 155 (see TABLE_3_MISLABELLED) ---
    55: 0.7092, 60: 0.7328, 65: 0.7531, 70: 0.7705, 75: 0.7858, 80: 0.7992, 85: 0.8111,
    90: 0.8217, 95: 0.8312, 100: 0.8398, 105: 0.8476, 110: 0.8547, 115: 0.8612, 120: 0.8671,
    125: 0.8726, 130: 0.8776, 135: 0.8823, 140: 0.8867, 145: 0.8907, 150: 0.8945, 155: 0.8980,
    # --- correctly labelled again from r = 160 ---
    160: 0.9045, 165: 0.9074, 170: 0.9101, 175: 0.9127, 180: 0.9152, 185: 0.9175, 190: 0.9198,
    195: 0.9219, 200: 0.9239, 205: 0.9258, 210: 0.9276, 215: 0.9293, 220: 0.9309, 225: 0.9325,
    230: 0.9340, 235: 0.9355, 240: 0.9369, 245: 0.9382, 250: 0.9395, 255: 0.9407, 260: 0.9419,
    265: 0.9430, 270: 0.9441, 275: 0.9452, 280: 0.9462, 285: 0.9471, 290: 0.9481, 295: 0.9490,
    300: 0.9499, 310: 0.9516, 320: 0.9531, 330: 0.9546, 340: 0.9560, 350: 0.9573, 360: 0.9586,
    370: 0.9597, 380: 0.9609, 390: 0.9619, 400: 0.9629, 410: 0.9639, 420: 0.9648, 430: 0.9656,
    440: 0.9664, 450: 0.9672, 460: 0.9680, 470: 0.9687, 480: 0.9694, 490: 0.9700, 500: 0.9707,
    550: 0.9735, 600: 0.9758, 650: 0.9778, 700: 0.9795, 750: 0.9809, 800: 0.9822, 850: 0.9833,
    900: 0.9843, 950: 0.9852, 1000: 0.9860, 1500: 0.9909, 2000: 0.9933, 2500: 0.9947,
    3000: 0.9957, 4000: 0.9968, 5000: 0.9975, 10000: 0.9988,
}
TABLE_3_MISLABELLED = set(range(55, 156, 5))     # 55, 60, ..., 155: these rows hold P_local(r - 5)
L_TABLE = 1_000_000


class AppendixTable3(unittest.TestCase):
    def test_correctly_labelled_rows(self):
        """115 rows reproduce at four decimals with N = 1 000 000 (ambiguity A5)."""
        checked = 0
        for r, printed in TABLE_3.items():
            if r in TABLE_3_MISLABELLED:
                continue
            with self.subTest(r=r):
                self.assertEqual(round(pc.solve_p_local(r, L_TABLE), 4), printed, r)
                checked += 1
        self.assertEqual(checked, 136 - 21)

    def test_mislabelled_block_holds_values_for_r_minus_5(self):
        """Ambiguity A6: printed "55: 0.7092" is P_local(50), ..., "155: 0.8980" is P_local(150).
        This is a labelling error in the standard, recorded, not fudged: the code is not changed
        to reproduce the printed labels, and the test says what the rows actually contain."""
        for r in sorted(TABLE_3_MISLABELLED):
            with self.subTest(printed_r=r):
                printed = TABLE_3[r]
                self.assertNotEqual(round(pc.solve_p_local(r, L_TABLE), 4), printed,
                                    "row %d would be right as labelled" % r)
                self.assertEqual(round(pc.solve_p_local(r - 5, L_TABLE), 4), printed)
        # and the first correctly-labelled row after the block really is r = 160
        self.assertEqual(round(pc.solve_p_local(160, L_TABLE), 4), 0.9045)

    def test_table_does_not_distinguish_N_from_L_minus_2(self):
        """A5: at four decimals the table also matches N = L - 1 and N = L - 2 on every
        correctly labelled row (the four predictors' N are L-63, L-1, L-2, L-17)."""
        for N in (L_TABLE - 1, L_TABLE - 2):
            for r, printed in TABLE_3.items():
                if r in TABLE_3_MISLABELLED:
                    continue
                self.assertEqual(round(pc.solve_p_local(r, N), 4), printed, (N, r))


# ==========================================================================================
# 3. Hand-derived degenerate inputs.
# ==========================================================================================
class DegenerateInputs(unittest.TestCase):
    def test_no_correct_prediction_N9_k2_and_k256(self):
        # correct = nine zeros:  C = 0 -> "if P_global = 0": P' = 1 - 0.01^(1/9).
        #   ln 0.01 = -4.6051702; /9 = -0.5116856; e^that = 0.5994843; P' = 0.4005157.
        # r = 1 (longest run 0 + 1).  For r = 1 the recurrence x = 1 + q p x^2 converges
        # (for p < 1/2) to x = 1/q, and the right-hand side collapses to q^N (hand algebra:
        # (1 - p/q) / ((2 - 1/q) q) = 1/q, times q^(N+1)), so 0.99 = (1 - P_local)^9 and
        #   P_local = 1 - 0.99^(1/9): ln 0.99 = -0.01005034; /9 = -0.001116704;
        #   P_local = 1 - e^-0.001116704 = 0.0011160807.
        # k = 2: max(0.4005, 0.00112, 0.5) = 0.5 -> min-entropy = 1 exactly, 1/k binds.
        # k = 256: max(..., 1/256) = 0.4005157 -> min-entropy = -log2(0.4005157) = 1.320069.
        correct = [0] * 9
        res2 = pc.estimate(correct, 1)
        self.assertEqual((res2["C"], res2["r"], res2["N"], res2["k"]), (0, 1, 9, 2))
        self.assertEqual(res2["P_global"], 0.0)
        self.assertAlmostEqual(res2["P_global'"], 1 - 0.01 ** (1 / 9), places=15)
        self.assertAlmostEqual(res2["P_global'"], 0.4005157, places=7)
        self.assertAlmostEqual(res2["P_local"], 1 - 0.99 ** (1 / 9), delta=1e-15)
        self.assertAlmostEqual(res2["P_local"], 0.0011160807, places=10)
        self.assertEqual(res2["min_entropy"], 1.0)
        self.assertEqual(res2["binding"], "1/k")
        res256 = pc.estimate(correct, 8)
        self.assertEqual(res256["k"], 256)
        self.assertAlmostEqual(res256["min_entropy"], -math.log2(1 - 0.01 ** (1 / 9)), places=15)
        self.assertAlmostEqual(res256["min_entropy"], 1.320069, places=6)
        self.assertEqual(res256["binding"], "P_global'")

    def test_every_prediction_correct(self):
        # correct = nine ones: P_global = 1; sqrt(1 * 0 / 8) = 0 -> P' = min(1, 1) = 1;
        # min-entropy = -log2(1) = 0 (and +0.0, not -0.0).  r = 10 > N = 9 (ambiguity A4):
        # the formula still yields a number in (0, 1); it cannot bind because P' = 1.
        res = pc.estimate([1] * 9, 8)
        self.assertEqual((res["C"], res["r"], res["N"]), (9, 10, 9))
        self.assertEqual(res["P_global"], 1.0)
        self.assertEqual(res["P_global'"], 1.0)
        self.assertEqual(res["min_entropy"], 0.0)
        self.assertEqual(math.copysign(1.0, res["min_entropy"]), 1.0)
        self.assertEqual(res["binding"], "P_global'")
        self.assertTrue(0.0 < res["P_local"] < 1.0)
        self.assertFalse(res["P_local_changes_result"])

    def test_r1_closed_form_across_N(self):
        """r = 1 -> P_local = 1 - 0.99^(1/N) (derivation in the first test); at N = 1e6 that
        is -expm1(ln 0.99 / 1e6) = 1.0050336e-8, Table 3's "0.0000"."""
        for N in (1, 2, 9, 100, 10**4, 10**6):
            with self.subTest(N=N):
                want = -math.expm1(LN_099 / N)
                got = pc.solve_p_local(1, N)
                self.assertTrue(math.isclose(got, want, rel_tol=1e-12), (N, got, want))
        self.assertAlmostEqual(pc.solve_p_local(1, 10**6) * 1e8, 1.0050336, places=6)

    def test_N1(self):
        # N = 1, C = 0: P' = 1 - 0.01^1 = 0.99 (defined); r = 1; P_local = 1 - 0.99 = 0.01;
        # k = 2: max(0.99, 0.01, 0.5) = 0.99 -> min-entropy = -log2(0.99) = 0.0144996.
        res = pc.finish(0, 1, 1, 1)
        self.assertAlmostEqual(res["P_global'"], 0.99, places=15)
        self.assertAlmostEqual(res["P_local"], 0.01, places=14)
        self.assertAlmostEqual(res["min_entropy"], -math.log2(0.99), places=15)
        # N = 1, C = 1 (ambiguity A2): sqrt(1 * 0 / 0) has no value -> NaN, and NOT 1.0
        # (Python's min(1.0, nan) would return 1.0; the code must not go that way).
        res = pc.finish(1, 1, 2, 1)
        self.assertEqual(res["P_global"], 1.0)
        self.assertTrue(_nan(res["P_global'"]))
        self.assertTrue(_nan(res["min_entropy"]))
        self.assertIsNone(res["binding"])
        self.assertIsNone(res["P_local_changes_result"])

    def test_N0_all_nan(self):
        res = pc.finish(0, 0, 1, 1)
        for key in ("P_global", "P_global'", "P_local", "min_entropy"):
            self.assertTrue(_nan(res[key]), key)
        self.assertTrue(_nan(pc.solve_p_local(1, 0)))
        self.assertTrue(_nan(pc.solve_p_local(0, 5)))
        self.assertTrue(pc.solve_p_local_exact(1, 0).is_nan())
        res = pc.estimate([], 1)
        self.assertTrue(_nan(res["min_entropy"]))
        self.assertEqual(res["N"], 0)

    def test_p_global_prime_clamp_to_one(self):
        # P_global = 0.9, N = 2: 0.9 + 2.576 sqrt(0.09 / 1) = 0.9 + 0.7728 = 1.6728 -> min(1, .) = 1
        self.assertEqual(pc.p_global_prime(0.9, 2), 1.0)

    def test_z_variant_is_smaller_than_text(self):
        """Z_EXACT < 2.576, so the variant gives a smaller P' and a LARGER min-entropy
        (FORK-DIVERGENCE-AND-TRUST.md D-1: permissive direction).  Default must be the text."""
        text = pc.finish(39756, 79937, 15, 1)
        variant = pc.finish(39756, 79937, 15, 1, z=pc.Z_EXACT)
        self.assertEqual(text["z"], 2.576)
        self.assertLess(variant["P_global'"], text["P_global'"])
        self.assertGreater(variant["min_entropy"], text["min_entropy"])
        self.assertLess(variant["min_entropy"] - text["min_entropy"], 1e-6)


# ==========================================================================================
# 4. The solver: bisection soundness, precision against decimal arithmetic, variants.
# ==========================================================================================
class Solver(unittest.TestCase):
    GRID = [(r, N) for r in (1, 2, 3, 5, 10, 15, 36, 100, 1000) for N in (7, 9, 100, 9937, 79937, 999937, 10**6)]

    def test_rhs_is_one_at_zero_and_undefined_at_one(self):
        for r, N in ((1, 9), (3, 9), (36, 10**6)):
            self.assertEqual(pc.log_run_probability(0.0, r, N), 0.0)
            self.assertEqual(pc.log_run_probability(1.0, r, N), -math.inf)
        with self.assertRaises(ValueError):
            pc.log_run_probability(1.5, 2, 9)

    def test_returned_root_is_bracketed(self):
        """rhs(P_local (1 - 1e-6)) > 0.99 >= rhs(P_local (1 + 1e-6)) -- the root the bisection
        found is a crossing, with the function above 0.99 on its left."""
        for r, N in self.GRID:
            with self.subTest(r=r, N=N):
                p = pc.solve_p_local(r, N)
                self.assertTrue(0.0 < p < 1.0)
                self.assertGreater(pc.log_run_probability(p * (1 - 1e-6), r, N), LN_099)
                self.assertLessEqual(pc.log_run_probability(min(1.0, p * (1 + 1e-6)), r, N), LN_099)

    def test_single_crossing_on_a_grid(self):
        """The right-hand side crosses 0.99 exactly once on a 4 000-point sweep of (0, 1)
        for a spread of (r, N) -- so the bisection's crossing is THE crossing."""
        sweep = sorted(set([10.0 ** (-k / 20.0) for k in range(20, 200)] + [i / 4000.0 for i in range(1, 4000)]))
        for r, N in ((1, 9), (2, 7), (3, 8), (10, 9), (15, 100), (36, 10**6), (1000, 10**6), (5, 2), (11, 9)):
            with self.subTest(r=r, N=N):
                above = [pc.log_run_probability(p, r, N) > LN_099 for p in sweep]
                self.assertTrue(above[0])
                self.assertFalse(above[-1])
                self.assertEqual(sum(1 for a, b in zip(above, above[1:]) if a != b), 1)

    def test_binary64_solve_against_decimal_solve(self):
        """Relative error <= 2e-12 for N >= 100 (measured ~1e-14); at tiny N the equation is
        flat and binary64 evaluation of it costs tens of ulps (measured <= 60) -- the field
        P_local_ulp_error exists to show that."""
        for r, N in self.GRID:
            with self.subTest(r=r, N=N):
                got = pc.solve_p_local(r, N)
                exact = pc.solve_p_local_exact(r, N, digits=30)
                rel = abs(Decimal(got) - exact) / exact
                if N >= 100:
                    self.assertLess(rel, Decimal("2e-12"), (r, N, got, str(exact)))
                else:
                    ulps = abs(Decimal(got) - exact) / Decimal(math.ulp(got))
                    self.assertLess(ulps, 200, (r, N, got, str(exact)))

    def test_x10_versus_converged_recurrence(self):
        """Tracker F08: x_10 against the fixed point.  On Table 3's grid and the worked
        examples the two solves differ by less than 1e-12 (measured 0 at N = 1e6)."""
        cases = [(r, L_TABLE) for r in (1, 2, 3, 10, 36, 100, 1000, 10000)] + [(2, 9), (3, 9), (3, 7), (3, 8)]
        for r, N in cases:
            with self.subTest(r=r, N=N):
                a = pc.solve_p_local(r, N)
                b = pc.solve_p_local(r, N, steps="converge")
                self.assertLess(abs(a - b), 1e-12, (r, N, a, b))

    def test_tol_variant(self):
        full = pc.solve_p_local(36, L_TABLE)
        coarse = pc.solve_p_local(36, L_TABLE, tol=1e-6)
        self.assertLess(abs(full - coarse), 1e-6)
        self.assertNotEqual(full, coarse)

    def test_underflow_of_p_to_the_r_is_harmless(self):
        """0.5**1100 underflows to 0 in binary64; the bisection must still find Table 3's
        value for r = 1000 (0.9860) and the r = 10000 row (0.9988)."""
        self.assertEqual(round(pc.solve_p_local(1000, L_TABLE), 4), 0.9860)
        self.assertEqual(round(pc.solve_p_local(10000, L_TABLE), 4), 0.9988)

    def test_exact_solver_matches_table_3(self):
        for r in (2, 3, 4, 10, 36, 160, 1000, 10000):
            with self.subTest(r=r):
                self.assertEqual(round(float(pc.solve_p_local_exact(r, L_TABLE, digits=25)), 4), TABLE_3[r])

    def test_finish_exact_fields(self):
        res = pc.finish(3, 9, 2, None, k=3, exact=True, exact_digits=30)
        self.assertIn("P_local_exact", res)
        self.assertTrue(res["P_local_exact"].startswith("0.0359675587163"))
        self.assertLess(abs(res["P_local_ulp_error"]), 200)
        self.assertTrue(res["min_entropy_exact"].startswith("0.390875448604853"))


# ==========================================================================================
# 5. Step 4 / run length helpers and input handling.
# ==========================================================================================
class Helpers(unittest.TestCase):
    def test_longest_run(self):
        self.assertEqual(pc.longest_run_of_ones([]), 0)
        self.assertEqual(pc.longest_run_of_ones([0, 0, 0]), 0)
        self.assertEqual(pc.longest_run_of_ones([1]), 1)
        self.assertEqual(pc.longest_run_of_ones([1, 1, 0, 1, 1, 1, 0, 1]), 3)
        self.assertEqual(pc.longest_run_of_ones([1, 1, 1, 1]), 4)
        self.assertEqual(pc.longest_run_of_ones([0, 1, 1, 0, 1, 1]), 2)
        self.assertEqual(pc.run_parameter_r([0, 0, 0, 1, 1, 0, 0, 0, 0]), 3)
        self.assertEqual(pc.count_correct([0, 1, 1, 0, 1]), 3)

    def test_to_bitstring_msb_first(self):
        # glossary (PDF p. 69): "The leftmost bit is the most significant bit"
        self.assertEqual(pc.to_bitstring([0b101, 0b011], 3).tolist(), [1, 0, 1, 0, 1, 1])
        self.assertEqual(pc.to_bitstring([0x80, 0x01], 8).tolist(), [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(pc.to_bitstring([0, 1, 1, 0], 1).tolist(), [0, 1, 1, 0])

    def test_estimate_rejects_non_boolean_without_predictor(self):
        with self.assertRaises(ValueError):
            pc.estimate([0, 1, 2, 1, 0], 2)
        with self.assertRaises(ValueError):
            pc.estimate([0, 1, 4], 2)            # out of [0, 2**bits)
        with self.assertRaises(TypeError):
            pc.estimate([0, 1], 1, bogus=1)
        with self.assertRaises(ValueError):
            pc.estimate([0, 1], 1, predictor="nosuch")

    def test_estimate_k_handling(self):
        c = [0, 0, 1, 1, 0, 1, 1, 0]
        self.assertEqual(pc.estimate(c, 8)["k"], 256)
        self.assertEqual(pc.estimate(c, 8, bitstring=True)["k"], 2)
        self.assertEqual(pc.estimate(c, 8, k=3)["k"], 3)
        self.assertEqual(pc.estimate(c, 1)["k"], 2)

    def test_estimate_equals_finish(self):
        rng = np.random.default_rng(3)
        c = (rng.random(5000) < 0.3).astype(np.int64)
        a = pc.estimate(c, 8)
        b = pc.finish(int(c.sum()), 5000, pc.run_parameter_r(c), 8)
        for key in ("C", "r", "N", "k", "P_global", "P_global'", "P_local", "min_entropy", "binding"):
            self.assertEqual(a[key], b[key], key)

    def test_one_million_correct_array_is_fast(self):
        rng = np.random.default_rng(1)
        c = (rng.random(10**6) < 0.5).astype(np.int64)
        t0 = time.time()
        res = pc.estimate(c, 8)
        self.assertLess(time.time() - t0, 5.0)
        self.assertEqual(res["N"], 10**6)
        self.assertTrue(0.0 < res["min_entropy"] <= 8.0)


# ==========================================================================================
# 6. The sibling modules' fallback copies (guarded: they are written by other agents).
# ==========================================================================================
def _try_import(name):
    try:
        return __import__("py90b." + name, fromlist=[name])
    except Exception:           # noqa: BLE001 -- a sibling mid-write must not fail this suite
        return None


class SiblingFallbackCopies(unittest.TestCase):
    """The task: 'the four modules may also carry a fallback copy -- if they do, assert
    equality in tests'.  Measured (logs/reference-predictor-common-smoke.log and
    -lagdev-probe.log): p_global_prime is bit-identical in all four; the P_local copies in
    multimcw/multimmc/lz78y are within 1 ulp; lag's copy deviates by up to 1.03e-8 RELATIVE
    at (r=1, N=1e6) and 1.7e-10 absolute at (r=15, N=999937) because it evaluates ln(x)
    directly with x = 1 + O(1e-8) (module docstring, A9).  Equality is therefore asserted to
    1e-7 relative for lag, 1e-13 for the log1p-style copies, and the decimal solve is used
    to show, at every grid point, which side of a deviation is the accurate one."""

    GRID = Solver.GRID

    def _solver(self, mod):
        return getattr(mod, "solve_p_local", None) or getattr(mod, "p_local", None)

    def _check(self, name, rel_tol):
        mod = _try_import(name)
        if mod is None:
            self.skipTest("py90b.%s not importable" % name)
        solver = self._solver(mod)
        if solver is None:
            self.skipTest("py90b.%s carries no P_local copy" % name)
        for r, N in self.GRID:
            with self.subTest(r=r, N=N):
                mine, theirs = pc.solve_p_local(r, N), solver(r, N)
                self.assertTrue(math.isclose(mine, theirs, rel_tol=rel_tol), (name, r, N, mine, theirs))
        pgp = getattr(mod, "p_global_prime", None)
        if pgp is not None:
            for C, N in ((0, 9), (2, 9), (3, 7), (4, 8), (43, 9937), (39756, 79937), (0, 1)):
                mine = pc.p_global_prime(C / N, N)
                try:
                    theirs = pgp(C / N, N)
                    if isinstance(theirs, tuple):
                        raise TypeError
                except TypeError:
                    theirs = pgp(C, N)
                    theirs = theirs[1] if isinstance(theirs, tuple) else theirs
                self.assertEqual(mine, theirs, (name, C, N))

    def test_lag_copy(self):
        self._check("lag", 1e-7)

    def test_multimcw_copy(self):
        self._check("multimcw", 1e-13)

    def test_multimmc_copy(self):
        self._check("multimmc", 1e-13)

    def test_lz78y_copy(self):
        self._check("lz78y", 1e-13)

    def test_lag_deviation_is_on_lags_side(self):
        """Wherever lag's copy and this module differ by more than 1e-13 relative, THIS
        module's value is the one nearer the decimal solve.  (At the two measured worst
        points: (1, 1e6) mine is 2e-15 relative from the closed form 1 - 0.99^(1/N), lag's
        1.03e-8; (15, 999937) |mine - exact| = 1.7e-15, |lag - exact| = 1.7e-10.)"""
        mod = _try_import("lag")
        if mod is None or self._solver(mod) is None:
            self.skipTest("py90b.lag not importable")
        solver = self._solver(mod)
        adjudicated = 0
        for r, N in self.GRID:
            mine, theirs = pc.solve_p_local(r, N), solver(r, N)
            if math.isclose(mine, theirs, rel_tol=1e-13):
                continue
            with self.subTest(r=r, N=N):
                exact = pc.solve_p_local_exact(r, N, digits=30)
                self.assertLess(abs(Decimal(mine) - exact) / exact, Decimal("1e-12"), (r, N, mine, str(exact)))
                self.assertLess(abs(Decimal(mine) - exact), abs(Decimal(theirs) - exact), (r, N, mine, theirs, str(exact)))
                adjudicated += 1
        self.assertGreater(adjudicated, 0, "no deviation left to adjudicate: tighten test_lag_copy")

    def test_predictor_mode_matches_each_available_sibling(self):
        rng = np.random.default_rng(11)
        raw = rng.integers(0, 256, 400, dtype=np.int64)
        for name in ("lag", "multimcw", "multimmc", "lz78y"):
            if _try_import(name) is None:
                continue
            for bitstring in (False, True):
                with self.subTest(predictor=name, bitstring=bitstring):
                    res = pc.estimate(raw, 8, predictor=name, bitstring=bitstring)
                    self.assertEqual(res["mode"], "predictor")
                    self.assertEqual(res["k"], 2 if bitstring else 256)
                    self.assertTrue(res["finish_matches_sibling"], (name, bitstring, res["sibling"], res["P_local"]))
                    self.assertLess(res["sibling_max_rel_dev"], 1e-9, (name, bitstring))


# ==========================================================================================
# 7. The command line.
# ==========================================================================================
class CommandLine(unittest.TestCase):
    MODULE = os.path.join(_REFERENCE, "py90b", "predictor_common.py")

    def _run(self, *args):
        env = dict(os.environ, OMP_NUM_THREADS="2")
        return subprocess.run([sys.executable, self.MODULE, *args], capture_output=True, text=True, env=env)

    def test_correct_array_file(self):
        rng = np.random.default_rng(5)
        c = (rng.random(300) < 0.45).astype(np.uint8)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "correct.bin")
            c.tofile(path)
            proc = self._run(path, "8")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            want = pc.estimate(c.astype(np.int64), 8)
            for key in ("C", "r", "N", "k", "P_global", "P_global'", "P_local", "min_entropy"):
                self.assertEqual(out[key], want[key], key)
            self.assertEqual(out["input"]["samples"], 300)
            proc = self._run(path, "8", "--bitstring", "--exact", "--digits", "25")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["k"], 2)
            self.assertIn("P_local_exact", out)

    def test_non_boolean_file_is_refused_without_predictor(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "raw.bin")
            with open(path, "wb") as fh:
                fh.write(bytes([0, 1, 2, 1, 0, 3]))
            proc = self._run(path, "2")
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("correct", proc.stderr)

    def test_predictor_flag(self):
        if _try_import("lag") is None:
            self.skipTest("py90b.lag not importable")
        rng = np.random.default_rng(9)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "raw.bin")
            rng.integers(0, 256, 200, dtype=np.uint8).tofile(path)
            proc = self._run(path, "8", "--predictor=lag", "--bitstring")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["predictor"], "lag")
            self.assertTrue(out["finish_matches_sibling"], out)
            self.assertLess(out["sibling_max_rel_dev"], 1e-9)
            self.assertEqual(out["N"], 1599)                   # Lag: N = L - 1 on 1600 bits


if __name__ == "__main__":
    unittest.main()
