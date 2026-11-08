"""SP 800-90B section 6.3.3 -- The Markov Estimate.  Independent reference.

Written from the text of NIST SP 800-90B (January 2018), section 6.3.3
(PDF pp. 51-53), WITHOUT reading the C++ implementation.  The only thing
taken from the C++ is the spelling of the verbose-mode labels, so that a
differential driver can match the intermediates by name:

    P_0  P_1  P_{0,0}  P_{0,1}  P_{1,0}  P_{1,1}  p-hat_max  min_entropy

The spec, quoted (SP 800-90B section 6.3.3, PDF p. 51-52):

  "This entropy estimation method is only applied to binary inputs.
   Given the input S = (s1, ..., sL), where si in A = {0,1},
   1. Estimate the initial probabilities for each output value,
        P_0 = #{0 in S} / L   and   P_1 = 1 - P_0.
   2. Let T be the 2x2 transition matrix ... where the probabilities are
      calculated as
        P_{0,0} = #{00 in S} / (#{00 in S} + #{01 in S}),
        P_{0,1} = #{01 in S} / (#{00 in S} + #{01 in S}),
        P_{1,0} = #{10 in S} / (#{10 in S} + #{11 in S}),  and
        P_{1,1} = #{11 in S} / (#{10 in S} + #{11 in S}).
   3. Find the probability of the most likely sequence of outputs of
      length 128, as calculated below.
        Sequence    Probability
        00...0      P_0 x P_{0,0}^127
        0101...01   P_0 x P_{0,1}^64 x P_{1,0}^63
        011...1     P_0 x P_{0,1} x P_{1,1}^126
        100...0     P_1 x P_{1,0} x P_{0,0}^126
        1010...10   P_1 x P_{1,0}^64 x P_{0,1}^63
        11...1      P_1 x P_{1,1}^127
   4. Let p-hat_max be the maximum of the probabilities in the table given
      above.  The min-entropy estimate is the negative logarithm of the
      probability of the most likely sequence of outputs, p-hat_max:
        min-entropy = min( -log2(p-hat_max) / 128, 1 )."

Readings fixed by the spec's own worked example (PDF p. 52-53, L = 40):
  * "#{00 in S}" counts OVERLAPPING adjacent pairs (s_i, s_{i+1}),
    i = 1..L-1.  The example gives P_{0,0} = 0.389 = 7/18; counting
    non-overlapping pairs would give 4/9 = 0.444.  See the tests.
  * P_0 is #{0}/L over all L samples (19/40 = 0.475 in the example).

Where the spec gives NO value:
  * A transition probability whose denominator is 0 (a state that never
    precedes another sample) is 0/0.  It is reported as NaN, exactly as the
    spec leaves it.  What that does to the six-row table and to p-hat_max
    is controlled by the ``undefined_transition`` option; see estimate().
  * The January 2018 text has NO confidence adjustment on P_0 or on the
    transition probabilities (no epsilon term).  None is implemented.

Everything is computed in the log2 domain so that a 127th power cannot
underflow; the probabilities themselves are reported as 2**log2 (which may
read as 0.0 when the true value is below the double range -- the log2
values are reported alongside).
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np

# section 6.3.3 step 3: "the most likely sequence of outputs of length 128"
SEQUENCE_LENGTH = 128

# The six rows of the step-3 table, in the spec's order.  Each row is
# (name, initial-probability label, [(transition label, exponent), ...]).
# The exponents in every row add up to SEQUENCE_LENGTH - 1 = 127 transitions.
SEQUENCE_TABLE = (
    ("00...0",    "P_0", (("P_{0,0}", 127),)),
    ("0101...01", "P_0", (("P_{0,1}", 64), ("P_{1,0}", 63))),
    ("011...1",   "P_0", (("P_{0,1}", 1),  ("P_{1,1}", 126))),
    ("100...0",   "P_1", (("P_{1,0}", 1),  ("P_{0,0}", 126))),
    ("1010...10", "P_1", (("P_{1,0}", 64), ("P_{0,1}", 63))),
    ("11...1",    "P_1", (("P_{1,1}", 127),)),
)

UNDEFINED_TRANSITION_VARIANTS = ("bounds", "nan", "one", "zero")
BINARY_BY_VARIANTS = ("alphabet", "values")

NAN = float("nan")


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------

def _as_symbol_array(symbols, bits_per_symbol: int) -> np.ndarray:
    """Validate and return the symbols as a 1-D numpy integer array."""
    if not isinstance(bits_per_symbol, (int, np.integer)) or bits_per_symbol < 1:
        raise ValueError(f"bits_per_symbol must be a positive int, got {bits_per_symbol!r}")
    arr = np.asarray(symbols)
    if arr.dtype == np.bool_:
        arr = arr.astype(np.int64)
    if arr.size and not np.issubdtype(arr.dtype, np.integer):
        raise TypeError(f"symbols must be integers, got dtype {arr.dtype}")
    if arr.ndim != 1:
        arr = arr.ravel()
    if arr.size:
        lo, hi = int(arr.min()), int(arr.max())
        if lo < 0 or hi >= (1 << bits_per_symbol):
            raise ValueError(
                f"symbols must lie in [0, 2**{bits_per_symbol}); observed range [{lo}, {hi}]")
    return arr


def to_bitstring(symbols, bits_per_symbol: int) -> np.ndarray:
    """Section 3.1.3 (PDF p. 20): 'the sequential dataset that contains L
    samples (each having n bits) is considered as a bitstring of size nL'.

    Each symbol is expanded to ``bits_per_symbol`` bits, most-significant
    bit first, and the expansions are concatenated in sample order.
    (The standard does not fix the bit order inside a sample; MSB-first is
    the convention this reference uses, as the task contract specifies.)
    """
    arr = _as_symbol_array(symbols, bits_per_symbol)
    if bits_per_symbol == 1:
        return arr.astype(np.uint8)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.uint32)   # MSB first
    bits = (arr.astype(np.uint32)[:, None] >> shifts) & 1
    return bits.astype(np.uint8).ravel()


def _translate_to_binary(arr: np.ndarray, binary_by: str):
    """Decide whether the input is 'binary' for section 6.2/6.3.3 and map it
    onto {0,1}.

    Returns (bits_or_None, info) where info records the decision.

    binary_by='values'   -- the literal section 6.3.3 reading: applicable only
                            when every sample is already 0 or 1
                            ("si in A = {0,1}", PDF p. 51).
    binary_by='alphabet' -- the standard's own definition of a binary source:
                            section 4.4.2 (PDF p. 34) "the noise source
                            produces only two distinct values" and section 5
                            (PDF p. 38) "when the input is binary, i.e.,
                            k = 2".  Applicable when at most two distinct
                            values occur; values not already in {0,1} are
                            mapped onto 0/1 in increasing order.  (The
                            estimate is invariant under relabelling 0<->1:
                            the six-row table is symmetric.)
    """
    if binary_by not in BINARY_BY_VARIANTS:
        raise ValueError(f"binary_by must be one of {BINARY_BY_VARIANTS}, got {binary_by!r}")
    distinct = np.unique(arr)
    info = {"distinct_values": [int(v) for v in distinct],
            "binary_by": binary_by, "translated": False, "translation": None}
    already_binary = distinct.size == 0 or (distinct.size <= 2 and int(distinct.max()) <= 1)
    if already_binary:
        return arr.astype(np.uint8), info
    if binary_by == "values":
        info["reason"] = "section 6.3.3 requires si in {0,1}; other values observed"
        return None, info
    if distinct.size > 2:
        info["reason"] = (f"{distinct.size} distinct values: not a binary input "
                          "(section 6.2: 'only applied to binary inputs')")
        return None, info
    mapping = {int(v): i for i, v in enumerate(distinct)}      # increasing order -> 0, 1
    info["translated"] = True
    info["translation"] = {str(k): v for k, v in mapping.items()}
    bits = np.zeros(arr.shape, dtype=np.uint8)
    for value, bit in mapping.items():
        bits[arr == value] = bit
    return bits, info


# ---------------------------------------------------------------------------
# The estimator, step by step
# ---------------------------------------------------------------------------

def count_symbols(bits: np.ndarray) -> dict:
    """#{0 in S}, #{1 in S}, and L."""
    L = int(bits.size)
    n0 = int(np.count_nonzero(bits == 0))
    return {"L": L, "#{0 in S}": n0, "#{1 in S}": L - n0}


