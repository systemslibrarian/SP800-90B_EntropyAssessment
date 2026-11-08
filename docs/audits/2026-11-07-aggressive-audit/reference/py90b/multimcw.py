"""py90b.multimcw -- SP 800-90B section 6.3.7, the Multi Most Common in Window (MultiMCW)
prediction estimate, written from the published text only.

Source of authority: NIST SP 800-90B (January 2018), section 6.3.7 "Multi Most Common in
Window Prediction Estimate", PDF pp. 57-59 of reference/sp800-90b.pages.txt (sha256 of the PDF
9b0dd771...defe7, see AUDIT-BRIEF.md).  Nothing here was taken from the C++ under cpp/; the
only borrowed items are the verbose-output LABEL NAMES ("C", "r", "N", "P_global",
"P_global'", "P_local", "min entropy") from reference/cpp-verbose-labels-non_iid.txt so a
differential driver can match them.

The algorithm, quoted from the standard (PDF p. 57-58), with the 0-based index used in this
file beside each step.  The spec indexes S = (s1, ..., sL) from 1; this file holds s[0..L-1]
with s[t] = s_(t+1).  A spec window (s_(i-wj), ..., s_(i-1)) is the slice s[t-wj : t] with
t = i-1, the condition "i > wj" is "t >= wj", and correct_(i-w1) is correct[t-w1].

  1. "Let window sizes be w1=63, w2=255, w3=1023, w4=4095, and N = L - w1.  Let correct be
     an array of N Boolean values, each initialized to 0."
  2. "Let scoreboard be a list of four counters, each initialized to 0.  Let frequent be a
     list of four values, each initialized to Null.  Let winner = 1."
  3. "For i = w1 + 1 to L:
       a. For j = 1 to 4,
          i.  If i > wj, let frequentj be the most frequent value in (s_(i-wj), s_(i-wj+1),
              ..., s_(i-1)).  If there is a tie, then the most frequent value that has
              appeared most recently is assigned to frequentj.
          ii. Else, let frequentj = Null.
       b. Let prediction = frequent_winner.
       c. If (prediction = si), let correct_(i-w1) = 1.
       d. Update the scoreboard.  For j = 1 to 4,
          i. If (frequentj = si)
             1. Let scoreboardj = scoreboardj + 1
             2. If scoreboardj >= scoreboard_winner, let winner = j"
  4. "Let C be the number of ones in correct."
  5. "Calculate the predictor's global performance as P_global = C/N.  The upper bound of
     the 99 % confidence interval on P_global, denoted P'_global is calculated as:
        P'_global = 1 - 0.01^(1/N)                                       if P_global = 0,
                  = min(1, P_global + 2.576 sqrt(P_global (1-P_global)/(N-1)))  otherwise
     where 2.576 corresponds to the Z(1-0.005) value."
  6. "Calculate the predictor's local performance, based on the longest run of correct
     predictions.  Let r be one greater than the length of the longest run of ones in
     correct.  Use a binary search to solve the following for P_local:
        0.99 = (1 - P_local x) / ((r + 1 - r x) q)  *  1 / x^(N+1),
     where q = 1 - P_local and x = x10, derived by iterating the recurrence relation
        x_j = 1 + q P_local^r x_(j-1)^(r+1)
     for j from 1 to 10, and x0 = 1.  Note that solving for P_local using the logarithm of
     these equations is robust against overflows."
  7. "The min-entropy is the negative logarithm of the greater performance metric
        min-entropy = -log2(max(P'_global, P_local, 1/k))."

Readings taken where the text leaves room (each is also returned/selectable; see the
module-level AMBIGUITIES list and the `estimate` options):

  * Tie rule (3.a.i): among the values whose count in the window is maximal, the one whose
    most recent occurrence is latest (closest to s_(i-1)).  This is the only reading that
    reproduces every row of the section's worked example (tested).
  * Scoreboard rule (3.d.i.2): the comparison uses "scoreboard_winner" as it stands at that
    moment, i.e. `winner` may already have been changed earlier in the same j loop, and ">="
    hands ties to the LARGER j.  The worked example at i = 7 (winner becomes 2 on a tie) and
    i = 12 (j = 1 takes the winner, then j = 2 takes it back) requires exactly this.
  * k in step 7: the size of the output space A = {x1..xk} "specified by the submitter"
    (section 6, PDF p. 48), i.e. 2**bits_per_symbol.  `k_mode='observed'` uses the number
    of distinct symbols actually present instead.  The two can differ materially (tested).
  * 2.576 is used literally (step 5).  `z=` lets a driver substitute the binary64 0.995
    quantile 2.5758293035489008 that FORK-DIVERGENCE-AND-TRUST.md D-1 documents the fork using.
  * The binary search (step 6) has no stated bounds or tolerance; this file searches [0, 1]
    to the resolution of binary64 (until the midpoint stops moving).  `plocal_mode='mp'`
    repeats the search in arbitrary precision with mpmath if that package is importable.
  * N <= 0 (L <= w1): the spec defines nothing; every statistic is returned as NaN.
  * N = 1 with P_global != 0: step 5 divides by N-1 = 0; returned as NaN.
  * P_local is ALWAYS computed here, even when it cannot exceed P'_global (the C++ prints
    "P_local can't change the result." and omits the number in that case).  The dict also
    carries `P_local_changes_result` so a driver can check the C++'s shortcut claim.

Complexity: O(L * k) with numpy over chunks for step 3.a, plus a sequential Python loop over
only the steps at which at least one subpredictor matched (steps with no match leave
`correct` and the scoreboard untouched, so skipping them is exact).
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

# ---- constants named in the text --------------------------------------------------------
WINDOWS = (63, 255, 1023, 4095)      # step 1: w1..w4 (PDF p. 57)
Z_TEXT = 2.576                        # step 5: "where 2.576 corresponds to the Z(1-0.005) value"
Z_BINARY64 = 2.5758293035489008       # variant only (FORK-DIVERGENCE-AND-TRUST.md D-1); not the text's constant
CONFIDENCE = 0.99                     # step 6 left-hand side; step 5's "99 % confidence interval"
RECURRENCE_STEPS = 10                 # step 6: "x = x10 ... for j from 1 to 10, and x0 = 1"
NULL = -1                             # encoding of the spec's Null (symbols are >= 0)

AMBIGUITIES = [
    "step 7 'k': 2**bits_per_symbol (the submitter-specified output space, default) vs the "
    "number of distinct symbols observed (k_mode='observed'); materially different when the "
    "data uses a strict subset of the alphabet and the predictor does worse than 1/k",
    "step 5 '2.576' is a printed rounding of the 0.995 normal quantile; the text's constant is "
    "the default here (z=2.576), the exact binary64 quantile is a variant (z=Z_BINARY64)",
    "step 6 'binary search': bounds and tolerance unstated; [0,1] to binary64 resolution here, "
    "arbitrary precision optional (plocal_mode='mp')",
    "step 1 with L <= w1 gives N <= 0: undefined, returned as NaN",
    "step 5 with N = 1 and P_global != 0 divides by zero: undefined, returned as NaN",
    "Appendix G.2 Table 3 is labelled 'L = 1 000 000' but step 6 uses N; the table is "
    "reproduced here to its printed 4 decimals with N = 1 000 000",
    "Appendix G.2 Table 3 (PDF p. 76), second column, rows r = 55..155: each printed value is "
    "the value for r - 5 (0.7092 is r=50's, ..., 0.8980 is r=150's); r = 160 onward is labelled "
    "correctly.  MEASURED 2026-11-07, logs/reference-multimcw-probe1-worked-example-table3.log; "
    "the test suite asserts the shift",
    "step 6's right-hand side is not monotone in P_local over (0, 1) (it has sub-target wiggles "
    "and a pole where r + 1 - r x = 0); but on all 17 (r, N) pairs measured, including r = N+1, "
    "the set where it exceeds 0.99 is a single initial interval, so a [0,1] bisection is "
    "well-posed there (logs/reference-multimcw-probe2-step6-crossings.log).  Narrower regions "
    "below the 2.5e-6 grid remain a SUSPICION only",
    "the worked example prints min-entropy 0.3908 = -log2(0.7627), i.e. computed from the ROUNDED "
    "P'_global; the unrounded value gives 0.39088.  A rounding artefact of the example, not a "
    "reading of the algorithm",
]


# ============================================================================================
# step 3.a -- the most-common-in-window subpredictors, all positions at once
# ============================================================================================
def most_common_in_windows(s, k, windows=WINDOWS, chunk=32768):
    """Return a list (one entry per window) of int64 arrays `frequent_j`, each of length
    N = L - w1, holding step 3.a's frequentj for the prediction of s[t], t = w1 .. L-1
    (array index n = t - w1), or NULL where "i > wj" fails.

    `s` must be an int array with values in [0, k).  For each window the value chosen is
    the one with the largest count in s[t-w : t]; ties go to the value whose most recent
    occurrence (largest index < t) is latest -- step 3.a.i's "most frequent value that has
    appeared most recently".

    Implementation: positions are processed in chunks; for each chunk a (k x range) one-hot
    cumulative sum gives every symbol's count in every window, a running maximum gives
    every symbol's most recent position before t, and the lexicographic argmax of
    (count, last position) is taken along the symbol axis.  Plain arithmetic, no heuristics.
    """
    s = np.asarray(s, dtype=np.int64)
    L = int(s.shape[0])
    windows = tuple(int(w) for w in windows)
    if any(b <= a for a, b in zip(windows, windows[1:])) or windows[0] < 1:
        raise ValueError("windows must be strictly increasing and positive (spec: 63,255,1023,4095)")
    w1, wmax = windows[0], windows[-1]
    N = L - w1
    out = [np.full(max(N, 0), NULL, dtype=np.int64) for _ in windows]
    if N <= 0:
        return out

    # last[a] = most recent index u < T0 with s[u] == a, or -1.  Positions 0..w1-1 precede
    # the first prediction (t = w1).
    last = np.full(k, -1, dtype=np.int64)
    for u in range(w1):
        last[s[u]] = u

    T0 = w1
    while T0 < L:
        T1 = min(L, T0 + chunk)
        B = T1 - T0
        lo = max(0, T0 - wmax)                       # earliest position any window in this chunk needs
        seg = s[lo:T1]
        M = seg.shape[0]

        # cs[a, m] = number of occurrences of a in s[lo : lo+m]   (m = 0..M)
        onehot = np.zeros((k, M + 1), dtype=np.int32)
        onehot[seg, np.arange(1, M + 1)] = 1
        cs = np.cumsum(onehot, axis=1, dtype=np.int32)

        # lp[a, m] = most recent index u < T0+m with s[u] == a  (m = 0..B-1), -1 if none
        arr = np.full((k, B + 1), -1, dtype=np.int64)
        arr[:, 0] = last
        arr[s[T0:T1], np.arange(1, B + 1)] = np.arange(T0, T1)
        acc = np.maximum.accumulate(arr, axis=1)
        lp = acc[:, :B]
        last = acc[:, B]

        t = np.arange(T0, T1)
        for j, w in enumerate(windows):
            valid = t >= w                            # step 3.a.i's "If i > wj"  (i = t+1)
            if not valid.any():
                continue                              # step 3.a.ii: frequentj stays Null
            tv = t[valid]
            count = cs[:, tv - lo] - cs[:, tv - w - lo]          # occurrences in s[t-w : t]
            # lexicographic key: count first, then most recent position.  Among symbols with
            # count >= 1 the last positions are distinct, so the argmax is unique.
            key = count.astype(np.int64) * (L + 1) + (lp[:, valid] + 1)
            out[j][tv - w1] = np.argmax(key, axis=0)
        T0 = T1
    return out


# ============================================================================================
# steps 2, 3.b-3.d -- the scoreboard and the correct[] array
# ============================================================================================
def run_scoreboard_literal(s_pred, frequent):
    """steps 2 and 3.b-3.d exactly as written, one step at a time (the readable oracle; used
    for the spec's worked-example trace and as the check on `run_scoreboard`).

    `s_pred[n]` is the symbol being predicted at step n (= s[w1+n]); `frequent[j][n]` is
    subpredictor j's value at that step (NULL = Null).  Returns (correct, scoreboard, winner,
    trace) with `winner` 1-based and trace[n] = (winner_used, prediction, correct_n,
    scoreboard_after) -- the columns of the table on PDF p. 58.
    """
    N = len(s_pred)
    J = len(frequent)
    correct = np.zeros(N, dtype=np.uint8)           # step 1: "each initialized to 0"
    scoreboard = [0] * J                            # step 2: "four counters, each initialized to 0"
    winner = 0                                      # step 2: "winner = 1"  (0-based index here)
    trace = []
    for n in range(N):                              # step 3: for i = w1+1 .. L
        si = int(s_pred[n])
        prediction = int(frequent[winner][n])       # 3.b  prediction = frequent_winner
        if prediction == si:                        # 3.c  (Null is NULL = -1, never equal)
            correct[n] = 1
        winner_used = winner
        for j in range(J):                          # 3.d  for j = 1 .. 4
            if int(frequent[j][n]) == si:           # 3.d.i    frequentj = si
                scoreboard[j] += 1                  # 3.d.i.1
                if scoreboard[j] >= scoreboard[winner]:   # 3.d.i.2  (winner as it stands now)
                    winner = j
        trace.append((winner_used + 1, prediction, int(correct[n]), list(scoreboard)))
    return correct, scoreboard, winner + 1, trace


def run_scoreboard(s_pred, frequent):
    """steps 2 and 3.b-3.d, visiting only the steps at which some frequentj equals si.

    A step where no subpredictor matches leaves everything unchanged: 3.c needs
    prediction = si with prediction one of the frequentj, and 3.d needs frequentj = si.  So
    skipping those steps is exact (tested against `run_scoreboard_literal`).
    Returns (correct, scoreboard, winner) with `winner` 1-based.
    """
    s_pred = np.asarray(s_pred, dtype=np.int64)
    N = int(s_pred.shape[0])
    J = len(frequent)
    mask = np.zeros(N, dtype=np.uint8)              # bit j set  <=>  frequentj = si
    for j in range(J):
        mask |= (np.asarray(frequent[j]) == s_pred).astype(np.uint8) << j

    correct = np.zeros(N, dtype=np.uint8)           # step 1
    scoreboard = [0] * J                            # step 2
    winner = 0                                      # step 2: winner = 1
    idx = np.flatnonzero(mask)
    for n, m in zip(idx.tolist(), mask[idx].tolist()):
        if (m >> winner) & 1:                       # 3.b + 3.c: frequent_winner = si
            correct[n] = 1
        for j in range(J):                          # 3.d
            if (m >> j) & 1:                        # 3.d.i
                scoreboard[j] += 1                  # 3.d.i.1
                if scoreboard[j] >= scoreboard[winner]:   # 3.d.i.2
                    winner = j
    return correct, scoreboard, winner + 1


# ============================================================================================
# steps 4-6 -- C, r, P_global, P'_global, P_local
# ============================================================================================
def longest_run_of_ones(correct):
    """step 6: 'the length of the longest run of ones in correct'."""
    c = np.asarray(correct, dtype=np.int8)
    if c.shape[0] == 0:
        return 0
    padded = np.concatenate(([0], c, [0]))
    d = np.diff(padded)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return int((ends - starts).max()) if starts.shape[0] else 0


def p_global_prime(C, N, z=Z_TEXT):
    """step 5.  Returns (P_global, P'_global); NaN where the text divides by zero."""
    if N <= 0:
        return float("nan"), float("nan")
    P = C / N
    if P == 0:
        return P, 1.0 - 0.01 ** (1.0 / N)
    if N - 1 == 0:
        return P, float("nan")                       # P(1-P)/(N-1) is x/0 or 0/0
    return P, min(1.0, P + z * math.sqrt(P * (1.0 - P) / (N - 1)))


def log_run_probability(p, r, N, steps=RECURRENCE_STEPS):
    """Natural log of step 6's right-hand side at P_local = p:

        (1 - p x) / ((r + 1 - r x) q) * 1 / x^(N+1),   q = 1 - p,
        x = x_steps,  x_j = 1 + q p^r x_(j-1)^(r+1),  x_0 = 1.

    Evaluated in logs as the text recommends.  x is carried as 1 + d (d = q p^r x^(r+1)) so
    that log(x) = log1p(d) keeps its precision when d is ~1e-8, which it is for N ~ 1e6.
    Returns -inf where the expression is not a positive number (q = 0, or 1 - p x <= 0, or
    r + 1 - r x <= 0), which the bisection treats as 'probability too small => p too large'.
    """
    q = 1.0 - p
    if not (0.0 <= p <= 1.0) or q <= 0.0:
        return -math.inf
    pr = p ** r
    d = 0.0                                          # x_0 = 1  ->  d_0 = 0
    for _ in range(steps):
        d = q * pr * (1.0 + d) ** (r + 1)            # x_j = 1 + q p^r x_(j-1)^(r+1)
    x = 1.0 + d
    numerator = 1.0 - p * x
    denominator = (r + 1 - r * x) * q
    if not (numerator > 0.0 and denominator > 0.0):
        return -math.inf
    return math.log(numerator) - math.log(denominator) - (N + 1) * math.log1p(d)


def p_local(r, N, confidence=CONFIDENCE, max_iter=4000):
    """step 6: bisection on [0, 1] for P_local such that the run probability equals 0.99.

    The right-hand side falls as p rises (more likely to see a long run), so a midpoint whose
    value is above the target is too small a p.  Stops when the midpoint can no longer be
    distinguished from an endpoint in binary64.
    """
    if N <= 0 or r < 1:
        return float("nan")
    target = math.log(confidence)
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        if not (lo < mid < hi):
            break
        if log_run_probability(mid, r, N) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def p_local_mp(r, N, dps=50, confidence=None):
    """step 6 in arbitrary precision (mpmath), same bisection; returns (float, decimal str).
    Imports mpmath lazily; raises ImportError if it is not installed."""
    import mpmath as mp  # optional dependency, not part of the default path

    with mp.workdps(dps):
        conf = mp.mpf("0.99") if confidence is None else mp.mpf(confidence)
        target = mp.log(conf)
        r_ = mp.mpf(r)
        Np1 = mp.mpf(N) + 1

        def f(p):
            q = 1 - p
            if q <= 0 or p < 0:
                return -mp.inf
            pr = p ** r_
            d = mp.mpf(0)
            for _ in range(RECURRENCE_STEPS):
                d = q * pr * (1 + d) ** (r_ + 1)
            x = 1 + d
            num = 1 - p * x
            den = (r_ + 1 - r_ * x) * q
            if num <= 0 or den <= 0:
                return -mp.inf
            return mp.log(num) - mp.log(den) - Np1 * mp.log1p(d)

        lo, hi = mp.mpf(0), mp.mpf(1)
        eps = mp.mpf(10) ** (-(dps - 3))
        while hi - lo > eps:
            mid = (lo + hi) / 2
            if f(mid) > target:
                lo = mid
            else:
                hi = mid
        p = (lo + hi) / 2
        return float(p), mp.nstr(p, dps - 5)


# ============================================================================================
# the estimator
# ============================================================================================
def to_bitstring(symbols, bits_per_symbol):
    """Section 3.1.3 (PDF p. 20): 'the sequential dataset that contains L samples (each having
    n bits) is considered as a bitstring of size nL'; glossary (PDF p. 69): 'The leftmost bit
    is the most significant bit' -- so each symbol contributes its bits MSB first."""
    s = np.asarray(symbols, dtype=np.int64)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.int64)
    return ((s[:, None] >> shifts) & 1).ravel()


