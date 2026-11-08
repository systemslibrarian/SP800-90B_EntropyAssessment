"""py90b.multimmc -- SP 800-90B section 6.3.9, the MultiMMC prediction estimate, written from
the published text only.

Source of authority: NIST SP 800-90B (January 2018), section 6.3.9 "The MultiMMC Prediction
Estimate", PDF pp. 60-63 of reference/sp800-90b.pages.txt (PDF sha256 9b0dd771...defe7, see
AUDIT-BRIEF.md).  Nothing here was taken from the C++ under cpp/; the only borrowed items are
the verbose-output LABEL NAMES ("C", "r", "N", "P_global", "P_global'", "P_local",
"min entropy") from reference/cpp-verbose-labels-non_iid.txt so a differential driver can
match them.

The algorithm, quoted from the standard (PDF pp. 61-62).  The spec indexes S = (s1, ..., sL)
from 1; this file holds s[0..L-1] with s[t] = s_(t+1), so s_i is s[i-1], the d-tuple
(s_(i-d), ..., s_(i-1)) is the slice s[i-d-1 : i-1], (s_(i-d-1), ..., s_(i-2)) is
s[i-d-2 : i-2], and correct_(i-2) is correct[i-3].

  "Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},
   1. Let D = 16, and N = L - 2.  Let subpredict be a list of D values, each initialized to
      Null.  Let correct be an array of N values, each initialized to 0.  Let entries be an
      array of D values, each initialized to 0, and let maxEntries = 100 000.
   2. For d = 1 to D, let Md be a set of counters, where Md[x, y] denotes the number of
      observed transitions from output x to output y for the dth-order MMC.
   3. Let scoreboard be a list of D counters, each initialized to 0.  Let winner = 1.
   4. For i = 3 to L:
        a. For d = 1 to D:
             i. If d < i-1:
                  1. If [(s_(i-d-1), ..., s_(i-2)), s_(i-1)] is in Md, increment
                     Md[(s_(i-d-1), ..., s_(i-2)), s_(i-1)] by 1.
                  2. Else if entries_d < maxEntries, add a counter for
                     [(s_(i-d-1), ..., s_(i-2)), s_(i-1)] to the set, let
                     Md[(s_(i-d-1), ..., s_(i-2)), s_(i-1)] = 1 and increment entries_d by 1.
        b. For d = 1 to D:
             i. If d < i, find the y value that corresponds to the highest
                Md[(s_(i-d), ..., s_(i-1)), y] value, and denote that y as ymax.  If there is
                a tie, let ymax be the greatest y in the tie.  Let subpredict_d = ymax.  If
                all possible values of Md[(s_(i-d), ..., s_(i-1)), y] are 0, then let
                subpredict_d = Null.
        c. Let prediction = subpredict_winner.
        d. If (prediction = si), let correct_(i-2) = 1.
        e. Update the scoreboard.  For d = 1 to D:
             i. If (subpredict_d = si)
                  1. Let scoreboard_d = scoreboard_d + 1.
                  2. If scoreboard_d >= scoreboard_winner, let winner = d.
   5. Let C be the number of ones in correct.
   6. Calculate the predictor's global performance as P_global = C/N.  The upper bound of
      the 99 % confidence interval on P_global, denoted P'_global is calculated as:
         P'_global = 1 - 0.01^(1/N)                                               if P_global = 0,
                   = min(1, P_global + 2.576 sqrt(P_global (1 - P_global)/(N - 1)))  otherwise
      where 2.576 corresponds to the Z(1-0.005) value.
   7. Calculate the predictor's local performance, based on the longest run of correct
      predictions.  Let r be one greater than the length of the longest run of ones in
      correct.  Use a binary search to solve the following for P_local:
         0.99 = (1 - P_local x) / ((r + 1 - r x) q)  *  1 / x^(N+1),
      where q = 1 - P_local and x = x10, derived by iterating the recurrence relation
         x_j = 1 + q P_local^r x_(j-1)^(r+1)
      for j from 1 to 10, and x0 = 1.  Note that solving for P_local using the logarithm of
      these equations is robust against overflows.
   8. The min-entropy is the negative logarithm of the greater performance metric
         min-entropy = -log2(max(P'_global, P_local, 1/k))."

Readings taken where the text leaves room (the module-level AMBIGUITIES list repeats these and
is returned in every result; where a reading is selectable the `estimate` option is named):

  * step 1 / 4.a.i.2 "entries" / "maxEntries": the text adds "a counter for [(context),
    s_(i-1)]" and increments entries_d once per counter added, so entries_d counts distinct
    [context, next-symbol] PAIRS and a pair not among the first 100 000 distinct pairs of
    order d is never counted -- even when its context already has other counters.  That is
    the literal reading and the default (entries_mode='pairs').  entries_mode='contexts' is a
    NON-LITERAL variant in which the cap counts distinct contexts and a pair whose context is
    already present is always added; it exists only so a differential driver can diagnose a
    mismatch, and the two differ materially at width 8 (tested).
  * step 4.b.i tie rule: "the greatest y" is the numerically greatest symbol value.
  * step 4.d: Null is not equal to any symbol, so a Null prediction (an unseen context, or an
    order with no data yet) leaves correct_(i-2) = 0 and therefore ENDS a run of correct
    predictions.  The worked example (PDF p. 62) shows prediction = Null, correct = 0 at
    i = 3 and i = 4.  (FORK-DIVERGENCE-AND-TRUST.md D-4 records that NIST's code chose
    otherwise; this file follows the text.)
  * step 4.e.i.2: "scoreboard_winner" is read as it stands at that moment, so `winner` may
    already have been changed earlier in the same d loop, and ">=" hands a tie to the LARGER
    d.  Section 6.3.7 uses identical wording and its worked example (PDF p. 58, i = 7 and
    i = 12) is reproducible only under this reading (see py90b.multimcw); the 6.3.9 example
    never changes winner, so it cannot distinguish the readings on its own.
  * step 8 "k": the size of the output space A = {x1..xk} "specified by the submitter"
    (section 6, PDF p. 48), i.e. 2**bits_per_symbol.  k_mode='observed' uses the number of
    distinct symbols actually present instead.
  * step 6 "2.576" is used literally.  `z=` lets a driver substitute the binary64 0.995
    quantile 2.5758293035489008 that FORK-DIVERGENCE-AND-TRUST.md D-1/C22c documents.
  * step 7 "binary search": bounds and tolerance are unstated; this file searches [0, 1] to
    the resolution of binary64 (until the midpoint stops moving).
  * N <= 0 (L <= 2): the spec defines nothing; every statistic is returned as NaN.
  * N = 1 (L = 3): the single prediction at i = 3 comes from M1 after it has learned the one
    transition s1 -> s2, so it is s2 when s2 = s1 and Null otherwise.  If s1 = s2 = s3 it is
    correct, P_global = 1, and step 6's second branch divides P(1-P) = 0 by N - 1 = 0:
    undefined, returned as NaN.  In every other L = 3 case P_global = 0 and the first branch
    gives P'_global = 1 - 0.01^(1/1) = 0.99.
  * P_local is ALWAYS computed here, even when it cannot exceed P'_global (the C++ prints
    "P_local can't change the result." and omits the number in that case).  The dict carries
    `P_local_changes_result` so a driver can check that shortcut's claim.

Two implementations of steps 1-4 are provided and tested against each other:
  * `run_predictor_literal` -- the text transcribed one line at a time with Python dicts
    keyed by the spec's tuples.  O(L * D * d) and slow, but the one to read.
  * `run_predictor` -- the same arithmetic reorganised so that numpy does the n-gram
    identification (dense ids by extending (n-1)-gram ids, i.e. prefix extension) and the
    dictionary-cap admission (a pair is counted iff it is among the first maxEntries distinct
    pairs by first learn event, which is a pure function of the data), leaving a sequential
    loop per order that maintains each context's running (count, y) maximum, and a second
    sequential loop for the scoreboard.  This is what `estimate` uses by default.
"""
from __future__ import annotations

