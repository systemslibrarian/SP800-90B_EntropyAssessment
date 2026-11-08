"""
Tests for py90b.collision -- SP 800-90B section 6.3.2 (PDF pp. 50-51).

Every expected number below is either quoted from the standard's worked
example (PDF p. 51) or derived BY HAND in the comment above the test.

Run:  <venv>/bin/python -m unittest tests.test_collision      (from reference/py90b)
  or  <venv>/bin/python tests/test_collision.py
"""
import json
import math
import os
from decimal import Decimal, localcontext
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

import numpy as np

# make `py90b` importable when run as a script from anywhere
_HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))          # .../reference
from py90b import collision as C                   # noqa: E402

_trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz")

# --- the standard's worked example, SP 800-90B section 6.3.2, PDF p. 51 ------------
# "Suppose that S = (1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0,
#  1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0).  The collisions of
#  the sequence are (1, 0, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (0, 1, 0), (1, 1),
#  (1, 0, 0), (1, 1), (0, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (0, 1, 0), (1, 1).
#  After step 5, v=14, and the sequence (t1, ... tv) is (3, 3, 3, 3, 3, 2, 3, 2,
#  2, 3, 3, 3, 3, 2).  Then X-bar = 2.7143, sigma-hat = 0.4688, and
#  X-bar' = 2.3915.  The solution to the equation is p = 0.7329, giving an
#  estimated min-entropy of 0.4483."
SPEC_S = [1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0,
          1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0]
SPEC_T = [3, 3, 3, 3, 3, 2, 3, 2, 2, 3, 3, 3, 3, 2]


def closed_form_p(x_bar_prime):
    """rhs(p) = 2 + 2 p (1 - p) = X-bar'  =>  p = (1 + sqrt(5 - 2 X-bar')) / 2.
    Evaluated in 60-digit decimal: in binary64 the subtraction 5 - 2 X-bar' loses
    ~7 digits near X-bar' = 2.5, which is the closed form's problem, not the search's."""
    with localcontext() as ctx:
        ctx.prec = 60
        X = Decimal(x_bar_prime)
        return float((1 + (5 - 2 * X).sqrt()) / 2)


class WorkedExample(unittest.TestCase):
    def test_collision_times_match_the_listed_collisions(self):
        t, consumed = C.collision_times(SPEC_S)
        self.assertEqual(t, SPEC_T)
        self.assertEqual(len(t), 14)
        self.assertEqual(consumed, 38)       # 40 samples; trailing (1, 0) dropped

    def test_all_printed_intermediates(self):
        r = C.estimate(SPEC_S, 1)
        self.assertEqual(r["v"], 14)
        self.assertEqual(r["Sum t_i"], 38)
        self.assertEqual(r["discarded_tail"], 2)
        self.assertEqual(r["k"], 2)
        # X-bar = 38/14 = 2.714285...
        self.assertAlmostEqual(r["X-bar"], 2.7143, places=4)
        self.assertAlmostEqual(r["X-bar"], 38 / 14, places=15)
        # sum (t - mean)^2 = 10*(2/7)^2 + 4*(5/7)^2 = (40 + 100)/49 = 140/49 = 20/7
        # sigma-hat = sqrt((20/7)/13) = sqrt(20/91) = 0.46881...
        self.assertAlmostEqual(r["sigma-hat"], 0.4688, places=4)
        self.assertAlmostEqual(r["sigma-hat"], math.sqrt(20 / 91), places=15)
        # X-bar' = 2.714286 - 2.576 * 0.468807 / sqrt(14) = 2.391541
        self.assertAlmostEqual(r["X-bar'"], 2.3915, places=4)
        self.assertAlmostEqual(r["X-bar'"], 38 / 14 - 2.576 * math.sqrt(20 / 91) / math.sqrt(14), places=15)
        self.assertTrue(r["found_p"])
        self.assertAlmostEqual(r["p"], 0.7329, places=4)
        # Full-precision chain: X-bar' = 2.3915284, p = 0.7328858, -log2 p = 0.4483396,
        # which rounds to the printed 0.4483 (and -log2 of the rounded 0.7329 is
        # 0.4483117, also 0.4483).  So the worked example agrees with the literal
        # reading at every printed digit.
        self.assertAlmostEqual(r["min entropy"], 0.4483, places=4)
        self.assertAlmostEqual(-math.log2(0.7329), 0.4483, places=4)
        self.assertEqual(r["min entropy"], r["min_entropy"])
        self.assertEqual(r["note"], "")

    def test_variants_and_equations_agree_inside_the_solvable_window(self):
        base = C.estimate(SPEC_S, 1)
        for kw in ({"variant": "clamp"}, {"equation": "simplified"},
                   {"variant": "clamp", "equation": "simplified"}):
            r = C.estimate(SPEC_S, 1, **kw)
            self.assertAlmostEqual(r["p"], base["p"], places=13, msg=str(kw))
            self.assertAlmostEqual(r["min_entropy"], base["min_entropy"], places=13, msg=str(kw))
        self.assertAlmostEqual(base["min_entropy_spec_fallback"], base["min_entropy_clamp"], places=13)

    def test_exact_quantile_option_moves_x_bar_prime_only_slightly(self):
        # D-1 / C22c (documented): 2.5758293035489008 instead of 2.576.
        r_spec = C.estimate(SPEC_S, 1)
        r_exact = C.estimate(SPEC_S, 1, z_alpha=C.Z_ALPHA_EXACT)
        self.assertGreater(r_exact["X-bar'"], r_spec["X-bar'"])      # smaller z -> higher bound
        self.assertLess(r_exact["min_entropy"], r_spec["min_entropy"] + 1e-3)
        self.assertGreater(r_exact["min_entropy"], r_spec["min_entropy"])   # higher X-bar' -> smaller p -> more entropy
        self.assertLess(abs(r_exact["min_entropy"] - r_spec["min_entropy"]), 1e-3)


