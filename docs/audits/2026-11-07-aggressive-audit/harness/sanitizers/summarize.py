#!/usr/bin/env python3
"""summarize.py -- write RESULTS.md for the sanitizer phase from the logs run.sh wrote.

Reads every logs/sanitizers/<variant>/*.log, re-derives the sanitizer verdict FROM THE TOOL
OUTPUT REGION of each log (it does not trust the header run.sh wrote; a disagreement is
flagged), tabulates (input, tool, exit, report yes/no, first report line, outcome, wall), and
triages ThreadSanitizer reports against the OpenMP construct line ranges DERIVED FROM THE
SOURCE at generation time (cpp/iid/permutation_tests.h, cpp/restart_main.cpp).

    summarize.py --log-root DIR --san-dir DIR --out RESULTS.md
    summarize.py --selftest          # fixtures: proves the classifiers can fail (exit 1 if not)

TSan report classes (README.md explains the platform limitation that makes this necessary):
  SAME_CRITICAL     both accesses inside the same `#pragma omp critical(NAME)` block.  On this
                    host libomp's lock is invisible to TSan, so this is the expected
                    false-positive class; TSan CANNOT distinguish it from a real race here.
  CROSSES_CRITICAL  one access inside a critical block, the other outside any construct:
                    unsynchronized by construction -> candidate.
  DIFFERENT_CRITICALS  each access inside a differently named critical: those do not exclude
                    each other -> candidate.
  ATOMIC_VS_PLAIN   one access at a `#pragma omp atomic` statement, the other a plain access
                    (inside a critical or not) -> candidate (the `completed` counter,
                    logs/analysis/iid-permutation.md section 2.11).
  PARALLEL_PLAIN    both accesses in the parallel region but in no critical/atomic -> candidate.
  LIBOMP_INTERNAL   neither access has a frame in the tool's source (runtime-only stacks).
  OUTSIDE_OMP       at least one access is in tool source outside any `#pragma omp` region.
  UNPARSED          the report block did not parse.
What the triage cannot see: a frame TSan failed to symbolize to file:line; a critical block
whose braces this brace-matcher mis-parsed (the derived ranges are printed so they can be
checked by eye); races in code paths no input reached.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(AUDIT)))
CPP = os.path.join(REPO, "cpp")
OMP_SOURCES = ["iid/permutation_tests.h", "restart_main.cpp"]

HDR_RE = re.compile(r"^## ([a-z_]+): ?(.*)$")
REPORT_RE = re.compile(r"(^==\d+==ERROR: |: runtime error: |^WARNING: ThreadSanitizer: |^==\d+==WARNING: [A-Za-z]*Sanitizer)")
SUMMARY_RE = re.compile(r"^SUMMARY: (Address|UndefinedBehavior|Thread|Leak)Sanitizer: (.*)$")
ACCESS_RE = re.compile(r"^\s*((?:Previous )?(?:atomic )?(?:write|read)) of size \d+ at 0x[0-9a-f]+ by (.*?):\s*$", re.I)
FRAME_RE = re.compile(r"^\s*#(\d+) (\S+) (.*)$")
FILELINE_RE = re.compile(r"([A-Za-z0-9_./-]+\.(?:h|cpp|hpp|c)):(\d+)(?::\d+)?")


# ----------------------------------------------------------------------------------------
# log parsing
# ----------------------------------------------------------------------------------------
def parse_log(path):
    hdr, body = {}, []
    in_body = False
    with open(path, "r", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line == "## --- tool output ---":
                in_body = True
                continue
            if line == "## --- end of tool output ---":
                in_body = False
                continue
            if in_body:
                body.append(line)
                continue
            m = HDR_RE.match(line)
            if m:
                hdr[m.group(1)] = m.group(2)
    first = next((l for l in body if REPORT_RE.search(l)), None)
    summaries = [l for l in body if SUMMARY_RE.match(l) or l.startswith("WARNING: ThreadSanitizer: ")]
    classes = sorted({SUMMARY_RE.match(l).group(1) for l in body if SUMMARY_RE.match(l)})
    ub_kinds = sorted({SUMMARY_RE.match(l).group(2).split(" ")[0] for l in body
                       if SUMMARY_RE.match(l) and SUMMARY_RE.match(l).group(1) == "UndefinedBehavior"})
    return {
        "path": path,
        "hdr": hdr,
        "body": body,
        "complete": "exit" in hdr,
        "report_first": first,
        "report_count": len(summaries),
        "report_classes": classes,
        "ubsan_kinds": ub_kinds,
    }


# ----------------------------------------------------------------------------------------
# OpenMP construct ranges derived from the source
# ----------------------------------------------------------------------------------------
def _block_end(lines, start_idx):
    """Index (0-based) of the line closing the brace block that opens at/after start_idx."""
    depth = 0
    opened = False
    for i in range(start_idx, len(lines)):
        s = lines[i]
        # strip string literals crudely so braces inside them do not count
        s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
        s = re.sub(r"//.*$", "", s)
        for ch in s:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return i
        if not opened and i > start_idx + 3:
            break
    return None


def derive_constructs(src_path):
    """[{file, kind, name, start, end}] with 1-based inclusive line ranges."""
    out = []
    try:
        with open(src_path, "r", errors="replace") as f:
            lines = f.read().split("\n")
    except OSError:
        return out
    rel = os.path.relpath(src_path, CPP)
    for i, line in enumerate(lines):
        m = re.match(r"^\s*#pragma omp (parallel|for|critical|atomic|barrier|single|master)(?:\s*\(\s*(\w+)\s*\))?", line)
        if not m:
            continue
        kind, name = m.group(1), m.group(2) or ""
        if kind == "atomic":
            # the next non-blank line is the atomic statement
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            out.append({"file": rel, "kind": "atomic", "name": "", "start": i + 1, "end": j + 1})
        elif kind in ("parallel", "critical", "single", "master"):
            end = _block_end(lines, i + 1)
            if end is None:
                out.append({"file": rel, "kind": kind, "name": name, "start": i + 1, "end": i + 1, "note": "block not found"})
            else:
                out.append({"file": rel, "kind": kind, "name": name, "start": i + 1, "end": end + 1})
        elif kind == "for":
            end = _block_end(lines, i + 1)
            out.append({"file": rel, "kind": "for", "name": "", "start": i + 1, "end": (end + 1) if end else i + 1})
        else:
            out.append({"file": rel, "kind": kind, "name": name, "start": i + 1, "end": i + 1})
    return out


def all_constructs():
    cs = []
    for rel in OMP_SOURCES:
        cs.extend(derive_constructs(os.path.join(CPP, rel)))
    return cs


def locate(file_, line, constructs):
    """Innermost construct containing (file, line): the one with the smallest range."""
    best = None
    for c in constructs:
        if not file_.endswith(c["file"]) and not c["file"].endswith(os.path.basename(file_)):
            continue
        if c["start"] <= line <= c["end"]:
            if best is None or (c["end"] - c["start"]) < (best["end"] - best["start"]):
                best = c
    return best


def containing(file_, line, constructs, kind):
    for c in constructs:
        if c["kind"] == kind and (file_.endswith(c["file"]) or c["file"].endswith(os.path.basename(file_))) and c["start"] <= line <= c["end"]:
            return c
    return None


# ----------------------------------------------------------------------------------------
# TSan report triage
# ----------------------------------------------------------------------------------------
def tsan_blocks(body):
    blocks, cur = [], None
    for l in body:
        if l.startswith("WARNING: ThreadSanitizer: "):
            if cur:
                blocks.append(cur)
            cur = [l]
        elif cur is not None:
            cur.append(l)
            if l.startswith("SUMMARY: ThreadSanitizer"):
                blocks.append(cur)
                cur = None
    if cur:
        blocks.append(cur)
    return blocks


def tool_frame(frames):
    """First frame whose file:line is in the tool's own source (not the runtime, not libomp)."""
    for fn, rest in frames:
        m = FILELINE_RE.search(rest)
        if not m:
            continue
        f = m.group(1)
        if "libomp" in rest or "/tsan" in f or "sanitizer" in f or "compiler-rt" in f:
            continue
        if f.endswith((".h", ".cpp", ".hpp", ".c")):
            return fn, f, int(m.group(2))
    return None


