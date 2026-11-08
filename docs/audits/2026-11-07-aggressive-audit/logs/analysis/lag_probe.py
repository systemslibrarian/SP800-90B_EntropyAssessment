#!/usr/bin/env python3
"""Analysis-phase probe for SP 800-90B 6.3.8 (Lag prediction estimate).

This is NOT the independent reference (reference/py90b/); its author has read
cpp/non_iid/lag_test.h, so it cannot serve as one. It is a transcription of the
SPEC TEXT (PDF p. 59-60) used to (1) check itself against the standard's own
worked example (D=3, S=(2,1,3,2,1,3,1,3,1,2)), (2) generate tiny inputs, and
(3) compute the per-spec C, r, N, P_global, P_global', P_local, min-entropy for
each, so the orchestrator can compare them against the C++ -vvv labels.

Everything is written to files; nothing is piped.
"""
import math
import os
import random
import struct
import sys
import hashlib
import json

ZTEXT = 2.576                    # printed in the text, step 5
ZEXACT = 2.5758293035489008      # exact 0.995 quantile (fork's ZALPHA, D-1)
LOG_ALPHA = math.log(0.99)


def lag_counts(S, D=128):
    """Steps 1-4 of 6.3.8, transcribed with 1-based spec indices.

    Returns (C, r, N, correct list)."""
    L = len(S)
    N = L - 1
    scoreboard = [0] * (D + 1)       # scoreboard[1..D]
    winner = 1
    correct = [0] * N
    for i in range(2, L + 1):        # step 3: for i = 2 to L
        si = S[i - 1]
        # step 3a: lag_d = s_{i-d} if d < i else Null
        # step 3b: prediction = lag_winner
        prediction = S[i - winner - 1] if winner < i else None
        # step 3c
        if prediction is not None and prediction == si:
            correct[i - 2] = 1
        # step 3d: for d = 1..D, if lag_d = s_i: scoreboard_d += 1;
        #          if scoreboard_d >= scoreboard_winner: winner = d
        for d in range(1, D + 1):
            if d < i and S[i - d - 1] == si:
                scoreboard[d] += 1
                if scoreboard[d] >= scoreboard[winner]:
                    winner = d
    C = sum(correct)
    # step 6: r = 1 + longest run of ones in correct
    longest = cur = 0
    for c in correct:
        cur = cur + 1 if c else 0
        longest = max(longest, cur)
    r = longest + 1
    return C, r, N, correct


def p_global_prime(C, N, Z):
    """Step 5."""
    pg = C / N
    if pg == 0:
        return pg, 1.0 - 0.01 ** (1.0 / N)
    return pg, min(1.0, pg + Z * math.sqrt(pg * (1.0 - pg) / (N - 1.0)))


def f_runs(p, r, N, iters):
    """Step 6 right-hand side, in log form; iters=10 is the text (x = x_10),
    iters=None iterates to convergence (what the C++ does, F08)."""
    if p <= 0.0:
        return 0.0            # Pr(no run) = 1 -> log 1 = 0
    if p >= 1.0:
        return -math.inf
    q = 1.0 - p
    x = 1.0
    if iters is None:
        for _ in range(200):
            xn = 1.0 + q * p ** r * x ** (r + 1)
            if xn - x <= 2.2e-16 * xn:
                x = xn
                break
            x = xn
    else:
        for _ in range(iters):
            x = 1.0 + q * p ** r * x ** (r + 1)
    a = 1.0 - p * x
    b = (r + 1.0 - r * x) * q
    if a <= 0.0 or b <= 0.0:
        return -math.inf
    return math.log(a) - math.log(b) - (N + 1.0) * math.log(x)


def p_local(r, N, iters=10):
    """Step 6: binary search for P_local on [0,1]. f is decreasing in p."""
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if mid == lo or mid == hi:
            break
        if f_runs(mid, r, N, iters) > LOG_ALPHA:
            lo = mid
        else:
            hi = mid
    return hi   # the upper end of the bracket: conservative side


