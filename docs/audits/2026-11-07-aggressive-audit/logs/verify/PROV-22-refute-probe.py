#!/usr/bin/env python3
"""PROV-22 REFUTE-lens probe (verifier's own, written from cpp/shared/utils.h as read on 2026-11-08; not the
reproducer author's model.py).

Objections tested:
  O1  transcription: my own transcription of xoshiro_jump() must reproduce the author's k=0,1 agree / k>=2 differ claim.
  O2  closed form: the author says thread k starts at "a J-linear image of the seed". Derive it exactly:
      state_k = (1+J)^(k-1) * J  applied to S0  (k >= 1), where J is the jump polynomial and 1+J is a field element.
  O3  nonzero / pairwise distinct for EVERY seed, not one seed: the multipliers E_k = (1+J)^(k-1) J are nonzero,
      pairwise-distinct elements of GF(2^256) (needs the minimal polynomial P of the xoshiro256 transition to be
      irreducible of degree 256 -- checked here, not assumed).
  O4  the author frames inter-thread overlap as PROBABILISTIC (~threads*2^44/2^256). That framing is wrong in kind:
      because the transition T is GF(2)-linear and the state space is a 1-dim vector space over K = GF(2)[T],
      thread k and thread m are ALWAYS exactly d_{k,m} steps apart where x^d = E_k/E_m in K -- a constant that does
      not depend on the seed. So the streams either overlap on every run or on none. Measure: baby-step/giant-step
      over |d| < 2^34 for every pair among threads 0..7 (14 distinct ratios + inverses). The production per-thread
      segment is <= ceil(10000/T) * (n-1) draws ~ 2^31.6 at T=3, n=10^6, so |d| >= 2^34 means NO overlap at any
      thread count 3..8 at the target profile. Positive controls: x^(+c1) and x^(-c2) planted in the table must be
      found; negative control: a random field element must not be.
  O5  the field arithmetic is tied back to the generator: apply(x^c mod P) to a state == c actual steps of
      xoshiro256starstar(); apply(J) == canonical jump; apply((1+J)J) == code_jump(2, .) from the transcription.
Nothing here builds anything or runs a binary.
"""
import sys, os, time, random, hashlib, subprocess, datetime, platform

REPO = "/Users/gmcas/repos/SP800-90B_EntropyAssessment"
MASK = (1 << 64) - 1
DEG = 256

def rotl(x, k): return ((x << k) | (x >> (64 - k))) & MASK

def step(s):
    """cpp/shared/utils.h xoshiro256starstar() state transition (output discarded)."""
    t = (s[1] << 17) & MASK
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]
    s[2] ^= t
    s[3] = rotl(s[3], 45)

JUMP = [0x180ec6d33cfd0aba, 0xd5a61266f0c9392c, 0xa9582618e03fc9aa, 0x39abdc4529b1661c]

def canonical_jump(s):
    """Blackman/Vigna jump(): accumulators zeroed per call."""
    acc = [0, 0, 0, 0]
    for w in JUMP:
        for b in range(64):
            if (w >> b) & 1:
                for i in range(4): acc[i] ^= s[i]
            step(s)
    s[:] = acc

def code_jump(jump_count, st):
    """My transcription of utils.h:765-789 as read 2026-11-08: s0..s3 declared ONCE, before the j loop."""
    s0 = s1 = s2 = s3 = 0
    for _j in range(jump_count):
        for i in range(4):
            for b in range(64):
                if JUMP[i] & (1 << b):
                    s0 ^= st[0]; s1 ^= st[1]; s2 ^= st[2]; s3 ^= st[3]
                step(st)
        st[0] = s0; st[1] = s1; st[2] = s2; st[3] = s3

def pack(s): return s[0] | (s[1] << 64) | (s[2] << 128) | (s[3] << 192)
def unpack(v): return [(v >> (64 * i)) & MASK for i in range(4)]

