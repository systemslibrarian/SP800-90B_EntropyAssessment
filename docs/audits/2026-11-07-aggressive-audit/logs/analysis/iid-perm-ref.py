#!/usr/bin/env python3
"""Independent transcription of the SP 800-90B 5.1.1-5.1.11 permutation-test
STATISTICS, written from the spec text (PDF p37-43) for the 2026-11-07 audit of
the IID permutation component.  It computes the 19 unpermuted statistics the
C++ prints at -vvv as "Permutation testing: Unpermuted result <name> = <v>",
so the two can be compared on the same input.  It is a probe oracle, not the
audit's py90b reference.

Self-test: `python3 iid-perm-ref.py --selftest` checks the spec's Examples 1-10.
Usage:     `python3 iid-perm-ref.py <file> <bits_per_symbol>` prints JSON.

Spec readings encoded here (cited in iid-permutation.md):
  * Fig. 4 counters (p37): C0 = #(T > Ti), C1 = #(T = Ti); fail if C0+C1 <= 5
    or C0 >= 9995.
  * Conversion I / II (p38): 8-bit non-overlapping blocks, zero-padded; I counts
    ones, II is the big-endian integer (first bit is the MSB: 10001110 -> 142).
  * 5.1.1 excursion: no conversion for binary; uses the SAMPLE VALUES and their
    mean.  5.1.2-5.1.4: Conversion I.  5.1.5/5.1.6: median, binary median is
    0.5, no conversion.  5.1.7/5.1.8: Conversion II.  5.1.9/5.1.10: Conversion
    I.  5.1.11: "144 21 139 0 0 15" encoding, bzip2, no conversion.
  * "binary" means k = 2 (p38 "when the input is binary, i.e., k = 2").  For a
    two-valued input whose values are not {0,1} the conversions are applied to
    the values mapped to {0,1} in value order; excursion and compression see the
    raw values.  This is a reading, flagged as such in the analysis.
"""
import bz2, json, sys


def conversion1(bits):
    return [sum(bits[i:i + 8]) for i in range(0, len(bits), 8)]


def conversion2(bits):
    out = []
    for i in range(0, len(bits), 8):
        blk = bits[i:i + 8] + [0] * (8 - len(bits[i:i + 8]))
        v = 0
        for b in blk:
            v = (v << 1) | b
        out.append(v)
    return out


def excursion(s):
    L = len(s)
    xbar = sum(s) / L            # spec: average of the sample values
    run = 0.0
    best = 0.0
    for i, v in enumerate(s, start=1):
        run += v
        d = abs(run - i * xbar)
        if d > best:
            best = d
    return best


def sprime_directional(s):
    return [(-1 if s[i] > s[i + 1] else 1) for i in range(len(s) - 1)]


def num_runs(sp):
    if not sp:
        return 0
    return 1 + sum(1 for i in range(1, len(sp)) if sp[i] != sp[i - 1])


def longest_run(sp):
    best = run = 1 if sp else 0
    for i in range(1, len(sp)):
        if sp[i] == sp[i - 1]:
            run += 1
        else:
            run = 1
        best = max(best, run)
    return best


def num_inc_dec(sp):
    pos = sum(1 for x in sp if x == 1)
    return max(pos, len(sp) - pos)


