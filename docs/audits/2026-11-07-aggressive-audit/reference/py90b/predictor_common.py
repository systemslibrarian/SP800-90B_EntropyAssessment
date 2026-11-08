"""py90b.predictor_common -- SP 800-90B (January 2018) sections 6.3.7-6.3.10: the steps the
four prediction estimators (MultiMCW, Lag, MultiMMC, LZ78Y) SHARE once a predictor has
produced its `correct` array -- the global-performance bound P'_global, the binary-search
solve for the local performance P_local, and the min-entropy finish.

Written from the standard's text only (AUDIT-BRIEF.md, "Independence of the reference
implementation").  No file under cpp/ was opened.  The only items borrowed from the C++ are
the verbose-output LABEL NAMES ("C", "r", "N", "P_global", "P_global'", "P_local",
"min entropy") listed in reference/cpp-verbose-labels-non_iid.txt, so that the differential
driver can match this module's keys to the tool's printed lines.

THE TEXT IMPLEMENTED (identical in 6.3.7 steps 4-7 PDF pp. 57-58, 6.3.8 steps 4-7 PDF
pp. 59-60, 6.3.9 steps 5-8 PDF pp. 61-62, 6.3.10 steps 3c-6 PDF pp. 64-65; quoted here from
SP 800-90B section 6.3.7, PDF pp. 57-58):

  step 4  "Let C be the number of ones in correct."

  step 5  "Calculate the predictor's global performance as P_global = C / N.  The upper
           bound of the 99 % confidence interval on P_global, denoted P'_global is
           calculated as:
               P'_global = 1 - 0.01^(1/N),                                        if P_global = 0,
                           min(1, P_global + 2.576 sqrt(P_global (1 - P_global) / (N - 1))),  otherwise
           where 2.576 corresponds to the Z(1-0.005) value."

  step 6  "Calculate the predictor's local performance, based on the longest run of
           correct predictions.  Let r be one greater than the length of the longest run of
           ones in correct.  Use a binary search to solve the following for P_local:
               0.99 = (1 - P_local x) / ((r + 1 - r x) q)  x  1 / x^(N+1),
           where q = 1 - P_local and x = x_10, derived by iterating the recurrence relation
               x_j = 1 + q P_local^r x_{j-1}^(r+1)
           for j from 1 to 10, and x_0 = 1.  Note that solving for P_local using the
           logarithm of these equations is robust against overflows.  Table 3 given in
           Appendix G.2 provides some pre-calculated values of P_local."

  step 7  "The min-entropy is the negative logarithm of the greater performance metric
               min-entropy = -log2(max(P'_global, P_local, 1/k))."

k is the alphabet size: section 6 (PDF p. 48) "each s_i comes from an output space
A = {x_1, ..., x_k} that is specified by the submitter"; section 6.4 (PDF p. 66) "the size
of the alphabet A, denoted k".

WHAT IS LITERAL HERE AND WHAT IS A VARIANT

  * z = 2.576 exactly as printed (Z_TEXT) is the default.  The exact binary64 0.995 normal
    quantile 2.5758293035489008 (Z_EXACT) is exposed as a VARIANT only; it is the known,
    documented divergence D-1 / C22c of FORK-DIVERGENCE-AND-TRUST.md, not the text.
  * x = x_10: the recurrence is iterated exactly ten times (RECURRENCE_STEPS = 10).
    steps="converge" iterates to the binary64 fixed point instead -- a VARIANT (tracker F08).
  * "Use a binary search": the text gives no tolerance.  The default bisects on [0, 1]
    until the bracket is one binary64 step wide; tol= stops earlier (a variant for drivers
    that want to emulate a tolerance-based search).  solve_p_local_exact() repeats the
    search in decimal arithmetic at a chosen precision, independent of binary64 rounding.
  * "using the logarithm of these equations": the right-hand side is evaluated as a
    natural logarithm.  x is carried as 1 + d with d = q P_local^r x_{j-1}^(r+1), so that
    ln x = log1p(d) keeps its precision when d ~ 1e-8 (which it is at N ~ 1e6).  This is
    the same equation, not a variant: it changes rounding, not the quantity.

AMBIGUITIES RECORDED (see also the module's tests and the structured return)

  A1. k: 2**bits_per_symbol (the declared output space) is the literal reading of "A ...
      specified by the submitter".  The number of distinct symbols actually observed is a
      different reading; pass k= to use it.  For the bitstring track k = 2.
  A2. N = 1 with P_global != 0 (C = 1): step 5's "otherwise" branch is sqrt(0/0).  The text
      gives no value -> NaN.  (Python's min(1.0, nan) returns 1.0 -- the code never relies
      on min() with a NaN operand.)  N = 1 with C = 0 IS defined: P'_global = 0.99.
  A3. N < 1: P_global = C/N has no value -> every statistic is NaN.
  A4. r > N (every prediction correct, r = N + 1): a run of r ones cannot occur in N
      trials, so the true probability is 1 for every P_local and "0.99 = ..." has no
      solution; the step-6 FORMULA (Feller's approximation) still crosses 0.99 and the
      literal reading solves it anyway.  Implemented literally; result is large (conservative).
  A5. Appendix G.2 Table 3 (PDF p. 84) says "when L = 1 000 000" while the equation uses
      N.  At four decimals the table matches N = 1 000 000, N - 1 and N - 2 alike.
  A6. Table 3 has a labelling error: the 21 rows printed as r = 55, 60, ..., 155 hold the
      values for r = 50, 55, ..., 150 (printed "55: 0.7092" is P_local(50); the value for
      r = 155, 0.9013, is absent).  All other 115 rows reproduce at four decimals.
  A7. The text does not say which end of the final bracket to report; the midpoint is
      returned.  At one-ulp width this is a last-bit choice.
  A8. The worked examples' printed figures are not round-half-up of the exact values:
      6.3.8 prints P'_global = 0.6008 for 0.600859 (a truncation) and 6.3.7 prints
      min-entropy 0.3908 for 0.390875, which is -log2 of the ROUNDED P'_global 0.7627.
      Every printed figure agrees with this module within one unit in its last printed
      place; the tests check that, not round-half-up.  The code is not adjusted.
  A9. Binary64 evaluation of step 6's right-hand side is ill-conditioned when it is done
      as ln(x) with x = 1 + d and d ~ 1e-8 (N ~ 1e6): about eight significant digits of
      ln x are lost, and the solved P_local moves by ~1e-10 .. 1e-8 relative (measured on a
      sibling copy that does exactly that; see tests).  log1p(d) avoids it.  The standard
      says "using the logarithm of these equations" and no more.  Differences of this
      size between two implementations (or two platforms' libm) are therefore expected
      and are NOT evidence about the equation; solve_p_local_exact() is the arbiter.

API

  solve_p_local(r, N, *, steps=10, confidence=0.99, tol=None)      -> float   (step 6)
  solve_p_local_exact(r, N, *, digits=40, steps=10)                 -> Decimal (step 6, high precision)
  p_global_prime(P_global, N, z=Z_TEXT)                             -> float   (step 5)
  min_entropy(P_global_prime, P_local, k)                           -> float   (step 7)
  finish(C, N, r, bits, *, k=None, z=Z_TEXT, steps=10, exact=False) -> dict    (steps 5-7)
  estimate(symbols, bits_per_symbol, **options)                     -> dict
      default: `symbols` IS the `correct` array (N Boolean values) and bits_per_symbol is
               the width of the samples that were predicted (k = 2**bits_per_symbol, or
               k = 2 with bitstring=True);
      predictor='multimcw'|'lag'|'multimmc'|'lz78y': `symbols` are raw samples; the named
               sibling module runs its own steps 1-4 to produce C, r, N and THIS module
               performs steps 5-7; the sibling's finish is returned under 'sibling'.
  __main__: python predictor_common.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
            [--predictor=NAME] [--k=INT] [--z=2.576|exact] [--steps=10|converge] [--exact]
            [--tol=FLOAT] [--digits=INT]     -> prints the dict as JSON
"""