import copy
import json
import math
import sys

import numpy as np

# ---- constants named in the text (PDF p. 61) -------------------------------------------
D_TEXT = 16                           # step 1: "Let D = 16"
MAX_ENTRIES_TEXT = 100_000            # step 1: "let maxEntries = 100 000"
Z_TEXT = 2.576                        # step 6: "where 2.576 corresponds to the Z(1-0.005) value"
Z_BINARY64 = 2.5758293035489008       # variant only (FORK-DIVERGENCE-AND-TRUST.md D-1); not the text's constant
CONFIDENCE = 0.99                     # step 7 left-hand side; step 6's "99 % confidence interval"
RECURRENCE_STEPS = 10                 # step 7: "x = x10 ... for j from 1 to 10, and x0 = 1"
NULL = -1                             # encoding of the spec's Null (symbols are >= 0)

AMBIGUITIES = [
    "step 1/4.a.i.2 'entries'/'maxEntries': counts distinct [context, next-symbol] pairs "
    "(literal, default entries_mode='pairs'); a non-literal variant counting distinct contexts "
    "is exposed as entries_mode='contexts' for differential diagnosis only",
    "step 4.b.i tie rule 'the greatest y': the numerically greatest symbol value",
    "step 4.d: a Null prediction is not equal to s_i, so it leaves correct = 0 and ends a run "
    "(the worked example shows this at i = 3, 4); D-4 records that NIST's code differed",
    "step 4.e.i.2: 'scoreboard_winner' is read live inside the d loop, so a tie goes to the "
    "larger d and winner can change several times in one step; 6.3.7's worked example "
    "requires this reading of the identical wording, 6.3.9's example cannot distinguish it",
    "step 8 'k': 2**bits_per_symbol (the submitter-specified output space, default) vs the "
    "number of distinct symbols observed (k_mode='observed')",
    "step 6 '2.576' is a printed rounding of the 0.995 normal quantile; the text's constant is "
    "the default (z=2.576), the exact binary64 quantile is a variant (z=Z_BINARY64)",
    "step 7 'binary search': bounds and tolerance unstated; [0,1] to binary64 resolution here",
    "step 1 with L <= 2 gives N <= 0: undefined, returned as NaN",
    "step 6 with N = 1 and P_global = 1 (L = 3, s1 = s2 = s3) divides 0 by N - 1 = 0: "
    "undefined, returned as NaN; any other L = 3 input has P_global = 0 and P'_global = 0.99",
    "Appendix G.2 Table 3 is labelled 'L = 1 000 000' but step 7 uses N = L - 2; at the table's "
    "4 printed decimals the two are indistinguishable",
]


