"""Tests for py90b.lrs -- SP 800-90B §6.3.6 LRS estimate (PDF p. 56-57).

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_lrs.py
  or: <venv>/bin/python reference/py90b/tests/test_lrs.py
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
REFERENCE_DIR = os.path.dirname(os.path.dirname(HERE))       # .../reference
if REFERENCE_DIR not in sys.path:
    sys.path.insert(0, REFERENCE_DIR)

from py90b import lrs  # noqa: E402

# The spec's example input, shared by the t-tuple (§6.3.5) and LRS (§6.3.6)
# worked examples (PDF p. 56-57):
#   "S = (2, 2, 0, 1, 0, 2, 0, 1, 2, 1, 2, 0, 1, 2, 1, 0, 0, 1, 0, 0, 0), and L = 21"
SPEC_S = [2, 2, 0, 1, 0, 2, 0, 1, 2, 1, 2, 0, 1, 2, 1, 0, 0, 1, 0, 0, 0]

# Printed to four decimals in the spec; half a unit in the last place, with a
# little room for the spec's own rounding of intermediates.
TOL4 = 6e-5


class SpecWorkedExample(unittest.TestCase):
    """§6.3.6 example (PDF p. 57): "suppose that the cutoff is 3 instead of 35 in
    step 1. ... In step 1, u is calculated as 4, as the frequency of the most
    common 4-tuple is 2. In step 2, v is calculated as 5. After step 3,
    P4 = 0.0131, P5 = 0.0074, Pmax,4 = 0.3381, Pmax,5 = 0.3744, and
    p-hat = max(0.3381, 0.3744) = 0.3744. After step 4, p_u = 0.6531. The
    min-entropy estimate is -log2(0.6531) = 0.6146."

    Checked by hand before coding (so the exact integer counts are asserted,
    not only the rounded decimals):
      4-tuples, 18 positions: (2,0,1,2) at positions 6 and 11, (0,1,2,1) at
        7 and 12, all others unique  ->  sum C(C_i,2) = 2, C(18,2) = 153,
        P4 = 2/153 = 0.013072 -> "0.0131".
      5-tuples, 17 positions: (2,0,1,2,1) at 6 and 11 only -> sum = 1,
        C(17,2) = 136, P5 = 1/136 = 0.007353 -> "0.0074".
      6-tuples: position 6 gives (2,0,1,2,1,2), position 11 gives
        (2,0,1,2,1,0): no repeat, so v = 5.
    """

    def check(self, res):
        self.assertTrue(res["can_run"])
        self.assertEqual(res["u"], 4)
        self.assertEqual(res["v"], 5)
        self.assertEqual(res["pair_sum_W"], {4: 2, 5: 1})
        self.assertEqual(res["positions_choose2_W"], {4: 153, 5: 136})
        self.assertAlmostEqual(res["P_W"][4], 0.0131, delta=TOL4)
        self.assertAlmostEqual(res["P_W"][5], 0.0074, delta=TOL4)
        self.assertAlmostEqual(res["Pmax_W"][4], 0.3381, delta=TOL4)
        self.assertAlmostEqual(res["Pmax_W"][5], 0.3744, delta=TOL4)
        self.assertEqual(res["argmax_W"], 5)
        self.assertAlmostEqual(res["p-hat"], 0.3744, delta=TOL4)
        self.assertAlmostEqual(res["p_u"], 0.6531, delta=TOL4)
        self.assertAlmostEqual(res["min_entropy"], 0.6146, delta=TOL4)
        # exact values of the same quantities, from the hand count above
        self.assertEqual(res["P_W"][4], 2 / 153)
        self.assertEqual(res["P_W"][5], 1 / 136)
        p_hat = (1 / 136) ** (1 / 5)
        p_u = p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / 20)
        self.assertAlmostEqual(res["p_u"], p_u, places=15)
        self.assertAlmostEqual(res["min_entropy"], -math.log2(p_u), places=15)

    def test_direct_path_alone(self):
        self.check(lrs.estimate(SPEC_S, 2, cutoff=3, method="direct"))

    def test_suffix_path_alone(self):
        self.check(lrs.estimate(SPEC_S, 2, cutoff=3, method="suffix"))

    def test_auto_cross_checks_both(self):
        res = lrs.estimate(SPEC_S, 2, cutoff=3)
        self.check(res)
        self.assertEqual(res["method"], "suffix+direct (agree)")

    def test_most_common_tuple_counts_match_the_t_tuple_example(self):
        # §6.3.5 example on the same S (PDF p. 56): "Q[1] = 9, Q[2] = 4, and
        # Q[3] = 3" and "The number of occurrences of the most common 4-tuple is 2".
        c = lrs._counts_direct(np.asarray(SPEC_S), cutoff=3)
        self.assertEqual({W: c["Q"][W] for W in (1, 2, 3, 4)}, {1: 9, 2: 4, 3: 3, 4: 2})
        self.assertEqual(c["Q"][5], 2)
        self.assertEqual(c["Q"][6], 1)
        s = lrs._counts_suffix(np.asarray(SPEC_S), cutoff=3)
        self.assertEqual(s["Q"], {3: 3, 4: 2, 5: 2, 6: 1})   # u-1, u, v, v+1

    def test_spec_cutoff_35_on_the_example_cannot_run(self):
        # With the real cutoff, Q[1] = 9 < 35 so u = 1 <= v = 5: it CAN run.
        # Check the literal consequence instead: u = 1, W ranges over 1..5.
        res = lrs.estimate(SPEC_S, 2)
        self.assertEqual((res["u"], res["v"]), (1, 5))
        self.assertEqual(sorted(res["P_W"]), [1, 2, 3, 4, 5])
        # W = 1 by hand: counts 0:9, 1:6, 2:6 -> 36+15+15 = 66 pairs over C(21,2)=210
        self.assertEqual(res["pair_sum_W"][1], 66)
        self.assertEqual(res["positions_choose2_W"][1], 210)


class HandDerivedExamples(unittest.TestCase):

    def test_degenerate_all_one_symbol(self):
        # S = forty 0s (L = 40), cutoff 35.  By hand:
        #   the only W-tuple is 0^W, occurring L-W+1 = 41-W times, so
        #   Q[W] = 41-W.  Step 1: smallest W with 41-W < 35  ->  u = 7.
        #   Step 2: Q[39] = 2, Q[40] = 1  ->  v = 39.
        #   Step 3: for every W, one unique tuple with C_i = 41-W, so
        #   sum C(C_i,2) = C(41-W, 2) = C(L-W+1, 2): P_W = 1, Pmax,W = 1, p-hat = 1.
        #   Step 4: p_u = min(1, 1 + 2.576*0) = 1.   Step 5: -log2(1) = 0.
        for method in ("direct", "suffix", "auto"):
            res = lrs.estimate([0] * 40, 1, method=method)
            self.assertEqual((res["u"], res["v"]), (7, 39), method)
            self.assertEqual(sorted(res["P_W"]), list(range(7, 40)), method)
            self.assertTrue(all(p == 1.0 for p in res["P_W"].values()), method)
            self.assertEqual(res["p-hat"], 1.0, method)
            self.assertEqual(res["p_u"], 1.0, method)
            self.assertEqual(res["min_entropy"], 0.0, method)
            self.assertEqual(math.copysign(1.0, res["min_entropy"]), 1.0, "must be +0.0, not -0.0")
            # Q at the lengths the spec's conditions mention
            self.assertEqual(res["Q"][6], 35)
            self.assertEqual(res["Q"][7], 34)
            self.assertEqual(res["Q"][39], 2)
            self.assertEqual(res["Q"][40], 1)

    def test_all_one_symbol_width_eight(self):
        # Same shape with symbol 255 at 8 bits, L = 100: u = 100-33 = 67, v = 99, H = 0.
        res = lrs.estimate([255] * 100, 8)
        self.assertEqual((res["u"], res["v"]), (67, 99))
        self.assertEqual(res["min_entropy"], 0.0)

    def test_clamp_to_one(self):
        # S = (0, 0, 0, 1), L = 4, cutoff 35.  By hand:
        #   Q[1] = 3 < 35 -> u = 1.  "00" repeats (positions 1, 2); the 3-tuples
        #   000 and 001 are each unique -> v = 2.
        #   W = 1: counts 3 and 1 -> sum C = 3; C(4,2) = 6; P_1 = 1/2; Pmax,1 = 1/2.
        #   W = 2: 00, 00, 01 -> counts 2, 1 -> sum C = 1; C(3,2) = 3; P_2 = 1/3;
        #          Pmax,2 = (1/3)^(1/2) = 0.57735.
        #   p-hat = 0.57735.  p_u = min(1, 0.57735 + 2.576*sqrt(0.57735*0.42265/3))
        #          = min(1, 0.57735 + 2.576*0.28519) = min(1, 1.312) = 1.  H = 0.
        res = lrs.estimate([0, 0, 0, 1], 1)
        self.assertEqual((res["u"], res["v"]), (1, 2))
        self.assertEqual(res["P_W"], {1: 0.5, 2: 1 / 3})
        self.assertEqual(res["argmax_W"], 2)
        self.assertAlmostEqual(res["p-hat"], math.sqrt(1 / 3), places=15)
        self.assertEqual(res["p_u"], 1.0)
        self.assertEqual(res["min_entropy"], 0.0)

    def test_no_clamp_sparse_alphabet(self):
        # S = (0, 1, 2, ..., 32, 0): L = 34 symbols at 6 bits.  By hand:
        #   every symbol occurs once except 0 (twice): Q[1] = 2 < 35 -> u = 1.
        #   No 2-tuple repeats ("0,1" at position 1 only; position 34 starts no
        #   2-tuple) -> v = 1.
        #   W = 1: sum C(C_i,2) = C(2,2) = 1; C(34,2) = 561; P_1 = 1/561 = p-hat.
        #   p_u = 1/561 + 2.576*sqrt((1/561)*(560/561)/33)   (not clamped)
        #   H = -log2(p_u)
        res = lrs.estimate(list(range(33)) + [0], 6)
        self.assertEqual((res["u"], res["v"]), (1, 1))
        self.assertEqual(res["pair_sum_W"], {1: 1})
        self.assertEqual(res["positions_choose2_W"], {1: 561})
        p_hat = 1 / 561
        p_u = p_hat + 2.576 * math.sqrt(p_hat * (560 / 561) / 33)
        self.assertAlmostEqual(res["p-hat"], p_hat, places=17)
        self.assertAlmostEqual(res["p_u"], p_u, places=15)
        self.assertAlmostEqual(res["min_entropy"], -math.log2(p_u), places=14)
        self.assertLess(res["p_u"], 1.0)
        # z = 2.5758... is smaller than 2.576, so the documented-divergence
        # variant is the PERMISSIVE direction (higher entropy), as D-1 records.
        self.assertLess(res["p_u_z_exact"], res["p_u"])
        self.assertGreater(res["min_entropy_z_exact"], res["min_entropy"])
        # and passing z explicitly makes it the primary
        res2 = lrs.estimate(list(range(33)) + [0], 6, z=lrs.Z_EXACT_0995)
        self.assertEqual(res2["p_u"], res["p_u_z_exact"])


class CannotRun(unittest.TestCase):

    def test_no_repeat_at_all(self):
        # all distinct symbols: v = 0 < u = 1  ->  "this estimate cannot be computed"
        for method in ("direct", "suffix", "auto"):
            res = lrs.estimate(list(range(16)), 4, method=method)
            self.assertEqual((res["u"], res["v"]), (1, 0), method)
            self.assertFalse(res["can_run"])
            self.assertTrue(math.isnan(res["min_entropy"]))
            self.assertTrue(math.isnan(res["p-hat"]))
            self.assertTrue(math.isnan(res["p_u"]))
            self.assertIn("v < u", res["reason"])

    def test_cutoff_two_always_gives_u_equal_v_plus_one(self):
        # With cutoff 2, "smallest u whose most common u-tuple occurs < 2 times"
        # is exactly v + 1, so v < u for every input.
        rng = np.random.default_rng(7)
        for method in ("direct", "suffix"):
            res = lrs.estimate(rng.integers(0, 2, 300), 1, cutoff=2, method=method)
            self.assertEqual(res["u"], res["v"] + 1, method)
            self.assertFalse(res["can_run"])

    def test_single_symbol_sequence(self):
        res = lrs.estimate([5], 3)
        self.assertEqual((res["u"], res["v"]), (1, 0))
        self.assertFalse(res["can_run"])

    def test_two_symbols(self):
        res = lrs.estimate([1, 1], 1)
        # Q[1] = 2 -> v = 1; u = 1 (2 < 35); W = 1: sum C = 1, C(2,2) = 1 -> P_1 = 1 -> H = 0
        self.assertEqual((res["u"], res["v"]), (1, 1))
        self.assertEqual(res["min_entropy"], 0.0)


class SuffixAgainstDirect(unittest.TestCase):
    """The suffix-array path must reproduce the literal dictionary count exactly
    on random, biased, periodic and bitstring inputs (both are run and compared
    inside estimate(method='auto'); here the comparison is made explicit)."""

    def compare(self, S, cutoff=35):
        S = np.asarray(S)
        d = lrs._counts_direct(S, cutoff)
        s = lrs._counts_suffix(S, cutoff)
        self.assertEqual(d["u"], s["u"])
        self.assertEqual(d["v"], s["v"])
        self.assertEqual(d["pair_sum"], s["pair_sum"])
        for W, q in s["Q"].items():
            self.assertEqual(q, d["Q"][W], f"Q[{W}]")
        r1 = lrs.estimate(S, 8, cutoff=cutoff, method="direct")
        r2 = lrs.estimate(S, 8, cutoff=cutoff, method="suffix")
        for key in ("u", "v", "P_W", "p-hat", "p_u", "min_entropy"):
            if isinstance(r1[key], float) and math.isnan(r1[key]):
                self.assertTrue(math.isnan(r2[key]))
            else:
                self.assertEqual(r1[key], r2[key], key)

    def test_random_bits(self):
        rng = np.random.default_rng(1)
        for n in (50, 200, 1000, 3000):
            self.compare(rng.integers(0, 2, n))

    def test_biased_bits(self):
        rng = np.random.default_rng(2)
        self.compare((rng.random(3000) < 0.9).astype(int))

    def test_random_bytes(self):
        rng = np.random.default_rng(3)
        self.compare(rng.integers(0, 256, 2000))

    def test_small_alphabet(self):
        rng = np.random.default_rng(4)
        self.compare(rng.integers(0, 3, 2500))
        self.compare(rng.integers(0, 3, 2500), cutoff=3)

    def test_periodic_with_a_flaw(self):
        base = np.tile(np.array([3, 1, 4, 1, 5, 9, 2]), 60)   # period 7, L = 420
        base[200] = 7
        self.compare(base)

    def test_long_repeated_block(self):
        rng = np.random.default_rng(5)
        block = rng.integers(0, 2, 400)
        self.compare(np.concatenate([block, rng.integers(0, 2, 50), block]))

    def test_bitstring_of_bytes(self):
        rng = np.random.default_rng(6)
        bits = lrs.to_bitstring(rng.integers(0, 256, 300), 8)
        self.assertEqual(bits.size, 2400)
        self.compare(bits)


class Internals(unittest.TestCase):

    def test_suffix_array_is_sorted_and_a_permutation(self):
        rng = np.random.default_rng(11)
        for S in (rng.integers(0, 2, 300), rng.integers(0, 256, 300), np.zeros(50, int),
                  np.tile([0, 1], 100)):
            sa = lrs._suffix_array(S)
            self.assertEqual(sorted(sa.tolist()), list(range(S.size)))
            sufs = [tuple(S[i:].tolist()) for i in sa]
            self.assertEqual(sufs, sorted(sufs))
            lcp = lrs._lcp_kasai(S.tolist(), sa.tolist())
            for r in range(S.size - 1):
                a, b = sufs[r], sufs[r + 1]
                k = 0
                while k < min(len(a), len(b)) and a[k] == b[k]:
                    k += 1
                self.assertEqual(lcp[r], k)

    def test_pairs_by_exact_lcp_counts_every_pair_once(self):
        rng = np.random.default_rng(12)
        for _ in range(20):
            m = int(rng.integers(0, 40))
            lcp = rng.integers(0, 6, m).tolist()
            exact = lrs._pairs_by_exact_lcp(lcp)
            self.assertEqual(sum(exact), (m + 1) * m // 2)
            # brute force: LCP(a,b) = min(lcp[a..b-1])
            brute = [0] * (max(lcp) + 1 if m else 1)
            for a in range(m + 1):
                for b in range(a + 1, m + 1):
                    brute[min(lcp[a:b])] += 1
            self.assertEqual(exact, brute)

    def test_to_bitstring_is_msb_first(self):
        self.assertEqual(lrs.to_bitstring([0b101, 0b010], 3).tolist(), [1, 0, 1, 0, 1, 0])
        self.assertEqual(lrs.to_bitstring([1], 1).tolist(), [1])
        self.assertEqual(lrs.to_bitstring([0x80, 0x01], 8).tolist(),
                         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])

    def test_input_validation(self):
        with self.assertRaises(ValueError):
            lrs.estimate([0, 2], 1)
        with self.assertRaises(ValueError):
            lrs.estimate([], 1)
        with self.assertRaises(ValueError):
            lrs.estimate([0, 1], 1, cutoff=1)
        with self.assertRaises(ValueError):
            lrs.estimate([0, 1], 0)


class CommandLine(unittest.TestCase):

    def run_cli(self, data: bytes, *args):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "in.bin")
            with open(path, "wb") as fh:
                fh.write(data)
            proc = subprocess.run([sys.executable, os.path.join(REFERENCE_DIR, "py90b", "lrs.py"),
                                   path, *args], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_literal_matches_estimate(self):
        data = bytes(SPEC_S)
        out = self.run_cli(data, "2", "--literal", "--cutoff", "3")
        ref = lrs.estimate(SPEC_S, 2, cutoff=3)
        self.assertEqual(out["mode"], "literal")
        self.assertEqual((out["u"], out["v"]), (4, 5))
        self.assertEqual(out["min_entropy"], ref["min_entropy"])
        self.assertEqual(out["P_W"], {str(k): v for k, v in ref["P_W"].items()})

    def test_low_bits_are_the_symbol(self):
        # bytes 0xFE, 0xFF at 1 bit/symbol are the symbols 0, 1
        out = self.run_cli(bytes([0xFE, 0xFF, 0xFE, 0xFE]), "1")
        ref = lrs.estimate([0, 1, 0, 0], 1)
        self.assertEqual(out["u"], ref["u"])
        self.assertEqual(out["v"], ref["v"])
        self.assertEqual(out["min_entropy"], ref["min_entropy"])

    def test_bitstring_mode(self):
        rng = np.random.default_rng(21)
        raw = rng.integers(0, 256, 200).astype(np.uint8)
        out = self.run_cli(raw.tobytes(), "8", "--bitstring")
        ref = lrs.estimate(lrs.to_bitstring(raw.astype(int), 8), 1)
        self.assertEqual(out["mode"], "bitstring")
        self.assertEqual(out["L"], 1600)
        self.assertEqual((out["u"], out["v"]), (ref["u"], ref["v"]))
        self.assertEqual(out["min_entropy"], ref["min_entropy"])

    def test_nan_round_trips_for_cannot_run(self):
        out = self.run_cli(bytes(range(16)), "4")
        self.assertFalse(out["can_run"])
        self.assertTrue(math.isnan(out["min_entropy"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
