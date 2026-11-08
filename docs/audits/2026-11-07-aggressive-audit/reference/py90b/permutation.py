"""
py90b.permutation -- SP 800-90B section 5.1, Permutation Testing (the IID
"shuffling" tests): the eleven test statistics of sections 5.1.1 - 5.1.11,
Conversions I and II for binary data, the 10 000-shuffle procedure of Figure 4
with its counters C_{i,0} and C_{i,1}, the Fisher-Yates shuffle of Figure 5,
the per-test ranking rule and the overall IID decision.

INDEPENDENT reference implementation, written FROM THE STANDARD'S TEXT ONLY
(NIST SP 800-90B, January 2018, as extracted to reference/sp800-90b.pages.txt).
No file under cpp/ was opened while writing this.  The verbose-label capture
for ea_iid (reference/cpp-verbose-labels-iid.txt) shows the permutation tests
were SKIPPED in that run ("** Skipped IID permutation tests after an earlier
required IID test failure"), so there are NO C++ label names to borrow for this
module; the keys below are the standard's own statistic names.

----------------------------------------------------------------------------
Spec text relied on (quoted; PDF page numbers of the January 2018 PDF)
----------------------------------------------------------------------------

Section 5 intro (PDF p. 37): "These tests take the sequence S = (s1,...,sL),
where si in A = {x1,...,xk}, as input, and test the hypothesis that the values
in S are IID.  If the hypothesis is rejected by any of the tests, the values in
S are assumed to be non-IID."

Section 5.1, Figure 4 (PDF p. 37) -- the procedure:
    "Input: S = (s1,..., sL)   Output: Decision on the IID assumption
     1. For each test i
        1.1. Assign the counters Ci,0 and Ci,1 to zero.
        1.2. Calculate the test statistic Ti on S.
     2. For j = 1 to 10 000
        2.1. Permute S using the Fisher-Yates shuffle algorithm.
        2.2. For each test i
             2.2.1. Calculate the test statistic T on the permuted data.
             2.2.2. If (T > Ti), increment Ci,0. If (T = Ti), increment Ci,1.
     3. If ((Ci,0+Ci,1 <= 5) or (Ci,0 >= 9995)) for any i, reject the IID
        assumption; else, assume that the noise source outputs are IID."

Section 5.1 prose (PDF p. 38): "If the sum of Ci,0 and Ci,1 is less than 5, it
means that the original test statistic has a very high rank; conversely, if
Ci,0 is greater than 9995, it means that the original test statistics has a
very low rank.  The cutoff values for Ci,0 and Ci,1 are calculated using a type
I error probability of 0.001."
    -> The prose uses STRICT inequalities ("less than 5", "greater than 9995")
       where Figure 4 step 3 uses <= 5 and >= 9995.  The two differ exactly at
       Ci,0 + Ci,1 = 5 and at Ci,0 = 9995.  Figure 4 is the algorithm and is
       the default here (counter_rule='figure4'); the prose reading is exposed
       as counter_rule='prose'.  Recorded as a spec ambiguity.

Section 5.1, Figure 5 (PDF p. 38) -- the shuffle:
    "Input: S = (s1,..., sL)   Output: Shuffled S = (s1,..., sL)
     1. for i from L downto 1 do
        a. Generate a random integer j such that 1 <= j <= i.
        b. Swap sj and si"

Section 5.1 (PDF p. 38) -- binary data:
    "The tests are applicable to both binary and non-binary data, but for some
     of the tests, the number of distinct sample values, denoted k (the size of
     the set A), significantly affects the distribution of the test statistics,
     and thus the type I error.  For such tests, one of the following
     conversions is applied to the input data, when the input is binary, i.e.,
     k = 2.
     * Conversion I partitions the sequences into eight-bit non-overlapping
       blocks, and counts the number of ones in each block.  Zeroes are
       appended when the last block has less than eight bits.  For example, let
       the 20-bit input be (1,0,0,0,1,1,1,0,1,1,0,1,1,0,1,1,0,0,1,1).  The first
       and the second eight-bit blocks include four and six ones, respectively.
       The last block, which is not complete, includes two ones.  The output
       sequence is (4, 6, 2).
     * Conversion II partitions the sequences into eight-bit non-overlapping
       blocks, and calculates the integer value of each block.  For example,
       let the input message be (1,0,0,0,1,1,1,0,1,1,0,1,1,0,1,1,0,0,1,1).  The
       integer values of the first two blocks are 142, and 219.  Zeroes are
       appended when the last block has less than eight bits.  Then, the last
       block becomes (0,0,1,1,0,0,0,0) with an integer value of 48.  The output
       sequence is (142, 219, 48)."
    -> 142 = (1,0,0,0,1,1,1,0) read with the FIRST bit most significant, so
       Conversion II is big-endian within a block.
    -> "binary, i.e., k = 2" defines binary by the OBSERVED alphabet size, not
       by the declared sample width.  binary_mode='alphabet' (default, literal)
       follows that; binary_mode='width' (binary iff bits_per_symbol == 1) is
       exposed because the two differ materially when an 8-bit file happens to
       hold exactly two values.  When k = 2 but the two values are not {0, 1},
       the conversions need bits: the smaller value is taken as 0 and the
       larger as 1 (the standard does not say; recorded as an ambiguity).

Which statistics use which conversion when the input is binary (each section's
"Handling binary data" paragraph, PDF pp. 39-43):
    5.1.1  Excursion ................ "no additional conversion steps are required"
    5.1.2  Number of directional runs  "first apply Conversion I"
    5.1.3  Length of directional runs  "first apply Conversion I"
    5.1.4  Number of increases/decreases "first apply the Conversion I"
    5.1.5  Number of runs based on median "the median of the input data is
           assumed to be 0.5.  No additional conversion steps are required."
    5.1.6  Length of runs based on median  (same as 5.1.5)
    5.1.7  Average collision ........ "first apply Conversion II"
    5.1.8  Maximum collision ........ "first apply Conversion II"
    5.1.9  Periodicity .............. "first apply Conversion I"
    5.1.10 Covariance ............... "first apply Conversion I"
    5.1.11 Compression .............. "applied directly to binary data, with
           no conversion required"
The conversion is applied to the PERMUTED binary sequence inside each
statistic (Figure 4 permutes S, the input; each section says to convert "the
input sequence" first), i.e. the bits are shuffled and then blocked.  That is
the literal reading and the default (conversion_timing='after_shuffle').  The
text can also be read as forming the Conversion I / II sequences once and
permuting THOSE ("one of the following conversions is applied to the input
data" before the procedure); the two readings give different null
distributions for the 12 converted statistics, so the second is exposed as
conversion_timing='before_shuffle' (the converted sequences are then shuffled
by the same per-iteration RNG stream, after the bits).  Recorded as a spec
ambiguity.

The eleven statistics are quoted in their own docstrings below.  Sections
5.1.9 and 5.1.10 each say "The test is repeated for five different values of
p: 1, 2, 8, 16, and 32", so the battery has 8 + 5 + 5 + 1 = 19 statistics,
each with its own counters, and step 3's "for any i" ranges over all 19.

----------------------------------------------------------------------------
API (contract for the differential driver)
----------------------------------------------------------------------------

    estimate(symbols, bits_per_symbol, **options) -> dict
        symbols: a sequence / np.ndarray / bytes of ints in [0, 2**bits_per_symbol)
        returns {'min_entropy': nan, 'iid_assumption': bool,
                 <statistic name>: T on the original data, for all 19,
                 'tests': {name: {'T', 'C0', 'C1', 'passed', 'defined', ...}},
                 ...}.
        Section 5.1 yields a DECISION, not an entropy figure, so 'min_entropy'
        is float('nan') ("use float('nan') where the spec gives no value").

    permutation_test(symbols, bits_per_symbol, shuffles=10000, rng=None, **options)
        the same dict; `rng` is any object with an in-place .shuffle(ndarray)
        that is a correct Fisher-Yates (numpy's Generator.shuffle is one; see
        PythonFisherYates below for the Figure 5 transcription).  With rng=None
        every shuffle j uses its own numpy PCG64 stream derived from `seed`
        via SeedSequence(seed, spawn_key=(j,)), so the result is reproducible
        and independent of how the shuffles are split across `workers`.

    Each statistic is its own function on a symbol list (excursion(S), ...).
    The counting rule is pure: counter_update(), cutoffs(), test_rejects(),
    iid_decision().

    python permutation.py <rawfile> <bits_per_symbol> [--literal|--bitstring] [...]
        rawfile: one symbol per byte, the low bits_per_symbol bits are the symbol;
        --bitstring expands each symbol to bits_per_symbol bits MSB-first and
        treats the result as 1-bit symbols.  Prints the dict as JSON.

Pure Python + numpy (+ the standard library's bz2, which IS the bzip2
algorithm [BZ2] the standard names, and multiprocessing for `workers`).
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import multiprocessing
import os
import sys

import numpy as np


def _import_bz2():
    """Import the standard library's bz2 (libbzip2) even when this directory
    is on sys.path.  Python 3.14's bz2.py does `from compression._common import
    _streams`, and the sibling module compression.py (py90b's section 6.3.4
    reference) shadows the stdlib package `compression` whenever the py90b
    directory is sys.path[0] -- which it is when permutation.py runs as a
    script.  So: try plainly; on that failure set this directory aside, drop
    the shadowing entry from sys.modules, import, and restore sys.path."""
    try:
        import bz2
        return bz2
    except ModuleNotFoundError:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    saved_path = list(sys.path)
    shadow = sys.modules.pop("compression", None)
    sys.path = [p for p in sys.path
                if os.path.abspath(p if p else os.getcwd()) != here]
    try:
        import bz2
    finally:
        sys.path = saved_path
    # The shadowing module (if any) stays out of sys.modules on purpose: putting
    # it back would re-shadow the stdlib package for every later import.
    del shadow
    return bz2


bz2 = _import_bz2()

NAN = float("nan")

#: Figure 4 step 2: "For j = 1 to 10 000".
SHUFFLES = 10_000

#: Sections 5.1.9 / 5.1.10: "The test is repeated for five different values of
#: p: 1, 2, 8, 16, and 32."
LAGS = (1, 2, 8, 16, 32)

#: Section 5.1.11 step 2: "the bzip2 compression algorithm provided in [BZ2]".
#: The standard names no compression level; 9 (900 kB blocks) is bzip2's own
#: default and is used unless bz2_level says otherwise.
BZ2_LEVEL = 9


# ==========================================================================
# Input handling
# ==========================================================================

def _dtype_for(bits_per_symbol: int):
    if bits_per_symbol <= 8:
        return np.uint8
    if bits_per_symbol <= 16:
        return np.uint16
    if bits_per_symbol <= 32:
        return np.uint32
    if bits_per_symbol <= 64:
        return np.uint64
    raise ValueError("bits_per_symbol above 64 is not supported by this module")


def _seq(S) -> np.ndarray:
    """A 1-D integer ndarray view of a statistic's input (list, tuple, bytes or array)."""
    if isinstance(S, (bytes, bytearray, memoryview)):
        a = np.frombuffer(S, dtype=np.uint8)
    else:
        a = np.asarray(S)
    if a.ndim != 1:
        raise ValueError("a sample sequence must be one-dimensional")
    if a.dtype == np.bool_:
        a = a.astype(np.uint8)
    if a.size and not np.issubdtype(a.dtype, np.integer):
        raise ValueError(f"samples must be integers, got dtype {a.dtype}")
    return a


def _as_symbol_array(symbols, bits_per_symbol: int, validate: bool) -> np.ndarray:
    arr = _seq(symbols)
    if arr.size == 0:
        return np.zeros(0, dtype=_dtype_for(bits_per_symbol))
    if validate:
        lo, hi = int(arr.min()), int(arr.max())
        if lo < 0 or hi >= (1 << bits_per_symbol):
            raise ValueError(
                f"symbols must lie in [0, 2**{bits_per_symbol}); observed min={lo} max={hi}"
            )
    return arr.astype(_dtype_for(bits_per_symbol), copy=False)


def to_bitstring(symbols, bits_per_symbol: int, bit_order: str = "msb") -> np.ndarray:
    """Expand every symbol to bits_per_symbol bits and concatenate (MSB-first by
    default; the standard fixes no order -- MSB-first is this audit's convention)."""
    bps = int(bits_per_symbol)
    if bps < 1:
        raise ValueError("bits_per_symbol must be >= 1")
    arr = _as_symbol_array(symbols, bps, validate=True)
    if bps == 1:
        return arr.astype(np.uint8, copy=False)
    if bit_order == "msb":
        shifts = np.arange(bps - 1, -1, -1)
    elif bit_order == "lsb":
        shifts = np.arange(0, bps)
    else:
        raise ValueError("bit_order must be 'msb' or 'lsb'")
    shifts = shifts.astype(arr.dtype)
    bits = (arr[:, None] >> shifts[None, :]) & arr.dtype.type(1)
    return bits.reshape(-1).astype(np.uint8, copy=False)


def _distinct_count(S: np.ndarray) -> int:
    """k, 'the number of distinct sample values' (section 5.1, PDF p. 38)."""
    if S.size == 0:
        return 0
    if S.dtype.itemsize <= 2:
        return int(np.count_nonzero(np.bincount(S.astype(np.intp, copy=False))))
    return int(np.unique(S).size)


# ==========================================================================
# Conversions I and II (section 5.1, PDF p. 38)
# ==========================================================================

def _blocks_of_8(bits) -> np.ndarray:
    """'partitions the sequences into eight-bit non-overlapping blocks ...
    Zeroes are appended when the last block has less than eight bits.'
    Returns an (nblocks, 8) array of 0/1."""
    b = _seq(bits)
    if b.size and (int(b.min()) < 0 or int(b.max()) > 1):
        raise ValueError("Conversions I and II take a sequence of bits (0/1)")
    b = b.astype(np.uint8, copy=False)
    pad = (-b.size) % 8
    if pad:
        b = np.concatenate([b, np.zeros(pad, dtype=np.uint8)])
    return b.reshape(-1, 8)


def conversion_I(bits) -> np.ndarray:
    """Conversion I: 'counts the number of ones in each block'.  Example in the
    text: 20 bits (1,0,0,0,1,1,1,0,1,1,0,1,1,0,1,1,0,0,1,1) -> (4, 6, 2)."""
    return _blocks_of_8(bits).sum(axis=1).astype(np.uint8)


#: Conversion II reads each block with its first bit most significant:
#: (1,0,0,0,1,1,1,0) = 128 + 8 + 4 + 2 = 142, as the text's example says.
_BIT_WEIGHTS = np.array([128, 64, 32, 16, 8, 4, 2, 1], dtype=np.int64)


def conversion_II(bits) -> np.ndarray:
    """Conversion II: 'calculates the integer value of each block'.  Example in
    the text: the same 20 bits -> (142, 219, 48)."""
    return np.dot(_blocks_of_8(bits), _BIT_WEIGHTS).astype(np.uint8)


# ==========================================================================
# The eleven test statistics (sections 5.1.1 - 5.1.11)
# Each takes the sequence S (a list / array of integers) and returns T exactly
# as the section defines it; float('nan') where the definition has no value.
# ==========================================================================

def excursion(S) -> float:
    """
    5.1.1 Excursion Test Statistic (PDF p. 39):
      "1. Calculate the average of the sample values, i.e., X-bar = (s1 + s2 + ... + sL) / L
       2. For i = 1 to L   Calculate di = | sum_{j=1..i} sj - i * X-bar |.
       3. T = max (d1,..., dL)."
    Example 1: S = (2, 15, 4, 10, 9) -> X-bar = 8, d = (6, 1, 3, 1, 0), T = 6.
    Handling binary data: "no additional conversion steps are required".

    Arithmetic: di = |P_i - i*total/L| = |L*P_i - i*total| / L with P_i the
    i-th partial sum, so the maximum is found EXACTLY in integers and divided
    by L once (one correctly rounded division).  Equal exact values therefore
    give equal floats, which matters for step 2.2.2's "T = Ti" test.
    """
    S = _seq(S)
    L = int(S.size)
    if L == 0:
        return NAN
    partial = np.cumsum(S.astype(np.int64))          # s1, s1+s2, ..., s1+...+sL
    total = int(partial[-1])                         # s1 + ... + sL   (X-bar = total / L)
    i = np.arange(1, L + 1, dtype=np.int64)
    if L * total < (1 << 62):                        # every |L*P_i - i*total| fits in int64
        d_scaled = np.abs(L * partial - i * total)   # = L * d_i, exactly
        return int(d_scaled.max()) / L
    # (unreachable for byte-per-symbol files; kept for completeness)
    xbar = total / L
    return float(np.abs(partial.astype(np.float64) - i * xbar).max())


def _directional_sequence(S) -> np.ndarray:
    """Step 1 of 5.1.2 / 5.1.3 / 5.1.4 (PDF pp. 39-40):
      "Construct the sequence S' = (s'1, ..., s'(L-1)), where
         s'i = -1, if si > si+1
               +1, if si <= si+1          for i = 1, ..., L-1."
    Empty when L < 2."""
    S = _seq(S)
    return np.where(S[:-1] > S[1:], -1, 1).astype(np.int8)


def _number_of_runs(seq: np.ndarray) -> int:
    """The number of runs (maximal blocks of equal consecutive values) in seq;
    0 for an empty sequence."""
    n = int(seq.size)
    if n == 0:
        return 0
    return 1 + int(np.count_nonzero(seq[1:] != seq[:-1]))


def _longest_run(seq: np.ndarray):
    """The length of the longest run in seq; nan for an empty sequence (the
    maximum over no runs has no value)."""
    n = int(seq.size)
    if n == 0:
        return NAN
    change = np.flatnonzero(seq[1:] != seq[:-1]) + 1          # indices where a new run starts
    bounds = np.concatenate(([0], change, [n]))
    return int(np.diff(bounds).max())


def num_directional_runs(S) -> int:
    """5.1.2 Number of Directional Runs (PDF p. 39): "The test statistic T is the
    number of runs in S'."  Example 2: S = (2, 2, 2, 5, 7, 7, 9, 3, 1, 4, 4) ->
    S' = (+1,+1,+1,+1,+1,+1,-1,-1,+1,+1), three runs, T = 3.
    Handling binary data: "first apply Conversion I"."""
    return _number_of_runs(_directional_sequence(S))


def len_directional_runs(S):
    """5.1.3 Length of Directional Runs (PDF p. 40): "The test statistic T is the
    length of the longest run in S'."  Example 3: same S as Example 2, T = 6.
    Handling binary data: "first apply Conversion I"."""
    return _longest_run(_directional_sequence(S))


def num_increases_decreases(S) -> int:
    """5.1.4 Number of Increases and Decreases (PDF p. 40): "Calculate the number
    of -1's and +1's in S'; the test statistic T is the maximum of these numbers,
    i.e., T = max (number of -1's, number of +1's)."  Example 4: same S,
    eight +1's and two -1's, T = 8.
    Handling binary data: "first apply the Conversion I"."""
    d = _directional_sequence(S)
    plus = int(np.count_nonzero(d == 1))
    minus = int(d.size) - plus
    return max(minus, plus)


def median_of(S, rule: str = "mean"):
    """
    "Find the median X-tilde of S" (5.1.5 step 1, 5.1.6 step 1).  The standard
    does not say what the median of an even-length sequence is; the textbook
    definition (the middle value, or the mean of the two middle values) is the
    default.  rule='lower' / 'upper' take the lower / upper middle value
    instead, since the two readings can change s'_i for values between them.
    Example 5/6: S = (5, 15, 12, 1, 13, 9, 4) -> 9 (odd L: all rules agree).
    """
    S = _seq(S)
    L = int(S.size)
    if L == 0:
        return NAN
    srt = np.sort(S)
    lower = int(srt[(L - 1) // 2])
    upper = int(srt[L // 2])
    if rule == "mean":
        return (lower + upper) / 2          # equals the middle value when L is odd
    if rule == "lower":
        return lower
    if rule == "upper":
        return upper
    raise ValueError("median rule must be 'mean', 'lower' or 'upper'")


def _median_sequence(S, median) -> np.ndarray:
    """5.1.5 step 2 / 5.1.6 step 2 (PDF pp. 40-41):
      "Construct the sequence S' = (s'1, ..., s'L) where
         s'i = -1, if si < X-tilde
               +1, if si >= X-tilde        for i = 1, ..., L." """
    S = _seq(S)
    return np.where(S < median, -1, 1).astype(np.int8)


def num_runs_median(S, median=None, median_rule: str = "mean") -> int:
    """5.1.5 Number of Runs Based on the Median (PDF pp. 40-41): "The test
    statistic T is the number of runs in S'."  Example 5: S = (5, 15, 12, 1, 13,
    9, 4), median 9, S' = (-1,+1,+1,-1,+1,+1,-1), five runs, T = 5.
    Handling binary data: "the median of the input data is assumed to be 0.5.
    No additional conversion steps are required."  Pass median=0.5 for that.
    (The median is permutation-invariant, so a caller may compute it once.)"""
    if median is None:
        median = median_of(S, median_rule)
    return _number_of_runs(_median_sequence(S, median))


def len_runs_median(S, median=None, median_rule: str = "mean"):
    """5.1.6 Length of Runs Based on Median (PDF p. 41): "The test statistic T is
    the length of the longest run in S'."  Example 6: same S, T = 2.
    Handling binary data: as 5.1.5 (median assumed 0.5)."""
    if median is None:
        median = median_of(S, median_rule)
    return _longest_run(_median_sequence(S, median))


def collision_list(S) -> list:
    """
    The list C shared by 5.1.7 and 5.1.8 (PDF pp. 41-42):
      "1. Let C be a list of the number of the samples observed to find two
          occurrences of the same value in the input sequence S = (s1, ..., sL).
          C is initially empty.
       2. Let i = 1.
       3. While i < L
          a. Find the smallest j such that (si, ..., si+j-1) contains two
             identical values.  If no such j exists, break out of the while loop.
          b. Add j to the list C.
          c. i = i + j."
    Example 7: S = (2, 1, 1, 2, 0, 1, 0, 1, 1, 2) -> C = [3, 4, 2].

    Vectorised search: next[m] is the position of the next later occurrence of
    the value at m (L if none); the window starting at i first holds a
    duplicate at e[i] = min_{m >= i} next[m] (a suffix minimum), and then
    j = e[i] - i + 1.  Step 3's walk itself is sequential by definition
    (i = i + j) and is done in a plain loop over the precomputed e[].
    Positions are 0-based here; the standard's i runs 1..L.
    """
    S = _seq(S)
    L = int(S.size)
    if L < 2:
        return []
    order = np.argsort(S, kind="stable")                 # positions sorted by (value, position)
    sv = S[order]
    same = sv[1:] == sv[:-1]                             # consecutive entries holding equal values
    nxt = np.full(L, L, dtype=np.int64)                  # L means "no later occurrence"
    nxt[order[:-1][same]] = order[1:][same]
    e = np.minimum.accumulate(nxt[::-1])[::-1].tolist()  # e[i] = min_{m >= i} nxt[m]
    C = []
    i = 0                                                # "Let i = 1"
    while i < L - 1:                                     # "While i < L"  (1-based)
        end = e[i]                                       # position closing the smallest window
        if end >= L:                                     # "If no such j exists, break"
            break
        j = end - i + 1                                  # (si, ..., si+j-1) has j samples
        C.append(j)                                      # "Add j to the list C"
        i += j                                           # "i = i + j"
    return C


def avg_collision(S, C=None):
    """5.1.7 Average Collision Test Statistic (PDF pp. 41-42): "The test statistic
    T is the average of all values in the list C."  Example 7: C = [3, 4, 2],
    T = 3.  nan when C is empty (no collision anywhere).
    Handling binary data: "first apply Conversion II".
    The average is computed as (integer sum) / (integer count), one correctly
    rounded division, so equal exact averages give equal floats."""
    if C is None:
        C = collision_list(S)
    if not C:
        return NAN
    return sum(C) / len(C)


def max_collision(S, C=None):
    """5.1.8 Maximum Collision Test Statistic (PDF p. 42): "The test statistic T is
    the maximum value in the list C."  Example 8: C = [3, 4, 2], T = 4.  nan when
    C is empty.  Handling binary data: "first apply Conversion II"."""
    if C is None:
        C = collision_list(S)
    if not C:
        return NAN
    return max(C)


def periodicity(S, p: int):
    """5.1.9 Periodicity Test Statistic (PDF p. 42): "The test takes a lag
    parameter p as input, where p < L ...
       1. Initialize T to zero.
       2. For i = 1 to L - p   If (si = si+p), increment T by one."
    Example 9: S = (2, 1, 2, 1, 0, 1, 0, 1, 1, 2), p = 2 -> T = 5.
    Handling binary data: "first apply Conversion I".  Repeated for p in LAGS.
    The definition requires p < L; otherwise there is no value (nan)."""
    S = _seq(S)
    L = int(S.size)
    p = int(p)
    if p < 1 or p >= L:
        return NAN
    return int(np.count_nonzero(S[:-p] == S[p:]))


def covariance(S, p: int):
    """5.1.10 Covariance Test Statistic (PDF p. 43): "The test takes a lag value
    p < L as input ...
       1. Initialize T to zero.
       2. For i = 1 to L - p   T = T + (si x si+p)."
    Example 10: S = (5, 2, 6, 10, 12, 3, 1), p = 2 -> 5*6 + 2*10 + 6*12 + 10*3
    + 12*1 = 164.  Handling binary data: "first apply Conversion I".  Repeated
    for p in LAGS.  Requires p < L; otherwise nan."""
    S = _seq(S)
    L = int(S.size)
    p = int(p)
    if p < 1 or p >= L:
        return NAN
    a = S[:-p].astype(np.int64, copy=False)
    b = S[p:].astype(np.int64, copy=False)
    return int(np.dot(a, b))


#: Section 5.1.11 step 1 encoding, as a fixed-width table for byte-sized
#: values: entry v is the text of v followed by one space, NUL-padded to 4
#: bytes.  The NULs are removed after concatenation, leaving "144 21 139 0 ".
_DECIMAL_TABLE = np.array([(str(v) + " ").encode().ljust(4, b"\0") for v in range(256)], dtype="S4")


def encode_for_compression(S) -> bytes:
    """5.1.11 step 1 (PDF p. 43): "Encode the input data as a character string
    containing a list of values separated by a single space, e.g., 'S = (144,
    21, 139, 0, 0, 15)' becomes '144 21 139 0 0 15'."  No leading or trailing
    space, no newline."""
    S = _seq(S)
    if S.size == 0:
        return b""
    if S.dtype == np.uint8:
        return _DECIMAL_TABLE[S].tobytes().replace(b"\0", b"")[:-1]
    return " ".join(map(str, S.tolist())).encode("ascii")


def compression(S, level: int = BZ2_LEVEL) -> int:
    """5.1.11 Compression Test Statistic (PDF p. 43):
       "1. Encode the input data as a character string containing a list of
           values separated by a single space ...
        2. Compress the character string with the bzip2 compression algorithm
           provided in [BZ2].
        3. T is the length of the compressed string, in bytes."
    Handling binary data: "applied directly to binary data, with no conversion
    required".  Python's bz2 module IS libbzip2; `level` is bzip2's block-size
    level (the standard names none; 9 is bzip2's default)."""
    return len(bz2.compress(encode_for_compression(S), compresslevel=int(level)))


# ==========================================================================
# The battery: names, and which data each statistic sees for binary input
# ==========================================================================

def statistic_names(lags=LAGS) -> tuple:
    """The 19 statistics of the battery, in the order of sections 5.1.1-5.1.11."""
    return (
        "excursion",                 # 5.1.1
        "numDirectionalRuns",        # 5.1.2
        "lenDirectionalRuns",        # 5.1.3
        "numIncreasesDecreases",     # 5.1.4
        "numRunsMedian",             # 5.1.5
        "lenRunsMedian",             # 5.1.6
        "avgCollision",              # 5.1.7
        "maxCollision",              # 5.1.8
        *[f"periodicity({p})" for p in lags],   # 5.1.9
        *[f"covariance({p})" for p in lags],    # 5.1.10
        "compression",               # 5.1.11
    )


#: For BINARY input (k = 2): the data each statistic is computed on, from the
#: "Handling binary data" paragraph of each section.  'raw' = the sequence as
#: given, 'bits' = the same sequence as 0/1 bits, 'conv1' / 'conv2' = Conversion
#: I / II of those bits.  For non-binary input every statistic sees 'raw'.
BINARY_INPUT = {
    "excursion": "raw",                # 5.1.1: no conversion
    "numDirectionalRuns": "conv1",     # 5.1.2
    "lenDirectionalRuns": "conv1",     # 5.1.3
    "numIncreasesDecreases": "conv1",  # 5.1.4
    "numRunsMedian": "bits",           # 5.1.5: no conversion, median assumed 0.5
    "lenRunsMedian": "bits",           # 5.1.6: no conversion, median assumed 0.5
    "avgCollision": "conv2",           # 5.1.7
    "maxCollision": "conv2",           # 5.1.8
    "periodicity": "conv1",            # 5.1.9  (every lag)
    "covariance": "conv1",             # 5.1.10 (every lag)
    "compression": "raw",              # 5.1.11: no conversion
}


def _base_name(name: str) -> str:
    return name.split("(")[0]


def _lag_of(name: str) -> int:
    return int(name[name.index("(") + 1 : -1])


#: What the per-permutation statistic computation needs besides the data:
#:   binary    -- k = 2 (or bits_per_symbol = 1 under binary_mode='width')
#:   one_value -- the symbol read as bit 1 when binary and S is not already 0/1; None otherwise
#:   median    -- the median of S (permutation-invariant); unused when binary
#:   bz2_level -- bzip2 level for 5.1.11
#:   tests     -- the statistic names to compute
#:   conversion_timing -- 'after_shuffle' (literal) or 'before_shuffle'; see permutation_test()
#: (a namedtuple: picklable for the worker pool and independent of how the
#: module was loaded)
_Context = collections.namedtuple(
    "_Context", ["binary", "one_value", "median", "bz2_level", "tests", "conversion_timing"])


def _needs(tests, source: str) -> bool:
    """Does any requested statistic read `source` ('conv1' / 'conv2') for binary input?"""
    return any(BINARY_INPUT[_base_name(n)] == source for n in tests)


def _statistics(S: np.ndarray, ctx: _Context, pre_converted: dict = None) -> dict:
    """Every requested statistic of one dataset -- the original S, or one
    permutation of it.  This is Figure 4 step 1.2 / step 2.2.1.
    `pre_converted` (conversion_timing='before_shuffle' only) supplies the
    already-permuted Conversion I / II sequences instead of converting S."""
    if ctx.binary:
        bits = S if ctx.one_value is None else (S == ctx.one_value).astype(np.uint8)
        data = {"raw": S, "bits": bits}
        if pre_converted:
            data.update(pre_converted)
        if "conv1" not in data and _needs(ctx.tests, "conv1"):
            data["conv1"] = conversion_I(bits)
        if "conv2" not in data and _needs(ctx.tests, "conv2"):
            data["conv2"] = conversion_II(bits)
        median = 0.5                      # 5.1.5 / 5.1.6: "assumed to be 0.5"
    else:
        median = ctx.median

    out = {}
    C = None                              # the collision list, shared by 5.1.7 and 5.1.8
    for name in ctx.tests:
        x = data[BINARY_INPUT[_base_name(name)]] if ctx.binary else S
        if name == "excursion":
            out[name] = excursion(x)
        elif name == "numDirectionalRuns":
            out[name] = num_directional_runs(x)
        elif name == "lenDirectionalRuns":
            out[name] = len_directional_runs(x)
        elif name == "numIncreasesDecreases":
            out[name] = num_increases_decreases(x)
        elif name == "numRunsMedian":
            out[name] = num_runs_median(x, median)
        elif name == "lenRunsMedian":
            out[name] = len_runs_median(x, median)
        elif name in ("avgCollision", "maxCollision"):
            if C is None:
                C = collision_list(x)
            out[name] = avg_collision(x, C) if name == "avgCollision" else max_collision(x, C)
        elif name.startswith("periodicity("):
            out[name] = periodicity(x, _lag_of(name))
        elif name.startswith("covariance("):
            out[name] = covariance(x, _lag_of(name))
        elif name == "compression":
            out[name] = compression(x, ctx.bz2_level)
        else:
            raise ValueError(f"unknown statistic {name!r}")
    return out


# ==========================================================================
# The shuffle (Figure 5) and the RNG plumbing
# ==========================================================================

def fisher_yates_shuffle(seq, random_integer):
    """
    Figure 5 (PDF p. 38), transcribed line by line:
      "1. for i from L downto 1 do
          a. Generate a random integer j such that 1 <= j <= i.
          b. Swap sj and si"
    `seq` is any mutable sequence (list or 1-D ndarray); the figure's positions
    1..L are indices 0..L-1 here.  `random_integer(i)` must return a uniformly
    distributed integer in [1, i].  Shuffles in place and returns seq.
    """
    L = len(seq)
    for i in range(L, 0, -1):             # for i from L downto 1
        j = random_integer(i)             # 1 <= j <= i
        if not 1 <= j <= i:
            raise ValueError(f"random_integer({i}) returned {j}, outside [1, {i}]")
        seq[j - 1], seq[i - 1] = seq[i - 1], seq[j - 1]   # swap s_j and s_i
    return seq


class PythonFisherYates:
    """An injectable RNG whose .shuffle() is the Figure 5 transcription above,
    drawing j from Python's random.Random (Mersenne Twister; randint is
    unbiased).  Slow -- for tests and small inputs; numpy's Generator.shuffle
    is the production shuffle."""

    def __init__(self, seed=None):
        import random
        self._rand = random.Random(seed)

    def shuffle(self, arr) -> None:
        fisher_yates_shuffle(arr, lambda i: self._rand.randint(1, i))


def _generator_for_shuffle(entropy, j: int) -> np.random.Generator:
    """The RNG stream of shuffle number j (0-based): PCG64 seeded from
    SeedSequence(entropy, spawn_key=(j,)).  Depends only on (entropy, j), so the
    j-th permutation is the same whichever worker computes it."""
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy, spawn_key=(j,))))


# ==========================================================================
# The counting / ranking rule (Figure 4 steps 2.2.2 and 3) -- pure functions
# ==========================================================================

def counter_update(T_original, T_permuted, c0: int, c1: int) -> tuple:
    """Figure 4 step 2.2.2: "If (T > Ti), increment Ci,0.  If (T = Ti),
    increment Ci,1."  Returns the updated (Ci,0, Ci,1).  A nan on either side
    compares False both ways, so an undefined statistic never increments."""
    if T_permuted > T_original:
        return c0 + 1, c1
    if T_permuted == T_original:
        return c0, c1 + 1
    return c0, c1


def cutoffs(shuffles: int = SHUFFLES) -> tuple:
    """The (low, high) counter cutoffs of Figure 4 step 3: (5, 9995) for the
    normative 10 000 shuffles.  For another shuffle count they are scaled in the
    same proportion (5 in 10 000 = 0.0005 per tail, the "type I error
    probability of 0.001" split over the two tails) -- a convenience for short
    test runs, NOT a reading of the standard, which fixes 10 000."""
    shuffles = int(shuffles)
    if shuffles < 1:
        raise ValueError("shuffles must be >= 1")
    low = (5 * shuffles) // SHUFFLES
    return low, shuffles - low


def test_rejects(c0: int, c1: int, shuffles: int = SHUFFLES, rule: str = "figure4") -> bool:
    """Does one test's counter pair reject the IID assumption?
    rule='figure4' (default): step 3's "(Ci,0 + Ci,1 <= 5) or (Ci,0 >= 9995)".
    rule='prose': the p. 38 prose's "less than 5" / "greater than 9995",
    i.e. (Ci,0 + Ci,1 < 5) or (Ci,0 > 9995) -- differs only at equality."""
    low, high = cutoffs(shuffles)
    if rule == "figure4":
        return (c0 + c1 <= low) or (c0 >= high)
    if rule == "prose":
        return (c0 + c1 < low) or (c0 > high)
    raise ValueError("rule must be 'figure4' or 'prose'")


def iid_decision(counters: dict, shuffles: int = SHUFFLES, rule: str = "figure4") -> tuple:
    """Figure 4 step 3 over the whole battery: `counters` maps test name ->
    (Ci,0, Ci,1).  Returns (iid_assumed: bool, passed: {name: bool}).
    "If (...) for any i, reject the IID assumption; else, assume that the noise
    source outputs are IID." """
    passed = {name: not test_rejects(c0, c1, shuffles, rule) for name, (c0, c1) in counters.items()}
    return all(passed.values()), passed


# ==========================================================================
# Figure 4 steps 2 - 2.2.2: the shuffle loop
# ==========================================================================

def _count_range(S: np.ndarray, ctx: _Context, original: dict, j_lo: int, j_hi: int,
                 entropy, rng=None) -> dict:
    """Run shuffles j_lo .. j_hi-1 and return, per statistic, [C0, C1,
    min of T over these permutations, max of T over them]."""
    names = ctx.tests
    c0 = {n: 0 for n in names}
    c1 = {n: 0 for n in names}
    lo = {n: math.inf for n in names}
    hi = {n: -math.inf for n in names}
    work = S.copy()
    # conversion_timing='before_shuffle' (the non-literal reading): the converted
    # sequences are formed once from the ORIGINAL bits and are themselves
    # permuted every iteration, after the bits, by the same RNG stream.
    pre_src = {}
    if ctx.binary and ctx.conversion_timing == "before_shuffle":
        bits = S if ctx.one_value is None else (S == ctx.one_value).astype(np.uint8)
        if _needs(names, "conv1"):
            pre_src["conv1"] = conversion_I(bits)
        if _needs(names, "conv2"):
            pre_src["conv2"] = conversion_II(bits)
    pre_work = {key: arr.copy() for key, arr in pre_src.items()}
    for j in range(j_lo, j_hi):
        g = rng if rng is not None else _generator_for_shuffle(entropy, j)
        work[:] = S                      # 2.1 "Permute S": a fresh Fisher-Yates permutation of the input
        g.shuffle(work)                  #     (a uniform permutation whatever the start, so chained
        for key in pre_work:             #     and fresh shuffles have the same distribution)
            pre_work[key][:] = pre_src[key]
            g.shuffle(pre_work[key])
        T = _statistics(work, ctx, pre_work)
        for n in names:                  # 2.2.2
            c0[n], c1[n] = counter_update(original[n], T[n], c0[n], c1[n])
            t = T[n]
            if t == t:                   # not nan
                lo[n] = min(lo[n], t)
                hi[n] = max(hi[n], t)
    return {n: [c0[n], c1[n], lo[n], hi[n]] for n in names}


def _worker(task):
    """multiprocessing entry point: unpack, run a range of shuffles."""
    S_bytes, dtype, ctx, original, j_lo, j_hi, entropy = task
    S = np.frombuffer(S_bytes, dtype=dtype)
    return _count_range(S, ctx, original, j_lo, j_hi, entropy)


def _split(n: int, parts: int):
    """Contiguous ranges [lo, hi) covering 0..n-1 in `parts` pieces."""
    edges = [round(n * t / parts) for t in range(parts + 1)]
    return [(edges[t], edges[t + 1]) for t in range(parts) if edges[t + 1] > edges[t]]


# ==========================================================================
# The procedure (Figure 4) end to end
# ==========================================================================

def permutation_test(symbols, bits_per_symbol, shuffles: int = SHUFFLES, rng=None, *,
                     seed=None, workers: int = 1, binary_mode: str = "alphabet",
                     median_rule: str = "mean", bz2_level: int = BZ2_LEVEL,
                     counter_rule: str = "figure4", conversion_timing: str = "after_shuffle",
                     tests=None, validate: bool = True) -> dict:
    """
    Section 5.1 permutation testing of S (Figure 4), returning the counters,
    the per-test outcome and the decision.

    symbols, bits_per_symbol : the dataset and its declared width.
    shuffles     : Figure 4 says 10 000; smaller values are for quick runs
                   (cutoffs() then scales the thresholds -- see its docstring).
    rng          : an object with an in-place .shuffle(ndarray) that is a
                   correct Fisher-Yates (e.g. np.random.default_rng(seed), or
                   PythonFisherYates(seed) for the literal Figure 5).  When
                   given, the shuffles run in this process, in order.
    seed         : with rng=None, the SeedSequence entropy; None draws fresh OS
                   entropy, and the value used is reported as 'seed_entropy'.
    workers      : processes to spread the shuffles over (rng=None only); the
                   result does not depend on it.  Default 1.
    binary_mode  : 'alphabet' (literal: binary iff k = 2 distinct values are
                   observed), 'width' (binary iff bits_per_symbol == 1), or
                   'never' (apply no conversion whatever the data).
    median_rule  : 'mean' | 'lower' | 'upper' -- see median_of().
    bz2_level    : bzip2 block-size level for 5.1.11 (1..9; default 9).
    counter_rule : 'figure4' (default) | 'prose' -- see test_rejects().
    conversion_timing : binary input only.  'after_shuffle' (default, literal
                   Figure 4): the bits are permuted and Conversion I / II is
                   applied to the permuted bits inside each statistic.
                   'before_shuffle': the Conversion I / II sequences are formed
                   once and are themselves permuted each iteration.  The two
                   readings give different null distributions; see the module
                   docstring.
    tests        : an iterable of statistic names to run (default: all 19).
    validate     : check every symbol lies in [0, 2**bits_per_symbol).
    """
    bps = int(bits_per_symbol)
    if bps < 1:
        raise ValueError("bits_per_symbol must be >= 1")
    shuffles = int(shuffles)
    if shuffles < 1:
        raise ValueError("shuffles must be >= 1")
    workers = int(workers)
    if workers < 1:
        raise ValueError("workers must be >= 1")
    if rng is not None and workers != 1:
        raise ValueError("an injected rng is a single stream; use workers=1 with it")
    if binary_mode not in ("alphabet", "width", "never"):
        raise ValueError("binary_mode must be 'alphabet', 'width' or 'never'")
    median_of([0], median_rule)                      # validates the rule name
    if conversion_timing not in ("after_shuffle", "before_shuffle"):
        raise ValueError("conversion_timing must be 'after_shuffle' or 'before_shuffle'")
    test_rejects(0, 0, shuffles, counter_rule)       # validates the rule name
    if not 1 <= int(bz2_level) <= 9:
        raise ValueError("bz2_level must be in 1..9")

    all_names = statistic_names()
    if tests is None:
        names = all_names
    else:
        names = tuple(tests)
        unknown = [n for n in names if n not in all_names]
        if unknown or len(set(names)) != len(names):
            raise ValueError(f"unknown or repeated test name(s): {unknown or 'repeated'}")

    S = _as_symbol_array(symbols, bps, validate)
    L = int(S.size)
    k = _distinct_count(S)

    # "when the input is binary, i.e., k = 2"
    if binary_mode == "alphabet":
        binary = (k == 2)
    elif binary_mode == "width":
        binary = (bps == 1)
    else:
        binary = False
    one_value = None
    if binary:
        values = np.unique(S)
        if not (values.size <= 2 and set(values.tolist()) <= {0, 1}):
            one_value = int(values.max())            # smaller value -> 0, larger -> 1
    median = NAN if binary else median_of(S, median_rule)

    ctx = _Context(binary=binary, one_value=one_value, median=median,
                   bz2_level=int(bz2_level), tests=names, conversion_timing=conversion_timing)

    # Step 1: counters to zero (in _count_range), Ti on S:
    original = _statistics(S, ctx)

    # Step 2: the shuffles.
    if rng is not None:
        entropy = None
        counted = _count_range(S, ctx, original, 0, shuffles, None, rng=rng)
    else:
        entropy = np.random.SeedSequence(seed).entropy
        if workers == 1 or shuffles < 2 * workers:
            counted = _count_range(S, ctx, original, 0, shuffles, entropy)
        else:
            tasks = [(S.tobytes(), S.dtype.str, ctx, original, lo, hi, entropy)
                     for lo, hi in _split(shuffles, workers)]
            with multiprocessing.get_context().Pool(workers) as pool:
                parts = pool.map(_worker, tasks)
            counted = {}
            for n in names:
                c0 = sum(p[n][0] for p in parts)
                c1 = sum(p[n][1] for p in parts)
                lo = min(p[n][2] for p in parts)
                hi = max(p[n][3] for p in parts)
                counted[n] = [c0, c1, lo, hi]

    # Step 3: the decision.
    counters = {n: (counted[n][0], counted[n][1]) for n in names}
    iid, passed = iid_decision(counters, shuffles, counter_rule)
    low, high = cutoffs(shuffles)

    def _py(v):
        """Python scalars for JSON."""
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return float(v)
        return v

    tests_out = {}
    for n in names:
        T = _py(original[n])
        c0, c1, lo, hi = counted[n]
        tests_out[n] = {
            "T": T,
            "C0": int(c0),
            "C1": int(c1),
            "passed": bool(passed[n]),
            "defined": bool(T == T),                     # False for nan
            "perm_min": _py(lo) if lo != math.inf else NAN,
            "perm_max": _py(hi) if hi != -math.inf else NAN,
        }

    result = {
        "min_entropy": NAN,                 # section 5.1 gives a decision, not a figure
        "iid_assumption": bool(iid),
        "L": L,
        "bits_per_symbol": bps,
        "k": k,
        "binary": bool(binary),
        "binary_mode": binary_mode,
        "bit_one_value": one_value,
        "median": _py(median),
        "median_rule": median_rule if not binary else "assumed 0.5 (binary)",
        "conversion_I_blocks": int(math.ceil(L / 8)) if binary else None,
        "conversion_timing": conversion_timing if binary else None,
        "shuffles": shuffles,
        "cutoffs": [low, high],
        "counter_rule": counter_rule,
        "rng": "injected" if rng is not None else "numpy PCG64 per shuffle (SeedSequence(seed_entropy, spawn_key=(j,)))",
        "seed_entropy": int(entropy) if entropy is not None else None,
        "bz2_level": int(bz2_level),
        "failed_tests": [n for n in names if not passed[n]],
        "undefined_statistics": [n for n in names if not tests_out[n]["defined"]],
        "tests": tests_out,
    }
    # Flattened: every original statistic under its own name, for label matching.
    for n in names:
        result[n] = tests_out[n]["T"]
    return result


def estimate(symbols, bits_per_symbol, **options) -> dict:
    """
    The driver-contract entry point: section 5.1 permutation testing.

    Options are those of permutation_test() plus
        track     : 'literal' (default) -> test the symbols as given
                    'bitstring'         -> expand each symbol to bits_per_symbol
                                           bits MSB-first and test the 1-bit symbols
        bit_order : 'msb' (default) | 'lsb' for track='bitstring'
    Returns permutation_test()'s dict; 'min_entropy' is nan because section 5.1
    yields a decision on the IID assumption and no entropy figure.
    """
    opts = dict(options)
    track = opts.pop("track", "literal")
    bit_order = opts.pop("bit_order", "msb")
    bps = int(bits_per_symbol)
    if track == "literal":
        S, bps_used = symbols, bps
    elif track == "bitstring":
        S, bps_used = to_bitstring(symbols, bps, bit_order), 1
    else:
        raise ValueError("track must be 'literal' or 'bitstring'")
    result = permutation_test(S, bps_used, **opts)
    result["track"] = track
    result["declared_bits_per_symbol"] = bps
    return result


# ==========================================================================
# Command line
# ==========================================================================

USAGE = """usage: python permutation.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                 [--shuffles N] [--seed N] [--workers W] [--binary-mode alphabet|width|never]
                 [--median-rule mean|lower|upper] [--counter-rule figure4|prose]
                 [--conversion-timing after_shuffle|before_shuffle]
                 [--bz2-level 1..9] [--tests name,name,...] [--lsb-first]

  rawfile          one symbol per byte; the low <bits_per_symbol> bits are the symbol
  bits_per_symbol  1..8 for this byte-per-symbol file format
  --literal        (default) test the symbols as read
  --bitstring      expand each symbol to <bits_per_symbol> bits, MSB-first, and test the bits
  --shuffles N     Figure 4 says 10000 (the default); smaller for quick runs
  --seed N         SeedSequence entropy for the per-shuffle PCG64 streams (default: fresh,
                   reported in the output as seed_entropy)
  --workers W      processes to spread the shuffles over (default 1; result independent of W)
  --binary-mode    'alphabet' (default: binary iff k = 2), 'width' (iff bits_per_symbol = 1), 'never'
  --median-rule    even-length median: 'mean' (default), 'lower', 'upper'
  --counter-rule   'figure4' (default: <= 5, >= 9995) or 'prose' (< 5, > 9995)
  --conversion-timing  binary input: 'after_shuffle' (default: shuffle the bits, then apply
                   Conversion I/II) or 'before_shuffle' (shuffle the converted sequences)
  --bz2-level      bzip2 block-size level for 5.1.11 (default 9)
  --tests          comma-separated statistic names (default: all 19)
  --lsb-first      with --bitstring: LSB-first bit order within each symbol
Prints the result dict as JSON on stdout (NaN as the JSON-extension token NaN).
"""


def _parse_args(argv):
    positional = []
    opts = {"track": "literal", "bit_order": "msb"}
    i = 0

    def take():
        nonlocal i
        i += 1
        if i >= len(argv):
            raise SystemExit(USAGE)
        return argv[i]

    while i < len(argv):
        a = argv[i]
        if a == "--literal":
            opts["track"] = "literal"
        elif a == "--bitstring":
            opts["track"] = "bitstring"
        elif a == "--lsb-first":
            opts["bit_order"] = "lsb"
        elif a == "--shuffles":
            opts["shuffles"] = int(take())
        elif a == "--seed":
            opts["seed"] = int(take())
        elif a == "--workers":
            opts["workers"] = int(take())
        elif a == "--binary-mode":
            opts["binary_mode"] = take()
        elif a == "--median-rule":
            opts["median_rule"] = take()
        elif a == "--counter-rule":
            opts["counter_rule"] = take()
        elif a == "--conversion-timing":
            opts["conversion_timing"] = take()
        elif a == "--bz2-level":
            opts["bz2_level"] = int(take())
        elif a == "--tests":
            opts["tests"] = tuple(t for t in take().split(",") if t)
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
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