# ============================================================================================
# steps 1-4, transcribed one line at a time (the readable oracle)
# ============================================================================================
def run_predictor_literal(s, D=D_TEXT, max_entries=MAX_ENTRIES_TEXT, entries_mode="pairs",
                          trace=False):
    """Steps 1-4 of section 6.3.9 exactly as written, with Python dicts keyed by the spec's
    tuples.  `s` is a sequence of non-negative ints.

    Returns a dict:
      'correct'     list of N ints (step 1 / 4.d)
      'scoreboard'  final list of D counters (1-based positions 0..D-1 hold d = 1..D)
      'winner'      final winner, 1-based
      'entries'     final entries_d per order (list of D)
      'refused'     number of step-4.a learn events per order that 4.a.i.2 declined (cap hit)
      'subpredict'  list of D lists indexed by the spec's i (0..L); subpredict[d-1][i] is
                    subpredict_d after step 4.b at step i, NULL where undefined
      'trace'       (trace=True) one row per i: dict(i, subpredict, scoreboard_4c, winner_4c,
                    prediction, s_i, correct, scoreboard_4e) -- the columns of the table on
                    PDF p. 62
      'models'      (trace=True) per i, the D models after step 4.a as
                    {context tuple: {y: count}} -- the table on PDF p. 63
    """
    if entries_mode not in ("pairs", "contexts"):
        raise ValueError("entries_mode must be 'pairs' or 'contexts'")
    s = [int(v) for v in s]
    L = len(s)
    N = L - 2                                       # step 1: N = L - 2
    subpredict = [NULL] * (D + 1)                   # step 1: D values, each Null (1-based)
    correct = [0] * max(N, 0)                       # step 1: N values, each 0
    entries = [0] * (D + 1)                         # step 1: D values, each 0 (1-based)
    refused = [0] * (D + 1)
    M = [None] + [dict() for _ in range(D)]         # step 2: M[d][x] = {y: count}; absent = 0
    scoreboard = [0] * (D + 1)                      # step 3: D counters, each 0 (1-based)
    winner = 1                                      # step 3: winner = 1
    trace_rows = []
    models = []
    sub_hist = [[NULL] * (L + 1) for _ in range(D)]

    for i in range(3, L + 1):                       # step 4: for i = 3 to L
        # ---- 4.a: record the transition that ended at s_(i-1) in every order that has it
        for d in range(1, D + 1):
            if d < i - 1:                           # 4.a.i
                x = tuple(s[i - d - 2: i - 2])      #   (s_(i-d-1), ..., s_(i-2))
                y = s[i - 2]                        #   s_(i-1)
                counters = M[d].get(x)
                if counters is not None and y in counters:
                    counters[y] += 1                # 4.a.i.1: in Md -> increment
                else:
                    if entries_mode == "pairs":     # 4.a.i.2 as written: one entry per counter
                        allowed = entries[d] < max_entries
                        counts_as_entry = True
                    elif counters is not None:      # variant: context present -> pair is free
                        allowed = True
                        counts_as_entry = False
                    else:                           # variant: new context -> counts against cap
                        allowed = entries[d] < max_entries
                        counts_as_entry = True
                    if allowed:
                        if counters is None:
                            counters = M[d][x] = {}
                        counters[y] = 1             #   let Md[x, y] = 1
                        if counts_as_entry:
                            entries[d] += 1         #   increment entries_d by 1
                    else:
                        refused[d] += 1
        if trace:
            models.append([copy.deepcopy(M[d]) for d in range(1, D + 1)])

        # ---- 4.b: each order predicts s_i from the context (s_(i-d), ..., s_(i-1))
        for d in range(1, D + 1):
            if d < i:                               # 4.b.i
                x = tuple(s[i - d - 1: i - 1])      #   (s_(i-d), ..., s_(i-1))
                counters = M[d].get(x)
                if counters:
                    # highest Md[x, y]; "If there is a tie, let ymax be the greatest y"
                    subpredict[d] = max(counters, key=lambda yy: (counters[yy], yy))
                else:
                    subpredict[d] = NULL            #   all Md[x, y] are 0 -> Null
            sub_hist[d - 1][i] = subpredict[d]

        # ---- 4.c / 4.d
        prediction = subpredict[winner]             # 4.c
        si = s[i - 1]                               # s_i
        scoreboard_4c = scoreboard[1:]
        winner_4c = winner
        if prediction == si:                        # 4.d  (NULL never equals a symbol)
            correct[i - 3] = 1                      #   correct_(i-2) = 1

        # ---- 4.e: scoreboard
        for d in range(1, D + 1):
            if subpredict[d] == si:                 # 4.e.i
                scoreboard[d] += 1                  # 4.e.i.1
                if scoreboard[d] >= scoreboard[winner]:   # 4.e.i.2 (winner as it stands now)
                    winner = d
        if trace:
            trace_rows.append({
                "i": i, "subpredict": tuple(subpredict[1:]), "scoreboard_4c": scoreboard_4c,
                "winner_4c": winner_4c, "prediction": prediction, "s_i": si,
                "correct": correct[i - 3], "scoreboard_4e": scoreboard[1:],
            })

    out = {
        "correct": correct, "scoreboard": scoreboard[1:], "winner": winner,
        "entries": entries[1:], "refused": refused[1:], "subpredict": sub_hist,
    }
    if trace:
        out["trace"] = trace_rows
        out["models"] = models
    return out


