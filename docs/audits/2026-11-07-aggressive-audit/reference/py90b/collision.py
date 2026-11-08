#!/usr/bin/env python3
"""
SP 800-90B section 6.3.2, "The Collision Estimate" (NIST SP 800-90B, January
2018, PDF pp. 50-51) -- an independent reference implementation written from
the standard's text only.

INDEPENDENCE.  Nothing in this file was derived from the C++ tool.  The only
C++-derived content is the set of *label names* of the intermediate quantities
("v", "Sum t_i", "X-bar", "sigma-hat", "X-bar'", "p", "min entropy"), taken from
reference/cpp-verbose-labels-non_iid.txt so that a differential driver can
match them.  Everything else follows the quoted text below, step by step.

THE SPEC, quoted (SP 800-90B section 6.3.2, PDF p. 50):

    "This entropy estimation method is only applied to binary inputs.
     Given the input S = (s1, ..., sL), where si in A = {0,1},
       1. Set v = 0, index = 1.
       2. Beginning with s_index, step through the input until any observed
          value is repeated; i.e., find the smallest j such that si = sj, for
          some i with index <= i < j.
       3. Set v = v + 1, tv = j - index + 1 and index = j + 1.
       4. Repeat steps 2-3 until the end of the dataset is reached.
       5. Calculate the sample mean X-bar, and the sample standard deviation
          sigma-hat, of ti as
              X-bar = (1/v) sum_{i=1..v} ti ,
              sigma-hat = sqrt( (1/(v-1)) sum_{i=1..v} (ti - X-bar)^2 ).
       6. Compute the lower-bound of the confidence interval for the mean,
          based on a normal distribution with a confidence level of 99 %,
              X-bar' = X-bar - 2.576 sigma-hat / sqrt(v).
       7. Using a binary search, solve for the parameter p, such that
              X-bar' = p q^-2 (1 + 1/2 (p^-1 - q^-1)) F(q)
                       - p q^-1 (1/2)(p^-1 - q^-1).
          where q = 1 - p,  p >= q,  F(1/z) = Gamma(3, z) z^-3 e^z,"

(PDF p. 51:)

    "and Gamma(a,b) is the incomplete Gamma function defined as
     integral_b^infinity t^(a-1) e^-t dt.  An efficient implementation of
     F(1/z) is provided in Appendix G.1.1.  The bounds of the binary search
     should be 1/2 and 1.
       8. If the binary search yields a solution, then the min-entropy
          estimation is the negative logarithm of the parameter, p:
              min-entropy = -log2(p).
          If the search does not yield a solution, then the min-entropy
          estimation is:
              min-entropy = log2(2) = 1."

Worked example (PDF p. 51): S = (1,0,0,0,1,1,1,0,0,1,0,1,0,1,0,1,1,1,0,0,
1,1,0,0,0,1,1,1,0,0,1,0,1,0,1,0,1,1,1,0) gives v = 14, (t1..tv) =
(3,3,3,3,3,2,3,2,2,3,3,3,3,2), X-bar = 2.7143, sigma-hat = 0.4688,
X-bar' = 2.3915, p = 0.7329, min-entropy 0.4483.  tests/test_collision.py
checks every one of those numbers.

AMBIGUITIES met while implementing, and how each was resolved (each is also
listed in the structured return of the agent that wrote this file):

  A1. Appendix G.1.1's "efficient" continued fraction for F(1/z) (PDF p. 82,
      "Derived from Equation 8.9.2 at http://dlmf.nist.gov/8.9") did not
      survive the PDF-to-text extraction.  It is only an *approximation* of the
      defined quantity, so this file evaluates F(1/z) from the DEFINITION
      instead: for integer a = 3 the incomplete Gamma function is elementary,
      Gamma(3, z) = e^-z (z^2 + 2z + 2) (integrate by parts twice), hence
      F(1/z) = (z^2 + 2z + 2) / z^3 exactly.  The test file checks this
      against direct numerical integration of the defining integral.

  A2. The step-7 right-hand side is undefined at the search bound p = 1
      (q = 0, q^-1 undefined).  Substituting F(q) = q + 2q^2 + 2q^3 and
      expanding, the right-hand side simplifies EXACTLY to 2 + 2pq, which is
      2.5 at p = 1/2 and 2 at p = 1.  The limit 2.0 is used at p = 1.  The
      simplified form is also offered (equation='simplified') because the
      printed form suffers catastrophic cancellation as q -> 0.

  A3. "If the search does not yield a solution, then min-entropy = 1".  The
      solvable window is 2 <= X-bar' <= 2.5.  X-bar' > 2.5 (collisions
      slower than a fair coin) -> 1 bit is the natural cap.  X-bar' < 2 (the
      99 % lower bound sits below the smallest possible collision time) is
      ALSO "no solution", and the literal text awards 1 bit to what is a
      heavily biased source.  The literal reading is the default
      (variant='spec'); variant='clamp' instead clamps X-bar' up to 2, which
      gives p = 1 and 0 bits.  Both figures are always reported.  This is the
      difference recorded as D-2 in FORK-DIVERGENCE-AND-TRUST.md; it is a
      documented divergence, not a new finding.

  A4. v = 1 makes sigma-hat = sqrt(0/0); v = 0 makes X-bar = 0/0.  The spec
      gives no value, so every downstream quantity is float('nan') and
      min_entropy is NaN with a note (NOT 1.0 -- a NaN target is not "the
      search did not yield a solution", it is "the input is too short to
      measure").  The fork's documented repair (tracker F12) declines when
      v < 2; a differential driver should treat NaN here as "declined".

  A5. "Binary input": the spec applies the method only to binary inputs
      (section 6.3.2), and section 4.4.2 / section 5 define binary by the
      ALPHABET ("produces only two distinct values"; "k = 2"), not by the
      declared sample width.  Collision times depend only on equality of
      symbols, so a two-valued 8-bit file needs no translation.  Inputs with
      more than two distinct values return NaN with a note unless
      allow_nonbinary=True, which then applies the two-symbol equation
      anyway (flagged in the result).

  A6. Section 3.1.3 (PDF p. 20) says the bitstring is the L n-bit samples
      "considered as a bitstring of size nL" and that "the bits after the
      first 1 000 000 bits MAY be ignored".  The bit order inside a sample is
      not stated; MSB-first is used (the task contract).  No truncation is
      applied unless truncate_bits is given.

  A7. The standard writes the 99 % normal quantile as the rounded decimal
      2.576 (step 6).  That decimal is the default (z_alpha=2.576); the exact
      binary64 quantile 2.5758293035489008 can be passed (D-1 / C22c in the
      divergence record, documented, not a finding).

  A8. The spec gives no tolerance or iteration count for the binary search.
      Bisection runs until the bracket can no longer shrink in binary64
      (adjacent floats), capped at 200 steps, comparing against the target in
      exact decimal arithmetic; the midpoint is returned (within one ulp).
"""

