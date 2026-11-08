"""Tests for py90b.lag -- SP 800-90B section 6.3.8, the Lag Prediction Estimate.

Oracles are the standard's own worked examples (sections 6.3.7-6.3.10 share the
step-5/6 formulas) and Appendix G.2 Table 3, plus hand-derived degenerate inputs.
Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_lag.py
"""

import math
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))      # .../reference

import numpy as np                                                # noqa: E402

from py90b import lag                                             # noqa: E402


def _nan(v):
    return isinstance(v, float) and math.isnan(v)


class SpecWorkedExample(unittest.TestCase):
    """SP 800-90B section 6.3.8 example (PDF p. 60):
    S = (2, 1, 3, 2, 1, 3, 1, 3, 1, 2), L = 10, N = 9, D = 3 instead of 128."""

    S = [2, 1, 3, 2, 1, 3, 1, 3, 1, 2]

    # The table in step 3 as printed (lag, winner used in 3b, prediction, s_i,
    # correct_{i-1}, scoreboard after 3d).  '--' is Null -> None.
    TABLE = [
        (2,  (2, None, None), 1, 2, 1, 0, (0, 0, 0)),
        (3,  (1, 2, None),    1, 1, 3, 0, (0, 0, 0)),
        (4,  (3, 1, 2),       1, 3, 2, 0, (0, 0, 1)),
        (5,  (2, 3, 1),       3, 1, 1, 1, (0, 0, 2)),
        (6,  (1, 2, 3),       3, 3, 3, 1, (0, 0, 3)),
        (7,  (3, 1, 2),       3, 2, 1, 0, (0, 1, 3)),
        (8,  (1, 3, 1),       3, 1, 3, 0, (0, 2, 3)),
        (9,  (3, 1, 3),       3, 3, 1, 0, (0, 3, 3)),
        (10, (1, 3, 1),       2, 3, 2, 0, (0, 3, 3)),
    ]

    def test_step3_table_stepwise(self):
        r = lag.estimate(self.S, 2, D=3, method="stepwise", trace=True)
        self.assertEqual(len(r["trace"]), 9)
        for row, (i, lg, winner, pred, s_i, corr, sb) in zip(r["trace"], self.TABLE):
            self.assertEqual(row["i"], i)
            self.assertEqual(row["lag"], lg)
            self.assertEqual(row["winner"], winner, "winner at i=%d" % i)
            self.assertEqual(row["prediction"], pred, "prediction at i=%d" % i)
            self.assertEqual(row["s_i"], s_i)
            self.assertEqual(row["correct"], corr, "correct at i=%d" % i)
            self.assertEqual(row["scoreboard"], sb, "scoreboard at i=%d" % i)

    def _check_figures(self, r):
        # "After all of the predictions are made, correct = (0, 0, 0, 1, 1, 0, 0, 0, 0)."
        self.assertEqual(r["correct"], [0, 0, 0, 1, 1, 0, 0, 0, 0])
        self.assertEqual(r["N"], 9)
        self.assertEqual(r["C"], 2)
        self.assertEqual(r["longest_run"], 2)
        self.assertEqual(r["r"], 3)
        # "P_global = 0.2222"
        self.assertAlmostEqual(r["P_global"], 2 / 9)
        self.assertEqual(round(r["P_global"], 4), 0.2222)
        # "P_global' = 0.6008".  Exact arithmetic gives
        #   2/9 + 2.576*sqrt((2/9)(7/9)/8) = 0.600858632...  (-> 0.6009 at 4 dp);
        # the printed 0.6008 is what one gets by substituting the ROUNDED
        # P_global = 0.2222 into step 5: 0.2222 + 2.576*sqrt(0.2222*0.7778/8) = 0.60083.
        # So the example's figure carries the example's own rounding; we check the
        # exact value and separately that the rounded-input replica prints 0.6008.
        self.assertAlmostEqual(r["P_global'"], 2 / 9 + 2.576 * math.sqrt((2 / 9) * (7 / 9) / 8), places=12)
        self.assertLess(abs(r["P_global'"] - 0.6008), 1e-4)
        replica = 0.2222 + 2.576 * math.sqrt(0.2222 * 0.7778 / 8)
        self.assertEqual(round(replica, 4), 0.6008)
        # "P_local = 0.1167"
        self.assertEqual(round(r["P_local"], 4), 0.1167)
        # "the resulting min-entropy estimate is 0.735"
        self.assertEqual(round(r["min_entropy"], 3), 0.735)
        self.assertAlmostEqual(r["min_entropy"], -math.log2(r["P_global'"]), places=12)

    def test_figures_stepwise(self):
        self._check_figures(lag.estimate(self.S, 2, D=3, method="stepwise", return_correct=True))

    def test_figures_vectorised(self):
        self._check_figures(lag.estimate(self.S, 2, D=3, method="vectorised", return_correct=True))
        # chunk boundaries inside the data must not change anything
        self._check_figures(lag.estimate(self.S, 2, D=3, method="vectorised", chunk=2, return_correct=True))

    def test_k_reading_does_not_matter_here(self):
        # 1/k = 1/4 (alphabet of 2-bit symbols) or 1/3 (values {1,2,3} observed): both below P_global'.
        a = lag.estimate(self.S, 2, D=3, k_mode="alphabet")
        b = lag.estimate(self.S, 2, D=3, k_mode="observed")
        self.assertEqual(a["k"], 4)
        self.assertEqual(b["k"], 3)
        self.assertEqual(a["min_entropy"], b["min_entropy"])


