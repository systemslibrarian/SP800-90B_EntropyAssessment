#!/usr/bin/env python3
"""Independent verifier for PROV-22, written by the verifier (not the reproducer's author).
No binary is run; pure Python over the generator's 256-bit linear algebra.

 V1  xoshiro_jump as written in cpp/shared/utils.h (JUMP constants and accumulator placement
     read from the source text at run time) vs. k canonical Blackman/Vigna jumps, k = 0..8.
 V2  closed form code_jump(k, S0) == J (I+J)^(k-1) S0, k = 1..8.
 V3  J is GF(2)-linear, and J == T^(2^128) by exact 256x256 GF(2) matrix exponentiation
     (what the comment 'equivalent to 2^128 calls' asserts).
 V4  S0 -> code_jump(k, S0) has rank 256 (a bijection) for k = 1..8: a uniform seed gives a
     uniform NONZERO start state on every thread, so each thread's stream is still a
     uniformly-seeded xoshiro256**.
 V5  the one-line fix (zero s0..s3 per iteration) == k canonical jumps.
 V6  the minimal polynomial of T has degree 256, is irreducible and PRIMITIVE, so every nonzero
     state lies on ONE cycle of length 2^256-1 -- the premise of the harmlessness argument --
     and hence (I+J) = T^m for a FIXED m: thread k >= 1 starts at offset 2^128 + (k-1)m from
     thread 0, an offset that does NOT depend on the seed.
 V7  bounded probe: no inter-thread offset below 2^18 among threads {0,1,2} in either direction
     (positive control: an offset of 1234 planted and found). States what it cannot see.
"""
import os, random, re, sys, time

MASK = (1 << 64) - 1
def rotl(x, k): return ((x << k) | (x >> (64 - k))) & MASK

def next_(s):
    r = (rotl((s[1] * 5) & MASK, 7) * 9) & MASK
    t = (s[1] << 17) & MASK
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]
    s[2] ^= t
    s[3] = rotl(s[3], 45)
    return r

repo = sys.argv[1]
src = open(os.path.join(repo, "cpp/shared/utils.h")).read()
m = re.search(r"void xoshiro_jump\(unsigned int jump_count, uint64_t \*xoshiro256starstarState\) \{(.*?)\n\}", src, re.S)
body = m.group(1)
JUMP = [int(x.strip(), 16) for x in re.search(r"JUMP\[\] = \{([^}]*)\}", body).group(1).split(",")]
print("JUMP constants read from utils.h:", ["%016x" % w for w in JUMP])
decl_pos = body.find("uint64_t s0 = 0;")
loop_pos = body.find("for(unsigned int j=0; j < jump_count; j++)")
print("accumulator declaration at body offset %d, j-loop at %d -> declared %s the loop"
      % (decl_pos, loop_pos, "BEFORE" if decl_pos < loop_pos else "INSIDE"))
reset_inside = re.search(r"j\+\+\) \{\s*(uint64_t )?s0 = 0;", body) is not None
print("accumulators re-zeroed inside the j loop?", reset_inside)

def canonical_jump(s):
    acc = [0, 0, 0, 0]
    for w in JUMP:
        for b in range(64):
            if w & (1 << b):
                for i in range(4): acc[i] ^= s[i]
            next_(s)
    s[:] = acc

def code_jump(k, s):            # utils.h as written: s0..s3 declared once, outside the j loop
    s0 = s1 = s2 = s3 = 0
    for _ in range(k):
        for w in JUMP:
            for b in range(64):
                if w & (1 << b):
                    s0 ^= s[0]; s1 ^= s[1]; s2 ^= s[2]; s3 ^= s[3]
                next_(s)
        s[0], s[1], s[2], s[3] = s0, s1, s2, s3

def fixed_jump(k, s):           # the fix: accumulators zeroed per iteration
    for _ in range(k): canonical_jump(s)

def Jk(s, k):
    t = list(s)
    for _ in range(k): canonical_jump(t)
    return t
def CJ(k, s):
    t = list(s); code_jump(k, t); return t
def FJ(k, s):
    t = list(s); fixed_jump(k, t); return t
