"""
py90b.mcv -- SP 800-90B section 6.3.1, The Most Common Value Estimate.

INDEPENDENT reference implementation, written FROM THE STANDARD'S TEXT ONLY
(NIST SP 800-90B, January 2018, as extracted to reference/sp800-90b.pages.txt).
No file under cpp/ was opened while writing this.  The only thing taken from the
C++ tool is the NAMES of the intermediate quantities it prints in verbose mode
("Mode count", "p-hat", "p_u", "min entropy"), so a differential driver can
match them.

Spec text relied on -- SP 800-90B section 6.3.1 (PDF p. 49):

    "This method first finds the proportion p-hat of the most common value in
     the input dataset, and then constructs a confidence interval for this
     proportion.  The upper bound of the confidence interval is used to
     estimate the min-entropy per sample of the source.

     Given the input S = (s1, ..., sL), where si in A = {x1, ..., xk},

       1. Find the proportion of the most common value p-hat in the dataset,
          i.e.,   p-hat = max_i  #{x_i in S} / L .

       2. Calculate an upper bound on the probability of the most common
          value p_u as
              p_u = min( 1,  p-hat + 2.576 * sqrt( p-hat (1 - p-hat) / (L - 1) ) ),
          where 2.576 corresponds to the Z_(1-0.005) value.

       3. The estimated min-entropy is -log2(p_u)."

So the ONLY clamp the section prescribes is  min(1, ...)  on p_u, i.e. the
upper confidence bound is capped at probability 1, which caps the estimate
below at 0 bits.  There is NO clamp of the estimate to bits_per_symbol in
section 6.3.1, and none is needed: the most common value occurs at least
L/k times, so p-hat >= 1/k, p_u >= p-hat >= 1/k, and -log2(p_u) <= log2(k)
<= bits_per_symbol automatically.

Worked example -- section 6.3.1 (PDF p. 50):

    "If the dataset is S = (0, 1, 1, 2, 0, 1, 2, 2, 0, 1, 0, 1, 1, 0, 2, 2,
     1, 0, 2, 1), with L = 20, the most common value is 1, with p-hat = 0.4.
     p_u = 0.4 + 2.576 sqrt(0.012) = 0.6895.  The min-entropy estimate is
     -log2(0.6822) = 0.5363."

ERRATUM in that example (recorded, not fudged -- see tests/test_mcv.py):
    the formula gives p-hat(1-p-hat)/(L-1) = 0.24/19 = 0.012632, not 0.012;
    0.012 = 0.24/20 is a division by L.  0.4 + 2.576*sqrt(0.24/20) = 0.6822 is
    the text's log argument, and -log2(0.6822) = 0.5517, NOT 0.5363.  The
    printed FINAL figures 0.6895 and 0.5363 = -log2(0.6895) do follow the
    formula with L-1.  This module implements the formula as printed in step 2
    (L-1), which reproduces the example's final figures.

The constant.  Step 2 prints 2.576 and says it "corresponds to the
Z_(1-0.005) value".  The exact 0.995 standard-normal quantile is
2.5758293035489...  The two give different results (about 2e-4 relative on
the half-width).  The literal reading -- the number printed -- is the default
here; variant='exact_quantile' uses Phi^-1(0.995) computed from the standard
library, for drivers that want to separate "constant rounding" from every
other difference.  (The fork documents its own use of the exact quantile as
D-1 / C22c in FORK-DIVERGENCE-AND-TRUST.md; that is a documented divergence,
not a defect, and this module takes no position on it beyond exposing both.)

Bitstring track.  Section 3.1.3 (PDF p. 20): "If the sequential dataset is not
binary, an additional entropy estimation (per bit), denoted H_bitstring, is
estimated.  First, the sequential dataset that contains L samples (each having
n bits) is considered as a bitstring of size nL.  The bits after the first
1 000 000 bits may be ignored."  The standard does not fix the order of bits
within a sample (the 2026-09-30 tracker's F21 records this); MSB-first is the
convention this audit uses, and LSB-first is exposed as an option so both
readings are available.  The optional truncation ("may be ignored") is OFF
unless bitstring_limit is given.

API (contract for the differential driver):

    estimate(symbols, bits_per_symbol, **options) -> dict
        symbols: a sequence / np.ndarray / bytes of ints in [0, 2**bits_per_symbol)
        returns {'min_entropy': float, 'Mode count': int, 'p-hat': float,
                 'p_u': float, 'min entropy': float, ...extras...}
        float('nan') wherever the spec gives no value (L < 2).

    python mcv.py <rawfile> <bits_per_symbol> [--literal|--bitstring] [options]
        rawfile: one symbol per byte, the low bits_per_symbol bits are the symbol.
        Prints the dict as JSON (NaN is printed as the JSON-extension token NaN,
        which Python's json.loads accepts).

Pure Python + numpy.  Vectorised where the spec's algorithm allows (counting);
the arithmetic of steps 2 and 3 is done in plain binary64 Python floats, in
exactly the order the formula is printed, so a reader can check it line by line.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys

import numpy as np

# --------------------------------------------------------------------------
# The confidence constant of section 6.3.1 step 2.
# --------------------------------------------------------------------------

#: The constant exactly as PRINTED in section 6.3.1 step 2 (PDF p. 49).
Z_LITERAL = 2.576

#: What the text says that constant "corresponds to": the Z_(1-0.005) value,
#: i.e. the 0.995 quantile of the standard normal distribution, computed here
#: from the Python standard library (Wichura's AS241 algorithm, accurate to
#: ~1e-16) rather than copied from anywhere.  Value: 2.5758293035489...
Z_EXACT_QUANTILE = statistics.NormalDist().inv_cdf(1.0 - 0.005)

VARIANTS = {
    "literal": Z_LITERAL,
    "exact_quantile": Z_EXACT_QUANTILE,
}

NAN = float("nan")


# --------------------------------------------------------------------------
# Input handling
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


def _as_symbol_array(symbols, bits_per_symbol: int, validate: bool) -> np.ndarray:
    """Coerce `symbols` to a 1-D unsigned integer array; optionally check the range."""
    if isinstance(symbols, (bytes, bytearray, memoryview)):
        arr = np.frombuffer(symbols, dtype=np.uint8)
    else:
        arr = np.asarray(symbols)
    if arr.ndim != 1:
        raise ValueError("symbols must be one-dimensional")
    if arr.size == 0:
        return np.zeros(0, dtype=_dtype_for(bits_per_symbol))
    if arr.dtype == np.bool_:
        arr = arr.astype(np.uint8)
    if not np.issubdtype(arr.dtype, np.integer):
        raise ValueError(f"symbols must be integers, got dtype {arr.dtype}")
    if validate:
        lo = int(arr.min())
        hi = int(arr.max())
        if lo < 0 or hi >= (1 << bits_per_symbol):
            raise ValueError(
                f"symbols must lie in [0, 2**{bits_per_symbol}); "
                f"observed min={lo} max={hi}"
            )
    return arr.astype(_dtype_for(bits_per_symbol), copy=False)


def to_bitstring(symbols, bits_per_symbol: int, bit_order: str = "msb") -> np.ndarray:
    """
    Section 3.1.3 (PDF p. 20): the L samples "(each having n bits)" are
    "considered as a bitstring of size nL".  Expand every symbol to
    bits_per_symbol bits and concatenate.

    bit_order='msb' (default): bit bits_per_symbol-1 of each symbol comes first.
    bit_order='lsb': bit 0 of each symbol comes first.
    The standard does not fix this order; MSB-first is this audit's convention.
    """
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
    # (L, 1) >> (1, bps)  ->  (L, bps) matrix of bits, then flatten row-major.
    bits = (arr[:, None] >> shifts[None, :]) & arr.dtype.type(1)
    return bits.reshape(-1).astype(np.uint8, copy=False)


def _symbol_counts(arr: np.ndarray, bits_per_symbol: int):
    """
    Return (values, counts) for the distinct symbols in `arr`, with `values`
    sorted ascending.  Vectorised: np.bincount for small alphabets, np.unique
    for wide ones.  This is the only place numpy does the spec's work
    ("#{x_i in S}" for every i).
    """
    if bits_per_symbol <= 24:
        counts = np.bincount(arr.astype(np.intp, copy=False))
        values = np.nonzero(counts)[0]
        return values, counts[values]
    values, counts = np.unique(arr, return_counts=True)
    return values, counts


# --------------------------------------------------------------------------
# The estimator
# --------------------------------------------------------------------------

def estimate(symbols, bits_per_symbol, **options) -> dict:
    """
    SP 800-90B section 6.3.1, The Most Common Value Estimate (PDF p. 49).

    Parameters
    ----------
    symbols : sequence / np.ndarray / bytes of ints in [0, 2**bits_per_symbol)
    bits_per_symbol : int >= 1

    Options (keyword only)
    ----------------------
    variant : 'literal' (default) -> z = 2.576, the constant as printed in step 2
              'exact_quantile'    -> z = Phi^-1(0.995), what the text says 2.576
                                     "corresponds to"
    z       : float; overrides `variant` with an arbitrary constant (variant is
              then reported as 'custom')
    track   : 'literal' (default) -> estimate on the symbols as given
              'bitstring'         -> first expand to bits_per_symbol-bit strings
                                     (section 3.1.3) and estimate on the 1-bit symbols
    bit_order : 'msb' (default) | 'lsb' -- bit order within a symbol for track='bitstring'
    bitstring_limit : None (default) | int -- section 3.1.3: "The bits after the
              first 1 000 000 bits may be ignored."  None keeps every bit.
    validate : bool (default True) -- check every symbol is in [0, 2**bits_per_symbol)

    Returns
    -------
    dict with the C++ verbose-label names as keys:
        'Mode count'  : int    -- #{most common value in S}
        'p-hat'       : float  -- step 1
        'p_u'         : float  -- step 2 (after min(1, .))
        'min entropy' : float  -- step 3
    plus 'min_entropy' (same value as 'min entropy', per the driver contract) and
    the extras 'L', 'mode value', 'k observed', 'z', 'variant', 'track',
    'bits_per_symbol', 'bit_order', 'bitstring_limit', 'p_u clamped'.
    Where the spec gives no value (L < 2 makes step 2 divide by zero) the
    floats are float('nan').
    """
    opts = dict(options)
    variant = opts.pop("variant", "literal")
    z = opts.pop("z", None)
    track = opts.pop("track", "literal")
    bit_order = opts.pop("bit_order", "msb")
    bitstring_limit = opts.pop("bitstring_limit", None)
    validate = bool(opts.pop("validate", True))
    if opts:
        raise TypeError(f"estimate(): unknown option(s) {sorted(opts)}")

    if z is None:
        if variant not in VARIANTS:
            raise ValueError(f"variant must be one of {sorted(VARIANTS)}, got {variant!r}")
        z = VARIANTS[variant]
    else:
        variant = "custom"
    z = float(z)

    bps = int(bits_per_symbol)
    if bps < 1:
        raise ValueError("bits_per_symbol must be >= 1")

    S = _as_symbol_array(symbols, bps, validate)

    if track == "literal":
        bps_used = bps
    elif track == "bitstring":
        S = to_bitstring(S, bps, bit_order)
        if bitstring_limit is not None:
            S = S[: int(bitstring_limit)]
        bps_used = 1
    else:
        raise ValueError("track must be 'literal' or 'bitstring'")

    # "Given the input S = (s1, ..., sL)"
    L = int(S.size)

    # ---- Step 1.  p-hat = max_i #{x_i in S} / L -------------------------------
    if L == 0:
        mode_count = 0
        mode_value = None
        k_observed = 0
        p_hat = NAN
    else:
        values, counts = _symbol_counts(S, bps_used)
        k_observed = int(values.size)
        i_max = int(np.argmax(counts))        # first (smallest) value attaining the max
        mode_value = int(values[i_max])
        mode_count = int(counts[i_max])       # #{x_i in S} for the most common x_i
        p_hat = mode_count / L                # Python int / int -> correctly rounded binary64

    # ---- Step 2.  p_u = min(1, p-hat + z * sqrt(p-hat (1 - p-hat) / (L - 1))) -
    if L < 2:
        # L - 1 = 0: the formula divides by zero (0/0 when L = 1).  The spec
        # gives no value, so none is returned.
        half_width = NAN
        p_u_unclamped = NAN
        p_u = NAN
        clamped = False
    else:
        half_width = z * math.sqrt(p_hat * (1.0 - p_hat) / (L - 1))
        p_u_unclamped = p_hat + half_width
        clamped = p_u_unclamped > 1.0
        p_u = min(1.0, p_u_unclamped)

    # ---- Step 3.  min-entropy = -log2(p_u) ----------------------------------------
    if math.isnan(p_u):
        min_entropy = NAN
    else:
        # Written as 0.0 - log2(p_u) rather than -log2(p_u) so that p_u == 1
        # yields +0.0 instead of IEEE -0.0 (same value; cleaner JSON).
        min_entropy = 0.0 - math.log2(p_u)

    return {
        "min_entropy": min_entropy,
        # --- the C++ verbose-label names ---
        "Mode count": mode_count,
        "p-hat": p_hat,
        "p_u": p_u,
        "min entropy": min_entropy,
        # --- extras (not C++ labels) ---
        "L": L,
        "mode value": mode_value,
        "k observed": k_observed,
        "z": z,
        "variant": variant,
        "track": track,
        "bits_per_symbol": bps,
        "bit_order": bit_order if track == "bitstring" else None,
        "bitstring_limit": bitstring_limit if track == "bitstring" else None,
        "p_u unclamped": p_u_unclamped,
        "p_u clamped": bool(clamped),
    }


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

USAGE = """usage: python mcv.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
                     [--variant literal|exact_quantile] [--z Z]
                     [--lsb-first] [--bitstring-limit N]

  rawfile          one symbol per byte; the low <bits_per_symbol> bits are the symbol
  bits_per_symbol  1..8 for this byte-per-symbol file format
  --literal        (default) estimate on the symbols as read
  --bitstring      expand each symbol to <bits_per_symbol> bits, MSB-first (section 3.1.3),
                   and estimate on the 1-bit symbols
  --variant        'literal' (default, z = 2.576 as printed) or 'exact_quantile'
  --z Z            use an arbitrary confidence constant instead
  --lsb-first      with --bitstring: LSB-first bit order within each symbol
  --bitstring-limit N   with --bitstring: keep only the first N bits (section 3.1.3
                   says the bits after the first 1 000 000 "may be ignored")
