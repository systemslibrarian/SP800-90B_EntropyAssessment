"""Tests for the differential harness (harness/diff_driver.py, harness/gen_corpus.py).

The harness has no SP 800-90B worked example of its own, so every expected value
here is derived BY HAND in a comment next to the assertion, from the standard's
text (SP 800-90B 3.1.3, PDF p. 20; 6.2, PDF p. 49) or from the construction of
the input.  Reference estimators are replaced by stubs: the point is to test the
harness's parsing, comparison, combination and corpus construction, not any
estimator.

Run:  <venv>/bin/python -m unittest reference/py90b/tests/test_diff_driver.py
"""
from __future__ import annotations

import math
import os
import random
import sys
import tempfile
import unittest

import numpy as np

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "..", ".."))
HARNESS_DIR = os.path.join(AUDIT_DIR, "harness")
if HARNESS_DIR not in sys.path:
    sys.path.insert(0, HARNESS_DIR)

import diff_driver as dd  # noqa: E402
import gen_corpus as gc  # noqa: E402


def load_capture() -> str:
    with open(dd.LABEL_CAPTURE, "r", encoding="utf-8") as f:
        return f.read()


# ----------------------------------------------------------------------------
# parsing the C++ verbose text by label
# ----------------------------------------------------------------------------

class TestParse(unittest.TestCase):
    def test_label_capture_values(self):
        # Values read off reference/cpp-verbose-labels-non_iid.txt, which is a genuine
        # ea_non_iid -v -v output on ../bin/rand8_short.bin (10000 samples, 8 bits).
        p = dd.parse_cpp_text(load_capture())
        self.assertEqual(p["n"], 10000)
        self.assertEqual(p["k"], 256)
        self.assertEqual(p["width"], 8)
        self.assertEqual(p["n_binary"], 80000)
        self.assertEqual(p["loaded_sha256"], "17d2eaf9544cd6aea3e245bec362f494376d0b1ca6140c475a35f1ad1f8c2803")
        lit_mcv = p["estimates"]["Literal"]["Most Common Value"]
        self.assertEqual(lit_mcv["Mode count"]["value"], 58)
        self.assertIsInstance(lit_mcv["Mode count"]["value"], int)
        self.assertEqual(lit_mcv["p_u"]["value"], 0.0077560937775866317)
        self.assertEqual(lit_mcv["min entropy"]["value"], 7.0104540377360411)
        self.assertEqual(p["estimates"]["Bitstring"]["Collision"]["v"]["value"], 32005)
        self.assertEqual(p["estimates"]["Bitstring"]["Collision"]["X-bar'"]["value"], 2.4923789816296962)
        self.assertEqual(p["estimates"]["Bitstring"]["Markov"]["P_{0,1}"]["value"], 0.49921444425048012)
        self.assertEqual(p["estimates"]["Literal"]["Lag Prediction"]["P_local"]["value"], 0.010051528494081152)
        self.assertEqual(p["H_original"], 6.6364412870612322)
        self.assertEqual(p["H_bitstring"], 0.73261171806065617)
        self.assertEqual(p["H_bitstring Per Symbol"], 5.8608937444852494)
        self.assertEqual(p["assessed"], 5.8608937444852494)
        # free-text lines are notes, never values
        self.assertIn("P_local can't change the result.", p["notes"]["Literal"]["MultiMCW Prediction"])
        self.assertIn("Found p.", p["notes"]["Bitstring"]["Collision"])
        self.assertEqual(p["unparsed_estimate_lines"], [])
        self.assertEqual(len(p["warnings"]), 3)

    def test_parse_by_label_not_position(self):
        text = load_capture()
        lines = text.splitlines()
        random.Random(7).shuffle(lines)
        a, b = dd.parse_cpp_text(text), dd.parse_cpp_text("\n".join(lines))
        self.assertEqual(a["estimates"], b["estimates"])
        self.assertEqual(a["assessed"], b["assessed"])
        self.assertEqual(a["H_original"], b["H_original"])

    def test_parse_number_and_printed_precision(self):
        self.assertEqual(dd.parse_number("40099"), 40099)
        self.assertIsInstance(dd.parse_number("40099"), int)
        self.assertEqual(dd.parse_number("-0"), 0)
        self.assertTrue(math.isnan(dd.parse_number("nan")))
        self.assertEqual(dd.parse_number("3.5960141043503829e-39"), 3.5960141043503829e-39)
        self.assertIsNone(dd.parse_number("Found"))
        # half a unit in the last printed place
        self.assertAlmostEqual(dd.printed_half_ulp("0.0057999999999999996"), 0.5e-19, delta=1e-30)
        self.assertEqual(dd.printed_half_ulp("40099"), 0.0)
        self.assertAlmostEqual(dd.printed_half_ulp("0.847017"), 0.5e-6)
        self.assertAlmostEqual(dd.printed_half_ulp("3.5960141043503829e-39") / 0.5e-55, 1.0, places=6)

    def test_canon_key(self):
        self.assertEqual(dd.canon_key("min entropy"), "min_entropy")
        self.assertEqual(dd.canon_key("Mode count"), "mode_count")
        self.assertEqual(dd.canon_key("X-bar'"), "x_bar'")
        self.assertEqual(dd.canon_key("X_bar_prime"), "x_bar'")
        self.assertNotEqual(dd.canon_key("X-bar"), dd.canon_key("X-bar'"))
        self.assertEqual(dd.canon_key("P_global'"), dd.canon_key("P_global_prime"))
        self.assertEqual(dd.canon_key("P_{0,0}"), "p_{0,0}")
        self.assertEqual(dd.canon_key("p-hat_max"), "p_hat_max")
        self.assertNotEqual(dd.canon_key("p-hat"), dd.canon_key("p-hat_max"))


