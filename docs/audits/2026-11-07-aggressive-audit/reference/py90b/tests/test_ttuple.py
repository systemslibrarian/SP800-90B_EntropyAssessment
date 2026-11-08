"""Tests for py90b.ttuple, SP 800-90B section 6.3.5 (PDF pp. 55-56).

Runs under pytest or directly:  python test_ttuple.py   (plain asserts, exit status 1 on failure).
Every expected number is either quoted from the standard's worked example or derived BY HAND in
a comment next to the assertion.
"""

from __future__ import annotations

import json
import math
import os
import random
import subprocess
import sys
import tempfile
import traceback
from collections import Counter
from decimal import Decimal, getcontext

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REFERENCE_DIR = os.path.dirname(os.path.dirname(_HERE))      # .../reference
if _REFERENCE_DIR not in sys.path:
    sys.path.insert(0, _REFERENCE_DIR)

from py90b import ttuple                                      # noqa: E402
from py90b.ttuple import (                                    # noqa: E402
    Z_EXACT, Z_LITERAL, estimate, most_common_tuple_count_literal, to_bitstring,
    _lcp_kasai, _suffix_array, _tuple_counts_all_suffix_array,
)

ALL_METHODS = ("literal", "direct", "suffix_array", "auto")


def close(a, b, tol):
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol


# --------------------------------------------------------------------------------------------
# The standard's own worked example (SP 800-90B section 6.3.5, PDF p. 56), quoted:
#   "For the purpose of this example, suppose that the cutoff is 3 instead of 35 in step one.
#    Suppose that S = (2, 2, 0, 1, 0, 2, 0, 1, 2, 1, 2, 0, 1, 2, 1, 0, 0, 1, 0, 0, 0), and L = 21.
#    The number of occurrences of the most common 4-tuple is 2, which falls below the threshold,
#    and therefore t = 3.  In step 2, Q[1] = 9, Q[2] = 4, and Q[3] = 3.  P[1] = 0.4286,
#    P[2] = 0.2, P[3] = 0.1579.  Pmax[1] = 0.4286, Pmax[2] = 0.4472, Pmax[3] = 0.5405, and
#    p-hat_max = 0.5405.  The upper bound of a 99 % confidence interval is 0.8276.  The
#    min-entropy estimate is -log2(0.8276) = 0.273."
# Step 2's own example (same S): "Q[1] = max(#0's, #1's, #2's) = #0's = 9, and Q[2] = 4 is
# obtained by the number of the tuple 01 in S."
# --------------------------------------------------------------------------------------------
SPEC_S = [2, 2, 0, 1, 0, 2, 0, 1, 2, 1, 2, 0, 1, 2, 1, 0, 0, 1, 0, 0, 0]


def test_spec_example_counts_by_hand():
    # By hand on SPEC_S (1-based positions):
    #   0 at positions 3,5,7,12,16,17,19,20,21 -> 9;  1 at 4,8,10,13,15,18 -> 6;  2 at 1,2,6,9,11,14 -> 6.
    #   pairs: "01" at 3,7,12,17 -> 4; "20","12","10","00" -> 3 each; "21" -> 2; "02","22" -> 1.
    #   triples: "201" at 2,6,11 -> 3; "012","010","121","100" -> 2 each.
    #   4-tuples: "2012" at 6,11 -> 2, "0121" at 7,12 -> 2, "2010" at 2 only; max 2.
    assert len(SPEC_S) == 21
    assert Counter(SPEC_S)[0] == 9
    assert most_common_tuple_count_literal(SPEC_S, 1) == 9
    assert most_common_tuple_count_literal(SPEC_S, 2) == 4
    assert most_common_tuple_count_literal(SPEC_S, 3) == 3
    assert most_common_tuple_count_literal(SPEC_S, 4) == 2
    assert most_common_tuple_count_literal(SPEC_S, 21) == 1
    assert most_common_tuple_count_literal(SPEC_S, 22) == 0