class HandDerivedInputs(unittest.TestCase):
    def test_degenerate_constant_sequence_gives_zero_bits(self):
        # S = (0,0,0,0,0,0), L = 6.  Steps 2-3: every window is (0,0), t = 2.
        # v = 3, t = (2,2,2), X-bar = 2, sigma-hat = 0, X-bar' = 2 - 0 = 2.
        # Step 7: rhs(p) = 2 + 2pq = 2  =>  q = 0, p = 1.  Step 8: -log2(1) = 0.
        for variant in ("spec", "clamp"):
            for equation in ("spec", "simplified"):
                r = C.estimate([0] * 6, 1, variant=variant, equation=equation)
                self.assertEqual(r["v"], 3)
                self.assertEqual(r["Sum t_i"], 6)
                self.assertEqual(r["discarded_tail"], 0)
                self.assertEqual(r["X-bar"], 2.0)
                self.assertEqual(r["sigma-hat"], 0.0)
                self.assertEqual(r["X-bar'"], 2.0)
                self.assertTrue(r["found_p"])
                self.assertEqual(r["p"], 1.0)
                self.assertEqual(r["min_entropy"], 0.0)
                self.assertEqual(r["min_entropy_spec_fallback"], 0.0)
                self.assertEqual(r["min_entropy_clamp"], 0.0)
        # L = 7: the seventh sample has no partner -> dropped.
        r = C.estimate([0] * 7, 1)
        self.assertEqual((r["v"], r["discarded_tail"]), (3, 1))
        # A constant 8-bit sequence is a (degenerate) binary alphabet: k = 1.
        r8 = C.estimate([255] * 6, 8)
        self.assertEqual((r8["k"], r8["v"], r8["min_entropy"]), (1, 3, 0.0))

    def test_alternating_sequence_has_no_solution_above_2_5(self):
        # S = (0,1,0,1,0,1,0,1,0), L = 9.  Windows: (0,1,0),(1,0,1),(0,1,0): t = 3 each.
        # v = 3, X-bar = 3, sigma-hat = 0, X-bar' = 3 > 2.5 = rhs(1/2).
        # Step 7 finds no p in [1/2, 1]; step 8: min-entropy = log2(2) = 1.
        for variant in ("spec", "clamp"):
            r = C.estimate([0, 1] * 4 + [0], 1, variant=variant)
            self.assertEqual(r["v"], 3)
            self.assertEqual(r["Sum t_i"], 9)
            self.assertEqual(r["X-bar"], 3.0)
            self.assertEqual(r["sigma-hat"], 0.0)
            self.assertEqual(r["X-bar'"], 3.0)
            self.assertFalse(r["found_p"])
            self.assertTrue(math.isnan(r["p"]))
            self.assertEqual(r["min_entropy"], 1.0)
            self.assertEqual(r["min_entropy_spec_fallback"], 1.0)
            self.assertEqual(r["min_entropy_clamp"], 1.0)
            self.assertIn("above 2.5", r["note"])

    def test_lower_bound_below_2_exposes_the_two_readings(self):
        # S = eighteen 0s then (0,1,0), L = 21.
        # Windows: nine (0,0) with t = 2, then (0,1,0) with t = 3.  v = 10, sum = 21.
        # X-bar = 2.1.  sum (t - 2.1)^2 = 9*(0.1)^2 + (0.9)^2 = 0.09 + 0.81 = 0.90
        # sigma-hat = sqrt(0.90 / 9) = sqrt(0.1) = 0.316228
        # X-bar' = 2.1 - 2.576 * sqrt(0.1)/sqrt(10) = 2.1 - 2.576 * 0.1 = 1.8424 < 2.
        # Literal step 8 ("the search does not yield a solution"): 1 bit.
        # The clamp reading (FORK-DIVERGENCE D-2): X-bar' -> 2, p = 1, 0 bits.
        S = [0] * 18 + [0, 1, 0]
        r = C.estimate(S, 1)                       # default variant='spec'
        self.assertEqual(r["v"], 10)
        self.assertEqual(r["Sum t_i"], 21)
        self.assertAlmostEqual(r["X-bar"], 2.1, places=15)
        self.assertAlmostEqual(r["sigma-hat"], math.sqrt(0.1), places=15)
        self.assertAlmostEqual(r["X-bar'"], 1.8424, places=12)
        self.assertFalse(r["found_p"])
        self.assertTrue(math.isnan(r["p"]))
        self.assertEqual(r["min_entropy"], 1.0)
        self.assertIn("below 2", r["note"])
        self.assertEqual(r["min_entropy_spec_fallback"], 1.0)
        self.assertEqual(r["min_entropy_clamp"], 0.0)
        rc = C.estimate(S, 1, variant="clamp")
        self.assertTrue(rc["found_p"])
        self.assertEqual(rc["p"], 1.0)
        self.assertEqual(rc["min_entropy"], 0.0)
        self.assertEqual(rc["min_entropy_spec_fallback"], 1.0)
        self.assertEqual(rc["min_entropy_clamp"], 0.0)

    def test_fewer_than_two_collisions_gives_nan_not_one(self):
        # S = (0,1): no repeat before the end -> v = 0 -> X-bar = 0/0.
        r = C.estimate([0, 1], 1)
        self.assertEqual(r["v"], 0)
        self.assertEqual(r["discarded_tail"], 2)
        for key in ("X-bar", "sigma-hat", "X-bar'", "p", "min_entropy"):
            self.assertTrue(math.isnan(r[key]), key)
        self.assertIn("v=0", r["note"])
        # S = (0,1,1,0,1) (the tracker's F12 input): (0,1,1) t = 3, then (0,1) runs out.
        # v = 1 -> X-bar = 3, sigma-hat = sqrt(0/0) undefined -> NaN downstream.
        r = C.estimate([0, 1, 1, 0, 1], 1)
        self.assertEqual(r["v"], 1)
        self.assertEqual(r["X-bar"], 3.0)
        for key in ("sigma-hat", "X-bar'", "p", "min_entropy"):
            self.assertTrue(math.isnan(r[key]), key)
        self.assertFalse(r["found_p"])
        self.assertIn("v=1", r["note"])

    def test_non_binary_input_is_not_applied_unless_asked(self):
        S = [0, 1, 2] * 4                            # k = 3
        r = C.estimate(S, 2)
        self.assertEqual(r["k"], 3)
        self.assertEqual(r["v"], 0)                  # steps not run
        self.assertTrue(math.isnan(r["min_entropy"]))
        self.assertIn("not applied", r["note"])
        # allow_nonbinary: windows (0,1,2,0),(1,2,0,1),(2,0,1,2) -> t = 4,4,4;
        # X-bar' = 4 > 2.5 -> no solution -> 1 bit, with a warning.
        r = C.estimate(S, 2, allow_nonbinary=True)
        self.assertEqual((r["v"], r["Sum t_i"], r["X-bar"], r["X-bar'"]), (3, 12, 4.0, 4.0))
        self.assertEqual(r["min_entropy"], 1.0)
        self.assertIn("WARNING", r["note"])

    def test_two_valued_wide_symbols_are_a_binary_alphabet(self):
        # Collision times depend only on equality, so the worked example with
        # 0 -> 0 and 1 -> 255 at 8 bits per symbol must give the same figures.
        S8 = [255 if s else 0 for s in SPEC_S]
        r1 = C.estimate(SPEC_S, 1)
        r8 = C.estimate(S8, 8)
        self.assertEqual(r8["k"], 2)
        for key in ("v", "Sum t_i", "X-bar", "sigma-hat", "X-bar'", "p", "min_entropy"):
            self.assertEqual(r8[key], r1[key], key)

    def test_out_of_range_symbol_is_refused(self):
        with self.assertRaises(ValueError):
            C.estimate([0, 2], 1)
        with self.assertRaises(ValueError):
            C.estimate([0, -1], 1)