# ============================================================================================
# steps 1-4, reorganised for speed (numpy n-gram ids + cap admission, short sequential loops)
# ============================================================================================
def _extend_ngram_ids(prev_ids, s, k, n):
    """Dense ids for the n-grams of s from dense ids of its (n-1)-grams.

    prev_ids[e] is the id of the (n-1)-gram ending at e (valid for e >= n-2); the returned
    array holds the id of the n-gram ending at e for e >= n-1 and -1 before that.  Two
    n-grams get the same id iff they are equal, because they are equal iff their (n-1)-gram
    prefixes are equal and their last symbols are equal.  Returns (ids, number_of_distinct)."""
    L = s.shape[0]
    ids = np.full(L, -1, dtype=np.int64)
    if L < n:
        return ids, 0
    key = prev_ids[n - 2: L - 1] * k + s[n - 1: L]       # ((n-1)-gram ending at e-1, s[e])
    uniq, inverse = np.unique(key, return_inverse=True)
    ids[n - 1:] = inverse.reshape(-1)
    return ids, int(uniq.shape[0])


def _cap_admission(seg, max_entries):
    """Step 4.a.i.2 as a pure function of the learn-event sequence.

    `seg[j]` is the id (pair id, or context id for the variant) of the j-th learn event of one
    order, in step order.  An id is admitted iff it is among the first `max_entries` distinct
    ids by first occurrence.  Returns (admitted bool array aligned with seg, or None when
    every id is admitted; entries = number of distinct admitted ids)."""
    if seg.shape[0] == 0:
        return None, 0
    uniq, first = np.unique(seg, return_index=True)
    if uniq.shape[0] <= max_entries:
        return None, int(uniq.shape[0])
    order = np.argsort(first, kind="stable")             # ids in order of first appearance
    keep = uniq[order[:max_entries]]
    lookup = np.zeros(int(seg.max()) + 1, dtype=bool)
    lookup[keep] = True
    return lookup[seg], int(max_entries)


