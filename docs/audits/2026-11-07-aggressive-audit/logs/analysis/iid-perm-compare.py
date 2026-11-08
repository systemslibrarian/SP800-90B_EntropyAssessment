#!/usr/bin/env python3
"""Compare the C++ 'Unpermuted result' lines with the Python reference JSON
for each probe, and compare the C[i][*] tables of two runs on the same input.
Labelled reads only (instrument rule 5): every value is found by its name."""
import json, math, re, sys
from pathlib import Path

logs = Path(sys.argv[1])
pairs = [("p1-w1", "analysis-iid-perm-cpp-p1-w1-runA.log", "analysis-iid-perm-ref-p1-w1.json"),
         ("p2-w3", "analysis-iid-perm-cpp-p2-w3.log", "analysis-iid-perm-ref-p2-w3.json"),
         ("p3-w8", "analysis-iid-perm-cpp-p3-w8.log", "analysis-iid-perm-ref-p3-w8.json")]

UNP = re.compile(r"^Permutation testing: Unpermuted result (\S+) = (\S+)$")
ROW = re.compile(r"^\s*(\S+?)(\*?)\s+(\d+)\s+(\d+)\s+(\d+)\s*$")


def parse_cpp(path):
    stats, table, verdict, exit_ = {}, {}, None, None
    for line in path.read_text().splitlines():
        m = UNP.match(line)
        if m:
            stats[m.group(1)] = float(m.group(2))
            continue
        m = ROW.match(line)
        if m and m.group(1) in NAMES:
            table[m.group(1)] = (m.group(2) == "*", int(m.group(3)), int(m.group(4)), int(m.group(5)))
            continue
        if line.startswith("IID permutation tests: "):
            verdict = line.split(": ", 1)[1]
        if line.startswith("exit="):
            exit_ = int(line.split("=")[1])
    return stats, table, verdict, exit_


NAMES = {"excursion", "numDirectionalRuns", "lenDirectionalRuns", "numIncreasesDecreases",
         "numRunsMedian", "lenRunsMedian", "avgCollision", "maxCollision",
         "periodicity(1)", "periodicity(2)", "periodicity(8)", "periodicity(16)", "periodicity(32)",
         "covariance(1)", "covariance(2)", "covariance(8)", "covariance(16)", "covariance(32)",
         "compression"}

total_mismatch = 0
for tag, cpp_name, ref_name in pairs:
    stats, table, verdict, exit_ = parse_cpp(logs / cpp_name)
    ref = json.loads((logs / ref_name).read_text())
    print(f"=== {tag}: cpp exit={exit_} verdict={verdict} k={ref['_k']} L={ref['_L']} mean={ref['_mean']}"
          + (f" median={ref['_median']}" if "_median" in ref else ""))
    if len(stats) != 19:
        print(f"  ERROR: expected 19 unpermuted statistics, found {len(stats)}")
        total_mismatch += 1
    for name in sorted(NAMES):
        c = stats.get(name)
        r = ref.get(name)
        if c is None or r is None:
            print(f"  MISSING {name}: cpp={c} ref={r}")
            total_mismatch += 1
            continue
        same = (math.isnan(c) and math.isnan(r)) or math.isclose(c, r, rel_tol=1e-12, abs_tol=1e-9)
        flag = "ok  " if same else "DIFF"
        if not same:
            total_mismatch += 1
        row = table.get(name)
        rowtxt = f"C0={row[1]} C1={row[2]} C2={row[3]}{' FAIL' if row[0] else ''}" if row else "(no table row)"
        print(f"  {flag} {name:24s} cpp={c!r:24} ref={r!r:24} {rowtxt}")
    if len(table) != 19:
        print(f"  NOTE: results table rows found = {len(table)} (expected 19 at -vvv)")

# seed-liveness: two runs on the same input must differ somewhere in the counters
sa, ta, va, ea = parse_cpp(logs / "analysis-iid-perm-cpp-p1-w1-runA.log")
sb, tb, vb, eb = parse_cpp(logs / "analysis-iid-perm-cpp-p1-w1-runB.log")
print("=== seed liveness (p1 run A vs run B)")
print(f"  unpermuted statistics identical across runs: {sa == sb}")
diff_rows = [n for n in sorted(NAMES) if ta.get(n) != tb.get(n)]
print(f"  counter rows that differ: {len(diff_rows)} of {len(ta)}: {diff_rows}")
for n in diff_rows:
    print(f"    {n:24s} A={ta[n][1:]} B={tb[n][1:]}")
print(f"  verdict A={va} B={vb}; exit A={ea} B={eb}")
print(f"TOTAL statistic mismatches across the three probes: {total_mismatch}")