class BitstringConstruction(unittest.TestCase):
    def test_msb_first_unpacking(self):
        self.assertEqual(C.to_bitstring([0b101, 0b010], 3).tolist(), [1, 0, 1, 0, 1, 0])
        self.assertEqual(C.to_bitstring([0xA5], 8).tolist(), [1, 0, 1, 0, 0, 1, 0, 1])
        self.assertEqual(C.to_bitstring([1, 0, 1], 1).tolist(), [1, 0, 1])
        self.assertEqual(C.to_bitstring([0xA5, 0xFF], 8, truncate_bits=10).tolist(),
                         [1, 0, 1, 0, 0, 1, 0, 1, 1, 1])

    def test_bitstring_mode_equals_estimate_on_the_unpacked_bits(self):
        rng = np.random.default_rng(90)
        sym = rng.integers(0, 256, size=500)
        r_mode = C.estimate(sym, 8, mode="bitstring")
        r_bits = C.estimate(C.to_bitstring(sym, 8), 1)
        self.assertEqual(r_mode["L"], 4000)
        self.assertEqual(r_mode["width"], 1)
        for key in ("v", "Sum t_i", "X-bar", "sigma-hat", "X-bar'", "p", "min_entropy"):
            self.assertEqual(r_mode[key], r_bits[key], key)