def run_predictor(s, k, D=D_TEXT, max_entries=MAX_ENTRIES_TEXT, entries_mode="pairs"):
    """Steps 1-4 with the same result as `run_predictor_literal` (tested), faster.

    `s` is an int array with values in [0, k).  Returns a dict with 'correct' (uint8 array of
    length N), 'scoreboard' (list of D), 'winner' (1-based), 'entries', 'refused' (lists of
    D) and 'subpredict' (list of D int64 arrays indexed by the 0-based position p of the
    symbol being predicted, i.e. subpredict[d-1][i-1] is the spec's subpredict_d at step i;
    NULL where Null or undefined).

    How the spec's steps map onto this code, in the 0-based index e of the sample s[e]:
      * step 4.a at spec step i records the (d+1)-gram ending at e = i-2 (its context is the
        d-gram ending at e-1, its "y" is s[e]);  step 4.b then predicts s[e+1] from the
        d-gram ending at e.  So for each order d, for e = d .. L-2: learn the (d+1)-gram
        ending at e (if admitted), then predict s[e+1].  The (d+1)-gram ending at L-1 is
        never learned (the loop ends at i = L), and predictions for p = e+1 <= d stay Null
        ("If d < i" fails, or no transition of order d has been seen).
      * the running maximum per context is exact: a count rises by one at a time and the key
        (count, y) is a total order, so the new maximum is max(old maximum, changed key).
    """
    if entries_mode not in ("pairs", "contexts"):
        raise ValueError("entries_mode must be 'pairs' or 'contexts'")
    s = np.asarray(s, dtype=np.int64).ravel()
    L = int(s.shape[0])
    N = L - 2
    subpredict = [np.full(L, NULL, dtype=np.int64) for _ in range(D)]
    entries = [0] * D
    refused = [0] * D
    if N <= 0:
        return {"correct": np.zeros(0, dtype=np.uint8), "scoreboard": [0] * D, "winner": 1,
                "entries": entries, "refused": refused, "subpredict": subpredict}

    s_list = s.tolist()
    ctx_ids = s.copy()                  # ids of the 1-grams: the symbol values themselves
    num_ctx = int(k)
    for d in range(1, D + 1):
        if d > L - 2:                   # no learn event exists for this order (e in [d, L-2] empty)
            break
        pair_ids, num_pairs = _extend_ngram_ids(ctx_ids, s, k, d + 1)

        # step 4.a.i.2 -- which learn events (e = d .. L-2, in order) are admitted
        if entries_mode == "pairs":
            seg = pair_ids[d: L - 1]                        # the pair ending at e
        else:
            seg = ctx_ids[d - 1: L - 2]                     # variant: the context ending at e-1
        admitted, entries[d - 1] = _cap_admission(seg, max_entries)
        if admitted is not None:
            refused[d - 1] = int((~admitted).sum())

        # sequential pass over the learn/predict events of this order
        ctx_l = ctx_ids.tolist()
        pair_l = pair_ids.tolist()
        count = [0] * num_pairs                             # Md[x, y], indexed by pair id
        best_count = [0] * num_ctx                          # highest Md[x, .] per context
        best_y = [NULL] * num_ctx                           # its y (greatest y on a tie)
        sub = [NULL] * L
        if admitted is None:
            for e in range(d, L - 1):
                pid = pair_l[e]
                c = count[pid] + 1
                count[pid] = c
                cid = ctx_l[e - 1]
                y = s_list[e]
                if c > best_count[cid] or (c == best_count[cid] and y > best_y[cid]):
                    best_count[cid] = c
                    best_y[cid] = y
                sub[e + 1] = best_y[ctx_l[e]]               # 4.b: predict s[e+1]
        else:
            adm_l = admitted.tolist()
            for e in range(d, L - 1):
                if adm_l[e - d]:
                    pid = pair_l[e]
                    c = count[pid] + 1
                    count[pid] = c
                    cid = ctx_l[e - 1]
                    y = s_list[e]
                    if c > best_count[cid] or (c == best_count[cid] and y > best_y[cid]):
                        best_count[cid] = c
                        best_y[cid] = y
                sub[e + 1] = best_y[ctx_l[e]]
        subpredict[d - 1] = np.asarray(sub, dtype=np.int64)
        ctx_ids, num_ctx = pair_ids, num_pairs             # the (d+1)-grams are order d+1's contexts

    correct, scoreboard, winner = run_scoreboard(s, subpredict)
    return {"correct": correct, "scoreboard": scoreboard, "winner": winner,
            "entries": entries, "refused": refused, "subpredict": subpredict}


