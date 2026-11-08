"""
Tests for py90b.multimmc -- SP 800-90B section 6.3.9, The MultiMMC Prediction Estimate.

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_multimmc.py -v
(or   <venv>/bin/python reference/py90b/tests/test_multimmc.py)

Every expected value below is either quoted from the standard (with the PDF page) or derived
BY HAND in the comment beside it.  Nothing is taken from the C++ tool's output.  The only
values taken from the module itself are in TestFastEqualsLiteral, which asserts that the two
transcriptions of steps 1-4 agree with each other, not that either is right.
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
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE.parent / "multimmc.py"


def _load():
    """Load multimmc.py straight from its file so this test does not depend on whatever else
    the py90b package may import."""
    spec = importlib.util.spec_from_file_location("py90b_multimmc_under_test", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mm = _load()
NULL = mm.NULL


def _flat(models_for_i):
    """Turn the module's per-order {ctx: {y: c}} into the spec table's {(ctx, y): c}."""
    return [{(ctx, y): c for ctx, ys in M.items() for y, c in ys.items()} for M in models_for_i]


# ============================================================================================
# the section's own worked example (PDF pp. 62-63)
# ============================================================================================
class TestSpecWorkedExample(unittest.TestCase):
    """'Suppose that S = (2, 1, 3, 2, 1, 3, 1, 3, 1), so that L = 9 and N = 7.  For the
    purpose of this example, further suppose that D = 3 (instead of 16).'  (PDF p. 62)"""

    S = [2, 1, 3, 2, 1, 3, 1, 3, 1]

    # The table on PDF p. 62, one row per i:
    #   (subpredict after 4.b, scoreboard at 4.c, winner at 4.c, prediction, s_i,
    #    correct_(i-2), scoreboard after 4.e)
    TABLE_P62 = {
        3: ((NULL, NULL, NULL), [0, 0, 0], 1, NULL, 3, 0, [0, 0, 0]),
        4: ((NULL, NULL, NULL), [0, 0, 0], 1, NULL, 2, 0, [0, 0, 0]),
        5: ((1, NULL, NULL),    [0, 0, 0], 1, 1,    1, 1, [1, 0, 0]),
        6: ((3, 3, NULL),       [1, 0, 0], 1, 3,    3, 1, [2, 1, 0]),
        7: ((2, 2, 2),          [2, 1, 0], 1, 2,    1, 0, [2, 1, 0]),
        8: ((3, NULL, NULL),    [2, 1, 0], 1, 3,    3, 1, [3, 1, 0]),
        9: ((2, 2, NULL),       [3, 1, 0], 1, 2,    1, 0, [3, 1, 0]),
    }

    # The table on PDF p. 63: 'Models M1, M2, and M3 are shown below after step 4a (the model
    # update step) for each value of i.'  {x->y:c} written here as {(x, y): c}.
    TABLE_P63 = {
        3: [{((2,), 1): 1}, {}, {}],
        4: [{((1,), 3): 1, ((2,), 1): 1}, {((2, 1), 3): 1}, {}],
        5: [{((1,), 3): 1, ((2,), 1): 1, ((3,), 2): 1},
            {((1, 3), 2): 1, ((2, 1), 3): 1},
            {((2, 1, 3), 2): 1}],
        6: [{((1,), 3): 1, ((2,), 1): 2, ((3,), 2): 1},
            {((1, 3), 2): 1, ((2, 1), 3): 1, ((3, 2), 1): 1},
            {((1, 3, 2), 1): 1, ((2, 1, 3), 2): 1}],
        7: [{((1,), 3): 2, ((2,), 1): 2, ((3,), 2): 1},
            {((1, 3), 2): 1, ((2, 1), 3): 2, ((3, 2), 1): 1},
            {((1, 3, 2), 1): 1, ((2, 1, 3), 2): 1, ((3, 2, 1), 3): 1}],
        8: [{((1,), 3): 2, ((2,), 1): 2, ((3,), 1): 1, ((3,), 2): 1},
            {((1, 3), 1): 1, ((1, 3), 2): 1, ((2, 1), 3): 2, ((3, 2), 1): 1},
            {((1, 3, 2), 1): 1, ((2, 1, 3), 1): 1, ((2, 1, 3), 2): 1, ((3, 2, 1), 3): 1}],
        9: [{((1,), 3): 3, ((2,), 1): 2, ((3,), 1): 1, ((3,), 2): 1},
            {((1, 3), 1): 1, ((1, 3), 2): 1, ((2, 1), 3): 2, ((3, 1), 3): 1, ((3, 2), 1): 1},
            {((1, 3, 1), 3): 1, ((1, 3, 2), 1): 1, ((2, 1, 3), 1): 1, ((2, 1, 3), 2): 1,
             ((3, 2, 1), 3): 1}],
    }

    def test_trace_rows_match_the_table_on_p62(self):
        r = mm.estimate(self.S, 2, D=3, trace=True)
        rows = {row["i"]: row for row in r["trace"]}
        self.assertEqual(sorted(rows), list(range(3, 10)))
        for i, (sub, sb_4c, win, pred, si, corr, sb_4e) in self.TABLE_P62.items():
            with self.subTest(i=i):
                row = rows[i]
                self.assertEqual(row["subpredict"], sub)
                self.assertEqual(row["scoreboard_4c"], sb_4c)
                self.assertEqual(row["winner_4c"], win)
                self.assertEqual(row["prediction"], pred)
                self.assertEqual(row["s_i"], si)
                self.assertEqual(row["correct"], corr)
                self.assertEqual(row["scoreboard_4e"], sb_4e)

    def test_models_match_the_table_on_p63(self):
        r = mm.estimate(self.S, 2, D=3, trace=True)
        for idx, i in enumerate(range(3, 10)):
            with self.subTest(i=i):
                self.assertEqual(_flat(r["models"][idx]), self.TABLE_P63[i])

    def test_tie_rule_at_i_9(self):
        # At i = 9, M1[(3), .] = {1: 1, 2: 1} and M2[(1, 3), .] = {1: 1, 2: 1} are ties;
        # 'If there is a tie, let ymax be the greatest y in the tie' -> 2 in both orders,
        # which is what the table prints: subpredict = (2, 2, Null).
        r = mm.estimate(self.S, 2, D=3, trace=True)
        row = r["trace"][-1]
        self.assertEqual(row["i"], 9)
        self.assertEqual(row["subpredict"], (2, 2, NULL))

    def _check_final_figures(self, r):
        # 'After the predictions are all made, correct = (0, 0, 1, 1, 0, 1, 0).  Then,
        #  P_global = 0.4286, P'_global = 0.9490, P_local = 0.1307, and the resulting
        #  min-entropy estimate is 0.0755.'  (PDF p. 63)
        self.assertEqual(r["L"], 9)
        self.assertEqual(r["N"], 7)                        # N = L - 2
        self.assertEqual(list(map(int, r["correct"])), [0, 0, 1, 1, 0, 1, 0])
        self.assertEqual(r["C"], 3)                        # three ones in correct
        self.assertAlmostEqual(r["P_global"], 3 / 7)       # = 0.428571...
        self.assertAlmostEqual(r["P_global"], 0.4286, places=4)
        # By hand: 3/7 + 2.576 * sqrt((3/7)(4/7)/6) = 0.428571 + 2.576 * sqrt(0.0408163)
        #        = 0.428571 + 2.576 * 0.2020305 = 0.428571 + 0.520431 = 0.949002
        self.assertAlmostEqual(r["P_global'"], 3 / 7 + 2.576 * math.sqrt((3 / 7) * (4 / 7) / 6))
        self.assertAlmostEqual(r["P_global'"], 0.9490, places=4)
        self.assertEqual(r["longest_run"], 2)              # the '1, 1' at positions 3-4
        self.assertEqual(r["r"], 3)                        # one greater than the longest run
        self.assertAlmostEqual(r["P_local"], 0.1307, places=4)
        self.assertEqual(r["binding"], "P_global'")        # 0.9490 > 0.1307 and > 1/k
        self.assertAlmostEqual(r["min_entropy"], -math.log2(r["P_global'"]))
        self.assertAlmostEqual(r["min_entropy"], 0.0755, places=4)
        self.assertEqual(r["min entropy"], r["min_entropy"])
        self.assertEqual(r["scoreboard"], [3, 1, 0])
        self.assertEqual(r["winner"], 1)
        self.assertFalse(r["cap_bound"])

    def test_final_figures_literal_method(self):
        self._check_final_figures(mm.estimate(self.S, 2, D=3, method="literal", return_arrays=True))

    def test_final_figures_fast_method(self):
        self._check_final_figures(mm.estimate(self.S, 2, D=3, method="fast", return_arrays=True))

    def test_k_does_not_bind_in_the_example(self):
        # The example's alphabet is {1, 2, 3} (k = 3, 1/k = 0.333); passing the symbols as
        # 2-bit values makes k_alphabet = 4 (1/k = 0.25).  Neither exceeds P'_global = 0.949,
        # so the figure is the same under both readings of k.
        a = mm.estimate(self.S, 2, D=3, k_mode="alphabet")
        b = mm.estimate(self.S, 2, D=3, k_mode="observed")
        self.assertEqual(a["k"], 4)
        self.assertEqual(b["k"], 3)
        self.assertEqual(a["min_entropy"], b["min_entropy"])

    def test_subpredict_arrays_align_between_methods(self):
        lit = mm.estimate(self.S, 2, D=3, method="literal", return_arrays=True)
        fast = mm.estimate(self.S, 2, D=3, method="fast", return_arrays=True)
        for d in range(3):
            for i in range(3, 10):
                # literal indexes by the spec's i; fast by the 0-based position i-1
                self.assertEqual(int(fast["subpredict"][d][i - 1]), lit["subpredict"][d][i])
        # the p62 table's subpredict column, order 1: Null, Null, 1, 3, 2, 3, 2
        self.assertEqual([int(v) for v in fast["subpredict"][0][2:]], [NULL, NULL, 1, 3, 2, 3, 2])


