"""Unit tests for py90b.compression -- SP 800-90B section 6.3.4, Compression Estimate.

Every expected value here is either quoted from the standard (the worked example,
PDF p. 55) or derived BY HAND in the comment above the test, from the spec's
printed formulas.  Nothing is taken from the C++ tool.

Run:  <venv>/bin/python -m unittest py90b.tests.test_compression -v
from  docs/audits/2026-11-07-aggressive-audit/reference/
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REFERENCE_DIR = os.path.dirname(os.path.dirname(HERE))
if REFERENCE_DIR not in sys.path:
    sys.path.insert(0, REFERENCE_DIR)

from py90b import compression as cmp  # noqa: E402

# The spec's worked example input (SP 800-90B 6.3.4, PDF p. 55):
# "suppose that d = 4 (instead of 1000), L = 48 and S = (1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0,
#  1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0,
#  1, 1, 1, 0, 0, 0, 1, 1)"
SPEC_S = [1, 0, 0, 0, 1, 1,  1, 0, 0, 1, 0, 1,  0, 1, 0, 1, 1, 1,  0, 0, 1, 1, 0, 0,
          0, 1, 1, 1, 0, 0,  1, 0, 1, 0, 1, 0,  1, 1, 1, 0, 1, 1,  1, 0, 0, 0, 1, 1]


def blocks_to_bits(block_values, b=6):
    """Helper: integers -> their b-bit MSB-first expansion, concatenated."""
    out = []
    for x in block_values:
        out.extend(int(ch) for ch in format(int(x), f"0{b}b"))
    return out


class TestSpecWorkedExample(unittest.TestCase):
    """SP 800-90B 6.3.4 worked example (PDF p. 55), d = 4, L = 48."""

    def test_step1_blocks(self):
        # "After step 1, the new blocked sequence is S' = (100011, 100101, 010111,
        #  001100, 011100, 101010, 111011, 100011)."
        blocks = cmp.blocks_from_bits(np.array(SPEC_S, dtype=np.uint8))
        self.assertEqual([format(x, "06b") for x in blocks.tolist()],
                         ["100011", "100101", "010111", "001100",
                          "011100", "101010", "111011", "100011"])

    def test_step3_dictionary_and_step4_D(self):
        # "dict[s'_i]: 100011 -> 1, 100101 -> 2, 010111 -> 3, 001100 -> 4"
        # "After Step 4, the resulting D1 = 5, D2 = 6, D3 = 7, and D4 = 7."
        blocks = cmp.blocks_from_bits(np.array(SPEC_S, dtype=np.uint8))
        D, dct = cmp.compression_distances(blocks, d=4)
        nonzero = {format(i, "06b"): int(x) for i, x in enumerate(dct) if x}
        self.assertEqual(nonzero, {"100011": 1, "100101": 2, "010111": 3, "001100": 4})
        self.assertEqual(D.tolist(), [5, 6, 7, 7])

    def test_steps5_to_8_match_the_printed_figures(self):
        # "X-bar = 2.6304 and sigma-hat = 0.9074, and the value for step 6 is
        #  X-bar' = 1.4617. The value of p that solves the equation in step 7 is
        #  0.5715, and the min-entropy estimate is 0.1345."
        r = cmp.estimate(SPEC_S, 1, d=4)
        self.assertEqual(r["v"], 4)
        self.assertAlmostEqual(r["X-bar"], 2.6304, places=4)
        self.assertAlmostEqual(r["sigma-hat"], 0.9074, places=4)
        self.assertAlmostEqual(r["X-bar'"], 1.4617, places=4)
        self.assertTrue(r["found_p"])
        self.assertAlmostEqual(r["p"], 0.5715, places=4)
        self.assertAlmostEqual(r["min_entropy"], 0.1345, places=4)
        # and the printed closing step: min-entropy = -log2(p)/b
        self.assertAlmostEqual(r["min_entropy"], -math.log2(r["p"]) / 6, places=12)
        # the solution actually solves step 7's equation
        self.assertLess(abs(r["residual"]), 1e-9)

    def test_step5_by_hand(self):
        # By hand from D = (5, 6, 7, 7), x_i = log2 D_i:
        #   sum x   = log2 5 + log2 6 + 2 log2 7 = 2.321928 + 2.584963 + 5.614710 = 10.521601
        #   X-bar   = 10.521601 / 4 = 2.630400
        #   sum x^2 = 5.391350 + 6.682031 + 2 * 7.881240 = 27.835861
        #   printed radicand = 27.835861 / 3 - 2.630400^2 = 9.278620 - 6.919004 = 2.359616
        #   sigma-hat = 0.5907 * sqrt(2.359616) = 0.5907 * 1.536104 = 0.907377
        #   X-bar' = 2.630400 - 2.576 * 0.907377 / sqrt(4) = 2.630400 - 1.168702 = 1.461698
        x = [math.log2(5), math.log2(6), math.log2(7), math.log2(7)]
        x_bar = sum(x) / 4
        radicand = sum(t * t for t in x) / 3 - x_bar ** 2
        sigma = 0.5907 * math.sqrt(radicand)
        r = cmp.estimate(SPEC_S, 1, d=4)
        self.assertAlmostEqual(r["X-bar"], x_bar, places=12)
        self.assertAlmostEqual(r["radicand"], radicand, places=12)
        self.assertAlmostEqual(r["sigma-hat"], sigma, places=12)
        self.assertAlmostEqual(r["X-bar'"], x_bar - 2.576 * sigma / 2.0, places=12)

    def test_the_literal_upper_limit_L_does_NOT_reproduce_the_example(self):
        # SPEC AMBIGUITY, recorded, not fudged: the printed G(z) sums t from d+1 to L
        # (the number of BITS, 48 here).  Under that literal reading p comes out near
        # 0.976 and the min-entropy near 0.006, not the printed 0.5715 / 0.1345.
        # Summing t over the block indices d+1 .. floor(L/b) (= d + v = 8) reproduces
        # the example, so that is the default ('blocks'); 'L' stays exposed.
        r_L = cmp.estimate(SPEC_S, 1, d=4, t_upper="L")
        self.assertEqual(r_L["t_max"], 48)
        self.assertGreater(abs(r_L["p"] - 0.5715), 0.1)
        r_blocks = cmp.estimate(SPEC_S, 1, d=4, t_upper="blocks")
        self.assertEqual(r_blocks["t_max"], 8)
        self.assertAlmostEqual(r_blocks["p"], 0.5715, places=4)

    def test_the_textbook_unbiased_sigma_does_NOT_reproduce_the_example(self):
        # The printed radicand  sum(x^2)/(v-1) - X-bar^2  is not the unbiased sample
        # variance; the textbook form gives sigma-hat = 0.5907*sqrt((27.835861-4*6.919004)/3)
        # = 0.5907 * sqrt(0.053282) = 0.1364, not the printed 0.9074.  The spec's own
        # example therefore uses the printed form; 'unbiased' is exposed for comparison.
        r = cmp.estimate(SPEC_S, 1, d=4, sigma_variant="unbiased")
        self.assertAlmostEqual(r["sigma-hat"], 0.1364, places=3)
        self.assertGreater(abs(r["sigma-hat"] - 0.9074), 0.5)

    def test_trailing_bits_are_discarded(self):
        # step 1: "If L is not a multiple of b, discard the extra data."
        r48 = cmp.estimate(SPEC_S, 1, d=4)
        r49 = cmp.estimate(SPEC_S + [1], 1, d=4)
        self.assertEqual(r49["L"], 49)
        self.assertEqual(r49["n_blocks"], 8)
        self.assertEqual(r49["min_entropy"], r48["min_entropy"])


class TestHandDerivedInputs(unittest.TestCase):

    def test_degenerate_all_one_symbol_gives_zero(self):
        # All-zero bits, d = 1000, 2000 blocks (12000 bits), v = 1000.
        # Step 3: dict[000000] = 1000.  Step 4, i = 1001: D_1 = 1001 - 1000 = 1, then
        # dict[0] = 1001; i = 1002: D_2 = 1; ... every D_i = 1, so every log2 D_i = 0.
        # Step 5: X-bar = 0, printed radicand = 0/999 - 0 = 0, sigma-hat = 0.
        # Step 6: X-bar' = 0.  Step 7: rhs(1) = G(1) + 63 G(0) = 0 exactly, so p = 1.
        # Step 8: min-entropy = -log2(1)/6 = 0.
        r = cmp.estimate([0] * 12000, 1)
        self.assertEqual(r["v"], 1000)
        self.assertEqual(r["X-bar"], 0.0)
        self.assertEqual(r["sigma-hat"], 0.0)
        self.assertEqual(r["X-bar'"], 0.0)
        self.assertTrue(r["found_p"])
        self.assertEqual(r["p"], 1.0)
        self.assertEqual(r["min_entropy"], 0.0)
        self.assertEqual(r["search_status"], "found_at_upper_bound")

    def test_four_symbols_repeated_once(self):
        # d = 4; S' = (A, B, C, D, A, B, C, D) with A..D = 000001, 000010, 000011, 000100.
        # Step 3: dict[A]=1, dict[B]=2, dict[C]=3, dict[D]=4.
        # Step 4: i=5 A -> 5-1 = 4; i=6 B -> 6-2 = 4; i=7 C -> 4; i=8 D -> 4.  x_i = 2.
        # Step 5: X-bar = 2; printed radicand = 4*4/3 - 4 = 4/3; sigma-hat = 0.5907*sqrt(4/3)
        #         = 0.5907 * 1.1547005 = 0.6820816.
        # Step 6: X-bar' = 2 - 2.576 * 0.6820816 / 2 = 2 - 0.8785211 = 1.1214789.
        # Step 7/8: p solves rhs(p) = 1.1214789 (checked by residual); 0 < H < 1.
        bits = blocks_to_bits([1, 2, 3, 4, 1, 2, 3, 4])
        r = cmp.estimate(bits, 1, d=4)
        self.assertEqual(r["v"], 4)
        self.assertAlmostEqual(r["X-bar"], 2.0, places=12)
        self.assertAlmostEqual(r["sigma-hat"], 0.5907 * math.sqrt(4.0 / 3.0), places=12)
        self.assertAlmostEqual(r["X-bar'"], 2.0 - 2.576 * 0.5907 * math.sqrt(4.0 / 3.0) / 2.0, places=12)
        self.assertTrue(r["found_p"])
        self.assertLess(abs(r["residual"]), 1e-9)
        self.assertAlmostEqual(r["min_entropy"], -math.log2(r["p"]) / 6, places=12)
        self.assertTrue(0.0 < r["min_entropy"] < 1.0)

    def test_period_64_cycle_has_no_solution_and_step8_gives_one(self):
        # Blocks cycle through all 64 values: block i (1-based) = (i-1) mod 64; d = 1000,
        # 2000 blocks, v = 1000.  For every test index i the same value last occurred at
        # i - 64, so every D_i = 64 and x_i = 6.
        # Step 5: X-bar = 6; printed radicand = 36*1000/999 - 36 = 36/999;
        #         sigma-hat = 0.5907 * 6 / sqrt(999) = 0.1121337.
        # Step 6: X-bar' = 6 - 2.576 * 0.1121337 / sqrt(1000) = 6 - 0.0091341 = 5.9908659.
        # Step 7: the uniform value rhs(2^-6) is about 5.2177 < X-bar', so no p in
        #         [2^-6, 1] solves the equation.  Step 8: "If the search does not yield
        #         a solution, then the min-entropy estimation is: min-entropy = 1."
        # (A zero-entropy periodic sequence credited with 1 bit/bit: this is the
        #  standard's own step 8, recorded in the fork as F06, NOT-A-BUG.)
        bits = blocks_to_bits([(i - 1) % 64 for i in range(1, 2001)])
        r = cmp.estimate(bits, 1)
        self.assertEqual(r["v"], 1000)
        self.assertAlmostEqual(r["X-bar"], 6.0, places=12)
        self.assertAlmostEqual(r["sigma-hat"], 0.5907 * 6.0 / math.sqrt(999.0), places=12)
        self.assertAlmostEqual(r["X-bar'"], 6.0 - 2.576 * (0.5907 * 6.0 / math.sqrt(999.0)) / math.sqrt(1000.0), places=12)
        self.assertGreater(r["X-bar'"], r["rhs_at_lower_bound"])
        self.assertFalse(r["found_p"])
        self.assertTrue(math.isnan(r["p"]))
        self.assertEqual(r["search_status"], "no_solution_above_uniform")
        self.assertEqual(r["min_entropy"], 1.0)
        self.assertEqual(r["min_entropy_step8_literal"], 1.0)
        self.assertEqual(r["min_entropy_conservative"], 1.0)

    def test_near_constant_stream_drives_X_bar_prime_below_zero(self):
        # All-zero blocks except block 1500 = 000001; d = 1000, 2000 blocks, v = 1000.
        # Step 4: i = 1001..1499: D = 1 (the zero block was seen one step before);
        #         i = 1500: value 1 never seen -> D_500 = 1500;
        #         i = 1501: zero last seen at 1499 -> D_501 = 2;  i >= 1502: D = 1.
        # So x = (0, ..., 0, log2 1500, 1, 0, ..., 0):
        #   sum x = log2(1500) + 1 = 11.5507468;  X-bar = 0.0115507
        #   sum x^2 = log2(1500)^2 + 1 = 112.318259
        #   printed radicand = 112.318259/999 - 0.0115507^2 = 0.1124307 - 0.0001334 = 0.1122973
        #   sigma-hat = 0.5907 * sqrt(0.1122973) = 0.5907 * 0.3351079 = 0.1979482
        # Step 6: X-bar' = 0.0115507 - 2.576 * 0.1979482 / sqrt(1000) = 0.0115507 - 0.0161254
        #                = -0.0045747  < 0 = rhs(1).
        # Step 7: no p in [2^-6, 1] solves the equation (rhs >= 0 there).
        # Step 8 read literally: "min-entropy = 1".  The conservative boundary reading
        # (p = 1) gives 0.  Both are reported; the default follows the literal text.
        # NOTE for the differential driver: this is reachable at ANY v (the deficit
        # scales as (log2 i + 1 - 2.576*c*sqrt(log2(i)^2 + 1)) / v, negative whenever
        # 2.576*0.5907 = 1.5216 > 1), so it is a live overstatement path if an
        # implementation follows step 8 literally.
        blocks = [0] * 2000
        blocks[1500 - 1] = 1
        bits = blocks_to_bits(blocks)
        r = cmp.estimate(bits, 1)
        lg = math.log2(1500)
        sum_x, sum_x2 = lg + 1.0, lg * lg + 1.0
        x_bar = sum_x / 1000
        radicand = sum_x2 / 999 - x_bar ** 2
        sigma = 0.5907 * math.sqrt(radicand)
        xp = x_bar - 2.576 * sigma / math.sqrt(1000)
        self.assertAlmostEqual(r["X-bar"], x_bar, places=12)
        self.assertAlmostEqual(r["sigma-hat"], sigma, places=12)
        self.assertAlmostEqual(r["X-bar'"], xp, places=12)
        self.assertLess(r["X-bar'"], 0.0)
        self.assertFalse(r["found_p"])
        self.assertEqual(r["search_status"], "no_solution_below_zero")
        self.assertEqual(r["min_entropy_step8_literal"], 1.0)
        self.assertEqual(r["min_entropy_conservative"], 0.0)
        self.assertEqual(r["min_entropy"], 1.0)                       # default: literal step 8
        r2 = cmp.estimate(bits, 1, no_solution_low="conservative")
        self.assertEqual(r2["min_entropy"], 0.0)

    def test_v_equal_one_and_v_below_one_give_no_value(self):
        # d = 4 with 5 blocks: v = 1, sigma-hat divides by v-1 = 0 -> spec gives no value.
        r1 = cmp.estimate(blocks_to_bits([1, 2, 3, 4, 5]), 1, d=4)
        self.assertEqual(r1["v"], 1)
        self.assertAlmostEqual(r1["X-bar"], math.log2(5), places=12)   # D_1 = 5 (never seen)
        self.assertTrue(math.isnan(r1["sigma-hat"]))
        self.assertTrue(math.isnan(r1["X-bar'"]))
        self.assertTrue(math.isnan(r1["min_entropy"]))
        self.assertEqual(r1["search_status"], "undefined")
        # d = 4 with 4 blocks: v = 0, no test data at all.
        r0 = cmp.estimate(blocks_to_bits([1, 2, 3, 4]), 1, d=4)
        self.assertEqual(r0["v"], 0)
        self.assertTrue(math.isnan(r0["min_entropy"]))
        # fewer blocks than d
        rneg = cmp.estimate(blocks_to_bits([1, 2]), 1, d=4)
        self.assertEqual(rneg["v"], -2)
        self.assertTrue(math.isnan(rneg["min_entropy"]))


class TestG(unittest.TestCase):

    def test_vectorised_G_matches_the_printed_double_loop(self):
        for z in (2 ** -6, 0.01, 0.1, 0.5715, 0.9, 0.999, (1 - 0.5715) / 63):
            for (v, d, t_max) in ((4, 4, None), (4, 4, 48), (10, 3, None), (1, 1, None), (7, 0, None)):
                a, b = cmp.G(z, v, d, t_max), cmp.G_literal(z, v, d, t_max)
                self.assertLess(abs(a - b), 1e-13 * max(1.0, abs(b)), msg=f"z={z} v={v} d={d} t_max={t_max}")

    def test_G_terms_match_inner_sums_term_by_term(self):
        z, v, d = 0.3, 5, 3
        terms = cmp.G_terms(z, v, d)
        self.assertEqual(terms.size, v)
        for k, t in enumerate(range(d + 1, d + v + 1)):
            inner = sum(math.log2(u) * cmp.F(z, t, u) for u in range(1, t + 1))
            self.assertAlmostEqual(float(terms[k]), inner, places=14)

    def test_F_as_printed(self):
        z = 0.25
        self.assertEqual(cmp.F(z, 5, 1), z * z)                  # u < t: z^2 (1-z)^0
        self.assertAlmostEqual(cmp.F(z, 5, 3), z * z * 0.75 ** 2, places=15)
        self.assertAlmostEqual(cmp.F(z, 5, 5), z * 0.75 ** 4, places=15)   # u = t
        with self.assertRaises(ValueError):
            cmp.F(z, 5, 6)

    def test_endpoints(self):
        # G(0): every F is 0.  G(1): F(1,t,u) = 0 except u = 1 where log2(1) = 0.
        self.assertEqual(cmp.G(0.0, 4, 4), 0.0)
        self.assertEqual(cmp.G(1.0, 4, 4), 0.0)
        self.assertEqual(cmp.G_literal(1.0, 4, 4), 0.0)
        self.assertEqual(cmp.rhs(1.0, 1000, 1000), 0.0)

    def test_rhs_is_decreasing_in_p(self):
        ps = np.linspace(2 ** -6, 1.0, 41)
        fs = [cmp.rhs(float(p), 500, 1000) for p in ps]
        self.assertTrue(all(fs[i] > fs[i + 1] for i in range(len(fs) - 1)))

    def test_uniform_value_matches_maurer_L6_expectation(self):
        # Sanity check against the literature, not the spec: Maurer (1992) tabulates
        # the expected per-block statistic for L = 6 as 5.2177052.  At p = q = 2^-6
        # the right-hand side is the expected log2-distance under the uniform
        # distribution, so it should reproduce that figure once t is large.
        self.assertAlmostEqual(cmp.rhs(2 ** -6, 1000, 1000), 5.2177052, places=6)


class TestInputHandlingAndOptions(unittest.TestCase):

    def test_bitstring_expansion_is_msb_first(self):
        bits = cmp.to_bitstring([0b10001110, 0b00000001], 8)
        self.assertEqual(bits.tolist(), [1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(cmp.blocks_from_bits(bits).tolist(), [0b100011, 0b100000])
        self.assertEqual(cmp.to_bitstring([1, 0, 1], 1).tolist(), [1, 0, 1])
        self.assertEqual(cmp.to_bitstring([5], 3).tolist(), [1, 0, 1])

    def test_bitstring_mode_on_8bit_symbols_equals_the_bits_run_directly(self):
        rng = np.random.default_rng(90)
        sym = rng.integers(0, 256, size=1600, dtype=np.uint8)     # 12800 bits, v = 1133
        r_sym = cmp.estimate(sym, 8)
        r_bits = cmp.estimate(cmp.to_bitstring(sym, 8), 1)
        self.assertEqual(r_sym["min_entropy"], r_bits["min_entropy"])
        self.assertEqual(r_sym["X-bar"], r_bits["X-bar"])

    def test_literal_mode_on_non_binary_symbols_gives_no_value(self):
        # "This entropy estimation method is only applied to binary inputs."
        r = cmp.estimate([3, 1, 2, 0] * 2000, 2, mode="literal")
        self.assertTrue(math.isnan(r["min_entropy"]))
        self.assertIn("binary", r["note"])
        # literal on genuine binary symbols is the same as bitstring
        self.assertEqual(cmp.estimate(SPEC_S, 1, d=4, mode="literal")["min_entropy"],
                         cmp.estimate(SPEC_S, 1, d=4, mode="bitstring")["min_entropy"])

    def test_out_of_alphabet_symbol_is_refused(self):
        with self.assertRaises(ValueError):
            cmp.estimate([0, 1, 2], 1)
        with self.assertRaises(ValueError):
            cmp.estimate([0, -1], 1)

    def test_unknown_option_is_refused(self):
        with self.assertRaises(TypeError):
            cmp.estimate(SPEC_S, 1, d=4, bogus=1)

    def test_exact_quantile_option(self):
        self.assertAlmostEqual(cmp.exact_z_0995(), 2.5758293035489, places=12)
        r_printed = cmp.estimate(SPEC_S, 1, d=4)
        r_exact = cmp.estimate(SPEC_S, 1, d=4, z="exact")
        self.assertEqual(r_printed["z"], 2.576)
        self.assertAlmostEqual(r_exact["z"], 2.5758293035489, places=12)
        # the exact quantile is smaller, so X-bar' is larger and p smaller: more entropy
        self.assertGreater(r_exact["X-bar'"], r_printed["X-bar'"])
        self.assertGreater(r_exact["min_entropy"], r_printed["min_entropy"])

    def test_cli_prints_json_with_the_example_figures(self):
        py = sys.executable
        module = os.path.join(REFERENCE_DIR, "py90b", "compression.py")
        with tempfile.TemporaryDirectory() as tmp:
            raw = os.path.join(tmp, "spec_example_1bit.bin")
            with open(raw, "wb") as fh:
                fh.write(bytes(SPEC_S))                      # one symbol per byte
            out = subprocess.run([py, module, raw, "1", "--literal", "--d=4"],
                                 capture_output=True, text=True, check=True)
            res = json.loads(out.stdout)
            self.assertAlmostEqual(res["p"], 0.5715, places=4)
            self.assertAlmostEqual(res["min_entropy"], 0.1345, places=4)
            self.assertEqual(res["mode"], "literal")
            # 8-bit file, bitstring view (the default), low bits are the symbol
            raw8 = os.path.join(tmp, "rand8.bin")
            rng = np.random.default_rng(1)
            rng.integers(0, 256, size=1000, dtype=np.uint8).tofile(raw8)   # 8000 bits, v = 333
            out8 = subprocess.run([py, module, raw8, "8"], capture_output=True, text=True, check=True)
            res8 = json.loads(out8.stdout)
            self.assertEqual(res8["mode"], "bitstring")
            self.assertEqual(res8["L"], 8000)
            self.assertEqual(res8["v"], 333)
            self.assertTrue(res8["found_p"])
            # --literal on an 8-bit file: the spec gives no value
            outL = subprocess.run([py, module, raw8, "8", "--literal"], capture_output=True, text=True, check=True)
            self.assertTrue(math.isnan(json.loads(outL.stdout)["min_entropy"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