def run_scoreboard(s, subpredict):
    """Steps 3 and 4.c-4.e on a finished subpredict table.

    `s` is the int array of samples (0-based); `subpredict[d-1][p]` is the spec's
    subpredict_d at the step that predicts s[p] (p = i-1), NULL where Null.  Returns
    (correct uint8 array of length N = L-2, scoreboard list of D, winner 1-based).

    Only the steps at which at least one order matched s_i are visited: a step with no
    match leaves correct (4.d needs prediction = s_i, and prediction is one of the
    subpredict_d) and the scoreboard (4.e needs subpredict_d = s_i) untouched, so skipping
    it is exact.  Within a step the orders are visited in ascending d, as 4.e says.
    """
    s = np.asarray(s, dtype=np.int64).ravel()
    L = int(s.shape[0])
    N = L - 2
    D = len(subpredict)
    correct = np.zeros(max(N, 0), dtype=np.uint8)           # step 1: correct = 0
    scoreboard = [0] * D                                    # step 3: D counters, each 0
    winner = 0                                              # step 3: winner = 1 (0-based here)
    if N <= 0:
        return correct, scoreboard, winner + 1
    mask = np.zeros(L, dtype=np.int64)
    for d in range(D):
        sub_d = np.asarray(subpredict[d], dtype=np.int64)
        mask |= (sub_d == s).astype(np.int64) << d          # bit d-1 set <=> subpredict_d = s_i
    idx = np.flatnonzero(mask[2:]) + 2                      # p = i-1 >= 2
    for p, m in zip(idx.tolist(), mask[idx].tolist()):
        if (m >> winner) & 1:                               # 4.c + 4.d: subpredict_winner = s_i
            correct[p - 2] = 1
        while m:                                            # 4.e, d ascending
            low = m & -m
            d = low.bit_length() - 1
            m ^= low
            scoreboard[d] += 1                              # 4.e.i.1
            if scoreboard[d] >= scoreboard[winner]:         # 4.e.i.2 (winner as it stands now)
                winner = d
    return correct, scoreboard, winner + 1


# ============================================================================================
# steps 5-8 -- C, r, P_global, P'_global, P_local, min-entropy
# ============================================================================================
def longest_run_of_ones(correct):
    """step 7: 'the length of the longest run of ones in correct'."""
    c = np.asarray(correct, dtype=np.int8).ravel()
    if c.shape[0] == 0:
        return 0
    padded = np.concatenate(([0], c, [0]))
    d = np.diff(padded)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)
    return int((ends - starts).max()) if starts.shape[0] else 0


def p_global_prime(C, N, z=Z_TEXT):
    """step 6.  Returns (P_global, P'_global); NaN where the text divides by zero."""
    if N <= 0:
        return float("nan"), float("nan")
    P = C / N
    if P == 0:
        return P, 1.0 - 0.01 ** (1.0 / N)                 # "1 - 0.01^(1/N), if P_global = 0"
    if N - 1 == 0:
        return P, float("nan")                           # P(1-P)/(N-1) is x/0
    return P, min(1.0, P + z * math.sqrt(P * (1.0 - P) / (N - 1)))


def log_run_probability(p, r, N, steps=RECURRENCE_STEPS):
    """Natural log of step 7's right-hand side at P_local = p:

        (1 - p x) / ((r + 1 - r x) q) * 1 / x^(N+1),   q = 1 - p,
        x = x_steps,  x_j = 1 + q p^r x_(j-1)^(r+1),  x_0 = 1.

    Evaluated in logs as the text recommends.  x is carried as 1 + dlt (dlt = q p^r x^(r+1))
    so that log(x) = log1p(dlt) keeps its precision when dlt is ~1e-8, as it is for N ~ 1e6.
    Returns -inf where the expression is not a positive number (q = 0, or 1 - p x <= 0, or
    r + 1 - r x <= 0), which the bisection treats as 'probability too small => p too large'.
    The recurrence cannot overflow: q p^r <= r^r/(r+1)^(r+1) for every p in [0, 1], which is
    exactly the value at which the fixed point of x = 1 + q p^r x^(r+1) still exists.
    """
    q = 1.0 - p
    if not (0.0 <= p <= 1.0) or q <= 0.0:
        return -math.inf
    pr = p ** r
    dlt = 0.0                                            # x_0 = 1  ->  dlt_0 = 0
    for _ in range(steps):
        dlt = q * pr * (1.0 + dlt) ** (r + 1)            # x_j = 1 + q p^r x_(j-1)^(r+1)
    x = 1.0 + dlt
    numerator = 1.0 - p * x
    denominator = (r + 1 - r * x) * q
    if not (numerator > 0.0 and denominator > 0.0):
        return -math.inf
    return math.log(numerator) - math.log(denominator) - (N + 1) * math.log1p(dlt)