def estimate(S, k, D=128):
    C, r, N, correct = lag_counts(S, D)
    out = {"C": C, "r": r, "N": N}
    for tag, Z in (("text", ZTEXT), ("exact", ZEXACT)):
        pg, pgp = p_global_prime(C, N, Z)
        pl10 = p_local(r, N, 10)
        plinf = p_local(r, N, None)
        out["P_global"] = pg
        out["P_global_prime_" + tag] = pgp
        out["P_local_x10"] = pl10
        out["P_local_converged"] = plinf
        out["min_entropy_" + tag + "_x10"] = -math.log2(max(pgp, pl10, 1.0 / k))
        out["min_entropy_" + tag + "_conv"] = -math.log2(max(pgp, plinf, 1.0 / k))
    return out, correct


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    audit = os.path.abspath(os.path.join(here, "..", ".."))
    corpus = os.path.join(audit, "corpus")
    logs = os.path.join(audit, "logs")
    os.makedirs(corpus, exist_ok=True)
    report = {}

    # ---- (1) the standard's worked example, D = 3 (PDF p. 60)
    S = [2, 1, 3, 2, 1, 3, 1, 3, 1, 2]
    C, r, N, correct = lag_counts(S, D=3)
    pg, pgp = p_global_prime(C, N, ZTEXT)
    pl = p_local(r, N, 10)
    ex = {
        "correct": correct, "C": C, "r": r, "N": N,
        "P_global": pg, "P_global_prime_text": pgp, "P_local_x10": pl,
        "min_entropy": -math.log2(max(pgp, pl, 1.0 / 3)),
        "expected_from_text": {"correct": [0, 0, 0, 1, 1, 0, 0, 0, 0],
                                "P_global": 0.2222, "P_global_prime": 0.6008,
                                "P_local": 0.1167, "min_entropy": 0.735},
    }
    ex["selfcheck_pass"] = (correct == ex["expected_from_text"]["correct"]
                            and abs(pgp - 0.6008) < 5e-4
                            and abs(pl - 0.1167) < 5e-4
                            and abs(ex["min_entropy"] - 0.735) < 5e-3)
    report["worked_example_D3"] = ex
    # the same example with D = 128 (what the tool can actually run)
    C, r, N, correct = lag_counts(S, D=128)
    report["worked_example_D128"] = {"correct": correct, "C": C, "r": r, "N": N}

    # ---- (2) tiny inputs
    inputs = {}
    rng = random.Random(20261107)

    def put(name, syms, bits):
        path = os.path.join(corpus, name)
        with open(path, "wb") as fh:
            fh.write(bytes(syms))
        inputs[name] = {"path": path, "bits": bits, "L": len(syms),
                        "sha256": sha256_file(path), "symbols": syms}

    put("lag-rand8-5000.bin", [rng.randrange(256) for _ in range(5000)], 8)
    put("lag-k3-tieheavy-5000.bin",
        [rng.choice([0, 0, 0, 1, 1, 2]) for _ in range(5000)], 8)
    base128 = [rng.randrange(256) for _ in range(128)]
    put("lag-period128-8bit-5000.bin", [base128[i % 128] for i in range(5000)], 8)
    base129 = [rng.randrange(256) for _ in range(129)]
    put("lag-period129-8bit-5000.bin", [base129[i % 129] for i in range(5000)], 8)
    base127 = [rng.randrange(256) for _ in range(127)]
    put("lag-period127-8bit-5000.bin", [base127[i % 127] for i in range(5000)], 8)
    b128 = [rng.randrange(2) for _ in range(128)]
    put("lag-period128-1bit-20000.bin", [b128[i % 128] for i in range(20000)], 1)
    b129 = [rng.randrange(2) for _ in range(129)]
    put("lag-period129-1bit-20000.bin", [b129[i % 129] for i in range(20000)], 1)
    put("lag-rand1-20000.bin", [rng.randrange(2) for _ in range(20000)], 1)
    # a stream where lags 1 and 2 tie constantly: 0,0,1,1,0,0,1,1,...  (period 4)
    put("lag-tie-0011-1bit-20000.bin", [(i // 2) & 1 for i in range(20000)], 1)
    # alternating 0101 (lag 1 always wrong, lag 2 always right)
    put("lag-alt-0101-1bit-20000.bin", [i & 1 for i in range(20000)], 1)
    # counter 0..255 cycling: lags 1..128 never match, C = 0 path
    put("lag-counter8-5000.bin", [i & 255 for i in range(5000)], 8)
    # minimum-length boundaries
    put("lag-L3-1bit.bin", [0, 1, 0], 1)
    put("lag-L2-1bit.bin", [0, 1], 1)
    put("lag-L3-8bit.bin", [5, 7, 5], 8)

    # ---- (3) spec figures for each
    for name, info in inputs.items():
        syms = info.pop("symbols")
        k = len(set(syms))
        if info["L"] < 3:
            info["spec"] = "L < 3: N = L-1 < 2, step 5 divides by N-1 = 0; no estimate"
            continue
        est, _ = estimate(syms, k)
        est["k"] = k
        info["spec"] = est
        if info["bits"] == 8 and k > 2:
            bits = []
            for s in syms:
                bits.extend((s >> (7 - j)) & 1 for j in range(8))
            best, _ = estimate(bits, 2)
            info["spec_bitstring"] = best
    report["inputs"] = inputs

    out = os.path.join(logs, "analysis-lag-spec-figures.json")
    with open(out, "w") as fh:
        json.dump(report, fh, indent=1)
    with open(os.path.join(logs, "analysis-lag-probe.log"), "w") as fh:
        fh.write("worked example D=3 selfcheck_pass=%s\n" % ex["selfcheck_pass"])
        fh.write(json.dumps(ex, indent=1) + "\n")
        fh.write("wrote %d inputs to %s\n" % (len(inputs), corpus))
        fh.write("figures in %s\n" % out)


if __name__ == "__main__":
    main()
