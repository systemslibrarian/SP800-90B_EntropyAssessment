"""Tests for py90b.markov -- SP 800-90B section 6.3.3, the Markov estimate.

Every expected value here is either quoted from the standard's worked example
(PDF pp. 52-53) or derived by hand in the comment above the assertion.

Run:  <venv>/bin/python -m pytest tests/test_markov.py
  or: <venv>/bin/python tests/test_markov.py
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG_PARENT = os.path.dirname(os.path.dirname(HERE))          # .../reference
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

from py90b import markov                                       # noqa: E402
from py90b.markov import (SEQUENCE_TABLE, estimate, sequence_log2_probabilities,  # noqa: E402
                          to_bitstring)

MARKOV_PY = os.path.join(PKG_PARENT, "py90b", "markov.py")

# SP 800-90B section 6.3.3 worked example (PDF p. 52): "L = 40 and S = (...)".
SPEC_S = [1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0,
          1, 1, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0]

# The six probabilities the spec prints (PDF p. 53), in the table's order.
SPEC_TABLE = {
    "00...0":    3.9837e-53,
    "0101...01": 4.4813e-30,
    "011...1":   1.4202e-47,
    "100...0":   6.4631e-53,
    "1010...10": 4.6288e-30,
    "11...1":    1.1021e-47,
}


class WorkedExample(unittest.TestCase):
    """PDF pp. 52-53: P_0 = 0.475, P_1 = 0.525, T = [[0.389, 0.611],
    [0.571, 0.429]], p-hat_max = 4.6288e-30, min-entropy 0.761."""

    def setUp(self):
        self.r = estimate(SPEC_S, 1)

    def test_table_exponents_cover_128_symbols(self):
        # Each row is one initial symbol plus 127 transitions.
        for name, _initial, transitions in SEQUENCE_TABLE:
            self.assertEqual(sum(e for _, e in transitions), 127, name)

    def test_counts_by_hand(self):
        # Zeros: positions 2,3,4,8,9,11,13,15,19,20,23,24,25,29,30,32,34,36,40 -> 19.
        # Overlapping pairs (s_i, s_{i+1}), i = 1..39:
        #   00 at i = 2,3,8,19,23,24,29                    -> 7
        #   01 at i = 4,9,11,13,15,20,25,30,32,34,36       -> 11
        #   10 at i = 1,7,10,12,14,18,22,28,31,33,35,39    -> 12
        #   11 at i = 5,6,16,17,21,26,27,37,38             -> 9
        r = self.r
        self.assertEqual(r["L"], 40)
        self.assertEqual(r["#{0 in S}"], 19)
        self.assertEqual(r["#{1 in S}"], 21)
        self.assertEqual(r["#{00 in S}"], 7)
        self.assertEqual(r["#{01 in S}"], 11)
        self.assertEqual(r["#{10 in S}"], 12)
        self.assertEqual(r["#{11 in S}"], 9)
        self.assertEqual(7 + 11 + 12 + 9, 39)           # every adjacent pair counted once

    def test_step1_initial_probabilities(self):
        # Spec: "P_0 = 0.475 and P_1 = 0.525".  19/40 = 0.475 exactly.
        self.assertEqual(self.r["P_0"], 19 / 40)
        self.assertAlmostEqual(self.r["P_1"], 0.525, places=12)

    def test_step2_transition_matrix(self):
        # Spec prints the matrix to three decimals: 0.389 0.611 / 0.571 0.429.
        r = self.r
        self.assertEqual(r["P_{0,0}"], 7 / 18)
        self.assertEqual(r["P_{0,1}"], 11 / 18)
        self.assertEqual(r["P_{1,0}"], 12 / 21)
        self.assertEqual(r["P_{1,1}"], 9 / 21)
        self.assertEqual(round(r["P_{0,0}"], 3), 0.389)
        self.assertEqual(round(r["P_{0,1}"], 3), 0.611)
        self.assertEqual(round(r["P_{1,0}"], 3), 0.571)
        self.assertEqual(round(r["P_{1,1}"], 3), 0.429)

    def test_overlapping_pairs_is_the_reading_the_example_fixes(self):
        # Non-overlapping pairs (s1s2),(s3s4),... of SPEC_S are
        # 10 00 11 10 01 01 01 01 11 00 11 00 01 11 00 10 10 10 11 10
        # -> #{00} = 4, #{01} = 5 -> P_{0,0} would be 4/9 = 0.444, not 0.389.
        pairs = [(SPEC_S[i], SPEC_S[i + 1]) for i in range(0, 40, 2)]
        n00 = pairs.count((0, 0))
        n01 = pairs.count((0, 1))
        self.assertEqual((n00, n01), (4, 5))
        self.assertNotEqual(round(n00 / (n00 + n01), 3), 0.389)
        self.assertEqual(round(self.r["P_{0,0}"], 3), 0.389)

    def test_step4_min_entropy(self):
        # Spec: "min(-log2(4.6288e-30)/128, 1) = min(0.761, 1) = 0.761".
        r = self.r
        self.assertTrue(r["applicable"])
        self.assertEqual(round(r["min_entropy"], 3), 0.761)
        # The maximum is the 1010...10 row, as in the spec's table.
        rows = r["sequence_probabilities"]
        self.assertEqual(max(rows, key=rows.get), "1010...10")
        self.assertEqual(r["p-hat_max"], rows["1010...10"])
        # No undefined transitions, so the bounds coincide with the value.
        self.assertFalse(r["undefined_transitions_present"])
        self.assertEqual(r["min_entropy_lower"], r["min_entropy"])
        self.assertEqual(r["min_entropy_upper"], r["min_entropy"])

    def test_step3_table_matches_spec_loosely_and_the_reason_is_rounding(self):
        # RECORDED AMBIGUITY.  The spec's printed six probabilities were
        # computed from the 3-decimal ROUNDED matrix (0.389, 0.611, 0.571,
        # 0.429), not from the exact fractions.  With exact fractions the rows
        # differ from the printed values by 3.5 % to 12 % (e.g. 00...0 is
        # 3.84e-53 against the printed 3.9837e-53), while the final
        # min-entropy still rounds to 0.761 either way (0.76064 exact,
        # 0.76131 rounded).  The code is not fudged to match the table; this
        # test shows (a) the literal result is within 13 % of every printed
        # row and (b) feeding the rounded matrix through the same step-3
        # arithmetic reproduces the printed table to 4 significant digits.
        rows = self.r["sequence_probabilities"]
        for name, printed in SPEC_TABLE.items():
            rel = abs(rows[name] - printed) / printed
            self.assertLess(rel, 0.13, f"{name}: {rows[name]:.4e} vs printed {printed:.4e}")
        rounded = {"P_0": 0.475, "P_1": 0.525,
                   "P_{0,0}": 0.389, "P_{0,1}": 0.611, "P_{1,0}": 0.571, "P_{1,1}": 0.429}
        log2_rows = sequence_log2_probabilities(rounded)
        for name, printed in SPEC_TABLE.items():
            got = 2.0 ** log2_rows[name]
            self.assertLess(abs(got - printed) / printed, 1e-3,
                            f"{name}: rounded-matrix {got:.4e} vs printed {printed:.4e}")
        self.assertEqual(round(-max(log2_rows.values()) / 128, 3), 0.761)


class HandDerivedCases(unittest.TestCase):

    def test_all_zero_is_degenerate_and_determined(self):
        # L = 1000 zeros.  P_0 = 1000/1000 = 1, P_1 = 0.
        # #{00} = 999, #{01} = 0 -> P_{0,0} = 1, P_{0,1} = 0.
        # #{10} = #{11} = 0 -> P_{1,0} = P_{1,1} = 0/0: NO VALUE (NaN).
        # Row 00...0 = P_0 x P_{0,0}^127 = 1.  Every other row has a factor
        # that is exactly 0 (P_1 = 0 or P_{0,1} = 0), so whatever value the
        # undefined entries take in [0,1] those rows are 0: the bounds
        # coincide, p-hat_max = 1, min-entropy = min(-log2(1)/128, 1) = 0.
        r = estimate([0] * 1000, 1)
        self.assertEqual(r["P_0"], 1.0)
        self.assertEqual(r["P_1"], 0.0)
        self.assertEqual(r["P_{0,0}"], 1.0)
        self.assertEqual(r["P_{0,1}"], 0.0)
        self.assertTrue(math.isnan(r["P_{1,0}"]))
        self.assertTrue(math.isnan(r["P_{1,1}"]))
        self.assertTrue(r["undefined_transitions_present"])
        self.assertEqual(r["p-hat_max"], 1.0)
        self.assertEqual(r["min_entropy"], 0.0)
        self.assertEqual(r["min_entropy_lower"], 0.0)
        self.assertEqual(r["min_entropy_upper"], 0.0)
        # The other variants: 'one' and 'zero' agree; the literal IEEE
        # reading ('nan') has no value because a NaN row enters the maximum.
        self.assertEqual(estimate([0] * 1000, 1, undefined_transition="one")["min_entropy"], 0.0)
        self.assertEqual(estimate([0] * 1000, 1, undefined_transition="zero")["min_entropy"], 0.0)
        self.assertTrue(math.isnan(estimate([0] * 1000, 1, undefined_transition="nan")["min_entropy"]))

    def test_all_one_is_symmetric(self):
        # Same argument with 0 <-> 1: P_1 = 1, row 11...1 = 1, min-entropy 0.
        r = estimate([1] * 1000, 1)
        self.assertEqual(r["P_0"], 0.0)
        self.assertEqual(r["P_1"], 1.0)
        self.assertEqual(r["P_{1,1}"], 1.0)
        self.assertTrue(math.isnan(r["P_{0,0}"]))
        self.assertEqual(r["p-hat_max"], 1.0)
        self.assertEqual(r["min_entropy"], 0.0)
        self.assertFalse(r["translated"])         # {1} is already inside {0,1}

    def test_alternating(self):
        # S = 0101...01, L = 1000.  #{0} = 500 -> P_0 = P_1 = 0.5.
        # Pairs: 01 at every odd i (500 of them), 10 at every even i (499);
        # #{00} = #{11} = 0.  So P_{0,0} = 0, P_{0,1} = 1, P_{1,0} = 1, P_{1,1} = 0.
        # Rows: 00...0 = 0.5 x 0 = 0;  0101...01 = 0.5 x 1 x 1 = 0.5;
        #       011...1 = 0.5 x 1 x 0 = 0;  100...0 = 0.5 x 1 x 0 = 0;
        #       1010...10 = 0.5;  11...1 = 0.
        # p-hat_max = 0.5, min-entropy = min(1/128, 1) = 0.0078125 exactly.
        r = estimate([0, 1] * 500, 1)
        self.assertEqual(r["#{01 in S}"], 500)
        self.assertEqual(r["#{10 in S}"], 499)
        self.assertEqual(r["P_{0,0}"], 0.0)
        self.assertEqual(r["P_{0,1}"], 1.0)
        self.assertEqual(r["P_{1,0}"], 1.0)
        self.assertEqual(r["P_{1,1}"], 0.0)
        self.assertEqual(r["p-hat_max"], 0.5)
        self.assertEqual(r["min_entropy"], 1 / 128)
        self.assertEqual(r["sequence_probabilities"]["00...0"], 0.0)
        self.assertEqual(r["sequence_log2_probabilities"]["00...0"], -math.inf)

    def test_five_samples_all_transitions_seen(self):
        # S = (0,0,1,1,0): P_0 = 3/5 = 0.6, P_1 = 0.4.
        # Pairs 00, 01, 11, 10 once each -> every P_{x,y} = 1/2.
        # Every row = P_first x 2^-127; the max has P_first = P_0 = 0.6.
        # min-entropy = (127 - log2(0.6)) / 128.
        r = estimate([0, 0, 1, 1, 0], 1)
        self.assertEqual(r["P_0"], 0.6)
        self.assertAlmostEqual(r["P_1"], 0.4, places=15)
        for k in ("P_{0,0}", "P_{0,1}", "P_{1,0}", "P_{1,1}"):
            self.assertEqual(r[k], 0.5)
        self.assertAlmostEqual(r["min_entropy"], (127 - math.log2(0.6)) / 128, places=15)
        # 2**(log2(0.6) - 127) round-trips through log2/pow: compare relatively.
        expected = 0.6 * 2.0 ** -127
        self.assertAlmostEqual(r["p-hat_max"], expected, delta=1e-14 * expected)

    def test_undetermined_tiny_case_reports_bounds_and_nan(self):
        # S = (0,0,0,0,1), L = 5: P_0 = 0.8, P_1 = 1 - 0.8.
        # #{00} = 3, #{01} = 1 -> P_{0,0} = 0.75, P_{0,1} = 0.25.
        # #{10} = #{11} = 0 -> P_{1,0}, P_{1,1} undefined (NaN).
        # Substituting u for the undefined entries:
        #   u = 0: only 00...0 survives: 0.8 x 0.75^127 ~ 1.06e-16.
        #   u = 1: 011...1 = 0.8 x 0.25 x 1 = 0.2 and 11...1 = P_1 x 1 = 0.2
        #          dominate; max = 0.2.
        # The two ends differ, so the spec gives no single value: NaN, with
        #   min_entropy_lower = -log2(0.2)/128 = 0.018140...   (u = 1)
        #   min_entropy_upper = -log2(0.8 x 0.75^127)/128 = 0.414310...  (u = 0)
        r = estimate([0, 0, 0, 0, 1], 1)
        self.assertEqual(r["P_{0,0}"], 0.75)
        self.assertEqual(r["P_{0,1}"], 0.25)
        self.assertTrue(math.isnan(r["P_{1,0}"]))
        self.assertTrue(math.isnan(r["P_{1,1}"]))
        self.assertTrue(math.isnan(r["min_entropy"]))
        self.assertTrue(math.isnan(r["p-hat_max"]))
        lower_h = -math.log2(r["P_1"]) / 128                      # P_1 = 1 - 0.8 as the spec writes it
        upper_h = -(math.log2(0.8) + 127 * math.log2(0.75)) / 128
        self.assertAlmostEqual(r["min_entropy_lower"], lower_h, places=14)
        self.assertAlmostEqual(r["min_entropy_upper"], upper_h, places=14)
        self.assertAlmostEqual(r["min_entropy_lower"], 0.018140, places=6)
        self.assertAlmostEqual(r["min_entropy_upper"], 0.414310, places=6)
        self.assertAlmostEqual(r["p-hat_max_upper"], 0.2, places=15)
        self.assertAlmostEqual(r["p-hat_max_lower"], 0.8 * 0.75 ** 127, delta=1e-30)
        # The explicit variants pick the ends.
        self.assertAlmostEqual(estimate([0, 0, 0, 0, 1], 1, undefined_transition="one")["min_entropy"],
                               lower_h, places=14)
        self.assertAlmostEqual(estimate([0, 0, 0, 0, 1], 1, undefined_transition="zero")["min_entropy"],
                               upper_h, places=14)
        self.assertTrue(math.isnan(estimate([0, 0, 0, 0, 1], 1, undefined_transition="nan")["min_entropy"]))

    def test_single_sample_and_empty_input(self):
        # L = 1: P_0 = 1 but every transition is 0/0.  Row 00...0 = 1 x u^127
        # ranges over [0, 1]: undetermined -> NaN, bounds [1.0 (p=0 -> min(inf,1)), 0.0].
        r = estimate([0], 1)
        self.assertEqual(r["P_0"], 1.0)
        self.assertTrue(math.isnan(r["min_entropy"]))
        self.assertEqual(r["min_entropy_lower"], 0.0)
        self.assertEqual(r["min_entropy_upper"], 1.0)
        # L = 0: P_0 = 0/0 -> everything NaN, no exception.
        r = estimate([], 1)
        self.assertEqual(r["L"], 0)
        self.assertTrue(math.isnan(r["P_0"]))
        self.assertTrue(math.isnan(r["min_entropy"]))


class InputHandling(unittest.TestCase):

    def test_to_bitstring_is_msb_first(self):
        self.assertEqual(to_bitstring([0b101, 0b010], 3).tolist(), [1, 0, 1, 0, 1, 0])
        self.assertEqual(to_bitstring([0x80, 0x01], 8).tolist(),
                         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(to_bitstring([1, 0, 1], 1).tolist(), [1, 0, 1])

    def test_bitstring_mode_equals_estimate_on_the_bits(self):
        # [0b101, 0b010] -> 1,0,1,0,1,0: L = 6, alternating -> p-hat_max = 0.5.
        a = estimate([0b101, 0b010], 3, bitstring=True)
        b = estimate([1, 0, 1, 0, 1, 0], 1)
        self.assertEqual(a["L"], 6)
        self.assertEqual(a["min_entropy"], 1 / 128)
        for k in ("P_0", "P_1", "P_{0,0}", "P_{0,1}", "P_{1,0}", "P_{1,1}", "p-hat_max", "min_entropy"):
            self.assertEqual(a[k], b[k], k)
        self.assertEqual(a["mode"], "bitstring")
        self.assertEqual(a["input_symbols"], 2)

    def test_bitstring_limit(self):
        # 0xFF,0x00 -> 16 bits; keeping the first 8 leaves all ones -> min-entropy 0.
        r = estimate([0xFF, 0x00], 8, bitstring=True, bitstring_limit=8)
        self.assertEqual(r["L"], 8)
        self.assertEqual(r["min_entropy"], 0.0)
        r = estimate([0xFF, 0x00], 8, bitstring=True)
        self.assertEqual(r["L"], 16)

    def test_non_binary_literal_is_not_applicable(self):
        r = estimate([0, 1, 2, 1, 0], 8)
        self.assertFalse(r["applicable"])
        self.assertTrue(math.isnan(r["min_entropy"]))
        self.assertTrue(math.isnan(r["P_0"]))
        self.assertEqual(r["distinct_values"], [0, 1, 2])

    def test_two_valued_alphabet_is_binary_by_alphabet_not_by_values(self):
        # {33, 211} is a two-symbol alphabet (section 4.4.2 / section 5).
        sym = [33, 211, 33, 33, 211, 211, 33]
        bits = [0, 1, 0, 0, 1, 1, 0]
        a = estimate(sym, 8)                       # default binary_by='alphabet'
        b = estimate(bits, 1)
        self.assertTrue(a["applicable"])
        self.assertTrue(a["translated"])
        self.assertEqual(a["translation"], {"33": 0, "211": 1})
        for k in ("P_0", "P_1", "P_{0,0}", "P_{0,1}", "P_{1,0}", "P_{1,1}", "min_entropy"):
            self.assertEqual(a[k], b[k], k)
        c = estimate(sym, 8, binary_by="values")   # literal section 6.3.3: si in {0,1}
        self.assertFalse(c["applicable"])
        self.assertTrue(math.isnan(c["min_entropy"]))

    def test_relabelling_invariance(self):
        # The six-row table is symmetric under 0 <-> 1, so complementing the
        # data leaves p-hat_max and the min-entropy unchanged.
        rng = np.random.default_rng(1)
        bits = (rng.random(3000) < 0.3).astype(np.uint8)
        a = estimate(bits, 1)
        b = estimate(1 - bits, 1)
        self.assertEqual(a["min_entropy"], b["min_entropy"])
        self.assertEqual(a["P_0"], b["P_1"])
        self.assertEqual(a["P_{0,0}"], b["P_{1,1}"])

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            estimate([0, 2], 1)
        with self.assertRaises(ValueError):
            estimate([-1, 0], 1)
        with self.assertRaises(ValueError):
            estimate([256], 8)
        with self.assertRaises(ValueError):
            estimate([0], 0)
        with self.assertRaises(ValueError):
            estimate([0], 1, undefined_transition="guess")
        with self.assertRaises(ValueError):
            estimate([0], 1, binary_by="width")

    def test_random_data_invariants(self):
        rng = np.random.default_rng(2026)
        sym = rng.integers(0, 256, size=20000, dtype=np.uint8)
        r = estimate(sym, 8, bitstring=True)
        self.assertEqual(r["L"], 160000)
        self.assertAlmostEqual(r["P_{0,0}"] + r["P_{0,1}"], 1.0, places=12)
        self.assertAlmostEqual(r["P_{1,0}"] + r["P_{1,1}"], 1.0, places=12)
        self.assertTrue(0.0 <= r["min_entropy"] <= 1.0)
        self.assertGreater(r["min_entropy"], 0.95)       # a fair byte stream
        self.assertFalse(r["undefined_transitions_present"])


class CommandLine(unittest.TestCase):

    def _run(self, data: bytes, bps: int, *flags):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "in.bin")
            with open(path, "wb") as f:
                f.write(data)
            proc = subprocess.run([sys.executable, MARKOV_PY, path, str(bps), *flags],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)

    def test_cli_worked_example_literal(self):
        out = self._run(bytes(SPEC_S), 1, "--literal")
        self.assertEqual(out["L"], 40)
        self.assertEqual(round(out["min_entropy"], 3), 0.761)
        self.assertEqual(round(out["P_{0,0}"], 3), 0.389)
        self.assertEqual(out["out_of_width_bytes"], 0)
        self.assertEqual(out["mode"], "literal")

    def test_cli_bitstring_and_masking(self):
        # 8-bit file assessed as a bitstring; bytes 0x80,0x01 -> 16 bits.
        out = self._run(bytes([0x80, 0x01] * 20), 8, "--bitstring")
        self.assertEqual(out["L"], 320)
        self.assertEqual(out["mode"], "bitstring")
        # Declared width 1 with bytes above 1: the low bit is the symbol and
        # the excess is counted, not refused (the harness contract).
        out = self._run(bytes([0x02, 0x03, 0x00, 0x01]), 1, "--literal")
        self.assertEqual(out["out_of_width_bytes"], 2)
        self.assertEqual(out["#{1 in S}"], 2)

    def test_cli_nan_is_emitted_for_undetermined(self):
        out = self._run(bytes([0, 0, 0, 0, 1]), 1)
        self.assertTrue(math.isnan(out["min_entropy"]))
        self.assertAlmostEqual(out["min_entropy_lower"], 0.018140, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
