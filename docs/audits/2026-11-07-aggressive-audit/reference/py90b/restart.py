"""
py90b.restart -- SP 800-90B sections 3.1.4.1, 3.1.4.2 and 3.1.4.3: the Restart
Tests (restart matrix, row/column datasets, validation testing, and the
"Sanity Check - Most Common Value in the Rows and Columns").

INDEPENDENT reference implementation, written FROM THE STANDARD'S TEXT ONLY
(NIST SP 800-90B, January 2018, as extracted to reference/sp800-90b.pages.txt).
No file under cpp/ was opened while writing this, and no file under
logs/analysis/ was read.  There is no verbose-label capture for ea_restart in
reference/ (only ea_non_iid and ea_iid were captured), so the key names below
are (a) the standard's own symbols (X_R, X_C, X_max, p, alpha, H_r, H_c, H_I)
and (b) the fork's JSON report field names as listed in the repository's
NOTICE file (restartHI, restartAlpha, restartXmax, restartXcutoff,
restartXcutoffPrintedBinomial, restartCutoffMethod, passedRestartSanityCheck),
so a differential driver can match either.

The fork DELIBERATELY diverges from this section (FORK-DIVERGENCE-AND-TRUST.md
section B, entry C23: it decides on the exact multinomial maximum, not step
5's printed single-binomial tail).  This module implements THE TEXT AS
PRINTED; the C23 divergence is the fork's documented choice and is not a
finding against either side.  Where the fork and this module differ, the
driver should expect the difference to be exactly the C23 one and nothing
else.

======================================================================
Spec text relied on (quoted; PDF page numbers are of the NIST PDF)
======================================================================

SP 800-90B section 3.1.1 item 3 (PDF p. 19):

    "For the restart tests (see Section 3.1.4), the entropy source must be
     restarted 1000 times; for each restart, 1000 consecutive samples shall
     be collected directly from the noise source. [...] This data is stored
     in a 1000x1000 restart matrix M, where M[i][j] represents the jth
     sample from the ith restart."

SP 800-90B section 3.1.4.1 (PDF p. 21):

    "To construct restart data, the entropy source shall be restarted
     r = 1000 times; for each restart, c = 1000 consecutive samples shall be
     collected directly from the noise source. [...] The output samples are
     stored in an r by c matrix M, where M[i][j] represents the jth sample
     from the ith restart.
     Two datasets are constructed using the matrix M:
       - The row dataset is constructed by concatenating the rows of the
         matrix M, i.e., the row dataset is
         M[1][1] ||...|| M[1][c] || M[2][1] ||...|| M[2][c] || ... || M[r][1] ||...|| M[r][c].
       - The column dataset is constructed by concatenating the columns of
         the matrix M, i.e., the column dataset is
         M[1][1] ||...|| M[r][1] || M[1][2] ||...|| M[r][2] || ... || M[1][c] ||...|| M[r][c]."

SP 800-90B section 3.1.4.2 (PDF p. 21):

    "First, the sanity check described in Section 3.1.4.3 is performed on
     the matrix M. If the test fails, the validation fails and no entropy
     estimate is awarded.
     If the noise source does not fail the sanity check, then the entropy
     estimation methods described in Section 6.1 (for the IID track) or
     Section 6.2 (for the non-IID track) are performed on the row and the
     column datasets, based on the track of the entropy source. Let Hr and
     Hc be the resulting entropy estimates of the row and the column
     datasets, respectively. [...] If the minimum of Hr and Hc is less than
     half of HI, the validation fails, and no entropy estimate is awarded.
     Otherwise, the entropy assessment of the noise source is taken as the
     minimum of the row, the column and the initial estimates, i.e.,
     min(Hr, Hc, HI)."

SP 800-90B section 3.1.4.3 (PDF p. 21-22):

    "This sanity check is based on a binomial test, where there are two
     possible outcomes for each trial: the most frequent value or any other
     value is observed. [...] The probability of type I error, denoted
     alpha, is set at 0.01 over the entire sanity check, where each of the
     2000 binomial experiments [footnote 3] has type I error probability of
     0.000 005.
     Only the experiment yielding the highest count is tested. If that
     experiment passes the test, then the other 1999 experiments will pass
     as well. [...] Therefore, it is sufficient to test the experiment with
     the highest count.
     Given the 1000 by 1000 restart matrix and the initial entropy estimate
     HI, the test is performed as follows:
       1. Let p = 2^-HI . Let alpha be 0.000 005.
       2. For each row (1 <= i <= 1000) of the matrix, count the number of
          occurrences of each sample present in the row. Set XRi to the
          highest count value for row i. Let XR be the maximum count value
          for all the rows, i.e., XR = max (XR1,...,XR1000).
       3. For each column (1 <= i <= 1000) of the matrix, count the number
          of occurrences of each sample present in the column. Set XCi to
          the highest count value for column i. Let XC be the maximum count
          value for all the columns, i.e., XC = max (XC1,...,XC1000).
       4. Let Xmax = max(XC, XR).
       5. Calculate P(X >= Xmax) = sum_{j=Xmax}^{1000} C(1000, j) p^j (1-p)^(1000-j).
          If Pr(X >= Xmax) < alpha, the test fails. Otherwise, the test
          passes."
    Footnote 3: "The experiments done for each row or column are considered
    to be independent."

SP 800-90B section 6.1 (PDF p. 48):  "For sources with IID outputs, the
    min-entropy estimation is determined using the most common value
    estimate described in Section 6.3.1."

SP 800-90B section 6.2 (PDF p. 49):  "For non-IID data, the following
    estimators shall be calculated [...] and the minimum of all the estimates
    is taken as the entropy assessment [...]: [MCV, Collision, Markov,
    Compression, t-Tuple, LRS, MultiMCW, Lag, MultiMMC, LZ78Y].  The
    Collision, Markov and Compression estimates are only applied to binary
    inputs."

SP 800-90B section 6.3.1 (PDF p. 49), used here for the IID track only:
    "1. Find the proportion of the most common value p-hat in the dataset,
        i.e., p-hat = max_i #{x_i in S}/L.
     2. Calculate an upper bound on the probability of the most common value
        p_u as p_u = min(1, p-hat + 2.576 sqrt(p-hat(1-p-hat)/(L-1))), where
        2.576 corresponds to the Z_(1-0.005) value.
     3. The estimated min-entropy is -log2(p_u)."

======================================================================
How literally this module reads the text, and where it had to choose
======================================================================

alpha.  Step 1 prints "0.000 005".  The narrative derives it as 0.01 over
    "the 2000 binomial experiments" (1000 rows + 1000 columns), i.e.
    0.01 / (2 * 1000).  Both are exposed (ALPHA_PRINTED, ALPHA_DERIVED); they
    are the same binary64 and the same exact decimal (1/200000).  The default
    is the printed literal.  alpha is compared as the DECIMAL it prints as
    (Fraction("0.000005") == 1/200000), not as the nearest binary64, because
    the text gives a decimal literal.

p.  p = 2^-HI is computed in binary64 (2.0 ** -H_I); the tail sum then uses
    THAT value exactly (Fraction(p) is the exact binary rational), so the
    printed sum is evaluated with no further rounding.  A float64 "naive" sum
    is also reported so a driver can see the rounding difference.

The sum in step 5.  Evaluated exactly in rational arithmetic, term by term,
    exactly as printed: sum_{j=Xmax}^{n} C(n,j) p^j (1-p)^(n-j).  The only
    algebra applied is factoring out the common denominator (every term is a
    multiple of 1/d^n when p = a/d), which changes nothing.  The result is
    returned as a float AND as a 40-significant-digit decimal of the exact
    value ('P(X >= X_max) exact (40 digits)'), so a driver can compare past
    binary64 precision.  (The exact rational itself has a ~53,000-bit
    denominator and is not printed; binomial_upper_tail() returns it.)

"Only the experiment yielding the highest count is tested."  Implemented as
    written: one tail, at Xmax = max(XC, XR), with n = 1000 trials.  This
    reasoning is valid only because every row and every column has the same
    number of trials (r = c = 1000).  For a NON-SQUARE matrix (which this
    module accepts for probes, flagged spec_shape=False) the text gives no
    rule; the generalisation used is to test XR against n = c trials and XC
    against n = r trials and fail if EITHER tail is below alpha.  For a
    square matrix that reduces exactly to the printed single test (the tail
    is non-increasing in X, so the smaller tail is the one at Xmax).

Cutoff.  The standard never defines a "cutoff"; it tests the tail at Xmax.
    Because the tail is non-increasing in X, the verdict is equivalent to a
    threshold on Xmax, and two conventions for naming that threshold exist:
      X_cutoff_fail  = smallest X with P(X >= X) < alpha  (Xmax >= it fails)
      X_cutoff_pass  = X_cutoff_fail - 1                   (Xmax <= it passes)
    Both are exposed.  'restartXcutoff' / 'restartXcutoffPrintedBinomial' are
    set to X_cutoff_pass, by this inference ONLY: FORK-DIVERGENCE-AND-TRUST.md
    entry C23 states that at H_I = 0.696 (width 1) "both cutoffs give 684",
    and the printed formula at that point gives X_cutoff_pass = 684,
    X_cutoff_fail = 685 (see tests/test_restart.py).  No C++ was read.  A
    driver should confirm the convention on one point before relying on it.

Row/column datasets.  Built exactly as the concatenations in 3.1.4.1:
    row dataset = M in row-major order; column dataset = M^T in row-major
    order.  A flat input of r*c symbols is interpreted as the matrix in
    row-major order (restart 1's c samples first).  The standard defines the
    matrix, not a file layout; that is this module's assumption.

Sanity check first, estimates second.  3.1.4.2 performs the estimators only
    "if the noise source does not fail the sanity check".  So by default H_r
    and H_c are NaN when the sanity check fails.  always_estimate=True
    computes them anyway (for drivers that want to compare them).

The HI/2 rule.  "If the minimum of Hr and Hc is less than half of HI, the
    validation fails" -- strict '<'; equality passes.  Otherwise
    H = min(Hr, Hc, HI).

Which estimators give Hr and Hc.  estimation_track='iid' uses the in-module
    MCV above (section 6.1).  estimation_track='non_iid' uses the minimum of
    the sibling py90b modules that can be imported (section 6.2), skipping
    Collision/Markov/Compression for non-binary input as 6.2 says, and
    RECORDS which estimators were used and which were missing
    ('estimators_used', 'estimators_missing', 'estimators_complete').  A
    caller may pass estimator=callable(symbols, bps) -> float instead.

Bitstring.  3.1.4 says nothing about a bitstring track for the matrix; the
    row/column estimates are literally the section 6.x estimators on the
    SAMPLE datasets, and the sanity check counts SAMPLES ("count the number
    of occurrences of each sample").  That is the literal reading and the
    default (track='literal').  track='bitstring' is provided because the
    API contract asks for it and 3.1.3 does define a bitstring estimate for
    the sequential dataset: each n-bit sample is expanded MSB-first in place
    in its row, so the matrix becomes r x (c*n) one-bit symbols
    (bitstring_mode='full'); bitstring_mode='truncate_rows' keeps only the
    first c bits of each row so the matrix stays r x c (the 3.1.3 "bits after
    the first 1 000 000 bits may be ignored" idea applied per restart).  In
    bitstring mode H_I must be per BIT for the sanity check; H_I given per
    sample is divided by n (H_I_scale='symbol', the default).  That division
    is this module's convention, not the standard's.

Degenerate inputs.  H_I <= 0, NaN or infinite is refused (p would be >= 1 or
    undefined; the text assumes an entropy estimate).  H_I > bits per matrix
    symbol is accepted and flagged (p < 1/k is unusual but computable).

======================================================================
API (contract for the differential driver)
======================================================================

    estimate(symbols, bits_per_symbol, **options) -> dict
        symbols: flat sequence / np.ndarray / bytes of ints in
                 [0, 2**bits_per_symbol), length r*c (default 1000*1000)
        options: H_I (float, or '<v>/symbol' | '<v>/bit'), H_I_scale, r, c,
                 alpha, estimation_track ('non_iid'|'iid'), estimator,
                 track ('literal'|'bitstring'), bit_order, bitstring_mode,
                 always_estimate, include_per_line, run_estimators
        returns {'min_entropy': float, 'X_R', 'X_C', 'X_max', 'p', 'alpha',
                 'P(X >= X_max)', 'H_r', 'H_c', 'H_I', 'restartHI',
                 'restartAlpha', 'restartXmax', 'restartXcutoff', ...}
        float('nan') wherever the spec gives no value (validation failed,
        sanity check failed, H_I not supplied).

    sanity_cutoff(p, alpha, n) -> int      (X_cutoff_fail, see above)
    check(matrix, H_I, bps, **options) -> dict   (the full 3.1.4.2 procedure)

    python restart.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                      [--H_I <v>[/symbol|/bit]] [--iid|--non-iid]
                      [--shape RxC] [--alpha A] [--no-estimators]
                      [--always-estimate] [--per-line] [--lsb-first]
                      [--bitstring-mode full|truncate_rows]
        rawfile: one symbol per byte, low bits_per_symbol bits are the symbol.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from fractions import Fraction

import numpy as np

# --------------------------------------------------------------------------
# Constants, each with the sentence it comes from
# --------------------------------------------------------------------------

R_SPEC = 1000            # 3.1.4.1: "restarted r = 1000 times"
C_SPEC = 1000            # 3.1.4.1: "c = 1000 consecutive samples"
N_TRIALS_SPEC = 1000     # 3.1.4.3 step 5: the binomial has 1000 trials

ALPHA_OVERALL = "0.01"          # 3.1.4.3: "set at 0.01 over the entire sanity check"
N_EXPERIMENTS = 2 * 1000        # 3.1.4.3: "each of the 2000 binomial experiments"
ALPHA_PRINTED = 0.000005        # 3.1.4.3 step 1: "Let alpha be 0.000 005."
ALPHA_DERIVED = float(Fraction(ALPHA_OVERALL) / N_EXPERIMENTS)   # 0.01/2000

Z_MCV_PRINTED = 2.576           # 6.3.1 step 2: "2.576 corresponds to the Z_(1-0.005) value"

CUTOFF_METHOD = "printed-binomial (SP 800-90B 3.1.4.3 step 5, literal)"

# The section-6.2 battery, in the order the standard lists it, with the
# py90b module expected to implement each.  "binary_only" follows the last
# sentence of 6.2.
NON_IID_BATTERY = (
    # (label, module file stem, binary_only)
    ("Most Common Value", "mcv", False),
    ("Collision", "collision", True),
    ("Markov", "markov", True),
    ("Compression", "compression", True),
    ("t-Tuple", "ttuple", False),
    ("LRS", "lrs", False),
    ("MultiMCW Prediction", "multimcw", False),
    ("Lag Prediction", "lag", False),
    ("MultiMMC Prediction", "multimmc", False),
    ("LZ78Y Prediction", "lz78y", False),
)

HERE = pathlib.Path(__file__).resolve().parent


# --------------------------------------------------------------------------
# Input coercion
# --------------------------------------------------------------------------

def _dtype_for(bits_per_symbol: int):
    """Smallest unsigned numpy dtype that holds every symbol of this width."""
    if bits_per_symbol <= 8:
        return np.uint8
    if bits_per_symbol <= 16:
        return np.uint16
    if bits_per_symbol <= 32:
        return np.uint32
    if bits_per_symbol <= 64:
        return np.uint64
    raise ValueError("bits_per_symbol above 64 is not supported by this module")


def _validate_range(arr: np.ndarray, bits_per_symbol: int) -> None:
    if arr.size == 0:
        return
    lo = int(arr.min())
    hi = int(arr.max())
    if lo < 0 or hi >= (1 << bits_per_symbol):
        raise ValueError(
            f"symbols must lie in [0, 2**{bits_per_symbol}); observed min={lo} max={hi}"
        )


def as_matrix(symbols, bits_per_symbol: int, r: int | None = None, c: int | None = None) -> np.ndarray:
    """
    Return the restart matrix M as a 2-D unsigned array of shape (r, c).

    * A 2-D input is taken as M itself (M[i][j] = jth sample of restart i);
      r and c, if given, must match.
    * A flat input is the matrix in ROW-MAJOR order (restart 1's c samples,
      then restart 2's, ...).  With r and c absent, the spec shape
      1000 x 1000 is assumed and exactly 1 000 000 symbols are required.
    """
    bps = int(bits_per_symbol)
    if bps < 1:
        raise ValueError("bits_per_symbol must be >= 1")
    if isinstance(symbols, (bytes, bytearray, memoryview)):
        arr = np.frombuffer(symbols, dtype=np.uint8)
    else:
        arr = np.asarray(symbols)
    if arr.dtype == np.bool_:
        arr = arr.astype(np.uint8)
    if not np.issubdtype(arr.dtype, np.integer):
        raise ValueError(f"symbols must be integers, got dtype {arr.dtype}")

    if arr.ndim == 2:
        if (r is not None and arr.shape[0] != r) or (c is not None and arr.shape[1] != c):
            raise ValueError(f"matrix has shape {arr.shape}, but r={r}, c={c} were requested")
        M = arr
    elif arr.ndim == 1:
        if r is None and c is None:
            r, c = R_SPEC, C_SPEC
        elif r is None or c is None:
            raise ValueError("give both r and c, or neither")
        if arr.size != r * c:
            raise ValueError(
                f"restart data must hold exactly r*c = {r}*{c} = {r*c} symbols "
                f"(3.1.4.1); got {arr.size}"
            )
        M = arr.reshape(r, c)          # row-major: M[i][j] = jth sample of restart i
    else:
        raise ValueError("symbols must be a flat sequence or a 2-D matrix")

    if M.shape[0] < 1 or M.shape[1] < 1:
        raise ValueError("the restart matrix must have at least one row and one column")
    _validate_range(M, bps)
    return M.astype(_dtype_for(bps), copy=False)


def row_dataset(M: np.ndarray) -> np.ndarray:
    """3.1.4.1: M[1][1] ||...|| M[1][c] || M[2][1] ||...|| M[r][c]  (rows concatenated)."""
    return np.ascontiguousarray(M).reshape(-1)


def column_dataset(M: np.ndarray) -> np.ndarray:
    """3.1.4.1: M[1][1] ||...|| M[r][1] || M[1][2] ||...|| M[r][c]  (columns concatenated)."""
    return np.ascontiguousarray(M.T).reshape(-1)


def to_bit_matrix(M: np.ndarray, bits_per_symbol: int, bit_order: str = "msb") -> np.ndarray:
    """
    Expand every n-bit sample of M in place within its row, so an r x c
    matrix of n-bit samples becomes an r x (c*n) matrix of bits.
    bit_order='msb' (default): bit n-1 of each sample first; 'lsb': bit 0 first.
    """
    bps = int(bits_per_symbol)
    if bps == 1:
        return M.astype(np.uint8, copy=False)
    if bit_order == "msb":
        shifts = np.arange(bps - 1, -1, -1)
    elif bit_order == "lsb":
        shifts = np.arange(0, bps)
    else:
        raise ValueError("bit_order must be 'msb' or 'lsb'")
    shifts = shifts.astype(M.dtype)
    r, c = M.shape
    bits = (M[:, :, None] >> shifts[None, None, :]) & M.dtype.type(1)   # (r, c, n)
    return bits.reshape(r, c * bps).astype(np.uint8, copy=False)


# --------------------------------------------------------------------------
# Steps 2 and 3: the highest count in every row / column
# --------------------------------------------------------------------------

_BINCOUNT_MAX_ALPHABET = 1 << 12    # above this, the sort-based path is used


def _max_count_per_row_bincount(M: np.ndarray, k: int) -> np.ndarray:
    """Count every symbol in every row at once: cell (i, v) of an (r, k) table."""
    r, c = M.shape
    offsets = (np.arange(r, dtype=np.int64)[:, None] * k) + M.astype(np.int64, copy=False)
    table = np.bincount(offsets.reshape(-1), minlength=r * k).reshape(r, k)
    return table.max(axis=1).astype(np.int64)


def _max_count_per_row_sorted(M: np.ndarray) -> np.ndarray:
    """
    Sort each row; equal samples become runs; the longest run in a row is
    the highest count in that row.  Works for any alphabet size.
    """
    r, c = M.shape
    S = np.sort(M, axis=1)
    idx = np.arange(c, dtype=np.int64)
    starts_run = np.ones((r, c), dtype=bool)
    starts_run[:, 1:] = S[:, 1:] != S[:, :-1]
    run_start = np.maximum.accumulate(np.where(starts_run, idx[None, :], 0), axis=1)
    run_len = idx[None, :] - run_start + 1
    return run_len.max(axis=1).astype(np.int64)


def max_count_per_row(M: np.ndarray, bits_per_symbol: int, method: str = "auto") -> np.ndarray:
    """
    Step 2: "For each row of the matrix, count the number of occurrences of
    each sample present in the row. Set XRi to the highest count value for
    row i."  Returns the vector (XR_1, ..., XR_r).
    """
    k = 1 << int(bits_per_symbol)
    if method == "auto":
        method = "bincount" if k <= _BINCOUNT_MAX_ALPHABET else "sorted"
    if method == "bincount":
        return _max_count_per_row_bincount(M, k)
    if method == "sorted":
        return _max_count_per_row_sorted(M)
    if method == "python":
        # Plain Python, for cross-checking the vectorised paths in tests.
        from collections import Counter
        return np.array([max(Counter(row.tolist()).values()) for row in M], dtype=np.int64)
    raise ValueError("method must be 'auto', 'bincount', 'sorted' or 'python'")


def max_count_per_column(M: np.ndarray, bits_per_symbol: int, method: str = "auto") -> np.ndarray:
    """Step 3, the same for columns: (XC_1, ..., XC_c)."""
    return max_count_per_row(np.ascontiguousarray(M.T), bits_per_symbol, method)


# --------------------------------------------------------------------------
# Step 5: the printed binomial tail, exactly
# --------------------------------------------------------------------------

def _p_as_fraction(p) -> Fraction:
    """p as an exact rational.  A float is taken at its exact binary64 value."""
    if isinstance(p, Fraction):
        fp = p
    elif isinstance(p, (int, np.integer)):
        fp = Fraction(int(p))
    elif isinstance(p, (float, np.floating)):
        if not math.isfinite(float(p)):
            raise ValueError("p must be finite")
        fp = Fraction(float(p))
    else:
        fp = Fraction(p)
    if not (0 <= fp <= 1):
        raise ValueError(f"p must lie in [0, 1]; got {p}")
    return fp


def _alpha_as_fraction(alpha) -> Fraction:
    """alpha as the exact DECIMAL it prints as (the text gives a decimal literal)."""
    if isinstance(alpha, Fraction):
        fa = alpha
    elif isinstance(alpha, str):
        fa = Fraction(alpha)
    else:
        fa = Fraction(repr(float(alpha)))
    if not (0 < fa < 1):
        raise ValueError(f"alpha must lie in (0, 1); got {alpha}")
    return fa


def _term_numerators(n: int, a: int, b: int) -> list:
    """
    Integers N_j = C(n, j) a^j b^(n-j) for j = 0..n.  With p = a/d and
    1 - p = b/d (b = d - a), the printed term C(n,j) p^j (1-p)^(n-j) equals
    N_j / d^n, so these are the printed terms over their common denominator.
    Powers are built incrementally (a^j = a^(j-1) * a) -- same numbers, fewer
    big multiplications.  0^0 = 1, as in the binomial theorem, so p = 0 and
    p = 1 are handled.
    """
    a_pow = [1] * (n + 1)
    b_pow = [1] * (n + 1)
    for j in range(1, n + 1):
        a_pow[j] = a_pow[j - 1] * a
        b_pow[j] = b_pow[j - 1] * b
    return [math.comb(n, j) * a_pow[j] * b_pow[n - j] for j in range(n + 1)]


def binomial_terms(n: int, p) -> list:
    """
    The n+1 terms  C(n, j) p^j (1-p)^(n-j),  j = 0..n,  as exact Fractions.
    (For tests and inspection; the verdict path sums integers and reduces
    once, which is the same arithmetic.)
    """
    n = int(n)
    if n < 0:
        raise ValueError("n must be >= 0")
    fp = _p_as_fraction(p)
    a, d = fp.numerator, fp.denominator
    denom = d ** n
    return [Fraction(num, denom) for num in _term_numerators(n, a, d - a)]


def _tail_table(n: int, p):
    """(numerators N_0..N_n, common denominator d^n) for the printed terms."""
    n = int(n)
    if n < 0:
        raise ValueError("n must be >= 0")
    fp = _p_as_fraction(p)
    a, d = fp.numerator, fp.denominator
    return _term_numerators(n, a, d - a), d ** n


def _tail_from_table(x: int, nums: list, denom: int) -> Fraction:
    """P(X >= x) = sum_{j=x}^{n} N_j / d^n from a prepared table."""
    n = len(nums) - 1
    x = int(x)
    if x > n:
        return Fraction(0)
    return Fraction(sum(nums[max(x, 0):]), denom)


def _cutoff_from_table(nums: list, denom: int, fa: Fraction) -> int:
    """Smallest x with P(X >= x) < alpha, from a prepared table (n+1 if none)."""
    n = len(nums) - 1
    # "tail(x) < alpha"  <=>  tail_num * alpha_den < alpha_num * d^n  (exact integers).
    rhs = fa.numerator * denom
    tail_num = 0
    smallest_failing = n + 1
    for x in range(n, -1, -1):
        tail_num += nums[x]
        if tail_num * fa.denominator < rhs:
            smallest_failing = x
        else:
            break
    return smallest_failing


def binomial_upper_tail(x: int, n: int, p) -> Fraction:
    """
    Step 5, as printed:  P(X >= x) = sum_{j=x}^{n} C(n, j) p^j (1-p)^(n-j).
    Exact.  x > n gives 0 (empty sum); x <= 0 gives 1.
    """
    nums, denom = _tail_table(n, p)
    return _tail_from_table(x, nums, denom)


def fraction_to_decimal_str(fr: Fraction, digits: int = 40) -> str:
    """fr as a decimal string with `digits` significant digits (correctly rounded)."""
    import decimal
    ctx = decimal.Context(prec=digits, rounding=decimal.ROUND_HALF_EVEN)
    return str(ctx.divide(decimal.Decimal(fr.numerator), decimal.Decimal(fr.denominator)))


def binomial_upper_tail_float(x: int, n: int, p: float) -> float:
    """
    The same sum evaluated naively in binary64 (math.comb exact, float pow,
    math.fsum), for drivers that want to see what a float implementation of
    the printed formula gives.  Not used for the verdict.
    """
    n = int(n)
    x = int(x)
    if x > n:
        return 0.0
    x = max(x, 0)
    p = float(p)
    q = 1.0 - p
    return math.fsum(math.comb(n, j) * (p ** j) * (q ** (n - j)) for j in range(x, n + 1))


def sanity_cutoff(p, alpha=ALPHA_PRINTED, n: int = N_TRIALS_SPEC) -> int:
    """
    The smallest count X in [0, n+1] such that P(X' >= X) < alpha under the
    printed formula -- i.e. the smallest Xmax that FAILS step 5.  Xmax <=
    sanity_cutoff(...) - 1 passes.  Returns n+1 if no count in [0, n] fails
    (e.g. p = 1).  Exact rational arithmetic throughout.
    """
    nums, denom = _tail_table(n, p)
    return _cutoff_from_table(nums, denom, _alpha_as_fraction(alpha))


def sanity_cutoff_pass(p, alpha=ALPHA_PRINTED, n: int = N_TRIALS_SPEC) -> int:
    """The largest Xmax that PASSES step 5: sanity_cutoff(p, alpha, n) - 1."""
    return sanity_cutoff(p, alpha, n) - 1


# --------------------------------------------------------------------------
# The sanity check (3.1.4.3) on a matrix
# --------------------------------------------------------------------------

def _p_from_H_I(H_I: float) -> float:
    """Step 1: p = 2^-HI, in binary64."""
    H_I = float(H_I)
    if not math.isfinite(H_I):
        raise ValueError(f"H_I must be finite; got {H_I}")
    if H_I <= 0:
        raise ValueError(f"H_I must be > 0 (p = 2^-H_I must be a probability < 1); got {H_I}")
    return 2.0 ** (-H_I)


def sanity_check(M: np.ndarray, H_I: float, bits_per_symbol: int, alpha=ALPHA_PRINTED,
                 include_per_line: bool = False, count_method: str = "auto") -> dict:
    """
    SP 800-90B 3.1.4.3 steps 1-5 on the matrix M (already coerced, see
    as_matrix), with HI per matrix symbol.  Returns the intermediates and the
    verdict.  For a square matrix this is exactly the printed procedure; for
    a non-square one, see the module docstring ("Only the experiment ...").
    """
    r, c = M.shape
    bps = int(bits_per_symbol)
    p = _p_from_H_I(H_I)                                   # step 1
    fa = _alpha_as_fraction(alpha)

    XR_i = max_count_per_row(M, bps, count_method)         # step 2
    XC_i = max_count_per_column(M, bps, count_method)      # step 3
    X_R = int(XR_i.max())
    X_C = int(XC_i.max())
    X_max = max(X_C, X_R)                                  # step 4
    X_max_from = "row" if X_R >= X_C else "column"

    square = (r == c)
    if square:
        n = c                                              # 1000 in the spec
        nums, denom = _tail_table(n, p)                    # the printed terms, once
        P_exact = _tail_from_table(X_max, nums, denom)     # step 5, as printed
        P_R = _tail_from_table(X_R, nums, denom)
        P_C = _tail_from_table(X_C, nums, denom)
        passed = not (P_exact < fa)                        # "If Pr(X >= Xmax) < alpha, the test fails"
        n_rows_trials = n_cols_trials = n
        x_fail = _cutoff_from_table(nums, denom, fa)
    else:
        # Generalisation for probes only (see docstring): a row experiment
        # has c trials, a column experiment has r trials.
        n_rows_trials, n_cols_trials = c, r
        nums_r, denom_r = _tail_table(c, p)
        nums_c, denom_c = _tail_table(r, p)
        P_R = _tail_from_table(X_R, nums_r, denom_r)
        P_C = _tail_from_table(X_C, nums_c, denom_c)
        P_exact = min(P_R, P_C)
        passed = not (P_R < fa or P_C < fa)
        n = None
        x_fail = None

    out = {
        "r": r,
        "c": c,
        "spec_shape": bool(r == R_SPEC and c == C_SPEC),
        "square": square,
        "bits_per_matrix_symbol": bps,
        "H_I": float(H_I),
        "p": p,                                            # step 1
        "p_exact": str(Fraction(p)),
        "alpha": float(fa),
        "alpha_exact": str(fa),
        "alpha_printed": ALPHA_PRINTED,
        "alpha_derived_0.01_over_2000": ALPHA_DERIVED,
        "X_R": X_R,                                        # step 2
        "X_C": X_C,                                        # step 3
        "X_max": X_max,                                    # step 4
        "X_max_from": X_max_from,
        "n_trials": n,
        "n_trials_rows": n_rows_trials,
        "n_trials_columns": n_cols_trials,
        "P(X >= X_max)": float(P_exact),                   # step 5
        "P(X >= X_max) exact (40 digits)": fraction_to_decimal_str(P_exact, 40),
        "P(X >= X_max) float64 naive": (
            binomial_upper_tail_float(X_max, n, p) if square else float("nan")
        ),
        "P(X >= X_R)": float(P_R),
        "P(X >= X_C)": float(P_C),
        "sanity_check_passed": bool(passed),
        "H_I_exceeds_width": bool(float(H_I) > bps),
    }
    # Cutoffs (derived; the text never names one -- see docstring).
    if square:
        out["X_cutoff_fail"] = x_fail                      # Xmax >= this fails
        out["X_cutoff_pass"] = x_fail - 1                  # Xmax <= this passes
        # consistency: the threshold form and the printed tail must agree
        assert passed == (X_max <= x_fail - 1), (passed, X_max, x_fail)
    else:
        out["X_cutoff_fail_rows"] = _cutoff_from_table(nums_r, denom_r, fa)
        out["X_cutoff_fail_columns"] = _cutoff_from_table(nums_c, denom_c, fa)
        out["X_cutoff_fail"] = None
        out["X_cutoff_pass"] = None
    if include_per_line:
        out["X_R_i"] = XR_i.tolist()
        out["X_C_i"] = XC_i.tolist()
    # Fork JSON field names (from NOTICE), for the differential driver.
    out["restartHI"] = float(H_I)
    out["restartAlpha"] = float(fa)
    out["restartXmax"] = X_max
    out["restartXcutoff"] = out["X_cutoff_pass"]
    out["restartXcutoffPrintedBinomial"] = out["X_cutoff_pass"]
    out["restartCutoffMethod"] = CUTOFF_METHOD
    out["passedRestartSanityCheck"] = bool(passed)
    return out


# --------------------------------------------------------------------------
# Hr and Hc: the section 6.1 / 6.2 estimators on the row and column datasets
# --------------------------------------------------------------------------

def mcv_estimate_literal(symbols, bits_per_symbol: int) -> dict:
    """
    Section 6.3.1 as printed (the IID track of 6.1), self-contained so the
    IID restart path does not depend on a sibling module.
    """
    arr = np.asarray(symbols)
    L = int(arr.size)
    if L < 2:
        return {"L": L, "Mode count": int(L), "p-hat": float("nan"),
                "p_u": float("nan"), "min entropy": float("nan"), "min_entropy": float("nan")}
    bps = int(bits_per_symbol)
    if bps <= 24:
        counts = np.bincount(arr.astype(np.intp, copy=False))
        mode_count = int(counts.max())
    else:
        _, counts = np.unique(arr, return_counts=True)
        mode_count = int(counts.max())
    p_hat = mode_count / L                                             # step 1
    p_u = min(1.0, p_hat + Z_MCV_PRINTED * math.sqrt(p_hat * (1.0 - p_hat) / (L - 1)))   # step 2
    h = -math.log2(p_u) + 0.0                                          # step 3 (+0.0: -0.0 -> 0.0)
    return {"L": L, "Mode count": mode_count, "p-hat": p_hat, "p_u": p_u,
            "min entropy": h, "min_entropy": h}


def _load_sibling(stem: str):
    """Import py90b/<stem>.py by path; None if it is absent or fails to import."""
    path = HERE / f"{stem}.py"
    if not path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(f"py90b_restart_sibling_{stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:          # a sibling that cannot import is reported as missing
        return None


def non_iid_estimate(symbols, bits_per_symbol: int) -> dict:
    """
    Section 6.2: the minimum over the ten estimators, skipping Collision,
    Markov and Compression for non-binary input ("only applied to binary
    inputs").  Uses whichever sibling py90b modules import; records the rest
    as missing so the caller knows whether the battery was complete.
    """
    bps = int(bits_per_symbol)
    arr = np.asarray(symbols)
    per = {}
    used, missing, skipped_binary_only, failed = [], [], [], {}
    for label, stem, binary_only in NON_IID_BATTERY:
        if binary_only and bps != 1:
            skipped_binary_only.append(label)
            continue
        mod = _load_sibling(stem)
        if mod is None or not hasattr(mod, "estimate"):
            missing.append(label)
            continue
        try:
            res = mod.estimate(arr, bps)
            h = float(res["min_entropy"])
        except Exception as exc:   # record, do not hide
            failed[label] = f"{type(exc).__name__}: {exc}"
            continue
        per[label] = h
        if math.isfinite(h):
            used.append(label)
    finite = [per[k] for k in used]
    h_min = min(finite) if finite else float("nan")
    return {
        "min_entropy": h_min,
        "per_estimator": per,
        "estimators_used": used,
        "estimators_missing": missing,
        "estimators_failed": failed,
        "estimators_skipped_binary_only": skipped_binary_only,
        "estimators_complete": not missing and not failed,
    }


def _make_estimator(estimation_track: str, estimator):
    """Return (callable(symbols, bps) -> dict with 'min_entropy', description)."""
    if estimator is not None:
        def _wrap(symbols, bps):
            v = estimator(symbols, bps)
            if isinstance(v, dict):
                return {"min_entropy": float(v["min_entropy"]), "detail": v}
            return {"min_entropy": float(v)}
        return _wrap, "caller-supplied estimator"
    if estimation_track == "iid":
        return mcv_estimate_literal, "6.1 IID track: Most Common Value (6.3.1), in-module"
    if estimation_track == "non_iid":
        return non_iid_estimate, "6.2 non-IID track: minimum over sibling py90b estimators"
    raise ValueError("estimation_track must be 'iid' or 'non_iid'")


# --------------------------------------------------------------------------
# H_I parsing (per symbol / per bit)
# --------------------------------------------------------------------------

def parse_H_I(value, default_scale: str = "symbol"):
    """
    Accept a number, or a string '<v>', '<v>/symbol', '<v>/bit'.
    Returns (float value, scale) with scale in {'symbol', 'bit'}.
    """
    if value is None:
        return None, default_scale
    if isinstance(value, str):
        s = value.strip()
        scale = default_scale
        for suffix, sc in (("/symbol", "symbol"), ("/sample", "symbol"), ("/bit", "bit")):
            if s.endswith(suffix):
                s = s[: -len(suffix)]
                scale = sc
                break
        try:
            v = float(s)
        except ValueError:
            raise ValueError(f"H_I must be a number optionally followed by /symbol or /bit; got {value!r}")
        return v, scale
    return float(value), default_scale


# --------------------------------------------------------------------------
# The full validation test (3.1.4.2)
# --------------------------------------------------------------------------

def check(matrix, H_I, bits_per_symbol, *, alpha=ALPHA_PRINTED, estimation_track: str = "non_iid",
          estimator=None, track: str = "literal", bit_order: str = "msb",
          bitstring_mode: str = "full", H_I_scale: str = "symbol", always_estimate: bool = False,
          include_per_line: bool = False, run_estimators: bool = True, r=None, c=None,
          count_method: str = "auto") -> dict:
    """
    SP 800-90B 3.1.4.2 on the restart matrix:
      1. sanity check (3.1.4.3); fail -> no estimate;
      2. Hr, Hc from 6.1 / 6.2 on the row and column datasets;
      3. min(Hr, Hc) < HI/2 -> fail -> no estimate; else H = min(Hr, Hc, HI).
    H_I is per SAMPLE by default (H_I_scale='symbol'); 'bit' means per bit.
    Returns the intermediates with both the standard's names and the fork's
    JSON names.  min_entropy is per MATRIX SYMBOL (a bit in bitstring mode);
    min_entropy_per_sample is per original sample.
    """
    bps = int(bits_per_symbol)
    M = as_matrix(matrix, bps, r, c)
    r0, c0 = M.shape

    H_I_value, scale = parse_H_I(H_I, H_I_scale)
    if H_I_value is None:
        raise ValueError("H_I is required for the validation test")
    if not math.isfinite(H_I_value) or H_I_value <= 0:
        raise ValueError(f"H_I must be finite and > 0; got {H_I_value}")
    H_I_per_symbol = H_I_value if scale == "symbol" else H_I_value * bps
    H_I_per_bit = H_I_value if scale == "bit" else H_I_value / bps

    if track == "literal" or bps == 1:
        # The matrix of samples as read.  (For bps == 1 a sample IS a bit,
        # so per-symbol and per-bit HI coincide and the bitstring track is
        # the literal one.)
        M_used, bps_used = M, bps
        H_I_used = H_I_per_symbol
    elif track == "bitstring":
        bits = to_bit_matrix(M, bps, bit_order)
        if bitstring_mode == "full":
            M_used = bits
        elif bitstring_mode == "truncate_rows":
            M_used = np.ascontiguousarray(bits[:, :c0])
        else:
            raise ValueError("bitstring_mode must be 'full' or 'truncate_rows'")
        bps_used = 1
        H_I_used = H_I_per_bit
    else:
        raise ValueError("track must be 'literal' or 'bitstring'")

    sc = sanity_check(M_used, H_I_used, bps_used, alpha, include_per_line, count_method)

    est_fn, est_desc = _make_estimator(estimation_track, estimator)
    H_r = H_c = float("nan")
    row_detail = col_detail = None
    estimated = False
    if run_estimators and (sc["sanity_check_passed"] or always_estimate):
        rd = est_fn(row_dataset(M_used), bps_used)
        cd = est_fn(column_dataset(M_used), bps_used)
        H_r, H_c = float(rd["min_entropy"]), float(cd["min_entropy"])
        row_detail, col_detail = rd, cd
        estimated = True

    half = H_I_used / 2.0
    min_rc = min(H_r, H_c) if estimated else float("nan")
    if not sc["sanity_check_passed"]:
        validation_passed = False
        reason = "sanity check failed (3.1.4.3)"
        H = float("nan")
    elif not estimated:
        validation_passed = None
        reason = "row/column estimates not computed"
        H = float("nan")
    elif not (math.isfinite(H_r) and math.isfinite(H_c)):
        validation_passed = None
        reason = "a row/column estimate is not a number"
        H = float("nan")
    elif min_rc < half:                                 # "less than half of HI" -- strict
        validation_passed = False
        reason = "min(Hr, Hc) < HI/2 (3.1.4.2)"
        H = float("nan")
    else:
        validation_passed = True
        reason = "passed"
        H = min(H_r, H_c, H_I_used)                     # "min(Hr, Hc, HI)"

    out = dict(sc)
    out.update({
        "track": track if bps > 1 else "literal",
        "bits_per_symbol": bps,
        "bitstring_mode": bitstring_mode if (track == "bitstring" and bps > 1) else None,
        "bit_order": bit_order if (track == "bitstring" and bps > 1) else None,
        "H_I_input": H_I_value,
        "H_I_input_scale": scale,
        "H_I_per_symbol": H_I_per_symbol,
        "H_I_per_bit": H_I_per_bit,
        "H_I": H_I_used,                     # the value step 1 used, per matrix symbol
        "H_I/2": half,
        "estimation_track": estimation_track if estimator is None else "custom",
        "estimator": est_desc,
        "H_r": H_r,
        "H_c": H_c,
        "min(H_r, H_c)": min_rc,
        "row_estimate": row_detail,
        "column_estimate": col_detail,
        "validation_passed": validation_passed,
        "validation_reason": reason,
        "min_entropy": H,
        "min_entropy_per_sample": (H * bps) if (track == "bitstring" and bps > 1 and math.isfinite(H)) else H,
    })
    out["restartHI"] = H_I_used
    return out


def estimate(symbols, bits_per_symbol, **options) -> dict:
    """
    Driver-facing wrapper over check().  `symbols` is the flat restart data
    (row-major), length r*c.  Option H_I may be absent: then the matrix
    statistics (X_R, X_C, X_max) and, if run_estimators, H_r/H_c are
    returned with min_entropy = NaN and validation_passed = None, because the
    standard gives no verdict without HI.
    """
    bps = int(bits_per_symbol)
    opts = dict(options)
    H_I = opts.pop("H_I", None)
    r = opts.pop("r", None)
    c = opts.pop("c", None)
    if H_I is not None:
        return check(symbols, H_I, bps, r=r, c=c, **opts)

    # No HI: report what can be reported.
    track = opts.get("track", "literal")
    bit_order = opts.get("bit_order", "msb")
    bitstring_mode = opts.get("bitstring_mode", "full")
    include_per_line = opts.get("include_per_line", False)
    run_estimators = opts.get("run_estimators", True)
    count_method = opts.get("count_method", "auto")
    M = as_matrix(symbols, bps, r, c)
    if track == "bitstring" and bps > 1:
        bits = to_bit_matrix(M, bps, bit_order)
        M_used = bits if bitstring_mode == "full" else np.ascontiguousarray(bits[:, : M.shape[1]])
        bps_used = 1
    else:
        M_used, bps_used = M, bps
    XR_i = max_count_per_row(M_used, bps_used, count_method)
    XC_i = max_count_per_column(M_used, bps_used, count_method)
    out = {
        "r": M_used.shape[0], "c": M_used.shape[1],
        "spec_shape": bool(M_used.shape == (R_SPEC, C_SPEC)),
        "bits_per_symbol": bps, "bits_per_matrix_symbol": bps_used,
        "track": track if bps > 1 else "literal",
        "H_I": float("nan"), "p": float("nan"), "alpha": ALPHA_PRINTED,
        "X_R": int(XR_i.max()), "X_C": int(XC_i.max()),
        "X_max": int(max(XR_i.max(), XC_i.max())),
        "P(X >= X_max)": float("nan"),
        "sanity_check_passed": None,
        "H_r": float("nan"), "H_c": float("nan"),
        "validation_passed": None,
        "validation_reason": "H_I not supplied: the standard gives no verdict",
        "min_entropy": float("nan"),
        "restartHI": float("nan"), "restartAlpha": ALPHA_PRINTED,
        "restartXmax": int(max(XR_i.max(), XC_i.max())),
        "restartXcutoff": None, "restartXcutoffPrintedBinomial": None,
        "restartCutoffMethod": CUTOFF_METHOD, "passedRestartSanityCheck": None,
    }
    if include_per_line:
        out["X_R_i"] = XR_i.tolist()
        out["X_C_i"] = XC_i.tolist()
    if run_estimators:
        est_fn, est_desc = _make_estimator(opts.get("estimation_track", "non_iid"), opts.get("estimator"))
        rd = est_fn(row_dataset(M_used), bps_used)
        cd = est_fn(column_dataset(M_used), bps_used)
        out.update({"H_r": float(rd["min_entropy"]), "H_c": float(cd["min_entropy"]),
                    "row_estimate": rd, "column_estimate": cd, "estimator": est_desc})
    return out


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

USAGE = """usage: python restart.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                         [--H_I <v>[/symbol|/bit]] [--iid|--non-iid] [--shape RxC]
                         [--alpha A] [--no-estimators] [--always-estimate]
                         [--per-line] [--lsb-first] [--bitstring-mode full|truncate_rows]

  rawfile          one symbol per byte; the low bits_per_symbol bits are the symbol
  --literal        test the matrix of samples as read (default; SP 800-90B 3.1.4 as written)
  --bitstring      expand each sample to bits_per_symbol bits MSB-first within its row
  --H_I            the initial entropy estimate HI (3.1.3); '/symbol' (default) or '/bit'
  --iid/--non-iid  which section 6 track gives Hr and Hc (default --non-iid)
  --shape RxC      matrix shape when the file is not 1000x1000 (probes only)
  --alpha A        per-experiment alpha (default 0.000005, 3.1.4.3 step 1)
Prints the result dict as JSON on stdout.
"""


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Fraction):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def _parse_args(argv):
    positional = []
    opts = {"track": "literal", "estimation_track": "non_iid", "bit_order": "msb",
            "bitstring_mode": "full", "run_estimators": True, "always_estimate": False,
            "include_per_line": False}
    H_I = None
    shape = None
    alpha = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--literal":
            opts["track"] = "literal"
        elif a == "--bitstring":
            opts["track"] = "bitstring"
        elif a == "--iid":
            opts["estimation_track"] = "iid"
        elif a == "--non-iid":
            opts["estimation_track"] = "non_iid"
        elif a == "--lsb-first":
            opts["bit_order"] = "lsb"
        elif a == "--no-estimators":
            opts["run_estimators"] = False
        elif a == "--always-estimate":
            opts["always_estimate"] = True
        elif a == "--per-line":
            opts["include_per_line"] = True
        elif a in ("--H_I", "--HI", "--h_i"):
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            H_I = argv[i]
        elif a == "--shape":
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            try:
                rs, cs = argv[i].lower().split("x")
                shape = (int(rs), int(cs))
            except ValueError:
                raise SystemExit(f"--shape wants RxC, got {argv[i]!r}\n{USAGE}")
        elif a == "--alpha":
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            alpha = argv[i]          # kept as a string so the decimal is exact
        elif a == "--bitstring-mode":
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            opts["bitstring_mode"] = argv[i]
        elif a in ("-h", "--help"):
            raise SystemExit(USAGE)
        elif a.startswith("-") and len(a) > 1:
            raise SystemExit(f"unknown option {a!r}\n{USAGE}")
        else:
            positional.append(a)
        i += 1
    if len(positional) != 2:
        raise SystemExit(USAGE)
    path = positional[0]
    try:
        bps = int(positional[1])
    except ValueError:
        raise SystemExit(f"bits_per_symbol must be an integer, got {positional[1]!r}\n{USAGE}")
    if not 1 <= bps <= 8:
        raise SystemExit("bits_per_symbol must be in 1..8 for a byte-per-symbol file\n" + USAGE)
    if H_I is not None:
        opts["H_I"] = H_I
    if shape is not None:
        opts["r"], opts["c"] = shape
    if alpha is not None:
        opts["alpha"] = alpha
    return path, bps, opts


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    path, bps, opts = _parse_args(argv)

    with open(path, "rb") as fh:
        raw = fh.read()
    data = np.frombuffer(raw, dtype=np.uint8)

    # "one symbol per byte, low bits_per_symbol bits are the symbol"
    mask = (1 << bps) - 1
    masked_bytes = int(np.count_nonzero(data > mask))
    symbols = data & np.uint8(mask)

    result = estimate(symbols, bps, **opts)
    result["input_path"] = path
    result["input_bytes"] = int(data.size)
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["out_of_width_bytes_masked"] = masked_bytes
    if masked_bytes:
        print(
            f"warning: {masked_bytes} byte(s) had bits set above width {bps}; "
            f"only the low {bps} bit(s) were used",
            file=sys.stderr,
        )
    print(json.dumps(result, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    sys.exit(main())