from __future__ import annotations

import json
import math
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# Step 6: "with a confidence level of 99 %" -- the standard prints 2.576.
Z_ALPHA_SPEC = 2.576
# The exact 0.995 standard-normal quantile in binary64 (for z_alpha=... callers).
Z_ALPHA_EXACT = 2.5758293035489008

# Step 7: "The bounds of the binary search should be 1/2 and 1."
P_LOWER_BOUND = 0.5
P_UPPER_BOUND = 1.0
MAX_BISECTION_STEPS = 200
# Digits used to evaluate the step-7 right-hand side as printed.  Its two terms
# are each ~1/(2 q^2) and cancel to ~2, so binary64 loses all significance for
# q < ~1e-6 (p near 1); 60 decimal digits keep the literal form exact to well
# below one ulp of the returned float for every binary64 p in [1/2, 1).
RHS_DECIMAL_DIGITS = 60

NAN = float("nan")


# ---------------------------------------------------------------------------
# Steps 1-4: collision times
# ---------------------------------------------------------------------------
def collision_times(symbols: Sequence[int]) -> Tuple[List[int], int]:
    """Steps 1-4 of section 6.3.2, for any alphabet (the steps never use the
    alphabet; only step 7's equation is binary-specific).

    Returns (t, consumed): t = [t1, ..., tv], and `consumed` = the number of
    leading samples covered by the v collision windows.  Samples after the
    last collision (a window that reaches the end without repeating) are
    dropped, exactly as the worked example drops its trailing (1, 0).

    Indices below are 0-based; the spec's are 1-based.  With the spec's
    index_s and j_s and ours index = index_s - 1, j = j_s - 1:
        t_v = j_s - index_s + 1 = j - index + 1  (same expression).
    """
    seq = symbols.tolist() if isinstance(symbols, np.ndarray) else list(symbols)
    L = len(seq)
    t: List[int] = []           # step 1: v = 0 (v == len(t))
    index = 0                   # step 1: index = 1 (0-based: 0)
    while index < L:
        # step 2: beginning with s_index, step through the input until any
        # observed value is repeated; j is the smallest index with s_j already
        # seen in [index, j).
        seen = set()
        j = index
        while j < L:
            s = seq[j]
            if s in seen:
                break
            seen.add(s)
            j += 1
        if j == L:
            # step 4: the end of the dataset is reached before a repeat; the
            # partial window yields no collision and the procedure stops.
            break
        # step 3: v = v + 1, t_v = j - index + 1, index = j + 1
        t.append(j - index + 1)
        index = j + 1
    return t, index