def triage_block(block, constructs):
    kind = block[0].replace("WARNING: ThreadSanitizer: ", "").split(" (pid")[0]
    accesses = []
    cur = None
    for l in block[1:]:
        m = ACCESS_RE.match(l)
        if m:
            cur = {"kind": m.group(1).lower(), "thread": m.group(2), "frames": []}
            accesses.append(cur)
            continue
        if cur is not None:
            fm = FRAME_RE.match(l)
            if fm:
                cur["frames"].append((fm.group(2), fm.group(3)))
            elif l.strip() == "" or l.startswith("  Location") or l.startswith("  Thread") or l.startswith("  Mutex"):
                cur = None
    if kind != "data race" or len(accesses) < 2:
        return {"kind": kind, "cls": "UNPARSED" if kind == "data race" else kind.upper().replace(" ", "_"), "a": None, "b": None, "reason": "not a two-access data race block"}
    a, b = accesses[0], accesses[1]
    fa, fb = tool_frame(a["frames"]), tool_frame(b["frames"])
    da = describe(fa, a, constructs)
    db = describe(fb, b, constructs)
    if fa is None and fb is None:
        cls, why = "LIBOMP_INTERNAL", "no tool-source frame in either stack"
    elif fa is None or fb is None:
        cls, why = "OUTSIDE_OMP", "one stack has no tool-source frame"
    else:
        ca, cb = locate(fa[1], fa[2], constructs), locate(fb[1], fb[2], constructs)
        ka = ca["kind"] if ca else None
        kb = cb["kind"] if cb else None
        atomic_a = ka == "atomic" or "atomic" in a["kind"]
        atomic_b = kb == "atomic" or "atomic" in b["kind"]
        crit_a = containing(fa[1], fa[2], constructs, "critical")
        crit_b = containing(fb[1], fb[2], constructs, "critical")
        par_a = containing(fa[1], fa[2], constructs, "parallel")
        par_b = containing(fb[1], fb[2], constructs, "parallel")
        if atomic_a and atomic_b:
            cls, why = "ATOMIC_ATOMIC", "both accesses atomic (TSan should not report this)"
        elif atomic_a or atomic_b:
            cls, why = "ATOMIC_VS_PLAIN", "one access is an `omp atomic`, the other a plain access"
        elif crit_a and crit_b and crit_a["name"] == crit_b["name"]:
            cls, why = "SAME_CRITICAL", "both inside critical(%s): libomp lock invisible to TSan on this host" % crit_a["name"]
        elif crit_a and crit_b:
            cls, why = "DIFFERENT_CRITICALS", "critical(%s) vs critical(%s) do not exclude each other" % (crit_a["name"], crit_b["name"])
        elif crit_a or crit_b:
            cls, why = "CROSSES_CRITICAL", "one access inside critical(%s), the other outside every construct" % ((crit_a or crit_b)["name"])
        elif par_a and par_b:
            cls, why = "PARALLEL_PLAIN", "both in the parallel region, in no critical/atomic"
        else:
            cls, why = "OUTSIDE_OMP", "at least one access is outside every `#pragma omp` region"
    return {"kind": kind, "cls": cls, "a": da, "b": db, "reason": why}


