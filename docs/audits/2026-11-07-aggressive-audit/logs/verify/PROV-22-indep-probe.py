#!/usr/bin/env python3
"""Verifier's INDEPENDENT probe for PROV-22 (written from cpp/shared/utils.h:745-789 text, not copied from model.py).
Checks: (1) model-independent transcription agrees that code_jump(k) != J^k for k>=2 on a DIFFERENT seed;
        (2) closed-form predictions the reproducer did not test: k=3 == S1^S3, k=4 == S1^S2^S3^S4;
        (3) MECHANISM CONTROL: the same function with the accumulators re-zeroed inside the j loop equals J^k for all k
            (this is the one-line mutation that isolates the cause; control.sh only varies k);
        (4) J is GF(2)-linear (the assumption behind the closed form), and the JUMP constants are the published
            xoshiro256 ones (as remembered by the verifier -- not fetched; stated as a limitation).
Exit 0 iff every check holds."""
import sys, random
M = (1 << 64) - 1
def rotl(x, k): return ((x << k) | (x >> (64 - k))) & M
def nxt(st):  # utils.h:745-760
    r = (rotl((st[1] * 5) & M, 7) * 9) & M
    t = (st[1] << 17) & M
    st[2] ^= st[0]; st[3] ^= st[1]; st[1] ^= st[2]; st[0] ^= st[3]
    st[2] ^= t; st[3] = rotl(st[3], 45)
    return r
JUMP = [0x180ec6d33cfd0aba, 0xd5a61266f0c9392c, 0xa9582618e03fc9aa, 0x39abdc4529b1661c]
PUBLISHED = [0x180ec6d33cfd0aba, 0xd5a61266f0c9392c, 0xa9582618e03fc9aa, 0x39abdc4529b1661c]
def J(st):  # Blackman/Vigna jump(): fresh zero accumulators every call; returns new state
    st = list(st); acc = [0]*4
    for w in JUMP:
        for b in range(64):
            if (w >> b) & 1: acc = [a ^ s for a, s in zip(acc, st)]
            nxt(st)
    return acc
def code_jump(k, st):  # utils.h:765-789 AS WRITTEN: s0..s3 declared once before `for j`
    st = list(st); s0 = s1 = s2 = s3 = 0
    for _j in range(k):
        for w in JUMP:
            for b in range(64):
                if (w >> b) & 1: s0 ^= st[0]; s1 ^= st[1]; s2 ^= st[2]; s3 ^= st[3]
                nxt(st)
        st[0], st[1], st[2], st[3] = s0, s1, s2, s3
    return st
def fixed_jump(k, st):  # MUTATION: the four `= 0` moved inside the j loop
    st = list(st)
    for _j in range(k):
        s0 = s1 = s2 = s3 = 0
        for w in JUMP:
            for b in range(64):
                if (w >> b) & 1: s0 ^= st[0]; s1 ^= st[1]; s2 ^= st[2]; s3 ^= st[3]
                nxt(st)
        st[0], st[1], st[2], st[3] = s0, s1, s2, s3
    return st
def Jk(k, st):
    for _ in range(k): st = J(st)
    return st
def X(*v):
    out = [0]*4
    for s in v: out = [a ^ b for a, b in zip(out, s)]
    return out
ok = True
def chk(label, cond):
    global ok; ok &= bool(cond); print(f"  {label}: {'OK' if cond else 'FAILED'}")
rng = random.Random(20261108)
seeds = [[rng.getrandbits(64) for _ in range(4)] for _ in range(3)]
seeds.append([0x9E3779B97F4A7C15,0xBF58476D1CE4E5B9,0x94D049BB133111EB,0x2545F4914F6CDD1D])  # model.py's seed, last
print("JUMP constants equal the published xoshiro256 jump constants (verifier's memory, not fetched):", JUMP == PUBLISHED)
for n, S0 in enumerate(seeds):
    print(f"seed[{n}] = {['%016x' % v for v in S0]}")
    S = [Jk(k, S0) for k in range(6)]
    for k in range(6):
        eq = code_jump(k, S0) == S[k]
        chk(f"code_jump({k}) == J^{k}  -> {eq}  (expected {'True' if k <= 1 else 'False'})", eq == (k <= 1))
    chk("code_jump(2) == S1^S2", code_jump(2, S0) == X(S[1], S[2]))
    chk("code_jump(3) == S1^S3           (verifier's own prediction, untested by model.py)", code_jump(3, S0) == X(S[1], S[3]))
    chk("code_jump(4) == S1^S2^S3^S4     (verifier's own prediction, untested by model.py)", code_jump(4, S0) == X(S[1], S[2], S[3], S[4]))
    for k in range(6):
        chk(f"MECHANISM CONTROL fixed_jump({k}) == J^{k}", fixed_jump(k, S0) == S[k])
    chk("every code_jump(k) state nonzero, k=0..5", all(any(code_jump(k, S0)) for k in range(6)))
a, b = seeds[0], seeds[1]
chk("J linear over GF(2): J(a^b) == J(a)^J(b)", J(X(a, b)) == X(J(a), J(b)))
print("RESULT:", "all checks hold" if ok else "A CHECK FAILED")
sys.exit(0 if ok else 1)
