"""
Tests for py90b.mcv -- SP 800-90B section 6.3.1, The Most Common Value Estimate.

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_mcv.py -v
(or   <venv>/bin/python reference/py90b/tests/test_mcv.py)

Every expected value below is either quoted from the standard (with the PDF
page) or derived BY HAND in the comment beside it.  Nothing is taken from the
C++ tool's output.
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
from collections import Counter

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MCV_PATH = HERE.parent / "mcv.py"


def _load_mcv():
    """Load mcv.py straight from its file so this test does not depend on
    whatever else the py90b package may import."""
    spec = importlib.util.spec_from_file_location("py90b_mcv_under_test", MCV_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mcv = _load_mcv()


def plain_python_mcv(symbols, z=2.576):
    """
    A deliberately un-vectorised transcription of section 6.3.1 (PDF p. 49),
    used to cross-check the numpy path.  Same operations in the same order, so
    the two must agree bit for bit.
    """
    S = list(symbols)
    L = len(S)
    if L == 0:
        return 0, float("nan"), float("nan"), float("nan")
    counts = Counter(S)
    mode_count = max(counts.values())                     # step 1: max_i #{x_i in S}
    p_hat = mode_count / L                                 #         / L
    if L < 2:
        return mode_count, p_hat, float("nan"), float("nan")
    p_u = min(1.0, p_hat + z * math.sqrt(p_hat * (1.0 - p_hat) / (L - 1)))   # step 2
    return mode_count, p_hat, p_u, 0.0 - math.log2(p_u)                      # step 3


class TestSpecWorkedExample(unittest.TestCase):
    """SP 800-90B section 6.3.1 worked example (PDF p. 50)."""

    # "If the dataset is S = (0, 1, 1, 2, 0, 1, 2, 2, 0, 1, 0, 1, 1, 0, 2, 2, 1, 0, 2, 1),
    #  with L = 20, the most common value is 1, with p-hat = 0.4.
    #  p_u = 0.4 + 2.576 sqrt(0.012) = 0.6895. The min-entropy estimate is
    #  -log2(0.6822) = 0.5363."
    S = [0, 1, 1, 2, 0, 1, 2, 2, 0, 1, 0, 1, 1, 0, 2, 2, 1, 0, 2, 1]

    def test_final_figures_match_the_formula(self):
        self.assertEqual(len(self.S), 20)
        r = mcv.estimate(self.S, 2)
        self.assertEqual(r["L"], 20)
        self.assertEqual(r["mode value"], 1)          # "the most common value is 1"
        self.assertEqual(r["Mode count"], 8)          # 1 occurs 8 times in S
        self.assertEqual(r["p-hat"], 0.4)             # 8/20 = 0.4
        # By hand, with the formula as printed (L - 1 = 19):
        #   p-hat(1-p-hat)/(L-1) = 0.4*0.6/19 = 0.24/19 = 0.0126316
        #   sqrt(0.0126316)      = 0.1123903
        #   2.576 * 0.1123903    = 0.2895174
        #   p_u = 0.4 + 0.2895174 = 0.6895174           -> "0.6895"   (matches the text)
        #   -log2(0.6895174)     = 0.53634              -> "0.5363"   (matches the text)
        self.assertAlmostEqual(r["p_u"], 0.6895, places=4)
        self.assertAlmostEqual(r["min entropy"], 0.5363, places=4)
        self.assertEqual(r["min_entropy"], r["min entropy"])
        self.assertFalse(r["p_u clamped"])
        self.assertEqual(r["z"], 2.576)
        self.assertEqual(r["variant"], "literal")

    def test_example_intermediates_are_an_erratum(self):
        """
        The example's intermediate text is internally inconsistent with its own
        formula; this test pins the diagnosis so nobody 'fixes' the code to
        match the typo.  (Recorded in spec_ambiguities.)
        """
        p_hat, L = 0.4, 20
        # The text prints "sqrt(0.012)".  0.012 = 0.24/20 = p-hat(1-p-hat)/L, i.e. a
        # division by L; the formula divides by L - 1 = 19, giving 0.0126316.
        self.assertAlmostEqual(p_hat * (1 - p_hat) / L, 0.012, places=12)
        self.assertNotAlmostEqual(p_hat * (1 - p_hat) / (L - 1), 0.012, places=4)
        # With that division by L one gets 0.4 + 2.576*sqrt(0.012) = 0.6822 -- which is
        # the text's log ARGUMENT, not the 0.6895 the text prints as p_u.
        self.assertAlmostEqual(p_hat + 2.576 * math.sqrt(0.012), 0.6822, places=4)
        # And -log2(0.6822) = 0.5517, NOT the printed 0.5363.  The printed 0.5363 is
        # -log2 of the formula's UNROUNDED p_u = 0.4 + 2.576*sqrt(0.24/19) = 0.689517
        # (-log2(0.689517) = 0.53634 -> 0.5363; note -log2 of the 4-digit 0.6895 would
        # be 0.53638 -> 0.5364, so the text carried full precision into step 3).
        # So the FINAL figures follow the formula and only the intermediates are mistyped.
        self.assertAlmostEqual(0.0 - math.log2(0.6822), 0.5517, places=4)
        p_u_formula = p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / (L - 1))
        self.assertAlmostEqual(p_u_formula, 0.6895, places=4)
        self.assertAlmostEqual(0.0 - math.log2(p_u_formula), 0.5363, places=4)
        self.assertAlmostEqual(0.0 - math.log2(0.6895), 0.5364, places=4)   # the rounded-input value
        # The module follows the formula (L - 1), hence the final figures:
        r = mcv.estimate(self.S, 2)
        self.assertAlmostEqual(r["p_u"], 0.6895, places=4)
        self.assertAlmostEqual(r["min entropy"], 0.5363, places=4)


class TestFootnote11(unittest.TestCase):
    """
    Section 6.1 footnote 11 (PDF p. 48): a two-valued source with joint
    probabilities Pr(A,A)=0.104, Pr(A,B)=0.332, Pr(B,A)=0.239, Pr(B,B)=0.325,
    read as a sequence of single values.  "The min-entropy according to the
    MCV estimator is 0.712".  That is a population (L -> infinity) statement:
    Pr(X=B) = 0.239+0.325 = 0.564, Pr(Y=B) = 0.332+0.325 = 0.657, so the
    per-value frequency of B is (0.564+0.657)/2 = 0.6105 and -log2(0.6105) = 0.712.
    """

    def test_population_limit_and_finite_sample_conservatism(self):
        L = 10_000
        S = [1] * 6105 + [0] * 3895          # exactly p-hat = 0.6105 for the value 1
        r = mcv.estimate(S, 1)
        self.assertEqual(r["L"], L)
        self.assertEqual(r["Mode count"], 6105)
        self.assertEqual(r["p-hat"], 0.6105)
        self.assertAlmostEqual(0.0 - math.log2(r["p-hat"]), 0.712, places=3)
        # The finite-L confidence bound only ever lowers the estimate:
        self.assertLess(r["min entropy"], 0.712)
        # by hand: 0.6105*0.3895 = 0.23778975 ; /9999 = 2.378135e-5 ; sqrt = 0.004876613
        #          *2.576 = 0.012562155 ; p_u = 0.623062155
        #          ln(0.623062155) = -0.473107 ; /ln 2 -> -log2(p_u) = 0.68255
        self.assertAlmostEqual(r["p_u"], 0.6230622, places=6)
        self.assertAlmostEqual(r["min entropy"], 0.68255, places=4)


class TestDegenerateInputs(unittest.TestCase):

    def test_all_one_symbol(self):
        # p-hat = 1 ; p-hat(1-p-hat) = 0 ; sqrt(0/(L-1)) = 0 ; p_u = min(1, 1 + 0) = 1 ;
        # -log2(1) = 0.  The clamp does not bind (1 is not > 1).
        for L, bps, v in [(1000, 8, 5), (2, 1, 0), (2, 1, 1), (3, 3, 7)]:
            with self.subTest(L=L, bps=bps, v=v):
                r = mcv.estimate([v] * L, bps)
                self.assertEqual(r["Mode count"], L)
                self.assertEqual(r["mode value"], v)
                self.assertEqual(r["k observed"], 1)
                self.assertEqual(r["p-hat"], 1.0)
                self.assertEqual(r["p_u"], 1.0)
                self.assertEqual(r["min entropy"], 0.0)
                self.assertFalse(r["p_u clamped"])
                # +0.0, not -0.0 (so the JSON reads 0.0)
                self.assertEqual(math.copysign(1.0, r["min entropy"]), 1.0)
                self.assertNotIn("-0.0", json.dumps(r))

    def test_clamp_binds_one_deviant_in_a_thousand(self):
        # S = 999 zeros and one 1 (1-bit symbols), L = 1000.
        #   p-hat = 0.999
        #   p-hat(1-p-hat) = 0.999*0.001 = 0.000999
        #   /(L-1) = 0.000999/999 = 1.0e-6 ; sqrt = 1.0e-3 ; *2.576 = 0.002576
        #   p-hat + 0.002576 = 1.001576 > 1  ->  p_u = min(1, 1.001576) = 1
        #   min-entropy = -log2(1) = 0
        r = mcv.estimate([0] * 999 + [1], 1)
        self.assertEqual(r["Mode count"], 999)
        self.assertEqual(r["p-hat"], 0.999)
        self.assertTrue(r["p_u clamped"])
        self.assertAlmostEqual(r["p_u unclamped"], 1.001576, places=6)
        self.assertEqual(r["p_u"], 1.0)
        self.assertEqual(r["min entropy"], 0.0)

    def test_clamp_negative_control_ten_deviants(self):
        # Mutation of the case above: 990 zeros and ten 1s.  Now
        #   p-hat = 0.99 ; p-hat(1-p-hat) = 0.0099 ; /999 = 9.9099e-6 ; sqrt = 3.1480e-3
        #   *2.576 = 8.1093e-3 ; p_u = 0.9981093 < 1  -> the clamp does NOT bind
        #   min-entropy = -log2(0.9981093) = 0.002730
        r = mcv.estimate([0] * 990 + [1] * 10, 1)
        self.assertFalse(r["p_u clamped"])
        self.assertAlmostEqual(r["p_u"], 0.9981093, places=6)
        self.assertAlmostEqual(r["min entropy"], 0.002730, places=5)
        self.assertGreater(r["min entropy"], 0.0)

    def test_two_samples_fair_coin_clamps_to_zero(self):
        # S = (0, 1): p-hat = 0.5 ; sqrt(0.25/1) = 0.5 ; 2.576*0.5 = 1.288 ;
        # 0.5 + 1.288 = 1.788 > 1 -> p_u = 1 -> 0 bits.  Two samples prove nothing.
        r = mcv.estimate([0, 1], 1)
        self.assertEqual(r["p-hat"], 0.5)
        self.assertAlmostEqual(r["p_u unclamped"], 1.788, places=12)
        self.assertTrue(r["p_u clamped"])
        self.assertEqual(r["p_u"], 1.0)
        self.assertEqual(r["min entropy"], 0.0)

    def test_L_equals_one_gives_no_value(self):
        # L - 1 = 0: step 2 divides by zero (0/0).  The spec gives no value -> nan.
        r = mcv.estimate([7], 3)
        self.assertEqual(r["L"], 1)
        self.assertEqual(r["Mode count"], 1)
        self.assertEqual(r["p-hat"], 1.0)
        self.assertTrue(math.isnan(r["p_u"]))
        self.assertTrue(math.isnan(r["min entropy"]))
        self.assertTrue(math.isnan(r["min_entropy"]))

    def test_empty_input_gives_no_value(self):
        for empty in ([], np.zeros(0, dtype=np.uint8), b""):
            with self.subTest(kind=type(empty).__name__):
                r = mcv.estimate(empty, 8)
                self.assertEqual(r["L"], 0)
                self.assertEqual(r["Mode count"], 0)
                self.assertIsNone(r["mode value"])
                self.assertTrue(math.isnan(r["p-hat"]))
                self.assertTrue(math.isnan(r["p_u"]))
                self.assertTrue(math.isnan(r["min entropy"]))


class TestHandDerivedTwoBit(unittest.TestCase):

    def test_two_bit_eight_samples(self):
        # S = (3, 3, 0, 1, 3, 2, 0, 3), bits_per_symbol = 2, L = 8.
        # counts: 3 -> 4, 0 -> 2, 1 -> 1, 2 -> 1 ; k observed = 4
        #   p-hat = 4/8 = 0.5
        #   p-hat(1-p-hat)/(L-1) = 0.25/7 = 0.0357142857
        #   sqrt(0.0357142857)   = 0.1889822365   (= 1/sqrt(28))
        #   2.576 * 0.1889822365 = 0.4868182413
        #   p_u = 0.5 + 0.4868182413 = 0.9868182413
        #   -log2(0.9868182413): ln(1 - 0.0131817587) = -(0.0131817587 + 0.0000868794
        #        + 0.0000007635 + ...) = -0.0132694 ; /ln 2 = 0.019144
        r = mcv.estimate([3, 3, 0, 1, 3, 2, 0, 3], 2)
        self.assertEqual(r["L"], 8)
        self.assertEqual(r["k observed"], 4)
        self.assertEqual(r["mode value"], 3)
        self.assertEqual(r["Mode count"], 4)
        self.assertEqual(r["p-hat"], 0.5)
        self.assertAlmostEqual(r["p_u"], 0.9868182413, places=9)
        self.assertAlmostEqual(r["min entropy"], 0.019144, places=5)
        self.assertFalse(r["p_u clamped"])

    def test_tie_reports_smallest_value_but_same_estimate(self):
        # Ties do not change p-hat; 'mode value' is the smallest tied value (a
        # reporting convention, not a spec quantity).
        r = mcv.estimate([2, 0, 2, 0], 2)
        self.assertEqual(r["Mode count"], 2)
        self.assertEqual(r["mode value"], 0)
        self.assertEqual(r["p-hat"], 0.5)


class TestConstantVariants(unittest.TestCase):

    def test_exact_quantile_constant(self):
        # Step 2: "2.576 corresponds to the Z_(1-0.005) value".  The textbook value of
        # Phi^-1(0.995) is 2.5758293035489...; it rounds to 2.576 at 3 decimals.
        self.assertAlmostEqual(mcv.Z_EXACT_QUANTILE, 2.5758293035489, places=12)
        self.assertEqual(round(mcv.Z_EXACT_QUANTILE, 3), 2.576)
        self.assertEqual(mcv.Z_LITERAL, 2.576)
        self.assertGreater(mcv.Z_LITERAL, mcv.Z_EXACT_QUANTILE)

    def test_exact_quantile_is_the_permissive_direction(self):
        # A smaller z gives a smaller half-width, a smaller p_u and a LARGER estimate.
        rng = random.Random(90)
        S = [rng.randrange(256) for _ in range(5000)]
        lit = mcv.estimate(S, 8)
        exa = mcv.estimate(S, 8, variant="exact_quantile")
        self.assertEqual(lit["Mode count"], exa["Mode count"])
        self.assertEqual(lit["p-hat"], exa["p-hat"])
        self.assertLess(exa["p_u"], lit["p_u"])
        self.assertGreater(exa["min entropy"], lit["min entropy"])
        self.assertLess(exa["min entropy"] - lit["min entropy"], 1e-3)
        self.assertEqual(exa["variant"], "exact_quantile")
        self.assertEqual(exa["z"], mcv.Z_EXACT_QUANTILE)

    def test_z_override(self):
        S = [0, 1, 1, 2, 0, 1, 2, 2, 0, 1, 0, 1, 1, 0, 2, 2, 1, 0, 2, 1]
        r0 = mcv.estimate(S, 2, z=0.0)          # no confidence adjustment at all
        self.assertEqual(r0["variant"], "custom")
        self.assertEqual(r0["p_u"], r0["p-hat"])
        self.assertAlmostEqual(r0["min entropy"], 0.0 - math.log2(0.4), places=15)
        r1 = mcv.estimate(S, 2, z=2.576)
        self.assertEqual(r1["p_u"], mcv.estimate(S, 2)["p_u"])


class TestBitstringTrack(unittest.TestCase):

    def test_to_bitstring_msb_and_lsb(self):
        self.assertEqual(mcv.to_bitstring([0b101, 0b011], 3).tolist(), [1, 0, 1, 0, 1, 1])
        self.assertEqual(mcv.to_bitstring([0b101, 0b011], 3, "lsb").tolist(), [1, 0, 1, 1, 1, 0])
        self.assertEqual(mcv.to_bitstring([0xA5], 8).tolist(), [1, 0, 1, 0, 0, 1, 0, 1])
        self.assertEqual(mcv.to_bitstring([0xA5], 8, "lsb").tolist(), [1, 0, 1, 0, 0, 1, 0, 1][::-1])
        self.assertEqual(mcv.to_bitstring([1, 0, 1], 1).tolist(), [1, 0, 1])   # width 1: identity
        self.assertEqual(mcv.to_bitstring(bytes([0x0F, 0xF0]), 8).tolist(),
                         [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0])
        with self.assertRaises(ValueError):
            mcv.to_bitstring([1], 2, "middle-endian")

    def test_bitstring_estimate(self):
        # 10 bytes of 0xFF -> 80 one-bits: p-hat = 1, 0 bits.
        r = mcv.estimate([0xFF] * 10, 8, track="bitstring")
        self.assertEqual(r["track"], "bitstring")
        self.assertEqual(r["L"], 80)
        self.assertEqual(r["Mode count"], 80)
        self.assertEqual(r["p-hat"], 1.0)
        self.assertEqual(r["min entropy"], 0.0)
        # 10 bytes of 0x0F -> 40 zeros, 40 ones: p-hat = 0.5 (tie -> mode value 0).
        r = mcv.estimate([0x0F] * 10, 8, track="bitstring")
        self.assertEqual(r["L"], 80)
        self.assertEqual(r["Mode count"], 40)
        self.assertEqual(r["mode value"], 0)
        self.assertEqual(r["p-hat"], 0.5)
        # by hand: 2.576*sqrt(0.25/79) = 2.576*0.0562544 = 0.1449113 ; p_u = 0.6449113 ;
        #          -log2(0.6449113) = 0.6328
        self.assertAlmostEqual(r["p_u"], 0.6449113, places=6)
        self.assertAlmostEqual(r["min entropy"], 0.6328, places=4)
        # Width-1 data: the bitstring track equals the literal track exactly.
        S1 = [0, 1, 1, 0, 1, 1, 1, 0]
        a, b = mcv.estimate(S1, 1), mcv.estimate(S1, 1, track="bitstring")
        for k in ("Mode count", "p-hat", "p_u", "min entropy"):
            self.assertEqual(a[k], b[k])

    def test_bitstring_equals_literal_on_expanded_bits(self):
        rng = random.Random(7)
        S = [rng.randrange(16) for _ in range(3000)]
        via_track = mcv.estimate(S, 4, track="bitstring")
        via_expand = mcv.estimate(mcv.to_bitstring(S, 4), 1)
        for k in ("L", "Mode count", "p-hat", "p_u", "min entropy"):
            self.assertEqual(via_track[k], via_expand[k])

    def test_bitstring_limit(self):
        # Section 3.1.3: "The bits after the first 1 000 000 bits may be ignored."
        r = mcv.estimate([0xF0] * 10, 8, track="bitstring", bitstring_limit=5)
        self.assertEqual(r["L"], 5)                 # 1,1,1,1,0
        self.assertEqual(r["Mode count"], 4)
        self.assertEqual(r["bitstring_limit"], 5)
        r = mcv.estimate([0xF0] * 10, 8, track="bitstring")
        self.assertEqual(r["L"], 80)
        self.assertIsNone(r["bitstring_limit"])

    def test_lsb_first_option_changes_order_not_counts(self):
        # Bit order within a symbol permutes the bitstring but cannot change the
        # count of ones, so the MCV estimate is identical under both conventions.
        rng = random.Random(11)
        S = [rng.randrange(256) for _ in range(2000)]
        a = mcv.estimate(S, 8, track="bitstring", bit_order="msb")
        b = mcv.estimate(S, 8, track="bitstring", bit_order="lsb")
        self.assertEqual(a["Mode count"], b["Mode count"])
        self.assertEqual(a["min entropy"], b["min entropy"])
        self.assertFalse(np.array_equal(mcv.to_bitstring(S, 8, "msb"),
                                        mcv.to_bitstring(S, 8, "lsb")))


class TestValidation(unittest.TestCase):

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            mcv.estimate([4], 2)
        with self.assertRaises(ValueError):
            mcv.estimate([0, 1, 2], 1)
        with self.assertRaises(ValueError):
            mcv.estimate([-1, 0], 2)
        with self.assertRaises(ValueError):
            mcv.estimate([256], 8)
        mcv.estimate([255], 8)                      # in range: fine
        mcv.estimate([3], 2)

    def test_non_integer_rejected(self):
        with self.assertRaises(ValueError):
            mcv.estimate([0.5, 1.0], 2)
        with self.assertRaises(ValueError):
            mcv.estimate(np.array([[0, 1], [1, 0]]), 1)   # not 1-D

    def test_bad_options_rejected(self):
        S = [0, 1]
        with self.assertRaises(ValueError):
            mcv.estimate(S, 0)
        with self.assertRaises(ValueError):
            mcv.estimate(S, 1, variant="rounded_up")
        with self.assertRaises(ValueError):
            mcv.estimate(S, 1, track="columns")
        with self.assertRaises(TypeError):
            mcv.estimate(S, 1, alpha=0.01)

    def test_validate_false_skips_the_range_check(self):
        # The caller takes responsibility; the arithmetic is unchanged.
        r = mcv.estimate([5, 5, 6], 2, validate=False)
        self.assertEqual(r["Mode count"], 2)

    def test_bools_and_bytes_accepted(self):
        r = mcv.estimate(np.array([True, False, True]), 1)
        self.assertEqual(r["Mode count"], 2)
        r = mcv.estimate(bytes([1, 2, 2, 3]), 8)
        self.assertEqual(r["Mode count"], 2)
        self.assertEqual(r["mode value"], 2)


class TestProperties(unittest.TestCase):

    def test_matches_plain_python_transcription_bit_for_bit(self):
        rng = random.Random(2026_11_07)
        for trial in range(40):
            bps = rng.choice([1, 1, 2, 3, 4, 8])
            L = rng.randrange(2, 3000)
            # vary the skew so the mode is sometimes dominant, sometimes not
            skew = rng.choice([0.0, 0.3, 0.7, 0.95])
            S = [0 if rng.random() < skew else rng.randrange(1 << bps) for _ in range(L)]
            with self.subTest(trial=trial, bps=bps, L=L, skew=skew):
                r = mcv.estimate(S, bps)
                mc, ph, pu, me = plain_python_mcv(S)
                self.assertEqual(r["Mode count"], mc)
                self.assertEqual(r["p-hat"], ph)
                self.assertEqual(r["p_u"], pu)
                self.assertEqual(r["min entropy"], me)

    def test_estimate_never_exceeds_the_symbol_width(self):
        # p-hat >= 1/k (the most common value is at least as frequent as the average),
        # p_u >= p-hat, so -log2(p_u) <= log2(k) <= bits_per_symbol.  No clamp needed.
        rng = random.Random(3)
        for bps in (1, 2, 4, 8):
            for _ in range(10):
                L = rng.randrange(2, 2000)
                S = [rng.randrange(1 << bps) for _ in range(L)]
                r = mcv.estimate(S, bps)
                self.assertLessEqual(r["min entropy"], bps + 1e-12)
                self.assertLessEqual(r["min entropy"], math.log2(r["k observed"]) + 1e-12)
                self.assertGreaterEqual(r["min entropy"], 0.0)
                self.assertLessEqual(r["p_u"], 1.0)
                self.assertGreaterEqual(r["p_u"], r["p-hat"])

    def test_deterministic(self):
        S = np.array([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5] * 50, dtype=np.uint8)
        a = mcv.estimate(S, 4)
        b = mcv.estimate(S, 4)
        self.assertEqual(a, b)

    def test_input_types_agree(self):
        vals = [5, 5, 1, 0, 5, 7, 2, 2]
        a = mcv.estimate(vals, 3)
        b = mcv.estimate(tuple(vals), 3)
        c = mcv.estimate(np.array(vals, dtype=np.int64), 3)
        d = mcv.estimate(bytes(vals), 3)
        for k in ("Mode count", "p-hat", "p_u", "min entropy"):
            self.assertEqual(a[k], b[k])
            self.assertEqual(a[k], c[k])
            self.assertEqual(a[k], d[k])


class TestCommandLine(unittest.TestCase):

    def _run(self, *args):
        proc = subprocess.run(
            [sys.executable, str(MCV_PATH), *args],
            capture_output=True, text=True, timeout=120,
        )
        return proc

    def test_literal_and_bitstring_match_the_api(self):
        rng = random.Random(1234)
        raw = bytes(rng.randrange(256) for _ in range(5000))
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "rand8.bin")
            with open(path, "wb") as fh:
                fh.write(raw)

            p = self._run(path, "8", "--literal")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            ref = mcv.estimate(raw, 8)
            for k in ("L", "Mode count", "p-hat", "p_u", "min entropy", "min_entropy"):
                self.assertEqual(out[k], ref[k], k)
            self.assertEqual(out["out_of_width_bytes_masked"], 0)
            self.assertEqual(out["input_bytes"], 5000)
            self.assertEqual(len(out["input_sha256"]), 64)

            p = self._run(path, "8", "--bitstring")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            ref = mcv.estimate(raw, 8, track="bitstring")
            self.assertEqual(out["L"], 40000)
            for k in ("Mode count", "p-hat", "p_u", "min entropy"):
                self.assertEqual(out[k], ref[k], k)

            p = self._run(path, "8", "--bitstring", "--variant", "exact_quantile")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            ref = mcv.estimate(raw, 8, track="bitstring", variant="exact_quantile")
            self.assertEqual(out["p_u"], ref["p_u"])
            self.assertEqual(out["z"], mcv.Z_EXACT_QUANTILE)

            # Default track is literal.
            p = self._run(path, "8")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["track"], "literal")

    def test_low_bits_are_the_symbol(self):
        # bytes with high bits set, declared width 4: the symbol is byte & 0xF.
        raw = bytes([0xA3, 0x53, 0x03, 0xF3, 0x1C])      # low nibbles: 3,3,3,3,C
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "nibbles.bin")
            with open(path, "wb") as fh:
                fh.write(raw)
            p = self._run(path, "4")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["Mode count"], 4)
            self.assertEqual(out["mode value"], 3)
            self.assertEqual(out["out_of_width_bytes_masked"], 4)   # 0x03 fits; the other four do not
            self.assertIn("warning", p.stderr)
            # width 1 on the same bytes: symbols are the low bits 1,1,1,1,0
            p = self._run(path, "1")
            out = json.loads(p.stdout)
            self.assertEqual(out["Mode count"], 4)
            self.assertEqual(out["mode value"], 1)
            # --bitstring at width 4 expands only the low nibble: 5*4 = 20 bits
            p = self._run(path, "4", "--bitstring")
            out = json.loads(p.stdout)
            self.assertEqual(out["L"], 20)

    def test_usage_errors(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "x.bin")
            with open(path, "wb") as fh:
                fh.write(bytes(range(16)))
            for args in ([path], [path, "9"], [path, "0"], [path, "eight"],
                         [path, "8", "--bogus"], [path, "8", "--variant"]):
                with self.subTest(args=args):
                    p = self._run(*args)
                    self.assertNotEqual(p.returncode, 0)
                    self.assertEqual(p.stdout, "")

    def test_nan_round_trips_through_json(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "one.bin")
            with open(path, "wb") as fh:
                fh.write(b"\x07")
            p = self._run(path, "3")
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["L"], 1)
            self.assertTrue(math.isnan(out["p_u"]))
            self.assertTrue(math.isnan(out["min entropy"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