def count_transitions(bits: np.ndarray) -> dict:
    """#{00 in S}, #{01 in S}, #{10 in S}, #{11 in S}: overlapping adjacent
    pairs (s_i, s_{i+1}) for i = 1..L-1 (the reading the worked example
    fixes; see module docstring)."""
    if bits.size < 2:
        return {"#{00 in S}": 0, "#{01 in S}": 0, "#{10 in S}": 0, "#{11 in S}": 0}
    pair_codes = bits[:-1].astype(np.uint8) * 2 + bits[1:].astype(np.uint8)   # 0b(s_i s_{i+1})
    n = np.bincount(pair_codes, minlength=4)
    return {"#{00 in S}": int(n[0]), "#{01 in S}": int(n[1]),
            "#{10 in S}": int(n[2]), "#{11 in S}": int(n[3])}


def _ratio(numerator: int, denominator: int) -> float:
    """a/b as the spec writes it; NaN where the spec gives no value (0/0)."""
    if denominator == 0:
        return NAN
    return numerator / denominator


def initial_probabilities(counts: dict) -> dict:
    """Step 1: P_0 = #{0 in S} / L and P_1 = 1 - P_0 (literally 1 - P_0,
    not #{1 in S}/L -- the two can differ in the last binary digit)."""
    P_0 = _ratio(counts["#{0 in S}"], counts["L"])
    return {"P_0": P_0, "P_1": 1.0 - P_0}