def estimate(symbols, bits_per_symbol, *, windows=WINDOWS, z=Z_TEXT, k_mode="alphabet",
             plocal_mode="float", plocal_dps=50, chunk=32768, return_arrays=False,
             trace=False):
    """SP 800-90B section 6.3.7 on `symbols` (ints in [0, 2**bits_per_symbol)).

    Returns a dict whose keys 'C', 'r', 'N', 'P_global', "P_global'", 'P_local' and
    'min_entropy' carry the quantities the standard names (labels as the C++ prints them),
    plus: 'L', 'k', 'k_alphabet', 'k_observed', 'k_mode', 'windows', 'z', 'confidence',
    'scoreboard' (final), 'winner' (final, 1-based), 'longest_run', 'binding' (which of
    P'_global / P_local / 1/k decided step 7), 'P_local_changes_result' (P_local > P'_global),
    'plocal_mode', and 'ambiguities'.  With return_arrays=True also 'correct' (uint8 array)
    and 'frequent' (list of 4 int64 arrays in original symbol values, -1 = Null); with
    trace=True also 'trace' (per-step (winner_used, prediction, correct, scoreboard_after)).
    NaN marks every quantity the text does not define for the input.
    """
    s = np.asarray(symbols, dtype=np.int64).ravel()
    bits_per_symbol = int(bits_per_symbol)
    if bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be >= 1")
    k_alphabet = 1 << bits_per_symbol
    if s.shape[0] and (s.min() < 0 or s.max() >= k_alphabet):
        raise ValueError("symbols must lie in [0, 2**bits_per_symbol)")
    windows = tuple(int(w) for w in windows)
    L = int(s.shape[0])
    w1 = windows[0]
    N = L - w1                                       # step 1

    uniq, dense = np.unique(s, return_inverse=True) if L else (np.zeros(0, np.int64), s)
    k_observed = int(uniq.shape[0])
    if k_mode == "alphabet":
        k = k_alphabet
    elif k_mode == "observed":
        k = k_observed
    else:
        raise ValueError("k_mode must be 'alphabet' or 'observed'")

    nan = float("nan")
    result = {
        "min_entropy": nan, "C": nan, "r": nan, "N": N,
        "P_global": nan, "P_global'": nan, "P_local": nan,
        "L": L, "k": k, "k_alphabet": k_alphabet, "k_observed": k_observed, "k_mode": k_mode,
        "windows": list(windows), "z": z, "confidence": CONFIDENCE,
        "scoreboard": [0] * len(windows), "winner": 1, "longest_run": nan,
        "binding": None, "P_local_changes_result": None, "plocal_mode": plocal_mode,
        "ambiguities": list(AMBIGUITIES),
    }
    if N <= 0:                                       # the text defines nothing here
        if return_arrays:
            result["correct"] = np.zeros(0, dtype=np.uint8)
            result["frequent"] = [np.zeros(0, dtype=np.int64) for _ in windows]
        return result

    # step 3.a for every step, then steps 2/3.b-d
    frequent_dense = most_common_in_windows(dense.astype(np.int64), max(k_observed, 1), windows, chunk)
    s_pred = dense[w1:].astype(np.int64)
    if trace:
        correct, scoreboard, winner, tr = run_scoreboard_literal(s_pred, frequent_dense)
    else:
        correct, scoreboard, winner = run_scoreboard(s_pred, frequent_dense)

    # step 4
    C = int(correct.sum())
    # step 5
    P_global, P_global_prime = p_global_prime(C, N, z)
    # step 6
    longest = longest_run_of_ones(correct)
    r = longest + 1
    if plocal_mode == "float":
        P_local = p_local(r, N)
    elif plocal_mode == "mp":
        P_local, P_local_str = p_local_mp(r, N, dps=plocal_dps)
        result["P_local_mp_str"] = P_local_str
    else:
        raise ValueError("plocal_mode must be 'float' or 'mp'")
    # step 7
    candidates = {"P_global'": P_global_prime, "P_local": P_local, "1/k": 1.0 / k}
    if any(math.isnan(v) for v in candidates.values()):
        min_entropy = nan
        binding = None
    else:
        binding = max(candidates, key=candidates.get)
        min_entropy = -math.log2(candidates[binding])

    result.update({
        "min_entropy": min_entropy, "C": C, "r": r,
        "P_global": P_global, "P_global'": P_global_prime, "P_local": P_local,
        "scoreboard": scoreboard, "winner": winner, "longest_run": longest,
        "binding": binding,
        "P_local_changes_result": (None if math.isnan(P_local) or math.isnan(P_global_prime)
                                   else bool(P_local > P_global_prime)),
    })
    if return_arrays or trace:
        result["correct"] = correct
        # back to original symbol values, Null preserved
        result["frequent"] = [np.where(f == NULL, NULL, uniq[np.where(f == NULL, 0, f)])
                              for f in frequent_dense]
    if trace:
        # translate predictions from dense to original symbols
        result["trace"] = [(wu, (NULL if pred == NULL else int(uniq[pred])), c, sb)
                           for (wu, pred, c, sb) in tr]
    return result


