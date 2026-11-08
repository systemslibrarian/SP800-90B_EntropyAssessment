"""Tests for py90b.multimcw against SP 800-90B (January 2018) section 6.3.7 and Appendix G.2.

Run:  <venv>/python -m unittest py90b.tests.test_multimcw   (from reference/)
Every expected value below is either quoted from the standard (PDF page given) or derived
by hand in the comment next to it.  Nothing here was taken from the C++ tool.
"""
import math
import os
import sys
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))  # reference/ -> import py90b

from py90b import multimcw as M  # noqa: E402


# ------------------------------------------------------------------------------------------
# 1. The section's own worked example (PDF p. 58-59)
# ------------------------------------------------------------------------------------------
class WorkedExample637(unittest.TestCase):
    """'Suppose that S = (1, 2, 1, 0, 2, 1, 1, 2, 2, 0, 0, 0), so that L = 12 ... suppose that
    w1 = 3, w2 = 5, w3 = 7, w4 = 9 ... Then N = 9.'  Table on PDF p. 58; results on p. 59."""

    S = [1, 2, 1, 0, 2, 1, 1, 2, 2, 0, 0, 0]
    WINDOWS = (3, 5, 7, 9)
    # columns: i, frequent (step 3a), winner (step 3b), prediction, s_i, correct_(i-w1), scoreboard (step 3d)
    TABLE = [
        (4,  (1, None, None, None), 1, 1, 0, 0, (0, 0, 0, 0)),
        (5,  (0, None, None, None), 1, 0, 2, 0, (0, 0, 0, 0)),
        (6,  (2, 2, None, None),    1, 2, 1, 0, (0, 0, 0, 0)),
        (7,  (1, 1, None, None),    1, 1, 1, 1, (1, 1, 0, 0)),
        (8,  (1, 1, 1, None),       2, 1, 2, 0, (1, 1, 0, 0)),
        (9,  (1, 2, 2, None),       2, 2, 2, 1, (1, 2, 1, 0)),
        (10, (2, 2, 2, 2),          2, 2, 0, 0, (1, 2, 1, 0)),
        (11, (2, 2, 2, 2),          2, 2, 0, 0, (1, 2, 1, 0)),
        (12, (0, 0, 2, 0),          2, 0, 0, 1, (2, 3, 1, 1)),
    ]

    def setUp(self):
        self.res = M.estimate(self.S, 2, windows=self.WINDOWS, trace=True)

    def test_step3_table_every_row(self):
        res = self.res
        self.assertEqual(res["N"], 9)
        for n, (i, freq, winner, pred, si, corr, sb_after) in enumerate(self.TABLE):
            self.assertEqual(i, n + 4)
            got_freq = tuple(None if int(f[n]) == M.NULL else int(f[n]) for f in res["frequent"])
            self.assertEqual(got_freq, freq, f"i={i} frequent (tie rule / Null rule)")
            wu, got_pred, got_corr, got_sb = res["trace"][n]
            self.assertEqual(wu, winner, f"i={i} winner used (scoreboard >= rule)")
            self.assertEqual(got_pred, pred, f"i={i} prediction")
            self.assertEqual(self.S[i - 1], si)
            self.assertEqual(got_corr, corr, f"i={i} correct")
            self.assertEqual(tuple(got_sb), sb_after, f"i={i} scoreboard after 3d")

    def test_results(self):
        res = self.res
        # 'correct = (0, 0, 0, 1, 0, 1, 0, 0, 1)'
        self.assertEqual(res["correct"].tolist(), [0, 0, 0, 1, 0, 1, 0, 0, 1])
        self.assertEqual(res["C"], 3)
        self.assertEqual(res["r"], 2)                  # longest run of ones = 1, r = 1 + 1
        # 'P_global = 0.3333, P'_global = 0.7627, P_local = 0.036, ... min-entropy estimate is 0.3908'
        self.assertAlmostEqual(res["P_global"], 1 / 3, places=12)
        # by hand: 1/3 + 2.576*sqrt((1/3)(2/3)/8) = 1/3 + 2.576*sqrt(1/36) = 1/3 + 2.576/6 = 0.762666...
        self.assertAlmostEqual(res["P_global'"], 1 / 3 + 2.576 / 6, places=12)
        self.assertAlmostEqual(res["P_global'"], 0.7627, delta=5e-5)
        self.assertAlmostEqual(res["P_local"], 0.036, delta=5e-4)      # printed to 3 decimals
        self.assertEqual(res["binding"], "P_global'")
        # The text prints 0.3908, which is -log2(0.7627) = 0.39081 (the ROUNDED P'_global);
        # -log2(0.762666...) = 0.390875.  Both round-trip within 1e-4; recorded in the module
        # docstring as a rounding artefact of the example, not an algorithmic ambiguity.
        self.assertAlmostEqual(res["min_entropy"], -math.log2(1 / 3 + 2.576 / 6), places=12)
        self.assertAlmostEqual(res["min_entropy"], 0.3908, delta=1e-4)
        self.assertEqual(res["scoreboard"], [2, 3, 1, 1])
        self.assertEqual(res["winner"], 2)