def transition_probabilities(tcounts: dict) -> dict:
    """Step 2: the 2x2 transition matrix T, entry by entry as the spec writes it."""
    from0 = tcounts["#{00 in S}"] + tcounts["#{01 in S}"]
    from1 = tcounts["#{10 in S}"] + tcounts["#{11 in S}"]
    return {
        "P_{0,0}": _ratio(tcounts["#{00 in S}"], from0),
        "P_{0,1}": _ratio(tcounts["#{01 in S}"], from0),
        "P_{1,0}": _ratio(tcounts["#{10 in S}"], from1),
        "P_{1,1}": _ratio(tcounts["#{11 in S}"], from1),
    }


def _log2(p: float) -> float:
    """log2 with the IEEE conventions this module relies on:
    log2(0) = -inf (an impossible transition), log2(NaN) = NaN."""
    if math.isnan(p):
        return NAN
    if p == 0.0:
        return -math.inf
    return math.log2(p)


def sequence_log2_probabilities(probs: dict, undefined_value: float | None = None) -> dict:
    """Step 3: log2 of each of the six row probabilities.

    ``probs`` holds P_0, P_1 and the four transition probabilities.
    ``undefined_value`` -- what to substitute for a NaN (0/0) transition
    probability before taking the product: None propagates the NaN
    (the literal reading: the spec gives no value, so the row has none);
    0.0 and 1.0 give the two ends of the interval a probability can lie in.

    Products are sums of logs, so a zero factor with a positive exponent
    gives -inf (probability 0) and never silently underflows.
    """
    out = {}
    for name, initial, transitions in SEQUENCE_TABLE:
        log2_p = _log2(probs[initial])
        for label, exponent in transitions:
            p = probs[label]
            if math.isnan(p) and undefined_value is not None:
                p = undefined_value
            log2_p += exponent * _log2(p)
        out[name] = log2_p
    return out


def _max_log2(rows: dict) -> float:
    """Step 4, first half: p-hat_max (as log2).  NaN if any row has no value."""
    values = list(rows.values())
    if any(math.isnan(v) for v in values):
        return NAN
    return max(values)


def min_entropy_from_log2_pmax(log2_pmax: float) -> float:
    """Step 4: min-entropy = min( -log2(p-hat_max) / 128, 1 )."""
    if math.isnan(log2_pmax):
        return NAN
    # -log2(0) = +inf -> min(+inf/128, 1) = 1, exactly as the formula reads.
    # "+ 0.0" only turns the -0.0 that -log2(1)/128 produces into 0.0.
    return min(-log2_pmax / SEQUENCE_LENGTH, 1.0) + 0.0


