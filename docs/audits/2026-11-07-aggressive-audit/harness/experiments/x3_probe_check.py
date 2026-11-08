#!/usr/bin/env python3
"""x3_probe_check.py -- compare the production binary's Literal MultiMMC (C, r, N) on the three
X3 light-probe files (read by label from logs/experiments/x3-probe-*.stdout) with the C++ model's
predictions in x3-validation.json.  Writes logs/experiments/x3-probe-vs-model.json."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.dirname(os.path.dirname(HERE))
LOGS = os.path.join(AUD, "logs", "experiments")
val = json.load(open(os.path.join(HERE, "x3-validation.json")))
pred = {
    "x3-probe-prefix20000": val["prefix20000_at_real_cap"]["cpp"],
    "x3-probe-scaled-naive": val["variants"]["naive"]["scaled_file_at_real_cap_no_saturation"]["cpp"],
    "x3-probe-scaled-gadget": val["variants"]["gadget"]["scaled_file_at_real_cap_no_saturation"]["cpp"],
}
rx = re.compile(r"^Literal MultiMMC Prediction Estimate: (C|r|N) = (\d+)$")
out, ok_all = {}, True
for name, p in pred.items():
    got = {}
    with open(os.path.join(LOGS, name + ".stdout"), encoding="utf-8", errors="replace") as f:
        for line in f:
            m = rx.match(line.strip())
            if m:
                got[m.group(1)] = int(m.group(2))
    rc = open(os.path.join(LOGS, name + ".rc")).read().strip()
    meta = open(os.path.join(LOGS, name + ".meta")).read()
    binsha = next((l.split()[1] for l in meta.splitlines() if l.startswith("sha256 ") and l.rstrip().endswith("ea_non_iid") or (l.startswith("sha256 ") and "/cpp/ea_non_iid" in l)), None)
    ok = got.get("C") == p["C"] and got.get("r") == p["r"]
    ok_all &= ok
    out[name] = {"rc": rc, "binary_sha256": binsha, "tool": got, "cpp_model": {"C": p["C"], "r": p["r"]},
                 "match": ok, "note": "EA_ALLOW_SHORT_DATASET=1 run, non-compliant; no saturation at cap 100,000"}
    print(f"{name}: tool C={got.get('C')} r={got.get('r')} N={got.get('N')}  model C={p['C']} r={p['r']}  {'MATCH' if ok else 'MISMATCH'}  rc={rc}")
json.dump({"all_match": ok_all, "probes": out}, open(os.path.join(LOGS, "x3-probe-vs-model.json"), "w"), indent=1)
print("ALL MATCH" if ok_all else "MISMATCH -- the C++ model is not trustworthy")
sys.exit(0 if ok_all else 1)