# ------------------------------------------------------------------------------------------
# 2. Step 6 (P_local) against every printed value in the standard
# ------------------------------------------------------------------------------------------
class PLocalAgainstTheStandard(unittest.TestCase):
    def test_worked_examples_of_all_four_predictors(self):
        # The same equation is printed in 6.3.7-6.3.10; each example gives correct[] and P_local.
        cases = [
            # section, correct[] as printed, printed P_local, PDF page
            ("6.3.7",  [0, 0, 0, 1, 0, 1, 0, 0, 1],    0.036,  59),
            ("6.3.8",  [0, 0, 0, 1, 1, 0, 0, 0, 0],    0.1167, 60),
            ("6.3.9",  [0, 0, 1, 1, 0, 1, 0],          0.1307, 63),
            ("6.3.10", [0, 0, 1, 1, 0, 1, 1, 0],       0.1229, 66),
        ]
        for sec, correct, expected, page in cases:
            N = len(correct)
            r = M.longest_run_of_ones(correct) + 1
            got = M.p_local(r, N)
            tol = 5e-4 if sec == "6.3.7" else 5e-5    # 3 vs 4 printed decimals
            self.assertAlmostEqual(got, expected, delta=tol, msg=f"{sec} (PDF p.{page}) r={r} N={N}")

    def test_solution_satisfies_the_equation(self):
        """Evaluate step 6's right-hand side (direct form, not the log form the solver uses)
        at the returned P_local and check it equals 0.99."""
        for r, N in ((2, 9), (3, 9), (3, 7), (3, 8), (4, 20), (1, 50), (15, 999937), (20, 1_000_000), (300, 1_000_000)):
            p = M.p_local(r, N)
            q = 1 - p
            x = 1.0
            for _ in range(10):
                x = 1 + q * p ** r * x ** (r + 1)
            rhs = (1 - p * x) / ((r + 1 - r * x) * q) * x ** (-(N + 1))
            self.assertAlmostEqual(rhs, 0.99, delta=1e-9, msg=f"r={r} N={N} p={p}")

    # Appendix G.2 Table 3 (PDF p. 76): 'P_local values for different r values when L=1 000 000'.
    TABLE3 = {
        1: 0.0000, 2: 0.0001, 3: 0.0022, 4: 0.0100, 5: 0.0253, 6: 0.0468, 7: 0.0728, 8: 0.1014, 9: 0.1313,
        10: 0.1614, 11: 0.1911, 12: 0.2200, 13: 0.2479, 14: 0.2746, 15: 0.3000, 16: 0.3242, 17: 0.3471,
        18: 0.3688, 19: 0.3893, 20: 0.4088, 21: 0.4272, 22: 0.4447, 23: 0.4613, 24: 0.4770, 25: 0.4919,
        26: 0.5060, 27: 0.5195, 28: 0.5323, 29: 0.5445, 30: 0.5561, 31: 0.5672, 32: 0.5778, 33: 0.5879,
        34: 0.5976, 35: 0.6068, 36: 0.6157, 37: 0.6242, 38: 0.6324, 39: 0.6402, 40: 0.6477, 41: 0.6549,
        42: 0.6619, 43: 0.6686, 44: 0.6750, 45: 0.6812, 46: 0.6872, 47: 0.6930, 48: 0.6986, 49: 0.7040,
        55: 0.7092, 60: 0.7328, 65: 0.7531, 70: 0.7705, 75: 0.7858, 80: 0.7992, 85: 0.8111, 90: 0.8217,
        95: 0.8312, 100: 0.8398, 105: 0.8476, 110: 0.8547, 115: 0.8612, 120: 0.8671, 125: 0.8726,
        130: 0.8776, 135: 0.8823, 140: 0.8867, 145: 0.8907, 150: 0.8945, 155: 0.8980,
        160: 0.9045, 165: 0.9074, 170: 0.9101, 175: 0.9127, 180: 0.9152, 185: 0.9175, 190: 0.9198,
        195: 0.9219, 200: 0.9239, 205: 0.9258, 210: 0.9276, 215: 0.9293, 220: 0.9309, 225: 0.9325,
        230: 0.9340, 235: 0.9355, 240: 0.9369, 245: 0.9382, 250: 0.9395, 255: 0.9407, 260: 0.9419,
        265: 0.9430, 270: 0.9441, 275: 0.9452, 280: 0.9462, 285: 0.9471, 290: 0.9481, 295: 0.9490,
        300: 0.9499, 310: 0.9516, 320: 0.9531, 330: 0.9546, 340: 0.9560, 350: 0.9573, 360: 0.9586,
        370: 0.9597, 380: 0.9609, 390: 0.9619, 400: 0.9629, 410: 0.9639, 420: 0.9648, 430: 0.9656,
        440: 0.9664, 450: 0.9672, 460: 0.9680, 470: 0.9687, 480: 0.9694, 490: 0.9700, 500: 0.9707,
        550: 0.9735, 600: 0.9758, 650: 0.9778, 700: 0.9795, 750: 0.9809, 800: 0.9822, 850: 0.9833,
        900: 0.9843, 950: 0.9852, 1000: 0.9860, 1500: 0.9909, 2000: 0.9933, 2500: 0.9947, 3000: 0.9957,
        4000: 0.9968, 5000: 0.9975, 10000: 0.9988,
    }
    # The second column of the printed table is mislabelled from r = 55 to r = 155: each printed
    # value is the value for r - 5 (0.7092 is r = 50's, 0.7328 is r = 55's, ..., 0.8980 is
    # r = 150's); r = 160 onward is labelled correctly again.  Measured in
    # logs/reference-multimcw-probe1-worked-example-table3.log on 2026-11-07: all 21 rows are
    # 0.3 % - 2.4 % off under their printed label and within 5e-5 under label - 5.
    MISLABELLED = set(range(55, 160, 5))

    def test_table3_correctly_labelled_rows(self):
        for r, expected in self.TABLE3.items():
            if r in self.MISLABELLED:
                continue
            got = M.p_local(r, 1_000_000)
            self.assertAlmostEqual(got, expected, delta=6e-5, msg=f"Table 3 r={r}")

    def test_table3_mislabelled_block_is_shifted_by_five(self):
        for r in sorted(self.MISLABELLED):
            printed = self.TABLE3[r]
            under_label = M.p_local(r, 1_000_000)
            under_label_minus_5 = M.p_local(r - 5, 1_000_000)
            self.assertGreater(abs(under_label - printed), 3e-3, f"r={r}: the printed value is NOT r's")
            self.assertAlmostEqual(under_label_minus_5, printed, delta=6e-5, msg=f"r={r}: printed value is r-5's")

    def test_r_equals_one_is_q_to_the_N(self):
        # With r = 1 (no correct prediction at all) the equation's x converges to 1/q and the
        # right-hand side reduces to q^N exactly (derived in the module); so P_local should be
        # 1 - 0.99**(1/N).  Hand value for N = 9: 1 - 0.99**(1/9) = 0.0011160807...
        self.assertAlmostEqual(M.p_local(1, 9), 1 - 0.99 ** (1 / 9), delta=2e-6)
        self.assertAlmostEqual(M.p_local(1, 999937), 1 - 0.99 ** (1 / 999937), delta=1e-11)

    def test_mp_variant_agrees_if_available(self):
        try:
            import mpmath  # noqa: F401
        except ImportError:
            self.skipTest("mpmath not installed in this venv")
        for r, N in ((2, 9), (20, 999937), (300, 1_000_000)):
            f = M.p_local(r, N)
            g, s = M.p_local_mp(r, N, dps=40)
            self.assertAlmostEqual(f, g, delta=1e-12, msg=f"r={r} N={N} mp={s}")