class EquationAndSearch(unittest.TestCase):
    def test_incomplete_gamma_3_closed_form_against_quadrature(self):
        # Gamma(3, z) = int_z^inf t^2 e^-t dt; integrand < 1e-30 beyond z + 80.
        for z in (0.5, 1.0, 2.0, 4.0):
            t = np.linspace(z, z + 80.0, 2_000_001)
            numeric = _trapezoid(t * t * np.exp(-t), t)
            self.assertAlmostEqual(numeric / C.upper_incomplete_gamma_3(z), 1.0, places=8, msg=str(z))

    def test_F_closed_form_equals_the_definition(self):
        for z in (0.5, 1.0, 2.0, 4.0, 10.0, 100.0, 500.0):
            self.assertAlmostEqual(C.F_of_reciprocal(z) / C.F_of_reciprocal_by_definition(z), 1.0,
                                   places=11, msg=str(z))
        # F(q) = q + 2q^2 + 2q^3
        for q in (0.1, 0.25, 0.5):
            self.assertAlmostEqual(C.F(q), q + 2 * q ** 2 + 2 * q ** 3, places=14)

    def test_printed_rhs_equals_2_plus_2pq_and_is_monotone(self):
        self.assertEqual(C.rhs_spec(0.5), 2.5)
        self.assertEqual(C.rhs_spec(1.0), 2.0)
        grid = np.linspace(0.5, 1.0 - 2.0 ** -40, 4001).tolist() + [1.0 - 2.0 ** -52]
        prev = float("inf")
        for p in grid:
            a, b = C.rhs_spec(p), C.rhs_simplified(p)
            self.assertAlmostEqual(a, b, places=12, msg=repr(p))
            self.assertLess(a, prev, msg=repr(p))
            prev = a
        # the worked example: 2 + 2(0.7329)(0.2671) = 2.3915
        self.assertAlmostEqual(C.rhs_spec(0.7329), 2.3915, places=4)

    def test_bisection_matches_the_closed_form_solution(self):
        for xbp in (2.0, 2.0000001, 2.001, 2.1, 2.3915, 2.49, 2.4999999, 2.5):
            for eq in ("spec", "simplified"):
                p = C.solve_p_by_binary_search(xbp, eq)
                self.assertIsNotNone(p, (xbp, eq))
                self.assertAlmostEqual(p, closed_form_p(xbp), places=14, msg=(xbp, eq))
                self.assertAlmostEqual(C.RHS_FUNCTIONS[eq](p), xbp, places=12, msg=(xbp, eq))
        self.assertEqual(C.solve_p_by_binary_search(2.0), 1.0)
        self.assertEqual(C.solve_p_by_binary_search(2.5), 0.5)
        for xbp in (1.9999999, 2.5000001, float("nan"), float("inf"), -float("inf")):
            self.assertIsNone(C.solve_p_by_binary_search(xbp), repr(xbp))