def _pow2(log2_p: float) -> float:
    if math.isnan(log2_p):
        return NAN
    if log2_p == -math.inf:
        return 0.0
    try:
        return 2.0 ** log2_p
    except OverflowError:          # cannot happen for log2 of a probability, kept for safety
        return math.inf


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _not_applicable(result: dict) -> dict:
    result.update({
        "P_0": NAN, "P_1": NAN,
        "P_{0,0}": NAN, "P_{0,1}": NAN, "P_{1,0}": NAN, "P_{1,1}": NAN,
        "p-hat_max": NAN, "min_entropy": NAN,
        "p-hat_max_lower": NAN, "p-hat_max_upper": NAN,
        "min_entropy_lower": NAN, "min_entropy_upper": NAN,
    })
    return result


def estimate(symbols, bits_per_symbol, *,
             bitstring: bool = False,
             bitstring_limit: int | None = None,
             undefined_transition: str = "bounds",
             binary_by: str = "alphabet") -> dict:
    """The Markov estimate of SP 800-90B section 6.3.3.

    symbols          -- ints in [0, 2**bits_per_symbol).
    bitstring        -- if True, first expand every symbol to bits_per_symbol
                        bits MSB-first and assess the result as 1-bit symbols
                        (section 3.1.3, 'H_bitstring').
    bitstring_limit  -- section 3.1.3 says "The bits after the first
                        1 000 000 bits MAY be ignored".  None (default) keeps
                        every bit; an int keeps only the first that many.
    undefined_transition -- how a 0/0 transition probability (reported as
                        NaN in P_{x,y}) enters the step-3 table:
          'bounds' (default): substitute 0 and 1 to get the interval
                   [p-hat_max_lower, p-hat_max_upper] every probability must
                   lie in.  If the two ends coincide the value is determined
                   and reported; otherwise 'p-hat_max' and 'min_entropy' are
                   NaN (the spec gives no value) and the bounds are reported.
          'nan'  : literal IEEE propagation -- any row touching the undefined
                   entry has no value, so neither does the maximum.
          'one'  : substitute 1 (largest p-hat_max, i.e. the LOWEST
                   min-entropy: the conservative end).
          'zero' : substitute 0 (the other end).
        In every variant the undefined P_{x,y} entries themselves are NaN.
    binary_by        -- 'alphabet' (default) or 'values'; see _translate_to_binary.

    Returns a dict with 'min_entropy' and the intermediates under the C++
    verbose-label names (P_0, P_1, P_{0,0}, P_{0,1}, P_{1,0}, P_{1,1},
    p-hat_max), plus the counts, the six sequence probabilities, and the
    bounds.  NaN wherever the spec gives no value.
    """
    if undefined_transition not in UNDEFINED_TRANSITION_VARIANTS:
        raise ValueError(f"undefined_transition must be one of "
                         f"{UNDEFINED_TRANSITION_VARIANTS}, got {undefined_transition!r}")
    arr = _as_symbol_array(symbols, bits_per_symbol)

    result = {
        "estimator": "Markov",
        "spec": "SP 800-90B section 6.3.3 (PDF p. 51-53)",
        "input_symbols": int(arr.size),
        "bits_per_symbol": int(bits_per_symbol),
        "mode": "bitstring" if bitstring else "literal",
        "bitstring_limit": bitstring_limit,
        "undefined_transition": undefined_transition,
        "sequence_length": SEQUENCE_LENGTH,
    }

    if bitstring:
        bits = to_bitstring(arr, bits_per_symbol)
        if bitstring_limit is not None:
            bits = bits[:int(bitstring_limit)]
        binfo = {"distinct_values": [int(v) for v in np.unique(bits)],
                 "binary_by": "bitstring", "translated": False, "translation": None}
    else:
        bits, binfo = _translate_to_binary(arr, binary_by)
    result.update(binfo)

    if bits is None:
        result["applicable"] = False
        return _not_applicable(result)
    result["applicable"] = True

    # Step 1
    counts = count_symbols(bits)
    result.update(counts)
    probs = initial_probabilities(counts)
    # Step 2
    tcounts = count_transitions(bits)
    result.update(tcounts)
    probs.update(transition_probabilities(tcounts))
    result.update(probs)

    # Step 3: the six rows -- literal (NaN propagating) and the two bounds.
    rows_literal = sequence_log2_probabilities(probs, undefined_value=None)
    rows_lower = sequence_log2_probabilities(probs, undefined_value=0.0)
    rows_upper = sequence_log2_probabilities(probs, undefined_value=1.0)

    # Step 4
    log2_pmax_literal = _max_log2(rows_literal)
    log2_pmax_lower = _max_log2(rows_lower)
    log2_pmax_upper = _max_log2(rows_upper)

    if undefined_transition == "nan":
        log2_pmax = log2_pmax_literal
    elif undefined_transition == "one":
        log2_pmax = log2_pmax_upper
    elif undefined_transition == "zero":
        log2_pmax = log2_pmax_lower
    else:  # 'bounds'
        log2_pmax = log2_pmax_upper if log2_pmax_lower == log2_pmax_upper else NAN

    result["sequence_log2_probabilities"] = rows_literal
    result["sequence_probabilities"] = {k: _pow2(v) for k, v in rows_literal.items()}
    result["sequence_log2_probabilities_lower"] = rows_lower
    result["sequence_log2_probabilities_upper"] = rows_upper
    result["undefined_transitions_present"] = any(
        math.isnan(probs[k]) for k in ("P_{0,0}", "P_{0,1}", "P_{1,0}", "P_{1,1}"))

    result["log2 p-hat_max"] = log2_pmax
    result["p-hat_max"] = _pow2(log2_pmax)
    result["min_entropy"] = min_entropy_from_log2_pmax(log2_pmax)
    # The interval (always reported).  Note the inversion: the LARGER
    # p-hat_max gives the SMALLER min-entropy.
    result["p-hat_max_lower"] = _pow2(log2_pmax_lower)
    result["p-hat_max_upper"] = _pow2(log2_pmax_upper)
    result["min_entropy_lower"] = min_entropy_from_log2_pmax(log2_pmax_upper)
    result["min_entropy_upper"] = min_entropy_from_log2_pmax(log2_pmax_lower)
    return result


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

