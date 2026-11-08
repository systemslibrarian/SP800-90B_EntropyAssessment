#!/usr/bin/env python3
"""compare_runs.py -- normalise and compare the determinism matrix; write RESULTS.md.

Reads the run directories run.sh produced under <out>/{non_iid,iid,restart}/<case>/ :
    <tag>.stdout.txt  <tag>.stderr.txt  <tag>.json  <tag>.rc  <tag>.meta
where <tag> is  t<threads>-r<rep>  (non_iid, restart)  or  <arm>-t<threads>-r<rep>  (iid,
arm a = default /dev/urandom, arm b = EA_TEST_RANDOM_SOURCE set).

NORMALISATION (exactly what the task permits, nothing more):
  JSON   : parsed; the top-level keys dateTimeStamp, commandline and filename are removed;
           re-serialised with sorted keys.  Floats round-trip through Python's float, whose
           repr is the shortest string that reproduces the same double, so two JSON numbers
           compare equal iff they are the same double (jsoncpp prints them at 17 significant
           digits, which already pins the double).  Written beside the run as <tag>.norm.json.
  stdout : byte-identical copy except that lines matching PROGRESS (the IID battery's
           progress meter, printed only at verbosity 2 and interleaved by thread) are removed
           and their count recorded; at -vv none are expected.  Written as <tag>.norm.stdout.
  stderr : compared as-is.   rc : compared as-is.

A run is WELL-FORMED only if its .rc exists, its JSON parses, the JSON is not the C14
placeholder (reportComplete == false) and the final marker for the tool is present:
  non_iid : rc 0, 'Assessed min entropy:' in stdout, errorLevel 0
  iid     : rc in {0,1}, assessmentComplete true, and either 'Assessed min entropy:' (pass)
            or 'IID test suite failed' (statistical fail) in stdout
  restart : rc 0, 'min(H_r, H_c, H_I):' in stdout, errorLevel 0; OR rc 255 with
            errorClass 'statistical' (sanity/validation failure -- well-formed, but the
            estimators may not have run, so such a pair proves little and is labelled)
Comparisons involving a malformed run are reported as NOT A RESULT (instrument rule 2:
an absent line, a usage message, a crash and a completed report are different outcomes
and only the last is evidence).

COMPARISON: every pair of well-formed runs within a case is compared byte-for-byte on the
four normalised channels; every differing field is listed with its label and both
values.  Labels come from the stdout line shapes ('<estimator>: <field> = <value>',
'<label> = <value>', '<label>: <value>', the IID C-table rows) and from the JSON paths
(testCases keyed by testCaseDesc; permutationTestResults keyed by dataLayout and
iteration 0/1/2 = C0/C1/C2).  Positional reads are not used (instrument rule 5).

CLASSIFICATION of a case from its pairs, and what each class would indicate:
  DETERMINISTIC          every pair identical on all four channels.
  THREAD-DEPENDENT       repeats at the same thread count identical; pairs across thread
                         counts differ.  Deterministic in the thread count: a parallel
                         REDUCTION ORDER (floating-point associativity) or a per-thread
                         PARTITION (the IID battery's one-stream-per-thread design).  It
                         shows at 2 threads vs 1 already.
  NONDETERMINISTIC       repeats at the same thread count differ.  With the seed live this
                         is EXPECTED for the IID battery's RNG-dependent fields (listed
                         below) and nothing else; for any other field, or any other tool,
                         it is the signature of a DATA RACE or a NON-THREAD-SAFE CALL
                         (two runs of the same program on the same bytes disagree).  A
                         1-thread repeat pair that still differs rules threads out and
                         points at the seed or at uninitialised memory.
  10-ONLY                1 vs 2 identical but 1 vs 10 or 2 vs 10 differ: scheduling or
                         contention sensitive; whatever it is, it is NOT long double
                         width, FMA contraction or libm -- those are compile-time and
                         host-wide properties and cannot depend on the thread count.
                         (Platform classes are compare_linux.py's business: they present
                         as IDENTICAL on this host at every thread count and different
                         from the other platform by the same amount every time.)
  INCOMPLETE             a run in the case is malformed.
For ea_iid the fields are split into RNG-DEPENDENT (the C0/C1/C2 counters, the permutation
verdict, the suite verdict, errorLevel/IID flags, and anything downstream of them) and
RNG-INDEPENDENT (unpermuted statistics, chi-square, LRS, rawMean, median, H values,
sha256).  A difference in an RNG-INDEPENDENT field is a FINDING CANDIDATE whatever the
thread count.  The prediction, stated before the measurement so the record can show it
wrong: arm (b) will vary exactly like arm (a), because EA_TEST_RANDOM_SOURCE is read only
into TestRunUtils.h:g_randomSourcePath (line 129) and used only for the report temp-file
suffix (line 478); utils.h:797 seed() opens the literal "/dev/urandom".

WHAT THIS CANNOT SEE (rule 18): a nondeterminism that did not manifest in two repeats
(n = 2 per thread count; identity of two runs is weak evidence of determinism and is
reported as 'identical in 2 of 2', never as 'deterministic' in the absolute); a
difference below the printed precision (doubles at 17 significant digits, long doubles
at 22 -- a long double perturbation can vanish in a double printed from it); races in
code paths these inputs do not reach; for the IID battery, seed-driven variation and a
race cannot be told apart with the production binary (needs a fixed-seed out-of-tree
build); 10 threads on this 10-core host is not oversubscription, so a race needing it may
not show; and two identical runs can both be wrong.

Usage: compare_runs.py [--out DIR] [--smoke]   (writes <out>/RESULTS.md and per-pair .diff.txt)
Exit: 0 when every case is DETERMINISTIC or its only differences are the IID RNG-dependent
fields; 1 when any other difference or any INCOMPLETE case exists; 2 when nothing could be
compared.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(os.path.dirname(HERE))
DEFAULT_OUT = os.path.join(AUDIT_DIR, "logs", "determinism")

TOOLS = ("non_iid", "iid", "restart")
DROP_JSON_KEYS = ("dateTimeStamp", "commandline", "filename")
PROGRESS = re.compile(r"% of Permutation test rounds")
TAG = re.compile(r"^(?:(?P<arm>[ab])-)?t(?P<threads>\d+)-r(?P<rep>\d+)$")

# stdout line shapes, all anchored; the value group is the text after the separator
EST_FIELD = re.compile(r"^(?P<label>[^:=]+?): (?P<field>[^=]+?) = (?P<value>.+)$")
LABEL_EQ = re.compile(r"^(?P<label>[^:=]+?) = (?P<value>.+)$")
LABEL_COLON = re.compile(r"^(?P<label>[^:=]+?): (?P<value>[-+0-9.eE]+|Passed|Failed|true|false)$")
CTABLE = re.compile(r"^\s*(?P<name>[A-Za-z()0-9]+?)(?P<star>\*?)\s+(?P<c0>\d+)\s+(?P<c1>\d+)\s+(?P<c2>\d+)\s*$")
CTABLE_NAMES = {"excursion", "numDirectionalRuns", "lenDirectionalRuns", "numIncreasesDecreases",
                "numRunsMedian", "lenRunsMedian", "avgCollision", "maxCollision", "periodicity(1)",
                "periodicity(2)", "periodicity(8)", "periodicity(16)", "periodicity(32)", "covariance(1)",
                "covariance(2)", "covariance(8)", "covariance(16)", "covariance(32)", "compression"}

# IID fields whose variation under a live seed is expected
RNG_DEPENDENT = re.compile(
    r"(^C-table\[|^IID permutation tests$|^IID test suite failed|^\*\* |"
    r"\.permutationTestResults\[|^json:IID$|^json:errorLevel$|^json:errorMessage$|^json:errorClass$|"
    r"\.passedIidPermutationTests$|\.hAssessed$|^Assessed min entropy$|^rc$|^stdout-line:)")
# NOTE on hAssessed / 'Assessed min entropy' for ea_iid: printed only when the battery
# passes, so their PRESENCE follows the verdict; their VALUE (= H_original / H_bitstring
# arithmetic) is RNG-independent and is cross-checked separately below.


def read(path):
    with open(path, "rb") as f:
        return f.read()


def load_meta(path):
    d = {}
    if os.path.exists(path):
        for ln in read(path).decode("utf-8", "replace").splitlines():
            if "=" in ln:
                k, v = ln.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def normalise_json(raw: bytes):
    try:
        j = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001 -- the failure is the datum
        return None, f"JSON does not parse: {e}"
    if isinstance(j, dict):
        for k in DROP_JSON_KEYS:
            j.pop(k, None)
    text = json.dumps(j, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
    return j, text


def normalise_stdout(raw: bytes):
    kept, dropped = [], 0
    for ln in raw.decode("utf-8", "replace").split("\n"):
        if PROGRESS.search(ln):
            dropped += 1
            continue
        kept.append(ln)
    return "\n".join(kept), dropped


def flatten_json(j, prefix="json"):
    """path -> scalar, with testCases keyed by testCaseDesc and permutation results by layout/C-index."""
    out = {}

    def walk(v, p):
        if isinstance(v, dict):
            for k in sorted(v):
                walk(v[k], f"{p}.{k}" if p else k)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                key = f"{p}[{i}]"
                if isinstance(item, dict):
                    if "testCaseDesc" in item:
                        key = f"{p}[{item['testCaseDesc']}]"
                    elif "iteration" in item:
                        it = item.get("iteration")
                        cname = {0: "C0", 1: "C1", 2: "C2"}.get(it, f"it{it}")
                        key = f"{p}[{item.get('dataLayout', '?')}].{cname}"
                walk(item, key)
        else:
            out[p] = v
    walk(j, prefix)
    return out


def labelled_stdout(text: str):
    """label -> value from the recognised line shapes; repeated labels get #2, #3 ... suffixes
    (ea_restart prints 'Literal <est>' once for rows and once for columns, in that order)."""
    out, counts = {}, {}

    def put(label, value):
        n = counts.get(label, 0) + 1
        counts[label] = n
        out[label if n == 1 else f"{label}#{n}"] = value

    for ln in text.split("\n"):
        s = ln.rstrip()
        if not s:
            continue
        m = CTABLE.match(s)
        if m and m.group("name") in CTABLE_NAMES:
            put(f"C-table[{m.group('name')}].C0", m.group("c0"))
            put(f"C-table[{m.group('name')}].C1", m.group("c1"))
            put(f"C-table[{m.group('name')}].C2", m.group("c2"))
            put(f"C-table[{m.group('name')}].failed", "yes" if m.group("star") else "no")
            continue
        m = EST_FIELD.match(s)
        if m:
            put(f"{m.group('label').strip()}: {m.group('field').strip()}", m.group("value").strip())
            continue
        m = LABEL_EQ.match(s)
        if m:
            put(m.group("label").strip(), m.group("value").strip())
            continue
        m = LABEL_COLON.match(s)
        if m:
            put(m.group("label").strip(), m.group("value").strip())
            continue
    return out


class Run:
    def __init__(self, tool, case, tag, d):
        self.tool, self.case, self.tag, self.dir = tool, case, tag, d
        m = TAG.match(tag)
        self.arm = m.group("arm") if m else None
        self.threads = int(m.group("threads")) if m else None
        self.rep = int(m.group("rep")) if m else None
        self.meta = load_meta(os.path.join(d, tag + ".meta"))
        self.problems = []
        p = lambda ext: os.path.join(d, tag + ext)  # noqa: E731
        self.rc = read(p(".rc")).decode().strip() if os.path.exists(p(".rc")) else None
        if self.rc is None:
            self.problems.append("no .rc file (the run did not finish writing)")
        self.stdout_raw = read(p(".stdout.txt")) if os.path.exists(p(".stdout.txt")) else b""
        self.stderr = read(p(".stderr.txt")) if os.path.exists(p(".stderr.txt")) else b""
        self.stdout, self.dropped = normalise_stdout(self.stdout_raw)
        self.json, self.json_text = (None, "")
        if os.path.exists(p(".json")):
            self.json, self.json_text = normalise_json(read(p(".json")))
            if self.json is None:
                self.problems.append(self.json_text)
                self.json_text = ""
        else:
            self.problems.append("no .json report")
        # persist the normalised channels beside the run (rule 17: files, not pipes)
        with open(p(".norm.stdout"), "w", encoding="utf-8") as f:
            f.write(self.stdout)
        with open(p(".norm.json"), "w", encoding="utf-8") as f:
            f.write(self.json_text)
        self.labels = labelled_stdout(self.stdout)
        self.jflat = flatten_json(self.json) if isinstance(self.json, dict) else {}
        self.well_formed = self.check_well_formed()

    def check_well_formed(self):
        j = self.json if isinstance(self.json, dict) else {}
        if j.get("reportComplete") is False:
            self.problems.append("JSON is the C14 placeholder (reportComplete false): the assessment did not complete")
        if self.tool == "non_iid":
            if self.rc != "0":
                self.problems.append(f"rc {self.rc} (expected 0)")
            if "Assessed min entropy:" not in self.stdout:
                self.problems.append("final marker 'Assessed min entropy:' absent from stdout")
            if j.get("errorLevel") != 0:
                self.problems.append(f"errorLevel {j.get('errorLevel')!r} (expected 0)")
        elif self.tool == "iid":
            if self.rc not in ("0", "1"):
                self.problems.append(f"rc {self.rc} (expected 0 pass or 1 statistical fail)")
            if j.get("assessmentComplete") is not True:
                self.problems.append("assessmentComplete is not true")
            if ("Assessed min entropy:" not in self.stdout) and ("IID test suite failed" not in self.stdout):
                self.problems.append("neither 'Assessed min entropy:' nor 'IID test suite failed' in stdout")
        elif self.tool == "restart":
            stat_fail = (self.rc == "255" and j.get("errorClass") == "statistical")
            if stat_fail:
                self.statistical_failure = True
            else:
                if self.rc != "0":
                    self.problems.append(f"rc {self.rc} (expected 0, or 255 with errorClass statistical)")
                if "min(H_r, H_c, H_I):" not in self.stdout:
                    self.problems.append("final marker 'min(H_r, H_c, H_I):' absent from stdout")
                if j.get("errorLevel") != 0:
                    self.problems.append(f"errorLevel {j.get('errorLevel')!r} (expected 0)")
        return not self.problems

    def label(self):
        return self.tag


def discover(out):
    runs = {}
    for tool in TOOLS:
        tdir = os.path.join(out, tool)
        if not os.path.isdir(tdir):
            continue
        for case in sorted(os.listdir(tdir)):
            cdir = os.path.join(tdir, case)
            if not os.path.isdir(cdir):
                continue
            tags = sorted({fn[:-len(".meta")] for fn in os.listdir(cdir) if fn.endswith(".meta")})
            for tag in tags:
                if TAG.match(tag):
                    runs.setdefault((tool, case), []).append(Run(tool, case, tag, cdir))
    return runs


def diff_fields(a: Run, b: Run):
    """List of (label, va, vb, rng_dependent) across stdout labels, JSON paths, rc, stderr."""
    diffs = []
    for key in sorted(set(a.labels) | set(b.labels)):
        va, vb = a.labels.get(key, "<absent>"), b.labels.get(key, "<absent>")
        if va != vb:
            diffs.append((key, va, vb))
    for key in sorted(set(a.jflat) | set(b.jflat)):
        va, vb = a.jflat.get(key, "<absent>"), b.jflat.get(key, "<absent>")
        if va != vb:
            diffs.append((key, json.dumps(va), json.dumps(vb)))
    if a.rc != b.rc:
        diffs.append(("rc", str(a.rc), str(b.rc)))
    if a.stderr != b.stderr:
        diffs.append(("stderr", repr(a.stderr[:200]), repr(b.stderr[:200])))
    # unlabelled stdout lines that differ (anything the label shapes did not catch)
    la, lb = a.stdout.split("\n"), b.stdout.split("\n")
    if a.stdout != b.stdout:
        sa, sb = set(la), set(lb)
        for ln in sorted(sa - sb):
            if not any(regex.match(ln) for regex in (EST_FIELD, LABEL_EQ, LABEL_COLON, CTABLE)):
                diffs.append((f"stdout-line:{ln[:80]}", "present", "<absent>"))
        for ln in sorted(sb - sa):
            if not any(regex.match(ln) for regex in (EST_FIELD, LABEL_EQ, LABEL_COLON, CTABLE)):
                diffs.append((f"stdout-line:{ln[:80]}", "<absent>", "present"))
    out = []
    for k, va, vb in diffs:
        dep = bool(RNG_DEPENDENT.search(k))
        # the PRESENCE of the assessed figure follows the verdict; its VALUE does not
        if dep and (k == "Assessed min entropy" or k.endswith(".hAssessed")) and "<absent>" not in (va, vb):
            dep = False
        out.append((k, va, vb, dep))
    return out


def channels_identical(a: Run, b: Run):
    return dict(json=(a.json_text == b.json_text), stdout=(a.stdout == b.stdout),
                stderr=(a.stderr == b.stderr), rc=(a.rc == b.rc))


def classify(tool, runs, pairs):
    """pairs: list of dict(a, b, identical, diffs, well_formed)."""
    if any(not r.well_formed for r in runs):
        return "INCOMPLETE"
    if not pairs:
        return "NO-PAIRS"
    same_t = [p for p in pairs if p["a"].threads == p["b"].threads and p["a"].arm == p["b"].arm]
    cross_t = [p for p in pairs if p["a"].threads != p["b"].threads and p["a"].arm == p["b"].arm]
    if tool == "iid":
        # the RNG-independent view decides the class; RNG-dependent variation is recorded apart
        def indep_diff(p):
            return [d for d in p["diffs"] if not d[3]]
        if all(not indep_diff(p) for p in pairs):
            return "DETERMINISTIC (RNG-independent fields)" if all(p["identical"] for p in pairs) \
                else "DETERMINISTIC (RNG-independent fields); RNG-dependent fields vary"
        if any(indep_diff(p) for p in same_t):
            return "NONDETERMINISTIC (RNG-independent field varies between repeats)"
        return "THREAD-DEPENDENT (RNG-independent field varies with thread count)"
    if all(p["identical"] for p in pairs):
        return "DETERMINISTIC"
    if any(not p["identical"] for p in same_t):
        return "NONDETERMINISTIC"
    # repeats identical, cross-thread differ
    t_pairs = {tuple(sorted((p["a"].threads, p["b"].threads))): p["identical"] for p in cross_t}
    if t_pairs.get((1, 2), None) is True and (t_pairs.get((1, 10)) is False or t_pairs.get((2, 10)) is False):
        return "10-ONLY (thread-dependent, not visible at 2)"
    return "THREAD-DEPENDENT"


def iid_table(runs):
    """Per-run verdict and counters, for the RESULTS table."""
    rows = []
    for r in runs:
        j = r.json if isinstance(r.json, dict) else {}
        verdict = r.labels.get("IID permutation tests", "<absent>")
        rows.append(dict(tag=r.tag, arm=r.arm, threads=r.threads, rc=r.rc,
                         chi=r.labels.get("Chi square tests", "?"),
                         lrs=r.labels.get("Length of longest repeated substring test", "?"),
                         perm=verdict, iid=j.get("IID"), err=j.get("errorLevel"),
                         assessed=r.labels.get("Assessed min entropy", "<absent>"),
                         source=r.meta.get("EA_TEST_RANDOM_SOURCE", "") or "/dev/urandom (default)",
                         wall=r.meta.get("wall_seconds", "?")))
    return rows


def counters_matrix(runs):
    """statistic -> list of (tag, C0, C1, C2)."""
    names = sorted(CTABLE_NAMES, key=lambda n: list(sorted(CTABLE_NAMES)).index(n))
    out = {}
    for n in names:
        out[n] = [(r.tag, r.labels.get(f"C-table[{n}].C0", "-"), r.labels.get(f"C-table[{n}].C1", "-"),
                   r.labels.get(f"C-table[{n}].C2", "-")) for r in runs]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--smoke", action="store_true", help="label the report as the smoke (plumbing) run")
    args = ap.parse_args(argv)
    out = os.path.abspath(args.out)
    runs = discover(out)
    if not runs:
        print(f"NO RUNS under {out}; nothing compared (SHAPE-03: this is a refusal, not a pass)")
        return 2

    host = read(os.path.join(out, "host.txt")).decode("utf-8", "replace") if os.path.exists(os.path.join(out, "host.txt")) else "(host.txt absent)"
    bins = read(os.path.join(out, "binaries.sha256")).decode("utf-8", "replace") if os.path.exists(os.path.join(out, "binaries.sha256")) else "(binaries.sha256 absent)"

    L = []
    L.append(f"# Determinism and thread-count phase -- RESULTS{' (SMOKE: plumbing check on 20,000-sample inputs, non-compliant, <= 2 threads)' if args.smoke else ''}")
    L.append("")
    L.append(f"Written {datetime.datetime.now().astimezone().isoformat(timespec='seconds')} by harness/determinism/compare_runs.py from `{out}`.")
    L.append("")
    L.append("## Binaries measured (instrument rule 4) and host")
    L.append("")
    L.append("```")
    L.append(bins.strip())
    L.append("```")
    L.append("```")
    L.append(host.strip())
    L.append("```")
    L.append("")
    L.append("## Threading in the three tools, from the source (the measurement below tests this)")
    L.append("")
    L.append("- `ea_non_iid`: NO `#pragma omp` anywhere in `non_iid_main.cpp`, `non_iid/*.h`, `shared/*.h` (`grep -rn 'pragma omp'`; the only `omp` token is `#include <omp.h>` in `shared/utils.h:19`). `libdivsufsort` does not link libomp (`otool -L`). `OMP_NUM_THREADS` should therefore have NO effect; any thread-dependent difference here is itself a finding (something outside the tool's own code -- runtime memory layout reaching an uninitialised read -- and belongs in the sanitizer phase).")
    L.append("- `ea_iid`: ONE parallel region, `iid/permutation_tests.h:625-729` (`omp parallel` / `omp for` over the 10,000 permutations, `omp critical(resultUpdate)` for the counters). Each thread copies the `/dev/urandom` seed and calls `xoshiro_jump(omp_get_thread_num(), ...)` (`:649`). The seed is read by `shared/utils.h:seed()` from the LITERAL path `/dev/urandom` (`:797`); `EA_TEST_RANDOM_SOURCE` reaches only `TestRunUtils.h:129` (`g_randomSourcePath`) and is used only for the report temp-file suffix (`:478`). PREDICTION: arm (b) varies exactly like arm (a).")
    L.append("- `ea_restart`: the only `#pragma omp` is in `simulateBound()` (`restart_main.cpp:307-316`), which is called only under `#ifdef EA_RESTART_WITHOUT_C23_FIX` (`:745`); the production compile line (BUILD-LINES.md) defines nothing, so under `-n` NO parallel region executes and `OMP_NUM_THREADS` should have no effect. Under `-i` it is threaded through `permutation_tests()` (`:1127`, `:1134`) -- not run here (heavy, and seeded like `ea_iid`).")
    L.append("- `xoshiro_jump(k)` for k >= 2: re-derived independently in `harness/determinism/xoshiro_model.py` (closed form `J (I+J)^(k-1) S0`; log `xoshiro-model.log`). Consequence for this phase: with the seed live every run differs; with a fixed seed the permutation SET would still depend on the thread count (static `omp for` partition, one stream per thread), so counters changing with the thread count would be expected and only a VERDICT change would not be.")
    L.append("")
    L.append("## How to read the classes")
    L.append("")
    L.append("| class | pattern in the pair table | what it indicates |")
    L.append("|---|---|---|")
    L.append("| DETERMINISTIC | every pair identical on json/stdout/stderr/rc | no race, no reduction-order effect, no RNG in the path (within n = 2 repeats per thread count) |")
    L.append("| THREAD-DEPENDENT | repeats at one thread count identical; 1 vs 2 differ | parallel reduction order (FP associativity) or per-thread partition -- deterministic in the thread count |")
    L.append("| 10-ONLY | 1 vs 2 identical, 1 vs 10 or 2 vs 10 differ | scheduling/contention-sensitive; NOT long double width, FMA or libm (those cannot depend on the thread count) |")
    L.append("| NONDETERMINISTIC | repeats at the same thread count differ | data race or non-thread-safe call (any tool, any non-RNG field); for `ea_iid` RNG-dependent fields it is the live seed, by design |")
    L.append("| INCOMPLETE | a run is malformed (rc, missing final line, placeholder JSON) | not a determinism result (instrument rule 2) |")
    L.append("")
    L.append("Platform classes (long double width, FMA contraction, libm) present as IDENTICAL at every thread count on this host and different from Linux by the same amount every time; see `compare-linux.md`.")
    L.append("")

    exit_code = 0
    summary_rows = []
    for (tool, case), rs in sorted(runs.items()):
        rs.sort(key=lambda r: (r.arm or "", r.threads, r.rep))
        pairs = []
        for a, b in combinations(rs, 2):
            if not (a.well_formed and b.well_formed):
                pairs.append(dict(a=a, b=b, identical=False, diffs=[], well_formed=False))
                continue
            ch = channels_identical(a, b)
            diffs = diff_fields(a, b) if not all(ch.values()) else []
            pairs.append(dict(a=a, b=b, identical=all(ch.values()), diffs=diffs, well_formed=True, ch=ch))
            # per-pair difference file
            with open(os.path.join(a.dir, f"{a.tag}__vs__{b.tag}.diff.txt"), "w", encoding="utf-8") as f:
                f.write(f"# {tool}/{case}: {a.tag} vs {b.tag}\n# channels identical: {ch}\n")
                for k, va, vb, dep in diffs:
                    f.write(f"{'RNG-DEP ' if dep else '        '}{k}\t{va}\t{vb}\n")
        cls = classify(tool, rs, pairs)
        L.append(f"## {tool} / {case} -- {cls}")
        L.append("")
        L.append("| run | arm | threads | rc | well-formed | wall s | binary sha256 (before/after) | input sha256 | progress lines dropped |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for r in rs:
            wf = "yes" if r.well_formed else "NO: " + "; ".join(r.problems)
            bsha = r.meta.get("binary_sha256", "?")
            bafter = r.meta.get("binary_sha256_after", "")
            bshow = bsha[:16] + ("" if (not bafter or bafter == bsha) else f" / CHANGED {bafter[:16]}")
            L.append(f"| {r.tag} | {r.arm or '-'} | {r.threads} | {r.rc} | {wf} | {r.meta.get('wall_seconds', '?')} | {bshow} | {r.meta.get('input_sha256', '?')[:16]} | {r.dropped} |")
        L.append("")
        L.append("| pair | json | stdout | stderr | rc | differing fields (RNG-dep / indep) |")
        L.append("|---|---|---|---|---|---|")
        for p in pairs:
            a, b = p["a"], p["b"]
            if not p["well_formed"]:
                L.append(f"| {a.tag} vs {b.tag} | - | - | - | - | NOT A RESULT: a run is malformed |")
                continue
            ch = p["ch"]
            dep = sum(1 for d in p["diffs"] if d[3]); ind = len(p["diffs"]) - dep
            L.append(f"| {a.tag} vs {b.tag} | {'=' if ch['json'] else 'DIFF'} | {'=' if ch['stdout'] else 'DIFF'} | {'=' if ch['stderr'] else 'DIFF'} | {'=' if ch['rc'] else 'DIFF'} | {len(p['diffs'])} ({dep} / {ind}) |")
        L.append("")
        # list every difference with label and both values (RNG-independent first)
        listed = False
        for p in pairs:
            if not p["well_formed"] or not p["diffs"]:
                continue
            a, b = p["a"], p["b"]
            indep = [d for d in p["diffs"] if not d[3]]
            dep = [d for d in p["diffs"] if d[3]]
            if indep:
                listed = True
                L.append(f"**{a.tag} vs {b.tag} -- RNG-INDEPENDENT differences (FINDING CANDIDATES):**")
                L.append("")
                L.append("| field | " + a.tag + " | " + b.tag + " |")
                L.append("|---|---|---|")
                for k, va, vb, _ in indep:
                    L.append(f"| `{k}` | `{va}` | `{vb}` |")
                L.append("")
            if dep:
                listed = True
                L.append(f"**{a.tag} vs {b.tag} -- RNG-dependent differences ({len(dep)}; expected under a live seed):** "
                         f"full list in `{tool}/{case}/{a.tag}__vs__{b.tag}.diff.txt`")
                L.append("")
                L.append("| field | " + a.tag + " | " + b.tag + " |")
                L.append("|---|---|---|")
                for k, va, vb, _ in dep[:60]:
                    L.append(f"| `{k}` | `{va}` | `{vb}` |")
                if len(dep) > 60:
                    L.append(f"| ... {len(dep) - 60} more | | |")
                L.append("")
        if tool == "iid":
            L.append("**Verdict and seed-source table (arm a = default `/dev/urandom`, arm b = `EA_TEST_RANDOM_SOURCE` set):**")
            L.append("")
            L.append("| run | arm | threads | random source env | rc | chi-square | LRS | permutation | JSON IID | errorLevel | Assessed min entropy | wall s |")
            L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
            for row in iid_table(rs):
                L.append(f"| {row['tag']} | {row['arm']} | {row['threads']} | {row['source']} | {row['rc']} | {row['chi']} | {row['lrs']} | {row['perm']} | {row['iid']} | {row['err']} | {row['assessed']} | {row['wall']} |")
            L.append("")
            verdicts = {r.labels.get("IID permutation tests", "<absent>") for r in rs if r.well_formed}
            if len(verdicts) > 1:
                L.append(f"**VERDICT FLIP across runs: {sorted(verdicts)} -- a seed-dependent verdict on the same bytes (MEDIUM: nondeterminism).**")
                L.append("")
            L.append("Counters C0/C1/C2 per statistic and run (`-` = not printed; a row identical across every run under a live seed would be surprising):")
            L.append("")
            hdr = "| statistic | " + " | ".join(r.tag for r in rs) + " | identical across runs |"
            L.append(hdr)
            L.append("|---|" + "---|" * len(rs) + "---|")
            for name, cells in counters_matrix(rs).items():
                vals = [f"{c0}/{c1}/{c2}" for _, c0, c1, c2 in cells]
                L.append(f"| {name} | " + " | ".join(vals) + f" | {'yes' if len(set(vals)) == 1 else 'no'} |")
            L.append("")
            b_runs = [r for r in rs if r.arm == "b" and r.well_formed]
            if len(b_runs) >= 2:
                bt = {}
                for r in b_runs:
                    bt.setdefault(r.threads, []).append(r)
                same_t_agree = []
                battery_ran = all("IID permutation tests" in r.labels for r in b_runs)
                for t, group in sorted(bt.items()):
                    if len(group) >= 2:
                        agree = all(channels_identical(group[0], g)["json"] for g in group[1:])
                        same_t_agree.append(f"threads={t}: {'AGREE' if agree else 'DIFFER'} ({len(group)} runs)")
                if battery_ran:
                    L.append("Arm (b) under `EA_TEST_RANDOM_SOURCE`: two runs at the same thread count agree on the JSON? "
                             + ("; ".join(same_t_agree) if same_t_agree else "(no repeated thread count)")
                             + ". Prediction from the source was DIFFER (the variable does not reach `seed()`); if they AGREE, the source reading above is wrong and must be re-read.")
                else:
                    L.append("Arm (b) under `EA_TEST_RANDOM_SOURCE`: the permutation battery did NOT run in every arm-b run "
                             "(skipped after a deterministic chi-square/LRS refusal), so these runs say nothing about the seed; "
                             "their agreement (" + ("; ".join(same_t_agree) if same_t_agree else "n/a") + ") is the deterministic path's.")
                L.append("")
        if tool == "restart":
            sf = [r.tag for r in rs if getattr(r, "statistical_failure", False)]
            if sf:
                L.append(f"Runs that ended in a statistical refusal (sanity/validation) -- estimators may not have run, so identity among them is weak evidence: {', '.join(sf)}")
                L.append("")
        if cls.startswith("DETERMINISTIC"):
            if "RNG-dependent fields vary" in cls:
                L.append("Reading: every RNG-independent field is identical in all pairs; only the permutation counters/verdict path varies, which the live seed explains. NOT a finding.")
            else:
                L.append("Reading: identical in every pair (n = 2 repeats per thread count); within that sample, nothing in this tool depends on the thread count or on the run.")
        elif cls == "INCOMPLETE":
            exit_code = 1
            L.append("Reading: at least one run is malformed -- see the well-formed column; nothing about determinism follows from this case until it is re-run.")
        elif cls == "NO-PAIRS":
            exit_code = 1
            L.append("Reading: fewer than two runs; nothing compared.")
        else:
            exit_code = 1
            L.append(f"Reading: **{cls}** -- see the field list above; this is a finding candidate (MEDIUM: nondeterminism, or HIGH if the mechanism is a race over memory).")
        L.append("")
        summary_rows.append((tool, case, cls, len(rs), sum(1 for p in pairs if p.get('identical'))))

    L.insert(L.index("## Threading in the three tools, from the source (the measurement below tests this)"), "## Summary\n\n| tool | case | class | runs | identical pairs |\n|---|---|---|---|---|\n" + "\n".join(f"| {t} | {c} | {cls} | {n} | {idp} |" for t, c, cls, n, idp in summary_rows) + "\n")
    with open(os.path.join(out, "RESULTS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {os.path.join(out, 'RESULTS.md')}; exit {exit_code}")
    for t, c, cls, n, idp in summary_rows:
        print(f"  {t:8s} {c:40s} {cls}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
