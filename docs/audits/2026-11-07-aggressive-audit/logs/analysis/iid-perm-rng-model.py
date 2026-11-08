#!/usr/bin/env python3
"""Pure-Python model of two pieces of cpp/shared/utils.h used by the IID
permutation tests, to settle two code-level questions without a build.

Q1. xoshiro_jump(jump_count, state) (utils.h:765-789) declares s0..s3 OUTSIDE
    the `for j < jump_count` loop and never re-zeroes them, so for jump_count
    >= 2 the result is not J^k(state) (k canonical jumps) but
    acc_{j+1} = acc_j XOR J(s_j).  This models both and prints whether they
    agree for jump_count = 0..4.  Thread k in permutation_tests() calls
    xoshiro_jump(k, ...) (permutation_tests.h:649), so threads >= 2 are the
    ones affected.  The states are also checked to be non-zero.

Q2. randomRange64(s, state) (utils.h:828-856): Lemire's method with the
    acceptance rule `l >= (2^L - s') mod s'` where s' = s + 1.  Modelled at
    L = 8 bits exhaustively for every s' in 1..256: each output in [0, s')
    must be hit exactly floor(2^L / s') times by the accepted x values.  The
    algebra is width-independent, so L = 8 stands for L = 64.
"""
MASK = (1 << 64) - 1


def rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & MASK


def next_(s):
    result = (rotl((s[1] * 5) & MASK, 7) * 9) & MASK
    t = (s[1] << 17) & MASK
    s[2] ^= s[0]
    s[3] ^= s[1]
    s[1] ^= s[2]
    s[0] ^= s[3]
    s[2] ^= t
    s[3] = rotl(s[3], 45)
    return result


JUMP = [0x180ec6d33cfd0aba, 0xd5a61266f0c9392c, 0xa9582618e03fc9aa, 0x39abdc4529b1661c]


def canonical_jump(s):
    """Blackman/Vigna jump(): equivalent to 2^128 next() calls."""
    acc = [0, 0, 0, 0]
    for w in JUMP:
        for b in range(64):
            if w & (1 << b):
                for i in range(4):
                    acc[i] ^= s[i]
            next_(s)
    s[:] = acc


def code_jump(jump_count, s):
    """Transcription of utils.h xoshiro_jump(): accumulators declared once."""
    s0 = s1 = s2 = s3 = 0
    for _ in range(jump_count):
        for w in JUMP:
            for b in range(64):
                if w & (1 << b):
                    s0 ^= s[0]; s1 ^= s[1]; s2 ^= s[2]; s3 ^= s[3]
                next_(s)
        s[0], s[1], s[2], s[3] = s0, s1, s2, s3


seed = [0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB, 0x2545F4914F6CDD1D]
print("Q1: xoshiro_jump(k) vs k canonical jumps")
for k in range(0, 5):
    a = list(seed); code_jump(k, a)
    b = list(seed)
    for _ in range(k):
        canonical_jump(b)
    print(f"  k={k}: code==canonical? {a == b}; code state nonzero? {any(a)}; "
          f"code={['%016x' % v for v in a]}")
# the algebraic prediction for k=2: S1 xor S2
s1 = list(seed); canonical_jump(s1)
s2 = list(s1); canonical_jump(s2)
pred = [x ^ y for x, y in zip(s1, s2)]
a2 = list(seed); code_jump(2, a2)
print(f"  k=2 equals S1 xor S2 (predicted from the un-reset accumulators)? {a2 == pred}")

print("Q2: randomRange64 acceptance rule, exhaustive at L=8")
L = 8
bad = 0
for s_in in range(0, 256):               # the caller passes i in [0, 2^L - 1]
    if s_in == (1 << L) - 1:             # the UINT64_MAX special case returns x
        continue
    s = s_in + 1                         # s++ : want [0, s_in] = [0, s)
    t = ((1 << L) - s) % s               # (2^L - s) mod s == 2^L mod s
    counts = [0] * s
    for x in range(1 << L):
        m = x * s
        l = m & ((1 << L) - 1)
        if l < s and l < t:              # the code's reject branch (redraw)
            continue
        counts[m >> L] += 1
    want = (1 << L) // s
    if any(c != want for c in counts):
        bad += 1
        print(f"  s={s}: NON-UNIFORM counts {counts}")
print(f"  non-uniform s values: {bad} of 255  -> {'UNBIASED' if bad == 0 else 'BIASED'}")

print("Q3: FYshuffle loop shape (i from n-1 down to 1, r uniform in [0,i]) on n=4")
import itertools
from collections import Counter
n = 4
tally = Counter()
# enumerate every draw sequence exactly once: r_i in [0,i] for i = 3,2,1
for draws in itertools.product(*[range(i + 1) for i in range(n - 1, 0, -1)]):
    a = list(range(n))
    for i, r in zip(range(n - 1, 0, -1), draws):
        a[r], a[i] = a[i], a[r]
    tally[tuple(a)] += 1
print(f"  distinct permutations reached: {len(tally)} of {24}; "
      f"each exactly once? {set(tally.values()) == {1}}")
