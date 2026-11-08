"""
Tests for py90b.lz78y -- SP 800-90B section 6.3.10, The LZ78Y Prediction Estimate.

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_lz78y.py -v
(or   <venv>/bin/python reference/py90b/tests/test_lz78y.py)

Every expected value below is either quoted from the standard (with the PDF page) or
derived BY HAND in the comment beside it.  Nothing is taken from the C++ tool's output.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
LZ78Y_PATH = HERE.parent / "lz78y.py"


def _load():
    """Load lz78y.py straight from its file so this test does not depend on whatever else
    the py90b package may import."""
    spec = importlib.util.spec_from_file_location("py90b_lz78y_under_test", LZ78Y_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lz = _load()
METHODS = ("literal", "vectorized")


# ============================================================================================
# 1. The standard's own worked example, SP 800-90B section 6.3.10 (PDF p. 65)
# ============================================================================================
class TestWorkedExample(unittest.TestCase):
    """PDF p. 65: 'Suppose that S = (2, 1, 3, 2, 1, 3, 1, 3, 1, 2, 1, 3, 2), and L = 13.  For the
    purpose of this example, suppose that B = 4 (instead of 16), then N = 8.'  ...  'After the
    predictions are all made, correct = (0, 0, 1, 1, 0, 1, 1, 0).  Then, P_global = 0.5,
    P'_global = 0.9868, P_local = 0.1229, and the resulting min-entropy estimate is 0.0191.'"""

    S = [2, 1, 3, 2, 1, 3, 1, 3, 1, 2, 1, 3, 2]
    # the table's "prediction" column, i = 6..13 (PDF p. 65): Null, Null, 3, 1, 3, 1, 3, 1
    PREDICTIONS = [lz.NULL, lz.NULL, 3, 1, 3, 1, 3, 1]
    CORRECT = [0, 0, 1, 1, 0, 1, 1, 0]

    def test_correct_array_both_methods(self):
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(self.S, 2, B=4, method=method, return_arrays=True)
                self.assertEqual(r["N"], 8)
                self.assertEqual(r["correct"].tolist(), self.CORRECT)
                self.assertEqual(r["prediction"].tolist(), self.PREDICTIONS)
                self.assertEqual(r["C"], 4)

    def test_trace_matches_table(self):
        # the table rows (i, prediction, s_i, correct_(i-B-1)) on PDF p. 65
        expected = [(6, lz.NULL, 3, 0), (7, lz.NULL, 1, 0), (8, 3, 3, 1), (9, 1, 1, 1),
                    (10, 3, 2, 0), (11, 1, 1, 1), (12, 3, 3, 1), (13, 1, 2, 0)]
        r = lz.estimate(self.S, 2, B=4, trace=True)
        self.assertEqual(r["trace"], expected)

    def test_statistics(self):
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(self.S, 2, B=4, method=method, k_mode="observed")
                self.assertEqual(r["k"], 3)                      # symbols {1, 2, 3}
                self.assertAlmostEqual(r["P_global"], 0.5, places=12)
                # P'_global = 0.5 + 2.576 sqrt(0.25/7) = 0.5 + 2.576 * 0.188982 = 0.98682
                self.assertAlmostEqual(r["P_global'"], 0.5 + 2.576 * math.sqrt(0.25 / 7), places=12)
                self.assertAlmostEqual(r["P_global'"], 0.9868, places=4)
                self.assertEqual(r["r"], 3)                      # longest run of ones is 2
                self.assertAlmostEqual(r["P_local"], 0.1229, delta=0.00005)
                self.assertAlmostEqual(r["min_entropy"], 0.0191, delta=0.00005)
                self.assertEqual(r["binding"], "P_global'")
                self.assertFalse(r["P_local_changes_result"])
                # with k = 2**2 = 4 (k_mode='alphabet') 1/k = 0.25 does not bind either
                r2 = lz.estimate(self.S, 2, B=4, method=method)
                self.assertAlmostEqual(r2["min_entropy"], r["min_entropy"], places=12)

    def test_dictionary_bookkeeping(self):
        # Count the contexts added in the table's "Add to D" column: 4 per step for i = 6..13
        # minus the repeats.  Repeats (already in D when revisited): i=9 D[1][3]; i=10 D[1,3][1]
        # and D[3][1]; i=12 D[2][1]; i=13 D[2,1][3] and D[1][3].  8*4 - 6 = 26?  No: D[1,3,1][2]
        # (i=11), D[3,1][2] (i=11) and D[1][2] (i=11) are new contexts? D[1,3,1] and D[3,1] and
        # D[1] already exist as CONTEXTS (added at i=9 / i=9 / i=7); only a new SYMBOL counter
        # is created, which does not change dictionarySize.  Distinct contexts, by hand:
        #   len 4: (2,1,3,2) (1,3,2,1) (3,2,1,3) (2,1,3,1) (1,3,1,3) (3,1,3,1) (1,3,1,2) (3,1,2,1) = 8
        #   len 3: (1,3,2) (3,2,1) (2,1,3) (1,3,1) (3,1,3) (3,1,2) (1,2,1) = 7
        #   len 2: (3,2) (2,1) (1,3) (3,1) (1,2) = 5
        #   len 1: (2) (1) (3) = 3                                            total 23
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(self.S, 2, B=4, method=method)
                self.assertEqual(r["dictionary_size"], 23)
                self.assertFalse(r["saturated"])
                self.assertIsNone(r["saturation_i"])


# ============================================================================================
# 2. Hand-derived tiny inputs that pin down the readings taken
# ============================================================================================
class TestHandDerived(unittest.TestCase):

    def test_tie_goes_to_higher_symbol_value(self):
        # B = 1, 2-bit symbols, S = (0, 1, 0, 2, 0, 2), L = 6, N = L - B - 1 = 4.
        # i=3: add D[(0)][1]=1.              predict from prev (1): not in D -> Null.  s_3=0 -> 0
        # i=4: add D[(1)][0]=1.              prev (0): D[0]={1:1} -> 1.           s_4=2 -> 0
        # i=5: D[(0)][2] -> D[0]={1:1,2:1}.  prev (2): not in D -> Null.           s_5=0 -> 0
        # i=6: add D[(2)][0]=1.              prev (0): {1:1,2:1} TIE -> "higher byte value" 2.
        #                                                                          s_6=2 -> 1
        # correct = (0,0,0,1): C=1, N=4, P_global=0.25,
        # P'_global = 0.25 + 2.576*sqrt(0.25*0.75/3) = 0.25 + 2.576*0.25 = 0.894
        # r = 2.  P_local(2, 4) ~ 0.059 < 0.894; 1/k = 0.25.  min-entropy = -log2(0.894) = 0.1617.
        # (Under a lowest-value tie rule the prediction at i=6 would be 1 -> C=0 ->
        #  P'_global = 1 - 0.01^(1/4) = 0.6838 -> min-entropy 0.548: the test discriminates.)
        S = [0, 1, 0, 2, 0, 2]
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(S, 2, B=1, method=method, return_arrays=True)
                self.assertEqual(r["N"], 4)
                self.assertEqual(r["prediction"].tolist(), [lz.NULL, 1, lz.NULL, 2])
                self.assertEqual(r["correct"].tolist(), [0, 0, 0, 1])
                self.assertAlmostEqual(r["P_global'"], 0.25 + 2.576 * 0.25, places=12)
                self.assertEqual(r["r"], 2)
                self.assertLess(r["P_local"], r["P_global'"])
                self.assertAlmostEqual(r["min_entropy"], -math.log2(0.894), places=12)

    def test_strict_greater_keeps_longer_context_on_count_tie(self):
        # B = 2, symbols {0,1,2} (2-bit), S = (0,1,0,2,1,2,0,1,0), L = 9, N = 6.  By hand:
        # i=4: add (0,1)->{0:1}, (1)->{0:1}.          prev (1,0),(0): not in D -> Null. s_4=2 -> 0
        # i=5: add (1,0)->{2:1}, (0)->{2:1}.          prev (0,2),(2): Null.             s_5=1 -> 0
        # i=6: add (0,2)->{1:1}, (2)->{1:1}.          prev (2,1) no; (1)->{0:1} -> 0.   s_6=2 -> 0
        # i=7: add (2,1)->{2:1}; (1)->{0:1,2:1}.      prev (1,2) no; (2)->{1:1} -> 1.   s_7=0 -> 0
        # i=8: add (1,2)->{0:1}; (2)->{1:1,0:1}.      prev (2,0) no; (0)->{2:1} -> 2.   s_8=1 -> 0
        # i=9: add (2,0)->{1:1}; (0)->{2:1,1:1}.      prev (0,1)->{0:1}: prediction 0, maxcount 1;
        #      then (1)->{0:1,2:1}: tie -> y=2 with count 1, and 1 > 1 is FALSE, so the
        #      prediction stays 0 (the longer context's).                       s_9=0 -> 1
        # correct = (0,0,0,0,0,1): C=1, N=6, P_global=1/6,
        # P'_global = 1/6 + 2.576*sqrt((1/6)(5/6)/5) = 1/6 + 2.576/6 = 0.59600
        # min-entropy = -log2(0.59600) = 0.7466.  (A '>=' reading predicts 2 at i=9 -> C=0 ->
        # P'_global = 1 - 0.01^(1/6) = 0.5358 -> 0.9003: the test discriminates.)
        S = [0, 1, 0, 2, 1, 2, 0, 1, 0]
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(S, 2, B=2, method=method, return_arrays=True)
                self.assertEqual(r["N"], 6)
                self.assertEqual(r["prediction"].tolist(), [lz.NULL, lz.NULL, 0, 1, 2, 0])
                self.assertEqual(r["correct"].tolist(), [0, 0, 0, 0, 0, 1])
                self.assertAlmostEqual(r["P_global'"], 1 / 6 + 2.576 / 6, places=12)
                self.assertAlmostEqual(r["min_entropy"], -math.log2(1 / 6 + 2.576 / 6), places=12)

    def test_dictionary_cap_worked_example_with_max_six(self):
        # The worked example again (B = 4) but maxDictionarySize = 6.  By hand:
        # i=6: adds (2,1,3,2),(1,3,2),(3,2),(2) -> size 4.  prediction Null.        s_6=3 -> 0
        # i=7: j=4 adds (1,3,2,1) -> 5; j=3 adds (3,2,1) -> 6 = max; j=2 (2,1) and j=1 (1) are
        #      NOT added (size < max fails) and are not in D so nothing is counted.
        #      prediction: (3,2,1,3),(2,1,3),(1,3),(3) none in D -> Null.           s_7=1 -> 0
        # i=8..10: no context visited is in D; predictions Null.           s=3,1,2 -> 0,0,0
        # i=11: update contexts (3,1,3,1),(1,3,1),(3,1),(1): none in D.
        #       prediction: (1,3,1,2),(3,1,2),(1,2) not in D; (2) -> D[2]={1:1} -> 1.  s_11=1 -> 1
        # i=12: update: (2) is in D -> D[2][1]=2.  prediction: (3,1,2,1),(1,2,1),(2,1),(1): none
        #       ((2,1) and (1) were refused at i=7) -> Null.                        s_12=3 -> 0
        # i=13: prediction (1,2,1,3),(2,1,3),(1,3),(3): none -> Null.               s_13=2 -> 0
        # correct = (0,0,0,0,0,1,0,0): C=1, N=8, dictionarySize=6, full at i=7.
        # P'_global = 1/8 + 2.576*sqrt((1/8)(7/8)/7) = 0.125 + 2.576*0.125 = 0.447
        S = [2, 1, 3, 2, 1, 3, 1, 3, 1, 2, 1, 3, 2]
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(S, 2, B=4, max_dictionary_size=6, method=method, return_arrays=True)
                self.assertEqual(r["prediction"].tolist(),
                                 [lz.NULL, lz.NULL, lz.NULL, lz.NULL, lz.NULL, 1, lz.NULL, lz.NULL])
                self.assertEqual(r["correct"].tolist(), [0, 0, 0, 0, 0, 1, 0, 0])
                self.assertEqual(r["dictionary_size"], 6)
                self.assertTrue(r["saturated"])
                self.assertEqual(r["saturation_i"], 7)
                self.assertAlmostEqual(r["P_global'"], 0.125 + 2.576 * 0.125, places=12)

    def test_degenerate_constant_input(self):
        # S = 40 zeros, 1-bit, B = 16: N = 40 - 17 = 23.  At i = 18 the update adds the all-zero
        # contexts of lengths 16..1 (16 contexts, each D[ctx][0] = 1); the prediction contexts
        # (s_(18-j)..s_17) are the SAME all-zero tuples, so prev is in D with D[prev][0] = 1 > 0
        # at j = 16 and the prediction is 0 = s_18.  Every later step likewise.  So
        # correct = all ones: C = N = 23, P_global = 1, P'_global = min(1, 1 + 2.576*0) = 1,
        # longest run 23, r = 24, dictionarySize stays 16, min-entropy = -log2(max(1, ., 1/2)) = 0.
        S = [0] * 40
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(S, 1, method=method, return_arrays=True)
                self.assertEqual(r["N"], 23)
                self.assertEqual(r["C"], 23)
                self.assertEqual(r["correct"].tolist(), [1] * 23)
                self.assertEqual(r["prediction"].tolist(), [0] * 23)
                self.assertEqual(r["P_global"], 1.0)
                self.assertEqual(r["P_global'"], 1.0)
                self.assertEqual(r["r"], 24)
                self.assertEqual(r["dictionary_size"], 16)
                self.assertFalse(r["saturated"])
                self.assertEqual(r["min_entropy"], 0.0)
                self.assertEqual(r["binding"], "P_global'")

    def test_too_short_is_nan(self):
        # L <= B + 1 gives N <= 0: the text defines nothing.  L = 17 -> N = 0; L = 5 -> N = -12.
        for L in (0, 1, 5, 16, 17):
            for method in METHODS:
                with self.subTest(L=L, method=method):
                    r = lz.estimate([0, 1] * (L // 2) + [0] * (L % 2), 1, method=method)
                    self.assertEqual(r["N"], L - 17)
                    self.assertTrue(math.isnan(r["min_entropy"]))
                    self.assertTrue(math.isnan(r["P_global"]))
                    self.assertTrue(math.isnan(r["P_local"]))
                    self.assertTrue(math.isnan(r["C"]))

    def test_first_prediction_index_and_count(self):
        # L = 18 -> N = 1: exactly one prediction, for s_18, made at i = B + 2 = 18.
        # Random 2-bit data: the dictionary has only just been filled with contexts ending at
        # s_16; the prediction contexts end at s_17 and can be in D only if they coincide.
        # Make them coincide with a constant tail: then the prediction is right.
        S = [1, 2, 3, 0, 1, 2, 3, 0] + [3] * 10          # L = 18; s_9..s_18 = 3
        for method in METHODS:
            with self.subTest(method=method):
                r = lz.estimate(S, 2, method=method, return_arrays=True)
                self.assertEqual(r["N"], 1)
                # j=16 context ending at s_16 = (s_1..s_16); prev = (s_2..s_17): differ.  j=1:
                # context (s_16) = (3) with D[3][s_17=3] = 1; prev (s_17) = (3) in D -> predict 3.
                self.assertEqual(r["prediction"].tolist(), [3])
                self.assertEqual(r["correct"].tolist(), [1])
                self.assertEqual(r["C"], 1)
                # N = 1 and P_global = 1: step 4 divides by N - 1 = 0 -> NaN by this file's reading
                self.assertTrue(math.isnan(r["P_global'"]))
                self.assertTrue(math.isnan(r["min_entropy"]))


# ============================================================================================
# 3. Steps 4-5 helpers against every number the standard prints for them
# ============================================================================================
class TestStatistics(unittest.TestCase):

    def test_p_local_spec_examples(self):
        # (r, N, printed P_local) from the worked examples of 6.3.7 (PDF p. 59), 6.3.8 (p. 60),
        # 6.3.9 (p. 63) and 6.3.10 (p. 65).  6.3.7: correct = (0,0,0,1,0,1,0,0,1) -> run 1 ->
        # r = 2, N = 9.  6.3.8: (0,0,0,1,1,0,0,0,0) -> r = 3, N = 9.  6.3.9: (0,0,1,1,0,1,0) ->
        # r = 3, N = 7.  6.3.10: (0,0,1,1,0,1,1,0) -> r = 3, N = 8.
        for r, N, printed, places in ((2, 9, 0.036, 3), (3, 9, 0.1167, 4), (3, 7, 0.1307, 4),
                                      (3, 8, 0.1229, 4)):
            with self.subTest(r=r, N=N):
                self.assertAlmostEqual(lz.p_local(r, N), printed, delta=0.5 * 10 ** (-places) + 1e-12)

    # Appendix G.2 Table 3 (PDF p. 84), "P_local values for different r values when
    # L = 1 000 000", transcribed in full; computed here with N = 1 000 000 (an N of
    # 1 000 000 - 17 changes nothing at the printed 4 decimals, see the probe log).
    TABLE3 = [
        (1, 0.0000), (2, 0.0001), (3, 0.0022), (4, 0.0100), (5, 0.0253), (6, 0.0468), (7, 0.0728),
        (8, 0.1014), (9, 0.1313), (10, 0.1614), (11, 0.1911), (12, 0.2200), (13, 0.2479),
        (14, 0.2746), (15, 0.3000), (16, 0.3242), (17, 0.3471), (18, 0.3688), (19, 0.3893),
        (20, 0.4088), (21, 0.4272), (22, 0.4447), (23, 0.4613), (24, 0.4770), (25, 0.4919),
        (26, 0.5060), (27, 0.5195), (28, 0.5323), (29, 0.5445), (30, 0.5561), (31, 0.5672),
        (32, 0.5778), (33, 0.5879), (34, 0.5976), (35, 0.6068), (36, 0.6157), (37, 0.6242),
        (38, 0.6324), (39, 0.6402), (40, 0.6477), (41, 0.6549), (42, 0.6619), (43, 0.6686),
        (44, 0.6750), (45, 0.6812), (46, 0.6872), (47, 0.6930), (48, 0.6986), (49, 0.7040),
        (55, 0.7092), (60, 0.7328), (65, 0.7531), (70, 0.7705), (75, 0.7858), (80, 0.7992),
        (85, 0.8111), (90, 0.8217), (95, 0.8312), (100, 0.8398), (105, 0.8476), (110, 0.8547),
        (115, 0.8612), (120, 0.8671), (125, 0.8726), (130, 0.8776), (135, 0.8823), (140, 0.8867),
        (145, 0.8907), (150, 0.8945), (155, 0.8980),
        (160, 0.9045), (165, 0.9074), (170, 0.9101), (175, 0.9127), (180, 0.9152), (185, 0.9175),
        (190, 0.9198), (195, 0.9219), (200, 0.9239), (205, 0.9258), (210, 0.9276), (215, 0.9293),
        (220, 0.9309), (225, 0.9325), (230, 0.9340), (235, 0.9355), (240, 0.9369), (245, 0.9382),
        (250, 0.9395), (255, 0.9407), (260, 0.9419), (265, 0.9430), (270, 0.9441), (275, 0.9452),
        (280, 0.9462), (285, 0.9471), (290, 0.9481), (295, 0.9490), (300, 0.9499), (310, 0.9516),
        (320, 0.9531), (330, 0.9546), (340, 0.9560), (350, 0.9573), (360, 0.9586),
        (370, 0.9597), (380, 0.9609), (390, 0.9619), (400, 0.9629), (410, 0.9639), (420, 0.9648),
        (430, 0.9656), (440, 0.9664), (450, 0.9672), (460, 0.9680), (470, 0.9687), (480, 0.9694),
        (490, 0.9700), (500, 0.9707), (550, 0.9735), (600, 0.9758), (650, 0.9778), (700, 0.9795),
        (750, 0.9809), (800, 0.9822), (850, 0.9833), (900, 0.9843), (950, 0.9852), (1000, 0.9860),
        (1500, 0.9909), (2000, 0.9933), (2500, 0.9947), (3000, 0.9957), (4000, 0.9968),
        (5000, 0.9975), (10000, 0.9988),
    ]
    # The 21 rows the table labels r = 55, 60, ..., 155 carry the values of r = 50, 55, ..., 150:
    # the label column jumps from 49 straight to 55 (no r = 50 row), each printed value in that
    # run equals the solver's value at r - 5 to all four decimals, and the next column resumes
    # in agreement at r = 160.  Read as a misprint of the LABELS in the standard's table
    # (measured in logs/reference-lz78y-probe-table3.log; recorded in spec_ambiguities).
    TABLE3_LABEL_OFFSET = {r: -5 for r in range(55, 156, 5)}

    def test_p_local_against_table_3_as_printed(self):
        # every row whose label is not disputed must match to the printed 4 decimals
        checked = 0
        for r, printed in self.TABLE3:
            if r in self.TABLE3_LABEL_OFFSET:
                continue
            with self.subTest(r=r):
                self.assertAlmostEqual(lz.p_local(r, 1_000_000), printed, delta=0.00005 + 1e-12)
            checked += 1
        self.assertEqual(checked, len(self.TABLE3) - len(self.TABLE3_LABEL_OFFSET))
        self.assertEqual(checked, 115)

    def test_p_local_table_3_mislabelled_block(self):
        # the disputed rows do NOT match as labelled, and DO match at label - 5
        for r, printed in self.TABLE3:
            if r not in self.TABLE3_LABEL_OFFSET:
                continue
            with self.subTest(r=r):
                as_labelled = lz.p_local(r, 1_000_000)
                self.assertGreater(abs(as_labelled - printed), 0.003)
                self.assertAlmostEqual(lz.p_local(r + self.TABLE3_LABEL_OFFSET[r], 1_000_000),
                                       printed, delta=0.00005 + 1e-12)

    def test_p_local_monotone_in_r(self):
        vals = [lz.p_local(r, 1000) for r in range(1, 60)]
        self.assertTrue(all(a < b for a, b in zip(vals, vals[1:])))
        self.assertTrue(all(0.0 <= v <= 1.0 for v in vals))

    def test_p_local_solves_the_equation(self):
        # the returned P_local makes step 5's right-hand side equal 0.99 (in logs)
        for r, N in ((2, 9), (3, 8), (24, 23), (10, 1_000_000), (300, 1_000_000)):
            with self.subTest(r=r, N=N):
                p = lz.p_local(r, N)
                self.assertAlmostEqual(lz.log_run_probability(p, r, N), math.log(0.99), places=9)

    def test_p_global_prime_branches(self):
        # P_global = 0 branch: 1 - 0.01^(1/N)
        P, Pp = lz.p_global_prime(0, 8)
        self.assertEqual(P, 0.0)
        self.assertAlmostEqual(Pp, 1 - 0.01 ** (1 / 8), places=15)
        # ordinary branch, the worked example: 0.5 + 2.576 sqrt(0.25/7)
        P, Pp = lz.p_global_prime(4, 8)
        self.assertAlmostEqual(Pp, 0.5 + 2.576 * math.sqrt(0.25 / 7), places=15)
        # the min(1, .) clamp
        P, Pp = lz.p_global_prime(4, 5)       # 0.8 + 2.576*sqrt(0.16/4) = 1.3152 -> 1
        self.assertEqual(Pp, 1.0)
        # z variant (FORK-DIVERGENCE-AND-TRUST.md D-1): 2.5758293... < 2.576, so the exact
        # quantile gives a SMALLER P'_global (and so a higher estimate) than the text's constant
        self.assertLess(lz.Z_BINARY64, lz.Z_TEXT)
        self.assertLess(lz.p_global_prime(4, 8, z=lz.Z_BINARY64)[1], lz.p_global_prime(4, 8)[1])
        # undefined cases
        self.assertTrue(math.isnan(lz.p_global_prime(1, 1)[1]))
        self.assertTrue(math.isnan(lz.p_global_prime(0, 0)[0]))

    def test_longest_run(self):
        self.assertEqual(lz.longest_run_of_ones([]), 0)
        self.assertEqual(lz.longest_run_of_ones([0, 0, 0]), 0)
        self.assertEqual(lz.longest_run_of_ones([0, 0, 1, 1, 0, 1, 1, 0]), 2)
        self.assertEqual(lz.longest_run_of_ones([1, 1, 1]), 3)
        self.assertEqual(lz.longest_run_of_ones([1, 0, 1, 1, 1, 0, 1]), 3)


# ============================================================================================
# 4. The two step-3 implementations agree, including when the dictionary cap binds
# ============================================================================================
class TestEquivalence(unittest.TestCase):

    def test_literal_equals_vectorized_random(self):
        rng = random.Random(2026_11_07)
        saturated_cases = 0
        for trial in range(300):
            bits = rng.choice([1, 1, 2, 3, 8])
            k = 1 << bits
            L = rng.randint(1, 300)
            B = rng.choice([1, 2, 3, 4, 16])
            md = rng.choice([1, 2, 3, 5, 7, 16, 50, 65536])
            if rng.random() < 0.3:
                base = [rng.randrange(k) for _ in range(rng.randint(1, 6))]
                s = [base[i % len(base)] if rng.random() < 0.85 else rng.randrange(k) for i in range(L)]
            else:
                s = [rng.randrange(k) for _ in range(L)]
            a = lz.predict_literal(s, B, md)
            b = lz.predict_vectorized(s, k, B, md)
            with self.subTest(trial=trial, bits=bits, L=L, B=B, md=md):
                self.assertEqual(a["correct"].tolist(), b["correct"].tolist())
                self.assertEqual(a["prediction"].tolist(), b["prediction"].tolist())
                self.assertEqual(a["dictionary_size"], b["dictionary_size"])
                self.assertEqual(a["saturated"], b["saturated"])
                self.assertEqual(a["saturation_i"], b["saturation_i"])
            saturated_cases += int(a["saturated"])
        self.assertGreater(saturated_cases, 50)      # the cap was actually exercised

    def test_literal_equals_vectorized_full_parameters(self):
        # the text's B = 16 and 65 536 on 8-bit and 1-bit data long enough to fill the dictionary
        rng = np.random.default_rng(90)
        saturated = {}
        for bits, L in ((8, 6000), (1, 6000)):
            s = rng.integers(0, 1 << bits, size=L)
            a = lz.estimate(s, bits, method="literal", return_arrays=True)
            b = lz.estimate(s, bits, method="vectorized", return_arrays=True)
            with self.subTest(bits=bits):
                self.assertEqual(a["correct"].tolist(), b["correct"].tolist())
                self.assertEqual(a["C"], b["C"])
                self.assertEqual(a["r"], b["r"])
                self.assertEqual(a["dictionary_size"], b["dictionary_size"])
                self.assertEqual(a["saturation_i"], b["saturation_i"])
                self.assertEqual(a["min_entropy"], b["min_entropy"])
            saturated[bits] = b["saturated"]
        # 8-bit random data fills 65 536 contexts quickly (~16 new contexts per step, so by
        # i ~ 4100 + 17); 6000 random BITS cannot (at most 2^j distinct j-bit contexts).
        self.assertTrue(saturated[8])
        self.assertFalse(saturated[1])


# ============================================================================================
# 5. Bitstring conversion (section 6.4 / 3.1.3) and the command line
# ============================================================================================
class TestBitstringAndCli(unittest.TestCase):

    def test_to_bitstring_msb_first(self):
        self.assertEqual(lz.to_bitstring([0b101, 0b010], 3).tolist(), [1, 0, 1, 0, 1, 0])
        self.assertEqual(lz.to_bitstring([0x80, 0x01], 8).tolist(),
                         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])

    def test_cli_literal_and_bitstring(self):
        rng = np.random.default_rng(5)
        raw = rng.integers(0, 256, size=600, dtype=np.uint8)
        raw[::3] = raw[::3] & 0x0F                         # some structure
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "in.bin")
            raw.tofile(path)
            env = dict(os.environ, OMP_NUM_THREADS="2")
            for mode in ("--literal", "--bitstring"):
                with self.subTest(mode=mode):
                    out = subprocess.run([sys.executable, str(LZ78Y_PATH), path, "8", mode],
                                         capture_output=True, text=True, env=env)
                    self.assertEqual(out.returncode, 0, out.stderr)
                    got = json.loads(out.stdout)
                    sym = raw.astype(np.int64) & 0xFF
                    exp = (lz.estimate(sym, 8) if mode == "--literal"
                           else lz.estimate(lz.to_bitstring(sym, 8), 1))
                    for key in ("C", "r", "N", "P_global", "P_global'", "P_local", "min_entropy",
                                "dictionary_size", "saturated"):
                        self.assertEqual(got[key], exp[key], key)
                    self.assertEqual(got["mode"], mode[2:])
                    self.assertEqual(got["bits_per_symbol_declared"], 8)

    def test_cli_low_bits_mask(self):
        # bits_per_symbol = 2 keeps the low 2 bits of every byte
        raw = np.array([0xFF, 0xFC, 0x01, 0x02, 0x83] * 20, dtype=np.uint8)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "in.bin")
            raw.tofile(path)
            out = subprocess.run([sys.executable, str(LZ78Y_PATH), path, "2", "--method=literal"],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            got = json.loads(out.stdout)
            exp = lz.estimate(raw.astype(np.int64) & 3, 2)
            self.assertEqual(got["C"], exp["C"])
            self.assertEqual(got["k"], 4)
            self.assertEqual(got["method"], "literal")

    def test_cli_usage(self):
        out = subprocess.run([sys.executable, str(LZ78Y_PATH)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertIn("usage", out.stderr)


# ============================================================================================
# 6. Options and the returned keys
# ============================================================================================
class TestOptionsAndKeys(unittest.TestCase):

    def test_required_keys_present(self):
        r = lz.estimate([0, 1] * 30, 1)
        for key in ("min_entropy", "C", "r", "N", "P_global", "P_global'", "P_local",
                    "dictionary_size", "saturated", "saturation_i", "k", "binding", "ambiguities"):
            self.assertIn(key, r)

    def test_k_mode_observed(self):
        # 8-bit declared, but the data uses only {0, 1, 2, 3}: k switches from 256 to the
        # observed count; C is unaffected; the estimate cannot rise (1/k only grows).
        s = np.array([0, 1, 2, 3, 1, 0, 3, 2, 2, 0, 1, 3, 3, 2, 0, 1] * 20)
        a = lz.estimate(s, 8)
        b = lz.estimate(s, 8, k_mode="observed")
        self.assertEqual(a["k"], 256)
        self.assertEqual(b["k"], 4)
        self.assertEqual(a["C"], b["C"])
        self.assertLessEqual(b["min_entropy"], a["min_entropy"] + 1e-12)

    def test_z_variant(self):
        s = np.random.default_rng(3).integers(0, 2, size=400)
        a = lz.estimate(s, 1)
        b = lz.estimate(s, 1, z=lz.Z_BINARY64)
        self.assertEqual(a["binding"], "P_global'")              # so z actually matters here
        self.assertNotEqual(a["P_global"], 0.0)
        # the exact quantile is the smaller z: smaller P'_global, HIGHER min-entropy (permissive,
        # the direction FORK-DIVERGENCE-AND-TRUST.md D-1 records for the C++'s ZALPHA)
        self.assertGreater(b["min_entropy"], a["min_entropy"])
        self.assertLess(b["min_entropy"] - a["min_entropy"], 1e-3)

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            lz.estimate([0, 2], 1)
        with self.assertRaises(ValueError):
            lz.estimate([0], 0)
        with self.assertRaises(ValueError):
            lz.estimate([0] * 20, 1, method="nope")
        with self.assertRaises(ValueError):
            lz.estimate([0] * 20, 1, k_mode="nope")


if __name__ == "__main__":
    unittest.main(verbosity=2)