class CommandLine(unittest.TestCase):
    def test_main_prints_json_for_the_worked_example(self):
        with tempfile.TemporaryDirectory() as d:
            raw = pathlib.Path(d) / "spec_example.bin"
            raw.write_bytes(bytes(SPEC_S))
            out = pathlib.Path(d) / "out.json"
            with open(out, "w") as fh:
                proc = subprocess.run([sys.executable, str(_HERE.parents[1] / "collision.py"),
                                       str(raw), "1", "--literal"], stdout=fh, stderr=subprocess.PIPE)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            r = json.loads(out.read_text())
            self.assertEqual(r["v"], 14)
            self.assertEqual(r["samples_read"], 40)
            self.assertEqual(r["out_of_width_bytes_masked"], 0)
            self.assertAlmostEqual(r["p"], 0.7329, places=4)
            self.assertAlmostEqual(r["min entropy"], 0.4483, delta=1e-4)
            # 8-bit file, default mode is the bitstring
            raw8 = pathlib.Path(d) / "bytes.bin"
            raw8.write_bytes(bytes([0xA5, 0x5A] * 20))
            out8 = pathlib.Path(d) / "out8.json"
            with open(out8, "w") as fh:
                proc = subprocess.run([sys.executable, str(_HERE.parents[1] / "collision.py"),
                                       str(raw8), "8"], stdout=fh, stderr=subprocess.PIPE)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            r8 = json.loads(out8.read_text())
            self.assertEqual((r8["mode"], r8["L"]), ("bitstring", 320))

    def test_usage_error_exit_code(self):
        self.assertEqual(C.main(["collision.py"]), 2)


class Performance(unittest.TestCase):
    def test_20000_byte_symbols_as_a_bitstring_is_fast(self):
        rng = np.random.default_rng(2026)
        sym = rng.integers(0, 256, size=20_000)
        t0 = time.perf_counter()
        r = C.estimate(sym, 8, mode="bitstring")
        dt = time.perf_counter() - t0
        self.assertEqual(r["L"], 160_000)
        self.assertTrue(r["found_p"])
        self.assertTrue(0.5 < r["min_entropy"] <= 1.0)
        self.assertLess(dt, 10.0)
        sys.stderr.write(f"\n[perf] 20,000 x 8-bit symbols -> 160,000 bits in {dt:.3f} s "
                         f"(linear extrapolation to 1,000,000 symbols: {dt * 50:.1f} s)\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