def median_of(s):
    v = sorted(s)
    L = len(v)
    return v[L // 2] if L % 2 else (v[L // 2] + v[L // 2 - 1]) / 2


def sprime_median(s, med):
    return [(-1 if x < med else 1) for x in s]


def collisions(s):
    """5.1.7 step 3: i=1; while i<L: smallest j with (s_i..s_{i+j-1}) containing
    a duplicate; append j; i += j."""
    C = []
    L = len(s)
    i = 0                        # 0-based
    while i < L - 1:             # spec 'i < L' with 1-based i
        seen = set()
        j = 0
        found = False
        while i + j < L:
            x = s[i + j]
            j += 1
            if x in seen:
                found = True
                break
            seen.add(x)
        if not found:
            break
        C.append(j)
        i += j
    return C


def periodicity(s, p):
    return sum(1 for i in range(len(s) - p) if s[i] == s[i + p])


def covariance(s, p):
    return sum(s[i] * s[i + p] for i in range(len(s) - p))


def compression(s):
    msg = " ".join(str(int(v)) for v in s).encode("ascii")
    return len(bz2.compress(msg, compresslevel=5))


NAMES = ["excursion", "numDirectionalRuns", "lenDirectionalRuns",
         "numIncreasesDecreases", "numRunsMedian", "lenRunsMedian",
         "avgCollision", "maxCollision",
         "periodicity(1)", "periodicity(2)", "periodicity(8)", "periodicity(16)", "periodicity(32)",
         "covariance(1)", "covariance(2)", "covariance(8)", "covariance(16)", "covariance(32)",
         "compression"]


def all_stats(raw):
    """raw: list of ints (the sample values).  Returns dict name -> value."""
    distinct = sorted(set(raw))
    k = len(distinct)
    out = {}
    out["excursion"] = excursion(raw)
    if k == 2:
        bits = [distinct.index(v) for v in raw]      # {a<b} -> {0,1}
        c1 = conversion1(bits)
        c2 = conversion2(bits)
        sp = sprime_directional(c1)
        out["numDirectionalRuns"] = num_runs(sp)
        out["lenDirectionalRuns"] = longest_run(sp)
        out["numIncreasesDecreases"] = num_inc_dec(sp)
        spm = sprime_median(bits, 0.5)
        out["numRunsMedian"] = num_runs(spm)
        out["lenRunsMedian"] = longest_run(spm)
        C = collisions(c2)
        out["avgCollision"] = (sum(C) / len(C)) if C else float("nan")
        out["maxCollision"] = max(C) if C else 0
        for p in (1, 2, 8, 16, 32):
            out[f"periodicity({p})"] = periodicity(c1, p)
            out[f"covariance({p})"] = covariance(c1, p)
    else:
        sp = sprime_directional(raw)
        out["numDirectionalRuns"] = num_runs(sp)
        out["lenDirectionalRuns"] = longest_run(sp)
        out["numIncreasesDecreases"] = num_inc_dec(sp)
        med = median_of(raw)
        spm = sprime_median(raw, med)
        out["numRunsMedian"] = num_runs(spm)
        out["lenRunsMedian"] = longest_run(spm)
        C = collisions(raw)
        out["avgCollision"] = (sum(C) / len(C)) if C else float("nan")
        out["maxCollision"] = max(C) if C else 0
        for p in (1, 2, 8, 16, 32):
            out[f"periodicity({p})"] = periodicity(raw, p)
            out[f"covariance({p})"] = covariance(raw, p)
        out["_median"] = med
    out["compression"] = compression(raw)
    out["_k"] = k
    out["_L"] = len(raw)
    out["_mean"] = sum(raw) / len(raw)
    return out


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'} {name}: got {got!r} want {want!r}")
        if not ok:
            fails += 1

    bits20 = [1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1]
    chk("Conversion I example (p38)", conversion1(bits20), [4, 6, 2])
    chk("Conversion II example (p38)", conversion2(bits20), [142, 219, 48])
    chk("Ex1 excursion (p39)", excursion([2, 15, 4, 10, 9]), 6)
    s2 = [2, 2, 2, 5, 7, 7, 9, 3, 1, 4, 4]
    chk("Ex2 numDirectionalRuns (p39)", num_runs(sprime_directional(s2)), 3)
    chk("Ex3 lenDirectionalRuns (p40)", longest_run(sprime_directional(s2)), 6)
    chk("Ex4 numIncreasesDecreases (p40)", num_inc_dec(sprime_directional(s2)), 8)
    s5 = [5, 15, 12, 1, 13, 9, 4]
    chk("Ex5 median (p41)", median_of(s5), 9)
    chk("Ex5 numRunsMedian (p41)", num_runs(sprime_median(s5, 9)), 5)
    chk("Ex6 lenRunsMedian (p41)", longest_run(sprime_median(s5, 9)), 2)
    s7 = [2, 1, 1, 2, 0, 1, 0, 1, 1, 2]
    chk("Ex7 collision list C (p41-42)", collisions(s7), [3, 4, 2])
    chk("Ex7 avgCollision (p42)", sum(collisions(s7)) / len(collisions(s7)), 3)
    chk("Ex8 maxCollision (p42)", max(collisions(s7)), 4)
    chk("Ex9 periodicity p=2 (p42)", periodicity([2, 1, 2, 1, 0, 1, 0, 1, 1, 2], 2), 5)
    chk("Ex10 covariance p=2 (p43)", covariance([5, 2, 6, 10, 12, 3, 1], 2), 164)
    chk("5.1.11 encoding (p43)", " ".join(str(v) for v in [144, 21, 139, 0, 0, 15]), "144 21 139 0 0 15")
    print("SELFTEST", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        sys.exit(1 if selftest() else 0)
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    bps = int(sys.argv[2])
    mask = (1 << bps) - 1
    raw = [b & mask for b in open(sys.argv[1], "rb").read()]
    print(json.dumps(all_stats(raw), indent=1, sort_keys=True))
