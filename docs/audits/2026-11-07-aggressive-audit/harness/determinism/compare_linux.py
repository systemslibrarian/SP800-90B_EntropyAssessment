#!/usr/bin/env python3
"""compare_linux.py -- this host's ea_non_iid -vv output against the Linux-matched refdata.

THE REFERENCE SIDE.  cpp/selftest/refdata/*.res are NIST's published reference outputs
(upstream, produced on Linux x86-64 / GCC, where long double is x87 80-bit extended --
audits/2026-10-11-independent-audit/logs/x86-64/01-float-environment.log).  The fork's
own binaries built on that platform matched them in the strict CI suite
(logs/x86-64/06-run-all-checks-strict.log: `selftest PASS`) -- matched to
compareresults.pl's epsilon, 1e-10 on min(|abs delta|, relative delta), NOT byte for
byte.  So every statement here about "Linux" is a statement about refdata plus a 1e-10
band, and the implied host-vs-Linux difference is bounded below by (delta - 1e-10).  With
--linux-dir pointing at actual -vv outputs produced by run.sh on a Linux host (same
layout), the band is zero and the comparison is exact.

THE HOST SIDE.  By default the 1-thread run of each bin/ case under <out>/non_iid/<case>/
(t1-r1.stdout.txt); --host-run selects another tag; --all-host-runs checks every run and
additionally asks whether the delta from refdata is the same at every thread count --
the platform signature.  --host-res-dir <dir> instead reads <dir>/<case>.res (the files
cpp/selftest/selftest leaves behind), which lets this script be exercised before the
determinism phase has run.

WHAT IS COMPARED.  Identity first (compareresults.pl's OC-74 limb: sample count, distinct
symbols, width -- a mismatch voids the comparison); then every numeric line in either
shape `<estimator>: <field> = <v>` / `<label> = <v>` / `<label>: <v>`, and the presence of
the textual flag lines (`Found p.`, `P_local can't change the result.`).  Keys present on
one side only are STRUCTURAL differences.  Lines beginning `#` in refdata are comments
(the DERIVED `H_bitstring Per Symbol` provenance notes) and are skipped.

CLASSES, per compared value, with delta_perl = min(|a-b|, |a-b|/max(|a|,|b|)) as
compareresults.pl computes it (the manifest's tolerances are in that metric):
  EXACT         identical decimal text
  FORMAT        different text, SAME double (refdata prints 17 significant digits where the
                current tool prints long doubles at 22; the extra digits parse to the same
                binary64 value) -- a print-width difference, not a numeric one.  Note the
                limit: 22-digit prints are compared at double precision here.
  SUBTHRESHOLD  0 < delta_perl < 1e-10: selftest passes; Linux agreement with refdata is
                only established to 1e-10, so this cannot be attributed to the platform.
                Listed (the task asks for every differing field), not flagged.
  KNOWN         delta_perl >= 1e-10 and (file, estimator, field) is a row of the manifest
                block for THIS platform with delta within its tolerance; headroom printed.
  EXCEEDS       a KNOWN row whose tolerance is exceeded -> FLAGGED (rule 6: do not widen)
  NEW           delta_perl >= 1e-10 with no manifest row -> FLAGGED: a new macOS/Linux
                difference beyond the eight known deltas.
  STRUCTURAL    key or flag line on one side only -> FLAGGED.
  MISSING       a manifest row for this platform that was never observed -> FLAGGED
                (check-platform-deltas.py rule 3: a comparison that stopped happening).

WHAT EACH CLASS OF DIFFERENCE WOULD INDICATE, AND HOW THE OUTPUTS SEPARATE THEM.
  * long double width (x87 80-bit on Linux vs IEEE double on arm64 macOS), libm
    implementation (expl/logl/lgammal/powl), FMA contraction (Apple clang on arm64
    contracts a*b+c by default; GCC on x86-64 without -mfma does not): compile-time and
    host-wide.  Signature: on this host IDENTICAL at 1, 2 and 10 threads and across
    repeats (RESULTS.md says DETERMINISTIC), and different from refdata by the SAME
    delta in every run (--all-host-runs prints 'same delta at every thread count').
    The eight known rows are all prediction-estimator P_local / min-entropy values on
    two files, consistent with the long double P_local solver.
  * data race / non-thread-safe call: NOT a platform class.  Signature in RESULTS.md:
    repeats at the same thread count differ; here it would show as a delta from refdata
    that CHANGES between host runs.  Such a row is reported here as 'delta varies across
    host runs' and must be read with RESULTS.md, not excused by any manifest row.
  * reduction order / partition: thread-count-dependent but repeat-stable.  ea_non_iid
    has no parallel region, so this class cannot arise in it; if a delta differs between
    t1 and t10 but not between repeats, that is the signature, and it points at code
    outside the tool's own sources.
  A difference that appears only at 10 threads and not at 2 is therefore never a long
  double / libm / FMA effect: those cannot see the thread count.

WHAT THIS CANNOT SEE (rule 18): fields the -vv text does not print (JSON-only values);
the four corpus cases, which have no refdata; a host-vs-Linux delta below 1e-10 (inside
the band); a platform difference that leaves the printed 17 digits unchanged; and the
refdata's own correctness (WHAT-A-GREEN-SUITE-ESTABLISHES.md: ten of eleven references
are upstream-captured with no independent derivation); and any digit beyond binary64 in a
22-digit long double print (both sides are parsed as doubles).

Platform block selection follows check-platform-deltas.py: PLAT_S / PLAT_M / PLAT_CC in
the environment, else the fields in <out>/host.txt (uname_s=, uname_m=, compiler=), else
`uname`.  Exit 0 when no row is NEW/EXCEEDS/STRUCTURAL/MISSING and every case compared;
1 when any is flagged; 2 on refusal (no comparisons, identity mismatch, unreadable
manifest).  Writes <out>/compare-linux.md and <out>/compare-linux.tsv.
"""
from __future__ import annotations