from __future__ import annotations

import importlib
import json
import math
import os
import sys
from decimal import Decimal, localcontext

import numpy as np

NAN = float("nan")

# ------------------------------------------------------------------------------------------
# Constants, each a quotation.
# ------------------------------------------------------------------------------------------
Z_TEXT = 2.576                    # step 5: "where 2.576 corresponds to the Z(1-0.005) value"
Z_EXACT = 2.5758293035489008      # VARIANT: exact binary64 0.995 quantile (D-1 / C22c), not the text
GLOBAL_ALPHA = 0.01               # step 5: "1 - 0.01^(1/N), if P_global = 0"
LOCAL_CONFIDENCE = 0.99           # step 6: "0.99 = ..."
RECURRENCE_STEPS = 10             # step 6: "x = x_10 ... for j from 1 to 10, and x_0 = 1"
CONVERGE_MAX_STEPS = 100_000      # cap for the steps="converge" variant only

PREDICTOR_MODULES = {"multimcw": "multimcw", "lag": "lag", "multimmc": "multimmc", "lz78y": "lz78y"}


def _is_nan(v):
    return isinstance(v, float) and math.isnan(v)


# ------------------------------------------------------------------------------------------
# Step 4 and the run length that step 6 needs.
# ------------------------------------------------------------------------------------------
def count_correct(correct):
    """Step 4: "Let C be the number of ones in correct." """
    c = np.asarray(correct)
    return int(np.count_nonzero(c)) if c.size else 0