def xor(a, b): return [x ^ y for x, y in zip(a, b)]

rng = random.Random(20261108)
seeds = [[rng.getrandbits(64) for _ in range(4)] for _ in range(3)]
seeds.append([0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB, 0x2545F4914F6CDD1D])  # the author's seed
ok_all = True

print("\nV1 code_jump(k) vs k canonical jumps (4 seeds, k = 0..8)")
for k in range(0, 9):
    agree = all(CJ(k, S) == Jk(S, k) for S in seeds)
    expect = (k <= 1)
    print("  k=%d: agree=%s expected=%s %s" % (k, agree, expect, "PASS" if agree == expect else "FAIL"))
    ok_all &= (agree == expect)
S = seeds[3]
print("  author's seed, k=2 == S1^S2 ?", CJ(2, S) == xor(Jk(S, 1), Jk(S, 2)))

print("\nV2 closed form code_jump(k,S0) == J (I+J)^(k-1) S0, k = 1..8")
for k in range(1, 9):
    good = True
    for S in seeds:
        v = list(S)
        for _ in range(k - 1): v = xor(v, Jk(v, 1))
        good &= (CJ(k, S) == Jk(v, 1))
    print("  k=%d: %s" % (k, "PASS" if good else "FAIL")); ok_all &= good

print("\nV3 J linear; J == T^(2^128) by GF(2) matrix exponentiation")
lin = all(Jk(xor(a, b), 1) == xor(Jk(a, 1), Jk(b, 1))
          for a, b in [([rng.getrandbits(64) for _ in range(4)], [rng.getrandbits(64) for _ in range(4)]) for _ in range(20)])
print("  J(a^b) == J(a)^J(b), 20 random pairs:", "PASS" if lin else "FAIL"); ok_all &= lin
def s2i(s): return s[0] | (s[1] << 64) | (s[2] << 128) | (s[3] << 192)
def i2s(v): return [(v >> (64 * i)) & MASK for i in range(4)]
def matrix_of(f):               # columns: image of each basis vector, as 256-bit ints
    cols = []
    for i in range(256):
        s = i2s(1 << i); f(s); cols.append(s2i(s))
    return cols
def matmul(A, B):
    out = []
    for i in range(256):
        v = B[i]; r = 0; j = 0
        while v:
            if v & 1: r ^= A[j]
            v >>= 1; j += 1
        out.append(r)
    return out
t0 = time.time()
T = matrix_of(next_)
P = T
for _ in range(128): P = matmul(P, P)
Jm = matrix_of(canonical_jump)
eqJ = (P == Jm)
print("  T^(2^128) == J (%.1fs): %s" % (time.time() - t0, "PASS" if eqJ else "FAIL")); ok_all &= eqJ

def rank_gf2(cols):
    piv = {}; r = 0
    for v in cols:
        while v:
            h = v.bit_length() - 1
            if h in piv: v ^= piv[h]
            else: piv[h] = v; r += 1; break
    return r
print("\nV4 rank over GF(2) of S0 -> code_jump(k,S0), k = 1..8 (256 = bijection)")
for k in range(1, 9):
    rk = rank_gf2(matrix_of(lambda s, k=k: code_jump(k, s)))
    print("  k=%d: rank %d %s" % (k, rk, "PASS" if rk == 256 else "FAIL")); ok_all &= (rk == 256)

print("\nV5 fixed_jump(k) == k canonical jumps, k = 0..8, 4 seeds")
fx = all(FJ(k, S) == Jk(S, k) for k in range(0, 9) for S in seeds)
print("  %s" % ("PASS" if fx else "FAIL")); ok_all &= fx

print("\nV6 minimal polynomial of T: degree, irreducibility, primitivity (single 2^256-1 cycle)")
# Berlekamp-Massey over GF(2) on bit 0 of state word 0 along the orbit of a nonzero start
st = i2s(1); seq = []
for _ in range(600):
    seq.append(st[0] & 1); next_(st)