import argparse
import datetime
import os
import platform
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(os.path.dirname(HERE))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(AUDIT_DIR)))
DEFAULT_OUT = os.path.join(AUDIT_DIR, "logs", "determinism")
DEFAULT_REFDATA = os.path.join(REPO, "cpp", "selftest", "refdata")
DEFAULT_MANIFEST = os.path.join(REPO, "cpp", "selftest", "known-platform-deltas.txt")
DEFAULT_BIN = os.path.join(REPO, "bin")
EPS = 1.0e-10                      # compareresults.pl: my $epsilon = 1.0E-10

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
EST_FIELD = re.compile(rf"^(?P<est>[^:=]+?): (?P<field>[^=]+?) = (?P<value>{NUM})$")
LABEL_EQ = re.compile(rf"^(?P<label>[^:=]+?) = (?P<value>{NUM})$")
LABEL_COLON = re.compile(rf"^(?P<label>[^:=]+?): (?P<value>{NUM})$")
FLAG = re.compile(r"^(?P<est>[^:=]+?): (?P<text>Found p\.|P_local can't change the result\.|.*Can't [Rr]un.*)$")
IDENT = re.compile(r"^Loaded\s+(?P<samples>\d+)\s+samples\s+of\s+(?P<distinct>\d+)\s+distinct\s+(?P<width>\d+)-bit")
FILE = re.compile(r"^(?:Opening|Loaded) file:\s*'(?P<path>[^']+)'")