def apply_poly(p, s):
    """Apply the GF(2) polynomial p(T) (bit i of p = coefficient of T^i) to state s; p need not be reduced."""
    acc = [0, 0, 0, 0]; cur = list(s); i = 0
    while p >> i:
        if (p >> i) & 1:
            for q in range(4): acc[q] ^= cur[q]
        step(cur); i += 1
    return acc

def bm_gf2(seq):
    """Berlekamp-Massey over GF(2). Returns (connection polynomial C as int, L)."""
    C = 1; B = 1; L = 0; m = 1
    for n in range(len(seq)):
        d = seq[n]
        for i in range(1, L + 1):
            if (C >> i) & 1: d ^= seq[n - i]
        if d:
            Tt = C
            C ^= B << m
            if 2 * L <= n:
                L = n + 1 - L; B = Tt; m = 1
            else:
                m += 1
        else:
            m += 1
    return C, L

def reciprocal(p, deg):
    r = 0
    for i in range(deg + 1):
        if (p >> i) & 1: r |= 1 << (deg - i)
    return r

def pdeg(a): return a.bit_length() - 1

def pmod(a, P):
    dP = pdeg(P)
    while a and pdeg(a) >= dP:
        a ^= P << (pdeg(a) - dP)
    return a

def pmulmod(a, b, P):
    r = 0
    while b:
        if b & 1: r ^= a
        b >>= 1
        a <<= 1
        if (a >> DEG) & 1: a ^= P
    return r

def ppow(a, e, P):
    r = 1
    while e:
        if e & 1: r = pmulmod(r, a, P)
        a = pmulmod(a, a, P); e >>= 1
    return r

def pgcd(a, b):
    while b:
        a, b = b, pmod(a, b)
    return a