def longest_run_of_ones(correct):
    """Step 6: "the length of the longest run of ones in correct" (0 when there is none)."""
    c = (np.asarray(correct) != 0).astype(np.int8)
    if c.size == 0:
        return 0
    padded = np.concatenate(([0], c, [0]))
    edges = np.diff(padded)                       # +1 where a run starts, -1 one past its end
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return int((ends - starts).max()) if starts.size else 0


def run_parameter_r(correct):
    """Step 6: "Let r be one greater than the length of the longest run of ones in correct." """
    return 1 + longest_run_of_ones(correct)


# ------------------------------------------------------------------------------------------
# Step 5.
# ------------------------------------------------------------------------------------------
def p_global(C, N):
    """Step 5: "P_global = C / N".  NaN when N < 1 (ambiguity A3)."""
    if N < 1:
        return NAN
    return C / N


def p_global_prime(P_global, N, z=Z_TEXT):
    """Step 5: P'_global.
        1 - 0.01^(1/N)                                              if P_global = 0,
        min(1, P_global + 2.576 sqrt(P_global (1 - P_global) / (N - 1)))   otherwise.
    NaN when N < 1 (A3) or when N = 1 with P_global != 0, where the text's expression is
    sqrt(0/0) (A2)."""
    if N < 1 or _is_nan(P_global):
        return NAN
    if P_global == 0:
        return 1.0 - GLOBAL_ALPHA ** (1.0 / N)
    if N == 1:
        return NAN
    bound = P_global + z * math.sqrt(P_global * (1.0 - P_global) / (N - 1))
    return 1.0 if bound > 1.0 else bound           # min(1, bound) without min()'s NaN trap


# ------------------------------------------------------------------------------------------
# Step 6.
# ------------------------------------------------------------------------------------------
def _recurrence_d(log_qpr, r, steps):
    """x_j - 1 = q P_local^r x_{j-1}^(r+1), iterated from x_0 = 1 (d_0 = 0).
    log_qpr = ln(q P_local^r).  Returns d = x - 1 after `steps` iterations, or after
    reaching a binary64 fixed point when steps is "converge"."""
    d = 0.0
    if steps == "converge" or steps is None:
        for _ in range(CONVERGE_MAX_STEPS):
            nd = math.exp(log_qpr + (r + 1) * math.log1p(d))
            if nd == d:
                break
            d = nd
        return d
    for _ in range(int(steps)):
        d = math.exp(log_qpr + (r + 1) * math.log1p(d))
    return d