# ---------------------------------------------------------------------------
# Step 5: sample mean and sample standard deviation (v - 1 denominator)
# ---------------------------------------------------------------------------
def sample_mean_and_sd(t: Sequence[int]) -> Tuple[float, float]:
    """X-bar = (1/v) sum t_i ;  sigma-hat = sqrt( (1/(v-1)) sum (t_i - X-bar)^2 ).

    v = 0 -> X-bar undefined (0/0) -> NaN.   v = 1 -> sigma-hat undefined -> NaN.
    Sums are done in exact integer / fraction arithmetic where possible so that
    the mean is correctly rounded.
    """
    v = len(t)
    if v == 0:
        return NAN, NAN
    total = sum(int(x) for x in t)           # exact integer
    x_bar = total / v
    if v < 2:
        return x_bar, NAN
    # sum (t_i - X-bar)^2 computed as sum t_i^2 - v X-bar^2 in exact rationals,
    # then rounded once.
    sum_sq = sum(int(x) * int(x) for x in t)
    ss = Fraction(sum_sq) - Fraction(total, 1) ** 2 / v   # = sum (t_i - mean)^2
    sigma_hat = math.sqrt(float(ss / (v - 1)))
    return x_bar, sigma_hat


# ---------------------------------------------------------------------------
# Step 6: lower 99 % confidence bound on the mean
# ---------------------------------------------------------------------------
def lower_confidence_bound(x_bar: float, sigma_hat: float, v: int,
                           z_alpha: float = Z_ALPHA_SPEC) -> float:
    """X-bar' = X-bar - z_alpha * sigma-hat / sqrt(v)   (spec: z_alpha = 2.576)."""
    if v < 1 or math.isnan(x_bar) or math.isnan(sigma_hat):
        return NAN
    return x_bar - z_alpha * sigma_hat / math.sqrt(v)


# ---------------------------------------------------------------------------
# Step 7: the function F and the equation's right-hand side
# ---------------------------------------------------------------------------
def upper_incomplete_gamma_3(z: float) -> float:
    """Gamma(3, z) = integral_z^inf t^2 e^-t dt.

    For a = 3 the integral is elementary.  Integrating by parts twice:
        int_z^inf t^2 e^-t dt = [ -t^2 e^-t ]_z^inf + 2 int_z^inf t e^-t dt
                              = z^2 e^-z + 2 ( z e^-z + e^-z )
                              = e^-z ( z^2 + 2z + 2 ).
    tests/test_collision.py checks this against direct numerical quadrature.
    """
    return math.exp(-z) * (z * z + 2.0 * z + 2.0)


def F_of_reciprocal_by_definition(z: float) -> float:
    """F(1/z) = Gamma(3, z) z^-3 e^z, evaluated exactly as the spec writes it.
    Overflows for z > ~709 (e^z); used only to validate the closed form."""
    return upper_incomplete_gamma_3(z) * z ** -3 * math.exp(z)


def F_of_reciprocal(z):
    """F(1/z) = Gamma(3, z) z^-3 e^z = (z^2 + 2z + 2) / z^3, with e^-z e^z
    cancelled analytically so small q (large z) does not overflow.  Works on
    float or Decimal arguments."""
    return (z * z + 2 * z + 2) / (z * z * z)


def F(x):
    """F evaluated at x, i.e. F(1/z) with z = 1/x.  The spec applies F to q.
    Works on float or Decimal arguments."""
    return F_of_reciprocal(1 / x)