# ============================================================================================
# step 7's equation, against every P_local the standard prints
# ============================================================================================
class TestPLocalSolver(unittest.TestCase):

    def test_multimmc_example_r3_N7(self):
        # PDF p. 63: P_local = 0.1307 with r = 3 and N = 7
        self.assertAlmostEqual(mm.p_local(3, 7), 0.1307, places=4)

    def test_lag_example_r3_N9(self):
        # PDF p. 60 (section 6.3.8's example): correct = (0,0,0,1,1,0,0,0,0), so the longest
        # run is 2, r = 3, N = 9, and 'P_local = 0.1167'
        self.assertAlmostEqual(mm.p_local(3, 9), 0.1167, places=4)

    # Appendix G.2 Table 3 (PDF p. 84): 'P_local values for different r values when
    # L = 1 000 000'.  Reproduced in full so the misprint below is visible in context.
    TABLE3 = {
        1: 0.0000, 2: 0.0001, 3: 0.0022, 4: 0.0100, 5: 0.0253, 6: 0.0468, 7: 0.0728,
        8: 0.1014, 9: 0.1313, 10: 0.1614, 11: 0.1911, 12: 0.2200, 13: 0.2479, 14: 0.2746,
        15: 0.3000, 16: 0.3242, 17: 0.3471, 18: 0.3688, 19: 0.3893, 20: 0.4088, 21: 0.4272,
        22: 0.4447, 23: 0.4613, 24: 0.4770, 25: 0.4919, 26: 0.5060, 27: 0.5195, 28: 0.5323,
        29: 0.5445, 30: 0.5561, 31: 0.5672, 32: 0.5778, 33: 0.5879, 34: 0.5976, 35: 0.6068,
        36: 0.6157, 37: 0.6242, 38: 0.6324, 39: 0.6402, 40: 0.6477, 41: 0.6549, 42: 0.6619,
        43: 0.6686, 44: 0.6750, 45: 0.6812, 46: 0.6872, 47: 0.6930, 48: 0.6986, 49: 0.7040,
        55: 0.7092, 60: 0.7328, 65: 0.7531, 70: 0.7705, 75: 0.7858, 80: 0.7992, 85: 0.8111,
        90: 0.8217, 95: 0.8312, 100: 0.8398, 105: 0.8476, 110: 0.8547, 115: 0.8612,
        120: 0.8671, 125: 0.8726, 130: 0.8776, 135: 0.8823, 140: 0.8867, 145: 0.8907,
        150: 0.8945, 155: 0.8980,
        160: 0.9045, 165: 0.9074, 170: 0.9101, 175: 0.9127, 180: 0.9152, 185: 0.9175,
        190: 0.9198, 195: 0.9219, 200: 0.9239, 205: 0.9258, 210: 0.9276, 215: 0.9293,
        220: 0.9309, 225: 0.9325, 230: 0.9340, 235: 0.9355, 240: 0.9369, 245: 0.9382,
        250: 0.9395, 255: 0.9407, 260: 0.9419, 265: 0.9430, 270: 0.9441, 275: 0.9452,
        280: 0.9462, 285: 0.9471, 290: 0.9481, 295: 0.9490, 300: 0.9499, 310: 0.9516,
        320: 0.9531, 330: 0.9546, 340: 0.9560, 350: 0.9573, 360: 0.9586, 370: 0.9597,
        380: 0.9609, 390: 0.9619, 400: 0.9629, 410: 0.9639, 420: 0.9648, 430: 0.9656,
        440: 0.9664, 450: 0.9672, 460: 0.9680, 470: 0.9687, 480: 0.9694, 490: 0.9700,
        500: 0.9707, 550: 0.9735, 600: 0.9758, 650: 0.9778, 700: 0.9795, 750: 0.9809,
        800: 0.9822, 850: 0.9833, 900: 0.9843, 950: 0.9852, 1000: 0.9860, 1500: 0.9909,
        2000: 0.9933, 2500: 0.9947, 3000: 0.9957, 4000: 0.9968, 5000: 0.9975, 10000: 0.9988,
    }
    MISPRINTED_BLOCK = list(range(55, 156, 5))      # r = 55, 60, ..., 155
    N_TABLE = 1_000_000
    TOL = 6e-5                                      # the table prints 4 decimals (half-unit 5e-5)

    def test_table3_consistent_rows(self):
        # Every row outside the misprinted block agrees with the equation of step 7.
        for r, expected in self.TABLE3.items():
            if r in self.MISPRINTED_BLOCK:
                continue
            with self.subTest(r=r):
                self.assertAlmostEqual(mm.p_local(r, self.N_TABLE), expected, delta=self.TOL)

    def test_table3_misprinted_block_is_shifted_one_row(self):
        # SPEC DEFECT (recorded, not fudged): in Table 3's second column the r labels jump
        # from 49 to 55, skipping 50, and from there to 155 every printed value is the
        # P_local of r - 5: the row labelled 55 holds 0.7092 = P_local(50), ..., the row
        # labelled 155 holds 0.8980 = P_local(150), and P_local(155) = 0.9013 is not in the
        # table at all.  Rows 1-49 and 160-10000 are correct, and the equation's solution
        # was confirmed independently with 50-digit decimal arithmetic (both with x = x10 as
        # written and with the fully converged fixed point; they agree to all printed digits)
        # -- see logs/reference-multimmc-probe2-table3.log.  The table is informative; the
        # normative equation is in step 7 and this module solves it.
        for r in self.MISPRINTED_BLOCK:
            with self.subTest(r=r):
                printed = self.TABLE3[r]
                self.assertAlmostEqual(mm.p_local(r - 5, self.N_TABLE), printed, delta=self.TOL)
                self.assertGreater(abs(mm.p_local(r, self.N_TABLE) - printed), 10 * self.TOL)

    def test_p_local_is_monotone_in_r_and_in_unit_interval(self):
        prev = -1.0
        for r in (1, 2, 3, 5, 10, 50, 100, 1000, 10000, 100000):
            p = mm.p_local(r, self.N_TABLE)
            self.assertTrue(0.0 <= p < 1.0)
            self.assertGreater(p, prev)
            prev = p

    def test_r_equal_N_plus_one_all_correct(self):
        # Every prediction correct: longest run N, r = N + 1.  The equation still has a root
        # in [0, 1) (the right-hand side falls from 1 at p = 0 towards 0 as p -> 1).
        p = mm.p_local(9, 8)
        self.assertTrue(0.0 < p < 1.0)

    def test_undefined_inputs_give_nan(self):
        self.assertTrue(math.isnan(mm.p_local(3, 0)))
        self.assertTrue(math.isnan(mm.p_local(0, 10)))

    def test_log_run_probability_at_p_zero_is_log_one(self):
        # p = 0: x_j = 1 for all j, numerator 1, denominator (r + 1 - r) * 1 = 1, x^(N+1) = 1
        self.assertEqual(mm.log_run_probability(0.0, 5, 100), 0.0)