def log_run_probability(p, r, N, steps=RECURRENCE_STEPS):
    """Natural logarithm of step 6's right-hand side at P_local = p:

        (1 - p x) / ((r + 1 - r x) q)  x  1 / x^(N+1),    q = 1 - p,  x = x_steps.

    "solving for P_local using the logarithm of these equations is robust against
    overflows" -- so this is ln(1 - p x) - ln((r + 1 - r x) q) - (N + 1) ln x, with x carried
    as 1 + d so that ln x = log1p(d).  Returns 0.0 at p = 0 (x = 1, the expression is exactly
    1) and -inf where a factor is not positive (q = 0 at p = 1, or 1 - p x <= 0, or
    r + 1 - r x <= 0): there the text's expression has no value, and the bisection reads
    -inf as "below 0.99", i.e. P_local too large."""
    if not (0.0 <= p <= 1.0):
        raise ValueError("P_local must lie in [0, 1]")
    if p == 0.0:
        return 0.0
    q = 1.0 - p
    if q <= 0.0:
        return -math.inf
    log_qpr = math.log(q) + r * math.log(p)       # ln(q P_local^r); exp() of it underflows to 0 harmlessly
    d = _recurrence_d(log_qpr, r, steps)
    x = 1.0 + d
    numerator = 1.0 - p * x
    denominator = (r + 1 - r * x) * q
    if not (numerator > 0.0 and denominator > 0.0):
        return -math.inf
    return math.log(numerator) - math.log(denominator) - (N + 1) * math.log1p(d)


def solve_p_local(r, N, *, steps=RECURRENCE_STEPS, confidence=LOCAL_CONFIDENCE, tol=None,
                  max_iter=2200):
    """Step 6: "Use a binary search to solve the following for P_local: 0.99 = ...".

    Bisection on [0, 1].  At p = 0 the right-hand side is 1 (> 0.99); at p = 1 it has no
    value (read as < 0.99).  The bracket keeps rhs(lo) > 0.99 >= rhs(hi) and narrows until
    its midpoint is no longer strictly inside it in binary64 (or until hi - lo <= tol when
    tol is given).  The midpoint of the final bracket is returned (A7).
    NaN when N < 1 or r < 1, where the text gives no value."""
    r = int(r)
    N = int(N)
    if N < 1 or r < 1:
        return NAN
    target = math.log(confidence)
    lo, hi = 0.0, 1.0
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if not (lo < mid < hi):
            break
        if tol is not None and (hi - lo) <= tol:
            break
        if log_run_probability(mid, r, N, steps) > target:
            lo = mid                               # still above 0.99: P_local too small
        else:
            hi = mid
    return 0.5 * (lo + hi)


def solve_p_local_exact(r, N, *, digits=40, steps=RECURRENCE_STEPS, confidence="0.99"):
    """Step 6 again, in decimal arithmetic (the standard library's `decimal`), so that the
    binary64 solve above can be checked against a result that owes nothing to binary64
    rounding.  Same equation, same ten-step recurrence, same bisection on [0, 1]; stops when
    the bracket is narrower than 10^-digits.  Returns a Decimal (NaN when N < 1 or r < 1)."""
    r = int(r)
    N = int(N)
    if N < 1 or r < 1:
        return Decimal("NaN")
    with localcontext() as ctx:
        ctx.prec = digits + 15
        one = Decimal(1)
        target = Decimal(confidence).ln()

        def log_rhs(p):
            if p <= 0:
                return Decimal(0)
            q = one - p
            if q <= 0:
                return None
            log_qpr = q.ln() + r * p.ln()
            d = Decimal(0)
            for _ in range(int(steps)):
                d = (log_qpr + (r + 1) * (one + d).ln()).exp()
            x = one + d
            numerator = one - p * x
            denominator = (r + 1 - r * x) * q
            if numerator <= 0 or denominator <= 0:
                return None
            return numerator.ln() - denominator.ln() - (N + 1) * x.ln()

        lo, hi = Decimal(0), Decimal(1)
        width = Decimal(10) ** (-digits)
        while hi - lo > width:
            mid = (lo + hi) / 2
            v = log_rhs(mid)
            if v is not None and v > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2


