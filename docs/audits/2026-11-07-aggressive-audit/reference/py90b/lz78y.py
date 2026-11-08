"""py90b.lz78y -- SP 800-90B section 6.3.10, The LZ78Y Prediction Estimate, written from the
published text only.

Source of authority: NIST SP 800-90B (January 2018), section 6.3.10 "The LZ78Y Prediction
Estimate", PDF pp. 63-65 of reference/sp800-90b.pages.txt (sha256 of the PDF 9b0dd771...defe7,
see AUDIT-BRIEF.md).  Nothing here was taken from the C++ under cpp/; the only borrowed items
are the verbose-output LABEL NAMES ("C", "r", "N", "P_global", "P_global'", "P_local",
"min entropy") from reference/cpp-verbose-labels-non_iid.txt so a differential driver can
match them.

The algorithm, quoted from the standard (PDF pp. 63-65).  The spec indexes S = (s1, ..., sL)
from 1; this file holds s[0..L-1] with s[m-1] = s_m.

  "Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},
   1. Let B = 16, and N = L - B - 1.  Let correct be an array of N Boolean values, each
      initialized to 0.  Let maxDictionarySize = 65 536.
   2. Let D be an empty dictionary.  Let dictionarySize = 0.
   3. For i = B+2 to L:
        a. For j = B down to 1:
             i.  If (s_(i-j-1), ..., s_(i-2)) is not in D, and dictionarySize < maxDictionarySize:
                   1. Let D[s_(i-j-1), ..., s_(i-2)] be added to the dictionary.
                   2. Let D[s_(i-j-1), ..., s_(i-2)][s_(i-1)] = 0.
                   3. dictionarySize = dictionarySize + 1
             ii. If (s_(i-j-1), ..., s_(i-2)) is in D,
                   1. Let D[s_(i-j-1), ..., s_(i-2)][s_(i-1)] = D[s_(i-j-1), ..., s_(i-2)][s_(i-1)] + 1.
        b. Use the dictionary to predict the next value, si.  Let prediction = Null, and let
           maxcount = 0.  For j = B down to 1:
             i.   Let prev = (s_(i-j), ... s_(i-1)).
             ii.  If prev is in the dictionary, find the y in {x1, ..., xk} that has the highest
                  D[prev][y] value.  In the event of a tie, let the y be the symbol with the
                  higher byte value.  For example, if D[prev][1] and D[prev][5] both have the
                  highest value, then y = 5.
             iii. If D[prev][y] > maxcount:
                   1. prediction = y.
                   2. maxcount = D[prev][y].
        c. If (prediction = si), let correct_(i-B-1) = 1.
   4. Calculate the predictor's global performance as P_global = C/N.  The upper bound of the
      99 % confidence interval on P_global, denoted P'_global is calculated as:
         P'_global = 1 - 0.01^(1/N),                                            if P_global = 0,
                   = min(1, P_global + 2.576 sqrt(P_global (1 - P_global) / (N - 1))),  otherwise
      where 2.576 corresponds to the Z(1-0.005) value.
   5. Calculate the predictor's local performance, based on the longest run of correct
      predictions.  Let r be one greater than the length of the longest run of ones in
      correct.  Use a binary search to solve the following for P_local:
         0.99 = (1 - P_local x) / ((r + 1 - r x) q) * 1 / x^(N+1),
      where q = 1 - P_local and x = x10, derived by iterating the recurrence relation
         x_j = 1 + q P_local^r x_(j-1)^(r+1)
      for j from 1 to 10, and x0 = 1.  Note that solving for P_local using the logarithm of
      these equations is robust against overflows.  Table 3 given in Appendix G.2 provides
      some pre-calculated values of P_local.
   6. The min-entropy is the negative logarithm of the greater performance metric
         min-entropy = -log2(max(P'_global, P_local, 1/k))."

(Step 4 of the text is labelled "4." although it follows step 3; the text has no separate
"Let C be the number of ones in correct" step for this estimator, unlike 6.3.7-6.3.9 -- C is
the count used in P_global = C/N and is returned under that name.)

Two implementations of step 3 are provided and tested against each other:

  * `predict_literal`   -- a line-by-line transliteration with tuple-keyed dictionaries.
                           O(L * B) Python operations; the one to read against the text.
  * `predict_vectorized` -- an exact re-derivation with numpy (see its docstring for the
                           argument that it computes the same `correct` array), fast enough
                           for L = 1 000 000 symbols / 8 000 000 bits.

Readings taken where the text leaves room (also listed in AMBIGUITIES and returned):

  * Step 3.a.i and 3.a.ii are two independent "If"s, not "If / Else if": a context added by
    3.a.i is then "in D" and 3.a.ii immediately increments its counter from 0 to 1.  The
    section's worked example requires this (D[1][3] is added at i = 7 and already predicts 3
    at i = 8, which needs D[1][3] > maxcount = 0).  Implemented literally.
  * Step 3.b.iii uses a strict ">", so when a longer context (examined first) and a shorter
    one have the same top count the LONGER context's symbol stands.  Implemented literally.
  * Step 3.b.ii's tie rule "higher byte value" is read as the larger symbol value, which is
    the same thing at every width this file accepts (1..8 bits).
  * "dictionarySize" counts contexts (keys of D), not (context, symbol) pairs; the text
    increments it once per added context.
  * k in step 6: the size of the output space A = {x1..xk} "specified by the submitter"
    (section 6, PDF p. 48), i.e. 2**bits_per_symbol by default.  `k_mode='observed'` uses the
    number of distinct symbols present instead.
  * 2.576 is used literally (step 4).  `z=` lets a driver substitute the binary64 0.995
    quantile 2.5758293035489008 that FORK-DIVERGENCE-AND-TRUST.md D-1 documents the fork using.
  * The binary search (step 5) has no stated bounds or tolerance; this file searches [0, 1]
    to the resolution of binary64 (until the midpoint stops moving).
  * N <= 0 (L <= B + 1 = 17): the text defines nothing; every statistic is returned as NaN.
  * N = 1 with P_global != 0: step 4 divides by N - 1 = 0; returned as NaN.
  * P_local is ALWAYS computed here, even when it cannot exceed P'_global (the C++ prints
    "P_local can't change the result." and omits the number in that case).  The dict carries
    `P_local_changes_result` so a driver can check the C++'s shortcut claim.
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

# ---- constants named in the text (PDF p. 63-64) --------------------------------------------
B_TEXT = 16                           # step 1: "Let B = 16"
MAX_DICTIONARY_SIZE = 65536           # step 1: "Let maxDictionarySize = 65 536"
Z_TEXT = 2.576                        # step 4: "where 2.576 corresponds to the Z(1-0.005) value"
Z_BINARY64 = 2.5758293035489008       # variant only (FORK-DIVERGENCE-AND-TRUST.md D-1); not the text's constant
CONFIDENCE = 0.99                     # step 5 left-hand side; step 4's "99 % confidence interval"
RECURRENCE_STEPS = 10                 # step 5: "x = x10 ... for j from 1 to 10, and x0 = 1"
NULL = -1                             # encoding of the spec's Null (symbols are >= 0)

AMBIGUITIES = [
    "step 3.a.i/ii are independent Ifs: a newly added context is counted 1 at once "
    "(settled by the worked example, i = 7 -> 8); an 'else if' reading would leave it at 0",
    "step 3.b.iii strict '>' hands a count tie between a longer and a shorter context to the "
    "longer (first examined) one; a '>=' reading would hand it to the shorter",
    "step 6 'k': 2**bits_per_symbol (the submitter-specified output space, default) vs the "
    "number of distinct symbols observed (k_mode='observed'); materially different when the "
    "data uses a strict subset of the alphabet and the predictor does worse than 1/k",
    "step 4 '2.576' is a printed rounding of the 0.995 normal quantile; the text's constant is "
    "the default here (z=2.576), the exact binary64 quantile is a variant (z=Z_BINARY64)",
    "step 5 'binary search': bounds and tolerance unstated; [0,1] to binary64 resolution here",
    "step 1 with L <= B + 1 gives N <= 0: undefined, returned as NaN",
    "step 4 with N = 1 and P_global != 0 divides by zero: undefined, returned as NaN",
    "Appendix G.2 Table 3 is labelled 'L = 1 000 000' but step 5 uses N; this file's solver "
    "reproduces 115 of its 136 rows to the printed 4 decimals with N = 1 000 000; the 21 rows "
    "labelled r = 55, 60, ..., 155 hold the values of r = 50, 55, ..., 150 (the label column "
    "skips 50), read as a misprint of the table's labels, not a property of step 5",
]


# ============================================================================================
# step 3, literal -- tuple-keyed dictionaries, one line per line of the text
# ============================================================================================
def predict_literal(symbols, B=B_TEXT, max_dictionary_size=MAX_DICTIONARY_SIZE, trace=False):
    """Steps 1-3 of 6.3.10 exactly as written.  Returns a dict with:
       'correct'          uint8 array of length N = L - B - 1 (empty if N <= 0),
       'prediction'       int64 array of length N (NULL = -1 where the text's prediction is Null),
       'dictionary_size'  final dictionarySize,
       'saturated'        True if dictionarySize reached max_dictionary_size,
       'saturation_i'     the spec's i at which it did (None if never),
       'trace'            (trace=True only) per-i list of (i, prediction, s_i, correct)."""
    s = [int(v) for v in symbols]                     # Python ints: tuple slicing is cheap
    L = len(s)
    N = L - B - 1                                     # step 1: "N = L - B - 1"
    correct = np.zeros(max(N, 0), dtype=np.uint8)     # step 1: "correct ... each initialized to 0"
    prediction_out = np.full(max(N, 0), NULL, dtype=np.int64)
    D = {}                                            # step 2: "Let D be an empty dictionary"
    dictionary_size = 0                               # step 2: "Let dictionarySize = 0"
    saturation_i = None
    rows = []
    for i in range(B + 2, L + 1):                     # step 3: "For i = B+2 to L"
        # -- step 3.a: every substring of the most recent B samples updates / joins D
        for j in range(B, 0, -1):                     # "For j = B down to 1"
            ctx = tuple(s[i - j - 2: i - 2])          # (s_(i-j-1), ..., s_(i-2))  [0-based i-j-2 .. i-3]
            nxt = s[i - 2]                            # s_(i-1)
            if ctx not in D and dictionary_size < max_dictionary_size:      # 3.a.i
                D[ctx] = {}                           # 3.a.i.1  "added to the dictionary"
                D[ctx][nxt] = 0                       # 3.a.i.2  "D[...][s_(i-1)] = 0"
                dictionary_size += 1                  # 3.a.i.3
                if dictionary_size == max_dictionary_size and saturation_i is None:
                    saturation_i = i
            if ctx in D:                                                    # 3.a.ii
                D[ctx][nxt] = D[ctx].get(nxt, 0) + 1  # 3.a.ii.1 "... + 1"
        # -- step 3.b: predict s_i from the longest-to-shortest previous contexts
        prediction = NULL                             # "Let prediction = Null"
        maxcount = 0                                  # "let maxcount = 0"
        for j in range(B, 0, -1):                     # "For j = B down to 1"
            prev = tuple(s[i - j - 1: i - 1])         # 3.b.i  prev = (s_(i-j), ..., s_(i-1))  [0-based i-j-1 .. i-2]
            if prev in D:                             # 3.b.ii "If prev is in the dictionary"
                counts = D[prev]
                top = max(counts.values())            # "the y that has the highest D[prev][y] value"
                y = max(yy for yy, c in counts.items() if c == top)   # tie: "the higher byte value"
                if counts[y] > maxcount:              # 3.b.iii "If D[prev][y] > maxcount"
                    prediction = y                    # 3.b.iii.1
                    maxcount = counts[y]              # 3.b.iii.2
        # -- step 3.c
        s_i = s[i - 1]
        hit = int(prediction != NULL and prediction == s_i)   # "If (prediction = si)"; Null never equals a symbol
        correct[i - B - 2] = hit                      # correct_(i-B-1)  [0-based i-B-2]
        prediction_out[i - B - 2] = prediction
        if trace:
            rows.append((i, prediction, s_i, hit))
    out = {
        "correct": correct, "prediction": prediction_out,
        "dictionary_size": dictionary_size,
        "saturated": dictionary_size >= max_dictionary_size and N > 0,
        "saturation_i": saturation_i,
    }
    if trace:
        out["trace"] = rows
    return out


# ============================================================================================
# step 3, vectorized -- the same `correct`, derived without the step-by-step loop
# ============================================================================================
def predict_vectorized(symbols, k, B=B_TEXT, max_dictionary_size=MAX_DICTIONARY_SIZE):
    """Steps 1-3 of 6.3.10 computed with numpy.  Same return keys as predict_literal (no
    trace).  `k` must exceed every symbol value (it is only used to pack pairs into one int).

    Why this equals the literal loop (0-based positions; q = index of the LAST symbol of a
    context; the spec's step i works on update contexts ending at q = i-3 with next symbol
    s[q+1] = s_(i-1), and predicts s[q'+1] from contexts ending at q' = i-2):

    * Identity of contexts.  A context is the tuple (s[q-j+1..q]); `ids[j][q]` below is an
      integer that is equal for two positions iff their j-tuples are equal (built by prefix
      extension: id_j(q) = unique(id_(j-1)(q-1), s[q])).  The dictionary key is (j, id).

    * Membership (3.a.i).  The update loop visits, in time order, the contexts ending at
      q = B-1, B, ..., L-3, and within one q the lengths j = B, ..., 1.  A context is added the
      FIRST time it is visited if dictionarySize < max at that moment, and membership never
      changes afterwards.  So the set of members is exactly the first `max_dictionary_size`
      distinct keys in the visiting order (first-visit position ascending, then j descending),
      and a key first visited at q_first is a member from the update at q_first onward.

    * Counts (3.a.ii).  For a member key, every visit at q (including the first, whose 3.a.i
      sets 0 and whose 3.a.ii then adds 1) adds one to D[ctx][s[q+1]].  So just before the
      prediction at step i (context ending at q' = i-2), D[ctx] is the histogram of s[q+1]
      over the member's visits at q in [B-1, q'-1] -- i.e. over all its earlier positions,
      because no position before B-1 is ever visited.

    * Argmax with the tie rule (3.b.ii).  After m visits with symbols y_1..y_m, the pair
      (highest count, largest y attaining it) equals the lexicographic maximum over
      t <= m of (c_t, y_t), where c_t is the running count of y_t among y_1..y_t.  (The
      winning y's last visit has c = its final count = the maximum; no other visit can
      exceed that count, and among visits with that count the largest y wins.)  So a
      per-group running maximum of the packed pair c*k + y gives D[prev][y] and y.

    * "prev is in the dictionary" (3.b.ii) at step i means: key (j, id_j(q')) is a member and
      was visited at some q <= q'-1, i.e. this is not the context's first position.

    * Choice across j (3.b.iii).  j = B..1 with a strict ">" starting from maxcount = 0 is
      applied exactly as written, as a vectorized pass per j in descending order.
    """
    s = np.asarray(symbols, dtype=np.int64).ravel()
    L = int(s.shape[0])
    N = L - B - 1                                                    # step 1
    out = {"correct": np.zeros(max(N, 0), dtype=np.uint8),
           "prediction": np.full(max(N, 0), NULL, dtype=np.int64),
           "dictionary_size": 0, "saturated": False, "saturation_i": None}
    if N <= 0:
        return out
    k = int(k)

    # --- context ids: ids[j][q] identifies the j-tuple ending at q (valid for q >= j-1) ------
    ids = [None] * (B + 1)
    ids[1] = s.astype(np.int32)
    for j in range(2, B + 1):
        # pair (id_(j-1)(q-1), s[q]) for q >= j-1; id_(j-1) < L and s < k so the pack is exact
        pair = ids[j - 1][j - 2: L - 1].astype(np.int64) * k + s[j - 1:]
        _, inv = np.unique(pair, return_inverse=True)
        row = np.empty(L, dtype=np.int32)
        row[: j - 1] = -1
        row[j - 1:] = inv.astype(np.int32)
        ids[j] = row

    # --- membership: first visit of every (j, id) over the update positions q in [B-1, L-3] --
    first_q, first_j, first_id = [], [], []
    for j in range(1, B + 1):
        seg = ids[j][B - 1: L - 2]                                   # q = B-1 .. L-3
        uniq, idx = np.unique(seg, return_index=True)                 # idx = first index in seg
        first_q.append(idx.astype(np.int64) + (B - 1))
        first_j.append(np.full(uniq.shape[0], j, dtype=np.int64))
        first_id.append(uniq.astype(np.int64))
    first_q = np.concatenate(first_q)
    first_j = np.concatenate(first_j)
    first_id = np.concatenate(first_id)
    visit_order = np.lexsort((-first_j, first_q))                    # q ascending, then j descending
    n_members = min(max_dictionary_size, visit_order.shape[0])
    members = visit_order[:n_members]
    out["dictionary_size"] = int(n_members)
    if visit_order.shape[0] > max_dictionary_size:
        out["saturated"] = True
        out["saturation_i"] = int(first_q[visit_order[max_dictionary_size - 1]] + 3)   # q = i - 3
    elif n_members == max_dictionary_size:
        out["saturated"] = True
        out["saturation_i"] = int(first_q[visit_order[-1]] + 3)
    member_mask = [None] * (B + 1)
    for j in range(1, B + 1):
        sel = members[first_j[members] == j]
        mask = np.zeros(int(ids[j].max()) + 1, dtype=bool)
        mask[first_id[sel]] = True
        member_mask[j] = mask

    # --- per length j: running (count, symbol) argmax within each member context --------------
    q_all = np.arange(B - 1, L - 1, dtype=np.int64)                  # positions B-1 .. L-2
    pred_pos = np.arange(B, L - 1, dtype=np.int64)                   # prediction contexts end at q' = B .. L-2
    prediction = np.full(N, NULL, dtype=np.int64)                    # "Let prediction = Null"
    maxcount = np.zeros(N, dtype=np.int64)                           # "let maxcount = 0"
    for j in range(B, 0, -1):                                        # "For j = B down to 1"
        g_all = ids[j][q_all]
        keep = member_mask[j][g_all]
        if not keep.any():
            continue
        q = q_all[keep]
        g = g_all[keep].astype(np.int64)
        y = s[q + 1]                                                 # the symbol that followed this context
        order = np.argsort(g, kind="stable")                         # (context, position) order
        g_s, q_s, y_s = g[order], q[order], y[order]
        n = g_s.shape[0]
        new_grp = np.empty(n, dtype=bool)
        new_grp[0] = True
        new_grp[1:] = g_s[1:] != g_s[:-1]
        grp = np.cumsum(new_grp) - 1
        start = np.flatnonzero(new_grp)
        rank = np.arange(n, dtype=np.int64) - start[grp]             # number of earlier visits
        # running count of y within (context, y)
        key2 = g_s * k + y_s
        order2 = np.argsort(key2, kind="stable")
        key2_s = key2[order2]
        new_sub = np.empty(n, dtype=bool)
        new_sub[0] = True
        new_sub[1:] = key2_s[1:] != key2_s[:-1]
        sub = np.cumsum(new_sub) - 1
        start2 = np.flatnonzero(new_sub)
        c_sorted = np.arange(n, dtype=np.int64) - start2[sub] + 1
        c = np.empty(n, dtype=np.int64)
        c[order2] = c_sorted
        # group-wise inclusive running max of the packed pair (c, y); then exclusive shift
        val = c * k + y_s
        big = (n + 1) * k
        inc = np.maximum.accumulate(val + grp * big) - grp * big
        excl = np.empty(n, dtype=np.int64)
        excl[0] = -1
        excl[1:] = inc[:-1]
        in_d = rank > 0                                              # "prev is in the dictionary"
        cand_c = np.where(in_d, excl // k, 0)
        cand_y = np.where(in_d, excl % k, NULL)
        # scatter to the prediction index n_pred = q' - B for q' in [B, L-2]
        is_pred = q_s >= B
        idx = q_s[is_pred] - B
        cc = cand_c[is_pred]
        cy = cand_y[is_pred]
        take = cc > maxcount[idx]                                    # 3.b.iii "If D[prev][y] > maxcount"
        idx_t = idx[take]
        prediction[idx_t] = cy[take]                                 # 3.b.iii.1
        maxcount[idx_t] = cc[take]                                   # 3.b.iii.2
    target = s[pred_pos + 1]                                         # s_i
    correct = ((prediction != NULL) & (prediction == target)).astype(np.uint8)   # 3.c
    out["correct"] = correct
    out["prediction"] = prediction
    return out


# ============================================================================================
# steps 4-6 -- C, P_global, P'_global, r, P_local, min-entropy
# ============================================================================================
def longest_run_of_ones(correct):
    """step 5: 'the length of the longest run of ones in correct'."""
    c = np.asarray(correct, dtype=np.int8)
    if c.shape[0] == 0:
        return 0
    padded = np.concatenate(([0], c, [0]))
    d = np.diff(padded)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return int((ends - starts).max()) if starts.shape[0] else 0


def p_global_prime(C, N, z=Z_TEXT):
    """step 4.  Returns (P_global, P'_global); NaN where the text divides by zero."""
    if N <= 0:
        return float("nan"), float("nan")
    P = C / N
    if P == 0:
        return P, 1.0 - 0.01 ** (1.0 / N)                 # "1 - 0.01^(1/N), if P_global = 0"
    if N - 1 == 0:
        return P, float("nan")                            # P(1-P)/(N-1) is x/0 or 0/0
    return P, min(1.0, P + z * math.sqrt(P * (1.0 - P) / (N - 1)))


def log_run_probability(p, r, N, steps=RECURRENCE_STEPS):
    """Natural log of step 5's right-hand side at P_local = p:

        (1 - p x) / ((r + 1 - r x) q) * 1 / x^(N+1),   q = 1 - p,
        x = x_steps,  x_j = 1 + q p^r x_(j-1)^(r+1),  x_0 = 1.

    Evaluated in logs as the text recommends.  x is carried as 1 + d (d = q p^r x^(r+1)) so
    that log(x) = log1p(d) keeps its precision when d is tiny, which it is for N ~ 1e6.
    Returns -inf where the expression is not a positive number (q = 0, or 1 - p x <= 0, or
    r + 1 - r x <= 0); the bisection treats that as 'probability too small => p too large'.
    """
    q = 1.0 - p
    if not (0.0 <= p <= 1.0) or q <= 0.0:
        return -math.inf
    pr = p ** r
    d = 0.0                                               # x_0 = 1  ->  d_0 = 0
    for _ in range(steps):
        d = q * pr * (1.0 + d) ** (r + 1)                 # x_j = 1 + q p^r x_(j-1)^(r+1)
    x = 1.0 + d
    numerator = 1.0 - p * x
    denominator = (r + 1 - r * x) * q
    if not (numerator > 0.0 and denominator > 0.0):
        return -math.inf
    return math.log(numerator) - math.log(denominator) - (N + 1) * math.log1p(d)


def p_local(r, N, confidence=CONFIDENCE, max_iter=4000):
    """step 5: bisection on [0, 1] for P_local such that the run probability equals 0.99.

    The right-hand side is the probability of seeing no run of r successes in N+1 trials at
    success probability p; it falls as p rises, so a midpoint whose value is above the target
    is too small a p.  Stops when the midpoint can no longer be distinguished from an endpoint
    in binary64.
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


def estimate(symbols, bits_per_symbol, *, B=B_TEXT, max_dictionary_size=MAX_DICTIONARY_SIZE,
             z=Z_TEXT, k_mode="alphabet", method="vectorized", return_arrays=False,
             trace=False):
    """SP 800-90B section 6.3.10 on `symbols` (ints in [0, 2**bits_per_symbol)).

    Returns a dict whose keys 'C', 'r', 'N', 'P_global', "P_global'", 'P_local' and
    'min_entropy' carry the quantities the standard names (labels as the C++ prints them),
    plus: 'L', 'k', 'k_alphabet', 'k_observed', 'k_mode', 'B', 'max_dictionary_size',
    'dictionary_size' (final dictionarySize), 'saturated' (the cap was reached),
    'saturation_i' (the spec's i at which it was reached, or None), 'z', 'confidence',
    'longest_run', 'binding' (which of P'_global / P_local / 1/k decided step 6),
    'P_local_changes_result' (P_local > P'_global), 'method', and 'ambiguities'.
    With return_arrays=True also 'correct' (uint8) and 'prediction' (int64, -1 = Null);
    with trace=True (forces method='literal') also 'trace' = [(i, prediction, s_i, correct)].
    NaN marks every quantity the text does not define for the input.
    """
    s = np.asarray(symbols, dtype=np.int64).ravel()
    bits_per_symbol = int(bits_per_symbol)
    if bits_per_symbol < 1 or bits_per_symbol > 8:
        raise ValueError("bits_per_symbol must be in 1..8")
    k_alphabet = 1 << bits_per_symbol
    if s.shape[0] and (s.min() < 0 or s.max() >= k_alphabet):
        raise ValueError("symbols must lie in [0, 2**bits_per_symbol)")
    B = int(B)
    max_dictionary_size = int(max_dictionary_size)
    L = int(s.shape[0])
    N = L - B - 1                                        # step 1

    k_observed = int(np.unique(s).shape[0]) if L else 0
    if k_mode == "alphabet":
        k = k_alphabet
    elif k_mode == "observed":
        k = k_observed
    else:
        raise ValueError("k_mode must be 'alphabet' or 'observed'")
    if trace:
        method = "literal"
    if method not in ("literal", "vectorized"):
        raise ValueError("method must be 'literal' or 'vectorized'")

    nan = float("nan")
    result = {
        "min_entropy": nan, "C": nan, "r": nan, "N": N,
        "P_global": nan, "P_global'": nan, "P_local": nan,
        "L": L, "k": k, "k_alphabet": k_alphabet, "k_observed": k_observed, "k_mode": k_mode,
        "B": B, "max_dictionary_size": max_dictionary_size,
        "dictionary_size": 0, "saturated": False, "saturation_i": None,
        "z": z, "confidence": CONFIDENCE, "longest_run": nan,
        "binding": None, "P_local_changes_result": None, "method": method,
        "ambiguities": list(AMBIGUITIES),
    }
    if N <= 0:                                           # the text defines nothing here
        if return_arrays:
            result["correct"] = np.zeros(0, dtype=np.uint8)
            result["prediction"] = np.zeros(0, dtype=np.int64)
        return result

    # steps 1-3
    if method == "literal":
        pred = predict_literal(s, B, max_dictionary_size, trace=trace)
    else:
        pred = predict_vectorized(s, k_alphabet, B, max_dictionary_size)
    correct = pred["correct"]
    # step 4
    C = int(correct.sum())
    P_global, P_global_prime = p_global_prime(C, N, z)
    # step 5
    longest = longest_run_of_ones(correct)
    r = longest + 1                                      # "one greater than the length of the longest run"
    P_local = p_local(r, N)
    # step 6
    candidates = {"P_global'": P_global_prime, "P_local": P_local, "1/k": (1.0 / k if k else nan)}
    if any(math.isnan(v) for v in candidates.values()):
        min_entropy = nan
        binding = None
    else:
        binding = max(candidates, key=candidates.get)
        min_entropy = -math.log2(candidates[binding])

    result.update({
        "min_entropy": min_entropy, "C": C, "r": r,
        "P_global": P_global, "P_global'": P_global_prime, "P_local": P_local,
        "dictionary_size": pred["dictionary_size"], "saturated": bool(pred["saturated"]),
        "saturation_i": pred["saturation_i"],
        "longest_run": longest, "binding": binding,
        "P_local_changes_result": (None if math.isnan(P_local) or math.isnan(P_global_prime)
                                   else bool(P_local > P_global_prime)),
    })
    if return_arrays or trace:
        result["correct"] = correct
        result["prediction"] = pred["prediction"]
    if trace:
        result["trace"] = pred["trace"]
    return result


# ============================================================================================
# command line
# ============================================================================================
def _json_ready(d):
    out = {}
    for key, v in d.items():
        if key in ("correct", "prediction", "trace"):
            continue
        if isinstance(v, np.generic):
            v = v.item()
        out[key] = v
    return out


def main(argv):
    if len(argv) < 3:
        sys.stderr.write("usage: lz78y.py <rawfile> <bits_per_symbol> [--literal|--bitstring] "
                         "[--z=2.576] [--k-mode=alphabet|observed] [--method=vectorized|literal] "
                         "[--B=16] [--max-dict=65536]\n")
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
        elif a.startswith("--method="):
            opts["method"] = a[len("--method="):]
        elif a.startswith("--B="):
            opts["B"] = int(a[len("--B="):])
        elif a.startswith("--max-dict="):
            opts["max_dictionary_size"] = int(a[len("--max-dict="):])
        else:
            sys.stderr.write(f"unknown option {a!r}\n")
            return 2
    raw = np.fromfile(path, dtype=np.uint8).astype(np.int64)
    symbols = raw & ((1 << bps) - 1)                     # one symbol per byte, low bps bits
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