def parse_res(path):
    """(identity dict, numeric dict key->(text, float), flags set)"""
    ident, nums, flags = {}, {}, set()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            s = ln.rstrip("\n")
            if not s or s.startswith("#"):
                continue
            m = FILE.match(s)
            if m:
                ident["file"] = os.path.basename(m.group("path")); continue
            m = IDENT.match(s)
            if m:
                ident.update(samples=m.group("samples"), distinct=m.group("distinct"), width=m.group("width")); continue
            m = EST_FIELD.match(s)
            if m:
                nums[(m.group("est").strip(), m.group("field").strip())] = (m.group("value"), float(m.group("value"))); continue
            m = LABEL_EQ.match(s)
            if m:
                nums[(m.group("label").strip(), "")] = (m.group("value"), float(m.group("value"))); continue
            m = LABEL_COLON.match(s)
            if m:
                nums[(m.group("label").strip(), "")] = (m.group("value"), float(m.group("value"))); continue
            m = FLAG.match(s)
            if m:
                flags.add((m.group("est").strip(), m.group("text").strip()))
    return ident, nums, flags


def perl_delta(a, b):
    ad = abs(a - b)
    mx = max(abs(a), abs(b))
    rel = ad / mx if mx > 0 else 0.0
    return min(ad, rel)


def load_manifest(path, s, m, cc):
    blocks, cur = [], None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            ln = raw.strip()
            if not ln or ln.startswith("#"):
                continue
            if ln.startswith("platform "):
                p = ln.split(None, 3)
                if len(p) < 4:
                    raise SystemExit(f"REFUSED: malformed platform line: {ln}")
                cur = dict(s=p[1], m=p[2], cc=p[3], rows={})
                blocks.append(cur)
            elif ln.startswith("delta "):
                if cur is None:
                    raise SystemExit("REFUSED: delta row before any platform line")
                f5 = ln[len("delta "):].split("|")
                if len(f5) != 5:
                    raise SystemExit(f"REFUSED: malformed delta row (5 fields expected): {ln}")
                cur["rows"][(f5[0].strip(), f5[1].strip(), f5[2].strip())] = (float(f5[3]), float(f5[4]))
            else:
                raise SystemExit(f"REFUSED: unrecognised manifest line: {ln}")
    for b in blocks:
        if b["s"] == s and b["m"] == m and b["cc"] in cc:
            return b, blocks
    return None, blocks