def describe(fr, acc, constructs):
    if fr is None:
        top = acc["frames"][0][0] if acc["frames"] else "?"
        return "%s by %s: %s (no tool frame)" % (acc["kind"], acc["thread"], top)
    fn, f, ln = fr
    c = locate(f, ln, constructs)
    where = ("%s(%s) %d-%d" % (c["kind"], c["name"], c["start"], c["end"])) if c else "no construct"
    return "%s by %s: %s:%d in %s [%s]" % (acc["kind"], acc["thread"], os.path.basename(f), ln, fn, where)


# ----------------------------------------------------------------------------------------
# RESULTS.md
# ----------------------------------------------------------------------------------------
def read_build_record(san_dir):
    p = os.path.join(san_dir, "BUILD-RECORD.txt")
    rows, extra = [], []
    if not os.path.exists(p):
        return None, rows, extra
    with open(p) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("binary="):
                kv = dict(re.findall(r"(\w+)=(\"[^\"]*\"|\S+)", line))
                rows.append(kv)
            elif line.startswith(("lsan_supported=", "compiler=", "libomp=", "host=", "production_binary=", "runtime_dylib=")):
                extra.append(line)
    return p, rows, extra


def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def write_results(log_root, san_dir, out_path, constructs=None):
    constructs = constructs if constructs is not None else all_constructs()
    logs = []
    for variant in sorted(os.listdir(log_root)) if os.path.isdir(log_root) else []:
        vdir = os.path.join(log_root, variant)
        if not os.path.isdir(vdir) or variant.startswith("."):
            continue
        for name in sorted(os.listdir(vdir)):
            if name.endswith(".log"):
                d = parse_log(os.path.join(vdir, name))
                d["variant"] = variant
                d["name"] = name
                logs.append(d)

    rec_path, bin_rows, rec_extra = read_build_record(san_dir)
    env_path = os.path.join(log_root, "ENV.txt")
    env_txt = open(env_path).read() if os.path.exists(env_path) else "(ENV.txt not found: run.sh has not run)"

    L = []
    w = L.append
    w("# Sanitizer phase -- RESULTS")
    w("")
    w("Generated %s by harness/sanitizers/summarize.py from `%s`." % (time.strftime("%Y-%m-%d %H:%M:%S %z"), os.path.relpath(log_root, AUDIT)))
    w("Every verdict below was re-derived from the tool-output region of the log file; the `hdr` column says whether run.sh's own trailer agreed.")
    w("")
    w("## Binaries measured (from BUILD-RECORD.txt)")
    w("")
    if rec_path is None:
        w("BUILD-RECORD.txt not found under `%s` -- no binary is named; nothing here is a measurement until build.sh has run." % san_dir)
    else:
        w("| variant | tool | sha256 | build exit | smoke exit |")
        w("|---|---|---|---|---|")
        for r in bin_rows:
            w("| %s | ea_%s | `%s` | %s | %s |" % (r.get("variant"), r.get("tool"), r.get("sha256"), r.get("build_exit"), r.get("smoke_exit")))
        w("")
        for e in rec_extra:
            w("- `%s`" % md_escape(e))
    w("")
    w("## Environment (ENV.txt)")
    w("")
    w("```")
    w(env_txt.rstrip("\n"))
    w("```")
    w("")

    # counts
    w("## Counts")
    w("")
    w("| variant | logs | complete | COMPLETED* | SANITIZER (re-derived) | REFUSED | TIMEOUT | SIGNAL | UNCLASSIFIED | ALIAS | SKIPPED-INPUT | incomplete (killed) | hdr disagreements |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    variants = sorted({d["variant"] for d in logs})
    for v in variants:
        ds = [d for d in logs if d["variant"] == v]

        def cnt(pred):
            return sum(1 for d in ds if pred(d))
        oc = lambda d: d["hdr"].get("tool_outcome", "")
        w("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            v, len(ds), cnt(lambda d: d["complete"]),
            cnt(lambda d: oc(d).startswith("COMPLETED")),
            cnt(lambda d: d["report_first"] is not None),
            cnt(lambda d: oc(d) == "REFUSED"), cnt(lambda d: oc(d) == "TIMEOUT"),
            cnt(lambda d: oc(d).startswith("SIGNAL")), cnt(lambda d: oc(d) == "UNCLASSIFIED"),
            cnt(lambda d: oc(d) == "ALIAS"), cnt(lambda d: oc(d).startswith("SKIPPED-INPUT")),
            cnt(lambda d: not d["complete"]),
            cnt(lambda d: d["complete"] and d["hdr"].get("sanitizer_report") in ("yes", "no") and ((d["hdr"].get("sanitizer_report") == "yes") != (d["report_first"] is not None)))))
    w("")
    w("## What this table cannot see")
    w("")
    w("- a sanitizer report in a format the detector regexes do not match (`==<pid>==ERROR:`, `: runtime error:`, `WARNING: ThreadSanitizer:`, `==<pid>==WARNING: <X>Sanitizer`); a crash that printed nothing is SIGNAL-n, not explained;")
    w("- a wrong NUMBER printed by a run that completed cleanly (that is the differential phase's job, not this one's);")
    w("- code paths no input reached: the sanitizers instrument the whole binary but report only on executed code; the stage list and the alias/skip columns bound what ran;")
    w("- leaks, if `detect_leaks_used=0` in ENV.txt (LeakSanitizer unsupported on this host per BUILD-RECORD);")
    w("- under UBSan `halt_on_error=1`, everything after the FIRST recoverable report on an input -- the `.ubsan-continue.log` re-run (listed below) is the only view of the rest;")
    w("- for TSan: the happens-before that libomp's uninstrumented barriers and locks establish (see the triage section); and `ea_non_iid`/`ea_restart -n` have no live parallel region, so a clean TSan result there is a control, not coverage;")
    w("- EA_ALLOW_SHORT_DATASET=1 rows are non-compliant runs by construction (brief, ground rule 5) -- the `short` column.")
    w("")

    for v in variants:
        ds = [d for d in logs if d["variant"] == v and not d["name"].endswith(".ubsan-continue.log")]
        w("## %s runs" % v)
        w("")
        w("| stage | tool | input (bytes) | operands | flags | short | heavy | exit | wall s | sanitizer report | #rep | first report line | outcome | hdr | battery | log |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for d in ds:
            h = d["hdr"]
            rep = "yes" if d["report_first"] else ("no" if d["complete"] else "-")
            hdr_ok = "-"
            if d["complete"] and h.get("sanitizer_report") in ("yes", "no"):
                hdr_ok = "agrees" if ((h.get("sanitizer_report") == "yes") == (d["report_first"] is not None)) else "**DISAGREES**"
            outcome = h.get("tool_outcome", "INCOMPLETE") if d["complete"] else "**INCOMPLETE (no `## exit:` trailer: killed run)**"
            battery = h.get("permutation_battery", "")
            if h.get("permutation_progress_lines"):
                battery += " (%s progress lines)" % h.get("permutation_progress_lines")
            w("| %s | %s | %s (%s) | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | `%s` |" % (
                h.get("stage", ""), h.get("tool", ""), md_escape(os.path.basename(h.get("input", ""))), h.get("input_bytes", ""),
                md_escape(h.get("operands", "")), md_escape(h.get("flags", "")), h.get("short_dataset_escape", ""), h.get("heavy", ""),
                h.get("exit", ""), h.get("wall_seconds", ""), rep, d["report_count"],
                md_escape((d["report_first"] or "-")[:140]), outcome, hdr_ok, battery, os.path.join(v, d["name"])))
        w("")

    cont = [d for d in logs if d["name"].endswith(".ubsan-continue.log")]
    w("## UBSan continue passes (halt_on_error=0; every recoverable report on that input)")
    w("")
    if not cont:
        w("none")
    else:
        w("| re-run of | exit | wall s | #reports | UBSan kinds | outcome | log |")
        w("|---|---|---|---|---|---|---|")
        for d in cont:
            h = d["hdr"]
            w("| %s | %s | %s | %d | %s | %s | `%s` |" % (h.get("rerun_of", ""), h.get("exit", ""), h.get("wall_seconds", ""), d["report_count"], ", ".join(d["ubsan_kinds"]) or "-", h.get("tool_outcome", "INCOMPLETE"), os.path.join(d["variant"], d["name"])))
    w("")

    w("## ThreadSanitizer report triage")
    w("")
    w("Construct line ranges derived from the source when this file was generated (check them by eye against `cpp/`):")
    w("")
    w("| file | kind | name | lines |")
    w("|---|---|---|---|")
    for c in constructs:
        w("| %s | %s | %s | %d-%d%s |" % (c["file"], c["kind"], c["name"] or "-", c["start"], c["end"], (" (%s)" % c["note"]) if c.get("note") else ""))
    w("")
    tsan_logs = [d for d in logs if d["variant"] == "tsan" and d["report_count"]]
    if not tsan_logs:
        w("No ThreadSanitizer report in any tsan log (or the tsan stage has not run).")
    else:
        w("| log | # | kind | access A | access B | class | reason |")
        w("|---|---|---|---|---|---|---|")
        for d in tsan_logs:
            for i, blk in enumerate(tsan_blocks(d["body"]), 1):
                t = triage_block(blk, constructs)
                w("| `%s` | %d | %s | %s | %s | **%s** | %s |" % (os.path.join(d["variant"], d["name"]), i, t["kind"], md_escape(t["a"] or "-"), md_escape(t["b"] or "-"), t["cls"], md_escape(t["reason"])))
        w("")
        w("Reading: SAME_CRITICAL is the platform false-positive class (indistinguishable from a real race by TSan with an uninstrumented libomp); every other class on tool code is a candidate that needs the code read and an owner decision.")
    w("")

    aliases = [d for d in logs if d["hdr"].get("tool_outcome") == "ALIAS"]
    w("## Aliases (byte-identical input at the same width and flags; run once)")
    w("")
    if not aliases:
        w("none")
    else:
        for d in aliases:
            w("- `%s` -> `%s`" % (d["name"], d["hdr"].get("alias_of", "")))
    w("")

    with open(out_path, "w") as f:
        f.write("\n".join(L) + "\n")
    return logs


# ----------------------------------------------------------------------------------------
# self-test: fixtures that prove the detector and the triage can fail
# ----------------------------------------------------------------------------------------
def _fixture(path, hdr, body, trailer):
    with open(path, "w") as f:
        for k, v in hdr:
            f.write("## %s: %s\n" % (k, v))
        f.write("## --- tool output ---\n")
        for l in body:
            f.write(l + "\n")
        f.write("## --- end of tool output ---\n")
        for k, v in trailer:
            f.write("## %s: %s\n" % (k, v))


def _race_block(a_line, a_kind, b_line, b_kind, file_="permutation_tests.h", fn="permutation_tests(data_t*, double, double, int, IidTestCase&, char const*)"):
    def stack(line):
        return ["    #0 .omp_outlined._debug__ %s/iid/%s:%d:17 (ea_iid:arm64+0x1000211f4)" % (CPP, file_, line),
                "    #1 .omp_outlined. %s/iid/%s:625:2 (ea_iid:arm64+0x100021000)" % (CPP, file_),
                "    #2 __kmp_invoke_microtask <null> (libomp.dylib:arm64+0x7c1c)"]
    return (["WARNING: ThreadSanitizer: data race (pid=4242)",
             "  %s of size 4 at 0x000104a3c000 by thread T3:" % a_kind] + stack(a_line) +
            ["", "  Previous %s of size 4 at 0x000104a3c000 by thread T1:" % b_kind.lower()] + stack(b_line) +
            ["", "  Location is global 'completed' of size 4 at 0x000104a3c000 (ea_iid+0x000100050000)",
             "", "SUMMARY: ThreadSanitizer: data race %s:%d:17 in %s" % (file_, a_line, fn), ""])


def selftest():
    constructs = all_constructs()
    perm = [c for c in constructs if c["file"] == "iid/permutation_tests.h"]
    crit_r = next((c for c in perm if c["kind"] == "critical" and c["name"] == "resultUpdate"), None)
    crit_v = next((c for c in perm if c["kind"] == "critical" and c["name"] == "verboseOutput"), None)
    atom = next((c for c in perm if c["kind"] == "atomic"), None)
    par = next((c for c in perm if c["kind"] == "parallel"), None)
    fails = []

    def check(name, cond, detail=""):
        print("%-60s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        if not cond:
            fails.append(name)

    check("derived critical(resultUpdate) from source", crit_r is not None and crit_r["end"] > crit_r["start"] + 3, str(crit_r))
    check("derived critical(verboseOutput) from source", crit_v is not None and crit_v["end"] > crit_v["start"], str(crit_v))
    check("derived `omp atomic` from source", atom is not None, str(atom))
    check("derived parallel region from source", par is not None and par["end"] > par["start"] + 50, str(par))
    if fails:
        return 1
    # a plain line inside the parallel region but outside every critical/atomic:
    src = open(os.path.join(CPP, "iid/permutation_tests.h"), errors="replace").read().split("\n")
    plain_line = next((i + 1 for i, l in enumerate(src) if "passed_count < 19" in l), None)
    check("found the unguarded `passed_count < 19` read", plain_line is not None and par["start"] < plain_line < par["end"] and locate("iid/permutation_tests.h", plain_line, constructs)["kind"] in ("for", "parallel"), str(plain_line))
    inside_r = crit_r["start"] + 2
    inside_v = crit_v["start"] + 1
    atomic_line = atom["end"]

    tmp = tempfile.mkdtemp(prefix="san-selftest-")
    os.makedirs(os.path.join(tmp, "asan_ubsan"))
    os.makedirs(os.path.join(tmp, "tsan"))
    hdr = [("stage", "x"), ("variant", "asan_ubsan"), ("tool", "ea_non_iid"), ("input", "/x/fixture.bin"), ("input_bytes", "50000"), ("operands", "8"), ("flags", "-i -a -vv"), ("short_dataset_escape", "yes"), ("heavy", "no")]
    _fixture(os.path.join(tmp, "asan_ubsan", "ea_non_iid-fx-clean.log"), hdr, ["Loaded 50000 samples", "Assessed min entropy: 0.5"],
             [("exit", "0"), ("wall_seconds", "1"), ("sanitizer_report", "no"), ("first_report_line", "-"), ("tool_outcome", "COMPLETED")])
    _fixture(os.path.join(tmp, "asan_ubsan", "ea_non_iid-fx-asan.log"), hdr, ["Loaded 50000 samples", "=================================================================",
             "==4242==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6020000000f1 at pc 0x000100001234 bp 0x00016fdff000 sp 0x00016fdfeff8",
             "READ of size 1 at 0x6020000000f1 thread T0", "    #0 0x100001233 in most_common(...) most_common.h:12:9", "SUMMARY: AddressSanitizer: heap-buffer-overflow most_common.h:12:9 in most_common"],
             [("exit", "134"), ("wall_seconds", "1"), ("sanitizer_report", "yes"), ("first_report_line", "==4242==ERROR: AddressSanitizer: heap-buffer-overflow"), ("tool_outcome", "SANITIZER")])
    # deliberately WRONG header: run.sh said "no", the body says otherwise -> must be flagged
    _fixture(os.path.join(tmp, "asan_ubsan", "ea_iid-fx-ubsan-badhdr.log"), hdr, ["shared/utils.h:520:28: runtime error: implicit conversion from type 'long' of value 4000000 (64-bit, signed) to type 'int' changed the value to -294967296",
             "    #0 0x1 in read_file utils.h:520", "SUMMARY: UndefinedBehaviorSanitizer: implicit-signed-integer-truncation utils.h:520:28 in", "Assessed min entropy: 0.9"],
             [("exit", "0"), ("wall_seconds", "1"), ("sanitizer_report", "no"), ("first_report_line", "-"), ("tool_outcome", "COMPLETED")])
    _fixture(os.path.join(tmp, "asan_ubsan", "ea_restart-fx-incomplete.log"), hdr, ["H_I: 0.9"], [])
    body = (_race_block(inside_r, "Write", atomic_line, "Atomic write") +
            _race_block(inside_r, "Write", inside_r + 1, "Write") +
            _race_block(inside_r, "Write", plain_line, "Read") +
            _race_block(inside_r, "Write", inside_v, "Write") +
            ["ThreadSanitizer: reported 4 warnings"])
    _fixture(os.path.join(tmp, "tsan", "ea_iid-fx-races.log"), [("stage", "tsan"), ("variant", "tsan"), ("tool", "ea_iid"), ("input", "/x/f.bin"), ("input_bytes", "50000"), ("operands", "1"), ("flags", "-i -a -v"), ("short_dataset_escape", "yes"), ("heavy", "yes")],
             body, [("exit", "66"), ("wall_seconds", "9"), ("sanitizer_report", "yes"), ("first_report_line", "WARNING: ThreadSanitizer: data race (pid=4242)"), ("tool_outcome", "SANITIZER")])

    out = os.path.join(tmp, "RESULTS.md")
    logs = write_results(tmp, tmp, out, constructs)
    by = {d["name"]: d for d in logs}
    check("clean log: no report detected", by["ea_non_iid-fx-clean.log"]["report_first"] is None)
    check("ASan log: report detected, class AddressSanitizer", by["ea_non_iid-fx-asan.log"]["report_first"] is not None and by["ea_non_iid-fx-asan.log"]["report_classes"] == ["Address"])
    d = by["ea_iid-fx-ubsan-badhdr.log"]
    check("UBSan log with a wrong header: report re-derived yes", d["report_first"] is not None and d["ubsan_kinds"] == ["implicit-signed-integer-truncation"])
    results_txt = open(out).read()
    check("RESULTS.md flags the header disagreement", "**DISAGREES**" in results_txt)
    check("incomplete log named as killed run", "INCOMPLETE" in results_txt and by["ea_restart-fx-incomplete.log"]["complete"] is False)
    blocks = tsan_blocks(by["ea_iid-fx-races.log"]["body"])
    check("TSan fixture: four blocks parsed", len(blocks) == 4, str(len(blocks)))
    cls = [triage_block(b, constructs)["cls"] for b in blocks]
    check("triage #1 critical vs atomic -> ATOMIC_VS_PLAIN", cls[0] == "ATOMIC_VS_PLAIN", cls[0])
    check("triage #2 both in resultUpdate -> SAME_CRITICAL", cls[1] == "SAME_CRITICAL", cls[1])
    check("triage #3 critical vs unguarded read -> CROSSES_CRITICAL", cls[2] == "CROSSES_CRITICAL", cls[2])
    check("triage #4 resultUpdate vs verboseOutput -> DIFFERENT_CRITICALS", cls[3] == "DIFFERENT_CRITICALS", cls[3])
    # negative control for the triage: swap the construct table for an empty one and the
    # same blocks must NOT come out SAME_CRITICAL (the classifier must depend on the ranges)
    cls_empty = [triage_block(b, [])["cls"] for b in blocks]
    check("triage with no construct ranges never says SAME_CRITICAL", "SAME_CRITICAL" not in cls_empty, str(cls_empty))
    print("selftest fixtures in %s; RESULTS fixture at %s" % (tmp, out))
    print("selftest: %s" % ("PASS" if not fails else "FAIL (%d)" % len(fails)))
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-root")
    ap.add_argument("--san-dir", default="")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.log_root or not a.out:
        ap.error("--log-root and --out are required (or --selftest)")
    logs = write_results(a.log_root, a.san_dir, a.out)
    n_rep = sum(1 for d in logs if d["report_first"])
    n_inc = sum(1 for d in logs if not d["complete"])
    print("RESULTS.md: %d logs, %d with sanitizer reports, %d incomplete -> %s" % (len(logs), n_rep, n_inc, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