class PLocalSolver(unittest.TestCase):
    """Step 6.  The same equation appears verbatim in 6.3.7, 6.3.8, 6.3.9 and
    6.3.10, so all four worked examples are oracles for the solver."""

    def test_worked_examples(self):
        # (r, N, printed P_local, where)
        cases = [
            (2, 9, 0.036,  "6.3.7 MultiMCW, PDF p. 59: correct=(0,0,0,1,0,1,0,0,1), longest run 1"),
            (3, 9, 0.1167, "6.3.8 Lag, PDF p. 60"),
            (3, 7, 0.1307, "6.3.9 MultiMMC, PDF p. 62: correct=(0,0,1,1,0,1,0), longest run 2"),
            (3, 8, 0.1229, "6.3.10 LZ78Y, PDF p. 65: correct=(0,0,1,1,0,1,1,0), longest run 2"),
        ]
        for r, N, want, where in cases:
            got = lag.solve_p_local(r, N)
            places = 3 if want == 0.036 else 4
            self.assertEqual(round(got, places), want, "%s: got %.8f" % (where, got))
            # and the solution really satisfies the printed equation
            self.assertAlmostEqual(math.exp(lag._log_rhs(got, r, N)), 0.99, places=9)

    # Appendix G.2 Table 3 (PDF p. 84): "P_local values for different r values
    # when L = 1 000 000".  For the Lag estimator N = L - 1 = 999 999.
    TABLE3 = {
        1: 0.0000, 2: 0.0001, 3: 0.0022, 4: 0.0100, 5: 0.0253, 6: 0.0468, 7: 0.0728, 8: 0.1014,
        9: 0.1313, 10: 0.1614, 11: 0.1911, 12: 0.2200, 13: 0.2479, 14: 0.2746, 15: 0.3000,
        16: 0.3242, 17: 0.3471, 18: 0.3688, 19: 0.3893, 20: 0.4088, 21: 0.4272, 22: 0.4447,
        23: 0.4613, 24: 0.4770, 25: 0.4919, 26: 0.5060, 27: 0.5195, 28: 0.5323, 29: 0.5445,
        30: 0.5561, 31: 0.5672, 32: 0.5778, 33: 0.5879, 34: 0.5976, 35: 0.6068, 36: 0.6157,
        37: 0.6242, 38: 0.6324, 39: 0.6402, 40: 0.6477, 41: 0.6549, 42: 0.6619, 43: 0.6686,
        44: 0.6750, 45: 0.6812, 46: 0.6872, 47: 0.6930, 48: 0.6986, 49: 0.7040,
        55: 0.7092, 60: 0.7328, 65: 0.7531, 70: 0.7705, 75: 0.7858, 80: 0.7992, 85: 0.8111,
        90: 0.8217, 95: 0.8312, 100: 0.8398, 105: 0.8476, 110: 0.8547, 115: 0.8612, 120: 0.8671,
        125: 0.8726, 130: 0.8776, 135: 0.8823, 140: 0.8867, 145: 0.8907, 150: 0.8945, 155: 0.8980,
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
    # Rows whose printed label does not match their value: each of these holds the
    # value for r - 5 (0.7092 is the r = 50 value, 0.7328 the r = 55 value, ...,
    # 0.8980 the r = 150 value), and the row labelled 160 is back in step.  The
    # 115 other rows match to 4 decimals, as do the four worked examples, so this
    # is read as a typesetting shift in the informative appendix, not as a
    # property of the formula.  Recorded in spec_ambiguities; the code is NOT
    # adjusted to it.
    SHIFTED = tuple(range(55, 156, 5))

    def test_table3_unshifted_rows(self):
        N = 999_999
        for r, want in self.TABLE3.items():
            if r in self.SHIFTED:
                continue
            got = lag.solve_p_local(r, N)
            self.assertEqual(round(got, 4), want, "Table 3 r=%d: got %.8f want %.4f" % (r, got, want))

    def test_table3_shifted_rows_match_r_minus_5(self):
        N = 999_999
        for r in self.SHIFTED:
            printed = self.TABLE3[r]
            self.assertNotEqual(round(lag.solve_p_local(r, N), 4), printed)
            self.assertEqual(round(lag.solve_p_local(r - 5, N), 4), printed,
                             "Table 3 row labelled r=%d holds the r=%d value" % (r, r - 5))

    def test_single_crossing(self):
        """The right-hand side of the step-6 equation is above 0.99 for every p
        below the returned root and below 0.99 for every p above it, so the
        binary search's answer is unambiguous (the formula is not monotone far
        from the root, where it leaves its domain, but it never climbs back to
        0.99)."""
        target = math.log(0.99)
        grid = np.linspace(1e-12, 1 - 1e-12, 20001)
        for r, N in [(1, 9), (2, 9), (3, 9), (10, 10), (11, 10), (1, 999_999), (2, 999_999),
                     (3, 999_999), (10, 999_999), (100, 999_999), (1000, 999_999),
                     (10_000, 999_999), (999_999, 999_999), (1_000_000, 999_999)]:
            root = lag.solve_p_local(r, N)
            vals = np.array([lag._log_rhs(p, r, N) for p in grid])
            below = grid < root
            self.assertTrue(np.all(vals[below] >= target - 1e-9), "r=%d N=%d: below root" % (r, N))
            self.assertTrue(np.all(vals[~below] <= target + 1e-9), "r=%d N=%d: above root" % (r, N))

    def test_r_one_closed_form(self):
        # r = 1 (no correct prediction at all).  Hand derivation: the recurrence is
        # x = 1 + q p x^2, whose roots are 1/q and 1/p; from x_0 = 1 it converges to
        # the smaller one, x = 1/q for p < 1/2.  Then 1 - p x = (q - p)/q and
        # (r + 1 - r x) q = (2 - 1/q) q = q - p, so the ratio is 1/q and the
        # right-hand side is (1/q) q^(N+1) = q^N.  Hence P_local = 1 - 0.99^(1/N)
        # (up to the 10-iteration truncation, negligible here).  N = 999 999 gives
        # 1.005e-8, which is Table 3's "0.0000" for r = 1.
        for N in (9, 1000, 999_999):
            got = lag.solve_p_local(1, N)
            self.assertAlmostEqual(got, 1 - 0.99 ** (1 / N), delta=1e-9)


class GlobalBound(unittest.TestCase):
    def test_step5_branches(self):
        self.assertAlmostEqual(lag.p_global_prime(0.0, 1999), 1 - 0.01 ** (1 / 1999), places=15)
        self.assertEqual(lag.p_global_prime(1.0, 50), 1.0)                       # clamp: min(1, 1 + 0)
        self.assertAlmostEqual(lag.p_global_prime(0.5, 101), 0.5 + 2.576 * math.sqrt(0.25 / 100), places=15)
        self.assertEqual(lag.p_global_prime(0.0, 1), 0.99)                       # 1 - 0.01^(1/1)
        self.assertTrue(_nan(lag.p_global_prime(1.0, 1)))                        # 1 + 2.576*sqrt(0/0)
        self.assertTrue(_nan(lag.p_global_prime(0.5, 0)))

    def test_exact_quantile_variant_is_less_conservative(self):
        x = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0] * 10)
        a = lag.estimate(x, 1)                      # z = 2.576, the printed constant
        b = lag.estimate(x, 1, z=lag.Z_EXACT)
        self.assertEqual(a["C"], b["C"])
        self.assertLess(b["P_global'"], a["P_global'"])
        self.assertGreaterEqual(b["min_entropy"], a["min_entropy"])