def test_spec_worked_example_all_methods():
    for method in ALL_METHODS:
        r = estimate(SPEC_S, 2, cutoff=3, method=method)
        assert r["t"] == 3, (method, r)
        assert r["Q"] == [9, 4, 3], (method, r)
        assert r["Q_next"] == 2, (method, r)                       # "the most common 4-tuple is 2"
        assert r["L"] == 21
        # The text prints four decimals; tolerance half a unit in the fourth place.
        for got, want in zip(r["P"], [0.4286, 0.2, 0.1579]):
            assert close(got, want, 5e-5), (method, r["P"])
        for got, want in zip(r["P_max"], [0.4286, 0.4472, 0.5405]):
            assert close(got, want, 5e-5), (method, r["P_max"])
        assert close(r["p-hat_max"], 0.5405, 5e-5), (method, r)
        assert r["argmax_i"] == 3
        assert close(r["p_u"], 0.8276, 5e-5), (method, r)
        assert close(r["min_entropy"], 0.273, 5e-4), (method, r)
        # Exact arithmetic for the same quantities, independent of the module:
        #   P = 9/21, 4/20, 3/19;  P_max = 9/21, sqrt(0.2), (3/19)^(1/3);  p_u from step 4 with z = 2.576.
        p_hat = (3 / 19) ** (1 / 3)
        assert r["p-hat_max"] == p_hat
        p_u = min(1.0, p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / 20))
        assert r["p_u"] == p_u
        assert r["min_entropy"] == -math.log2(p_u)


def test_spec_example_default_cutoff_gives_no_estimate():
    # With the real cutoff of 35 the most common symbol occurs 9 < 35 times: no t satisfies step 1.
    r = estimate(SPEC_S, 2)
    assert r["t"] == 0 and r["Q"] == [] and r["Q_next"] == 9
    assert math.isnan(r["min_entropy"]) and math.isnan(r["p_u"]) and math.isnan(r["p-hat_max"])


# --------------------------------------------------------------------------------------------
# Degenerate input: all one symbol.  By hand: in a constant sequence of length L every i-tuple
# is the same, so Q[i] = L - i + 1 (the number of start positions).  Q[i] >= 35 <=> i <= L - 34,
# so t = L - 34.  P[i] = Q[i]/(L-i+1) = 1, P_max[i] = 1, p-hat_max = 1,
# p_u = min(1, 1 + 2.576*sqrt(0)) = 1, min-entropy = -log2(1) = 0.
# --------------------------------------------------------------------------------------------
def test_degenerate_all_one_symbol():
    for L, bps, sym in ((40, 1, 0), (40, 1, 1), (100, 8, 200), (35, 3, 5)):
        for method in ALL_METHODS:
            r = estimate([sym] * L, bps, method=method)
            assert r["t"] == L - 34, (L, method, r["t"])              # L=40 -> 6, L=100 -> 66, L=35 -> 1
            assert r["Q"] == [L - i + 1 for i in range(1, L - 34 + 1)], (L, method)
            assert r["Q_next"] == 34, (L, method, r["Q_next"])        # Q[t+1] = L - (L-34+1) + 1 = 34
            assert all(p == 1.0 for p in r["P"]) and all(p == 1.0 for p in r["P_max"])
            assert r["p-hat_max"] == 1.0 and r["p_u"] == 1.0
            assert r["min_entropy"] == 0.0 and math.copysign(1.0, r["min_entropy"]) == 1.0
    # Shorter than the cutoff: the single symbol occurs L < 35 times, so no t exists.
    r = estimate([0] * 34, 1)
    assert r["t"] == 0 and r["Q_next"] == 34 and math.isnan(r["min_entropy"])
    # With cutoff 1 every length up to L is accepted (Q[L] = 1 >= 1) and no (L+1)-tuple exists.
    for method in ALL_METHODS:
        r = estimate([7] * 5, 3, cutoff=1, method=method)
        assert r["t"] == 5 and r["Q"] == [5, 4, 3, 2, 1] and r["Q_next"] == 0, (method, r)
        assert r["min_entropy"] == 0.0


