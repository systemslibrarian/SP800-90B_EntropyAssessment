#!/usr/bin/env python3
"""
py90b.chisquare -- independent reference implementation of SP 800-90B
Section 5.2 "Additional Chi-square Statistical Tests" (PDF p. 43-47):

    5.2.1  Testing Independence for Non-Binary Data        (PDF p. 43-44)
    5.2.2  Testing Goodness-of-fit for Non-Binary Data     (PDF p. 45)
    5.2.3  Testing Independence for Binary Data            (PDF p. 45-46)
    5.2.4  Testing Goodness-of-fit for Binary Data         (PDF p. 46-47)
    5.2.5  Length of the Longest Repeated Substring Test   (PDF p. 47)

INDEPENDENCE.  Written from the text of NIST SP 800-90B (January 2018) only,
as extracted to reference/sp800-90b.pages.txt.  Nothing under cpp/ was read.
The only thing taken from the C++ tool is the NAMES of its printed
intermediates, from reference/cpp-verbose-labels-iid.txt:

    "Chi square independence: T / df / P-value"
    "Chi square goodness of fit: T / df / P-value"
    "Chi square tests: Passed|Failed"
    "Literal Longest Repeated Substring results: P_col / W / Pr(X >= 1)"
    "Length of longest repeated substring test: Passed|Failed"

so a differential driver can match the keys of the returned dict.  (The
capture only shows the "Literal" prefix; the "Bitstring" prefix used here for
track='bitstring' is this module's guess by analogy with the other labels.)

These tests award NO min-entropy figure (Section 5 decides IID / non-IID; the
estimate is then made by Section 6.1 or 6.2), so 'min_entropy' is float('nan').

THE SPEC, quoted.  Every function below carries the sentence it implements.
Only the conventions that the text leaves open are decided here, and each
such decision is listed under "READINGS" and exposed as an option where two
readings differ materially:

  R1  Alphabet (5.2.1/5.2.2).  "si in A = {x1, ..., xk}".  Example 11 says
      "The alphabet consists of k = 3 values {1, 2, 3}" for data drawn from
      {1,2,3}; the text never says whether a declared-but-absent symbol value
      is in A.  alphabet='observed' (default): A is the set of values that
      occur in S.  alphabet='declared': A is all 2**bits_per_symbol values,
      absent ones having p_i = 0 (they join the first bin with e = 0 and only
      change k, hence the 5.2.1 degrees of freedom nbin - k).
  R2  Tie order when sorting by expected value.  Not stated.  Example 11
      lists (1,3) before (3,1), (1,2) before (2,1), (2,3) before (3,2): a
      stable sort of the pairs taken in lexicographic order (zi, zj).  That
      is what is done; for 5.2.2 ties are broken by ascending symbol value.
      The sort key is exact (c_i*c_j, resp. c_i, as integers) so that genuine
      ties ARE ties and the bin boundary "at least five" is decided exactly:
      sum e >= 5  <=>  sum(c_i c_j) >= 10 L   (5.2.1),   sum c_i >= 50  (5.2.2).
      A floating-point implementation could decide an exact boundary case
      differently; such cases are flagged in the result ('exact_boundary').
  R3  5.2.1 "If the value of degrees of freedom is less than one, do not apply
      the test" is explicit.  5.2.2 has no such sentence; its df = 9(nbin-1)
      is zero only when nbin = 1 (e.g. a constant sequence).  Default
      gof_df_zero='not_applied' (by analogy with 5.2.1); gof_df_zero=
      'degenerate' takes the chi-square with zero degrees of freedom to be the
      point mass at 0, so any T > 0 fails.  Both verdicts are returned.
  R4  5.2.3 "Find the maximum integer m such that min(p0,p1)^m floor(L/m) >= 5
      ... If m is 1, the test fails."  When not even m = 1 satisfies the
      inequality (fewer than five of the minority bit, or none) no such m
      exists; this is reported as m = 0 and the test fails, as it does for
      m = 1.  The inequality is evaluated exactly: c_min^m * floor(L/m) >= 5 L^m.
  R5  5.2.4 prints the critical value "27.887".  The 0.999 quantile of
      chi-square with 9 degrees of freedom is 27.877 (checked below against
      this module's own survival function: sf(27.877, 9) = 0.00100 and
      sf(27.887, 9) = 0.00099...).  variant='literal' (default) compares T with
      27.887 AS PRINTED; variant='pvalue' uses the p-value < 0.001, which is
      what "critical value at 0.001" means everywhere else.  Both verdicts are
      returned.  The literal constant is the PERMISSIVE one (T in
      (27.877, 27.887] passes under it).
  R6  5.2.4 with p = 0 or p = 1 (a constant bit string) makes e1 or e0 zero and
      every term (0 - 0)^2 / 0.  The text gives no value: T = nan, the test is
      reported as not applied.  (5.2.3 fails that input anyway: see R4.)
  R7  "Binary data" is taken to mean 1-bit samples: bits_per_symbol == 1, or
      track='bitstring'.  An 8-bit file whose values happen to be only {0, 1}
      is non-binary data with k = 2 under this reading.  Override: binary=.
  R8  5.2.5 step 3 says "for at least one i != j"; occurrences are allowed to
      overlap (e.g. (7,7,7,7) has W = 3).  W is read off a suffix array; for
      small inputs a literal substring-set search is run as well and must
      agree ('auto').
  R9  Section 3.1.3: "The bits after the first 1 000 000 bits may be ignored."
      Optional in the text; bitstring_limit=None (default) keeps every bit.
  R10 The decision T > critical value is implemented as the p-value
      Pr[chi2_df >= T] < 0.001 (equivalent in exact arithmetic) and, for the
      record, as T > the 0.999 quantile found by bisection on the same
      survival function ('fail_by_critical_value').  variant='literal' uses the
      quantile comparison, variant='pvalue' the p-value; they can differ only
      by floating-point noise at the boundary (and by R5 for 5.2.4).

The chi-square survival function is implemented here (regularized upper
incomplete gamma, series + continued fraction), not imported: see chi2_sf().
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np

# --------------------------------------------------------------------------
# Constants from the text
# --------------------------------------------------------------------------

ALPHA = 0.001                 # 5.2.1-5.2.5: "type I error is chosen as 0.001"
                              # / "fails if Pr(X >= 1) is less than 0.001"
MIN_EXPECTED = 5              # 5.2.1 / 5.2.2: "expected value of each bin is at
                              # least five"; 5.2.3: "... >= 5"
GOF_PARTS = 10                # 5.2.2 / 5.2.4: "ten data subsets"
BINARY_M_CAP = 11             # 5.2.3: "If m is greater than 11, set m = 11"
BINARY_GOF_DF = 9             # 5.2.4: "nine degrees of freedom"
BINARY_GOF_CRITICAL_PRINTED = 27.887   # 5.2.4: "the critical value at 0.001,
                                       # which is 27.887" (see R5)

VARIANTS = ("literal", "pvalue")


# ==========================================================================
# Chi-square survival function  Pr[X >= x],  X ~ chi-square(df)
# ==========================================================================
#
#   Pr[X >= x] = Q(df/2, x/2),   Q(a, x) = Gamma(a, x) / Gamma(a)
#
# Q is computed with the two classical expansions of the incomplete gamma
# function (Abramowitz & Stegun 6.5.29 and 6.5.31; Numerical Recipes gammp /
# gammq): the power series for x < a + 1 and the continued fraction (evaluated
# by the modified Lentz method) for x >= a + 1.  Both are iterated to a
# relative change below 1e-16 and capped at 10**7 terms.
#
# Checked in tests/test_chisquare.py against values that do not come from this
# code:
#   * df = 2 is the exponential:        sf(x, 2) = exp(-x/2)
#       sf(3.7, 2) = exp(-1.85) = 0.15723716631362761
#   * df = 1 is a folded normal:        sf(x, 1) = erfc(sqrt(x/2))
#       sf(1.0, 1) = 0.31731050786291410
#   * df = 4:                           sf(x, 4) = exp(-x/2) (1 + x/2)
#   * tabulated 0.999 quantiles (standard chi-square tables, and the spec's own
#     Example 11 "critical value 16.266" for df = 3):
#       sf(16.266, 3) = 0.00100   sf(27.877, 9) = 0.00100   sf(10.828, 1) = 0.00100
#       sf(149.449, 100) = 0.00100
#   * tabulated 0.95 / 0.99 quantiles:  sf(3.841, 1) = 0.0500, sf(23.209, 10) = 0.0100

_EPS = 1e-16
_ITMAX = 10_000_000


def _gamma_series_P(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) by its power series
    (A&S 6.5.29):  P = e^-x x^a / Gamma(a+1) * sum_{n>=0} x^n / ((a+1)...(a+n))."""
    if x <= 0.0:
        return 0.0
    ap = a
    term = 1.0 / a
    total = term
    for _ in range(_ITMAX):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * _EPS:
            break
    else:  # pragma: no cover
        raise ArithmeticError("incomplete gamma series did not converge")
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf_Q(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) by its continued fraction
    (A&S 6.5.31), modified Lentz evaluation."""
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, _ITMAX):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    else:  # pragma: no cover
        raise ArithmeticError("incomplete gamma continued fraction did not converge")
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def regularized_gamma_Q(a: float, x: float) -> float:
    """Q(a, x) = Gamma(a, x) / Gamma(a) for a > 0, x >= 0."""
    if a <= 0.0:
        raise ValueError("a must be > 0")
    if x < 0.0:
        raise ValueError("x must be >= 0")
    if x == 0.0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_series_P(a, x)
    return _gamma_cf_Q(a, x)


def chi2_sf(x: float, df: float) -> float:
    """Pr[X >= x] for X ~ chi-square with df > 0 degrees of freedom."""
    if df <= 0:
        raise ValueError("df must be > 0 (df = 0 is the point mass at 0; see R3)")
    if math.isnan(x):
        return float("nan")
    if x <= 0.0:
        return 1.0
    if math.isinf(x):
        return 0.0
    return regularized_gamma_Q(df / 2.0, x / 2.0)


def chi2_critical_value(alpha: float, df: float) -> float:
    """The value c with Pr[X >= c] = alpha (the (1-alpha) quantile), by
    bisection on chi2_sf.  Used only to report T > critical value alongside
    the p-value (R10); the two agree except for floating-point noise."""
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    lo, hi = 0.0, max(1.0, float(df))
    while chi2_sf(hi, df) > alpha:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid == lo or mid == hi:
            break
        if chi2_sf(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


# ==========================================================================
# Helpers shared by the tests
# ==========================================================================

def _as_symbol_array(symbols, bits_per_symbol: int, validate: bool = True) -> np.ndarray:
    if not isinstance(bits_per_symbol, (int, np.integer)) or bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be a positive integer")
    if isinstance(symbols, (bytes, bytearray, memoryview)):
        S = np.frombuffer(bytes(symbols), dtype=np.uint8).astype(np.int64)
    else:
        S = np.asarray(symbols)
        if S.ndim != 1:
            raise ValueError("symbols must be a one-dimensional sequence")
        if S.size and not np.issubdtype(S.dtype, np.integer):
            T = S.astype(np.int64)
            if not np.array_equal(T, S):
                raise ValueError("symbols must be integers")
            S = T
        S = S.astype(np.int64, copy=False)
    if validate and S.size:
        if S.min() < 0 or S.max() >= (1 << int(bits_per_symbol)):
            raise ValueError(f"symbols must lie in [0, 2**{bits_per_symbol})")
    return S


def to_bitstring(symbols, bits_per_symbol: int, bit_order: str = "msb") -> np.ndarray:
    """Section 3.1.3 (PDF p. 20): the L samples "(each having n bits)" are
    "considered as a bitstring of size nL".  Expand every symbol to
    bits_per_symbol bits and concatenate; MSB-first by default (the text does
    not fix the order within a symbol; MSB-first is this audit's convention)."""
    bps = int(bits_per_symbol)
    S = _as_symbol_array(symbols, bps, validate=True)
    if bps == 1:
        return S.copy()
    if bit_order == "msb":
        shifts = np.arange(bps - 1, -1, -1, dtype=np.int64)
    elif bit_order == "lsb":
        shifts = np.arange(0, bps, dtype=np.int64)
    else:
        raise ValueError("bit_order must be 'msb' or 'lsb'")
    bits = (S[:, None] >> shifts[None, :]) & 1
    return bits.reshape(-1).astype(np.int64)


def _symbol_counts(S: np.ndarray, bits_per_symbol: int, alphabet: str):
    """(values, counts): the alphabet A = {x1..xk} and "the number of x_i in S".
    alphabet='observed': the values that occur (R1).  'declared': every value
    in [0, 2**bits_per_symbol), absent ones with count 0."""
    k_declared = 1 << int(bits_per_symbol)
    counts_all = np.bincount(S, minlength=k_declared)
    if alphabet == "observed":
        values = np.nonzero(counts_all)[0]
    elif alphabet == "declared":
        values = np.arange(k_declared)
    else:
        raise ValueError("alphabet must be 'observed' or 'declared'")
    return values.astype(np.int64), counts_all[values].astype(np.int64)


def _greedy_bins(order, weights, threshold):
    """The binning procedure common to 5.2.1 step 2 and 5.2.2 step 3, in exact
    integer arithmetic (R2).

    `order`     : the items (indices) already sorted ascending by expected value;
    `weights`   : integer weight of each item, proportional to its expected
                  value (c_i*c_j for 5.2.1, c_i for 5.2.2);
    `threshold` : the integer weight that corresponds to an expected value of
                  exactly five (10 L for 5.2.1, 50 for 5.2.2).

    5.2.1: "Allocate the possible (zi, zj) pairs, starting from the smallest
    e_ij, into bins such that the expected value of each bin is at least five.
    ... After allocating all pairs, if the expected value of the last bin is
    less than five, merge the last two bins."
    5.2.2: "Starting from List[1], allocate the sample values into bins.  Assign
    consecutive List[i] values to a bin until the sum of the e_i for those
    binned items is at least five, then begin assigning the following List[i]
    value(s) to the next bin.  If the expected value of the last bin is less
    than five, merge the last two bins."

    Returns (bins, bin_weights, exact_boundary): bins is a list of lists of
    items; exact_boundary is True when some bin closed with weight == threshold
    (a case a floating-point implementation might decide the other way)."""
    bins, bin_weights = [], []
    cur, cur_w = [], 0
    exact_boundary = False
    for item in order:
        cur.append(int(item))
        cur_w += int(weights[item])
        if cur_w >= threshold:                     # "at least five": close the bin
            if cur_w == threshold:
                exact_boundary = True
            bins.append(cur)
            bin_weights.append(cur_w)
            cur, cur_w = [], 0
    if cur:                                        # items left over below five
        bins.append(cur)
        bin_weights.append(cur_w)
    merged_last_two = False
    if len(bins) >= 2 and bin_weights[-1] < threshold:
        # "if the expected value of the last bin is less than five, merge the
        #  last two bins"
        bins[-2].extend(bins[-1])
        bin_weights[-2] += bin_weights[-1]
        bins.pop()
        bin_weights.pop()
        merged_last_two = True
    return bins, bin_weights, exact_boundary, merged_last_two


def _chi_square_decision(T: float, df: int, variant: str) -> dict:
    """Shared tail: p-value, critical value and the fail/not-applied verdicts
    (R10).  df < 1 means "do not apply the test" (5.2.1; extended per R3)."""
    out = {"T": float(T), "df": int(df)}
    if df < 1 or math.isnan(T):
        out.update({"P-value": float("nan"), "critical_value": float("nan"),
                    "applied": False, "fail_by_pvalue": False,
                    "fail_by_critical_value": False, "failed": False})
        return out
    p = chi2_sf(T, df)
    crit = chi2_critical_value(ALPHA, df)
    out.update({"P-value": p, "critical_value": crit, "applied": True,
                "fail_by_pvalue": bool(p < ALPHA),
                "fail_by_critical_value": bool(T > crit)})
    out["failed"] = out["fail_by_critical_value"] if variant == "literal" else out["fail_by_pvalue"]
    return out


# ==========================================================================
# 5.2.1  Testing Independence for Non-Binary Data  (PDF p. 43-44)
# ==========================================================================

def independence_non_binary(S: np.ndarray, bits_per_symbol: int, *,
                            alphabet: str = "observed", variant: str = "literal",
                            keep_bins: bool = True) -> dict:
    """
    "Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk}, the
     following steps are initially performed to determine the number of bins
     nbin needed for the chi-square tests.
     1. Find the proportion p_i of each x_i in S, i.e., p_i = (number of x_i in
        S)/L.  Calculate the expected number of occurrences of each possible
        pair (zi, zj) in S, as e_ij = p_i p_j L/2.
     2. Allocate the possible (zi, zj) pairs, starting from the smallest e_ij,
        into bins such that the expected value of each bin is at least five.
        The expected value of a bin is equal to the sum of the e_ij values of
        the pairs that are included in the bin.  After allocating all pairs, if
        the expected value of the last bin is less than five, merge the last
        two bins.  Let nbin be the number of bins constructed using this
        procedure.
     After constructing the bins, the Chi-square test is executed as follows:
     1. Let o be a list of nbin counts, each initialized to 0.  For j=1 to L-1:
        a. If the pair (sj, sj+1) is in bin i, increment oi by 1.
        b. Let j = j+2.
     2. The test statistic is calculated as T = sum_{i=1}^{nbin}
        (oi - E(Bin_i))^2 / E(Bin_i).  The test fails if T is greater than the
        critical value of the Chi-square test statistic with (nbin-1)-(k-1) =
        nbin-k degrees of freedom when the probability of type I error is
        chosen as 0.001.  If the value of degrees of freedom is less than one,
        do not apply the test."
    """
    L = int(S.size)
    values, counts = _symbol_counts(S, bits_per_symbol, alphabet)
    k = int(values.size)
    res = {"L": L, "k": k}
    if L < 2 or k == 0:
        res.update(_chi_square_decision(float("nan"), 0, variant))
        res.update({"nbin": 0, "exact_boundary": False, "merged_last_two": False})
        return res

    # Step 1.  e_ij = p_i p_j L/2 = c_i c_j / (2L).  Weight w_ij = c_i c_j (exact);
    # e_ij >= 5  <=>  w_ij >= 10 L.
    c = counts.astype(object) if L > 3_000_000_000 else counts  # c_i*c_j < 2**63 for L <= 3e9
    w = np.multiply.outer(c, c).reshape(-1)             # row-major: (i, j) lexicographic
    # Step 2.  "starting from the smallest e_ij": stable sort keeps the
    # lexicographic (zi, zj) order among equal expectations (R2).
    order = np.argsort(w, kind="stable")
    bins, bin_w, exact_boundary, merged = _greedy_bins(order, w, MIN_EXPECTED * 2 * L)
    nbin = len(bins)
    E = np.array([bw / (2.0 * L) for bw in bin_w], dtype=float)

    # Chi-square step 1.  Non-overlapping pairs (s1,s2), (s3,s4), ...: floor(L/2)
    # of them; an odd trailing sample is unused.
    idx_of_value = np.full(int(values.max()) + 1, -1, dtype=np.int64)
    idx_of_value[values] = np.arange(k)
    idx = idx_of_value[S]
    npairs = L // 2
    pair_index = idx[0:2 * npairs:2] * k + idx[1:2 * npairs:2]
    o_pairs = np.bincount(pair_index, minlength=k * k)
    bin_of_pair = np.empty(k * k, dtype=np.int64)
    for b, members in enumerate(bins):
        bin_of_pair[members] = b
    o = np.bincount(bin_of_pair, weights=o_pairs, minlength=nbin)

    # Chi-square step 2.
    T = float(np.sum((o - E) ** 2 / E))
    df = nbin - k
    res.update(_chi_square_decision(T, df, variant))
    res.update({"nbin": nbin, "npairs": int(npairs), "exact_boundary": exact_boundary,
                "merged_last_two": merged})
    if keep_bins and k * k <= 4096:
        res["bins"] = [
            {"pairs": [(int(values[m // k]), int(values[m % k])) for m in members],
             "E": float(E[b]), "o": int(o[b])}
            for b, members in enumerate(bins)]
    return res


# ==========================================================================
# 5.2.2  Testing Goodness-of-fit for Non-Binary Data  (PDF p. 45)
# ==========================================================================

def goodness_of_fit_non_binary(S: np.ndarray, bits_per_symbol: int, *,
                               alphabet: str = "observed", variant: str = "literal",
                               gof_df_zero: str = "not_applied", keep_bins: bool = True) -> dict:
    """
    "Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk}, perform
     the following steps to calculate the number of bins nbin for the test.
     1. Let c_i be the number of occurrences of x_i in the entire dataset S, and
        let e_i = c_i/10, for 1 <= i <= k.  Note that c_i is divided by ten
        because S will be partitioned into ten data subsets.
     2. Let List[i] be the sample value with the ith smallest e_i ...
     3. Starting from List[1], allocate the sample values into bins.  Assign
        consecutive List[i] values to a bin until the sum of the e_i for those
        binned items is at least five, then begin assigning the following
        List[i] value(s) to the next bin.  If the expected value of the last bin
        is less than five, merge the last two bins.  Let nbin be the number of
        bins constructed after this procedure.
     4. Let Ei be the expected number of sample values in Bin i; Ei is the sum
        of the ei for the listed items in that bin.
     Given nbin, Ei and list of samples for each bin, the chi-square
     goodness-of-fit test is executed as follows:
     1. Partition S into ten non-overlapping sequences of length floor(L/10),
        where S_d = (s_{d floor(L/10)+1}, ..., s_{(d+1) floor(L/10)}) for
        d = 0, ..., 9.  If L is not a multiple of 10, the remaining samples are
        not used.
     2. T = 0.
     3. For d = 0 to 9
        3.1. For i = 1 to nbin
             3.1.1. Let oi be the total number of times the samples in Bin i
                    appear in S_d.
             3.1.2. T = T + (oi - Ei)^2 / Ei.
     The test fails if the test statistic T is greater than the critical value
     of chi-square with 9(nbin-1) degrees of freedom when the type I error is
     chosen as 0.001."

    Note: E_i uses c_i counted over the ENTIRE S (step 1), while each S_d has
    floor(L/10) samples; when L is not a multiple of 10 the two totals differ
    by (L mod 10)/10 -- that is what the text says, and it is kept.
    """
    L = int(S.size)
    values, counts = _symbol_counts(S, bits_per_symbol, alphabet)
    k = int(values.size)
    res = {"L": L, "k": k}
    if L < 1 or k == 0:
        res.update(_chi_square_decision(float("nan"), 0, variant))
        res.update({"nbin": 0, "exact_boundary": False, "merged_last_two": False,
                    "failed_if_df_zero_degenerate": False})
        return res

    # Steps 1-3.  e_i = c_i/10; weight c_i; sum e_i >= 5 <=> sum c_i >= 50.
    # "List[i] ... the ith smallest e_i": stable sort, ties by ascending value (R2).
    order = np.argsort(counts, kind="stable")
    bins, bin_w, exact_boundary, merged = _greedy_bins(order, counts, MIN_EXPECTED * GOF_PARTS)
    nbin = len(bins)
    # Step 4.
    E = np.array([bw / float(GOF_PARTS) for bw in bin_w], dtype=float)

    # Test step 1.  Ten subsets of floor(L/10); the remainder is not used.
    q = L // GOF_PARTS
    idx_of_value = np.full(int(values.max()) + 1, -1, dtype=np.int64)
    idx_of_value[values] = np.arange(k)
    bin_of_value = np.empty(k, dtype=np.int64)
    for b, members in enumerate(bins):
        bin_of_value[members] = b
    bin_seq = bin_of_value[idx_of_value[S[: GOF_PARTS * q]]].reshape(GOF_PARTS, q)
    # Test steps 2-3.
    o = np.stack([np.bincount(bin_seq[d], minlength=nbin) for d in range(GOF_PARTS)])
    T = float(np.sum((o - E[None, :]) ** 2 / E[None, :]))
    df = BINARY_GOF_DF * (nbin - 1)        # 9(nbin - 1)
    res.update(_chi_square_decision(T, df, variant))
    # R3: the alternative reading of df = 0.
    degenerate_fail = bool(df == 0 and T > 0.0)
    res["failed_if_df_zero_degenerate"] = degenerate_fail
    if df == 0 and gof_df_zero == "degenerate":
        res["failed"] = degenerate_fail
    elif gof_df_zero not in ("not_applied", "degenerate"):
        raise ValueError("gof_df_zero must be 'not_applied' or 'degenerate'")
    res.update({"nbin": nbin, "subset_length": int(q), "exact_boundary": exact_boundary,
                "merged_last_two": merged})
    if keep_bins and k <= 4096:
        res["bins"] = [{"values": [int(values[m]) for m in members], "E": float(E[b]),
                        "o": [int(x) for x in o[:, b]]} for b, members in enumerate(bins)]
    return res


# ==========================================================================
# 5.2.3  Testing Independence for Binary Data  (PDF p. 45-46)
# ==========================================================================

def binary_tuple_length_m(n0: int, n1: int, L: int) -> dict:
    """
    "1. Let p0 and p1 be the proportion of zeroes and ones in S, respectively,
        i.e., p0 = (# 0's in S)/L, and p1 = (# 1's in S)/L.
     2. Find the maximum integer m such that min(p0, p1)^m floor(L/m) >= 5.  If
        m is greater than 11, set m = 11.  If m is 1, the test fails.  For
        example, for p0 = 0.14, p1 = 0.86, and L = 1000, m = 2."

    Evaluated exactly: min(p)^m floor(L/m) >= 5  <=>  c_min^m floor(L/m) >= 5 L^m
    (R4).  The left side is non-increasing in m, so the maximum is the last m
    in 1, 2, 3, ... that satisfies it.  m = 0 records that no m >= 1 does.
    """
    c_min = min(int(n0), int(n1))
    m = 0
    while True:
        m_try = m + 1
        if c_min ** m_try * (L // m_try) >= MIN_EXPECTED * L ** m_try:
            m = m_try
        else:
            break
        if m_try > BINARY_M_CAP + 1:            # no need to look further than the cap
            break
    m_uncapped = m
    if m > BINARY_M_CAP:
        m = BINARY_M_CAP
    return {"m": m, "m_uncapped_floor": m_uncapped,
            "m_found": m_uncapped >= 1}


def independence_binary(S: np.ndarray, *, variant: str = "literal") -> dict:
    """
    "The test is applied if m >= 2.
     1. Initialize T to 0.
     2. Partition S into non-overlapping m-bit blocks, denoted as
        B = (B1, ..., B_floor(L/m)).  If L is not a multiple of m, discard the
        remaining bits.
     3. For each possible m-bit tuple (a1, a2, ..., am)
        a. Let o be the number of times that the pattern (a1, a2, ..., am)
           occurs in the input B.
        b. Let w be the number of ones in (a1, a2, ..., am).
        c. Let e = p1^w (p0)^(m-w) floor(L/m).
        d. T = T + (o-e)^2 / e.
     The test fails if the test statistic T is greater than the critical value
     of chi-square with 2^m - 2 degrees of freedom, when the type I error is
     chosen as 0.001."
    """
    L = int(S.size)
    n1 = int(np.count_nonzero(S))
    n0 = L - n1
    res = {"L": L, "k": int((n0 > 0) + (n1 > 0)), "n0": n0, "n1": n1,
           "p0": (n0 / L) if L else float("nan"), "p1": (n1 / L) if L else float("nan")}
    if L == 0:
        res.update({"m": 0, "m_found": False})
        res.update(_chi_square_decision(float("nan"), 0, variant))
        res["failed"] = True
        return res
    res.update(binary_tuple_length_m(n0, n1, L))
    m = res["m"]
    if m < 2:
        # "If m is 1, the test fails."  (m = 0: no m exists at all, R4.)
        res.update(_chi_square_decision(float("nan"), (1 << m) - 2 if m else 0, variant))
        res["failed"] = True
        res["failed_by_rule"] = "5.2.3 step 2: m is 1 (or no m satisfies the inequality)"
        return res
    p0, p1 = res["p0"], res["p1"]
    nblocks = L // m
    # Step 2.  Non-overlapping m-bit blocks; the pattern is read as an integer
    # (first bit most significant -- the sum over all tuples does not depend on it).
    blocks = S[: nblocks * m].reshape(nblocks, m)
    weights = (1 << np.arange(m - 1, -1, -1)).astype(np.int64)
    pattern = blocks @ weights
    # Step 3.
    o = np.bincount(pattern, minlength=1 << m).astype(float)
    tuples = np.arange(1 << m)
    w_ones = np.array([bin(t).count("1") for t in range(1 << m)], dtype=np.int64)
    e = (p1 ** w_ones) * (p0 ** (m - w_ones)) * nblocks
    T = float(np.sum((o - e) ** 2 / e))
    df = (1 << m) - 2
    res.update(_chi_square_decision(T, df, variant))
    res.update({"nblocks": int(nblocks), "tuples": int(tuples.size)})
    return res


# ==========================================================================
# 5.2.4  Testing Goodness-of-fit for Binary Data  (PDF p. 46-47)
# ==========================================================================

def goodness_of_fit_binary(S: np.ndarray, *, variant: str = "literal") -> dict:
    """
    "1. Let p be the proportion of ones in the entire sequence S, i.e., p =
        (the number of ones in S)/L.
     2. Partition S into ten non-overlapping subsets of length floor(L/10),
        where S_d = (s_{d floor(L/10)+1}, ..., s_{(d+1) floor(L/10)}) for
        d = 0, ..., 9.  If L is not a multiple of 10, the remaining bits are
        discarded.
     3. Initialize T to 0.
     4. Let the expected number of zeros and ones in each sub-sequence S_d be
        e0 = (1-p) floor(L/10),  e1 = p floor(L/10), respectively.
     5. For d = 0 to 9
        a. Let o0 and o1 be the number of zeros and ones in S_d, respectively.
        b. T = T + (o0-e0)^2/e0 + (o1-e1)^2/e1.
     T is a chi-square random variable with nine degrees of freedom.  The test
     fails if T is larger than the critical value at 0.001, which is 27.887."

    R5: variant='literal' compares with 27.887 as printed; variant='pvalue'
    with the p-value (equivalently the computed quantile 27.877...).  Both
    verdicts are always returned.
    """
    L = int(S.size)
    n1 = int(np.count_nonzero(S))
    res = {"L": L, "n1": n1}
    if L == 0:
        res.update({"p": float("nan"), "e0": float("nan"), "e1": float("nan")})
        res.update(_chi_square_decision(float("nan"), BINARY_GOF_DF, variant))
        res["fail_by_printed_critical_value"] = False
        return res
    p = n1 / L
    q = L // GOF_PARTS
    e0 = (1.0 - p) * q
    e1 = p * q
    res.update({"p": p, "subset_length": int(q), "e0": e0, "e1": e1})
    if e0 == 0.0 or e1 == 0.0:
        # R6: every term is (0 - 0)^2 / 0.  The text gives no value.
        res.update(_chi_square_decision(float("nan"), BINARY_GOF_DF, variant))
        res["fail_by_printed_critical_value"] = False
        res["not_applied_reason"] = "5.2.4: p is 0 or 1, so e0 or e1 is 0 and (o-e)^2/e is 0/0"
        return res
    subsets = S[: GOF_PARTS * q].reshape(GOF_PARTS, q)
    o1 = subsets.sum(axis=1).astype(float)
    o0 = q - o1
    T = float(np.sum((o0 - e0) ** 2 / e0 + (o1 - e1) ** 2 / e1))
    res.update(_chi_square_decision(T, BINARY_GOF_DF, variant))
    res["fail_by_printed_critical_value"] = bool(T > BINARY_GOF_CRITICAL_PRINTED)
    res["printed_critical_value"] = BINARY_GOF_CRITICAL_PRINTED
    if variant == "literal":
        res["failed"] = res["fail_by_printed_critical_value"]
    return res


# ==========================================================================
# 5.2.5  Length of the Longest Repeated Substring Test  (PDF p. 47)
# ==========================================================================

def _suffix_array(S: np.ndarray):
    """Suffix array by prefix doubling (numpy).  Returns (sa, rank): sa[r] is the
    start of the r-th smallest suffix, rank its inverse.  A suffix that runs
    out of symbols sorts before any longer suffix with the same prefix (its
    missing second key is -1), as a proper prefix should."""
    n = int(S.size)
    rank = S.astype(np.int64, copy=True)
    h = 1
    while True:
        second = np.full(n, -1, dtype=np.int64)
        second[: n - h] = rank[h:]
        order = np.lexsort((second, rank))             # by rank, then by second
        r_o, s_o = rank[order], second[order]
        changed = np.empty(n, dtype=bool)
        changed[0] = False
        changed[1:] = (r_o[1:] != r_o[:-1]) | (s_o[1:] != s_o[:-1])
        new_rank = np.empty(n, dtype=np.int64)
        new_rank[order] = np.cumsum(changed)
        rank = new_rank
        if rank[order[-1]] == n - 1:                   # ranks dense => all distinct
            return order, rank
        h *= 2


def _lcp_kasai(S_seq, sa, rank):
    """Kasai's algorithm: lcp[r] = length of the longest common prefix of the
    suffixes ranked r-1 and r.  The longest repeated substring is max(lcp)."""
    n = len(S_seq)
    lcp = [0] * n
    h = 0
    for i in range(n):
        r = rank[i]
        if r == 0:
            h = 0
            continue
        j = sa[r - 1]
        while i + h < n and j + h < n and S_seq[i + h] == S_seq[j + h]:
            h += 1
        lcp[r] = h
        if h:
            h -= 1
    return lcp


def longest_repeated_substring_suffix(S: np.ndarray) -> int:
    """W = max over all pairs of distinct suffixes of their common prefix length
    = max over adjacent suffixes in sorted order (R8)."""
    n = int(S.size)
    if n < 2:
        return 0
    sa, rank = _suffix_array(S)
    if S.max() < 256 and S.min() >= 0:
        seq = S.astype(np.uint8).tobytes()          # fast indexing in the Python loop
    else:
        seq = S.tolist()
    lcp = _lcp_kasai(seq, sa.tolist(), rank.tolist())
    return int(max(lcp))


def longest_repeated_substring_direct(S) -> int:
    """The literal reading of step 3: "find the largest W such that, for at
    least one i != j, si = sj, si+1 = sj+1, ..., si+W-1 = sj+W-1".  A repeat of
    length W implies one of length W-1, so W is the last length at which some
    substring occurs at two positions.  O(L W^2): for tiny inputs and checks."""
    seq = [int(x) for x in S]
    n = len(seq)
    W = 0
    while W + 1 <= n - 1:
        seen = set()
        found = False
        for i in range(n - W):
            t = tuple(seq[i:i + W + 1])
            if t in seen:
                found = True
                break
            seen.add(t)
        if not found:
            break
        W += 1
    return W


def lrs_length_test(S: np.ndarray, bits_per_symbol: int, *, method: str = "auto",
                    direct_budget: int = 2_000_000) -> dict:
    """
    "Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},
     1. Find the proportion p_i of each possible input value x_i in S, i.e.,
        p_i = (number of x_i in S)/L.
     2. Calculate the collision probability as p_col = sum_{i=1}^{k} p_i^2.
     3. Find the length of the longest repeated substring W, i.e., find the
        largest W such that, for at least one i != j, si = sj, si+1 = sj+1, ...,
        si+W-1 = sj+W-1.
     4. The number of overlapping subsequences of length W in S is L-W+1, and
        the number of pairs of overlapping subsequences is C(L-W+1, 2).
     5. Let X be a binomially distributed random variable with parameters
        N = C(L-W+1, 2) and a probability of success p_col^W.  Calculate the
        probability that X is greater than or equal to 1, i.e.,
        Pr(X >= 1) = 1 - Pr(X = 0) = 1 - (1 - p_col^W)^N.
     The test fails if Pr(X >= 1) is less than 0.001."

    p_col is formed exactly as sum(c_i^2) / L^2 (one rounding).  Pr(X >= 1) is
    evaluated as -expm1(N * log1p(-p_col^W)); when p_col^W underflows the
    first-order term N p_col^W is returned (it is then far below 0.001 either
    way).  Absent symbol values have p_i = 0 and contribute nothing, so the
    alphabet question (R1) does not arise here.
    """
    L = int(S.size)
    res = {"L": L}
    if L == 0:
        res.update({"P_col": float("nan"), "W": 0, "N": 0, "Pr(X >= 1)": float("nan"),
                    "passed": False, "applied": False})
        return res
    counts = np.bincount(S)
    counts = counts[counts > 0]
    k = int(counts.size)
    sum_c2 = int(np.sum(counts.astype(object) ** 2)) if L > 3_000_000_000 else int(np.sum(counts * counts))
    p_col = sum_c2 / (L * L)                        # steps 1-2, exactly then rounded once

    # Step 3.
    if method not in ("auto", "suffix", "direct"):
        raise ValueError("method must be 'auto', 'suffix' or 'direct'")
    W_suffix = W_direct = None
    if method in ("auto", "suffix"):
        W_suffix = longest_repeated_substring_suffix(S)
    if method == "direct" or (method == "auto" and L * (int(W_suffix) + 2) <= direct_budget):
        W_direct = longest_repeated_substring_direct(S)
    if W_suffix is not None and W_direct is not None and W_suffix != W_direct:
        raise AssertionError(f"suffix-array W={W_suffix} and direct W={W_direct} disagree")
    W = int(W_suffix if W_suffix is not None else W_direct)

    # Steps 4-5.
    n_sub = L - W + 1
    N = n_sub * (n_sub - 1) // 2
    if W == 0:
        pW = 1.0                                     # p_col^0 = 1: Pr = 1 - 0^N
    else:
        pW = p_col ** W
    log_pW = W * math.log(p_col) if p_col > 0 else float("-inf")
    if pW > 0.0:
        pr = -math.expm1(N * math.log1p(-pW)) if pW < 1.0 else 1.0
        underflow = False
    else:
        pr = math.exp(math.log(N) + log_pW) if N > 0 else 0.0   # first-order term
        underflow = True
    res.update({"k": k, "P_col": p_col, "W": W, "N": int(N), "p_col^W": pW,
                "log(p_col^W)": log_pW, "p_col^W underflowed": underflow,
                "Pr(X >= 1)": pr, "applied": True,
                "passed": not (pr < ALPHA),
                "W_suffix": W_suffix, "W_direct": W_direct})
    return res


# ==========================================================================
# estimate(): the whole of 5.2 on one sequence
# ==========================================================================

def estimate(symbols, bits_per_symbol, **options) -> dict:
    """
    Run the Section 5.2 tests on `symbols` (ints in [0, 2**bits_per_symbol)).

    Options (keyword only)
    ----------------------
    track        : 'literal' (default) -> test the symbols as given
                   'bitstring'         -> expand to bits (Section 3.1.3), 1-bit symbols
    bit_order    : 'msb' (default) | 'lsb'    -- bit order within a symbol (bitstring)
    bitstring_limit : None (default) | int   -- R9: keep only the first N bits
    binary       : None (default: 1-bit data <=> binary, R7) | True | False
    alphabet     : 'observed' (default) | 'declared'          -- R1
    variant      : 'literal' (default) | 'pvalue'             -- R5 / R10
    gof_df_zero  : 'not_applied' (default) | 'degenerate'     -- R3
    method       : 'auto' (default) | 'suffix' | 'direct'     -- how W is found
    validate     : True (default) -- check the symbol range

    Returns
    -------
    dict.  'min_entropy' is float('nan'): Section 5 awards no estimate.
    Nested results: 'chi_square_independence', 'chi_square_goodness_of_fit',
    'lrs_length_test', each carrying its intermediates ('T', 'df', 'P-value',
    'critical_value', 'applied', 'failed', ...; 'P_col', 'W', 'N',
    'Pr(X >= 1)', 'passed').  Verdicts: 'chi_square_tests_failed' (either
    applied chi-square test failed) and 'lrs_length_test_passed'.
    Flat keys named exactly as the C++ verbose labels are also present, e.g.
    'Chi square independence: T', 'Chi square tests' ('Passed'/'Failed'),
    'Literal Longest Repeated Substring results: P_col',
    'Length of longest repeated substring test' ('Passed'/'Failed').
    """
    opts = dict(options)
    track = opts.pop("track", "literal")
    bit_order = opts.pop("bit_order", "msb")
    bitstring_limit = opts.pop("bitstring_limit", None)
    binary = opts.pop("binary", None)
    alphabet = opts.pop("alphabet", "observed")
    variant = opts.pop("variant", "literal")
    gof_df_zero = opts.pop("gof_df_zero", "not_applied")
    method = opts.pop("method", "auto")
    validate = bool(opts.pop("validate", True))
    if opts:
        raise TypeError(f"estimate(): unknown option(s) {sorted(opts)}")
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}")
    bps = int(bits_per_symbol)
    S = _as_symbol_array(symbols, bps, validate=validate)
    if track == "bitstring":
        S = to_bitstring(S, bps, bit_order)
        if bitstring_limit is not None:
            S = S[: int(bitstring_limit)]
        width = 1
        label_prefix = "Bitstring"
    elif track == "literal":
        width = bps
        label_prefix = "Literal"
    else:
        raise ValueError("track must be 'literal' or 'bitstring'")
    if binary is None:
        binary = (width == 1)
    binary = bool(binary)
    L = int(S.size)

    if binary:
        indep = independence_binary(S, variant=variant)
        gof = goodness_of_fit_binary(S, variant=variant)
    else:
        indep = independence_non_binary(S, width, alphabet=alphabet, variant=variant)
        gof = goodness_of_fit_non_binary(S, width, alphabet=alphabet, variant=variant,
                                         gof_df_zero=gof_df_zero)
    lrs = lrs_length_test(S, width, method=method)

    chi_failed = bool(indep["failed"] or gof["failed"])
    res = {
        "min_entropy": float("nan"),
        "L": L, "bits_per_symbol": bps, "track": track, "binary": binary,
        "alphabet": alphabet, "variant": variant, "gof_df_zero": gof_df_zero,
        "bit_order": bit_order if track == "bitstring" else None,
        "bitstring_limit": bitstring_limit if track == "bitstring" else None,
        "chi_square_independence": indep,
        "chi_square_goodness_of_fit": gof,
        "chi_square_tests_failed": chi_failed,
        "lrs_length_test": lrs,
        "lrs_length_test_passed": bool(lrs["passed"]),
        "section_5_2_passed": bool((not chi_failed) and lrs["passed"]),
        # ---- flat keys, named as the C++ verbose labels ----
        "Chi square independence: T": indep["T"],
        "Chi square independence: df": indep["df"],
        "Chi square independence: P-value": indep["P-value"],
        "Chi square goodness of fit: T": gof["T"],
        "Chi square goodness of fit: df": gof["df"],
        "Chi square goodness of fit: P-value": gof["P-value"],
        "Chi square tests": "Failed" if chi_failed else "Passed",
        f"{label_prefix} Longest Repeated Substring results: P_col": lrs["P_col"],
        f"{label_prefix} Longest Repeated Substring results: W": lrs["W"],
        f"{label_prefix} Longest Repeated Substring results: Pr(X >= 1)": lrs["Pr(X >= 1)"],
        "Length of longest repeated substring test": "Passed" if lrs["passed"] else "Failed",
    }
    return res


# --------------------------------------------------------------------------
# __main__:  python chisquare.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
#                [--variant literal|pvalue] [--alphabet observed|declared]
#                [--gof-df-zero not_applied|degenerate] [--method auto|suffix|direct]
#                [--binary|--non-binary] [--lsb-first] [--bitstring-limit N]
# --------------------------------------------------------------------------

USAGE = ("usage: chisquare.py <rawfile> <bits_per_symbol> [--literal|--bitstring]\n"
         "         [--variant literal|pvalue] [--alphabet observed|declared]\n"
         "         [--gof-df-zero not_applied|degenerate] [--method auto|suffix|direct]\n"
         "         [--binary|--non-binary] [--lsb-first] [--bitstring-limit N]\n")


def _to_jsonable(x):
    if isinstance(x, dict):
        return {str(k): _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return _to_jsonable(x.tolist())
    return x


def _main(argv) -> int:
    args = list(argv)
    kw = {}
    track = "literal"
    positional = []
    i = 0
    try:
        while i < len(args):
            a = args[i]
            if a == "--literal":
                track = "literal"
            elif a == "--bitstring":
                track = "bitstring"
            elif a == "--variant":
                i += 1; kw["variant"] = args[i]
            elif a == "--alphabet":
                i += 1; kw["alphabet"] = args[i]
            elif a == "--gof-df-zero":
                i += 1; kw["gof_df_zero"] = args[i]
            elif a == "--method":
                i += 1; kw["method"] = args[i]
            elif a == "--binary":
                kw["binary"] = True
            elif a == "--non-binary":
                kw["binary"] = False
            elif a == "--lsb-first":
                kw["bit_order"] = "lsb"
            elif a == "--bitstring-limit":
                i += 1; kw["bitstring_limit"] = int(args[i])
            elif a.startswith("--"):
                sys.stderr.write(f"unknown option {a}\n" + USAGE)
                return 2
            else:
                positional.append(a)
            i += 1
    except IndexError:
        sys.stderr.write("option is missing its value\n" + USAGE)
        return 2
    if len(positional) != 2:
        sys.stderr.write(USAGE)
        return 2
    path, bps = positional[0], int(positional[1])
    if not 1 <= bps <= 8:
        sys.stderr.write("bits_per_symbol must be in 1..8 for a one-symbol-per-byte raw file\n")
        return 2
    with open(path, "rb") as fh:
        raw = np.frombuffer(fh.read(), dtype=np.uint8).astype(np.int64)
    symbols = raw & ((1 << bps) - 1)                  # one symbol per byte, low bps bits
    res = estimate(symbols, bps, track=track, **kw)
    res["rawfile"] = path
    sys.stdout.write(json.dumps(_to_jsonable(res), indent=1) + "\n")   # NaN emitted as NaN
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