class DegenerateInputs(unittest.TestCase):
    def test_constant_sequence(self):
        """All one symbol, 1-bit, L = 20.  Hand derivation: every defined lag
        matches at every step, so after step i scoreboard_d = i - d; lag 1 is
        always the strict maximum, winner stays 1 and prediction = s_{i-1} = s_i
        is right every time.  C = N = 19, P_global = 1, P_global' = min(1, 1+0) = 1,
        longest run 19 -> r = 20, min-entropy = -log2(max(1, P_local, 1/2)) = 0."""
        for method in ("stepwise", "vectorised"):
            r = lag.estimate([0] * 20, 1, method=method, return_correct=True)
            self.assertEqual(r["N"], 19)
            self.assertEqual(r["C"], 19)
            self.assertEqual(r["correct"], [1] * 19)
            self.assertEqual(r["P_global"], 1.0)
            self.assertEqual(r["P_global'"], 1.0)
            self.assertEqual(r["r"], 20)
            self.assertEqual(r["min_entropy"], 0.0)
            self.assertEqual(r["winner_final"], 1)
            self.assertEqual(r["scoreboard_final"][:3], [19, 18, 17])
        r8 = lag.estimate([0xAB] * 50, 8)
        self.assertEqual((r8["C"], r8["r"], r8["min_entropy"]), (49, 50, 0.0))

    def test_alternating_sequence(self):
        """0101..., 1-bit, L = 20.  Hand derivation: lag_d matches iff d is even.
        i=2: no match, prediction lag_1 = s_1 != s_2 -> correct_1 = 0.
        i=3: prediction still lag_1 (= s_2 != s_3) -> correct_2 = 0; then lag_2
             matches, scoreboard_2 = 1 >= scoreboard_1 = 0 -> winner = 2.
        i>=4: prediction = lag_2 = s_{i-2} = s_i -> correct; scoreboard_2 = i - 2
             stays the strict maximum (scoreboard_4 = i - 4, ...), winner stays 2.
        correct = (0, 0, 1 x 17): C = 17, longest run 17 -> r = 18,
        P_global = 17/19, P_global' = min(1, 17/19 + 2.576 sqrt((17/19)(2/19)/18)) = 1
        -> min-entropy 0."""
        x = [i % 2 for i in range(20)]
        for method in ("stepwise", "vectorised"):
            r = lag.estimate(x, 1, method=method, return_correct=True)
            self.assertEqual(r["correct"], [0, 0] + [1] * 17)
            self.assertEqual(r["C"], 17)
            self.assertEqual(r["r"], 18)
            self.assertEqual(r["winner_final"], 2)
            self.assertGreater(17 / 19 + 2.576 * math.sqrt((17 / 19) * (2 / 19) / 18), 1.0)
            self.assertEqual(r["P_global'"], 1.0)
            self.assertEqual(r["min_entropy"], 0.0)

    def test_counter_mod_200_and_the_two_readings_of_k(self):
        """s_i = (i-1) mod 200 as 8-bit symbols, L = 2000.  Hand derivation:
        lag_d = s_{i-d} equals s_i iff d is a multiple of 200, never for d <= 128,
        so nothing ever matches, the scoreboard stays 0, winner stays 1, and the
        prediction s_{i-1} is always wrong: C = 0, r = 1.
        P_global = 0 -> P_global' = 1 - 0.01^(1/1999) = 0.0023011...
        P_local (r = 1) ~ 1 - 0.99^(1/2000) = 5.0e-6.
        1/k binds:  k = 256 (alphabet) -> 8 bits exactly;
                    k = 200 (observed) -> log2(200) = 7.6439 (the conservative reading)."""
        x = [i % 200 for i in range(2000)]
        a = lag.estimate(x, 8, k_mode="alphabet", return_correct=True)
        self.assertEqual(a["C"], 0)
        self.assertEqual(a["r"], 1)
        self.assertEqual(sum(a["correct"]), 0)
        self.assertEqual(a["scoreboard_final"], [0] * 128)
        self.assertEqual(a["winner_final"], 1)
        self.assertAlmostEqual(a["P_global'"], 1 - 0.01 ** (1 / 1999), places=15)
        self.assertLess(a["P_local"], 1e-5)
        self.assertEqual(a["k"], 256)
        self.assertEqual(a["min_entropy"], 8.0)
        b = lag.estimate(x, 8, k_mode="observed")
        self.assertEqual(b["k"], 200)
        self.assertAlmostEqual(b["min_entropy"], math.log2(200), places=12)
        self.assertLess(b["min_entropy"], a["min_entropy"])

    def test_L_below_2_is_undefined(self):
        for S in ([], [1]):
            r = lag.estimate(S, 1)
            self.assertLessEqual(r["N"], 0)
            for key in ("min_entropy", "C", "r", "P_global", "P_global'", "P_local"):
                self.assertTrue(_nan(r[key]), key)

    def test_L_equals_2(self):
        # N = 1.  correct_1 = (s_1 == s_2).
        wrong = lag.estimate([0, 1], 1, return_correct=True)
        self.assertEqual(wrong["correct"], [0])
        self.assertEqual(wrong["P_global"], 0.0)
        self.assertEqual(wrong["P_global'"], 0.99)                  # 1 - 0.01^(1/1)
        self.assertEqual(wrong["r"], 1)
        self.assertAlmostEqual(wrong["min_entropy"], -math.log2(0.99), places=15)
        right = lag.estimate([1, 1], 1, return_correct=True)
        self.assertEqual(right["correct"], [1])
        self.assertEqual(right["P_global"], 1.0)
        self.assertTrue(_nan(right["P_global'"]))                     # 1 + 2.576*sqrt(0/0): no value
        self.assertTrue(_nan(right["min_entropy"]))
        self.assertEqual(right["r"], 2)
        self.assertFalse(_nan(right["P_local"]))


