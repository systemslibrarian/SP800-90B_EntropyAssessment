"""SP 800-90B (January 2018) section 6.3.8 -- The Lag Prediction Estimate.

Independent reference implementation written FROM THE STANDARD'S TEXT ONLY
(reference/sp800-90b.pages.txt, PDF pp. 59-60).  No file under cpp/ was
consulted.  The only thing taken from the C++ tool is the NAMES of the
intermediate quantities it prints in verbose mode
(reference/cpp-verbose-labels-non_iid.txt), so that a differential driver
can match them:  C, r, N, P_global, P_global', P_local, min entropy.

The text this module implements, quoted (SP 800-90B section 6.3.8, PDF p. 59-60):

    Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},
    1. Let D = 128, and N = L - 1.  Let lag be a list of D values, each
       initialized to Null.  Let correct be a list of N Boolean values, each
       initialized to 0.
    2. Let scoreboard be a list of D counters, each initialized to 0.
       Let winner = 1.
    3. For i = 2 to L:
         a. For d = 1 to D:
              i.  If (d < i), lag_d = s_{i-d},
              ii. Else lag_d = Null.
         b. Let prediction = lag_winner.
         c. If (prediction = s_i), let correct_{i-1} = 1.
         d. Update the scoreboard.  For d = 1 to D:
              i. If (lag_d = s_i)
                   1. Let scoreboard_d = scoreboard_d + 1.
                   2. If scoreboard_d >= scoreboard_winner, let winner = d.
    4. Let C be the number of ones in correct.
    5. Calculate the predictor's global performance as P_global = C / N.
       The upper bound of the 99 % confidence interval on P_global, denoted
       P_global', is calculated as:
         P_global' = 1 - 0.01^(1/N)                                 if P_global = 0,
                     min(1, P_global + 2.576 sqrt(P_global (1 - P_global) / (N - 1)))
                                                                    otherwise
       where 2.576 corresponds to the Z(1-0.005) value.
    6. Calculate the predictor's local performance, based on the longest run
       of correct predictions.  Let r be one greater than the length of the
       longest run of ones in correct.  Use a binary search to solve the
       following for P_local:
         0.99 = (1 - P_local x) / ((r + 1 - r x) q)  *  1 / x^(N+1),
       where q = 1 - P_local and x = x_10, derived by iterating the recurrence
       relation  x_j = 1 + q P_local^r x_{j-1}^(r+1)  for j from 1 to 10, and
       x_0 = 1.  Note that solving for P_local using the logarithm of these
       equations is robust against overflows.
    7. The min-entropy is the negative logarithm of the greater performance
       metric:  min-entropy = -log2(max(P_global', P_local, 1/k)).

Where the text is ambiguous the most literal reading is the default and the
other reading is exposed as an option (see `estimate`):

  * k.  Section 6 (PDF p. 48): "each si comes from an output space
    A = {x1, ..., xk} that is specified by the submitter"; section 1.1 symbol
    list (PDF p. 11): "k  The number of possible symbols, i.e., the size of the
    alphabet".  Default k_mode='alphabet': k = 2**bits_per_symbol.  The
    glossary (PDF p. 69) says "Alphabet size: The number of distinct symbols
    that the noise source produces", which can be read as the number of
    distinct values observed in S: k_mode='observed'.  The 'observed' reading
    is the conservative one (k_observed <= 2**bps, so 1/k is larger and the
    entropy is lower or equal).  The two coincide whenever every symbol value
    occurs in S, which is the normal case for 1-bit and 8-bit data at
    L = 1,000,000.

  * The constant 2.576.  The text prints the rounded decimal 2.576
    ("where 2.576 corresponds to the Z(1-0.005) value").  Default z=Z_SPEC
    (2.576).  The exact binary64 0.995 standard-normal quantile is exposed as
    z=Z_EXACT (2.5758293035489008); it yields a slightly smaller P_global'
    and therefore a slightly HIGHER min-entropy than the printed constant.
    (This is the documented divergence `C22c` / `D-1` in
    FORK-DIVERGENCE-AND-TRUST.md, recorded here only so the driver can match
    either convention; the default follows the printed text.)

  * The 'Bitstring' track.  Section 3.1.3 (PDF p. 20): "the sequential dataset
    that contains L samples (each having n bits) is considered as a bitstring
    of size nL"; glossary (PDF p. 69): "Bitstring: An ordered sequence of 0's
    and 1's. The leftmost bit is the most significant bit."  With
    bitstring=True each symbol is expanded to bits_per_symbol bits MSB-first,
    the result is treated as 1-bit symbols and k = 2.  Section 3.1.3 also says
    "The bits after the first 1 000 000 bits may be ignored" -- 'may', so this
    module does NOT truncate; pass the truncated data if that is wanted.

Where the spec gives no value the result is float('nan'):

  * L < 2 gives N <= 0: P_global = C/N is undefined -> every statistic is NaN.
  * N = 1 with C = 1: P_global = 1 and the 'otherwise' branch of step 5 is
    1 + 2.576 sqrt(0/0) -> NaN, and so is the min-entropy.
    (N = 1 with C = 0 is defined: P_global' = 1 - 0.01^(1/1) = 0.99.)

Two implementations of steps 1-3 are provided and must agree:
  method='stepwise'   -- a line-by-line transcription of step 3 (O(L*D) Python
                         loops; the one a reader checks against the text);
  method='vectorised' -- the default; the same computation with the inner loop
                         over d vectorised in numpy (see _scan_vectorised for
                         the equivalence argument).  Measured 0.028 s (1-bit)
                         and 0.017 s (8-bit) at L = 20,000, D = 128, on the
                         audit host (logs/analysis-pyref-lag-probe.log); the
                         work is linear in L, so ~2 s is expected at
                         L = 1,000,000 -- an extrapolation: runs above 20,000
                         samples were not executed in the analysis phase.
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np

# ---------------------------------------------------------------------------
# Constants, each tied to the line of the text it comes from.
# ---------------------------------------------------------------------------

D_SPEC = 128                    # step 1: "Let D = 128"
Z_SPEC = 2.576                  # step 5: "where 2.576 corresponds to the Z(1-0.005) value"
Z_EXACT = 2.5758293035489008    # exact 0.995 quantile in binary64 -- a VARIANT, not the text
GLOBAL_ALPHA = 0.01             # step 5: "1 - 0.01^(1/N)"
LOCAL_CONFIDENCE = 0.99         # step 6: "0.99 = ..."
RECURRENCE_ITERATIONS = 10      # step 6: "x = x_10 ... for j from 1 to 10, and x_0 = 1"

NAN = float("nan")


# ---------------------------------------------------------------------------
# Steps 1-3: the predictor itself.
# ---------------------------------------------------------------------------

def _scan_stepwise(x, D, trace=False):
    """Steps 1-3 transcribed line by line.  `x` is a Python list of ints
    holding s_1..s_L at x[0..L-1].

    Returns (correct, trace_rows, scoreboard, winner):
      correct     -- list of N ints (step 1 / 3c)
      trace_rows  -- when trace=True, one dict per i with the quantities the
                     spec's worked-example table shows (lag, winner used in
                     step 3b, prediction, s_i, correct_{i-1}, scoreboard after
                     step 3d); otherwise []
      scoreboard  -- the D counters after the last step
      winner      -- the winner after the last step
    """
    L = len(x)
    N = L - 1
    lag = [None] * D                       # step 1: lag[d-1] is the text's lag_d, Null = None
    correct = [0] * max(N, 0)              # step 1: N Booleans, each 0
    scoreboard = [0] * D                   # step 2
    winner = 1                             # step 2 (1-indexed, as in the text)
    rows = []
    for i in range(2, L + 1):              # step 3: "For i = 2 to L"  (1-indexed i)
        s_i = x[i - 1]
        for d in range(1, D + 1):          # step 3a
            lag[d - 1] = x[i - d - 1] if d < i else None     # lag_d = s_{i-d} if d < i, else Null
        prediction = lag[winner - 1]       # step 3b: prediction = lag_winner
        winner_used = winner
        if prediction is not None and prediction == s_i:   # step 3c (Null never equals a symbol)
            correct[i - 2] = 1             # correct_{i-1}
        for d in range(1, D + 1):          # step 3d, in order d = 1..D, winner updated in place
            if lag[d - 1] is not None and lag[d - 1] == s_i:            # 3d.i
                scoreboard[d - 1] += 1                                  # 3d.i.1
                if scoreboard[d - 1] >= scoreboard[winner - 1]:         # 3d.i.2
                    winner = d
        if trace:
            rows.append({
                "i": i,
                "lag": tuple(lag),
                "winner": winner_used,
                "prediction": prediction,
                "s_i": s_i,
                "correct": correct[i - 2],
                "scoreboard": tuple(scoreboard),
            })
    return correct, rows, scoreboard, winner


def _scan_vectorised(x, D, chunk=1 << 16):
    """Steps 1-3 with the loop over d vectorised; identical results to
    _scan_stepwise (asserted by tests/test_lag.py on random inputs).

    `x` is a 1-D numpy integer array holding s_1..s_L at x[0..L-1].  Below,
    t = i - 1 is the 0-based index of s_i, so step 3 runs over t = 1..L-1 and
    "d < i" is "d <= t".

    Why the winner update can be vectorised.  Step 3d walks d = 1..D in order;
    for each matching lag it increments scoreboard_d and moves `winner` to d
    when the freshly incremented scoreboard_d is >= the CURRENT winner's
    scoreboard (which may itself change during the walk).  Fix one step.  Let
    w0 be the winner entering it, M the set of matching d, S'(d) the
    scoreboard values after this step's increments, m* = max_{d in M} S'(d)
    and d* = the LARGEST d in M with S'(d) = m*.  Then the winner leaving the
    step is

        d*   if M is non-empty and m* >= S'(w0),
        w0   otherwise.

    Proof sketch.  (a) If some d in M takes the slot during the walk, the
    chain of later takeovers ends at d*: after the first takeover the current
    winner is always an already-processed member of M, so a later candidate
    takes over iff S'(candidate) >= S'(current); d* is processed at or after
    the first takeover (if it were processed earlier without taking over we
    would have S'(d*) < w0's then-score <= w0's later score <= S'(first
    takeover) <= m* = S'(d*), a contradiction, using that w0's score never
    decreases during the walk), d* beats whoever is current when it is
    reached (their score is <= m*), and nobody after d* has S' >= m* because
    d* is the largest index attaining m*.  (b) A takeover happens iff
    m* >= S'(w0): if w0 is in M then either someone took over before d = w0
    or w0 "takes over itself" at d = w0 (its own fresh score is >= itself),
    and m* >= S'(w0) holds trivially; if w0 is not in M its score is constant
    during the walk and the first d with S'(d) >= S'(w0) takes over, which
    exists iff m* >= S'(w0).

    The scoreboard trajectory does not depend on the winner at all, so it is
    computed by a cumulative sum over t; only the winner itself needs a
    sequential pass, and that pass is O(1) work per t.
    """
    L = int(len(x))
    N = L - 1
    if N <= 0:
        return np.zeros(0, dtype=bool), np.zeros(D, dtype=np.int64), 1

    x = np.ascontiguousarray(x)
    pred_winner = np.empty(L, dtype=np.int64)      # pred_winner[t] = winner used in step 3b at t
    pred_winner[0] = 1
    scores = np.zeros(D, dtype=np.int64)           # scoreboard entering the current chunk
    winner = 1

    for a in range(1, L, chunk):
        b = min(a + chunk, L)
        n = b - a
        # M[d-1, j] : does lag_d match s_t at t = a + j ?   (lag_d is Null when d > t)
        M = np.zeros((D, n), dtype=bool)
        for d in range(1, D + 1):
            t0 = max(a, d)                          # smallest t in this chunk with d <= t
            if t0 >= b:
                continue
            M[d - 1, t0 - a:] = x[t0 - d:b - d] == x[t0:b]
        # S[d-1, j] : scoreboard_d after step t = a + j   (step 3d.i.1 for every t)
        S = scores[:, None] + np.cumsum(M, axis=1, dtype=np.int64)
        any_match = M.any(axis=0)
        S_matched = np.where(M, S, -1)
        m_star = S_matched.max(axis=0)              # -1 where nothing matched
        hit = S_matched == m_star[None, :]
        d_star = D - np.argmax(hit[::-1, :], axis=0)   # largest d attaining m*  (1-indexed)

        any_l = any_match.tolist()
        m_l = m_star.tolist()
        d_l = d_star.tolist()
        used = [0] * n
        w = winner
        for j in range(n):
            used[j] = w                              # step 3b uses the winner BEFORE this step's update
            if any_l[j] and m_l[j] >= S[w - 1, j]:   # the rule derived above
                w = d_l[j]
        pred_winner[a:b] = used
        winner = w
        scores = S[:, -1].copy()

    # Step 3b/3c for every t at once: prediction = lag_winner = s_{t-winner} if winner <= t.
    t = np.arange(1, L)
    pw = pred_winner[1:L]
    defined = pw <= t
    src = np.where(defined, t - pw, 0)
    correct = defined & (x[src] == x[t])
    return correct, scores, int(winner)


# ---------------------------------------------------------------------------
# Steps 4-7: the statistics.
# ---------------------------------------------------------------------------

def longest_run_of_ones(correct):
    """Length of the longest run of ones in a 0/1 sequence (step 6)."""
    c = np.asarray(correct, dtype=np.int8)
    if c.size == 0:
        return 0
    padded = np.concatenate(([0], c, [0]))
    edges = np.diff(padded)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return int((ends - starts).max()) if starts.size else 0


def p_global_prime(P_global, N, z=Z_SPEC):
    """Step 5.  NaN where the text's expression is 0/0 (N = 1 and P_global != 0)."""
    if N < 1:
        return NAN
    if P_global == 0:
        return 1.0 - GLOBAL_ALPHA ** (1.0 / N)
    if N == 1:
        return NAN                                   # sqrt(P(1-P)/(N-1)) = sqrt(0/0)
    return min(1.0, P_global + z * math.sqrt(P_global * (1.0 - P_global) / (N - 1)))