# ============================================================================================
# step 6
# ============================================================================================
class TestPGlobalPrime(unittest.TestCase):

    def test_zero_correct_branch(self):
        # 'P'_global = 1 - 0.01^(1/N), if P_global = 0'
        P, Pp = mm.p_global_prime(0, 6)
        self.assertEqual(P, 0.0)
        self.assertAlmostEqual(Pp, 1.0 - 0.01 ** (1.0 / 6))    # = 1 - 0.46416 = 0.53584
        self.assertAlmostEqual(Pp, 0.5358, places=4)

    def test_general_branch_matches_the_formula(self):
        P, Pp = mm.p_global_prime(3, 7)
        self.assertAlmostEqual(P, 3 / 7)
        self.assertAlmostEqual(Pp, 3 / 7 + 2.576 * math.sqrt((3 / 7) * (4 / 7) / 6))

    def test_capped_at_one(self):
        # C = 7, N = 8: 0.875 + 2.576 * sqrt(0.875 * 0.125 / 7) = 0.875 + 2.576 * 0.125 = 1.197
        P, Pp = mm.p_global_prime(7, 8)
        self.assertEqual(Pp, 1.0)

    def test_all_correct_is_exactly_one(self):
        P, Pp = mm.p_global_prime(8, 8)
        self.assertEqual(P, 1.0)
        self.assertEqual(Pp, 1.0)

    def test_z_variant(self):
        _, a = mm.p_global_prime(3, 7, z=mm.Z_TEXT)
        _, b = mm.p_global_prime(3, 7, z=mm.Z_BINARY64)
        self.assertNotEqual(a, b)
        self.assertLess(abs(a - b), 1e-4)                    # 2.576 vs 2.57583 is a tiny shift