class VectorisedEqualsStepwise(unittest.TestCase):
    """The vectorised scan must reproduce the line-by-line transcription of step 3
    exactly, including tie-breaking in the scoreboard update, on inputs built to
    create ties (sticky and near-periodic sources) and across chunk boundaries."""

    KEYS = ("C", "r", "correct", "scoreboard_final", "winner_final", "P_local", "P_global'", "min_entropy")

    def _same(self, a, b):
        return a == b or (_nan(a) and _nan(b))

    def test_random_sticky_periodic(self):
        rng = np.random.default_rng(90)
        cases = 0
        for bps in (1, 2, 8):
            for L in (2, 3, 4, 5, 9, 17, 64, 129, 130, 257, 400):
                for D in (3, 128):
                    for kind in ("iid", "sticky", "periodic"):
                        if kind == "iid":
                            x = rng.integers(0, 1 << bps, size=L)
                        elif kind == "sticky":
                            x = np.empty(L, dtype=np.int64)
                            x[0] = rng.integers(0, 1 << bps)
                            for i in range(1, L):
                                x[i] = x[i - 1] if rng.random() < 0.8 else rng.integers(0, 1 << bps)
                        else:
                            per = int(rng.integers(1, 140))
                            x = np.resize(rng.integers(0, 1 << bps, size=per), L)
                            x = np.where(rng.random(L) < 0.05, rng.integers(0, 1 << bps, size=L), x)
                        a = lag.estimate(x, bps, D=D, method="stepwise", return_correct=True)
                        b = lag.estimate(x, bps, D=D, method="vectorised", return_correct=True, chunk=7)
                        c = lag.estimate(x, bps, D=D, method="vectorised", return_correct=True)
                        for key in self.KEYS:
                            self.assertTrue(self._same(a[key], b[key]) and self._same(a[key], c[key]),
                                            "bps=%d L=%d D=%d %s key=%s: %r / %r / %r" % (bps, L, D, kind, key, a[key], b[key], c[key]))
                        cases += 1
        self.assertGreater(cases, 150)