# ----------------------------------------------------------------------------
# input contract: low bits, bitstring conversion, binary rule, translation
# ----------------------------------------------------------------------------

class TestInput(unittest.TestCase):
    def test_bitstring_msb_first(self):
        # 0xA5 = 1010 0101 -> MSB-first bits 1,0,1,0,0,1,0,1 (3.1.3: the L samples of n bits are
        # 'considered as a bitstring of size nL'; the order is a convention, MSB-first here)
        self.assertEqual(dd.to_bitstring(np.array([0xA5], np.uint8), 8).tolist(), [1, 0, 1, 0, 0, 1, 0, 1])
        # 6 at 3 bits = 110 -> MSB-first 1,1,0 ; LSB-first 0,1,1
        self.assertEqual(dd.to_bitstring(np.array([6], np.uint8), 3).tolist(), [1, 1, 0])
        self.assertEqual(dd.to_bitstring(np.array([6], np.uint8), 3, "lsb").tolist(), [0, 1, 1])
        self.assertEqual(dd.to_bitstring(np.array([0, 1], np.uint8), 1).tolist(), [0, 1])
        self.assertEqual(len(dd.to_bitstring(np.zeros(10, np.uint8), 8)), 80)

    def test_low_bits_mask_and_overwidth_count(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.bin")
            with open(p, "wb") as f:
                f.write(bytes([0, 1, 2, 3]))
            sym, info = dd.read_symbols(p, 1)
            # low 1 bit of 0,1,2,3 = 0,1,0,1 ; two bytes (2 and 3) exceed width 1 ; raw max 3
            self.assertEqual(sym.tolist(), [0, 1, 0, 1])
            self.assertEqual(info["overwidth_count"], 2)
            self.assertEqual(info["raw_max"], 3)
            self.assertTrue(info["masked"])
            sym8, info8 = dd.read_symbols(p, 8)
            self.assertEqual(sym8.tolist(), [0, 1, 2, 3])
            self.assertEqual(info8["overwidth_count"], 0)

    def test_binary_rule_and_translation(self):
        two = np.array([0, 255, 255, 0, 255], np.uint8)
        b, k = dd.is_binary(two, 8, "observed")
        self.assertTrue(b)
        self.assertEqual(k, 2)
        b2, _ = dd.is_binary(two, 8, "declared")
        self.assertFalse(b2)
        t, info = dd.translate_binary(two)
        self.assertEqual(t.tolist(), [0, 1, 1, 0, 1])  # ascending value -> 0,1
        self.assertEqual(info["map"], {0: 0, 255: 1})
        three = np.array([0, 1, 2], np.uint8)
        self.assertFalse(dd.is_binary(three, 8, "observed")[0])
        one = np.zeros(5, np.uint8)
        self.assertTrue(dd.is_binary(one, 8, "observed")[0])   # degenerate k = 1 folded into binary
        # which modules apply (6.2: Collision, Markov, Compression only on binary inputs)
        self.assertEqual(set(dd.applicable_modules("literal", False)), set(dd.ESTIMATOR_BY_MODULE) - dd.BINARY_ONLY)
        self.assertEqual(set(dd.applicable_modules("literal", True)), set(dd.ESTIMATOR_BY_MODULE))
        self.assertEqual(set(dd.applicable_modules("bitstring", False)), set(dd.ESTIMATOR_BY_MODULE))


# ----------------------------------------------------------------------------
# comparison and classification
# ----------------------------------------------------------------------------

CPP = {"mode_count": 58, "p_hat": 0.0058, "p_u": 0.0077560937775866317, "min_entropy": 7.0104540377360411}
CPP_TEXT = {"mode_count": "58", "p_hat": "0.0057999999999999996", "p_u": "0.0077560937775866317",
            "min_entropy": "7.0104540377360411"}


def ref_with(**changes):
    v = dict(CPP)
    v.update(changes)
    return {"status": "ok", "values": v}


class TestCompare(unittest.TestCase):
    def test_agree(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with())
        self.assertEqual(c["class"], "AGREE")
        self.assertEqual(len(c["intermediates"]), 3)

    def test_cpp_higher_is_flagged(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(min_entropy=CPP["min_entropy"] - 1e-6))
        self.assertEqual(c["class"], "CPP_HIGHER")
        self.assertTrue(c["reason"].startswith("!!!"))
        self.assertNotIn("hint", c)  # only the minimum differs: not the shape of D-1, so no hint
        # the D-1 shape: the minimum AND p_u differ, and nothing else
        c2 = dd.compare_estimator(CPP, CPP_TEXT, ref_with(min_entropy=CPP["min_entropy"] - 1e-6, p_u=CPP["p_u"] + 1e-7))
        self.assertEqual(c2["class"], "CPP_HIGHER")
        self.assertIn("hint", c2)

    def test_cpp_lower(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(min_entropy=CPP["min_entropy"] + 1e-6))
        self.assertEqual(c["class"], "CPP_LOWER")

    def test_within_tolerance_agrees(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(min_entropy=CPP["min_entropy"] - 1e-10, p_u=CPP["p_u"] + 5e-10))
        self.assertEqual(c["class"], "AGREE")

    def test_intermediate_float_diff(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(p_u=CPP["p_u"] + 1e-6))
        self.assertEqual(c["class"], "INTERMEDIATE_DIFF")
        self.assertIn("p_u", c["reason"])

    def test_integer_count_is_exact(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(mode_count=59))
        self.assertEqual(c["class"], "INTERMEDIATE_DIFF")
        rec = [i for i in c["intermediates"] if i["key"] == "mode_count"][0]
        self.assertEqual(rec["kind"], "integer-exact")
        self.assertEqual(rec["tol"], 0.0)

    def test_tolerance_widens_to_printed_precision(self):
        # a value printed with six decimals cannot be compared tighter than 0.5e-6 (rule 16)
        c = dd.compare_value("min_entropy", 0.847017, 0.8470171234, "0.847017")
        self.assertEqual(c["status"], "agree")
        self.assertTrue(c.get("tol_widened_to_printed_precision"))
        c2 = dd.compare_value("min_entropy", 0.847017, 0.8470171234, "0.84701700000000000")
        self.assertEqual(c2["status"], "differ")

    def test_not_run_variants_are_never_agreement(self):
        self.assertEqual(dd.compare_estimator(CPP, CPP_TEXT, {"status": "missing", "values": None, "error": "x"})["class"], "NOT_RUN")
        self.assertEqual(dd.compare_estimator(None, {}, ref_with())["class"], "NOT_RUN")
        self.assertEqual(dd.compare_estimator(CPP, CPP_TEXT, ref_with(min_entropy=float("nan")))["class"], "NOT_RUN")
        self.assertEqual(dd.compare_estimator(None, {}, {"status": "missing", "values": None})["class"], "NOT_RUN")
        no_me = {k: v for k, v in CPP.items() if k != "min_entropy"}
        self.assertEqual(dd.compare_estimator(no_me, CPP_TEXT, ref_with())["class"], "NOT_RUN")

    def test_unmatched_keys_recorded_not_compared(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(P_local=0.5))
        self.assertEqual(c["class"], "AGREE")
        self.assertEqual(c["unmatched"]["ref_only"], ["p_local"])

    def test_case_class(self):
        per = {"a": {"class": "AGREE", "reason": ""}, "b": {"class": "NOT_RUN", "reason": "missing"}}
        self.assertEqual(dd.case_class(per)[0], "AGREE")
        per["c"] = {"class": "CPP_LOWER", "reason": ""}
        self.assertEqual(dd.case_class(per)[0], "CPP_LOWER")
        per["d"] = {"class": "CPP_HIGHER", "reason": ""}
        self.assertEqual(dd.case_class(per)[0], "CPP_HIGHER")
        only_nr = {"a": {"class": "NOT_RUN", "reason": "x"}}
        self.assertEqual(dd.case_class(only_nr)[0], "NOT_RUN")

    def test_compare_overall_incomplete_reference(self):
        # with a module missing, a higher C++ figure IS established (more modules only lower the
        # reference minimum); a lower or equal one is NOT
        hi = dd.compare_overall("Assessed min entropy", 1.0 + 1e-6, 1.0, False, None, ["lz78y"])
        self.assertEqual(hi["class"], "CPP_HIGHER")
        lo = dd.compare_overall("Assessed min entropy", 1.0 - 1e-6, 1.0, False, None, ["lz78y"])
        self.assertEqual(lo["class"], "NOT_RUN")
        eq = dd.compare_overall("Assessed min entropy", 1.0, 1.0, False, None, ["lz78y"])
        self.assertEqual(eq["class"], "NOT_RUN")
        eq2 = dd.compare_overall("Assessed min entropy", 1.0, 1.0, True, None, [])
        self.assertEqual(eq2["class"], "AGREE")
        lo2 = dd.compare_overall("Assessed min entropy", 1.0 - 1e-6, 1.0, True, None, [])
        self.assertEqual(lo2["class"], "CPP_LOWER")

    def test_cpp_internal_checks_on_capture_and_on_a_mutation(self):
        p = dd.parse_cpp_text(load_capture())
        checks = dd.cpp_internal_checks(p, 8, 10000, p["loaded_sha256"])
        self.assertTrue(checks)
        self.assertTrue(all(c["ok"] for c in checks), [c for c in checks if not c["ok"]])
        # Assessed raised above the minimum of its own printed estimates must be caught
        p["assessed"] = 7.5
        bad = {c["check"] for c in dd.cpp_internal_checks(p, 8, 10000, p["loaded_sha256"]) if not c["ok"]}
        self.assertIn("assessed_not_above_printed_min", bad)
        self.assertIn("assessed_equals_min_of_summary_terms", bad)


# ----------------------------------------------------------------------------
# the 3.1.3 combination, with stub estimators (hand-derived)
# ----------------------------------------------------------------------------

class Stub:
    """A stand-in estimator: returns `by_bps[bps]` as min_entropy and records what it was fed."""

    def __init__(self, by_bps):
        self.by_bps = by_bps
        self.calls = []

    def estimate(self, symbols, bps, **options):
        self.calls.append((np.asarray(symbols).copy(), bps, options))
        v = self.by_bps.get(bps, float("nan"))
        return {"min_entropy": v, "N": int(len(symbols))}


def stubs(**by_name):
    """All ten modules stubbed; unnamed ones return nan (= 'spec gives no value')."""
    out = {m: Stub({}) for m, _ in dd.MODULES}
    for name, by_bps in by_name.items():
        out[name] = Stub(by_bps)
    return out


class TestCombine(unittest.TestCase):
    def test_non_binary_eight_bit_hand_derived(self):
        # 8-bit data with many distinct symbols -> not binary.
        # literal: mcv 1.5, lag 0.7           -> H_original = min(1.5, 0.7) = 0.7
        # bitstring (bps 1): mcv 0.9, lag 0.95 -> H_bitstring = 0.9 ; per symbol = 8 x 0.9 = 7.2
        # 3.1.3: H_I = min(H_original, n x H_bitstring) = min(0.7, 7.2) = 0.7
        sym = np.arange(256, dtype=np.uint8)
        mods = stubs(mcv={8: 1.5, 1: 0.9}, lag={8: 0.7, 1: 0.95})
        out = dd.estimate(sym, 8, modules=mods)
        self.assertFalse(out["is_binary"])
        self.assertEqual(out["H_original"], 0.7)
        self.assertEqual(out["H_bitstring"], 0.9)
        self.assertAlmostEqual(out["H_bitstring Per Symbol"], 7.2)
        self.assertEqual(out["Assessed min entropy"], 0.7)
        self.assertEqual(out["min_entropy"], 0.7)
        self.assertEqual(out["binding"], {"literal": "lag", "bitstring": "mcv"})
        # binary-only estimators were not called on the literal symbols (6.2), but were on the bits
        self.assertEqual([bps for _, bps, _ in mods["collision"].calls], [1])
        self.assertEqual(len(mods["mcv"].calls[1][0]), 256 * 8)  # bitstring length nL = 2048

    def test_bitstring_term_binds_hand_derived(self):
        # literal mcv 7.9 ; bitstring mcv 0.5 -> per symbol 8 x 0.5 = 4.0 ; H_I = min(7.9, 4.0) = 4.0
        sym = np.arange(256, dtype=np.uint8)
        out = dd.estimate(sym, 8, modules=stubs(mcv={8: 7.9, 1: 0.5}))
        self.assertEqual(out["Assessed min entropy"], 4.0)

    def test_degenerate_all_one_symbol_binary(self):
        # all zeros at width 1: p_hat = 1, p_u = 1, MCV min-entropy = -log2(1) = 0 (6.3.1); binary source,
        # so 3.1.3 has no bitstring term: H_I = H_original = 0
        sym = np.zeros(1000, np.uint8)
        mods = stubs(mcv={1: 0.0})
        out = dd.estimate(sym, 1, modules=mods)
        self.assertTrue(out["is_binary"])
        self.assertEqual(out["k"], 1)
        self.assertEqual(out["H_original"], 0.0)
        self.assertIsNone(out["H_bitstring"])
        self.assertEqual(out["Assessed min entropy"], 0.0)
        self.assertNotIn("bitstring", out["estimators"])

    def test_two_symbol_eight_bit_is_translated_binary(self):
        # {0, 255} at declared width 8: binary by the observed rule, so the three binary-only
        # estimators run on the translated {0,1} data at bps 1 and there is no bitstring term
        sym = np.array([0, 255] * 50, np.uint8)
        mods = stubs(mcv={1: 0.99}, collision={1: 0.8})
        out = dd.estimate(sym, 8, modules=mods)
        self.assertTrue(out["is_binary"])
        fed, bps, _ = mods["collision"].calls[0]
        self.assertEqual(bps, 1)
        self.assertEqual(sorted(set(fed.tolist())), [0, 1])
        self.assertEqual(out["Assessed min entropy"], 0.8)
        self.assertIsNone(out["H_bitstring"])
        # under the declared rule the same data is NOT binary: no translation, bitstring term present
        mods2 = stubs(mcv={8: 0.99, 1: 0.6})
        out2 = dd.estimate(sym, 8, modules=mods2, binary_rule="declared")
        self.assertFalse(out2["is_binary"])
        self.assertAlmostEqual(out2["H_bitstring Per Symbol"], 4.8)   # 8 x 0.6
        self.assertAlmostEqual(out2["Assessed min entropy"], 0.99)   # min(0.99, 4.8)

    def test_missing_module_makes_result_incomplete_never_agreement(self):
        class Boom:
            def estimate(self, symbols, bps, **o):
                raise RuntimeError("simulated reference failure")

        sym = np.arange(256, dtype=np.uint8)
        mods = stubs(mcv={8: 1.5, 1: 0.9})
        mods["lrs"] = Boom()
        out = dd.estimate(sym, 8, modules=mods)
        self.assertFalse(out["complete"])
        self.assertIn("lrs", out["not_run"]["literal"])
        self.assertEqual(out["H_original"], 1.5)
        # reference_minimum: a nan from an applicable module is 'declined', not a value
        rm = dd.reference_minimum({"mcv": {"status": "ok", "values": {"min_entropy": float("nan")}},
                                   "lag": {"status": "ok", "values": {"min_entropy": 0.4}}}, ["mcv", "lag", "lrs"])
        self.assertEqual(rm["declined"], ["mcv"])
        self.assertEqual(rm["missing"], ["lrs"])
        self.assertEqual(rm["min"], 0.4)
        self.assertFalse(rm["complete"])


# ----------------------------------------------------------------------------
# the self-check (rule 7): the comparison can fail
# ----------------------------------------------------------------------------

class TestSelfCheck(unittest.TestCase):
    def test_self_check_passes_on_label_capture(self):
        out = dd.self_check(write=False)
        failing = [r for r in out["rows"] if not r["ok"]]
        self.assertTrue(out["ok"], failing)
        steps = {r["expected"] for r in out["rows"]}
        for cls in ("AGREE", "CPP_HIGHER", "CPP_LOWER", "INTERMEDIATE_DIFF", "NOT_RUN", "TOOL_REFUSED"):
            self.assertIn(cls, steps)


# ----------------------------------------------------------------------------
# corpus generator
# ----------------------------------------------------------------------------

class TestGenCorpus(unittest.TestCase):
    def test_keystream_deterministic_and_label_separated(self):
        a, b = gc.keystream("x", 100), gc.keystream("x", 100)
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, gc.keystream("y", 100)))
        self.assertEqual(len(gc.keystream_bits("x", 37)), 37)

    def test_minimal_period(self):
        self.assertEqual(gc.minimal_period(np.array([0, 1, 0, 1])), 2)
        self.assertEqual(gc.minimal_period(np.array([0, 0, 1])), 3)
        self.assertEqual(gc.minimal_period(np.array([0, 0, 0])), 1)

    def test_lfsr16_period_is_65535_and_not_a_proper_divisor(self):
        # x^16+x^14+x^13+x^11+1 is primitive: period 2^16-1 = 65535 = 3*5*17*257.  The output
        # sequence must repeat at 65535 and at none of 65535/3, /5, /17, /257 (any proper period
        # divides one of those).
        P = 65535
        bits, lows = gc.lfsr_run(gc.LFSRS["lfsr16"], 2 * P + 64)
        self.assertTrue(np.array_equal(bits[:P + 64], bits[P:2 * P + 64]))
        for q in (3, 5, 17, 257):
            d = P // q
            self.assertFalse(np.array_equal(bits[:d], bits[d:2 * d]), f"period divides {d}")
        # the low byte is the sliding 8-bit window of the output sequence (bit k of state = b[t+k])
        t = 100
        window = sum(int(bits[t + k]) << k for k in range(8))
        self.assertEqual(int(lows[t]), window)

    def test_two9010_proportion(self):
        sym, bps, _ = gc.fam_two9010(1)
        p0 = float(np.mean(sym == 0))
        # exact P(0) = 0.9 by construction; binomial sd at 1e6 = sqrt(0.09/1e6) = 0.0003
        self.assertAlmostEqual(p0, 0.9, delta=0.002)
        self.assertEqual(sorted(set(sym.tolist())), [0, 1])
        sym8, _, _ = gc.fam_two9010(8)
        self.assertEqual(sorted(set(sym8.tolist())), [0, 255])

    def test_periodic_families_have_exact_period(self):
        for p, w in ((2, 1), (3, 1), (7, 1), (1023, 1), (7, 8), (256, 8), (1000, 8), (4096, 8)):
            sym, bps, how = gc.make_periodic(p, w)
            self.assertEqual(gc.minimal_period(sym[:p]), p, (p, w, how))
            self.assertTrue(np.array_equal(sym[:gc.NMAX - p], sym[p:]), (p, w))
            self.assertLessEqual(int(sym.max()), (1 << w) - 1)

    def test_runs_counters_alternating(self):
        sym, _, _ = gc.fam_runs(10, 8)
        self.assertTrue(np.all(sym[0:10] == 0) and np.all(sym[10:20] == 1))
        self.assertTrue(np.all(sym[2550:2560] == 255) and np.all(sym[2560:2570] == 0))
        sym1, _, _ = gc.fam_runs(10000, 1)
        self.assertTrue(np.all(sym1[:10000] == 0) and np.all(sym1[10000:20000] == 1))
        c3, _, _ = gc.fam_counter3(8)
        self.assertEqual(int(c3[1]), 3)
        self.assertEqual(int(c3[86]), (3 * 86) % 256)  # 258 mod 256 = 2
        alt, _, _ = gc.fam_alternating(8)
        self.assertEqual(alt[:4].tolist(), [0, 255, 0, 255])
        cnt, _, _ = gc.fam_counter(1)
        self.assertEqual(cnt[:4].tolist(), [0, 1, 0, 1])

    def test_overwidth_and_onesym(self):
        sym, bps, _ = gc.fam_overwidth(1)
        self.assertEqual(bps, 1)
        self.assertEqual(int(sym.max()), 3)
        sym7, bps7, _ = gc.fam_overwidth(8)
        self.assertEqual(bps7, 7)
        self.assertEqual(int(sym7.max()), 255)
        z, _, _ = gc.fam_onesym0(8)
        self.assertEqual(int(z.max()), 0)
        m, _, _ = gc.fam_onesymmax(1)
        self.assertEqual(set(m.tolist()), {1})

    def test_lfsr_families_pack_consistently(self):
        bits, lows = gc.lfsr_run(gc.LFSRS["lfsr16"], 64)
        gc._LFSR_CACHE["lfsr16"] = gc.lfsr_run(gc.LFSRS["lfsr16"], 8 * 64)  # small cache for the test
        try:
            tap1_8, _, _ = gc.fam_lfsr("lfsr16", "tap1", 8)
            self.assertEqual(int(tap1_8[0]), int(np.packbits(bits[:8])[0]))
            tap1_1, _, _ = gc.fam_lfsr("lfsr16", "tap1", 1)
            self.assertEqual(tap1_1[:64].tolist(), bits.tolist())
            tap8_8, _, _ = gc.fam_lfsr("lfsr16", "tap8", 8)
            self.assertEqual(tap8_8[:64].tolist(), lows.tolist())
            tap8_1, _, _ = gc.fam_lfsr("lfsr16", "tap8", 1)
            self.assertEqual(tap8_1[:8].tolist(), np.unpackbits(lows[:1]).tolist())
        finally:
            gc._LFSR_CACHE.pop("lfsr16", None)

    def test_plan_count(self):
        # 26 families x 2 widths x 3 sizes + 2 smoke files = 158
        items = gc.plan(set(), (1, 8), gc.SIZES, smoke=True)
        self.assertEqual(len(items), 26 * 2 * 3 + 2)
        names = {(f, w) for f, w, _, _ in items}
        self.assertEqual(len(names), 52)

    def test_write_manifest_check_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            rc = gc.main(["--out", d, "--families", "csprng", "--sizes", "5000", "--no-smoke"])
            self.assertEqual(rc, 0)
            rows = gc.read_manifest(os.path.join(d, gc.MANIFEST_NAME))
            self.assertEqual(sorted(rows), ["csprng-1bit-5000.bin", "csprng-8bit-5000.bin"])
            self.assertEqual(os.path.getsize(os.path.join(d, "csprng-8bit-5000.bin")), 5000)
            self.assertEqual(gc.main(["--out", d, "--check"]), 0)
            sha_before = rows["csprng-8bit-5000.bin"]["sha256"]
            # regenerate: byte-identical, and a foreign manifest row survives the merge
            with open(os.path.join(d, gc.MANIFEST_NAME), "a") as f:
                f.write("foreign.bin\t8\t10\t" + "0" * 64 + "\tsomeone else's file\n")
            gc.main(["--out", d, "--families", "csprng", "--sizes", "5000", "--no-smoke"])
            rows2 = gc.read_manifest(os.path.join(d, gc.MANIFEST_NAME))
            self.assertEqual(rows2["csprng-8bit-5000.bin"]["sha256"], sha_before)
            self.assertIn("foreign.bin", rows2)
            # a corrupted file is caught by --check
            with open(os.path.join(d, "csprng-1bit-5000.bin"), "r+b") as f:
                f.seek(0)
                b = f.read(1)
                f.seek(0)
                f.write(bytes([b[0] ^ 1]))
            self.assertEqual(gc.main(["--out", d, "--check"]), 1)