# ------------------------------------------------------------------------------------------
# Step 7.
# ------------------------------------------------------------------------------------------
def min_entropy(P_global_prime_, P_local, k):
    """Step 7: "min-entropy = -log2(max(P'_global, P_local, 1/k))".
    NaN if either performance metric is NaN (the text gives no value for it)."""
    if _is_nan(P_global_prime_) or _is_nan(P_local):
        return NAN
    return -math.log2(max(P_global_prime_, P_local, 1.0 / k)) + 0.0     # + 0.0: -0.0 -> 0.0


def _binding(P_global_prime_, P_local, k):
    """Which of the three arguments of step 7's max() decided the estimate (ties resolve in
    the order the text lists them)."""
    if _is_nan(P_global_prime_) or _is_nan(P_local):
        return None
    best = max(P_global_prime_, P_local, 1.0 / k)
    for name, value in (("P_global'", P_global_prime_), ("P_local", P_local), ("1/k", 1.0 / k)):
        if value == best:
            return name
    return None


def finish(C, N, r, bits, *, k=None, z=Z_TEXT, steps=RECURRENCE_STEPS, exact=False,
           exact_digits=40, tol=None):
    """Steps 5-7 from a predictor's C, N and r.  `bits` is the width of the predicted
    samples and sets k = 2**bits unless k is given (ambiguity A1).

    Returns the labelled intermediates: 'C', 'r', 'N', 'k', 'P_global', "P_global'",
    'P_local', 'min_entropy', plus 'binding' (which argument of step 7's max decided),
    'P_local_changes_result' (P_local > P'_global -- the shortcut condition a tool may use
    to skip the solve), and the parameters used.  With exact=True, 'P_local_exact' (a
    decimal string from solve_p_local_exact) and 'P_local_ulp_error' (binary64 ulps between
    the float solve and the exact one) are added."""
    if k is None:
        if bits is None:
            raise ValueError("finish() needs bits (k = 2**bits) or k")
        k = 1 << int(bits)
    k = int(k)
    if k < 1:
        raise ValueError("k must be a positive integer")
    C = int(C)
    N = int(N)
    r = int(r)
    result = {
        "C": C, "r": r, "N": N, "k": k,
        "P_global": NAN, "P_global'": NAN, "P_local": NAN, "min_entropy": NAN,
        "binding": None, "P_local_changes_result": None,
        "z": z, "recurrence_steps": steps, "confidence": LOCAL_CONFIDENCE,
    }
    if N < 1:                                         # A3: C/N has no value
        return result
    Pg = p_global(C, N)
    Pgp = p_global_prime(Pg, N, z)
    Pl = solve_p_local(r, N, steps=steps, tol=tol)
    result.update({
        "P_global": Pg, "P_global'": Pgp, "P_local": Pl,
        "min_entropy": min_entropy(Pgp, Pl, k),
        "binding": _binding(Pgp, Pl, k),
        "P_local_changes_result": (None if (_is_nan(Pgp) or _is_nan(Pl)) else bool(Pl > Pgp)),
    })
    if exact:
        Pl_exact = solve_p_local_exact(r, N, digits=exact_digits, steps=steps)
        result["P_local_exact"] = str(Pl_exact)
        if not Pl_exact.is_nan() and not _is_nan(Pl):
            ulp = math.ulp(Pl) if Pl != 0.0 else math.ulp(0.0)
            result["P_local_ulp_error"] = float((Decimal(Pl) - Pl_exact) / Decimal(ulp))
            with localcontext() as ctx:
                ctx.prec = exact_digits + 15
                best = max(Decimal(Pgp), Pl_exact, Decimal(1) / Decimal(k))
                result["min_entropy_exact"] = str(-(best.ln() / Decimal(2).ln()))
        else:
            result["P_local_ulp_error"] = NAN
            result["min_entropy_exact"] = "NaN"
    return result


# ------------------------------------------------------------------------------------------
# Input handling.
# ------------------------------------------------------------------------------------------
def to_bitstring(symbols, bits_per_symbol):
    """Section 3.1.3 (PDF p. 20): "the sequential dataset that contains L samples (each
    having n bits) is considered as a bitstring of size nL"; glossary (PDF p. 69): "The
    leftmost bit is the most significant bit" -- each symbol contributes its bits MSB first."""
    s = np.asarray(symbols, dtype=np.int64)
    shifts = np.arange(bits_per_symbol - 1, -1, -1, dtype=np.int64)
    return ((s[:, None] >> shifts[None, :]) & 1).astype(np.uint8).ravel()


