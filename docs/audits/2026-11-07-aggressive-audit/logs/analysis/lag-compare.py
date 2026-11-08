#!/usr/bin/env python3
"""Compare the C++ -vvv labelled Lag lines with the spec-transcription figures.
Labelled reads only (instrument rule 5). Writes logs/analysis-lag-compare.log."""
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__)); audit = os.path.abspath(os.path.join(here, "..", ".."))
logs = os.path.join(audit, "logs")
fig = json.load(open(os.path.join(logs, "analysis-lag-spec-figures.json")))
LAB = re.compile(r"^(Bitstring|Literal) Lag Prediction Estimate: (.+?) = (.+)$")
NOTE = re.compile(r"^(Bitstring|Literal) Lag Prediction Estimate: (P_local can't change the result\.)$")
WARN = re.compile(r"not enough samples to run lag test")
out = []
worst = 0.0
for name, info in fig["inputs"].items():
    stem = name[:-4]
    path = os.path.join(logs, "analysis-lag-cpp-%s.log" % stem)
    if not os.path.exists(path):
        out.append("%s: NO C++ LOG (%s)" % (name, path)); continue
    txt = open(path, encoding="utf-8", errors="replace").read().splitlines()
    got = {"Bitstring": {}, "Literal": {}}
    warn = any(WARN.search(l) for l in txt)
    for l in txt:
        m = LAB.match(l.strip())
        if m:
            got[m.group(1)][m.group(2)] = m.group(3).strip()
        m = NOTE.match(l.strip())
        if m:
            got[m.group(1)]["P_local"] = "cant-change"
    out.append("== %s  (L=%d, bits=%d, sha256=%s)" % (name, info["L"], info["bits"], info["sha256"][:16]))
    out.append("   lag_test 'not enough samples' warning present: %s" % warn)
    spec = info["spec"]
    if isinstance(spec, str):
        out.append("   spec: %s" % spec)
        out.append("   C++ Literal labels: %s" % (got["Literal"] or "none"))
        out.append("   C++ Bitstring labels: %s" % (got["Bitstring"] or "none"))
        continue
    def cmp(path_label, cpp, sp):
        global worst
        for key, skey in (("C", "C"), ("r", "r"), ("N", "N")):
            c = cpp.get(key)
            line = "   %-9s %-10s cpp=%-24s spec=%-24s" % (path_label, key, c, sp[skey])
            line += "  MATCH" if c is not None and int(c) == sp[skey] else "  ** MISMATCH **"
            out.append(line)
        for key, skey in (("P_global", "P_global"), ("P_global'", "P_global_prime_exact")):
            c = cpp.get(key)
            if c is None:
                out.append("   %-9s %-10s cpp=MISSING" % (path_label, key)); continue
            d = abs(float(c) - sp[skey]); worst = max(worst, d)
            out.append("   %-9s %-10s cpp=%-24s spec(exactZ)=%-24.17g |d|=%.3g  text-Z would be %.17g" % (path_label, key, c, sp[skey], d, sp.get("P_global_prime_text", sp["P_global"])))
        c = cpp.get("P_local")
        if c == "cant-change":
            flag = "consistent" if sp["P_local_converged"] <= max(sp["P_global_prime_exact"], 1.0 / sp.get("k", 2)) + 1e-12 else "** spec P_local EXCEEDS curMax: skip is WRONG **"
            out.append("   %-9s %-10s cpp=can't change   spec P_local(x10)=%.17g conv=%.17g  curMax=%.17g  -> %s" % (path_label, "P_local", sp["P_local_x10"], sp["P_local_converged"], max(sp["P_global_prime_exact"], 1.0 / sp.get("k", 2)), flag))
        elif c is None:
            out.append("   %-9s P_local    cpp=MISSING" % path_label)
        else:
            d10 = float(c) - sp["P_local_x10"]; dc = float(c) - sp["P_local_converged"]
            out.append("   %-9s %-10s cpp=%-24s spec x10=%.17g (cpp-spec=%+.3g)  conv=%.17g (cpp-spec=%+.3g)" % (path_label, "P_local", c, sp["P_local_x10"], d10, sp["P_local_converged"], dc))
        c = cpp.get("min entropy")
        if c is not None:
            d = float(c) - sp["min_entropy_exact_conv"]
            out.append("   %-9s %-10s cpp=%-24s spec(exactZ,conv)=%.17g (cpp-spec=%+.3g)  spec(textZ,x10)=%.17g" % (path_label, "minH", c, sp["min_entropy_exact_conv"], d, sp["min_entropy_text_x10"]))
    if got["Literal"]:
        cmp("Literal", got["Literal"], spec)
    else:
        out.append("   Literal: no labels in C++ log")
    if "spec_bitstring" in info:
        if got["Bitstring"]:
            cmp("Bitstring", got["Bitstring"], info["spec_bitstring"])
        else:
            out.append("   Bitstring: expected (k>2) but no labels in C++ log")
    elif got["Bitstring"]:
        out.append("   Bitstring: C++ printed labels but spec had no bitstring path (k<=2): %s" % got["Bitstring"])
out.append("")
out.append("worked example D=3 selfcheck_pass=%s" % fig["worked_example_D3"]["selfcheck_pass"])
out.append("largest |P_global or P_global'| difference over all inputs: %.3g" % worst)
open(os.path.join(logs, "analysis-lag-compare.log"), "w").write("\n".join(out) + "\n")
print("\n".join(out))