# --------------------------------------------------------------------------------------------
# A second hand-derived input, binary, with a non-trivial argmax.
# S = 0,0,1,0,0,1,0,0,1,0  (L = 10), cutoff 3.
#   1-tuples: seven 0s, three 1s                                  -> Q[1] = 7
#   2-tuples: 00,01,10,00,01,10,00,01,10  -> "00","01","10" x3     -> Q[2] = 3
#   3-tuples: 001,010,100,001,010,100,001,010 -> "001" x3,"010" x3 -> Q[3] = 3
#   4-tuples: 0010,0100,1001,0010,0100,1001,0010 -> "0010" x3      -> Q[4] = 3
#   5-tuples: 00100,01001,10010,00100,01001,10010 -> max 2 < 3     -> t = 4, Q_next = 2
#   P = 7/10, 3/9, 3/8, 3/7;  P_max = 0.7, (1/3)^(1/2) = 0.57735, (3/8)^(1/3) = 0.72112,
#   (3/7)^(1/4) = 0.80911  -> p-hat_max = (3/7)^(1/4), attained at i = 4.
#   Step 4 with L - 1 = 9:  2.576*sqrt(0.80911*0.19089/9) = 2.576*0.13100 = 0.33746, so
#   p_u = min(1, 0.80911 + 0.33746 = 1.14657) = 1  and  min-entropy = -log2(1) = 0.
#   (The clamp binds: at L = 10 the 99 % interval is wider than the room above p-hat_max.)
#
# The same ten symbols twice, S2 = HAND_S + HAND_S (L = 20), cutoff 3.  Counted by hand on the
# 0-based start positions j:
#   1-tuples: 0 x14, 1 x6                                                       -> Q[1] = 14
#   2-tuples: "00" at j=0,3,6,9,10,13,16 (7); "01" x6; "10" x6                   -> Q[2] = 7
#   3-tuples: "001" at j=0,3,6,10,13,16 (6); "010" x6; "100" x5; "000" at j=9     -> Q[3] = 6
#   4-tuples: "0010" at j=0,3,6,10,13,16 (6); "0100" x5; "1001" x4; "1000","0001" -> Q[4] = 6
#   5-tuples: "00100" at j=0,3,6,10,13 (5); "01001" x4; "10010" x4                -> Q[5] = 5
#   6-tuples: "001001" at j=0,3,10,13 (4); "010010" x4; "100100" x3               -> Q[6] = 4
#   7-tuples: "0010010" at j=0,3,10,13 (4); "0100100" x3; "1001001" x2            -> Q[7] = 4
#   8-tuples: "00100100" at j=0,3,10 (3); "01001001" x2; "10010010" x2            -> Q[8] = 3
#   9-tuples: "001001001" at j=0,10 (2); "010010010" at j=1,11 (2); rest once      -> Q[9] = 2 < 3
#   so t = 8, Q = [14,7,6,6,5,4,4,3], Q_next = 2.
#   P = 14/20, 7/19, 6/18, 6/17, 5/16, 4/15, 4/14, 3/13
#   P_max = 0.7, 0.60698, 0.69336, 0.77077, 0.79245, 0.80228, 0.83613, 0.83252
#   -> p-hat_max = (4/14)^(1/7) = 0.83613 at i = 7.
#   Step 4 with L - 1 = 19: 2.576*sqrt(0.83613*0.16387/19) = 2.576*0.084919 = 0.21875, so
#   p_u = min(1, 1.05489) = 1 and min-entropy = 0 -- the clamp binds again.
# --------------------------------------------------------------------------------------------
HAND_S = [0, 0, 1, 0, 0, 1, 0, 0, 1, 0]
HAND_S2 = HAND_S + HAND_S


def test_hand_derived_binary_example():
    p_hat = (3 / 7) ** (1 / 4)
    assert close(p_hat, 0.80911, 5e-6)
    unclamped = p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / 9)
    assert close(unclamped, 1.14657, 5e-6)                    # > 1, so step 4's min(1, .) binds
    for method in ALL_METHODS:
        r = estimate(HAND_S, 1, cutoff=3, method=method)
        assert r["t"] == 4 and r["Q"] == [7, 3, 3, 3] and r["Q_next"] == 2, (method, r)
        assert r["P"] == [7 / 10, 3 / 9, 3 / 8, 3 / 7]
        for got, want in zip(r["P_max"], [0.7, 0.57735, 0.72112, 0.80911]):
            assert close(got, want, 5e-6), r["P_max"]
        assert r["argmax_i"] == 4
        assert r["p-hat_max"] == p_hat
        assert r["p_u"] == 1.0
        assert r["min_entropy"] == 0.0