def _validate_symbols(symbols, bits_per_symbol):
    if not isinstance(bits_per_symbol, (int, np.integer)) or bits_per_symbol < 1:
        raise ValueError("bits_per_symbol must be a positive integer")
    x = np.asarray(symbols)
    if x.ndim != 1:
        raise ValueError("symbols must be one-dimensional")
    if x.size and not np.issubdtype(x.dtype, np.integer):
        raise ValueError("symbols must be integers")
    x = x.astype(np.int64, copy=False)
    if x.size and (x.min() < 0 or x.max() >= (1 << int(bits_per_symbol))):
        raise ValueError("symbols must lie in [0, 2**bits_per_symbol)")
    return x


def _import_sibling(name):
    """Import py90b.<name> lazily (never at module import time, so that the four predictor
    modules can import THIS module without a cycle).  Works both when this module is part
    of the py90b package and when it is run as a script."""
    key = str(name).lower()
    if key not in PREDICTOR_MODULES:
        raise ValueError("predictor must be one of %s" % sorted(PREDICTOR_MODULES))
    modname = PREDICTOR_MODULES[key]
    if __package__:
        try:
            return importlib.import_module("." + modname, __package__)
        except ImportError:
            pass
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    return importlib.import_module(modname)


# ------------------------------------------------------------------------------------------
# The estimate() entry point.
# ------------------------------------------------------------------------------------------
def estimate(symbols, bits_per_symbol, **options):
    """Steps 4-7 of sections 6.3.7-6.3.10.

    Default (predictor=None): `symbols` IS the `correct` array -- N Boolean values -- and
    bits_per_symbol is the width of the samples that were predicted, so k = 2**bits_per_symbol
    (k = 2 with bitstring=True: the bitstring track's alphabet is {0, 1}).  N = len(symbols).

    predictor='multimcw'|'lag'|'multimmc'|'lz78y': `symbols` are the raw samples in
    [0, 2**bits_per_symbol).  The sibling module runs its steps 1-4 (on the MSB-first
    bitstring when bitstring=True) and reports C, r, N; this module performs steps 5-7 on
    them.  The sibling's own "P_global'", 'P_local' and 'min_entropy' are returned under
    'sibling', with 'sibling_max_rel_dev' (the largest relative deviation over those keys)
    and 'finish_matches_sibling' (that deviation <= match_rel_tol, default 1e-9 -- see A9
    for why not tighter).

    Other options: k (A1), z (Z_TEXT; Z_EXACT is the variant), steps (10; "converge" is the
    variant), tol (None), exact (False: add the decimal-arithmetic P_local), exact_digits (40),
    match_rel_tol (1e-9).
    """
    predictor = options.pop("predictor", None)
    bitstring = bool(options.pop("bitstring", False))
    k = options.pop("k", None)
    z = options.pop("z", Z_TEXT)
    steps = options.pop("steps", RECURRENCE_STEPS)
    tol = options.pop("tol", None)
    exact = bool(options.pop("exact", False))
    exact_digits = int(options.pop("exact_digits", 40))
    match_rel_tol = float(options.pop("match_rel_tol", 1e-9))
    if options:
        raise TypeError("unknown options: %s" % sorted(options))
    if isinstance(z, str):
        z = Z_EXACT if z.lower() == "exact" else float(z)
    if isinstance(steps, str) and steps.lower() != "converge":
        steps = int(steps)

    x = _validate_symbols(symbols, bits_per_symbol)
    if k is None:
        k = 2 if bitstring else (1 << int(bits_per_symbol))
    common = dict(k=int(k), z=z, steps=steps, exact=exact, exact_digits=exact_digits, tol=tol)

    if predictor is None:
        if x.size and x.max() > 1:
            raise ValueError("without predictor=, symbols must be the `correct` array of 0/1 "
                             "values; pass predictor='lag' etc. for raw samples")
        N = int(x.size)
        C = count_correct(x)
        r = run_parameter_r(x)
        result = finish(C, N, r, None, **common)
        result.update({"mode": "correct-array", "bitstring": bitstring, "predictor": None})
        return result

    module = _import_sibling(predictor)
    if bitstring:
        sib = module.estimate(to_bitstring(x, int(bits_per_symbol)), 1)
    else:
        sib = module.estimate(x, int(bits_per_symbol))
    C, r, N = sib["C"], sib["r"], sib["N"]
    if any(_is_nan(v) for v in (C, r, N)):
        result = finish(0, 0, 1, None, **common)          # N < 1 -> all NaN
    else:
        result = finish(int(C), int(N), int(r), None, **common)
    sibling = {key: sib.get(key, NAN) for key in ("P_global", "P_global'", "P_local", "min_entropy")}
    matches = True
    max_rel_dev = 0.0
    for key in sibling:
        mine, theirs = result[key], sibling[key]
        if _is_nan(mine) and _is_nan(theirs):
            continue
        if _is_nan(mine) or _is_nan(theirs):
            matches = False
            max_rel_dev = NAN
            continue
        scale = max(abs(mine), abs(theirs), 1e-300)
        dev = abs(mine - theirs) / scale
        if not _is_nan(max_rel_dev):
            max_rel_dev = max(max_rel_dev, dev)
        if dev > match_rel_tol:
            matches = False
    result.update({"mode": "predictor", "bitstring": bitstring, "predictor": PREDICTOR_MODULES[str(predictor).lower()],
                   "sibling": sibling, "sibling_max_rel_dev": max_rel_dev,
                   "finish_matches_sibling": matches, "match_rel_tol": match_rel_tol})
    return result