def _log_rhs(p, r, N):
    """Natural log of the right-hand side of the step-6 equation at
    P_local = p, computed "using the logarithm of these equations" as the text
    suggests.  Returns -inf where a factor is <= 0 (the formula is then
    outside its domain; it happens only for p far above the solution)."""
    q = 1.0 - p
    x = 1.0                                          # x_0 = 1
    qpr = q * p ** r
    for _ in range(RECURRENCE_ITERATIONS):           # x_j = 1 + q p^r x_{j-1}^(r+1), j = 1..10
        x = 1.0 + qpr * x ** (r + 1)
    num = 1.0 - p * x
    den = (r + 1 - r * x) * q
    if num <= 0.0 or den <= 0.0 or x <= 0.0:
        return -math.inf
    return math.log(num) - math.log(den) - (N + 1) * math.log(x)


def solve_p_local(r, N, max_iter=4000):
    """Step 6: binary search on P_local in [0, 1] for
    (1 - P x) / ((r + 1 - r x) q) / x^(N+1) = 0.99.
    The right-hand side is 1 at P = 0 and decreases towards 0 as P -> 1; the
    search narrows the bracket until it is one floating-point step wide."""
    if N < 1 or r < 1:
        return NAN
    target = math.log(LOCAL_CONFIDENCE)
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if mid <= lo or mid >= hi:
            break
        if _log_rhs(mid, r, N) > target:             # still above 0.99 -> P too small
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def min_entropy_from(P_global_prime_, P_local, k):
    """Step 7: -log2(max(P_global', P_local, 1/k)); NaN if any input is NaN."""
    cands = (P_global_prime_, P_local, 1.0 / k)
    if any(isinstance(c, float) and math.isnan(c) for c in cands):
        return NAN
    return -math.log2(max(cands)) + 0.0              # + 0.0 turns -0.0 into 0.0