# ------------------------------------------------------------------------------------------
# 3. Hand-derived inputs with the real windows (63, 255, 1023, 4095)
# ------------------------------------------------------------------------------------------
class HandDerived(unittest.TestCase):
    def test_degenerate_all_one_symbol(self):
        # 1-bit, L = 100 zeros.  N = 100 - 63 = 37.  Every window is all zeros, frequent_1 = 0 at
        # every step (j = 2..4 are Null since L < 255), prediction 0 = s_i always: correct is all
        # ones, C = 37, P_global = 1, P'_global = min(1, 1 + 2.576*sqrt(0)) = 1, longest run 37,
        # r = 38, min-entropy = -log2(max(1, P_local, 1/2)) = 0.  scoreboard_1 = 37, winner = 1.
        res = M.estimate([0] * 100, 1)
        self.assertEqual((res["N"], res["C"], res["r"]), (37, 37, 38))
        self.assertEqual(res["P_global"], 1.0)
        self.assertEqual(res["P_global'"], 1.0)
        self.assertEqual(res["min_entropy"], 0.0)
        self.assertEqual(res["scoreboard"], [37, 0, 0, 0])
        self.assertEqual(res["winner"], 1)
        self.assertEqual(res["binding"], "P_global'")

    def test_tie_rule_with_real_window(self):
        # 2-bit symbols.  s = 21 zeros, 21 ones, 21 twos, then 2, 0.   L = 65, N = 2.
        # t = 63: window s[0:63] has 21 of each of 0,1,2 -> three-way tie; the most recently
        #         appeared is 2 (s[62]) -> prediction 2; s[63] = 2 -> correct.  (Smallest-value
        #         or first-seen tie-breaking would predict 0 and be wrong.)  scoreboard_1 = 1.
        # t = 64: window s[1:64] = 20 zeros, 21 ones, 22 twos -> 2; s[64] = 0 -> wrong.
        # correct = (1, 0): C = 1, r = 2, P_global = 0.5,
        # P'_global = min(1, 0.5 + 2.576*sqrt(0.25/1)) = min(1, 1.788) = 1 -> min-entropy 0.
        s = [0] * 21 + [1] * 21 + [2] * 21 + [2, 0]
        res = M.estimate(s, 2, return_arrays=True)
        self.assertEqual(res["N"], 2)
        self.assertEqual(res["frequent"][0].tolist(), [2, 2])
        self.assertEqual([f.tolist() for f in res["frequent"][1:]], [[-1, -1]] * 3)
        self.assertEqual(res["correct"].tolist(), [1, 0])
        self.assertEqual((res["C"], res["r"]), (1, 2))
        self.assertEqual(res["P_global"], 0.5)
        self.assertEqual(res["P_global'"], 1.0)
        self.assertEqual(res["min_entropy"], 0.0)

    def test_binary_twenty_predictions(self):
        # 1-bit.  63 zeros then the 20-bit tail below; L = 83, N = 20.  Only w1 = 63 is ever
        # available (L < 255).  Every 63-window contains at most 20 ones (< 32), so frequent_1 = 0
        # at every step and the prediction is always 0; correct[n] = 1 iff tail[n] = 0.
        tail = [1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1]
        expected_correct = [1 - b for b in tail]      # = [0,1,0,0,1,1,0,1,1,1,0,0,0,1,0,1,1,0,1,0]
        # C = 10 zeros in tail; longest run of ones in correct = 3 (indices 7,8,9) -> r = 4;
        # P_global = 10/20 = 0.5; P'_global = 0.5 + 2.576*sqrt(0.25/19) = 0.5 + 2.576*0.1147079
        #          = 0.795488...; scoreboard_1 = 10 (one per zero), winner stays 1.
        res = M.estimate([0] * 63 + tail, 1, return_arrays=True)
        self.assertEqual(res["N"], 20)
        self.assertEqual(res["correct"].tolist(), expected_correct)
        self.assertEqual((res["C"], res["longest_run"], res["r"]), (10, 3, 4))
        self.assertEqual(res["P_global"], 0.5)
        self.assertAlmostEqual(res["P_global'"], 0.5 + 2.576 * math.sqrt(0.25 / 19), places=14)
        self.assertEqual(res["scoreboard"], [10, 0, 0, 0])
        self.assertEqual(res["winner"], 1)
        # step 7 with the module's own P_local (checked against the equation elsewhere)
        pl = M.p_local(4, 20)
        self.assertAlmostEqual(res["P_local"], pl, places=15)
        self.assertAlmostEqual(res["min_entropy"], -math.log2(max(res["P_global'"], pl, 0.5)), places=14)

    def test_k_floor_alphabet_vs_observed(self):
        # 4-bit counter (t mod 16) DECLARED as 8-bit, L = 2000, N = 1937.
        # Window 63 = 3*16 + 15: the residue of s[t] (= residue of s[t-16]) appears 3 times, the
        # other 15 residues 4 times, so the most common value is never s[t]; likewise 255 = 15*16+15,
        # 1023 = 63*16+15, 4095 (never available).  So C = 0, P_global = 0,
        # P'_global = 1 - 0.01**(1/1937) = 0.0023748..., r = 1.
        # Step 7: 1/k.  k = 2**8 = 256 -> 1/256 = 0.0039 > P'_global -> min-entropy = 8 bits.
        #                k = 16 observed -> 1/16 = 0.0625 -> 4 bits.  The reading of k is material.
        s = [t % 16 for t in range(2000)]
        a = M.estimate(s, 8, k_mode="alphabet")
        o = M.estimate(s, 8, k_mode="observed")
        for res in (a, o):
            self.assertEqual((res["N"], res["C"], res["r"]), (1937, 0, 1))
            self.assertEqual(res["P_global"], 0.0)
            self.assertAlmostEqual(res["P_global'"], 1 - 0.01 ** (1 / 1937), places=15)
        self.assertEqual((a["k"], a["binding"]), (256, "1/k"))
        self.assertEqual(a["min_entropy"], 8.0)
        self.assertEqual((o["k"], o["binding"]), (16, "1/k"))
        self.assertEqual(o["min_entropy"], 4.0)

    def test_short_input_is_nan(self):
        for L in (0, 1, 62, 63):
            res = M.estimate([0, 1] * (L // 2) + [0] * (L % 2), 1)
            self.assertEqual(res["N"], L - 63)
            for key in ("min_entropy", "C", "r", "P_global", "P_global'", "P_local"):
                self.assertTrue(math.isnan(res[key]), f"L={L} {key}")

    def test_n_equals_one_divides_by_zero(self):
        # L = 64 ones: N = 1, C = 1, P_global = 1, P'_global has (N-1) = 0 in a denominator.
        res = M.estimate([1] * 64, 1)
        self.assertEqual((res["N"], res["C"]), (1, 1))
        self.assertTrue(math.isnan(res["P_global'"]))
        self.assertTrue(math.isnan(res["min_entropy"]))
        # L = 64 with the single prediction wrong: P_global = 0 -> the first branch, no division.
        res0 = M.estimate([0] * 63 + [1], 1)
        self.assertEqual((res0["N"], res0["C"]), (1, 0))
        self.assertAlmostEqual(res0["P_global'"], 1 - 0.01, places=15)

    def test_z_variant(self):
        tail = [1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1]
        s = [0] * 63 + tail
        a = M.estimate(s, 1)
        b = M.estimate(s, 1, z=M.Z_BINARY64)
        self.assertAlmostEqual(a["P_global'"], 0.5 + 2.576 * math.sqrt(0.25 / 19), places=14)
        self.assertAlmostEqual(b["P_global'"], 0.5 + 2.5758293035489008 * math.sqrt(0.25 / 19), places=14)
        self.assertGreater(a["P_global'"], b["P_global'"])   # the text's constant is the larger

    def test_bitstring_is_msb_first(self):
        self.assertEqual(M.to_bitstring([0x80, 0x01], 8).tolist(), [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(M.to_bitstring([0b10, 0b01], 2).tolist(), [1, 0, 0, 1])


# ------------------------------------------------------------------------------------------
# 4. Internal consistency: the vectorised step 3.a and the fast scoreboard against naive loops
# ------------------------------------------------------------------------------------------
def naive_most_common(s, windows):
    """Step 3.a.i/ii written as plainly as possible, O(L * w)."""
    L = len(s)
    w1 = windows[0]
    out = [[] for _ in windows]
    for t in range(w1, L):
        for j, w in enumerate(windows):
            if t < w:
                out[j].append(M.NULL)
                continue
            window = s[t - w: t]
            counts = {}
            lastpos = {}
            for u, v in enumerate(window):
                counts[v] = counts.get(v, 0) + 1
                lastpos[v] = u
            best = max(counts.values())
            tied = [v for v, c in counts.items() if c == best]
            out[j].append(max(tied, key=lambda v: lastpos[v]))   # most recently appeared
    return [np.array(o, dtype=np.int64) for o in out]


class InternalConsistency(unittest.TestCase):
    def test_vectorised_frequent_matches_naive(self):
        rng = np.random.default_rng(90)
        for k, L, windows, chunk in ((3, 600, (3, 5, 7, 9), 50), (5, 1500, (63, 255), 128), (2, 900, (63, 255, 1023), 64),
                                     (7, 700, (63,), 1000), (4, 1200, (10, 11, 12, 13), 7)):
            s = rng.integers(0, k, size=L)
            # bias toward ties: long constant stretches
            s[200:260] = 1
            s[300:330] = 2 % k
            fast = M.most_common_in_windows(s, k, windows, chunk=chunk)
            slow = naive_most_common(s.tolist(), windows)
            for j in range(len(windows)):
                self.assertTrue(np.array_equal(fast[j], slow[j]), f"k={k} L={L} windows={windows} j={j}")

    def test_fast_scoreboard_matches_literal(self):
        rng = np.random.default_rng(7)
        for k, N in ((2, 5000), (4, 3000), (16, 4000)):
            s_pred = rng.integers(0, k, size=N)
            frequent = [rng.integers(-1, k, size=N) for _ in range(4)]
            c1, sb1, w1 = M.run_scoreboard(s_pred, frequent)
            c2, sb2, w2, _ = M.run_scoreboard_literal(s_pred, frequent)
            self.assertTrue(np.array_equal(c1, c2))
            self.assertEqual((sb1, w1), (sb2, w2))

    def test_chunking_does_not_change_the_answer(self):
        rng = np.random.default_rng(11)
        s = rng.integers(0, 4, size=9000)
        a = M.estimate(s, 2, chunk=32768, return_arrays=True)
        b = M.estimate(s, 2, chunk=97, return_arrays=True)
        self.assertTrue(np.array_equal(a["correct"], b["correct"]))
        self.assertEqual(a["min_entropy"], b["min_entropy"])

    def test_longest_run(self):
        self.assertEqual(M.longest_run_of_ones([]), 0)
        self.assertEqual(M.longest_run_of_ones([0, 0]), 0)
        self.assertEqual(M.longest_run_of_ones([1]), 1)
        self.assertEqual(M.longest_run_of_ones([1, 1, 0, 1, 1, 1, 0, 1]), 3)
        self.assertEqual(M.longest_run_of_ones([1, 1, 1, 1]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
