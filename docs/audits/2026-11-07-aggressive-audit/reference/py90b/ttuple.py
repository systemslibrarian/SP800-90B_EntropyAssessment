"""SP 800-90B section 6.3.5, the t-Tuple Estimate -- an independent reference implementation.

Written from the text of NIST SP 800-90B (January 2018) ONLY, PDF pages 55-56 (printed pages
47-48).  Nothing here was taken from the C++ tool except the NAMES of the printed intermediate
quantities ("t", "p-hat_max", "p_u", "min entropy"), so a differential driver can match them.

The specification, quoted (SP 800-90B section 6.3.5, PDF p. 55):

    "This method examines the frequency of t-tuples (pairs, triples, etc.) that appears in the
    input dataset and produces an estimate of the entropy per sample, based on the frequency of
    those t-tuples.  The frequency of the t-tuple (r1, r2, ..., rt) in S = (s1, ..., sL) is the
    number of i's such that si = r1, si+1 = r2, ..., si+t-1 = rt.  It should be noted that the
    tuples can overlap.

    Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},"

and (PDF p. 56):

    "1. Find the largest t such that the number of occurrences of the most common t-tuple in S is
        at least 35.
     2. Let Q[i] store the number of occurrences of the most common i-tuple in S for i = 1, ..., t.
     3. For i = 1 to t, let P[i] = Q[i] / (L-i+1), and compute an estimate on the maximum
        individual sample value probability as P_max[i] = P[i]^(1/i).
        Let p-hat_max = max(P_max[1], ..., P_max[t]).
     4. Calculate an upper bound on the probability of the most common value p_u as
            p_u = min(1, p-hat_max + 2.576 * sqrt( p-hat_max (1 - p-hat_max) / (L - 1) )),
     5. The entropy estimate is calculated as -log2(p_u)."

Reading notes (each is also recorded in the audit's spec_ambiguities):

  * Step 1 gives no value when NO t satisfies it, i.e. when even the most common single symbol
    occurs fewer than 35 times (Q[1] < 35).  The section has no "cannot be computed" clause (its
    neighbour 6.3.6 does).  This module returns t = 0 and min_entropy = NaN in that case.
  * Step 1's "largest t" is found by scanning t = 1, 2, ... and stopping at the first length
    whose most common tuple occurs fewer than `cutoff` times.  That is valid because Q is
    non-increasing in the tuple length: every occurrence of a (t+1)-tuple (r1..r_{t+1}) at
    position i is also an occurrence of the t-tuple (r1..rt) at position i, so the most common
    (t+1)-tuple occurs at most as often as its own t-prefix, hence at most Q[t] times.  The
    worked example relies on the same fact ("the most common 4-tuple is 2, which falls below the
    threshold, and therefore t = 3").
  * Step 4 prints the constant 2.576.  Section 6.3.1 step 2 says of the same constant that it
    "corresponds to the Z(1-0.005) value", whose exact value is 2.57582930354890076... (derived
    in tests/test_ttuple.py with decimal arithmetic).  The two readings differ materially at the
    sixth decimal of the estimate, so both are exposed: z_variant='literal' (2.576, the default,
    the most literal reading) and z_variant='exact' (the binary64 nearest to the quantile).
  * Step 4 divides by (L - 1) whatever tuple length i attained the maximum, although P[i] for
    i > 1 is a proportion of L-i+1 overlapping tuples.  Implemented as written: L - 1.
  * Step 3's maximum is over the real numbers P_max[i]; it is computed here in binary64, so the
    last bits of p-hat_max are the arithmetic's, not the specification's.

Three ways of counting are provided and cross-checked by the tests:

  method='literal'       pure Python: hash the actual tuples (collections.Counter), one tuple
                         length at a time.  The most literal reading; O(t * L) Python work.
  method='direct'        numpy: the same count, one tuple length at a time, each tuple
                         identified by a dense integer id built from the id of its (i-1)-prefix
                         and its last symbol (a perfect hash of the tuple).  O(t * L log L).
  method='suffix_array'  numpy + Python: a suffix array by prefix doubling, Kasai's LCP array,
                         and the lcp-interval tree, which gives Q[i] for EVERY i at once in
                         O(L log L).  Needed when t is huge (a stuck source: all one symbol has
                         t = L - 34, which makes the per-length methods O(L^2)).
  method='auto'          'direct', switching to 'suffix_array' when t exceeds direct_t_limit
                         and asserting that the two agree on the lengths already counted.

API:  estimate(symbols, bits_per_symbol, *, cutoff=35, z_variant='literal', method='auto',
               direct_t_limit=128) -> dict
      keys: 'min_entropy', 't', 'p-hat_max', 'p_u' (the C++ label names), plus 'Q', 'P',
      'P_max' (lists indexed from 0 for i = 1..t), 'Q_next' (the count that fell below the
      cutoff), 'argmax_i', 'L', 'k', 'cutoff', 'z', 'z_variant', 'method'.
      NaN where the specification gives no value.

Command line:  python ttuple.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                                [--cutoff N] [--z literal|exact]
                                [--method auto|direct|suffix_array|literal]
      rawfile holds one symbol per byte; the low bits_per_symbol bits are the symbol.
      --bitstring first writes each symbol as bits_per_symbol bits, most significant first, and
      assesses the result as 1-bit symbols (the tool's "Bitstring" estimates; section 6.4 is the
      standard's text on reducing the symbol space).  Prints the result dict as JSON.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter

import numpy as np

# Step 1's threshold: "at least 35".  The worked example on PDF p. 56 uses 3 "instead of 35".
CUTOFF = 35

# Step 4's constant as printed in the text.
Z_LITERAL = 2.576
# The exact Z(1-0.005) = Phi^-1(0.995) = 2.57582930354890076097857674860381... rounded to
# binary64.  Verified in tests/test_ttuple.py from a decimal-arithmetic erf series.
Z_EXACT = 2.5758293035489008
Z_VARIANTS = {"literal": Z_LITERAL, "exact": Z_EXACT}

METHODS = ("auto", "direct", "suffix_array", "literal")


# --------------------------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------------------------

def _as_symbol_array(symbols, bits_per_symbol):
    """Return S as a 1-D int64 numpy array, checking every value lies in [0, 2^bits_per_symbol)."""
    if not isinstance(bits_per_symbol, int) or isinstance(bits_per_symbol, bool) or bits_per_symbol < 1:
        raise ValueError(f"bits_per_symbol must be a positive integer, got {bits_per_symbol!r}")
    if isinstance(symbols, (bytes, bytearray, memoryview)):
        S = np.frombuffer(bytes(symbols), dtype=np.uint8).astype(np.int64)
    else:
        S = np.asarray(symbols)
        if S.size == 0:
            S = np.zeros(0, dtype=np.int64)              # [] has no dtype of its own
        elif S.dtype.kind not in "iub":
            raise ValueError(f"symbols must be integers, got dtype {S.dtype}")
        S = S.astype(np.int64)
    if S.ndim != 1:
        raise ValueError(f"symbols must be one-dimensional, got shape {S.shape}")
    k = 1 << bits_per_symbol
    if S.size and (int(S.min()) < 0 or int(S.max()) >= k):
        raise ValueError(
            f"symbols must lie in [0, {k}) for bits_per_symbol={bits_per_symbol}; "
            f"found min {int(S.min())}, max {int(S.max())}")
    return S, k


def to_bitstring(symbols, bits_per_symbol):
    """Write each symbol as bits_per_symbol bits, most significant bit first, giving 1-bit symbols.

    [5, 3] with bits_per_symbol=3 -> [1,0,1, 0,1,1].
    """
    S, _ = _as_symbol_array(symbols, bits_per_symbol)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.int64)
    return ((S[:, None] >> shifts) & 1).ravel()


# --------------------------------------------------------------------------------------------
# Counting the most common i-tuple -- three implementations
# --------------------------------------------------------------------------------------------

def most_common_tuple_count_literal(S, i):
    """The number of occurrences of the most common i-tuple in S, straight from the definition.

    "The frequency of the t-tuple (r1, ..., rt) in S = (s1, ..., sL) is the number of i's such
    that si = r1, si+1 = r2, ..., si+t-1 = rt.  It should be noted that the tuples can overlap."
    (PDF p. 55).  Positions run over every start that leaves room for i symbols: L - i + 1 of
    them.  If i > L there is no i-tuple and the count is 0.
    """
    S = [int(x) for x in S]
    L = len(S)
    if i > L:
        return 0
    counts = Counter(tuple(S[j:j + i]) for j in range(L - i + 1))
    return max(counts.values())


def _tuple_counts_literal(S, cutoff):
    """Q[1..t] by the literal method.  Returns (Q, Q_next)."""
    Q = []
    i = 1
    while True:
        q = most_common_tuple_count_literal(S, i)
        if q < cutoff:
            return Q, q
        Q.append(q)
        i += 1


def _tuple_counts_direct(S, k, cutoff, t_limit=None):
    """Q[1..t] by the numpy per-length method.  Returns (Q, Q_next, complete).

    ids[j] is a dense integer identifying the i-tuple that starts at position j (j = 0..L-i):
    two positions get the same id exactly when their i-tuples are equal.  For i = 1 the id is
    the symbol's index among the distinct symbols; for i+1 it is the index of the pair
    (id of the i-tuple at j, symbol at j+i) among the distinct pairs -- so by induction ids are
    a perfect hash of the tuples.  Q[i] is then the largest multiplicity of any id.

    Stops at the first length whose most common tuple occurs fewer than `cutoff` times (Q is
    non-increasing in the length, see the module docstring), or -- when t_limit is given -- after
    t_limit lengths have been accepted, in which case complete is False and Q_next is None.
    """
    L = int(S.size)
    Q = []
    if L == 0:
        return Q, 0, True
    _, ids, counts = np.unique(S, return_inverse=True, return_counts=True)
    ids = ids.reshape(-1).astype(np.int64)
    i = 1
    while True:
        q = int(counts.max())
        if q < cutoff:
            return Q, q, True
        Q.append(q)
        if i == L:
            # Every length up to L was accepted; no (L+1)-tuple exists, so its count is 0.
            return Q, 0, True
        if t_limit is not None and i >= t_limit:
            return Q, None, False
        # The (i+1)-tuple at j is (the i-tuple at j, the symbol at j+i), for j = 0..L-i-1.
        # ids < L and symbols < k, so the pair code ids*k + symbol is unique and fits int64.
        pair = ids[:-1] * k + S[i:]
        _, ids, counts = np.unique(pair, return_inverse=True, return_counts=True)
        ids = ids.reshape(-1).astype(np.int64)
        i += 1


def _suffix_array(S):
    """Suffix array of S by prefix doubling.  Returns (sa, rank): sa[r] is the start of the
    r-th smallest suffix, rank[j] is the position of suffix j in that order.

    A shorter suffix that is a prefix of a longer one sorts first (its missing symbol is coded
    as -1, below every real rank).
    """
    L = int(S.size)
    _, rank = np.unique(S, return_inverse=True)
    rank = rank.reshape(-1).astype(np.int64)  # order by the first symbol, dense in [0, L)
    sa = np.argsort(rank, kind="stable")
    if L <= 1:
        return sa, rank
    h = 1
    while True:
        # Sort by (rank of the first h symbols, rank of the next h symbols), i.e. by 2h symbols.
        second = np.full(L, -1, dtype=np.int64)
        m = max(L - h, 0)
        second[:m] = rank[h:h + m]
        key = rank * (L + 1) + (second + 1)        # both parts lie in [0, L], so the code is unique
        sa = np.argsort(key, kind="stable")
        ks = key[sa]
        new_rank_sorted = np.concatenate(([0], np.cumsum(ks[1:] != ks[:-1])))
        rank = np.empty(L, dtype=np.int64)
        rank[sa] = new_rank_sorted
        if int(new_rank_sorted[-1]) == L - 1:       # all L ranks distinct: the order is final
            return sa, rank
        h *= 2


def _lcp_kasai(S, sa, rank):
    """Kasai's algorithm.  lcp[r] = length of the longest common prefix of the suffixes sa[r-1]
    and sa[r] (r = 1..L-1); lcp[0] = 0.  O(L) comparisons in total."""
    L = int(S.size)
    s = S.tolist()
    sa_l = sa.tolist()
    rank_l = rank.tolist()
    lcp = [0] * L
    h = 0
    for j in range(L):
        r = rank_l[j]
        if r == 0:
            h = 0
            continue
        p = sa_l[r - 1]
        while j + h < L and p + h < L and s[j + h] == s[p + h]:
            h += 1
        lcp[r] = h
        if h > 0:
            h -= 1
    return lcp


def _largest_lcp_interval_by_depth(lcp, L):
    """best[d] = the largest number of suffixes that share a common prefix of EXACTLY depth d as
    an lcp-interval (d = 1..L-1; 0 where none).  Bottom-up traversal of the lcp-interval tree
    (Abouelhoda, Kurtz, Ohlebusch): an interval [lb, rb] with value d has lcp[lb] < d,
    lcp[lb+1..rb] >= d with minimum d, and lcp[rb+1] < d; its rb+1-lb suffixes all begin with
    the same d symbols."""
    best = [0] * (L + 1)
    stack = [(0, 0)]                                 # (lcp value, left boundary); the root
    for r in range(1, L + 1):
        cur = lcp[r] if r < L else 0                 # a final 0 closes every open interval
        lb = r - 1
        while cur < stack[-1][0]:
            depth, lb = stack.pop()                  # the interval [lb, r-1] closes here
            size = r - lb
            if size > best[depth]:
                best[depth] = size
        if cur > stack[-1][0]:
            stack.append((cur, lb))
    return best


def _tuple_counts_all_suffix_array(S):
    """Q[i] for every i = 1..L at once, as a numpy array Qall with Qall[i] = Q[i] (Qall[0] unused).

    The occurrences of an i-tuple are exactly the suffixes beginning with it, which are
    contiguous in the suffix array; a maximal such group of size >= 2 is an lcp-interval of some
    depth d >= i, and a group of size 1 is a tuple that occurs once.  So
    Q[i] = max(1, max over depths d >= i of best[d]).
    """
    L = int(S.size)
    if L == 0:
        return np.zeros(1, dtype=np.int64)
    sa, rank = _suffix_array(S)
    lcp = _lcp_kasai(S, sa, rank)
    best = np.array(_largest_lcp_interval_by_depth(lcp, L), dtype=np.int64)   # index 0..L
    Qall = np.maximum.accumulate(best[::-1])[::-1]   # Qall[i] = max_{d >= i} best[d]
    Qall = np.maximum(Qall, 1)
    Qall[0] = L                                      # the empty tuple "occurs" everywhere; unused
    return Qall


def _tuple_counts_suffix_array(S, cutoff):
    """Q[1..t] from the suffix-array counts.  Returns (Q, Q_next)."""
    Qall = _tuple_counts_all_suffix_array(S)
    L = int(S.size)
    # Qall[1..L] is non-increasing, so t = the number of lengths whose count reaches the cutoff.
    t = int(np.count_nonzero(Qall[1:] >= cutoff))
    Q = [int(q) for q in Qall[1:t + 1]]
    Q_next = int(Qall[t + 1]) if t + 1 <= L else 0
    return Q, Q_next


def most_common_tuple_counts(S, k, cutoff, method="auto", direct_t_limit=128):
    """Steps 1 and 2: Q[1..t] with t the largest length whose most common tuple occurs at least
    `cutoff` times.  Returns (Q, Q_next, method_used); Q_next is the count that fell short."""
    if method == "literal":
        Q, Q_next = _tuple_counts_literal(S, cutoff)
        return Q, Q_next, "literal"
    if method == "direct":
        Q, Q_next, _ = _tuple_counts_direct(S, k, cutoff, t_limit=None)
        return Q, Q_next, "direct"
    if method == "suffix_array":
        Q, Q_next = _tuple_counts_suffix_array(S, cutoff)
        return Q, Q_next, "suffix_array"
    if method == "auto":
        Q, Q_next, complete = _tuple_counts_direct(S, k, cutoff, t_limit=direct_t_limit)
        if complete:
            return Q, Q_next, "direct"
        Q2, Q2_next = _tuple_counts_suffix_array(S, cutoff)
        if Q2[:len(Q)] != Q:
            raise AssertionError(
                "the direct and suffix-array counts disagree on the lengths both computed: "
                f"direct {Q[:8]}..., suffix_array {Q2[:8]}...")
        return Q2, Q2_next, "suffix_array (after direct reached %d)" % len(Q)
    raise ValueError(f"method must be one of {METHODS}, got {method!r}")


# --------------------------------------------------------------------------------------------
# The estimate
# --------------------------------------------------------------------------------------------

def _nan_result(L, k, cutoff, z, z_variant, method_used, Q, Q_next, reason):
    return {
        "min_entropy": float("nan"),
        "t": len(Q),
        "p-hat_max": float("nan"),
        "p_u": float("nan"),
        "Q": list(Q),
        "P": [],
        "P_max": [],
        "Q_next": Q_next,
        "argmax_i": None,
        "L": L,
        "k": k,
        "cutoff": cutoff,
        "z": z,
        "z_variant": z_variant,
        "method": method_used,
        "undefined_because": reason,
    }


def estimate(symbols, bits_per_symbol, **options):
    """SP 800-90B section 6.3.5, the t-Tuple Estimate, on S = symbols with alphabet size
    k = 2^bits_per_symbol.  See the module docstring for the text implemented and the options."""
    cutoff = options.pop("cutoff", CUTOFF)
    z_variant = options.pop("z_variant", "literal")
    method = options.pop("method", "auto")
    direct_t_limit = options.pop("direct_t_limit", 128)
    if options:
        raise TypeError(f"unknown option(s): {sorted(options)}")
    if not isinstance(cutoff, int) or isinstance(cutoff, bool) or cutoff < 1:
        raise ValueError(f"cutoff must be a positive integer, got {cutoff!r}")
    if z_variant not in Z_VARIANTS:
        raise ValueError(f"z_variant must be one of {sorted(Z_VARIANTS)}, got {z_variant!r}")
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")
    z = Z_VARIANTS[z_variant]

    S, k = _as_symbol_array(symbols, bits_per_symbol)
    L = int(S.size)
    if L * k >= (1 << 62):
        raise ValueError("L * 2^bits_per_symbol is too large for the int64 tuple codes")

    # Steps 1 and 2.
    Q, Q_next, method_used = most_common_tuple_counts(S, k, cutoff, method, direct_t_limit)
    t = len(Q)
    if t == 0:
        return _nan_result(L, k, cutoff, z, z_variant, method_used, Q, Q_next,
                           f"no t has a most common t-tuple occurring at least {cutoff} times "
                           f"(the most common 1-tuple occurs {Q_next} times)")
    if L < 2:
        return _nan_result(L, k, cutoff, z, z_variant, method_used, Q, Q_next,
                           "step 4 divides by L - 1 = 0")

    # Step 3: P[i] = Q[i] / (L - i + 1), P_max[i] = P[i]^(1/i), p-hat_max = max_i P_max[i].
    P = [Q[i - 1] / (L - i + 1) for i in range(1, t + 1)]
    P_max = [P[i - 1] ** (1.0 / i) for i in range(1, t + 1)]
    argmax_i = 1 + max(range(t), key=lambda idx: P_max[idx])   # the first i attaining the max
    p_hat_max = P_max[argmax_i - 1]

    # Step 4: p_u = min(1, p-hat_max + z * sqrt(p-hat_max (1 - p-hat_max) / (L - 1))).
    p_u = min(1.0, p_hat_max + z * math.sqrt(p_hat_max * (1.0 - p_hat_max) / (L - 1)))

    # Step 5: min-entropy = -log2(p_u).  (+ 0.0 turns -0.0 into 0.0 when p_u == 1.)
    min_entropy = -math.log2(p_u) + 0.0

    return {
        "min_entropy": min_entropy,
        "t": t,
        "p-hat_max": p_hat_max,
        "p_u": p_u,
        "Q": [int(q) for q in Q],
        "P": P,
        "P_max": P_max,
        "Q_next": Q_next,
        "argmax_i": argmax_i,
        "L": L,
        "k": k,
        "cutoff": cutoff,
        "z": z,
        "z_variant": z_variant,
        "method": method_used,
    }


# --------------------------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------------------------

_USAGE = ("usage: python ttuple.py <rawfile> <bits_per_symbol> [--literal|--bitstring] "
          "[--cutoff N] [--z literal|exact] [--method auto|direct|suffix_array|literal]")


def main(argv):
    args = list(argv)
    mode = "literal"
    cutoff = CUTOFF
    z_variant = "literal"
    method = "auto"
    positional = []
    while args:
        a = args.pop(0)
        if a == "--literal":
            mode = "literal"
        elif a == "--bitstring":
            mode = "bitstring"
        elif a == "--cutoff":
            cutoff = int(args.pop(0))
        elif a == "--z":
            z_variant = args.pop(0)
        elif a == "--method":
            method = args.pop(0)
        elif a.startswith("-") and not a[1:].isdigit():
            sys.stderr.write(f"ttuple.py: unknown option {a!r}\n{_USAGE}\n")
            return 2
        else:
            positional.append(a)
    if len(positional) != 2:
        sys.stderr.write(_USAGE + "\n")
        return 2
    path, bps_text = positional
    bits_per_symbol = int(bps_text)
    if not 1 <= bits_per_symbol <= 8:
        sys.stderr.write("ttuple.py: bits_per_symbol must be 1..8 for a one-symbol-per-byte file\n")
        return 2

    with open(path, "rb") as fh:
        raw = np.frombuffer(fh.read(), dtype=np.uint8)
    mask = (1 << bits_per_symbol) - 1
    exceeding = int(np.count_nonzero(raw > mask))
    if exceeding:
        sys.stderr.write(f"ttuple.py: warning: {exceeding} of {raw.size} bytes have bits above "
                         f"bit {bits_per_symbol - 1} set; the low {bits_per_symbol} bits are used\n")
    S = (raw & mask).astype(np.int64)
    if mode == "bitstring":
        S = to_bitstring(S, bits_per_symbol)
        result = estimate(S, 1, cutoff=cutoff, z_variant=z_variant, method=method)
    else:
        result = estimate(S, bits_per_symbol, cutoff=cutoff, z_variant=z_variant, method=method)
    result = dict(result)
    result["mode"] = mode
    result["file"] = path
    result["bits_per_symbol"] = bits_per_symbol
    result["symbols_in_file"] = int(raw.size)
    result["bytes_exceeding_width"] = exceeding
    sys.stdout.write(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