# ============================================================================================
# hand-derived inputs
# ============================================================================================
class TestHandDerived(unittest.TestCase):

    def test_degenerate_all_one_symbol_1bit(self):
        # S = (0,0,0,0,0,0,0,0,0,0), L = 10, N = 8, D = 16.
        # i = 3 (p = 2): 4.a learns M1[(0), 0] = 1; 4.b: order 1 context (0) -> 0, every other
        #   order has no data -> Null.  prediction = subpredict_1 = 0 = s_3 -> correct_1 = 1.
        #   4.e: scoreboard_1 = 1, winner stays 1.
        # From then on order 1 always predicts 0 (the only transition ever seen) and order d
        # starts predicting 0 one step later than order d-1, so scoreboard_d = 9 - d for
        # d <= 8 and 0 beyond; scoreboard_1 is always strictly largest and winner stays 1.
        # All 8 predictions by the winner are correct: correct = (1,1,1,1,1,1,1,1).
        # C = 8, P_global = 1, P'_global = min(1, 1 + 0) = 1, longest run 8, r = 9,
        # min-entropy = -log2(max(1, P_local, 1/2)) = 0.
        r = mm.estimate([0] * 10, 1, return_arrays=True)
        self.assertEqual(r["N"], 8)
        self.assertEqual(list(map(int, r["correct"])), [1] * 8)
        self.assertEqual(r["C"], 8)
        self.assertEqual(r["P_global"], 1.0)
        self.assertEqual(r["P_global'"], 1.0)
        self.assertEqual(r["r"], 9)
        self.assertEqual(r["min_entropy"], 0.0)
        self.assertEqual(r["scoreboard"], [8, 7, 6, 5, 4, 3, 2, 1] + [0] * 8)
        self.assertEqual(r["winner"], 1)
        # each order d that saw anything holds exactly one counter: entries_d = 1 for d <= 8
        self.assertEqual(r["entries"], [1] * 8 + [0] * 8)

    def test_degenerate_all_one_symbol_8bit(self):
        # Same as above with the symbol 0xFF at width 8: k = 256 gives 1/k = 0.0039, still
        # below P'_global = 1, so the figure is 0 here too.
        r = mm.estimate([255] * 10, 8)
        self.assertEqual(r["C"], 8)
        self.assertEqual(r["r"], 9)
        self.assertEqual(r["P_global'"], 1.0)
        self.assertEqual(r["min_entropy"], 0.0)
        self.assertEqual(r["k"], 256)

    def test_alternating_bits(self):
        # S = (0,1,0,1,0,1,0,1,0,1), L = 10, N = 8, D = 16.   (0-based position p = i - 1)
        # p = 2: learn M1[(0),1]; context (1) unseen -> Null; s[2] = 0; correct = 0.
        # p = 3: learn M1[(1),0], M2[(0,1),0]; order 1: context (0) -> 1 = s[3]: correct = 1;
        #        order 2: context (1,0) unseen -> Null.  scoreboard = (1, 0, ...), winner 1.
        # p = 4: order 1 -> 0, order 2: (0,1) -> 0, both = s[4]; order 3 Null.  (2, 1, 0...)
        # p = 5..9: every order d <= p-1 predicts correctly (the alternation is deterministic
        #        at every order once seen); the winner is always order 1 (strictly largest).
        # correct = (0,1,1,1,1,1,1,1): C = 7, longest run 7, r = 8.
        # P_global = 7/8; P'_global = min(1, 0.875 + 2.576*sqrt(0.875*0.125/7))
        #          = min(1, 0.875 + 2.576*0.125) = min(1, 1.197) = 1  -> min-entropy 0.
        # scoreboard_d = number of p in [d+1, 9] = 9 - d for d <= 8.
        r = mm.estimate([0, 1] * 5, 1, return_arrays=True)
        self.assertEqual(list(map(int, r["correct"])), [0, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(r["C"], 7)
        self.assertEqual(r["r"], 8)
        self.assertEqual(r["P_global"], 7 / 8)
        self.assertEqual(r["P_global'"], 1.0)
        self.assertEqual(r["min_entropy"], 0.0)
        self.assertEqual(r["scoreboard"], [7, 6, 5, 4, 3, 2, 1] + [0] * 9)
        self.assertEqual(r["winner"], 1)

    def test_dictionary_cap_pairs_contexts_and_uncapped(self):
        # S = (0,1,0,2,0,2,0,2) at width 2 (k = 4), D = 1, L = 8, N = 6.  (p = i - 1)
        #
        # UNCAPPED (maxEntries = 100 000):
        #  p=2: learn (0->1).  ctx (1): unseen -> Null.  s[2]=0 -> correct_1 = 0.
        #  p=3: learn (1->0).  ctx (0): {1:1} -> 1.  s[3]=2 -> 0.
        #  p=4: learn (0->2).  ctx (2): unseen -> Null.  s[4]=0 -> 0.
        #  p=5: learn (2->0).  ctx (0): {1:1, 2:1} TIE -> greatest y = 2.  s[5]=2 -> 1.
        #  p=6: learn (0->2): 2.  ctx (2): {0:1} -> 0.  s[6]=0 -> 1.
        #  p=7: learn (2->0): 2.  ctx (0): {1:1, 2:2} -> 2.  s[7]=2 -> 1.
        #  correct = (0,0,0,1,1,1): C = 3, r = 4, entries = 4, refused = 0.
        #  P_global = 0.5, P'_global = min(1, 0.5 + 2.576*sqrt(0.25/5)) = min(1, 1.076) = 1
        #  -> min-entropy 0.
        #
        # LITERAL CAP, maxEntries = 1 (entries counts counters = pairs):
        #  p=2: (0->1) is new, entries 0 < 1 -> added, entries = 1.  Null; 0.
        #  p=3: (1->0) new, entries 1 is not < 1 -> REFUSED.  ctx (0): {1:1} -> 1; s[3]=2 -> 0.
        #  p=4: (0->2) REFUSED.  ctx (2): nothing -> Null; 0.
        #  p=5: (2->0) REFUSED.  ctx (0) -> 1; s[5]=2 -> 0.
        #  p=6: (0->2) REFUSED (not in M1, cap full).  ctx (2) -> Null; 0.
        #  p=7: (2->0) REFUSED.  ctx (0) -> 1; s[7]=2 -> 0.
        #  correct = (0,0,0,0,0,0): C = 0, r = 1, entries = 1, refused = 5.
        #  P'_global = 1 - 0.01^(1/6) = 1 - 10^(-1/3) = 1 - 0.464159 = 0.535841; 1/k = 0.25;
        #  P_local tiny  -> min-entropy = -log2(0.535841) = 0.900123.
        #
        # VARIANT CAP, maxEntries = 1 counting CONTEXTS (non-literal; for diagnosis only):
        #  p=2: context (0) new, entries 0 < 1 -> added with (0->1); entries = 1.
        #  p=3: context (1) new, cap full -> REFUSED.
        #  p=4: context (0) present -> (0->2) added freely: M1[(0)] = {1:1, 2:1}.
        #  p=5: context (2) new -> REFUSED.  ctx (0): tie -> 2 = s[5] -> correct 1.
        #  p=6: (0->2) -> 2.  ctx (2): nothing -> Null; 0.
        #  p=7: context (2) -> REFUSED.  ctx (0): {1:1, 2:2} -> 2 = s[7] -> 1.
        #  correct = (0,0,0,1,0,1): C = 2, r = 2, entries = 1, refused = 3.
        S = [0, 1, 0, 2, 0, 2, 0, 2]
        for method in ("fast", "literal"):
            with self.subTest(method=method, mode="uncapped"):
                r = mm.estimate(S, 2, D=1, method=method, return_arrays=True)
                self.assertEqual(list(map(int, r["correct"])), [0, 0, 0, 1, 1, 1])
                self.assertEqual((r["C"], r["r"]), (3, 4))
                self.assertEqual((r["entries"], r["refused"]), ([4], [0]))
                self.assertFalse(r["cap_bound"])
                self.assertEqual(r["P_global'"], 1.0)
                self.assertEqual(r["min_entropy"], 0.0)
            with self.subTest(method=method, mode="pairs"):
                r = mm.estimate(S, 2, D=1, max_entries=1, entries_mode="pairs", method=method,
                                return_arrays=True)
                self.assertEqual(list(map(int, r["correct"])), [0, 0, 0, 0, 0, 0])
                self.assertEqual((r["C"], r["r"]), (0, 1))
                self.assertEqual((r["entries"], r["refused"]), ([1], [5]))
                self.assertTrue(r["cap_bound"])
                self.assertAlmostEqual(r["P_global'"], 1.0 - 0.01 ** (1.0 / 6))
                self.assertEqual(r["binding"], "P_global'")
                self.assertAlmostEqual(r["min_entropy"], -math.log2(1.0 - 0.01 ** (1.0 / 6)))
                self.assertAlmostEqual(r["min_entropy"], 0.9001, places=4)
            with self.subTest(method=method, mode="contexts"):
                r = mm.estimate(S, 2, D=1, max_entries=1, entries_mode="contexts",
                                method=method, return_arrays=True)
                self.assertEqual(list(map(int, r["correct"])), [0, 0, 0, 1, 0, 1])
                self.assertEqual((r["C"], r["r"]), (2, 2))
                self.assertEqual((r["entries"], r["refused"]), ([1], [3]))

    def test_tie_rule_prediction_in_the_cap_example(self):
        # p = 5 above (uncapped): M1[(0), .] = {1:1, 2:1} -> 'the greatest y in the tie' = 2
        r = mm.estimate([0, 1, 0, 2, 0, 2, 0, 2], 2, D=1, trace=True)
        row = {x["i"]: x for x in r["trace"]}[6]            # spec i = p + 1 = 6
        self.assertEqual(row["subpredict"], (2,))
        self.assertEqual(row["correct"], 1)

    def test_null_prediction_ends_the_run(self):
        # The D-4 property: a Null prediction leaves correct = 0 and so ends a run.
        # Without the cap a winner cannot go Null straight after being correct (if it
        # predicted s[p-1] from the d-gram ending at p-2, the (d+1)-gram ending at p-1 was
        # learned earlier, so its tail -- the next context -- has a learned successor by
        # step p).  With the cap it can:
        # S = (0,1,0,1,0,1), width 1, D = 1, maxEntries = 1, L = 6, N = 4.
        #  p=2: (0->1) added (entries = 1).  ctx (1): nothing -> Null.  s[2]=0 -> correct 0.
        #  p=3: (1->0) REFUSED.  ctx (0): {1:1} -> 1 = s[3] -> correct 1.
        #  p=4: (0->1) -> 2.  ctx (1): still nothing -> Null.  s[4]=0 -> correct 0.
        #  p=5: (1->0) REFUSED.  ctx (0): {1:2} -> 1 = s[5] -> correct 1.
        #  correct = (0,1,0,1): C = 2, longest run 1, r = 2.
        # Had Null carried the run across (the quirk D-4 describes), the run would be 2 and
        # r = 3.  Uncapped, the same input gives correct = (0,1,1,1), C = 3, r = 4.
        r = mm.estimate([0, 1, 0, 1, 0, 1], 1, D=1, max_entries=1, trace=True)
        self.assertEqual([row["prediction"] for row in r["trace"]], [NULL, 1, NULL, 1])
        self.assertEqual(list(map(int, r["correct"])), [0, 1, 0, 1])
        self.assertEqual((r["C"], r["r"]), (2, 2))
        u = mm.estimate([0, 1, 0, 1, 0, 1], 1, D=1, return_arrays=True)
        self.assertEqual(list(map(int, u["correct"])), [0, 1, 1, 1])
        self.assertEqual((u["C"], u["r"]), (3, 4))

    def test_scoreboard_tie_goes_to_the_larger_d(self):
        # 4.e.i.2 with '>=': when two orders are both correct and tie, the later d wins.
        # S = (0,1,0,1,0,1,1,0,1,1,0,1), width 1, D = 2:  (0-based p)
        #  p=2: ctx(1) Null | Null.  s=0.  sb (0,0)
        #  p=3: learn (1->0), ((0,1)->0).  o1 ctx(0)->1 ok; o2 ctx(1,0) Null.  sb (1,0) w=1
        #  p=4: learn (0->1):2, ((1,0)->1).  o1 ctx(1)->0 ok; o2 ctx(0,1)->0 ok.  sb (2,1) w=1
        #  p=5: learn (1->0):2, ((0,1)->0):2.  o1 ctx(0)->1 ok; o2 ctx(1,0)->1 ok.  sb (3,2)
        #  p=6: learn (0->1):3, ((1,0)->1):2.  o1 ctx(1)->0; o2 ctx(0,1)->0.  s=1: both wrong.
        #  p=7: learn (1->1):1, ((0,1)->1):1.  o1 ctx(1): {0:2,1:1}->0 ok; o2 ctx(1,1) Null.
        #       sb (4,2)
        #  p=8: learn (1->0):3, ((1,1)->0):1.  o1 ctx(0)->1 ok; o2 ctx(1,0): {1:2}->1 ok.
        #       sb (5,3)
        #  p=9: learn (0->1):4, ((1,0)->1):3.  o1 ctx(1): {0:3,1:1}->0; o2 ctx(0,1): {0:2,1:1}
        #       ->0.  s=1: both wrong.
        #  p=10: learn (1->1):2, ((0,1)->1):2.  o1 ctx(1): {0:3,1:2}->0 ok; o2 ctx(1,1):
        #       {0:1}->0 ok.  sb (6,4)
        #  p=11: learn (1->0):4, ((1,1)->0):2.  o1 ctx(0)->1 ok; o2 ctx(1,0)->1 ok.  sb (7,5)
        # Order 1 leads throughout, so the winner never changes and this input does not
        # exercise the tie.  It is kept as a literal/fast agreement check with D = 2 and the
        # tie itself is exercised below by construction on the scoreboard loop.
        S = [0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1]
        a = mm.estimate(S, 1, D=2, method="fast", return_arrays=True)
        b = mm.estimate(S, 1, D=2, method="literal", return_arrays=True)
        self.assertEqual(a["scoreboard"], [7, 5])
        self.assertEqual(b["scoreboard"], [7, 5])
        self.assertEqual(list(map(int, a["correct"])), [0, 1, 1, 1, 0, 1, 1, 0, 1, 1])
        self.assertEqual(list(map(int, a["correct"])), list(map(int, b["correct"])))
        # Direct check of 4.e on a constructed subpredict table (D = 2), s = (0,0,1,1,1):
        #   p=2 (s=1): both orders say 1 -> prediction (winner 1) = 1, correct_1 = 1.
        #        4.e: d=1 -> sb (1,0), 1 >= sb_winner=1 -> winner 1;
        #             d=2 -> sb (1,1), 1 >= sb_winner=sb_1=1 -> winner = 2   (the tie)
        #   p=3 (s=1): order 1 says 1, order 2 says 0 -> prediction (winner 2) = 0: correct_2 = 0.
        #        4.e: d=1 -> sb (2,1), 2 >= sb_winner=sb_2=1 -> winner = 1.
        #   p=4 (s=1): order 1 says 1, order 2 Null -> prediction (winner 1) = 1: correct_3 = 1.
        #        4.e: d=1 -> sb (3,1).
        #   correct = (1,0,1), scoreboard (3,1), winner 1.  Under a strict '>' (ties do not
        #   move the winner) the p=3 prediction would come from order 1 and correct = (1,1,1).
        s = np.array([0, 0, 1, 1, 1], dtype=np.int64)
        sub = [np.array([NULL, NULL, 1, 1, 1]), np.array([NULL, NULL, 1, 0, NULL])]
        correct, scoreboard, winner = mm.run_scoreboard(s, sub)
        self.assertEqual(list(map(int, correct)), [1, 0, 1])
        self.assertEqual(scoreboard, [3, 1])
        self.assertEqual(winner, 1)
        # and the same from this file's own transcription of 4.c-4.e
        want = _scoreboard_only(s, sub)
        self.assertEqual((want["correct"], want["scoreboard"], want["winner"]), ([1, 0, 1], [3, 1], 1))


def _scoreboard_only(s, subpredict):
    """Steps 3 and 4.c-4.e alone, transcribed again here (not imported) on a given
    subpredict table, so the tests check the module's scoreboard loop from outside."""
    L = len(s)
    N = L - 2
    D = len(subpredict)
    correct = [0] * N
    scoreboard = [0] * D
    winner = 1
    for i in range(3, L + 1):
        p = i - 1
        si = int(s[p])
        prediction = int(subpredict[winner - 1][p])
        if prediction == si:
            correct[i - 3] = 1
        for d in range(1, D + 1):
            if int(subpredict[d - 1][p]) == si:
                scoreboard[d - 1] += 1
                if scoreboard[d - 1] >= scoreboard[winner - 1]:
                    winner = d
    return {"correct": correct, "scoreboard": scoreboard, "winner": winner}


class TestScoreboardLoopAgainstTranscription(unittest.TestCase):
    """The fast path's scoreboard loop (bit-mask, ascending set bits) against a plain
    transcription of 4.c-4.e, on random subpredict tables including ties and Nulls."""

    def test_random_tables(self):
        rng = np.random.default_rng(11)
        for trial in range(200):
            L = int(rng.integers(3, 40))
            D = int(rng.integers(1, 6))
            k = int(rng.integers(2, 5))
            s = rng.integers(0, k, size=L)
            sub = [np.where(rng.random(L) < 0.3, NULL, rng.integers(0, k, size=L)) for _ in range(D)]
            for arr in sub:
                arr[:2] = NULL
            want = _scoreboard_only(s, sub)
            correct, scoreboard, winner = mm.run_scoreboard(s, sub)
            with self.subTest(trial=trial):
                self.assertEqual(list(map(int, correct)), want["correct"])
                self.assertEqual(scoreboard, want["scoreboard"])
                self.assertEqual(winner, want["winner"])


# ============================================================================================
# the two transcriptions of steps 1-4 agree
# ============================================================================================
class TestFastEqualsLiteral(unittest.TestCase):

    def _compare(self, s, bits, D, max_entries, mode):
        a = mm.estimate(s, bits, D=D, max_entries=max_entries, entries_mode=mode,
                        method="fast", return_arrays=True)
        b = mm.estimate(s, bits, D=D, max_entries=max_entries, entries_mode=mode,
                        method="literal", return_arrays=True)
        L = len(s)
        self.assertEqual(list(map(int, a["correct"])), list(map(int, b["correct"])))
        self.assertEqual(a["scoreboard"], b["scoreboard"])
        self.assertEqual(a["winner"], b["winner"])
        self.assertEqual(a["entries"], b["entries"])
        self.assertEqual(a["refused"], b["refused"])
        if L >= 3:
            self.assertEqual((a["C"], a["r"]), (b["C"], b["r"]))
            if math.isnan(a["min_entropy"]) or math.isnan(b["min_entropy"]):
                # only the L = 3, s1 = s2 = s3 case (step 6's 0/0); both must be NaN
                self.assertTrue(math.isnan(a["min_entropy"]) and math.isnan(b["min_entropy"]))
                self.assertEqual((L, a["C"]), (3, 1))
            else:
                self.assertEqual(a["min_entropy"], b["min_entropy"])
        for d in range(D):
            for i in range(3, L + 1):
                self.assertEqual(int(a["subpredict"][d][i - 1]), b["subpredict"][d][i])
        return a

    def test_random_small_inputs(self):
        rng = np.random.default_rng(7)
        capped = 0
        for trial in range(90):
            bits = int(rng.integers(1, 4))
            k = 1 << bits
            L = int(rng.integers(3, 50))
            kind = trial % 3
            if kind == 0:
                s = rng.integers(0, k, size=L)
            elif kind == 1:
                s = (rng.random(L) < 0.15).astype(np.int64) * (k - 1)
            else:
                base = np.resize(rng.integers(0, k, size=int(rng.integers(1, 5))), L)
                s = np.where(rng.random(L) < 0.1, rng.integers(0, k, size=L), base)
            for D in (1, 3, 16):
                for me in (mm.MAX_ENTRIES_TEXT, 1, 3):
                    for mode in ("pairs", "contexts"):
                        with self.subTest(trial=trial, D=D, max_entries=me, mode=mode):
                            a = self._compare(s, bits, D, me, mode)
                            capped += a["cap_bound"]
        self.assertGreater(capped, 0)              # the cap actually bound in some cases

    def test_8bit_random_with_default_cap(self):
        rng = np.random.default_rng(3)
        s = rng.integers(0, 256, size=400)
        self._compare(s, 8, 16, mm.MAX_ENTRIES_TEXT, "pairs")

    def test_entries_readings_differ_materially_when_the_cap_binds(self):
        # With a cap small enough to bind, the literal 'pairs' reading and the 'contexts'
        # variant give different C on this seeded input -- the reason both are exposed.
        rng = np.random.default_rng(5)
        s = rng.integers(0, 4, size=300)
        a = mm.estimate(s, 2, D=2, max_entries=6, entries_mode="pairs")
        b = mm.estimate(s, 2, D=2, max_entries=6, entries_mode="contexts")
        self.assertTrue(a["cap_bound"])
        self.assertNotEqual(a["C"], b["C"])


# ============================================================================================
# edges and the API surface
# ============================================================================================
class TestEdgesAndApi(unittest.TestCase):

    def test_too_short_for_the_text(self):
        for L in (0, 1, 2):
            with self.subTest(L=L):
                r = mm.estimate([0] * L, 1)
                self.assertEqual(r["N"], L - 2)
                for key in ("min_entropy", "min entropy", "C", "r", "P_global", "P_global'", "P_local"):
                    self.assertTrue(math.isnan(r[key]), key)

    def test_L3_single_prediction(self):
        # L = 3, N = 1.  At i = 3 step 4.a learns M1[(s1), s2] = 1, then 4.b predicts from the
        # context (s2): if s2 = s1 the counter is found and subpredict_1 = s2, else Null.
        # Orders d >= 2 have 'd < i-1' false, so they learn nothing and predict Null.
        #  - S = (0,1,0): context (1) unseen -> Null -> C = 0, P_global = 0,
        #    P'_global = 1 - 0.01^(1/1) = 0.99, r = 1, min-entropy = -log2(0.99) = 0.0145.
        #  - S = (0,0,1): context (0) -> predicts 0, s3 = 1 -> wrong -> C = 0, same figures.
        #  - S = (5,6,7): Null -> same figures.
        for S in ([0, 1, 0], [0, 0, 1], [5, 6, 7]):
            with self.subTest(S=S):
                r = mm.estimate(S, 3, return_arrays=True)
                self.assertEqual(r["N"], 1)
                self.assertEqual(r["C"], 0)
                self.assertEqual(r["r"], 1)
                self.assertAlmostEqual(r["P_global'"], 0.99)
                self.assertAlmostEqual(r["min_entropy"], -math.log2(0.99))
        #  - S = (0,0,0): context (0) -> predicts 0 = s3 -> correct -> C = 1, P_global = 1,
        #    and step 6's second branch is 1 + 2.576 sqrt(1*0/(N-1)) with N - 1 = 0: a 0/0,
        #    undefined, so P'_global and the min-entropy are NaN (recorded in AMBIGUITIES).
        r = mm.estimate([0, 0, 0], 3, return_arrays=True)
        self.assertEqual(r["C"], 1)
        self.assertEqual(r["P_global"], 1.0)
        self.assertTrue(math.isnan(r["P_global'"]))
        self.assertTrue(math.isnan(r["min_entropy"]))

    def test_L4(self):
        # S = (0,0,0,1): p=2: order 1 ctx (0) -> 0 = s[2], correct; p=3: ctx (0): {0:2} -> 0
        # but s[3] = 1: wrong.  correct = (1, 0), C = 1, N = 2, P_global = 0.5,
        # P'_global = min(1, 0.5 + 2.576*sqrt(0.25/1)) = 1 -> min-entropy 0.
        r = mm.estimate([0, 0, 0, 1], 1, return_arrays=True)
        self.assertEqual(list(map(int, r["correct"])), [1, 0])
        self.assertEqual(r["P_global'"], 1.0)
        self.assertEqual(r["min_entropy"], 0.0)

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            mm.estimate([0, 1, 2], 1)                  # 2 is out of range for 1 bit
        with self.assertRaises(ValueError):
            mm.estimate([0, 1, 0], 0)
        with self.assertRaises(ValueError):
            mm.estimate([0, 1, 0], 1, k_mode="bogus")
        with self.assertRaises(ValueError):
            mm.estimate([0, 1, 0], 1, entries_mode="bogus")
        with self.assertRaises(ValueError):
            mm.estimate([0, 1, 0], 1, method="bogus")
        with self.assertRaises(ValueError):
            mm.estimate([0, 1, 0], 1, D=0)

    def test_to_bitstring_msb_first(self):
        self.assertEqual(mm.to_bitstring([5], 3).tolist(), [1, 0, 1])
        self.assertEqual(mm.to_bitstring([0xA5], 8).tolist(), [1, 0, 1, 0, 0, 1, 0, 1])
        self.assertEqual(mm.to_bitstring([1, 2], 2).tolist(), [0, 1, 1, 0])

    def test_result_carries_the_labels_and_ambiguities(self):
        r = mm.estimate([0, 1] * 20, 1)
        for key in ("C", "r", "N", "P_global", "P_global'", "P_local", "min entropy",
                    "min_entropy", "entries", "refused", "cap_bound", "binding",
                    "P_local_changes_result", "ambiguities", "D", "max_entries"):
            self.assertIn(key, r)
        self.assertEqual(r["D"], 16)
        self.assertEqual(r["max_entries"], 100_000)
        self.assertEqual(r["ambiguities"], mm.AMBIGUITIES)

    def test_longest_run_of_ones(self):
        self.assertEqual(mm.longest_run_of_ones([]), 0)
        self.assertEqual(mm.longest_run_of_ones([0, 0, 0]), 0)
        self.assertEqual(mm.longest_run_of_ones([1, 1, 0, 1]), 2)
        self.assertEqual(mm.longest_run_of_ones([0, 0, 1, 1, 0, 1, 0]), 2)
        self.assertEqual(mm.longest_run_of_ones([1] * 5), 5)


# ============================================================================================
# command line
# ============================================================================================
class TestCommandLine(unittest.TestCase):

    def _run(self, *args):
        return subprocess.run([sys.executable, str(MODULE_PATH), *args],
                              capture_output=True, text=True, timeout=120)

    def test_worked_example_through_the_cli(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "example.bin")
            with open(path, "wb") as fh:
                fh.write(bytes([2, 1, 3, 2, 1, 3, 1, 3, 1]))
            p = self._run(path, "2", "--literal", "--D=3")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["mode"], "literal")
            self.assertEqual(out["L"], 9)
            self.assertEqual(out["N"], 7)
            self.assertEqual(out["C"], 3)
            self.assertEqual(out["r"], 3)
            self.assertAlmostEqual(out["P_global"], 0.4286, places=4)
            self.assertAlmostEqual(out["P_global'"], 0.9490, places=4)
            self.assertAlmostEqual(out["P_local"], 0.1307, places=4)
            self.assertAlmostEqual(out["min entropy"], 0.0755, places=4)
            self.assertEqual(out["min_entropy"], out["min entropy"])

    def test_bitstring_mode(self):
        # 0xFF repeated: the bitstring is all ones -> C = N, min entropy 0; in literal mode
        # at width 8 the same holds.  Low-bits masking: 0x1FF does not fit a byte, so use
        # a byte 0x03 at bps = 1 -> symbol 1 (low bit), and 0x02 -> 0.
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "ones.bin")
            with open(path, "wb") as fh:
                fh.write(bytes([0xFF]) * 12)
            p = self._run(path, "8", "--bitstring")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["mode"], "bitstring")
            self.assertEqual(out["L"], 96)
            self.assertEqual(out["N"], 94)
            self.assertEqual(out["C"], 94)
            self.assertEqual(out["min entropy"], 0.0)
            p = self._run(path, "8")
            out = json.loads(p.stdout)
            self.assertEqual(out["L"], 12)
            self.assertEqual(out["C"], 10)
            self.assertEqual(out["k"], 256)
            path2 = os.path.join(td, "lowbits.bin")
            with open(path2, "wb") as fh:
                fh.write(bytes([0x03, 0x02, 0x03, 0x02, 0x03, 0x02]))
            p = self._run(path2, "1")
            out = json.loads(p.stdout)
            # symbols = (1,0,1,0,1,0): alternation, L = 6, N = 4 -> correct (0,1,1,1), C = 3
            self.assertEqual(out["C"], 3)
            self.assertEqual(out["k_observed"], 2)

    def test_options_reach_estimate(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cap.bin")
            with open(path, "wb") as fh:
                fh.write(bytes([0, 1, 0, 2, 0, 2, 0, 2]))
            a = json.loads(self._run(path, "2", "--D=1", "--max-entries=1").stdout)
            b = json.loads(self._run(path, "2", "--D=1", "--max-entries=1", "--entries-mode=contexts").stdout)
            c = json.loads(self._run(path, "2", "--D=1").stdout)
            self.assertEqual((a["C"], b["C"], c["C"]), (0, 2, 3))
            d = json.loads(self._run(path, "2", "--D=1", "--method=literal", "--k-mode=observed",
                                     "--z=2.5758293035489008").stdout)
            self.assertEqual(d["C"], 3)
            self.assertEqual(d["k"], 3)
            self.assertEqual(d["method"], "literal")

    def test_usage_errors(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "x.bin")
            with open(path, "wb") as fh:
                fh.write(bytes(range(16)))
            for args in ([path], [path, "9"], [path, "0"], [path, "eight"],
                         [path, "8", "--bogus"], [path, "8", "--D=zero"],
                         [path, "8", "--entries-mode=bogus"]):
                with self.subTest(args=args):
                    p = self._run(*args)
                    self.assertNotEqual(p.returncode, 0)
                    self.assertEqual(p.stdout, "")

    def test_nan_round_trips_through_json(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "two.bin")
            with open(path, "wb") as fh:
                fh.write(b"\x01\x00")
            p = self._run(path, "1")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["L"], 2)
            self.assertTrue(math.isnan(out["min entropy"]))
            self.assertTrue(math.isnan(out["P_local"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