def pinv(a, P):
    # a^(2^256 - 2) in GF(2^256)
    return ppow(a, (1 << DEG) - 2, P)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def main():
    t0 = time.time()
    print("# PROV-22 REFUTE probe  %s  host=%s %s  python=%s" % (
        datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"), platform.system(), platform.machine(), sys.version.split()[0]))
    try:
        head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        br = subprocess.run(["git", "-C", REPO, "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    except Exception as e:
        head = br = "unknown(%s)" % e
    print("# git=%s branch=%s" % (head, br))
    print("# source sha256 %s  cpp/shared/utils.h (transcribed, not executed)" % sha256(os.path.join(REPO, "cpp/shared/utils.h")))
    print("# binary sha256 %s  cpp/ea_iid (NAMED per instrument rule 4; NOT run by this probe)" % sha256(os.path.join(REPO, "cpp/ea_iid")))
    print("# no build, no binary run, no input file; pure GF(2) arithmetic on the xoshiro256 transition")
    failures = []
    def check(name, ok, detail=""):
        print("%-6s %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
        if not ok: failures.append(name)

    rng = random.Random(0x5EED_2026_11_08)
    seeds = [[0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB, 0x2545F4914F6CDD1D]] + \
            [[rng.getrandbits(64) for _ in range(4)] for _ in range(3)]

    # ---- O1: transcription reproduces the author's claim
    print("\n## O1 transcription (my own) vs canonical, k = 0..6, 4 seeds")
    agree = {}
    for S0 in seeds:
        for k in range(7):
            a = list(S0); code_jump(k, a)
            b = list(S0)
            for _ in range(k): canonical_jump(b)
            agree.setdefault(k, set()).add(a == b)
    for k in range(7):
        print("  k=%d code==canonical over 4 seeds: %s" % (k, sorted(agree[k])))
    check("O1 k=0,1 agree for every seed", agree[0] == {True} and agree[1] == {True})
    check("O1 k=2..6 disagree for every seed", all(agree[k] == {False} for k in range(2, 7)))

    # ---- minimal polynomial of T
    print("\n## P: minimal polynomial of the xoshiro256 transition T (Berlekamp-Massey on bit 0 of s[0], 600 steps)")
    s = list(seeds[1]); seq = []
    for _ in range(600):
        seq.append(s[0] & 1); step(s)
    C, L = bm_gf2(seq)
    P = reciprocal(C, L)
    print("  BM linear complexity L=%d ; P degree=%d ; P=0x%x" % (L, pdeg(P), P))
    check("P degree 256", pdeg(P) == 256 and L == 256)
    annih = all(apply_poly(P, S0) == [0, 0, 0, 0] for S0 in seeds)
    check("P(T) annihilates T on all 4 seeds (so P is T's minimal polynomial, not just the sequence's)", annih)
    x = 2
    x2_256 = x
    for _ in range(256): x2_256 = pmulmod(x2_256, x2_256, P)
    x2_128 = x
    for _ in range(128): x2_128 = pmulmod(x2_128, x2_128, P)
    irreducible = (x2_256 == x) and (pgcd(x2_128 ^ x, P) == 1)
    check("P irreducible over GF(2) (x^(2^256)==x mod P and gcd(x^(2^128)+x, P)==1) => GF(2)[T] is a field", irreducible)

    # ---- O5: tie field arithmetic to the generator
    print("\n## O5 field arithmetic <-> generator steps")
    c = 100003
    xc = ppow(x, c, P)
    s = list(seeds[2])
    for _ in range(c): step(s)
    check("apply(x^%d mod P) == %d real steps" % (c, c), apply_poly(xc, seeds[2]) == s)
    Jx = pack(JUMP)                      # the jump polynomial, degree < 256 (no reduction needed)
    s = list(seeds[2]); canonical_jump(s)
    check("apply(J) == canonical jump (J = packed JUMP words as a polynomial in T)", apply_poly(Jx, seeds[2]) == s)
    one_plus_J = Jx ^ 1
    check("J == x^(2^128) mod P (the comment's '2^128 calls' is right for ONE jump)", pmod(Jx, P) == x2_128)

    # ---- O2: closed form
    print("\n## O2 closed form: code_jump(k, S0) == ((1+J)^(k-1) J)(T) S0 for k = 1..8, 4 seeds")
    E = {0: 1}
    for k in range(1, 9):
        E[k] = Jx if k == 1 else pmulmod(E[k - 1], one_plus_J, P)
    ok = True
    for S0 in seeds:
        for k in range(1, 9):
            a = list(S0); code_jump(k, a)
            if apply_poly(E[k], S0) != a: ok = False
    check("O2 closed form holds (threads 0..8 start at E_k * S0 with E_k = (1+J)^(k-1) J)", ok)
    s1 = list(seeds[0]); canonical_jump(s1); s2 = list(s1); canonical_jump(s2); s3 = list(s2); canonical_jump(s3)
    a2 = list(seeds[0]); code_jump(2, a2); a3 = list(seeds[0]); code_jump(3, a3)
    check("k=2 == S1^S2 (author's prediction)", a2 == [p ^ q for p, q in zip(s1, s2)])
    check("k=3 == S1^S3 (closed form; the author gave no k=3 form)", a3 == [p ^ q for p, q in zip(s1, s3)])

    # ---- O3: nonzero and pairwise distinct multipliers for threads 0..255
    print("\n## O3 multipliers E_k for k = 0..255: nonzero and pairwise distinct as field elements")
    Ek = [1, pmod(Jx, P)]
    for k in range(2, 256): Ek.append(pmulmod(Ek[-1], one_plus_J, P))
    check("E_k != 0 for all k < 256 (=> every thread's state is nonzero for EVERY nonzero seed)", all(e != 0 for e in Ek))
    check("E_k pairwise distinct (=> no two threads share a state for ANY seed, up to 256 threads)", len(set(Ek)) == 256)

    # ---- O4: deterministic inter-thread offsets, windowed BSGS
    print("\n## O4 inter-thread offsets are seed-independent constants; search |d| < 2^34 for threads 0..7")
    Kmax = 8
    targets = {}
    for k in range(1, Kmax):
        for m in range(0, k):
            name = "thr%d/thr%d" % (k, m)
            R = pmulmod(Ek[k], pinv(Ek[m], P), P)
            if (k, m) == (1, 0):
                print("  %s = J = x^(2^128): canonical, outside any window by construction (skipped)" % name)
                continue
            targets.setdefault(R, []).append(name)
    print("  distinct non-canonical ratios among %d pairs: %d" % (Kmax * (Kmax - 1) // 2, len(targets)))
    c1 = 123456789; c2 = 987654321
    ctl_pos = ppow(x, c1, P); ctl_neg = pinv(ppow(x, c2, P), P)
    neg_ctl = rng.getrandbits(256) & ((1 << 256) - 1)
    neg_ctl = pmod(neg_ctl, P) or 3
    fam = []   # (element, label, sign) ; sign=+1 => d = i*m - j ; sign=-1 (inverse family) => d = j - i*m
    for R, names in targets.items():
        fam.append((R, "+".join(names), +1)); fam.append((pinv(R, P), "+".join(names), -1))
    fam.append((ctl_pos, "CONTROL x^+%d" % c1, +1)); fam.append((pinv(ctl_pos, P), "CONTROL x^+%d" % c1, -1))
    fam.append((ctl_neg, "CONTROL x^-%d" % c2, +1)); fam.append((pinv(ctl_neg, P), "CONTROL x^-%d" % c2, -1))
    fam.append((neg_ctl, "NEGATIVE-CONTROL random element", +1)); fam.append((pinv(neg_ctl, P), "NEGATIVE-CONTROL random element", -1))
    mb = 1 << 14; gs = 1 << 20          # window: d in (-2^34, 2^34)
    table = {}
    tb = time.time()
    for fi, (R, label, sign) in enumerate(fam):
        v = R
        for j in range(mb):
            table[v] = fi * mb + j
            v <<= 1
            if (v >> DEG) & 1: v ^= P
    print("  baby table: %d families x %d = %d entries (%.1fs)" % (len(fam), mb, len(table), time.time() - tb))
    xm = ppow(x, mb, P)
    g = 1; hits = []
    tg = time.time()
    for i in range(gs):
        if g in table:
            code = table[g]; fi, j = divmod(code, mb)
            R, label, sign = fam[fi]
            d = i * mb - j if sign > 0 else j - i * mb
            hits.append((label, d))
        g = pmulmod(g, xm, P)
    print("  giant steps: %d (%.1fs); window |d| < 2^34 = %d draws" % (gs, time.time() - tg, 1 << 34))
    for label, d in hits: print("  HIT  %-45s d = %d" % (label, d))
    check("O4 positive control x^+%d found at d=+%d" % (c1, c1), ("CONTROL x^+%d" % c1, c1) in hits)
    check("O4 positive control x^-%d found at d=-%d" % (c2, c2), ("CONTROL x^-%d" % c2, -c2) in hits)
    check("O4 negative control (random element) NOT found", not any(l.startswith("NEGATIVE") for l, _ in hits))
    thread_hits = [(l, d) for l, d in hits if l.startswith("thr")]
    check("O4 NO thread pair among threads 0..7 is within 2^34 steps of another (so no stream overlap at <= 2^31.6 draws/thread)", not thread_hits,
          "thread hits: %s" % thread_hits if thread_hits else "none")
    # production segment size
    n = 1_000_000; perms = 10_000
    for T in (3, 4, 8):
        seg = -(-perms // T) * (n - 1)
        print("  T=%d threads: per-thread draws <= %d (~2^%.1f) < 2^34 window" % (T, seg, seg.bit_length() - 1 + (seg / (1 << (seg.bit_length() - 1)) - 1)))

    print("\n## summary  elapsed %.1fs  failures=%d %s" % (time.time() - t0, len(failures), failures))
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