# ------------------------------------------------------------------------------------------
# Command line.
# ------------------------------------------------------------------------------------------
def _read_raw(path, bits_per_symbol):
    """One symbol per byte; the low bits_per_symbol bits are the symbol."""
    data = np.fromfile(path, dtype=np.uint8)
    mask = (1 << bits_per_symbol) - 1
    exceeding = int(np.count_nonzero(data > mask))
    return (data & mask).astype(np.int64), exceeding


def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(
        prog="predictor_common.py",
        description="SP 800-90B 6.3.7-6.3.10 shared finish: P_global', P_local, min-entropy.")
    ap.add_argument("rawfile")
    ap.add_argument("bits_per_symbol", type=int)
    track = ap.add_mutually_exclusive_group()
    track.add_argument("--literal", action="store_true", help="literal track (default): k = 2**bits")
    track.add_argument("--bitstring", action="store_true",
                       help="expand each symbol to bits MSB-first and treat the result as 1-bit symbols (k = 2)")
    ap.add_argument("--predictor", default=None, help="multimcw|lag|multimmc|lz78y: run that sibling's "
                    "steps 1-4 on the raw samples; without it the file bytes ARE the correct array (0/1)")
    ap.add_argument("--k", type=int, default=None, help="override the alphabet size k")
    ap.add_argument("--z", default=str(Z_TEXT), help="2.576 (text, default) or 'exact' (variant)")
    ap.add_argument("--steps", default=str(RECURRENCE_STEPS), help="10 (text, default) or 'converge' (variant)")
    ap.add_argument("--exact", action="store_true", help="also solve P_local in decimal arithmetic")
    ap.add_argument("--digits", type=int, default=40, help="precision of --exact")
    ap.add_argument("--tol", type=float, default=None, help="stop the bisection at this bracket width")
    args = ap.parse_args(argv)

    if not (1 <= args.bits_per_symbol <= 8):
        ap.error("bits_per_symbol must be in 1..8")
    symbols, exceeding = _read_raw(args.rawfile, args.bits_per_symbol)
    result = estimate(symbols, args.bits_per_symbol, predictor=args.predictor,
                      bitstring=bool(args.bitstring), k=args.k, z=args.z, steps=args.steps,
                      exact=args.exact, exact_digits=args.digits, tol=args.tol)
    result["input"] = {"file": args.rawfile, "samples": int(symbols.size),
                       "bits_per_symbol": args.bits_per_symbol, "bytes_exceeding_width": exceeding}
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
