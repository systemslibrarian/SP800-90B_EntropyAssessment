"""SP 800-90B section 6.3.4, "The Compression Estimate" -- independent reference.

This module was written from the text of NIST SP 800-90B (January 2018) ONLY,
as extracted to reference/sp800-90b.pages.txt.  No file under cpp/ was opened.
The only thing taken from the C++ tool is the NAMES of the quantities it prints
in verbose mode (reference/cpp-verbose-labels-non_iid.txt), so that a
differential driver can match them:

    Bitstring Compression Estimate: X-bar = ...
    Bitstring Compression Estimate: sigma-hat = ...
    Bitstring Compression Estimate: X-bar' = ...
    Bitstring Compression Estimate: Found p.
    Bitstring Compression Estimate: p = ...
    Bitstring Compression Estimate: min entropy = ...

Those become the dict keys 'X-bar', 'sigma-hat', "X-bar'", 'found_p', 'p' and
'min_entropy'.

The spec, quoted (SP 800-90B section 6.3.4, PDF pp. 53-55)
----------------------------------------------------------
"This entropy estimation method is only applied to binary inputs.
 Given the input S = (s1, ..., sL), where si in A = {0,1},
 1. Let b = 6. Create a new sequence, S' = (s'1, ..., s'floor(L/b)), by dividing
    S into non-overlapping b-bit blocks. If L is not a multiple of b, discard
    the extra data.
 2. Partition the dataset, S', into two disjoint groups. ...
    a. Create the dictionary from the first d = 1000 elements of S'.
    b. Use the remaining v = floor(L/b) - d observations, (s'd+1, ..., s'floor(L/b)),
       for testing.
 3. Initialize the dictionary dict to an all zero array of size 2^b. For i from
    1 to d, let dict[s'i] = i. The value of dict[s'i] is the index of the last
    occurrence of each s'i in the dictionary.
 4. Run the test data against the dictionary created in Step 2.
    a. Let D be a list of length v.
    b. For i from d+1 to floor(L/b):
       i.  If dict[s'i] is non-zero, then D_{i-d} = i - dict[s'i]. Update the
           dictionary with the index of the most recent observation, dict[s'i] = i.
       ii. If dict[si] is zero, add that value to the dictionary, i.e.,
           dict[s'i] = i. Let D_{i-d} = i.
 5. Calculate the sample mean, X-bar, and sample standard deviation, sigma-hat,
    of (log2(D1), ..., log2(Dv)).
        X-bar = (sum_{i=1}^{v} log2 Di) / v,     c = 0.5907
    and
        sigma-hat = c * sqrt( (sum_{i=1}^{v} (log2 Di)^2) / (v - 1)  -  X-bar^2 ).
 6. Compute the lower-bound of the confidence interval for the mean, based on a
    normal distribution using
        X-bar' = X-bar - 2.576 * sigma-hat / sqrt(v).
 7. Using a binary search, solve for the parameter p, such that the following
    equation is true:
        X-bar' = G(p) + (2^b - 1) G(q),
    where
        G(z) = (1/v) sum_{t=d+1}^{L} sum_{u=1}^{t} log2(u) F(z, t, u),
        F(z, t, u) = z^2 (1 - z)^(u-1)   if u < t
                   = z (1 - z)^(t-1)     if u = t,
    and
        q = (1 - p) / (2^b - 1).
    The bounds of the binary search should be 2^-b and 1.
 8. If the binary search yields a solution, then the min-entropy is the negative
    logarithm of the parameter, p:
        min-entropy = -log2(p) / b.
    If the search does not yield a solution, then the min-entropy estimation is:
        min-entropy = 1."

Worked example (PDF p. 55): d = 4, L = 48, S' = (100011, 100101, 010111, 001100,
011100, 101010, 111011, 100011), v = 4, D = (5, 6, 7, 7), X-bar = 2.6304,
sigma-hat = 0.9074, X-bar' = 1.4617, p = 0.5715, min-entropy = 0.1345.

Readings that the text leaves open (each is exposed as an option; see estimate())
--------------------------------------------------------------------------------
(a) t_upper.  The printed G(z) sums t from d+1 to L, the BIT count, but D is
    only defined for block indices d+1 .. floor(L/b) (= d + v) and the model
    behind F(z,t,u) is "the symbol at block position t was last seen u blocks
    ago".  'blocks' (default) uses t_max = d + v; 'L' uses the literal t_max = L.
    The worked example decides it -- see tests/test_compression.py.
(b) sigma_variant.  The printed radicand is  sum(x^2)/(v-1) - X-bar^2,  which is
    NOT the unbiased sample variance (that would be (sum(x^2) - v X-bar^2)/(v-1));
    algebraically printed^2/c^2 = s^2 + X-bar^2/(v-1).  'printed' (default) is
    what the worked example uses (it gives 0.9074; the unbiased form gives
    0.1364).  'unbiased' is exposed for comparison.
(c) z.  2.576 is printed; the exact 0.995 normal quantile is 2.5758293035489...
    'z=2.576' (default, literal) or z='exact'.  The fork documents its use of the
    exact value as C22c (FORK-DIVERGENCE-AND-TRUST.md section B).
(d) no_solution_low.  Over p in [2^-b, 1] the right-hand side f(p) decreases from
    its uniform value f(2^-b) to f(1) = 0 exactly (shown in G()).  If X-bar' lies
    ABOVE f(2^-b) the search has no solution and step 8 says 1 -- both readings
    agree (the fork records this as F06, NOT-A-BUG).  If X-bar' lies BELOW 0 --
    reachable at ANY v by a near-constant stream with one deviation, see the
    tests -- the literal step 8 again says 1 ('literal', default) while the
    conservative reading takes the boundary p = 1 and reports 0 ('conservative').
    The dict ALWAYS carries both numbers ('min_entropy_step8_literal' and
    'min_entropy_conservative') so a driver can see both regardless of the option.
(e) The binary search's stopping rule is unspecified.  We bisect until the
    bracket width is <= tol (default 1e-12) and report the midpoint; the number
    of iterations and the final bracket are in the dict.

Non-binary input.  The spec says the method "is only applied to binary inputs";
with bits_per_symbol > 1 the symbols are first expanded to bits (most significant
bit first, as the standard's section 6.4 / the tool's "bitstring" view does) and
the result is a per-bit figure.  mode='literal' with bits_per_symbol > 1 returns
NaN with a note, since the spec gives no value.
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any, Dict, Optional, Sequence

import numpy as np

# ---- constants fixed by the standard ---------------------------------------
B = 6               # SP 800-90B section 6.3.4 step 1 (PDF p. 53): "Let b = 6."
D_DICT = 1000       # step 2a (PDF p. 54): "the first d = 1000 elements of S'"
C = 0.5907          # step 5 (PDF p. 54): "c = 0.5907"
Z_PRINTED = 2.576   # step 6 (PDF p. 54): "X-bar' = X-bar - 2.576 sigma-hat / sqrt(v)"

NAN = float("nan")


# ---- helpers: input handling ------------------------------------------------
def to_bitstring(symbols: Sequence[int], bits_per_symbol: int) -> np.ndarray:
    """Expand each symbol to `bits_per_symbol` bits, most significant bit first.

    Symbols must lie in [0, 2**bits_per_symbol); anything else is a ValueError
    (the spec's alphabet is A, out-of-alphabet values are not silently masked).
    """
    if bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be >= 1")
    sym = np.asarray(symbols)
    if sym.ndim != 1:
        raise ValueError("symbols must be a one-dimensional sequence")
    if sym.size and (sym.min() < 0 or sym.max() >= (1 << bits_per_symbol)):
        raise ValueError(
            f"symbol out of range for bits_per_symbol={bits_per_symbol}: "
            f"min={int(sym.min())} max={int(sym.max())}")
    if bits_per_symbol == 1:
        return sym.astype(np.uint8)
    sym = sym.astype(np.uint64)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.uint64)  # MSB first
    bits = (sym[:, None] >> shifts[None, :]) & np.uint64(1)
    return bits.reshape(-1).astype(np.uint8)


def blocks_from_bits(bits: np.ndarray, b: int = B) -> np.ndarray:
    """Step 1: non-overlapping b-bit blocks; trailing bits that do not fill a
    block are discarded.  A block is read most-significant-bit first, so the
    example's block 100011 is the integer 35.  (Any bijection would do -- the
    dictionary only cares which blocks are equal -- this one is chosen so that
    the dict indices can be read against the spec's printed bit strings.)"""
    bits = np.asarray(bits, dtype=np.uint8)
    n_blocks = bits.size // b
    trimmed = bits[: n_blocks * b].reshape(n_blocks, b).astype(np.int64)
    weights = (np.int64(1) << np.arange(b - 1, -1, -1, dtype=np.int64))
    return trimmed @ weights


# ---- steps 2-4: dictionary and the distances D ------------------------------
def compression_distances(blocks: Sequence[int], d: int = D_DICT, b: int = B):
    """Steps 2, 3 and 4.  Returns (D, dict_after_step3).

    D has length v = len(blocks) - d and D[k-1] is the spec's D_k, k = 1..v.
    dict_after_step3 is the 2^b array after step 3 (zero where a block value
    never appeared among the first d), kept so the worked example's table can
    be checked.  Indices are 1-based exactly as the spec writes them; a zero in
    the dictionary means "never seen", as in step 4b.
    """
    blocks_list = [int(x) for x in blocks]
    n_blocks = len(blocks_list)
    v = n_blocks - d
    dictionary = [0] * (1 << b)                    # step 3: "all zero array of size 2^b"
    for i in range(1, min(d, n_blocks) + 1):       # step 3: "For i from 1 to d, let dict[s'_i] = i."
        dictionary[blocks_list[i - 1]] = i
    dict_after_init = np.array(dictionary, dtype=np.int64)
    if v < 1:                                      # no test data: D is empty
        return np.empty(0, dtype=np.int64), dict_after_init
    D = [0] * v                                    # step 4a: "Let D be a list of length v."
    for i in range(d + 1, n_blocks + 1):           # step 4b: "For i from d+1 to floor(L/b):"
        s = blocks_list[i - 1]
        last = dictionary[s]
        if last != 0:                              # 4b-i: "If dict[s'_i] is non-zero, then D_{i-d} = i - dict[s'_i]."
            D[i - d - 1] = i - last
        else:                                      # 4b-ii: "If dict[s'_i] is zero ... Let D_{i-d} = i."
            D[i - d - 1] = i
        dictionary[s] = i                          # both branches: dict[s'_i] = i
    return np.array(D, dtype=np.int64), dict_after_init


# ---- step 5: X-bar and sigma-hat --------------------------------------------
def sample_statistics(D: np.ndarray, c: float = C, variant: str = "printed") -> Dict[str, float]:
    """Step 5, on x_i = log2(D_i).

    variant='printed':  sigma-hat = c * sqrt( sum(x^2)/(v-1) - X-bar^2 )   (as printed)
    variant='unbiased': sigma-hat = c * sqrt( (sum(x^2) - v*X-bar^2)/(v-1) ) (textbook)
    Returns NaN for sigma-hat when v < 2 (division by v-1 = 0): the spec gives
    no value there.  The radicand is reported so a negative one is visible
    rather than hidden; it is provably >= 0 for 'printed' (it equals
    s^2 + X-bar^2/(v-1)) and the sqrt of a negative rounding residue is left NaN.
    """
    v = int(D.size)
    if v < 1:
        return {"v": v, "sum_log2_D": NAN, "sum_log2_D_sq": NAN, "X-bar": NAN,
                "radicand": NAN, "sigma-hat": NAN}
    x = np.log2(D.astype(np.float64))
    sum_x = math.fsum(x.tolist())
    sum_x2 = math.fsum((x * x).tolist())
    x_bar = sum_x / v
    if v < 2:
        radicand = NAN
    elif variant == "printed":
        radicand = sum_x2 / (v - 1) - x_bar * x_bar
    elif variant == "unbiased":
        radicand = (sum_x2 - v * x_bar * x_bar) / (v - 1)
    else:
        raise ValueError(f"unknown sigma_variant {variant!r}")
    if math.isnan(radicand) or radicand < 0.0:
        sigma = NAN
    else:
        sigma = c * math.sqrt(radicand)
    return {"v": v, "sum_log2_D": sum_x, "sum_log2_D_sq": sum_x2, "X-bar": x_bar,
            "radicand": radicand, "sigma-hat": sigma}


# ---- step 6: the lower confidence bound --------------------------------------
def lower_confidence_bound(x_bar: float, sigma: float, v: int, z: float = Z_PRINTED) -> float:
    """Step 6: X-bar' = X-bar - z * sigma-hat / sqrt(v), z = 2.576 as printed."""
    if v < 1:
        return NAN
    return x_bar - z * sigma / math.sqrt(v)


def exact_z_0995() -> float:
    """The exact two-sided 99% normal quantile Phi^{-1}(0.995), by bisection on
    math.erfc (pure Python; no scipy/mpmath).  The spec prints it as 2.576."""
    lo, hi = 2.0, 3.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        # upper tail P(Z > mid) = erfc(mid/sqrt(2))/2 ; we want it = 0.005
        if 0.5 * math.erfc(mid / math.sqrt(2.0)) > 0.005:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-16:
            break
    return 0.5 * (lo + hi)


# ---- step 7: F, G and the equation ------------------------------------------
def F(z: float, t: int, u: int) -> float:
    """The printed piecewise F(z, t, u):  z^2 (1-z)^(u-1) if u < t;  z (1-z)^(t-1) if u = t."""
    if u < t:
        return z * z * (1.0 - z) ** (u - 1)
    if u == t:
        return z * (1.0 - z) ** (t - 1)
    raise ValueError("F(z, t, u) is only defined for 1 <= u <= t")


def G_literal(z: float, v: int, d: int, t_max: Optional[int] = None) -> float:
    """G(z) exactly as printed, as a double loop.  O(t_max^2): for inspection and
    for checking G() on small cases only.
        G(z) = (1/v) sum_{t=d+1}^{t_max} sum_{u=1}^{t} log2(u) F(z, t, u)
    t_max defaults to d + v (= floor(L/b), the last block index); pass t_max=L
    for the literal upper limit printed in the spec (reading (a) above)."""
    if t_max is None:
        t_max = d + v
    total = 0.0
    for t in range(d + 1, t_max + 1):
        for u in range(1, t + 1):
            total += math.log2(u) * F(z, t, u)
    return total / v


def G_terms(z: float, v: int, d: int, t_max: Optional[int] = None) -> np.ndarray:
    """The inner sums  g_t = sum_{u=1}^{t} log2(u) F(z, t, u)  for t = d+1 .. t_max,
    returned as an array of length t_max - d, so each term can be compared.

    Vectorised by prefix sums.  Writing a_u = log2(u) (1-z)^(u-1):
        g_t = z^2 * sum_{u=1}^{t-1} a_u  +  z * a_t
    because for u < t, F = z^2 (1-z)^(u-1) = z * a_u / log2(u) * z ... i.e.
    log2(u) F(z,t,u) = z^2 a_u, and the u = t term is log2(t) z (1-z)^(t-1) = z a_t.
    (1-z)^(u-1) is evaluated as exp((u-1) * log1p(-z)), which is the same number
    with less rounding than repeated multiplication or pow for small z; the unit
    tests compare it against the plain-power G_literal.
    The endpoints are exact: z = 0 gives every F = 0; z = 1 gives F(1,t,u) = 0 for
    every u except u = 1, where log2(1) = 0, so G(0) = G(1) = 0.
    """
    if t_max is None:
        t_max = d + v
    n_t = t_max - d
    if n_t <= 0:
        return np.empty(0, dtype=np.float64)
    if z <= 0.0 or z >= 1.0:
        if z == 0.0 or z == 1.0:
            return np.zeros(n_t, dtype=np.float64)
        raise ValueError("G(z) needs 0 <= z <= 1")
    u = np.arange(1, t_max + 1, dtype=np.float64)              # u = 1 .. t_max
    with np.errstate(under="ignore"):
        a = np.log2(u) * np.exp((u - 1.0) * math.log1p(-z))     # a_u = log2(u) (1-z)^(u-1)
    prefix = np.concatenate(([0.0], np.cumsum(a)))             # prefix[k] = sum_{u=1}^{k} a_u
    t = np.arange(d + 1, t_max + 1)                            # t = d+1 .. t_max
    inner = (z * z) * prefix[t - 1] + z * a[t - 1]             # z^2 * sum_{u<t} a_u  +  z * a_t
    return inner


def G(z: float, v: int, d: int, t_max: Optional[int] = None) -> float:
    """G(z) = (1/v) sum_{t=d+1}^{t_max} sum_{u=1}^{t} log2(u) F(z, t, u),  vectorised.
    See G_terms for the derivation and G_literal for the printed double loop."""
    terms = G_terms(z, v, d, t_max)
    return float(np.sum(terms)) / v


def rhs(p: float, v: int, d: int, b: int = B, t_max: Optional[int] = None) -> float:
    """The right-hand side of step 7:  G(p) + (2^b - 1) G(q),  q = (1 - p)/(2^b - 1)."""
    k_minus_1 = (1 << b) - 1
    q = (1.0 - p) / k_minus_1
    return G(p, v, d, t_max) + k_minus_1 * G(q, v, d, t_max)


def solve_p(x_bar_prime: float, v: int, d: int, b: int = B, t_max: Optional[int] = None,
            tol: float = 1e-12, max_iter: int = 200) -> Dict[str, Any]:
    """Step 7's binary search for p in [2^-b, 1] with  rhs(p) = X-bar'.

    rhs(p) decreases in p on [2^-b, 1] (p = 2^-b is the uniform distribution,
    which maximises the expected log-distance; rhs(1) = 0).  So:
      X-bar' > rhs(2^-b)  -> no solution  (status 'no_solution_above_uniform')
      X-bar' < rhs(1) = 0 -> no solution  (status 'no_solution_below_zero')
      otherwise bisect; if rhs(mid) > X-bar' the root is to the right (lo = mid).
    Returns p (midpoint of the final bracket), found flag, status, iteration
    count, bracket and the residual rhs(p) - X-bar'.
    """
    lo, hi = 2.0 ** (-b), 1.0
    out: Dict[str, Any] = {"p": NAN, "found_p": False, "status": "", "iterations": 0,
                           "search_lo": lo, "search_hi": hi,
                           "rhs_at_lower_bound": NAN, "rhs_at_upper_bound": NAN,
                           "residual": NAN}
    if v < 1 or not math.isfinite(x_bar_prime):
        out["status"] = "undefined"          # spec gives no value (v < 1 or X-bar' not finite)
        return out
    f_lo = rhs(lo, v, d, b, t_max)
    f_hi = rhs(hi, v, d, b, t_max)           # = 0 exactly, see G_terms
    out["rhs_at_lower_bound"] = f_lo
    out["rhs_at_upper_bound"] = f_hi
    if x_bar_prime > f_lo:
        out["status"] = "no_solution_above_uniform"
        return out
    if x_bar_prime < f_hi:
        out["status"] = "no_solution_below_zero"
        return out
    if x_bar_prime == f_hi:                  # exactly on the p = 1 boundary (all D_i = 1)
        out.update(p=hi, found_p=True, status="found_at_upper_bound", residual=0.0,
                   search_lo=hi, search_hi=hi)
        return out
    if x_bar_prime == f_lo:                  # exactly the uniform value
        out.update(p=lo, found_p=True, status="found_at_lower_bound", residual=0.0,
                   search_lo=lo, search_hi=lo)
        return out
    iterations = 0
    while iterations < max_iter and (hi - lo) > tol:
        mid = 0.5 * (lo + hi)
        if rhs(mid, v, d, b, t_max) > x_bar_prime:
            lo = mid                         # rhs decreasing: need a larger p
        else:
            hi = mid
        iterations += 1
    p = 0.5 * (lo + hi)
    out.update(p=p, found_p=True, status="found", iterations=iterations,
               search_lo=lo, search_hi=hi, residual=rhs(p, v, d, b, t_max) - x_bar_prime)
    return out


# ---- the estimator ----------------------------------------------------------
def estimate(symbols: Sequence[int], bits_per_symbol: int, **options) -> Dict[str, Any]:
    """SP 800-90B section 6.3.4 Compression Estimate.

    symbols: ints in [0, 2**bits_per_symbol).  Options (all keyword):
      mode='bitstring' | 'literal'   bitstring: expand symbols to bits MSB-first and
                                     run the (binary-only) estimate on the bits.
                                     literal: run on the symbols as given; only
                                     defined for bits_per_symbol == 1 (NaN otherwise).
      d=1000, b=6, c=0.5907          the spec's constants (the worked example uses d=4)
      z=2.576 | 'exact' | float      step 6's quantile (reading (c))
      t_upper='blocks' | 'L'         G's upper limit: d+v blocks, or the literal L bits (reading (a))
      sigma_variant='printed' | 'unbiased'                                     (reading (b))
      no_solution_low='literal' | 'conservative'   X-bar' < 0 handling          (reading (d))
      tol=1e-12, max_iter=200        bisection stopping rule                      (reading (e))
    Returns a dict with 'min_entropy' and the named intermediates; NaN where the
    spec gives no value.
    """
    mode = options.pop("mode", "bitstring")
    d = int(options.pop("d", D_DICT))
    b = int(options.pop("b", B))
    c = float(options.pop("c", C))
    z_opt = options.pop("z", Z_PRINTED)
    t_upper = options.pop("t_upper", "blocks")
    sigma_variant = options.pop("sigma_variant", "printed")
    no_solution_low = options.pop("no_solution_low", "literal")
    tol = float(options.pop("tol", 1e-12))
    max_iter = int(options.pop("max_iter", 200))
    if options:
        raise TypeError(f"unknown options: {sorted(options)}")
    if mode not in ("bitstring", "literal"):
        raise ValueError("mode must be 'bitstring' or 'literal'")
    if t_upper not in ("blocks", "L"):
        raise ValueError("t_upper must be 'blocks' or 'L'")
    if no_solution_low not in ("literal", "conservative"):
        raise ValueError("no_solution_low must be 'literal' or 'conservative'")
    z = exact_z_0995() if z_opt == "exact" else float(z_opt)

    result: Dict[str, Any] = {
        "estimator": "Compression Estimate", "spec": "SP 800-90B 6.3.4 (PDF pp. 53-55)",
        "mode": mode, "bits_per_symbol": int(bits_per_symbol), "n_symbols": int(len(symbols)),
        "b": b, "d": d, "c": c, "z": z, "t_upper": t_upper, "sigma_variant": sigma_variant,
        "no_solution_low": no_solution_low,
        "L": NAN, "n_blocks": NAN, "v": NAN,
        "X-bar": NAN, "sigma-hat": NAN, "X-bar'": NAN, "radicand": NAN,
        "sum_log2_D": NAN, "sum_log2_D_sq": NAN,
        "found_p": False, "p": NAN, "search_status": "", "search_iterations": 0,
        "search_lo": NAN, "search_hi": NAN, "rhs_at_lower_bound": NAN,
        "rhs_at_upper_bound": NAN, "residual": NAN,
        "min_entropy": NAN, "min_entropy_step8_literal": NAN, "min_entropy_conservative": NAN,
        "note": "",
    }

    # -- which bits are assessed ------------------------------------------------
    if mode == "literal" and bits_per_symbol != 1:
        result["note"] = ("spec 6.3.4: 'This entropy estimation method is only applied to "
                          "binary inputs'; no value for literal non-binary symbols")
        return result
    bits = to_bitstring(symbols, bits_per_symbol)      # identity when bits_per_symbol == 1
    L = int(bits.size)                                 # the spec's L: the number of bits
    result["L"] = L

    # -- step 1: blocks -----------------------------------------------------------
    blocks = blocks_from_bits(bits, b)
    n_blocks = int(blocks.size)                        # floor(L/b)
    result["n_blocks"] = n_blocks

    # -- steps 2-4: dictionary and D ---------------------------------------------
    v = n_blocks - d                                   # step 2b: v = floor(L/b) - d
    result["v"] = v
    if v < 1:
        result["note"] = f"v = floor(L/b) - d = {v} < 1: no test data; spec gives no value"
        return result
    D, _dict_after_init = compression_distances(blocks, d, b)

    # -- step 5 ---------------------------------------------------------------------
    stats = sample_statistics(D, c, sigma_variant)
    result.update({k: stats[k] for k in ("X-bar", "sigma-hat", "radicand", "sum_log2_D", "sum_log2_D_sq")})

    # -- step 6 ---------------------------------------------------------------------
    x_bar_prime = lower_confidence_bound(stats["X-bar"], stats["sigma-hat"], v, z)
    result["X-bar'"] = x_bar_prime
    if not math.isfinite(x_bar_prime):
        result["note"] = ("X-bar' is not finite (sigma-hat undefined for v < 2, or overflow); "
                          "spec gives no value")
        result["search_status"] = "undefined"
        return result

    # -- step 7 ---------------------------------------------------------------------
    t_max = (d + v) if t_upper == "blocks" else L
    result["t_max"] = t_max
    search = solve_p(x_bar_prime, v, d, b, t_max, tol, max_iter)
    result.update({"found_p": search["found_p"], "p": search["p"],
                   "search_status": search["status"], "search_iterations": search["iterations"],
                   "search_lo": search["search_lo"], "search_hi": search["search_hi"],
                   "rhs_at_lower_bound": search["rhs_at_lower_bound"],
                   "rhs_at_upper_bound": search["rhs_at_upper_bound"],
                   "residual": search["residual"]})

    # -- step 8 ---------------------------------------------------------------------
    if search["found_p"]:
        h = -math.log2(search["p"]) / b                # "min-entropy = -log2(p)/b"
        result["min_entropy_step8_literal"] = h
        result["min_entropy_conservative"] = h
    elif search["status"] == "no_solution_above_uniform":
        # X-bar' exceeds even the uniform distribution's expectation: "If the search
        # does not yield a solution, then the min-entropy estimation is: min-entropy = 1."
        result["min_entropy_step8_literal"] = 1.0
        result["min_entropy_conservative"] = 1.0
        result["note"] = ("X-bar' > rhs(2^-b): the equation has no solution in [2^-b, 1]; "
                          "step 8 gives 1 (the fork records this as F06, spec-literal)")
    elif search["status"] == "no_solution_below_zero":
        # X-bar' < 0 = rhs(1): no p in [2^-b, 1] solves the equation.  Literally step 8
        # says 1; the conservative reading takes the boundary p = 1, i.e. 0.
        result["min_entropy_step8_literal"] = 1.0
        result["min_entropy_conservative"] = 0.0
        result["note"] = ("X-bar' < 0 = rhs(1): no solution in [2^-b, 1]; literal step 8 says 1, "
                          "the conservative boundary value p = 1 says 0 -- BOTH reported")
    else:
        result["note"] = f"search status {search['status']!r}; spec gives no value"
        return result
    result["min_entropy"] = (result["min_entropy_step8_literal"] if no_solution_low == "literal"
                             else result["min_entropy_conservative"])
    return result


# ---- __main__ ---------------------------------------------------------------
def _usage() -> str:
    return ("usage: python compression.py <rawfile> <bits_per_symbol> [--literal|--bitstring] "
            "[--d=N] [--z=exact|<float>] [--t-upper=blocks|L] [--sigma=printed|unbiased] "
            "[--no-solution-low=literal|conservative]\n"
            "  rawfile: one symbol per byte, the low bits_per_symbol bits are the symbol")


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def main(argv: Sequence[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = [a for a in argv[1:] if a.startswith("--")]
    if len(args) != 2:
        sys.stderr.write(_usage() + "\n")
        return 2
    path, bps = args[0], int(args[1])
    opts: Dict[str, Any] = {}
    for fl in flags:
        if fl == "--literal":
            opts["mode"] = "literal"
        elif fl == "--bitstring":
            opts["mode"] = "bitstring"
        elif fl.startswith("--d="):
            opts["d"] = int(fl[4:])
        elif fl.startswith("--z="):
            opts["z"] = fl[4:] if fl[4:] == "exact" else float(fl[4:])
        elif fl.startswith("--t-upper="):
            opts["t_upper"] = fl[len("--t-upper="):]
        elif fl.startswith("--sigma="):
            opts["sigma_variant"] = fl[len("--sigma="):]
        elif fl.startswith("--no-solution-low="):
            opts["no_solution_low"] = fl[len("--no-solution-low="):]
        else:
            sys.stderr.write(f"unknown flag {fl}\n" + _usage() + "\n")
            return 2
    raw = np.fromfile(path, dtype=np.uint8)
    if bps < 8:
        symbols = raw & np.uint8((1 << bps) - 1)       # "low bits_per_symbol bits are the symbol"
    else:
        symbols = raw
    res = estimate(symbols, bps, **opts)
    res["rawfile"] = path
    sys.stdout.write(json.dumps(_jsonable(res), indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
