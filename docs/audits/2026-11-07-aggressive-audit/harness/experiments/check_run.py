#!/usr/bin/env python3
"""check_run.py -- labelled reader for one run recorded by run_one.sh (instrument rule 5: every
value is read by its label, never by position), plus a pair comparison.

  check_run.py <name> [--json PATH] [--tool non_iid|iid|restart]
      reads logs/experiments/<name>.{stdout,stderr,rc,meta} (and the JSON report if given),
      writes logs/experiments/<name>.check.json and prints a one-line summary.
  check_run.py --compare <nameA> <nameB> [--truth T]
      prints Assessed(A), Assessed(B), B/A, A-B and each against the truth T (bits/sample).

What it extracts from the -vv text (ea_non_iid / ea_iid):
  loaded            'Loaded N samples of K distinct W-bit-wide symbols'
  narrower_warning  'Warning: Symbols appear to be narrower than described.'
  refusal           the 3.1.1 refusal line, the one-symbol refusal, the restart size refusal
  short_escape      the EA_ALLOW_SHORT_DATASET warning (run is non-compliant)
  estimates         every '<Block> <Estimator> Estimate: <label> = <value>' line, grouped
  h_original, h_bitstring, h_bitstring_per_symbol, assessed   the four summary lines
  degenerate        every estimate/summary value that is nan, inf, -inf or -0 (as printed)
  min_of_printed    the minimum over the printed 'min entropy' values per block, to compare
                    with the printed H_original / H_bitstring (a NaN replacing the running
                    minimum at an unguarded fold -- aggregation.md 2.2 -- would show here)
From the JSON: errorLevel, errorClass, errorMessage, nonCompliantShortDataset, bitsPerSymbol,
bitsPerSymbolInferred, subset*, sha256, every test case's literalEstimateNotRun /
bitstringEstimateNotRun, hOriginal/hBitstring/hAssessed, and for ea_restart the Overall
h_r/h_c/h_i and which cases carry h_r / h_c.
From .rc: the exit status (an absent line is NOT a result -- instrument rule 2; `well_formed`
is false unless the run printed an Assessed line or a recognised refusal).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(os.path.dirname(HERE))
LOG_DIR = os.path.join(AUDIT_DIR, "logs", "experiments")

EST_RE = re.compile(r"^(Literal|Bitstring) (.+?) Estimate: (.+?) = (.+)$")
EST_NOTE_RE = re.compile(r"^(Literal|Bitstring) (.+?) Estimate: (.+)$")
LOADED_RE = re.compile(r"^Loaded (\d+) samples (?:made up )?of (\d+) distinct (\d+)-bit-wide symbols")
REFUSALS = (
    "SP 800-90B Section 3.1.1 requires at least",
    "Symbol alphabet consists of 1 symbol",
    "does not contain 1000000 samples",
    "is at or past the end of the",
    "does not fit within described bit width",
    "Error reading file",
    "Invalid bits per symbol",
    "Restart Sanity Check Failed",
    "IID test suite failed",
)


def parse_number(text: str):
    t = text.strip()
    low = t.lower()
    if low in ("nan", "-nan", "+nan"):
        return float("nan")
    if low in ("inf", "+inf", "infinity"):
        return float("inf")
    if low in ("-inf", "-infinity"):
        return float("-inf")
    try:
        return float(t)
    except ValueError:
        return None


def is_degenerate(text: str, value) -> str | None:
    t = text.strip()
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    if isinstance(value, float) and math.isinf(value):
        return "inf" if value > 0 else "-inf"
    if t.startswith("-0") and value == 0.0:
        return "-0"
    return None


def parse_text(text: str) -> dict:
    out = {"loaded": None, "narrower_warning": False, "refusal": None, "short_escape": False,
           "estimates": {"Literal": {}, "Bitstring": {}}, "notes": [], "h_original": None,
           "h_bitstring": None, "h_bitstring_per_symbol": None, "assessed": None, "h_prime": None,
           "restart_min": None, "restart_passed": None, "degenerate": [], "lines": 0}
    for raw in text.splitlines():
        line = raw.strip()
        out["lines"] += 1
        m = LOADED_RE.match(line)
        if m:
            out["loaded"] = {"n": int(m.group(1)), "k": int(m.group(2)), "width": int(m.group(3))}
            continue
        if line.startswith("Warning: Symbols appear to be narrower than described."):
            out["narrower_warning"] = True
            continue
        if "EA_ALLOW_SHORT_DATASET is set" in line:
            out["short_escape"] = True
            continue
        if line.startswith("*** Warning"):          # the escape's own warning line, not a refusal
            continue
        for r in REFUSALS:
            if r in line and out["refusal"] is None:
                out["refusal"] = line
        m = EST_RE.match(line)
        if m:
            block, est, label, val = m.groups()
            v = parse_number(val)
            d = out["estimates"][block].setdefault(est, {})
            d[label] = {"text": val.strip(), "value": v}
            deg = is_degenerate(val, v)
            if deg:
                out["degenerate"].append({"line": line, "kind": deg})
            continue
        m = EST_NOTE_RE.match(line)
        if m:
            out["notes"].append(line)
            continue
        for key, prefix in (("h_original", "H_original = "), ("h_bitstring", "H_bitstring = "),
                            ("h_bitstring_per_symbol", "H_bitstring Per Symbol = "),
                            ("assessed", "Assessed min entropy: "), ("h_prime", "h': "),
                            ("restart_min", "min(H_r, H_c, H_I): ")):
            if line.startswith(prefix):
                val = line[len(prefix):]
                v = parse_number(val)
                out[key] = {"text": val.strip(), "value": v}
                deg = is_degenerate(val, v)
                if deg:
                    out["degenerate"].append({"line": line, "kind": deg})
        if line.startswith("Validation Test Passed"):
            out["restart_passed"] = True
    mins = {}
    for block in ("Literal", "Bitstring"):
        vals = [(est, d["min entropy"]["value"]) for est, d in out["estimates"][block].items()
                if "min entropy" in d and d["min entropy"]["value"] is not None]
        finite = [(e, v) for e, v in vals if not (isinstance(v, float) and math.isnan(v))]
        mins[block] = {"count": len(vals), "estimators": sorted(e for e, _ in vals),
                       "min": (min(v for _, v in finite) if finite else None),
                       "binding": (min(finite, key=lambda t: t[1])[0] if finite else None)}
    out["min_of_printed"] = mins
    return out


def parse_json(path: str) -> dict:
    if not os.path.exists(path):
        return {"present": False}
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    top = {k: j.get(k) for k in ("errorLevel", "errorClass", "errorMessage", "nonCompliantShortDataset",
                                 "bitsPerSymbol", "bitsPerSymbolInferred", "subsetRequested", "subsetIndex",
                                 "subsetRequestedSamples", "subsetActualSamples", "sha256", "sha256Scope",
                                 "assessmentComplete", "IID", "commandline")}
    cases = []
    for tc in j.get("testCases", []) or []:
        cases.append({k: tc.get(k) for k in ("testCaseDesc", "literalEstimateNotRun", "bitstringEstimateNotRun",
                                             "hOriginal", "hBitstring", "hAssessed", "dataWordSize",
                                             "retMinEntropy", "h_r", "h_c", "h_i", "lrsRes", "tTupleRes",
                                             "binLrsRes", "binTTupleRes", "mcvEstimatePU") if k in tc})
    overall = next((c for c in cases if c.get("testCaseDesc") == "Overall"), None)
    return {"present": True, "top": top, "cases": cases, "overall": overall,
            "not_run_flags": [{"case": c["testCaseDesc"], "literal": c.get("literalEstimateNotRun"),
                               "bitstring": c.get("bitstringEstimateNotRun")}
                              for c in cases if c.get("literalEstimateNotRun") or c.get("bitstringEstimateNotRun")],
            "restart_cases_with_h_r": [c["testCaseDesc"] for c in cases if "h_r" in c],
            "restart_cases_with_h_c": [c["testCaseDesc"] for c in cases if "h_c" in c]}


def check(name: str, json_path: str | None, tool: str) -> dict:
    base = os.path.join(LOG_DIR, name)
    rec = {"name": name, "tool": tool, "files": {}}
    for ext in ("stdout", "stderr", "rc", "meta"):
        p = f"{base}.{ext}"
        rec["files"][ext] = p if os.path.exists(p) else None
    rc = None
    if rec["files"]["rc"]:
        with open(rec["files"]["rc"]) as f:
            try:
                rc = int(f.read().strip())
            except ValueError:
                rc = None
    rec["rc"] = rc
    text = ""
    if rec["files"]["stdout"]:
        with open(rec["files"]["stdout"], "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    err = ""
    if rec["files"]["stderr"]:
        with open(rec["files"]["stderr"], "r", encoding="utf-8", errors="replace") as f:
            err = f.read()
    rec["stderr_tail"] = err.splitlines()[-5:]
    meta = {}
    if rec["files"]["meta"]:
        with open(rec["files"]["meta"]) as f:
            for line in f:
                if line.startswith("sha256 "):
                    parts = line.split()
                    meta.setdefault("sha256", {})[parts[2]] = parts[1]
                elif ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    rec["meta"] = meta
    rec["text"] = parse_text(text)
    rec["json"] = parse_json(json_path) if json_path else {"present": False}
    t = rec["text"]
    rec["well_formed"] = bool(t["assessed"] or t["refusal"] or t["restart_min"] or t["h_prime"]
                              or (rec["json"].get("present") and rec["json"]["top"].get("errorLevel") not in (None, 0)))
    rec["accepted"] = bool(t["loaded"] and not t["refusal"] and rc == 0)
    rec["compliant"] = bool(rec["accepted"] and not t["short_escape"]
                            and not (rec["json"].get("present") and rec["json"]["top"].get("nonCompliantShortDataset")))
    # consistency of the folds with the printed per-estimator minima
    cons = {}
    if t["h_original"] and t["min_of_printed"]["Literal"]["min"] is not None:
        cons["h_original_equals_min_literal"] = abs(t["h_original"]["value"] - t["min_of_printed"]["Literal"]["min"]) < 1e-12 \
            or (t["h_original"]["value"] <= t["min_of_printed"]["Literal"]["min"] + 1e-12)
    if t["h_bitstring"] and t["min_of_printed"]["Bitstring"]["min"] is not None:
        cons["h_bitstring_equals_min_bitstring"] = abs(t["h_bitstring"]["value"] - t["min_of_printed"]["Bitstring"]["min"]) < 1e-12 \
            or (t["h_bitstring"]["value"] <= t["min_of_printed"]["Bitstring"]["min"] + 1e-12)
    if t["assessed"] and t["loaded"]:
        parts = []
        if t["h_original"]:
            parts.append(t["h_original"]["value"])
        if t["h_bitstring_per_symbol"]:
            parts.append(t["h_bitstring_per_symbol"]["value"])
        if parts:
            cons["assessed_equals_min_terms"] = abs(t["assessed"]["value"] - min(parts)) < 1e-9
    rec["consistency"] = cons
    with open(f"{base}.check.json", "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, default=str)
    return rec


def one_line(rec: dict) -> str:
    t = rec["text"]
    bits = [f"{rec['name']}: rc={rec['rc']}", "well_formed" if rec["well_formed"] else "NOT-WELL-FORMED",
            "accepted" if rec["accepted"] else "refused/other", "COMPLIANT" if rec["compliant"] else "non-compliant"]
    if t["loaded"]:
        bits.append(f"loaded n={t['loaded']['n']} k={t['loaded']['k']} width={t['loaded']['width']}")
    if t["assessed"]:
        bits.append(f"Assessed={t['assessed']['text']}")
    if t["h_original"]:
        bits.append(f"H_original={t['h_original']['text']}")
    if t["h_bitstring_per_symbol"]:
        bits.append(f"nxH_bitstring={t['h_bitstring_per_symbol']['text']}")
    if t["h_prime"]:
        bits.append(f"h'={t['h_prime']['text']}")
    if t["restart_min"]:
        bits.append(f"min(H_r,H_c,H_I)={t['restart_min']['text']}")
    if t["refusal"]:
        bits.append(f"refusal='{t['refusal'][:90]}'")
    if t["narrower_warning"]:
        bits.append("narrower-warning")
    if t["degenerate"]:
        bits.append("DEGENERATE:" + ",".join(sorted({d['kind'] for d in t['degenerate']})) + f"({len(t['degenerate'])})")
    j = rec["json"]
    if j.get("present"):
        top = j["top"]
        bits.append(f"json errorLevel={top.get('errorLevel')} bps={top.get('bitsPerSymbol')} inferred={top.get('bitsPerSymbolInferred')}")
        if j["not_run_flags"]:
            bits.append("notRun=" + ";".join(f"{x['case']}:{'L' if x['literal'] else ''}{'B' if x['bitstring'] else ''}" for x in j["not_run_flags"]))
    if rec["consistency"]:
        bad = [k for k, v in rec["consistency"].items() if v is False]
        bits.append("fold-consistency " + ("OK" if not bad else "FAIL:" + ",".join(bad)))
    return "  ".join(bits)


def compare(a: str, b: str, truth: float | None) -> int:
    ra = json.load(open(os.path.join(LOG_DIR, a + ".check.json")))
    rb = json.load(open(os.path.join(LOG_DIR, b + ".check.json")))
    va = ra["text"]["assessed"]["value"] if ra["text"]["assessed"] else None
    vb = rb["text"]["assessed"]["value"] if rb["text"]["assessed"] else None
    print(f"A {a}: Assessed = {va}   (compliant={ra['compliant']})")
    print(f"B {b}: Assessed = {vb}   (compliant={rb['compliant']})")
    if va is None or vb is None:
        print("one side has no Assessed line: NOT a comparison (instrument rule 2)")
        return 2
    print(f"B / A = {vb / va if va else float('inf'):.6f}    A - B = {va - vb:.9g}")
    if truth is not None:
        print(f"truth = {truth}:  A - truth = {va - truth:+.6g} ({'OVERSTATES' if va > truth else 'at or below truth'});"
              f"  B - truth = {vb - truth:+.6g} ({'OVERSTATES' if vb > truth else 'at or below truth'})")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--compare":
        truth = None
        if "--truth" in argv:
            truth = float(argv[argv.index("--truth") + 1])
        return compare(argv[1], argv[2], truth)
    name = argv[0]
    json_path = None
    tool = "non_iid"
    if "--json" in argv:
        json_path = argv[argv.index("--json") + 1]
    if "--tool" in argv:
        tool = argv[argv.index("--tool") + 1]
    rec = check(name, json_path, tool)
    print(one_line(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