def test_hand_derived_binary_example_twenty_symbols():
    p_hat = (4 / 14) ** (1 / 7)
    assert close(p_hat, 0.83613, 5e-6)
    unclamped = p_hat + 2.576 * math.sqrt(p_hat * (1 - p_hat) / 19)
    assert close(unclamped, 1.05489, 5e-6)                    # 0.836134 + 0.218751
    for method in ALL_METHODS:
        r = estimate(HAND_S2, 1, cutoff=3, method=method)
        assert r["t"] == 8 and r["Q"] == [14, 7, 6, 6, 5, 4, 4, 3] and r["Q_next"] == 2, (method, r)
        assert r["P"] == [14 / 20, 7 / 19, 6 / 18, 6 / 17, 5 / 16, 4 / 15, 4 / 14, 3 / 13]
        for got, want in zip(r["P_max"], [0.7, 0.60698, 0.69336, 0.77077, 0.79245, 0.80228, 0.83613, 0.83252]):
            assert close(got, want, 5e-6), r["P_max"]
        assert r["argmax_i"] == 7
        assert r["p-hat_max"] == p_hat
        assert r["p_u"] == 1.0 and r["min_entropy"] == 0.0
    # Cross-check every hand count against the brute-force Counter.
    for i, q in enumerate([14, 7, 6, 6, 5, 4, 4, 3, 2], start=1):
        assert most_common_tuple_count_literal(HAND_S2, i) == q, i


# --------------------------------------------------------------------------------------------
# The three counting methods agree with each other and with a brute-force Counter on random data,
# including biased sources (large t) and every alphabet width the tool uses.
# --------------------------------------------------------------------------------------------
def _random_inputs():
    rng = random.Random(20261107)
    cases = []
    for bps in (1, 2, 4, 8):
        k = 1 << bps
        for L in (1, 2, 5, 36, 100, 257, 600):
            # uniform
            cases.append((bps, [rng.randrange(k) for _ in range(L)]))
            # strongly biased toward symbol 0 (long repeats, large t)
            cases.append((bps, [0 if rng.random() < 0.9 else rng.randrange(k) for _ in range(L)]))
            # periodic with noise
            period = [rng.randrange(k) for _ in range(rng.randrange(1, 7))]
            cases.append((bps, [period[j % len(period)] if rng.random() < 0.97 else rng.randrange(k)
                                for j in range(L)]))
    return cases


def test_methods_agree_on_random_inputs():
    checked = 0
    for bps, S in _random_inputs():
        for cutoff in (1, 2, 3, 35):
            results = {m: estimate(S, bps, cutoff=cutoff, method=m, direct_t_limit=4) for m in ALL_METHODS}
            base = results["literal"]
            for m, r in results.items():
                assert r["Q"] == base["Q"], (bps, cutoff, m, r["Q"][:10], base["Q"][:10])
                assert r["Q_next"] == base["Q_next"], (bps, cutoff, m)
                assert r["t"] == base["t"]
                if base["t"] == 0 or len(S) < 2:                 # no t, or step 4's L - 1 = 0
                    assert math.isnan(r["min_entropy"]) and math.isnan(base["min_entropy"])
                else:
                    assert r["min_entropy"] == base["min_entropy"], (bps, cutoff, m)
                    assert r["p_u"] == base["p_u"] and r["p-hat_max"] == base["p-hat_max"]
            checked += 1
    assert checked > 100


def test_suffix_array_and_lcp_against_brute_force():
    rng = random.Random(7)
    for bps in (1, 2, 8):
        k = 1 << bps
        for L in (1, 2, 3, 10, 64, 300):
            for bias in (None, 0.9):
                S = [0 if (bias and rng.random() < bias) else rng.randrange(k) for _ in range(L)]
                Sn = np.array(S, dtype=np.int64)
                sa, rank = _suffix_array(Sn)
                want = sorted(range(L), key=lambda j: S[j:])          # Python list order: a prefix sorts first
                assert sa.tolist() == want, (bps, L, bias)
                assert all(rank[sa[r]] == r for r in range(L))
                lcp = _lcp_kasai(Sn, sa, rank)
                for r in range(1, L):
                    a, b = S[sa[r - 1]:], S[sa[r]:]
                    n = 0
                    while n < len(a) and n < len(b) and a[n] == b[n]:
                        n += 1
                    assert lcp[r] == n, (bps, L, bias, r)
                # Q[i] for every i against brute force.
                Qall = _tuple_counts_all_suffix_array(Sn)
                for i in range(1, L + 1):
                    assert int(Qall[i]) == most_common_tuple_count_literal(S, i), (bps, L, bias, i)


def test_Q_is_non_increasing_in_tuple_length():
    # The stopping rule in step 1 relies on this (see the module docstring for the proof).
    rng = random.Random(99)
    for _ in range(40):
        L = rng.randrange(1, 400)
        S = np.array([rng.randrange(4) if rng.random() < 0.3 else 0 for _ in range(L)], dtype=np.int64)
        Qall = _tuple_counts_all_suffix_array(S)[1:]
        assert all(Qall[i] >= Qall[i + 1] for i in range(L - 1))
        assert int(Qall[0]) == int(np.bincount(S).max())