Prints the estimate dict as JSON on stdout.
"""


def _parse_args(argv):
    positional = []
    track = "literal"
    variant = "literal"
    z = None
    bit_order = "msb"
    bitstring_limit = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--literal":
            track = "literal"
        elif a == "--bitstring":
            track = "bitstring"
        elif a == "--lsb-first":
            bit_order = "lsb"
        elif a == "--variant":
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            variant = argv[i]
        elif a == "--z":
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            z = float(argv[i])
        elif a == "--bitstring-limit":
            i += 1
            if i >= len(argv):
                raise SystemExit(USAGE)
            bitstring_limit = int(argv[i])
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
    return path, bps, track, variant, z, bit_order, bitstring_limit


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    path, bps, track, variant, z, bit_order, bitstring_limit = _parse_args(argv)

    with open(path, "rb") as fh:
        raw = fh.read()
    data = np.frombuffer(raw, dtype=np.uint8)

    # "one symbol per byte, low bits_per_symbol bits are the symbol"
    mask = (1 << bps) - 1
    masked_bytes = int(np.count_nonzero(data > mask))   # bytes that had bits above the width
    symbols = data & np.uint8(mask)

    options = {"track": track, "bit_order": bit_order, "bitstring_limit": bitstring_limit}
    if z is not None:
        options["z"] = z
    else:
        options["variant"] = variant

    result = estimate(symbols, bps, **options)
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