def rhs_spec_exact(p: float) -> Decimal:
    """The right-hand side of the step-7 equation, as printed:
        p q^-2 (1 + 1/2 (p^-1 - q^-1)) F(q) - p q^-1 (1/2)(p^-1 - q^-1),  q = 1 - p,
    evaluated term by term in RHS_DECIMAL_DIGITS-digit decimal arithmetic.  The
    binary64 p is converted exactly, so this reproduces the printed form without
    the cancellation it suffers in binary64 (its two terms are each ~1/(2 q^2)).
    At the search bound p = 1, q = 0 and q^-1 is undefined; the limit is 2
    (see rhs_simplified_exact)."""
    with localcontext() as ctx:
        ctx.prec = RHS_DECIMAL_DIGITS
        if p >= 1.0:
            return Decimal(2)
        P = Decimal(p)                       # exact conversion of the binary64 p
        Q = 1 - P                            # q = 1 - p
        half_diff = (1 / P - 1 / Q) / 2      # 1/2 (p^-1 - q^-1)
        return P / (Q * Q) * (1 + half_diff) * F(Q) - P / Q * half_diff


def rhs_simplified_exact(p: float) -> Decimal:
    """The same right-hand side after exact algebra.

    With F(q) = (z^2 + 2z + 2)/z^3 at z = 1/q, F(q) = q + 2q^2 + 2q^3, so
        p q^-2 F(q) = p (q^-1 + 2 + 2q).
    Let D = 1/2 (p^-1 - q^-1) = 1/(2p) - 1/(2q).  Then
        RHS = p (q^-1 + 2 + 2q)(1 + D) - (p/q) D
            = [ p/q + 1/(2q) - p/(2q^2) + 2p + 1 - p/q + 2pq + q - p ]
              - [ 1/(2q) - p/(2q^2) ]
            = 1 + p + q + 2pq
            = 2 + 2pq                        (since p + q = 1).
    Check against the worked example: 2 + 2(0.7329)(0.2671) = 2.3915 = X-bar'.
    """
    with localcontext() as ctx:
        ctx.prec = RHS_DECIMAL_DIGITS
        P = Decimal(p)
        return 2 + 2 * P * (1 - P)


def rhs_spec(p: float) -> float:
    """rhs_spec_exact rounded once to binary64 (for display and cross-checks)."""
    return float(rhs_spec_exact(p))


def rhs_simplified(p: float) -> float:
    """rhs_simplified_exact rounded once to binary64 (for display and cross-checks)."""
    return float(rhs_simplified_exact(p))


RHS_FUNCTIONS = {"spec": rhs_spec, "simplified": rhs_simplified}
RHS_EXACT_FUNCTIONS = {"spec": rhs_spec_exact, "simplified": rhs_simplified_exact}