# ---------------------------------------------------------------------------
# Input handling.
# ---------------------------------------------------------------------------

def to_bitstring(symbols, bits_per_symbol):
    """Section 3.1.3 / glossary: expand each symbol to bits_per_symbol bits,
    most significant bit first, and concatenate."""
    s = np.asarray(symbols, dtype=np.int64)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.int64)
    return ((s[:, None] >> shifts[None, :]) & 1).astype(np.uint8).ravel()


def _validate(symbols, bits_per_symbol):
    if not isinstance(bits_per_symbol, int) or bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be a positive integer")
    x = np.asarray(symbols)
    if x.ndim != 1:
        raise ValueError("symbols must be one-dimensional")
    if x.size and not np.issubdtype(x.dtype, np.integer):
        raise ValueError("symbols must be integers")
    x = x.astype(np.int64, copy=False)
    if x.size and (x.min() < 0 or x.max() >= (1 << bits_per_symbol)):
        raise ValueError("symbols must lie in [0, 2**bits_per_symbol)")
    return x


# ---------------------------------------------------------------------------
# The estimator.
# ---------------------------------------------------------------------------

def estimate(symbols, bits_per_symbol, **options):
    """SP 800-90B section 6.3.8, the Lag Prediction Estimate.

    symbols          : sequence / np.ndarray of ints in [0, 2**bits_per_symbol)
    bits_per_symbol  : the submitter-declared sample width n

    options:
      bitstring  (False)        : apply the section 3.1.3 bitstring conversion
                                  first (MSB-first), then run on 1-bit symbols
      D          (128)          : number of lag subpredictors (step 1); the
                                  spec's worked example uses D = 3
      z          (Z_SPEC=2.576) : the step-5 constant; Z_EXACT is the variant
      k_mode     ('alphabet')   : 'alphabet' -> k = 2**bps ; 'observed' -> the
                                  number of distinct values in S
      method     ('vectorised') : or 'stepwise' (the line-by-line transcription)
      chunk      (65536)        : columns per block in the vectorised scan
      trace      (False)        : stepwise only -- also return the per-step
                                  table of the worked example ('trace')
      return_correct (False)    : also return the correct array ('correct')

    Returns a dict with the C++ verbose-label names as keys:
      'C', 'r', 'N', 'P_global', "P_global'", 'P_local', 'min_entropy'
    plus 'L', 'k', 'D', 'longest_run', 'z', 'k_mode', 'bits_per_symbol',
    'bitstring', 'method', 'P_local_binds', 'scoreboard_final', 'winner_final'.
    NaN wherever the text gives no value (see module docstring).
    """
    bitstring = bool(options.pop("bitstring", False))
    D = int(options.pop("D", D_SPEC))
    z = float(options.pop("z", Z_SPEC))
    k_mode = options.pop("k_mode", "alphabet")
    method = options.pop("method", "vectorised")
    chunk = int(options.pop("chunk", 1 << 16))
    trace = bool(options.pop("trace", False))
    return_correct = bool(options.pop("return_correct", False))
    if options:
        raise TypeError("unknown options: %s" % ", ".join(sorted(options)))
    if D < 1:
        raise ValueError("D must be >= 1")
    if k_mode not in ("alphabet", "observed"):
        raise ValueError("k_mode must be 'alphabet' or 'observed'")

    x = _validate(symbols, bits_per_symbol)
    if bitstring:
        x = to_bitstring(x, bits_per_symbol).astype(np.int64)
        bps = 1
    else:
        bps = bits_per_symbol

    L = int(x.size)
    N = L - 1                                         # step 1
    k = (1 << bps) if k_mode == "alphabet" else int(np.unique(x).size) if L else 0

    trace_rows = []
    if method == "stepwise":
        correct_list, trace_rows, scoreboard, winner = _scan_stepwise(x.tolist(), D, trace=trace)
        correct = np.asarray(correct_list, dtype=bool)
    elif method == "vectorised":
        correct, scoreboard, winner = _scan_vectorised(x, D, chunk=chunk)
    else:
        raise ValueError("method must be 'vectorised' or 'stepwise'")

    out = {
        "min_entropy": NAN,
        "C": NAN, "r": NAN, "N": N,
        "P_global": NAN, "P_global'": NAN, "P_local": NAN,
        "L": L, "k": k, "D": D, "longest_run": NAN,
        "z": z, "k_mode": k_mode, "bits_per_symbol": bps, "bitstring": bitstring,
        "method": method, "P_local_binds": None,
        "scoreboard_final": [int(v) for v in scoreboard],
        "winner_final": int(winner),
    }
    if trace:
        out["trace"] = trace_rows
    if return_correct:
        out["correct"] = [int(v) for v in np.asarray(correct, dtype=np.int8)]

    if N < 1:                                          # L < 2: N = 0, P_global = C/N undefined
        return out

    C = int(np.count_nonzero(correct))                 # step 4
    P_global = C / N                                   # step 5
    Pgp = p_global_prime(P_global, N, z)
    run = longest_run_of_ones(correct)                 # step 6
    r = run + 1
    P_local = solve_p_local(r, N)
    H = min_entropy_from(Pgp, P_local, k)              # step 7

    out.update({
        "min_entropy": H,
        "C": C, "r": r,
        "P_global": P_global, "P_global'": Pgp, "P_local": P_local,
        "longest_run": run,
        "P_local_binds": (None if math.isnan(Pgp) else bool(P_local > Pgp)),
    })
    return out


