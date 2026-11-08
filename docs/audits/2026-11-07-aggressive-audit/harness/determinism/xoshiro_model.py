#!/usr/bin/env python3
"""xoshiro_model.py -- independent re-check of the per-thread RNG stream claim.

logs/analysis/iid-permutation.md says cpp/shared/utils.h:xoshiro_jump(k, s) is NOT k
canonical Blackman/Vigna jumps for k >= 2 because its four accumulators are declared
once, outside the `for j < jump_count` loop, and never re-zeroed.  Each OpenMP thread t
in permutation_tests() (permutation_tests.h:649) and in restart_main.cpp:simulateBound
(:313) calls xoshiro_jump(t, seed_copy).  This file re-derives the consequence from the
code text and checks it by a different route than the analysis did:

  Let J be the canonical jump (linear over GF(2) on the 256-bit state).  With the
  accumulator carried across iterations, iteration j forms acc_{j+1} = acc_j XOR J(s_j)
  and then sets s_{j+1} = acc_{j+1}.  So s_1 = J S0, s_2 = J S0 + J^2 S0, and in general

        s_k = J (I + J)^(k-1) S0          (polynomial in J over GF(2); the analysis
                                           only predicted the k = 2 case S1 + S2)

  k = 0, 1 coincide with the canonical J^k; every k >= 2 differs.  The checks below:
   Q1 code_jump(k) == canonical J^k only for k in {0, 1}
   Q2 code_jump(k) == J (I+J)^(k-1) S0 for k = 2..9 (the closed form above)
   Q3 for 10 threads (OMP_NUM_THREADS=10 on this 10-core host) and 16 seeds, the ten
      thread states are pairwise distinct and non-zero (a collision would make two
      threads generate identical permutations; a zero state would be a stuck generator)
   Q4 the FIRST output drawn by each of the 10 thread streams is distinct (the quantity
      the shuffle actually consumes)

What this model cannot see (rule 18): it is a model of the source text, not a run of
the binary; it says nothing about the shuffle's statistical quality (uniform under any
non-zero state -- the analysis checked Lemire's draw exhaustively) nor about whether the
streams overlap within 2^31 draws (not computable; the analysis's probability bound
stands).  The practical consequence for THIS phase is stated in RESULTS.md: with a
fixed seed the permutation SET depends on the thread count even if the jump were
canonical (static `omp for` partition + one stream per thread), so counter changes
across thread counts are expected and are not, on their own, evidence of a defect.

Output: a plain log on stdout; exit 0 only if Q1..Q4 all hold.
"""
import sys

MASK = (1 << 64) - 1
JUMP = [0x180ec6d33cfd0aba, 0xd5a61266f0c9392c, 0xa9582618e03fc9aa, 0x39abdc4529b1661c]


def rotl(x, k):
    return ((x << k) | (x >> (64 - k))) & MASK


def step(s):
    """xoshiro256** next(): returns the output and advances s in place (utils.h:745-760)."""
    out = (rotl((s[1] * 5) & MASK, 7) * 9) & MASK
    t = (s[1] << 17) & MASK
    s[2] ^= s[0]
    s[3] ^= s[1]
    s[1] ^= s[2]
    s[0] ^= s[3]
    s[2] ^= t
    s[3] = rotl(s[3], 45)
    return out


def J(s):
    """Canonical jump: returns the jumped state (does not mutate its argument)."""
    s = list(s)
    acc = [0, 0, 0, 0]
    for w in JUMP:
        for b in range(64):
            if (w >> b) & 1:
                for i in range(4):
                    acc[i] ^= s[i]
            step(s)
    return acc


def code_jump(k, s):
    """utils.h:765-789 transcribed: accumulators declared ONCE, outside the j loop."""
    s = list(s)
    acc = [0, 0, 0, 0]                      # uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for _ in range(k):
        for w in JUMP:
            for b in range(64):
                if (w >> b) & 1:
                    for i in range(4):
                        acc[i] ^= s[i]
                step(s)
        s = list(acc)                       # state <- accumulators, which are NOT reset
    return s


def xor(a, b):
    return [x ^ y for x, y in zip(a, b)]


def closed_form(k, s0):
    """J (I+J)^(k-1) S0 computed by repeated application: v <- v + J v, (k-1) times, then J."""
    v = list(s0)
    for _ in range(k - 1):
        v = xor(v, J(v))
    return J(v)


def seeds(n):
    """n fixed, distinct, non-zero 256-bit seeds (splitmix-style, so nothing here is random)."""
    x = 0x9E3779B97F4A7C15
    out = []
    for _ in range(n):
        s = []
        for _ in range(4):
            x = (x + 0x9E3779B97F4A7C15) & MASK
            z = x
            z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
            z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
            s.append(z ^ (z >> 31))
        out.append(s)
    return out


def main():
    ok = True
    S0 = seeds(1)[0]
    print("Q1: code_jump(k) vs canonical J^k, k = 0..5")
    for k in range(6):
        canon = list(S0)
        for _ in range(k):
            canon = J(canon)
        same = code_jump(k, S0) == canon
        expect = (k <= 1)
        print(f"  k={k}: equal={same}  expected_equal={expect}  {'ok' if same == expect else 'UNEXPECTED'}")
        ok &= (same == expect)
    print("Q2: code_jump(k) == J (I+J)^(k-1) S0, k = 2..9  (closed form derived here)")
    for k in range(2, 10):
        same = code_jump(k, S0) == closed_form(k, S0)
        print(f"  k={k}: {same}")
        ok &= same
    print("Q3: 10 thread states, 16 seeds: pairwise distinct and non-zero")
    collisions = zeros = 0
    for s in seeds(16):
        states = [tuple(code_jump(t, s)) for t in range(10)]
        zeros += sum(1 for st in states if not any(st))
        collisions += len(states) - len(set(states))
    print(f"  zero states: {zeros}; colliding thread states: {collisions}")
    ok &= (zeros == 0 and collisions == 0)
    print("Q4: first output of each of the 10 thread streams distinct, 16 seeds")
    coll = 0
    for s in seeds(16):
        firsts = []
        for t in range(10):
            st = code_jump(t, s)
            firsts.append(step(st))
        coll += len(firsts) - len(set(firsts))
    print(f"  colliding first outputs: {coll}")
    ok &= (coll == 0)
    print("CONSEQUENCE (not a defect in this phase's sense): threads 0 and 1 use J^0 S0 and J^1 S0 as the")
    print("  comment promises; thread t >= 2 uses J (I+J)^(t-1) S0, a non-zero state at an unknown offset")
    print("  in the single 2^256-1 cycle, so 'non-overlapping' is probabilistic rather than guaranteed.")
    print("  Only OMP_NUM_THREADS >= 3 is affected.  The permutation SET already depends on the thread")
    print("  count with a fixed seed because `omp for` partitions the 10,000 iterations and each thread")
    print("  advances its own stream, so counter differences across thread counts are expected whatever")
    print("  the jump does; a VERDICT that depends on thread count would not be.")
    print(f"RESULT: {'all checks hold' if ok else 'A CHECK FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