def berlekamp_massey(s):
    C = 1; B = 1; L = 0; mm = 1          # polynomials as ints, bit i = coeff of x^i
    for n in range(len(s)):
        d = 0; c = C; i = 0
        while c and i <= L:
            if (c & 1) and s[n - i]: d ^= 1
            c >>= 1; i += 1
        if d:
            Tt = C; C ^= (B << mm)
            if 2 * L <= n: L = n + 1 - L; B = Tt; mm = 1
            else: mm += 1
        else: mm += 1
    return C, L
Cpoly, L = berlekamp_massey(seq)
print("  Berlekamp-Massey degree:", L, "(PASS: equals 256 => it is the minimal polynomial of T)" if L == 256 else "FAIL")
ok_all &= (L == 256)
def pmod(a, mod):               # polynomial a mod mod over GF(2)
    dm = mod.bit_length() - 1
    while a.bit_length() - 1 >= dm:
        a ^= mod << (a.bit_length() - 1 - dm)
    return a
def pmul(a, b, mod):
    r = 0
    while b:
        if b & 1: r ^= a
        b >>= 1; a <<= 1
        if a.bit_length() - 1 >= mod.bit_length() - 1: a ^= mod
    return r
def ppow(base, e, mod):
    r = 1; base = pmod(base, mod)
    while e:
        if e & 1: r = pmul(r, base, mod)
        base = pmul(base, base, mod); e >>= 1
    return r
def pgcd(a, b):
    while b:
        a, b = b, pmod(a, b)
    return a
x = 2
# irreducible iff x^(2^256) == x mod C and gcd(x^(2^128) - x, C) == 1 (256 = 2^8, only prime factor 2)
irr = (ppow(x, 1 << 256, Cpoly) == x) and (pgcd(ppow(x, 1 << 128, Cpoly) ^ x, Cpoly) == 1)
print("  irreducible:", "PASS" if irr else "FAIL"); ok_all &= irr
primes = [3, 5, 17, 257, 641, 65537, 274177, 6700417, 67280421310721, 59649589127497217, 5704689200685129054721]
prod = 1
for q in primes: prod *= q
assert prod == (1 << 256) - 1, "factorisation of 2^256-1 does not multiply back"
order_full = all(ppow(x, ((1 << 256) - 1) // q, Cpoly) != 1 for q in primes) and ppow(x, (1 << 256) - 1, Cpoly) == 1
print("  primitive (x has order 2^256-1 mod C; factorisation checked by multiplying back):", "PASS" if order_full else "FAIL")
ok_all &= order_full
print("  => every nonzero state is on one cycle; (I+J) is a fixed element of GF(2^256)* so (I+J) = T^m for a")
print("     FIXED m: thread k>=1 starts 2^128 + (k-1)m steps after thread 0, independent of the seed.")

print("\nV7 bounded offset probe among threads 0,1,2 (both directions, N = 2^18 steps); positive control")
N = 1 << 18
S0 = seeds[0]
th = {0: list(S0), 1: Jk(S0, 1), 2: CJ(2, S0)}
targets = {k: tuple(v) for k, v in th.items()}
def find_offset(start, want_set, N):
    s = list(start); hits = []
    for i in range(1, N + 1):
        next_(s)
        tup = tuple(s)
        if tup in want_set: hits.append((i, want_set[tup]))
    return hits
found = []
for a in (0, 1, 2):
    others = {targets[b]: b for b in (0, 1, 2) if b != a}
    for i, b in find_offset(th[a], others, N):
        found.append((a, b, i))
print("  offsets < 2^18 found between distinct threads:", found if found else "none")
ctrl = list(S0)
for _ in range(1234): next_(ctrl)
hits = find_offset(S0, {tuple(ctrl): "planted"}, N)
print("  positive control (state planted 1234 steps ahead of thread 0):", hits, "PASS" if hits == [(1234, "planted")] else "FAIL")
ok_all &= (hits == [(1234, "planted")]) and not found
print("  cannot see: offsets >= 2^18 (a run consumes ~2^34 draws per thread); the a-priori bound for a fixed m")
print("  landing within 2^44 of 0, +-2^128 or a multiple is ~2^-211 and is an argument, not a measurement.")

print("\nOVERALL:", "PASS (every check as predicted)" if ok_all else "FAIL (see above)")
sys.exit(0 if ok_all else 1)