# ---------------------------------------------------------------------------
# Command line:  python lag.py <rawfile> <bits_per_symbol> [--literal|--bitstring] [options]
# ---------------------------------------------------------------------------

_USAGE = """usage: python lag.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                     [--k-mode=alphabet|observed] [--z=spec|exact] [--D=<int>]
                     [--method=vectorised|stepwise] [--chunk=<int>]

  rawfile          one symbol per byte; the low <bits_per_symbol> bits are the symbol
  --literal        (default) run on the symbols as they are
  --bitstring      first expand each symbol to <bits_per_symbol> bits MSB-first (SP 800-90B
                   section 3.1.3) and run on the resulting 1-bit symbols
Prints the estimate() dict as JSON (NaN where the standard gives no value)."""


def _read_raw(path, bits_per_symbol):
    data = np.fromfile(path, dtype=np.uint8)
    mask = (1 << bits_per_symbol) - 1
    return (data & mask).astype(np.int64)


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(_USAGE + "\n")
        return 2
    path = argv[1]
    try:
        bps = int(argv[2])
    except ValueError:
        sys.stderr.write("bits_per_symbol must be an integer\n" + _USAGE + "\n")
        return 2
    if not 1 <= bps <= 8:
        sys.stderr.write("bits_per_symbol must be in 1..8 for a one-byte-per-symbol file\n")
        return 2
    opts = {}
    for arg in argv[3:]:
        if arg == "--literal":
            opts["bitstring"] = False
        elif arg == "--bitstring":
            opts["bitstring"] = True
        elif arg.startswith("--k-mode="):
            opts["k_mode"] = arg.split("=", 1)[1]
        elif arg.startswith("--z="):
            v = arg.split("=", 1)[1]
            opts["z"] = Z_SPEC if v == "spec" else Z_EXACT if v == "exact" else float(v)
        elif arg.startswith("--D="):
            opts["D"] = int(arg.split("=", 1)[1])
        elif arg.startswith("--method="):
            opts["method"] = arg.split("=", 1)[1]
        elif arg.startswith("--chunk="):
            opts["chunk"] = int(arg.split("=", 1)[1])
        else:
            sys.stderr.write("unknown argument: %s\n%s\n" % (arg, _USAGE))
            return 2
    symbols = _read_raw(path, bps)
    result = estimate(symbols, bps, **opts)
    result["input_file"] = path
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