def solve_p_by_binary_search(x_bar_prime: float,
                             equation: str = "spec") -> Optional[float]:
    """Step 7: 'Using a binary search, solve for the parameter p ... The bounds
    of the binary search should be 1/2 and 1.'

    The right-hand side is strictly decreasing on [1/2, 1] (2.5 down to 2), so a
    solution exists iff rhs(1) <= X-bar' <= rhs(1/2).  Returns p, or None when
    the search 'does not yield a solution' (a NaN or infinite target included).

    The comparison rhs(mid) > X-bar' is made in exact decimal arithmetic (the
    binary64 target converted exactly), so the bracket keeps shrinking to two
    adjacent floats and the returned p is within one ulp of the root -- in
    particular X-bar' = 2 gives p = 1 exactly and X-bar' = 2.5 gives p = 1/2.
    """
    if not math.isfinite(x_bar_prime):
        return None
    rhs = RHS_EXACT_FUNCTIONS[equation]
    target = Decimal(x_bar_prime)                  # exact
    lo, hi = P_LOWER_BOUND, P_UPPER_BOUND
    if not (rhs(hi) <= target <= rhs(lo)):         # outside [2, 2.5]
        return None
    for _ in range(MAX_BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        if mid <= lo or mid >= hi:                 # bracket is two adjacent floats
            break
        if rhs(mid) > target:
            lo = mid                               # rhs decreasing: root lies to the right
        else:
            hi = mid
    return 0.5 * (lo + hi)


def min_entropy_from_p(p: Optional[float]) -> float:
    """Step 8: -log2(p) when the search yielded p; log2(2) = 1 when it did not.
    p = 1 gives +0.0 rather than the -0.0 that -math.log2(1.0) would print."""
    if p is None:
        return 1.0
    return 0.0 if p >= 1.0 else -math.log2(p)


# ---------------------------------------------------------------------------
# Section 3.1.3 bitstring construction
# ---------------------------------------------------------------------------
def to_bitstring(symbols: Sequence[int], bits_per_symbol: int,
                 truncate_bits: Optional[int] = None) -> np.ndarray:
    """Section 3.1.3 (PDF p. 20): 'the sequential dataset that contains L
    samples (each having n bits) is considered as a bitstring of size nL.  The
    bits after the first 1 000 000 bits may be ignored.'  Bit order within a
    sample is not stated; MSB-first is used.  No truncation unless asked."""
    if not (1 <= bits_per_symbol <= 8):
        raise ValueError("bits_per_symbol must be in 1..8 for the bitstring path")
    arr = np.asarray(symbols, dtype=np.int64)
    _check_range(arr, bits_per_symbol)
    bits = np.unpackbits(arr.astype(np.uint8).reshape(-1, 1), axis=1,
                         bitorder="big")[:, 8 - bits_per_symbol:]
    bits = bits.ravel()
    if truncate_bits is not None:
        bits = bits[:truncate_bits]
    return bits


def _check_range(arr: np.ndarray, bits_per_symbol: int) -> None:
    if arr.size and (arr.min() < 0 or arr.max() >= (1 << bits_per_symbol)):
        raise ValueError(
            f"symbols must lie in [0, 2**{bits_per_symbol}); "
            f"observed min={int(arr.min())} max={int(arr.max())}")


# ---------------------------------------------------------------------------
# The estimator
# ---------------------------------------------------------------------------
def estimate(symbols: Sequence[int], bits_per_symbol: int, **options) -> Dict:
    """Collision estimate, SP 800-90B section 6.3.2, on `symbols` as given
    (the LITERAL sequence; convert with to_bitstring() first for the
    section 3.1.3 bitstring estimate -- or pass mode='bitstring').

    options:
      mode='literal' | 'bitstring'   (default 'literal'; 'bitstring' converts
                                       via to_bitstring first)
      variant='spec' | 'clamp'       no-solution handling below 2 (see A3)
      equation='spec' | 'simplified' which right-hand side the search uses (A2)
      z_alpha=2.576                  step-6 constant (A7)
      allow_nonbinary=False          apply the binary equation to k > 2 anyway (A5)
      truncate_bits=None             bitstring mode only (A6)

    Returns a dict keyed by the C++ verbose labels plus 'min_entropy'.  NaN
    marks quantities the spec gives no value for.
    """
    mode = options.pop("mode", "literal")
    variant = options.pop("variant", "spec")
    equation = options.pop("equation", "spec")
    z_alpha = float(options.pop("z_alpha", Z_ALPHA_SPEC))
    allow_nonbinary = bool(options.pop("allow_nonbinary", False))
    truncate_bits = options.pop("truncate_bits", None)
    if options:
        raise TypeError(f"unknown options: {sorted(options)}")
    if variant not in ("spec", "clamp"):
        raise ValueError("variant must be 'spec' or 'clamp'")
    if equation not in RHS_FUNCTIONS:
        raise ValueError("equation must be 'spec' or 'simplified'")

    arr = np.asarray(symbols, dtype=np.int64)
    _check_range(arr, bits_per_symbol)
    if mode == "bitstring":
        seq = to_bitstring(arr, bits_per_symbol, truncate_bits)
        width = 1
    elif mode == "literal":
        seq = arr
        width = bits_per_symbol
    else:
        raise ValueError("mode must be 'literal' or 'bitstring'")

    L = int(seq.size)
    k = int(np.unique(seq).size) if L else 0

    result: Dict = {
        "estimator": "Collision Estimate",
        "mode": mode,
        "L": L,
        "k": k,
        "width": width,
        "variant": variant,
        "equation": equation,
        "z_alpha": z_alpha,
        "v": 0,
        "Sum t_i": 0,
        "discarded_tail": L,
        "X-bar": NAN,
        "sigma-hat": NAN,
        "X-bar'": NAN,
        "found_p": False,
        "p": NAN,
        "min entropy": NAN,
        "min_entropy": NAN,
        "min_entropy_spec_fallback": NAN,
        "min_entropy_clamp": NAN,
        "note": "",
    }

    # section 6.3.2: "This entropy estimation method is only applied to binary inputs."
    if k > 2 and not allow_nonbinary:
        result["note"] = (f"not applied: input has k={k} distinct values; "
                          "section 6.3.2 applies the collision estimate to binary inputs only")
        return result
    if k > 2:
        result["note"] = (f"WARNING: k={k} > 2, the two-symbol equation of step 7 "
                          "was applied anyway (allow_nonbinary=True)")

    # steps 1-4
    t, consumed = collision_times(seq)
    v = len(t)
    result["v"] = v
    result["Sum t_i"] = int(sum(t))
    result["discarded_tail"] = L - consumed

    # step 5
    x_bar, sigma_hat = sample_mean_and_sd(t)
    result["X-bar"] = x_bar
    result["sigma-hat"] = sigma_hat
    if v < 2:
        result["note"] = (result["note"] + "; " if result["note"] else "") + (
            f"v={v} < 2: sigma-hat (1/(v-1)) is undefined; the spec gives no value, "
            "so min_entropy is NaN (A4)")
        return result

    # step 6
    x_bar_prime = lower_confidence_bound(x_bar, sigma_hat, v, z_alpha)
    result["X-bar'"] = x_bar_prime

    # step 7, literal: search on [1/2, 1] for the target as computed
    p_spec = solve_p_by_binary_search(x_bar_prime, equation)
    # step 8, literal: -log2(p) if found, else 1
    me_spec = min_entropy_from_p(p_spec)

    # alternative reading (D-2): clamp a target below 2 up to 2 (p = 1, 0 bits)
    target_clamp = max(x_bar_prime, 2.0)
    p_clamp = solve_p_by_binary_search(target_clamp, equation)
    me_clamp = min_entropy_from_p(p_clamp)

    result["min_entropy_spec_fallback"] = me_spec
    result["min_entropy_clamp"] = me_clamp
    if variant == "spec":
        p, me = p_spec, me_spec
    else:
        p, me = p_clamp, me_clamp
    result["found_p"] = p is not None
    result["p"] = p if p is not None else NAN
    result["min entropy"] = me
    result["min_entropy"] = me
    if p is None:
        side = "above 2.5" if x_bar_prime > 2.5 else "below 2"
        result["note"] = (result["note"] + "; " if result["note"] else "") + (
            f"binary search found no solution (X-bar' = {x_bar_prime!r} is {side}); "
            "step 8 fallback min-entropy = log2(2) = 1")
    return result


# ---------------------------------------------------------------------------
# __main__: python collision.py <rawfile> <bits_per_symbol> [--literal|--bitstring]
# ---------------------------------------------------------------------------
def _usage() -> str:
    return (
        "usage: python collision.py <rawfile> <bits_per_symbol> "
        "[--literal|--bitstring] [--variant spec|clamp] [--equation spec|simplified] "
        "[--z-alpha Z] [--allow-nonbinary]\n"
        "  rawfile: one symbol per byte; the low bits_per_symbol bits are the symbol\n"
        "  --literal   : run on the symbols as read (default when bits_per_symbol == 1)\n"
        "  --bitstring : convert each symbol to bits_per_symbol bits MSB-first and run on\n"
        "                the 1-bit sequence (section 3.1.3; default when bits_per_symbol > 1)\n"
    )


def main(argv: List[str]) -> int:
    if len(argv) < 3:
        sys.stderr.write(_usage())
        return 2
    path = argv[1]
    try:
        bps = int(argv[2])
    except ValueError:
        sys.stderr.write(_usage())
        return 2
    if not (1 <= bps <= 8):
        sys.stderr.write("bits_per_symbol must be in 1..8\n")
        return 2
    mode = "literal" if bps == 1 else "bitstring"
    opts: Dict = {}
    rest = argv[3:]
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--literal":
            mode = "literal"
        elif a == "--bitstring":
            mode = "bitstring"
        elif a == "--variant" and i + 1 < len(rest):
            opts["variant"] = rest[i + 1]; i += 1
        elif a == "--equation" and i + 1 < len(rest):
            opts["equation"] = rest[i + 1]; i += 1
        elif a == "--z-alpha" and i + 1 < len(rest):
            opts["z_alpha"] = float(rest[i + 1]); i += 1
        elif a == "--allow-nonbinary":
            opts["allow_nonbinary"] = True
        else:
            sys.stderr.write(_usage())
            return 2
        i += 1

    raw = np.fromfile(path, dtype=np.uint8)
    mask = (1 << bps) - 1
    out_of_width = int(np.count_nonzero(raw > mask))
    symbols = (raw & mask).astype(np.int64)

    res = estimate(symbols, bps, mode=mode, **opts)
    res["file"] = path
    res["bits_per_symbol"] = bps
    res["samples_read"] = int(raw.size)
    res["out_of_width_bytes_masked"] = out_of_width
    sys.stdout.write(json.dumps(res, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