# ============================================================================================
# command line
# ============================================================================================
def _json_ready(d):
    out = {}
    for key, v in d.items():
        if key in ("correct", "frequent", "trace"):
            continue
        if isinstance(v, np.generic):
            v = v.item()
        out[key] = v
    return out


def main(argv):
    if len(argv) < 3:
        sys.stderr.write("usage: multimcw.py <rawfile> <bits_per_symbol> [--literal|--bitstring] "
                         "[--z=2.576] [--k-mode=alphabet|observed] [--plocal=float|mp]\n")
        return 2
    path, bps = argv[1], int(argv[2])
    mode = "literal"
    opts = {}
    for a in argv[3:]:
        if a == "--literal":
            mode = "literal"
        elif a == "--bitstring":
            mode = "bitstring"
        elif a.startswith("--z="):
            opts["z"] = float(a[4:])
        elif a.startswith("--k-mode="):
            opts["k_mode"] = a[len("--k-mode="):]
        elif a.startswith("--plocal="):
            opts["plocal_mode"] = a[len("--plocal="):]
        elif a.startswith("--chunk="):
            opts["chunk"] = int(a[len("--chunk="):])
        else:
            sys.stderr.write(f"unknown option {a!r}\n")
            return 2
    raw = np.fromfile(path, dtype=np.uint8).astype(np.int64)
    symbols = raw & ((1 << bps) - 1)                 # one symbol per byte, low bps bits
    if mode == "bitstring":
        res = estimate(to_bitstring(symbols, bps), 1, **opts)
    else:
        res = estimate(symbols, bps, **opts)
    res["mode"] = mode
    res["file"] = path
    res["bits_per_symbol_declared"] = bps
    print(json.dumps(_json_ready(res), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