def host_platform(out):
    s, m, cc = os.environ.get("PLAT_S"), os.environ.get("PLAT_M"), os.environ.get("PLAT_CC")
    hp = os.path.join(out, "host.txt")
    if (not s or not m or not cc) and os.path.exists(hp):
        for ln in open(hp, encoding="utf-8", errors="replace"):
            if ln.startswith("uname_s=") and not s: s = ln.split("=", 1)[1].strip()
            if ln.startswith("uname_m=") and not m: m = ln.split("=", 1)[1].strip()
            if ln.startswith("compiler=") and not cc: cc = ln.split("=", 1)[1].strip()
    return s or platform.system(), m or platform.machine(), cc or ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--refdata", default=DEFAULT_REFDATA)
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--bin-dir", default=DEFAULT_BIN)
    ap.add_argument("--host-run", default="t1-r1", help="tag of the host run to read (default t1-r1)")
    ap.add_argument("--all-host-runs", action="store_true", help="read every run of each case")
    ap.add_argument("--host-res-dir", default=None, help="read <dir>/<case>.res instead of run outputs")
    ap.add_argument("--linux-dir", default=None, help="a Linux run tree with the same layout; replaces refdata as the reference and removes the 1e-10 band")
    ap.add_argument("--report-name", default="compare-linux")
    args = ap.parse_args(argv)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    s, m, cc = host_platform(out)
    block, blocks = load_manifest(args.manifest, s, m, cc)

    cases = sorted(fn[:-4] for fn in os.listdir(args.bin_dir) if fn.endswith(".bin"))
    ref_side = "linux-run-tree" if args.linux_dir else "refdata"
    band = 0.0 if args.linux_dir else EPS

    rows = []            # tsv rows: case, host_tag, estimator, field, ref, host, abs, perl, class
    problems = []
    seen_manifest = {}   # manifest key -> list of perl deltas observed
    compared_cases = []
    per_case_identity = {}

    for case in cases:
        # reference
        if args.linux_dir:
            rp = os.path.join(args.linux_dir, "non_iid", case, args.host_run + ".stdout.txt")
        else:
            rp = os.path.join(args.refdata, case + ".res")
        if not os.path.exists(rp):
            problems.append(f"{case}: reference file absent: {rp}")
            continue
        rid, rnums, rflags = parse_res(rp)
        # host side(s)
        host_files = []
        if args.host_res_dir:
            hp = os.path.join(args.host_res_dir, case + ".res")
            if os.path.exists(hp):
                host_files.append((case + ".res", hp))
        else:
            cdir = os.path.join(out, "non_iid", case)
            if os.path.isdir(cdir):
                tags = sorted(fn[:-len(".stdout.txt")] for fn in os.listdir(cdir) if fn.endswith(".stdout.txt") and not fn.endswith(".norm.stdout.txt"))
                if not args.all_host_runs:
                    tags = [t for t in tags if t == args.host_run]
                for t in tags:
                    rc_path = os.path.join(cdir, t + ".rc")
                    rc = open(rc_path).read().strip() if os.path.exists(rc_path) else None
                    if rc != "0":
                        problems.append(f"{case}/{t}: host run rc {rc!r}, not compared (instrument rule 2)")
                        continue
                    host_files.append((t, os.path.join(cdir, t + ".stdout.txt")))
        if not host_files:
            problems.append(f"{case}: no host output to compare (expected {args.host_run}.stdout.txt under {out}/non_iid/{case}/" + (f" or {args.host_res_dir}/{case}.res" if args.host_res_dir else "") + ")")
            continue
        deltas_by_key = {}
        for tag, hp in host_files:
            hid, hnums, hflags = parse_res(hp)
            # identity (OC-74)
            for k in ("samples", "distinct", "width"):
                if rid.get(k) is None or hid.get(k) is None:
                    problems.append(f"{case}/{tag}: identity field '{k}' absent on one side (ref {rid.get(k)!r}, host {hid.get(k)!r}); comparison REFUSED")
                    hnums = None
                    break
                if rid.get(k) != hid.get(k):
                    problems.append(f"{case}/{tag}: IDENTITY MISMATCH on {k}: ref {rid[k]} host {hid[k]}; the numbers would be about different things")
                    hnums = None
                    break
            if hnums is None:
                continue
            per_case_identity[case] = f"{hid.get('samples')} samples / {hid.get('distinct')} distinct / {hid.get('width')}-bit"
            if not rnums or not hnums:
                problems.append(f"{case}/{tag}: zero numeric keys on one side (ref {len(rnums)}, host {len(hnums)}); nothing compared")
                continue
            compared_cases.append((case, tag))
            for key in sorted(set(rnums) | set(hnums)):
                est, field = key
                mkey = (case + ".bin", est, field)
                if key not in rnums or key not in hnums:
                    rows.append((case, tag, est, field, rnums.get(key, ("<absent>",))[0], hnums.get(key, ("<absent>",))[0], "", "", "STRUCTURAL"))
                    continue
                (rt, rv), (ht, hv) = rnums[key], hnums[key]
                ad = abs(rv - hv)
                pd = perl_delta(rv, hv)
                if rt == ht:
                    cls = "EXACT"
                elif rv == hv:
                    cls = "FORMAT"
                elif pd < EPS:
                    cls = "SUBTHRESHOLD"
                else:
                    row = block["rows"].get(mkey) if block else None
                    if row is None:
                        cls = "NEW"
                    elif pd > row[0]:
                        cls = "EXCEEDS"
                    else:
                        cls = "KNOWN"
                    if row is not None:
                        seen_manifest.setdefault(mkey, []).append(pd)
                deltas_by_key.setdefault(key, []).append(pd)
                rows.append((case, tag, est, field, rt, ht, f"{ad:.6g}", f"{pd:.6g}", cls))
            for fl in sorted(rflags ^ hflags):
                rows.append((case, tag, fl[0], f"flag:{fl[1]}", "present" if fl in rflags else "<absent>", "present" if fl in hflags else "<absent>", "", "", "STRUCTURAL"))
        # platform signature across host runs
        if args.all_host_runs and len(host_files) > 1:
            for key, ds in deltas_by_key.items():
                if len(ds) > 1 and any(d >= EPS for d in ds):
                    same = len({f"{d:.17g}" for d in ds}) == 1
                    rows.append((case, "ALL", key[0], key[1], "", "", "", ";".join(f"{d:.6g}" for d in ds),
                                 "same delta at every host run (platform signature)" if same else "DELTA VARIES ACROSS HOST RUNS (not a platform effect; read RESULTS.md)"))

    # manifest completeness for this platform
    missing = []
    if block is not None:
        for mkey in sorted(block["rows"]):
            if mkey not in seen_manifest and any(c == mkey[0][:-4] for c, _ in compared_cases):
                missing.append(mkey)

    flagged = [r for r in rows if r[8] in ("NEW", "EXCEEDS", "STRUCTURAL") or r[8].startswith("DELTA VARIES")]
    known = [r for r in rows if r[8] == "KNOWN"]
    sub = [r for r in rows if r[8] == "SUBTHRESHOLD"]
    fmt = [r for r in rows if r[8] == "FORMAT"]
    exact = [r for r in rows if r[8] == "EXACT"]

    # ---- write tsv
    tsv = os.path.join(out, args.report_name + ".tsv")
    with open(tsv, "w", encoding="utf-8") as f:
        f.write("case\thost_run\testimator\tfield\treference\thost\tabs_delta\tperl_delta\tclass\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")

    # ---- write md
    L = []
    L.append("# macOS host vs Linux-matched reference -- compare_linux.py")
    L.append("")
    L.append(f"Written {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}. Reference side: **{ref_side}** "
             f"({'exact Linux outputs' if args.linux_dir else 'cpp/selftest/refdata, which the strict x86-64 CI suite matched to 1e-10 (06-run-all-checks-strict.log: selftest PASS)'}). "
             f"Host side: {'<host-res-dir>/<case>.res = ' + args.host_res_dir if args.host_res_dir else ('every run' if args.all_host_runs else 'run ' + args.host_run) + ' under ' + out + '/non_iid/'}.")
    L.append("")
    L.append(f"Platform block requested: uname -s `{s}`, uname -m `{m}`, compiler `{cc[:60]}` -> "
             + (f"MATCHED block `platform {block['s']} {block['m']} {block['cc']}` with {len(block['rows'])} rows" if block else
                "NO BLOCK MATCHES: every difference >= 1e-10 is NEW on this platform (as check-platform-deltas.py would rule)"))
    L.append("")
    L.append("| class | count | meaning |")
    L.append("|---|---|---|")
    L.append(f"| EXACT | {len(exact)} | identical decimal text |")
    L.append(f"| FORMAT | {len(fmt)} | same double, different print width (17 vs 22 significant digits); not a numeric difference |")
    L.append(f"| SUBTHRESHOLD | {len(sub)} | 0 < delta < 1e-10: inside the band in which Linux itself was matched; not attributable |")
    L.append(f"| KNOWN | {len(known)} | in the manifest for this platform, within tolerance |")
    L.append(f"| NEW / EXCEEDS / STRUCTURAL / varying | {len(flagged)} | **FLAGGED** |")
    L.append(f"| MISSING manifest rows | {len(missing)} | listed rows never observed (completeness) |")
    L.append("")
    L.append(f"Cases compared: {len(set(c for c, _ in compared_cases))} of {len(cases)} bin/ files; host runs read: {len(compared_cases)}. "
             "The four corpus cases have no refdata and are host-only (RESULTS.md).")
    L.append("")
    if flagged:
        L.append("## FLAGGED differences (new beyond the known deltas, exceeding a row, structural, or varying across host runs)")
        L.append("")
        L.append("| case | host run | estimator | field | reference | host | abs delta | perl delta | implied host-vs-Linux >= | class |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in flagged:
            implied = ""
            try:
                implied = f"{max(0.0, float(r[7]) - band):.3g}" if r[7] else ""
            except ValueError:
                pass
            L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | `{r[4]}` | `{r[5]}` | {r[6]} | {r[7]} | {implied} | **{r[8]}** |")
        L.append("")
    if known:
        L.append("## KNOWN platform deltas observed (manifest rows), with headroom")
        L.append("")
        L.append("| case | host run | estimator | field | reference | host | perl delta | tolerance | observed-in-manifest | headroom tol/delta |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in known:
            tol, obs = block["rows"][(r[0] + ".bin", r[2], r[3])]
            d = float(r[7])
            L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | `{r[4]}` | `{r[5]}` | {r[7]} | {tol:g} | {obs:.6g} | {tol / d if d else float('inf'):.1f}x |")
        L.append("")
    if missing:
        L.append("## MISSING: manifest rows for this platform that were not observed")
        L.append("")
        for mk in missing:
            L.append(f"- {mk[0]} | {mk[1]} | {mk[2]}")
        L.append("")
    if sub:
        L.append("## SUBTHRESHOLD differences (listed, not flagged)")
        L.append("")
        L.append("| case | host run | estimator | field | reference | host | abs delta | perl delta |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in sub:
            L.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | `{r[4]}` | `{r[5]}` | {r[6]} | {r[7]} |")
        L.append("")
    if problems:
        L.append("## Problems (refusals and skipped comparisons)")
        L.append("")
        for p in problems:
            L.append(f"- {p}")
        L.append("")
    L.append("## Identity matched per case (OC-74 limb)")
    L.append("")
    for c in sorted(per_case_identity):
        L.append(f"- {c}: {per_case_identity[c]}")
    L.append("")
    L.append("## What a difference in each class would indicate")
    L.append("")
    L.append("- **Same delta at every thread count and repeat on this host, present against Linux**: a compile-time / host-wide property -- `long double` width (x87 80-bit on x86-64 Linux vs IEEE double on arm64 macOS), libm (`expl`, `logl`, `lgammal`, `powl`), or FMA contraction (Apple clang contracts on arm64 by default; the known eight rows are all prediction-estimator `P_local` / `min entropy` values, consistent with the long double `P_local` solver).")
    L.append("- **Delta that varies between host runs at the same thread count**: a data race or non-thread-safe call, never a platform effect; it must be read with RESULTS.md and cannot be excused by a manifest row.")
    L.append("- **Delta that varies with the thread count but not between repeats**: reduction order or partition; `ea_non_iid` has no parallel region, so this would point outside the tool's own code.")
    L.append("- **A difference only at 10 threads and not at 2** therefore never points at `long double` width: a thread count cannot change a compile-time format.")
    L.append("")
    L.append("Limits (rule 18): JSON-only fields are not covered; a host-vs-Linux delta below 1e-10 is invisible inside the band; a platform difference that leaves the printed 17 significant digits unchanged is invisible; the refdata's own correctness is not established by this comparison (WHAT-A-GREEN-SUITE-ESTABLISHES.md).")
    md = os.path.join(out, args.report_name + ".md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    if not compared_cases:
        print("NO COMPARISONS WERE MADE (refusal, exit 2)")
        for p in problems:
            print("  - " + p)
        return 2
    print(f"wrote {md} and {tsv}: EXACT {len(exact)}, FORMAT {len(fmt)}, SUBTHRESHOLD {len(sub)}, KNOWN {len(known)}, FLAGGED {len(flagged)}, MISSING {len(missing)}; "
          f"{len(set(c for c, _ in compared_cases))} of {len(cases)} cases compared")
    if problems:
        print(f"  {len(problems)} problem(s) recorded in the report")
    return 1 if (flagged or missing or len(set(c for c, _ in compared_cases)) != len(cases)) else 0


if __name__ == "__main__":
    sys.exit(main())
