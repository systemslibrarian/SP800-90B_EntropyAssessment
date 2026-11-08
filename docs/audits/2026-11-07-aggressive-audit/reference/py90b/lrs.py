#!/usr/bin/env python3
"""
py90b.lrs -- independent reference implementation of the SP 800-90B
Longest Repeated Substring (LRS) estimate, SP 800-90B §6.3.6 (PDF p. 56-57).

INDEPENDENCE.  Written from the text of NIST SP 800-90B (January 2018) only,
as extracted to reference/sp800-90b.pages.txt.  Nothing under cpp/ was read.
The only thing taken from the C++ tool is the NAMES of its printed
intermediates ("u", "v", "p-hat", "p_u", "min entropy") from
reference/cpp-verbose-labels-non_iid.txt, so a differential driver can match
the keys of the returned dict.

THE SPEC, quoted (SP 800-90B §6.3.6, PDF p. 56-57):

  "Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},
   1. Find the smallest u such that the number of occurrences of the most
      common u-tuple in S is less than 35.
   2. Find the largest v such that the number of occurrences of the most
      common v-tuple in S is at least 2, and the most common (v+1)-tuple in S
      occurs once. In other words, v is the largest length that a tuple repeat
      occurs. If v < u, this estimate cannot be computed.
   3. For W = u to v, compute the estimated W-tuple collision probability
            P_W = sum_i C(C_i, 2) / C(L-W+1, 2),
      where C_i is the number of occurrences of the ith unique W-tuple.
      Compute the estimated average collision probability per string symbol
      as P_max,W = P_W^(1/W).  Let p-hat = max(P_max,u, ..., P_max,v).
   4. Calculate an upper bound on the probability of the most common value
      p_u as    p_u = min(1, p-hat + 2.576 * sqrt(p-hat (1 - p-hat) / (L-1))).
   5. The entropy estimate is calculated as -log2(p_u)."

Two implementations of the counting are kept and cross-checked:

  * DIRECT -- count the W-tuples literally, in a dictionary.  This is the
    line-by-line transcription of the text (steps 1-3) and the one a reader
    should check first.  Cost O(L * v * W): fine for small inputs, hopeless
    when the longest repeat v is long (e.g. a constant sequence).

  * SUFFIX -- a suffix array (prefix doubling, numpy) plus its LCP array
    (Kasai).  Every quantity the spec asks for is then read off the LCP
    array; the correspondence is stated at each function.  O(L log L) and
    independent of how long the repeats are, so it handles L = 10^6 and the
    pathological inputs.

  estimate(method="auto") runs SUFFIX and, whenever the DIRECT count is cheap
  (L*(v+1) <= direct_budget), also DIRECT, and asserts that u, v and every
  pair count agree EXACTLY.  method="direct" / method="suffix" run one alone.

Conventions:
  * Positions and tuple lengths are 1-based in prose (as in the spec) and
    0-based in code; L is the number of symbols in the sequence being assessed
    (bits, in bitstring mode -- see to_bitstring()).
  * Where the spec gives no value (v < u), min_entropy, p-hat and p_u are
    float('nan') and can_run is False.
  * The constant 2.576 is used exactly as printed (Z_LITERAL).  The fork under
    audit is DOCUMENTED (FORK-DIVERGENCE-AND-TRUST.md D-1 / C22c / tracker
    F07) to use the binary64 0.995 quantile 2.5758293035489008 instead; that
    variant is reported alongside under keys suffixed "_z_exact" so the two
    can be reconciled without either being hidden.  Pass z=Z_EXACT_0995 to
    make it the primary.
  * No cap at log2(k) or at bits_per_symbol is applied: §6.3.6 states none.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter

import numpy as np

# --------------------------------------------------------------------------
# Constants from the text
# --------------------------------------------------------------------------

CUTOFF = 35                        # §6.3.6 step 1: "... is less than 35"
Z_LITERAL = 2.576                  # §6.3.6 step 4, the constant as printed
Z_EXACT_0995 = 2.5758293035489008  # binary64 Z(1-0.005); the fork's documented
                                   # choice (D-1/C22c), NOT the printed text.

# The DIRECT cross-check is run in method="auto" only when L*(v+1) is at most
# this; above it only the SUFFIX path runs.  Measured on this host at
# L = 20,000 (logs/analysis-lrs-ref-timing-20000.log): the direct count costs
# about 1.9e-7 s per unit of L*(v+1), so 1e8 is roughly 20-30 s -- enough to
# cross-check ordinary 10^6-sample data (v of a few tens) and to skip the
# pathological inputs (a constant sequence has L*(v+1) ~ L^2).
DIRECT_BUDGET = 100_000_000


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def estimate(symbols, bits_per_symbol, *, cutoff=CUTOFF, z=Z_LITERAL,
             method="auto", direct_budget=DIRECT_BUDGET) -> dict:
    """SP 800-90B §6.3.6 LRS estimate of `symbols` (ints in [0, 2**bits_per_symbol)).

    Returns a dict whose keys follow the C++ verbose labels:
      'min_entropy' (float, nan if the estimate cannot be computed),
      'u', 'v' (int), 'p-hat', 'p_u' (float or nan),
    plus the full working: 'L', 'cutoff', 'z', 'can_run', 'reason',
      'pair_sum_W' {W: sum_i C(C_i,2)}, 'positions_choose2_W' {W: C(L-W+1,2)},
      'P_W', 'Pmax_W' {W: float}, 'argmax_W', 'Q' {W: count of the most
      common W-tuple, for the W the spec's conditions mention},
      'p_u_z_exact', 'min_entropy_z_exact' (the documented-divergence variant),
      'method' (which counting path(s) produced the numbers).

    options:
      cutoff  -- the "35" of step 1 (the spec's worked example uses 3).
      z       -- the "2.576" of step 4.
      method  -- "auto" | "direct" | "suffix"  (see module docstring).
    """
    S = _as_symbol_array(symbols, bits_per_symbol)
    L = int(S.size)
    if not isinstance(cutoff, int) or cutoff < 2:
        raise ValueError("cutoff must be an integer >= 2 (the spec's value is 35)")
    if method not in ("auto", "direct", "suffix"):
        raise ValueError("method must be 'auto', 'direct' or 'suffix'")

    counts = None
    how = None
    if method in ("auto", "suffix"):
        sfx = _counts_suffix(S, cutoff)
        counts, how = sfx, "suffix"
        if method == "auto" and L * (sfx["v"] + 1) <= direct_budget:
            drc = _counts_direct(S, cutoff)
            _assert_counts_agree(sfx, drc)
            how = "suffix+direct (agree)"
    if method == "direct":
        counts, how = _counts_direct(S, cutoff), "direct"

    out = _steps_3_to_5(counts, L, z)
    out.update({"L": L, "cutoff": cutoff, "z": float(z), "method": how,
                "Q": {int(k): int(val) for k, val in sorted(counts["Q"].items())}})
    return out


def to_bitstring(symbols, bits_per_symbol) -> np.ndarray:
    """Expand each symbol into its bits_per_symbol bits, MSB first, giving a
    sequence of 1-bit symbols (the H_bitstring view of §3.1.3, PDF p. 20:
    "the sequential dataset that contains L samples (each having n bits) is
    considered as a bitstring of size nL")."""
    S = _as_symbol_array(symbols, bits_per_symbol)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.int64)
    return ((S[:, None] >> shifts[None, :]) & 1).astype(np.int64).ravel()


# --------------------------------------------------------------------------
# Steps 3-5: arithmetic on the counts (shared by both counting paths)
# --------------------------------------------------------------------------

def _steps_3_to_5(counts, L, z) -> dict:
    u, v = counts["u"], counts["v"]
    nan = float("nan")
    out = {"u": int(u), "v": int(v), "can_run": v >= u, "reason": None,
           "pair_sum_W": {}, "positions_choose2_W": {}, "P_W": {}, "Pmax_W": {},
           "argmax_W": None, "p-hat": nan, "p_u": nan, "min_entropy": nan,
           "p_u_z_exact": nan, "min_entropy_z_exact": nan}
    if v < u:
        # step 2: "If v < u, this estimate cannot be computed."
        out["reason"] = f"v < u ({v} < {u}): the estimate cannot be computed (§6.3.6 step 2)"
        return out

    # step 3: "For W = u to v, compute ... P_W = sum_i C(C_i,2) / C(L-W+1, 2)"
    for W in range(u, v + 1):
        n_positions = L - W + 1                       # number of W-tuples in S
        den = n_positions * (n_positions - 1) // 2    # C(L-W+1, 2), exact int
        num = int(counts["pair_sum"][W])              # sum_i C(C_i, 2), exact int
        P_W = num / den
        out["pair_sum_W"][W] = num
        out["positions_choose2_W"][W] = den
        out["P_W"][W] = P_W
        out["Pmax_W"][W] = P_W ** (1.0 / W)           # "P_max,W = P_W^(1/W)"

    # "Let p-hat = max(P_max,u, ..., P_max,v)"  (ties -> smallest W)
    W_star = max(out["Pmax_W"], key=out["Pmax_W"].get)
    p_hat = out["Pmax_W"][W_star]
    out["argmax_W"] = int(W_star)
    out["p-hat"] = p_hat

    # step 4 and 5
    out["p_u"] = _p_u(p_hat, L, z)
    out["min_entropy"] = _neg_log2(out["p_u"])
    out["p_u_z_exact"] = _p_u(p_hat, L, Z_EXACT_0995)
    out["min_entropy_z_exact"] = _neg_log2(out["p_u_z_exact"])
    return out


def _p_u(p_hat, L, z):
    """§6.3.6 step 4:  p_u = min(1, p-hat + z * sqrt(p-hat (1 - p-hat) / (L - 1)))."""
    return min(1.0, p_hat + z * math.sqrt(p_hat * (1.0 - p_hat) / (L - 1)))


def _neg_log2(p_u):
    """§6.3.6 step 5:  -log2(p_u), with -log2(1) normalised to +0.0 (not -0.0)."""
    return 0.0 if p_u == 1.0 else -math.log2(p_u)


# --------------------------------------------------------------------------
# DIRECT counting -- the literal transcription of steps 1-3
# --------------------------------------------------------------------------

def _tuple_counter(seq, W) -> Counter:
    """Occurrence count of every W-tuple of seq (overlapping, all L-W+1 positions)."""
    return Counter(seq[i:i + W] for i in range(len(seq) - W + 1))


def _counts_direct(S, cutoff) -> dict:
    """Steps 1-3 by counting tuples in a dictionary.

    Returns {'u', 'v', 'Q': {W: Q[W] for W = 1..v+1},
             'pair_sum': {W: sum_i C(C_i,2) for W = u..v}}.
    Q[W] is "the number of occurrences of the most common W-tuple in S".
    """
    L = int(S.size)
    # hashable windows: bytes when the alphabet fits a byte, tuples otherwise
    seq = bytes(S.astype(np.uint8)) if int(S.max()) < 256 else tuple(int(x) for x in S)

    Q, pair_sum = {}, {}
    W = 1
    while True:
        c = _tuple_counter(seq, W)
        Q[W] = max(c.values()) if c else 0            # W > L: no W-tuples at all
        pair_sum[W] = sum(n * (n - 1) // 2 for n in c.values())  # sum_i C(C_i, 2)
        if Q[W] < 2:
            break                                     # no W-tuple repeats
        W += 1
    # step 2: v is the largest W whose most common W-tuple occurs >= 2 times,
    # with the most common (W+1)-tuple occurring once.  Q is non-increasing
    # in W, so v = (first W with Q[W] < 2) - 1.
    v = W - 1
    # step 1: the smallest u with Q[u] < cutoff.  Q[v+1] <= 1 < cutoff, so u
    # is found among 1..v+1.
    u = next(W for W in range(1, v + 2) if Q[W] < cutoff)
    return {"u": u, "v": v, "Q": Q,
            "pair_sum": {W: pair_sum[W] for W in range(u, v + 1)}}


# --------------------------------------------------------------------------
# SUFFIX counting -- suffix array + LCP array
# --------------------------------------------------------------------------
#
# Let sa be the suffix array of S (suffixes in lexicographic order, a proper
# prefix sorting before its extensions) and lcp[r] = LCP(S[sa[r]:], S[sa[r+1]:])
# for r = 0..L-2.  For two suffixes at sorted ranks a < b,
#       LCP(sa[a], sa[b]) = min(lcp[a], ..., lcp[b-1]).
# Two positions i != j carry the same W-tuple  <=>  LCP(i, j) >= W  (and then
# both suffixes have at least W symbols, i.e. both are legal W-tuple
# positions).  Hence:
#   * Q[W] (most common W-tuple count) = 1 + the longest run of consecutive
#     lcp entries that are all >= W;
#   * v = max(lcp)           (the longest length at which a repeat occurs);
#   * u = 1 + the largest W with Q[W] >= cutoff, i.e. 1 + the largest W for
#     which some window of (cutoff-1) consecutive lcp entries is all >= W,
#     i.e. 1 + max over windows of the window minimum (u = 1 if no window);
#   * sum_i C(C_i, 2) at length W = #{unordered suffix pairs with LCP >= W}.

def _suffix_array(S) -> np.ndarray:
    """Suffix array by prefix doubling (Manber-Myers), vectorised with numpy.

    Round k sorts suffixes by their first 2k symbols using the pair
    (rank of S[i:], rank of S[i+k:]) from the previous round, with a rank of
    -1 for a suffix that has ended (so a proper prefix sorts first).  Stops
    when all ranks are distinct.
    """
    n = int(S.size)
    rank = np.unique(S, return_inverse=True)[1].astype(np.int64).reshape(n)
    k = 1
    while True:
        second = np.full(n, -1, dtype=np.int64)
        if k < n:
            second[: n - k] = rank[k:]
        key = rank * (n + 1) + (second + 1)           # lexicographic (rank, second)
        sa = np.argsort(key, kind="stable")
        sorted_key = key[sa]
        new_rank_sorted = np.concatenate(
            ([0], np.cumsum(sorted_key[1:] != sorted_key[:-1]))).astype(np.int64)
        rank = np.empty(n, dtype=np.int64)
        rank[sa] = new_rank_sorted
        if new_rank_sorted[-1] == n - 1:              # all suffixes distinguished
            return sa
        k *= 2
        assert k <= 2 * n, "prefix doubling did not terminate"


def _lcp_kasai(S_list, sa_list) -> list:
    """Kasai's algorithm: lcp[r] = LCP of the suffixes at sorted ranks r, r+1."""
    n = len(sa_list)
    rank = [0] * n
    for r, i in enumerate(sa_list):
        rank[i] = r
    lcp = [0] * max(n - 1, 0)
    h = 0
    for i in range(n):
        r = rank[i]
        if r == 0:
            h = 0
            continue
        j = sa_list[r - 1]
        while i + h < n and j + h < n and S_list[i + h] == S_list[j + h]:
            h += 1
        lcp[r - 1] = h
        if h:
            h -= 1
    return lcp


def _Q_from_lcp(lcp_arr, W, L) -> int:
    """Count of the most common W-tuple: 1 + longest run of lcp entries >= W."""
    if W > L:
        return 0                                      # there are no W-tuples
    if W < 1:
        raise ValueError("W must be >= 1")
    if lcp_arr.size == 0:
        return 1
    hit = np.concatenate(([False], lcp_arr >= W, [False]))
    edges = np.flatnonzero(hit[1:] != hit[:-1])       # run starts/ends, paired
    if edges.size == 0:
        return 1
    return int((edges[1::2] - edges[0::2]).max()) + 1


def _pairs_by_exact_lcp(lcp) -> list:
    """exact[x] = number of unordered suffix pairs whose LCP is exactly x.

    A pair (ranks a < b) has LCP = min(lcp[a..b-1]).  Every interval of the
    lcp array is charged to the leftmost position attaining its minimum:
    for index k, the admissible intervals extend left to (but not including)
    the nearest p < k with lcp[p] <= lcp[k], and right to (but not including)
    the nearest q > k with lcp[q] < lcp[k].  Monotonic stacks, O(L).
    sum(exact) == C(L, 2) is asserted by the caller.
    """
    m = len(lcp)
    if m == 0:
        return [0]
    prev_le = [-1] * m
    stack = []
    for k in range(m):
        while stack and lcp[stack[-1]] > lcp[k]:
            stack.pop()
        prev_le[k] = stack[-1] if stack else -1
        stack.append(k)
    next_lt = [m] * m
    stack = []
    for k in range(m - 1, -1, -1):
        while stack and lcp[stack[-1]] >= lcp[k]:
            stack.pop()
        next_lt[k] = stack[-1] if stack else m
        stack.append(k)
    exact = [0] * (max(lcp) + 1)
    for k in range(m):
        exact[lcp[k]] += (k - prev_le[k]) * (next_lt[k] - k)
    return exact


def _counts_suffix(S, cutoff) -> dict:
    """Steps 1-3 read off the LCP array.  Same return shape as _counts_direct,
    except Q is given only for the W that the spec's conditions mention
    (u-1, u, v, v+1), and those conditions are asserted in the spec's words."""
    L = int(S.size)
    sa = _suffix_array(S)
    lcp = _lcp_kasai(S.tolist(), sa.tolist())
    lcp_arr = np.asarray(lcp, dtype=np.int64)
    m = lcp_arr.size                                  # = L - 1

    # step 2: v = the largest length at which a tuple repeat occurs
    v = int(lcp_arr.max()) if m else 0

    # step 1: u = smallest W with Q[W] < cutoff.  Q[W] >= cutoff iff some
    # (cutoff-1) consecutive lcp entries are all >= W.
    width = cutoff - 1
    if m < width:
        u = 1                                         # Q[1] <= L < cutoff
    else:
        window_min = np.lib.stride_tricks.sliding_window_view(lcp_arr, width).min(axis=1)
        u = int(window_min.max()) + 1

    # the spec's conditions, checked in its own words
    Q = {}
    for W in sorted({u - 1, u, v, v + 1}):
        if 1 <= W <= L:
            Q[W] = _Q_from_lcp(lcp_arr, W, L)
    assert Q[u] < cutoff, "step 1: the most common u-tuple must occur < cutoff times"
    if u > 1:
        assert Q[u - 1] >= cutoff, "step 1: u must be the SMALLEST such length"
    if v >= 1:
        assert Q[v] >= 2, "step 2: the most common v-tuple must occur at least twice"
        assert Q[v + 1] == 1, "step 2: the most common (v+1)-tuple must occur once"

    # step 3's numerators for every W in [u, v], all at once
    exact = _pairs_by_exact_lcp(lcp)
    assert sum(exact) == L * (L - 1) // 2, "every suffix pair must be counted once"
    pair_sum = {}
    if v >= u:
        ge = 0
        at_least = [0] * (v + 2)                      # at_least[W] = #pairs with LCP >= W
        for x in range(v, -1, -1):
            ge += exact[x]
            at_least[x] = ge
        pair_sum = {W: at_least[W] for W in range(u, v + 1)}
    return {"u": u, "v": v, "Q": Q, "pair_sum": pair_sum}


def _assert_counts_agree(a, b):
    assert a["u"] == b["u"], f"u disagrees: suffix {a['u']} vs direct {b['u']}"
    assert a["v"] == b["v"], f"v disagrees: suffix {a['v']} vs direct {b['v']}"
    for W in set(a["Q"]) & set(b["Q"]):
        assert a["Q"][W] == b["Q"][W], f"Q[{W}] disagrees: {a['Q'][W]} vs {b['Q'][W]}"
    assert a["pair_sum"] == b["pair_sum"], "pair counts disagree between suffix and direct"


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------

def _as_symbol_array(symbols, bits_per_symbol) -> np.ndarray:
    if not isinstance(bits_per_symbol, int) or bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be a positive integer")
    S = np.asarray(symbols)
    if S.ndim != 1:
        raise ValueError("symbols must be a one-dimensional sequence")
    if S.size == 0:
        raise ValueError("symbols is empty")
    if not np.issubdtype(S.dtype, np.integer):
        T = S.astype(np.int64)
        if not np.array_equal(T, S):
            raise ValueError("symbols must be integers")
        S = T
    S = S.astype(np.int64)
    if S.min() < 0 or S.max() >= (1 << bits_per_symbol):
        raise ValueError(f"symbols must lie in [0, 2**{bits_per_symbol})")
    return S


# --------------------------------------------------------------------------
# __main__:  python lrs.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
#                          [--cutoff N] [--z Z] [--method auto|direct|suffix]
# --------------------------------------------------------------------------

def _main(argv) -> int:
    args = list(argv)
    mode, cutoff, z, method = "literal", CUTOFF, Z_LITERAL, "auto"
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--literal":
            mode = "literal"
        elif a == "--bitstring":
            mode = "bitstring"
        elif a == "--cutoff":
            i += 1; cutoff = int(args[i])
        elif a == "--z":
            i += 1; z = float(args[i])
        elif a == "--method":
            i += 1; method = args[i]
        elif a.startswith("--"):
            sys.stderr.write(f"unknown option {a}\n"); return 2
        else:
            positional.append(a)
        i += 1
    if len(positional) != 2:
        sys.stderr.write("usage: lrs.py <rawfile> <bits_per_symbol> [--literal|--bitstring]"
                         " [--cutoff N] [--z Z] [--method auto|direct|suffix]\n")
        return 2
    path, bps = positional[0], int(positional[1])
    with open(path, "rb") as fh:
        raw = np.frombuffer(fh.read(), dtype=np.uint8).astype(np.int64)
    symbols = raw & ((1 << bps) - 1)                  # one symbol per byte, low bps bits
    if mode == "bitstring":
        res = estimate(to_bitstring(symbols, bps), 1, cutoff=cutoff, z=z, method=method)
    else:
        res = estimate(symbols, bps, cutoff=cutoff, z=z, method=method)
    res["mode"] = mode
    res["bits_per_symbol"] = bps
    sys.stdout.write(json.dumps(res, indent=1) + "\n")  # NaN is emitted as NaN
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