def test_auto_switches_to_suffix_array_and_cross_checks():
    rng = random.Random(3)
    S = [0 if rng.random() < 0.95 else 1 for _ in range(2000)]
    r_auto = estimate(S, 1, direct_t_limit=5)
    r_direct = estimate(S, 1, method="direct")
    r_lit = estimate(S, 1, method="literal")
    assert r_auto["t"] > 5, r_auto["t"]
    assert r_auto["method"].startswith("suffix_array"), r_auto["method"]
    assert r_direct["method"] == "direct"
    assert r_auto["Q"] == r_direct["Q"] == r_lit["Q"]
    assert r_auto["min_entropy"] == r_direct["min_entropy"] == r_lit["min_entropy"]
    # When the direct method finishes within the limit, auto reports 'direct'.
    assert estimate(S, 1, direct_t_limit=10_000)["method"] == "direct"


# --------------------------------------------------------------------------------------------
# Step 4's constant.  The text prints 2.576; section 6.3.1 says it "corresponds to the
# Z(1-0.005) value".  Derive Phi^-1(0.995) independently with decimal arithmetic: erf by its
# Maclaurin series, Phi(x) = (1 + erf(x/sqrt 2))/2, bisection.
# --------------------------------------------------------------------------------------------
def _phi_inverse_0995():
    getcontext().prec = 50

    def erf(x):
        s = Decimal(0)
        term = x
        n = 0
        while True:
            add = term / (2 * n + 1)
            if abs(add) < Decimal(10) ** -45:
                break
            s += add
            n += 1
            term = -term * x * x / n
        pi = Decimal("3.14159265358979323846264338327950288419716939937510")
        return 2 / pi.sqrt() * s

    def phi(x):
        return (1 + erf(x / Decimal(2).sqrt())) / 2

    lo, hi = Decimal("2.5"), Decimal("2.6")
    for _ in range(170):
        mid = (lo + hi) / 2
        if phi(mid) < Decimal("0.995"):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def test_z_constants():
    z = _phi_inverse_0995()
    assert str(z).startswith("2.57582930354890076"), str(z)
    assert float(z) == Z_EXACT                               # binary64 nearest to the quantile
    assert Z_LITERAL == 2.576                                # the text's printed constant
    assert abs(float(z) - Z_LITERAL) < 2e-4
    # The exact constant is the smaller one, so p_u is smaller and the estimate larger (by a hair):
    # the 'exact' variant is the permissive one.  Documented in the fork as D-1 / C22c.
    rng = random.Random(1)
    S = [0 if rng.random() < 0.7 else 1 for _ in range(3000)]
    lit = estimate(S, 1, z_variant="literal")
    exa = estimate(S, 1, z_variant="exact")
    assert lit["z"] == 2.576 and exa["z"] == Z_EXACT
    assert exa["p_u"] < lit["p_u"] and exa["min_entropy"] > lit["min_entropy"]
    assert exa["min_entropy"] - lit["min_entropy"] < 1e-3
    assert exa["Q"] == lit["Q"] and exa["p-hat_max"] == lit["p-hat_max"]


def test_step3_arithmetic_recomputed_independently():
    rng = random.Random(5)
    S = [rng.randrange(4) if rng.random() < 0.5 else 0 for _ in range(1500)]
    r = estimate(S, 2)
    L = len(S)
    assert r["t"] >= 2
    for idx, q in enumerate(r["Q"]):
        i = idx + 1
        assert q == most_common_tuple_count_literal(S, i)
        assert r["P"][idx] == q / (L - i + 1)
        assert r["P_max"][idx] == (q / (L - i + 1)) ** (1.0 / i)
    assert r["p-hat_max"] == max(r["P_max"])
    assert r["p_u"] == min(1.0, r["p-hat_max"] + 2.576 * math.sqrt(r["p-hat_max"] * (1 - r["p-hat_max"]) / (L - 1)))
    assert r["min_entropy"] == -math.log2(r["p_u"])
    assert r["p_u"] < 1.0 and 0.0 < r["min_entropy"] <= 2.0     # the clamp does not bind here