USAGE = """usage: python markov.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                        [--bitstring-limit N] [--undefined bounds|nan|one|zero]
                        [--binary-by alphabet|values]

rawfile: one symbol per byte; the low <bits_per_symbol> bits of each byte are
the symbol (higher bits are masked off and counted in 'out_of_width_bytes').
--literal  (default) assess the symbols as they are (section 6.3.3 applies
           only to binary inputs; a non-binary file yields NaN).
--bitstring expand every symbol to <bits_per_symbol> bits MSB-first and
           assess the concatenation as 1-bit symbols (section 3.1.3).
Prints the estimate() dict as JSON on stdout.
"""


def _parse_args(argv):
    opts = {"bitstring": False, "bitstring_limit": None,
            "undefined_transition": "bounds", "binary_by": "alphabet"}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--literal":
            opts["bitstring"] = False
        elif a == "--bitstring":
            opts["bitstring"] = True
        elif a == "--bitstring-limit":
            i += 1
            opts["bitstring_limit"] = int(argv[i])
        elif a == "--undefined":
            i += 1
            opts["undefined_transition"] = argv[i]
        elif a == "--binary-by":
            i += 1
            opts["binary_by"] = argv[i]
        elif a in ("-h", "--help"):
            sys.stdout.write(USAGE)
            sys.exit(0)
        elif a.startswith("--"):
            raise SystemExit(f"unknown option {a!r}\n{USAGE}")
        else:
            positional.append(a)
        i += 1
    if len(positional) != 2:
        raise SystemExit(USAGE)
    path, bps = positional[0], int(positional[1])
    if not 1 <= bps <= 8:
        raise SystemExit("bits_per_symbol must be in 1..8 for a one-symbol-per-byte file")
    return path, bps, opts


def main(argv=None) -> int:
    path, bps, opts = _parse_args(sys.argv[1:] if argv is None else argv)
    raw = np.fromfile(path, dtype=np.uint8)
    mask = (1 << bps) - 1
    out_of_width = int(np.count_nonzero(raw > mask))
    symbols = raw & mask
    result = estimate(symbols, bps, **opts)
    result["file"] = path
    result["bytes_read"] = int(raw.size)
    result["out_of_width_bytes"] = out_of_width
    json.dump(result, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