def p_local(r, N, confidence=CONFIDENCE, max_iter=4000):
    """step 7: bisection on [0, 1] for P_local such that the run probability equals 0.99.

    The right-hand side falls as p rises (a better predictor is likelier to produce a run of
    length r), so a midpoint whose value is above the target is too small a p.  Stops when
    the midpoint can no longer be distinguished from an endpoint in binary64.
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


def estimate(symbols, bits_per_symbol, *, D=D_TEXT, max_entries=MAX_ENTRIES_TEXT,
             entries_mode="pairs", z=Z_TEXT, k_mode="alphabet", method="fast",
             return_arrays=False, trace=False):
    """SP 800-90B section 6.3.9 on `symbols` (ints in [0, 2**bits_per_symbol)).

    Options: D and max_entries default to the text's 16 and 100 000 (the worked example uses
    D = 3); entries_mode 'pairs' (literal) or 'contexts' (variant); z the step-6 constant;
    k_mode 'alphabet' or 'observed'; method 'fast' (default) or 'literal' (the transcription,
    slow); return_arrays=True adds 'correct' and 'subpredict'; trace=True forces the literal
    method and adds 'trace' and 'models' (the two worked-example tables).

    Returns a dict whose keys 'C', 'r', 'N', 'P_global', "P_global'", 'P_local' and
    'min entropy' are the quantities the standard names under the labels the C++ prints
    ('min_entropy' repeats 'min entropy'), plus: 'L', 'k', 'k_alphabet', 'k_observed',
    'k_mode', 'D', 'max_entries', 'entries_mode', 'z', 'confidence', 'scoreboard' (final),
    'winner' (final, 1-based), 'entries' (final entries_d), 'refused' (learn events the cap
    declined, per order), 'cap_bound' (any order refused anything), 'longest_run', 'binding'
    (which of P'_global / P_local / 1/k decided step 8), 'P_local_changes_result'
    (P_local > P'_global), 'method', and 'ambiguities'.  NaN marks every quantity the text
    does not define for the input.
    """
    s = np.asarray(symbols, dtype=np.int64).ravel()
    bits_per_symbol = int(bits_per_symbol)
    if bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be >= 1")
    D = int(D)
    if D < 1:
        raise ValueError("D must be >= 1")
    if int(max_entries) < 0:
        raise ValueError("max_entries must be >= 0")
    k_alphabet = 1 << bits_per_symbol
    if s.shape[0] and (s.min() < 0 or s.max() >= k_alphabet):
        raise ValueError("symbols must lie in [0, 2**bits_per_symbol)")
    if k_mode not in ("alphabet", "observed"):
        raise ValueError("k_mode must be 'alphabet' or 'observed'")
    if method not in ("fast", "literal"):
        raise ValueError("method must be 'fast' or 'literal'")
    L = int(s.shape[0])
    N = L - 2                                            # step 1
    k_observed = int(np.unique(s).shape[0]) if L else 0
    k = k_alphabet if k_mode == "alphabet" else k_observed

    nan = float("nan")
    result = {
        "min_entropy": nan, "min entropy": nan, "C": nan, "r": nan, "N": N,
        "P_global": nan, "P_global'": nan, "P_local": nan,
        "L": L, "k": k, "k_alphabet": k_alphabet, "k_observed": k_observed, "k_mode": k_mode,
        "D": D, "max_entries": int(max_entries), "entries_mode": entries_mode,
        "z": z, "confidence": CONFIDENCE,
        "scoreboard": [0] * D, "winner": 1, "entries": [0] * D, "refused": [0] * D,
        "cap_bound": False, "longest_run": nan, "binding": None,
        "P_local_changes_result": None, "method": method if not trace else "literal",
        "ambiguities": list(AMBIGUITIES),
    }
    if N <= 0:                                           # the text defines nothing here
        if return_arrays:
            result["correct"] = np.zeros(0, dtype=np.uint8)
            result["subpredict"] = [np.full(L, NULL, dtype=np.int64) for _ in range(D)]
        return result

    # steps 1-4
    if trace or method == "literal":
        run = run_predictor_literal(s.tolist(), D=D, max_entries=int(max_entries),
                                    entries_mode=entries_mode, trace=trace)
        correct = np.asarray(run["correct"], dtype=np.uint8)
    else:
        run = run_predictor(s, k_alphabet, D=D, max_entries=int(max_entries),
                            entries_mode=entries_mode)
        correct = run["correct"]

    # step 5
    C = int(correct.sum())
    # step 6
    P_global, P_global_prime = p_global_prime(C, N, z)
    # step 7
    longest = longest_run_of_ones(correct)
    r = longest + 1
    P_local = p_local(r, N)
    # step 8
    if k <= 0:
        candidates = {"P_global'": P_global_prime, "P_local": P_local, "1/k": nan}
    else:
        candidates = {"P_global'": P_global_prime, "P_local": P_local, "1/k": 1.0 / k}
    if any(math.isnan(v) for v in candidates.values()):
        min_entropy = nan
        binding = None
    else:
        binding = max(candidates, key=candidates.get)
        min_entropy = -math.log2(candidates[binding])

    result.update({
        "min_entropy": min_entropy, "min entropy": min_entropy, "C": C, "r": r,
        "P_global": P_global, "P_global'": P_global_prime, "P_local": P_local,
        "scoreboard": list(run["scoreboard"]), "winner": int(run["winner"]),
        "entries": list(run["entries"]), "refused": list(run["refused"]),
        "cap_bound": any(v > 0 for v in run["refused"]),
        "longest_run": longest, "binding": binding,
        "P_local_changes_result": (None if math.isnan(P_local) or math.isnan(P_global_prime)
                                   else bool(P_local > P_global_prime)),
    })
    if return_arrays or trace:
        result["correct"] = correct
        result["subpredict"] = run["subpredict"]
    if trace:
        result["trace"] = run["trace"]
        result["models"] = run["models"]
    return result


# ============================================================================================
# command line
# ============================================================================================
def _json_ready(d):
    out = {}
    for key, v in d.items():
        if key in ("correct", "subpredict", "trace", "models"):
            continue
        if isinstance(v, np.generic):
            v = v.item()
        out[key] = v
    return out


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(
            "usage: multimmc.py <rawfile> <bits_per_symbol> [--literal|--bitstring] "
            "[--D=16] [--max-entries=100000] [--entries-mode=pairs|contexts] [--z=2.576] "
            "[--k-mode=alphabet|observed] [--method=fast|literal]\n")
        return 2
    path = argv[1]
    try:
        bps = int(argv[2])
    except ValueError:
        sys.stderr.write(f"bits_per_symbol must be an integer, got {argv[2]!r}\n")
        return 2
    if not 1 <= bps <= 8:
        sys.stderr.write("bits_per_symbol must be in 1..8 for a one-symbol-per-byte file\n")
        return 2
    mode = "literal"
    opts = {}
    try:
        for a in argv[3:]:
            if a == "--literal":
                mode = "literal"
            elif a == "--bitstring":
                mode = "bitstring"
            elif a.startswith("--D="):
                opts["D"] = int(a[len("--D="):])
            elif a.startswith("--max-entries="):
                opts["max_entries"] = int(a[len("--max-entries="):])
            elif a.startswith("--entries-mode="):
                opts["entries_mode"] = a[len("--entries-mode="):]
            elif a.startswith("--z="):
                opts["z"] = float(a[len("--z="):])
            elif a.startswith("--k-mode="):
                opts["k_mode"] = a[len("--k-mode="):]
            elif a.startswith("--method="):
                opts["method"] = a[len("--method="):]
            else:
                sys.stderr.write(f"unknown option {a!r}\n")
                return 2
    except ValueError as exc:
        sys.stderr.write(f"bad option value: {exc}\n")
        return 2
    raw = np.fromfile(path, dtype=np.uint8).astype(np.int64)
    symbols = raw & ((1 << bps) - 1)                     # one symbol per byte, low bps bits
    try:
        if mode == "bitstring":
            res = estimate(to_bitstring(symbols, bps), 1, **opts)
        else:
            res = estimate(symbols, bps, **opts)
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2
    res["mode"] = mode
    res["file"] = path
    res["bits_per_symbol_declared"] = bps
    print(json.dumps(_json_ready(res), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