class Bitstring(unittest.TestCase):
    def test_msb_first_expansion(self):
        # glossary (PDF p. 69): "Bitstring: ... The leftmost bit is the most significant bit."
        self.assertEqual(lag.to_bitstring([0b101, 0b011], 3).tolist(), [1, 0, 1, 0, 1, 1])
        self.assertEqual(lag.to_bitstring([0x80, 0x01], 8).tolist(), [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])

    def test_bitstring_option_equals_running_on_bits(self):
        rng = np.random.default_rng(7)
        x = rng.integers(0, 256, size=600)
        a = lag.estimate(x, 8, bitstring=True)
        b = lag.estimate(lag.to_bitstring(x, 8), 1)
        self.assertEqual(a["k"], 2)
        self.assertEqual(a["bits_per_symbol"], 1)
        self.assertEqual(a["N"], 600 * 8 - 1)
        for key in ("C", "r", "P_global'", "P_local", "min_entropy"):
            self.assertEqual(a[key], b[key], key)


class Validation(unittest.TestCase):
    def test_out_of_range_symbol(self):
        with self.assertRaises(ValueError):
            lag.estimate([0, 1, 2], 1)
        with self.assertRaises(ValueError):
            lag.estimate([0, -1], 1)
        with self.assertRaises(TypeError):
            lag.estimate([0, 1], 1, bogus=3)

    def test_scoreboard_consistency(self):
        # scoreboard_d after the last step = number of i in (d, L] with s_{i-d} = s_i
        rng = np.random.default_rng(3)
        x = rng.integers(0, 4, size=500)
        r = lag.estimate(x, 2)
        for d in range(1, 129):
            self.assertEqual(r["scoreboard_final"][d - 1], int(np.count_nonzero(x[d:] == x[:-d])), "d=%d" % d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