# ----------------------------------------------------------------------------
# result-file round trip
# ----------------------------------------------------------------------------

class TestJsonRoundTrip(unittest.TestCase):
    def test_sanitize_desanitize(self):
        obj = {"a": float("nan"), "b": [np.float64(1.5), np.int64(3), np.bool_(True)], "c": float("inf"),
               "d": np.array([1, 2])}
        s = dd.sanitize(obj)
        self.assertEqual(s["a"], "NaN")
        self.assertEqual(s["b"], [1.5, 3, True])
        self.assertEqual(s["c"], "Infinity")
        self.assertEqual(s["d"], [1, 2])
        back = dd.desanitize(s)
        self.assertTrue(math.isnan(back["a"]))
        self.assertEqual(back["c"], float("inf"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json")
            dd.write_json(p, obj)
            r = dd.read_json(p)
            self.assertTrue(math.isnan(r["a"]))


# ----------------------------------------------------------------------------
# the D-1 recheck (documented divergence: binary64 quantile vs the printed 2.576)
# ----------------------------------------------------------------------------

class TestD1Recheck(unittest.TestCase):
    def test_d1_candidate_shape(self):
        # D-1 moves only the quantities downstream of the 2.576 constant, by a small amount
        self.assertTrue(dd.d1_candidate(["p_u"], 2.9e-5))
        self.assertTrue(dd.d1_candidate(["p", "x_bar'"], 4.9e-6))
        self.assertFalse(dd.d1_candidate(["p_u", "mode_count"], 2.9e-5))  # an integer count differs: not D-1
        self.assertFalse(dd.d1_candidate(["p_u"], 0.01))                 # too large to be the constant
        self.assertFalse(dd.d1_candidate([], 1e-6))                      # nothing differs

    def test_d1_recheck_record(self):
        rerun_ok = {"status": "ok", "values": dict(CPP)}  # the z-exact rerun reproduces the C++ exactly
        r = dd.d1_recheck_record(CPP, CPP_TEXT, rerun_ok, ("z", dd.Z_EXACT))
        self.assertTrue(r["possible"])
        self.assertTrue(r["explained"])
        self.assertEqual(r["class_after"], "AGREE")
        self.assertEqual(r["option"], {"z": 2.5758293035489008})
        residual = {"status": "ok", "values": {**CPP, "min_entropy": CPP["min_entropy"] - 1e-6}}
        r2 = dd.d1_recheck_record(CPP, CPP_TEXT, residual, ("z", dd.Z_EXACT))
        self.assertFalse(r2["explained"])
        self.assertEqual(r2["class_after"], "CPP_HIGHER")
        err = {"status": "error", "values": None, "error": "TypeError: estimate() got an unexpected keyword argument 'z'"}
        r3 = dd.d1_recheck_record(CPP, CPP_TEXT, err, ("z", dd.Z_EXACT))
        self.assertFalse(r3["possible"])
        self.assertIn("does not accept", r3["error"])

    def test_verdict_tags_and_d1_explained_all(self):
        c = dd.compare_estimator(CPP, CPP_TEXT, ref_with(min_entropy=CPP["min_entropy"] - 2e-6, p_u=CPP["p_u"] + 1e-7))
        self.assertEqual(c["class"], "CPP_HIGHER")
        self.assertIn("hint", c)
        c["d1_recheck"] = dd.d1_recheck_record(CPP, CPP_TEXT, {"status": "ok", "values": dict(CPP)}, ("z", dd.Z_EXACT))
        comps = {"mcv": c, "lag": {"class": "NOT_RUN", "reason": "missing", "intermediates": []}}
        self.assertTrue(dd.d1_explained_all(comps, "CPP_HIGHER"))
        rec = {"d1_explained": True, "non_compliant_short_dataset": True}
        v = dd.build_verdict("case-x", "CPP_HIGHER", "cpp_higher 1, not_run 1", comps, rec)
        self.assertIn("!!! CPP_HIGHER", v)
        self.assertIn("mcv (+2e-06; p_u D-1)", v)
        self.assertIn("ALL explained by documented divergence D-1", v)
        self.assertTrue(v.endswith("[EA_ALLOW_SHORT_DATASET=1]"))
        # a residual after the recheck: not explained
        c2 = dict(c)
        c2["d1_recheck"] = dd.d1_recheck_record(
            CPP, CPP_TEXT, {"status": "ok", "values": {**CPP, "min_entropy": CPP["min_entropy"] - 1e-6}}, ("z", dd.Z_EXACT))
        self.assertFalse(dd.d1_explained_all({"mcv": c2}, "CPP_HIGHER"))
        v2 = dd.build_verdict("case-y", "CPP_HIGHER", "cpp_higher 1", {"mcv": c2}, {"d1_explained": False})
        self.assertIn("not-D-1", v2)
        self.assertIn("NOT all explained", v2)
        # no recheck ran: undetermined, not explained
        c3 = dict(c)
        del c3["d1_recheck"]
        self.assertIsNone(dd.d1_explained_all({"mcv": c3}, "CPP_HIGHER"))
        self.assertIsNone(dd.d1_explained_all({"mcv": c}, "AGREE"))

    def test_merge_d1_substitutes_only_successful_reruns(self):
        ref = {"mcv": {"status": "ok", "values": {"min_entropy": 1.0}}, "lag": {"status": "ok", "values": {"min_entropy": 2.0}}}
        d1 = {"mcv": {"status": "ok", "values": {"min_entropy": 1.5}}, "lag": {"status": "error", "values": None}}
        merged = dd._merge_d1(ref, d1)
        self.assertEqual(merged["mcv"]["values"]["min_entropy"], 1.5)
        self.assertEqual(merged["lag"]["values"]["min_entropy"], 2.0)
        self.assertEqual(dd._merge_d1(ref, None), ref)


if __name__ == "__main__":
    unittest.main()