# --------------------------------------------------------------------------------------------
# Input handling, bitstring conversion, command line.
# --------------------------------------------------------------------------------------------
def test_bitstring_conversion_msb_first():
    assert to_bitstring([5, 3], 3).tolist() == [1, 0, 1, 0, 1, 1]
    assert to_bitstring([0b10000000, 1], 8).tolist() == [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    assert to_bitstring([1, 0, 1], 1).tolist() == [1, 0, 1]
    assert to_bitstring([], 4).tolist() == []


def test_rejects_bad_input():
    for bad_symbols, bps in (([0, 2], 1), ([-1], 8), ([256], 8), ([[0, 1]], 1), ([0.5], 1)):
        try:
            estimate(bad_symbols, bps)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted {bad_symbols!r} at width {bps}")
    for bps in (0, -1, 1.0, True):
        try:
            estimate([0, 1], bps)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted bits_per_symbol={bps!r}")
    for opts in ({"cutoff": 0}, {"z_variant": "nist"}, {"method": "magic"}):
        try:
            estimate([0, 1], 1, **opts)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted {opts}")
    try:
        estimate([0, 1], 1, bogus=1)
    except TypeError:
        pass
    else:
        raise AssertionError("accepted an unknown option")
    # bytes are accepted as symbols
    assert estimate(bytes([0] * 40), 1)["t"] == 6
    # empty input: no tuple at all
    r = estimate([], 1)
    assert r["t"] == 0 and math.isnan(r["min_entropy"]) and r["L"] == 0


def _run_main(args):
    env = dict(os.environ)
    proc = subprocess.run([sys.executable, os.path.join(_REFERENCE_DIR, "py90b", "ttuple.py"), *args],
                          capture_output=True, text=True, env=env)
    return proc


def test_command_line_json_matches_estimate():
    tmp_parent = os.environ.get("PY90B_TMPDIR") or None
    with tempfile.TemporaryDirectory(dir=tmp_parent) as d:
        spec_file = os.path.join(d, "spec.bin")
        with open(spec_file, "wb") as fh:
            fh.write(bytes(SPEC_S))
        proc = _run_main([spec_file, "2", "--cutoff", "3"])
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        want = estimate(SPEC_S, 2, cutoff=3)
        for key in ("min_entropy", "t", "p-hat_max", "p_u", "Q", "P", "P_max", "Q_next", "L"):
            assert out[key] == want[key], key
        assert out["mode"] == "literal" and out["bits_per_symbol"] == 2 and out["symbols_in_file"] == 21
        assert out["bytes_exceeding_width"] == 0

        # --bitstring on an 8-bit file equals estimate() on the MSB-first bit expansion at width 1.
        rng = random.Random(11)
        data = bytes(rng.randrange(256) if rng.random() < 0.5 else 0 for _ in range(400))
        bit_file = os.path.join(d, "bytes.bin")
        with open(bit_file, "wb") as fh:
            fh.write(data)
        proc = _run_main([bit_file, "8", "--bitstring", "--z", "exact"])
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        want = estimate(to_bitstring(list(data), 8), 1, z_variant="exact")
        assert out["mode"] == "bitstring" and out["L"] == 3200 == want["L"]
        for key in ("min_entropy", "t", "p-hat_max", "p_u", "Q", "Q_next"):
            assert out[key] == want[key], key
        # --literal on the same file at width 8
        proc = _run_main([bit_file, "8", "--literal"])
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        want = estimate(list(data), 8)
        assert out["t"] == want["t"] and out["Q"] == want["Q"]
        assert (math.isnan(out["min_entropy"]) and math.isnan(want["min_entropy"])) or out["min_entropy"] == want["min_entropy"]

        # Low bits are the symbol; bytes with higher bits set are counted and reported.
        mixed = bytes([0x83, 0x01, 0x00, 0x02] * 10)
        mixed_file = os.path.join(d, "mixed.bin")
        with open(mixed_file, "wb") as fh:
            fh.write(mixed)
        proc = _run_main([mixed_file, "1", "--cutoff", "3"])
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["bytes_exceeding_width"] == 20 and "warning" in proc.stderr
        assert out["Q"] == estimate([b & 1 for b in mixed], 1, cutoff=3)["Q"]

        # Usage errors exit 2 and print nothing on stdout.
        assert _run_main([]).returncode == 2
        assert _run_main([spec_file, "9"]).returncode == 2
        assert _run_main([spec_file, "2", "--frobnicate"]).returncode == 2


# --------------------------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------------------------
def _main():
    tests = [(name, obj) for name, obj in sorted(globals().items()) if name.startswith("test_") and callable(obj)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
        except Exception:                                         # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
        else:
            print(f"PASS  {name}")
    print(f"{len(tests) - failed} passed, {failed} failed, {len(tests)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
