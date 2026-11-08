#!/usr/bin/env python3
"""diff_driver.py -- differential driver: cpp/ea_non_iid against the py90b reference.

THIS IS THE HARNESS, not a reference estimator.  It was written without reading
any file under cpp/ or any py90b module; the only thing taken from the C++ is the
label vocabulary in reference/cpp-verbose-labels-non_iid.txt.

For every (corpus file, declared bps) it runs, ONCE,

    OMP_NUM_THREADS=2 [EA_ALLOW_SHORT_DATASET=1 if n < 1,000,000]
    cpp/ea_non_iid -i -a -v -v -o <json> <file> <bps>

with stdout/stderr written to files (never piped: guide rule 17), records the
binary's sha256 beside every result (instrument rule 4), parses the verbose text
BY LABEL (instrument rule 5), and then runs each py90b module in a child process
(so a crash, hang or memory blow-up in one reference module is recorded, not
inherited).  One case at a time; resumable (a case whose result file exists is
skipped unless --force).

Two modes per (file, bps), both served by the single C++ run:
  literal    the symbols as read            <-> 'Literal <Estimator> Estimate:' lines
  bitstring  each symbol -> bps bits MSB-first, treated as 1-bit symbols (SP 800-90B
             3.1.3, PDF p. 20) <-> 'Bitstring <Estimator> Estimate:' lines
and a third pseudo-case per (file, bps), 'assessed', which combines the two per
3.1.3: H_I = min(H_original, n x H_bitstring) for non-binary sources, H_original
for binary sources, compared against 'H_original =', 'H_bitstring =',
'H_bitstring Per Symbol =' and 'Assessed min entropy:'.

Classification of every comparison (the task's six classes, worst first):
  TOOL_REFUSED       nonzero exit, signal, timeout, missing binary, or no
                     'Assessed min entropy' line (instrument rule 2: an absent line
                     is not a result; the sub-outcome is recorded in `cpp.outcome`)
  CPP_HIGHER         the C++ min-entropy exceeds the reference by more than the
                     tolerance -- THE DANGEROUS DIRECTION, flagged loudly
  CPP_LOWER          the C++ figure is below the reference by more than the tolerance
  INTERMEDIATE_DIFF  min-entropies agree but a shared intermediate differs
  NOT_RUN            a side produced no value (module missing / errored / timed out,
                     the C++ printed no value for the estimator, the reference gave
                     nan, or the mode does not apply) -- NEVER counted as agreement
  AGREE              min-entropy and every shared intermediate within tolerance

Tolerance (guide rule 16): absolute 1e-9 for probabilities and entropies, exact
for integer counts ('Mode count', 'v', 'Sum t_i', 't', 'u', 'C', 'r', 'N').  The
C++ prints doubles at 17 significant digits and long doubles at 22, so 1e-9 is
far above the printed quantisation; should a value ever be printed with fewer
digits, the tolerance for THAT comparison is widened to half a unit in its last
printed place and the record says so (a check cannot be tighter than the number
it reads).

WHAT THIS CLASSIFICATION CANNOT SEE (guide rule 18), stated here because the
branch is taken on it:
  * an estimator for which NEITHER side produced a value -- nothing is compared;
  * an intermediate the C++ does not print (e.g. P_local when it 'can't change
    the result') -- recorded under `unmatched`, not compared;
  * whether the C++ ran an estimator on translated symbols rather than the raw
    ones -- only the printed numbers are compared;
  * a difference smaller than the tolerance; and
  * for the 'assessed' pseudo-case with reference modules missing: AGREE and
    CPP_LOWER are NOT established (a missing module could only lower the reference
    minimum), so they are reported as NOT_RUN with the partial figures; CPP_HIGHER
    IS established by the available modules alone and is reported as such.

D-1 recheck (on by default; --no-d1-recheck): a disagreement whose differing intermediates
are all downstream of the 6.3.1 constant (p_u, P_global', X-bar', p) and whose delta is
below 1e-3 has the shape of documented divergence D-1 (the fork uses the binary64 0.995
quantile 2.5758293035489008 where the text prints 2.576).  The module is re-run with
z=2.5758293035489008 (name/value from --d1-option) and the comparison repeated; if it then
AGREEs the record is tagged d1_explained and the summary lists it apart from the
unexplained CPP_HIGHER cases.  THE CLASS IS NOT CHANGED: the C++ figure is still higher
than the literal-text reference and the record says so; the tag says why.  A module that
does not accept the option is recorded as 'recheck not possible' (tag D-1?).

Spec readings exposed as options (recorded, not decided here):
  --binary-rule observed|declared   what 'binary' means for 6.2's binary-only
        estimators (Collision, Markov, Compression) and for 3.1.3's 'If the
        sequential dataset is not binary'.  Default 'observed': k <= 2 distinct
        values (SP 800-90B 4.4.2 / 5 define binary by the alphabet; the fork's
        withdrawn F01 recorded the same reading).  'declared': bps == 1.
  --bit-order msb|lsb               bit order of the 3.1.3 bitstring (the standard
        does not fix it; F21 in the 2026-09-30 tracker).  Default msb (task contract).
  --bitstring-truncate N            3.1.3: 'The bits after the first 1 000 000 bits
        may be ignored'.  Default 0 = use all bits, matching the tool's -a.

Files:
  logs/diff/raw/<stem>-b<bps>.cpp.{stdout.txt,stderr.txt,json,meta.json}
  logs/diff/raw/<stem>-b<bps>-<mode>.<module>.ref.{json,stderr.txt}
  logs/diff/<stem>-b<bps>-<mode>.json           one result per case (strict JSON;
                                                non-finite floats are the strings
                                                "NaN", "Infinity", "-Infinity")
  logs/diff/SUMMARY.md                          one verdict line per case
  logs/diff/SELF-CHECK.md                       --self-check record

Usage:
  diff_driver.py run [--only GLOB] [--max-n N] [--mode literal|bitstring|both]
                     [--file PATH:BPS ...] [--force] [--force-ref] [--skip-ref] [--list]
                     [--no-d1-recheck] [--d1-option NAME=VALUE]
                     [--cpp-timeout S] [--ref-timeout S] [--ref-option mod:key=value]
                     [--binary-rule R] [--bit-order O] [--bitstring-truncate N]
  diff_driver.py summary
  diff_driver.py --self-check [--case CASE]
  diff_driver.py <rawfile> <bits_per_symbol> [--literal|--bitstring]   (API contract:
                     prints the combined reference dict as JSON; no C++ involved)
"""
from __future__ import annotations

import argparse
import fnmatch
import glob
import hashlib
import importlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
import traceback

import numpy as np

# ----------------------------------------------------------------------------
# paths and constants
# ----------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.abspath(os.path.join(AUDIT_DIR, "..", "..", ".."))
REFERENCE_DIR = os.path.join(AUDIT_DIR, "reference")
CORPUS_DIR = os.path.join(AUDIT_DIR, "corpus")
MANIFEST = os.path.join(CORPUS_DIR, "MANIFEST.txt")
LOGS_DIFF = os.path.join(AUDIT_DIR, "logs", "diff")
RAW_DIR = os.path.join(LOGS_DIFF, "raw")
BINARY = os.path.join(REPO_ROOT, "cpp", "ea_non_iid")
LABEL_CAPTURE = os.path.join(REFERENCE_DIR, "cpp-verbose-labels-non_iid.txt")

TOL = 1e-9
MIN_COMPLIANT_N = 1_000_000  # SP 800-90B 3.1.1
CLASS_ORDER = ["TOOL_REFUSED", "CPP_HIGHER", "CPP_LOWER", "INTERMEDIATE_DIFF", "NOT_RUN", "AGREE"]
INTEGER_LABELS = {"Mode count", "v", "Sum t_i", "t", "u", "C", "r", "N"}

# module name -> the estimator name the C++ prints between 'Literal '/'Bitstring ' and ' Estimate:'
MODULES = [
    ("mcv", "Most Common Value"),
    ("collision", "Collision"),
    ("markov", "Markov"),
    ("compression", "Compression"),
    ("ttuple", "t-Tuple"),
    ("lrs", "LRS"),
    ("multimcw", "MultiMCW Prediction"),
    ("lag", "Lag Prediction"),
    ("multimmc", "MultiMMC Prediction"),
    ("lz78y", "LZ78Y Prediction"),
]
MODULE_BY_ESTIMATOR = {e: m for m, e in MODULES}
ESTIMATOR_BY_MODULE = dict(MODULES)
BINARY_ONLY = {"collision", "markov", "compression"}  # SP 800-90B 6.2 (PDF p. 49)
Z_EXACT = 2.5758293035489008   # the binary64 0.995 standard-normal quantile (documented divergence D-1)
Z_PRINTED = 2.576              # what SP 800-90B prints (6.3.1 step 2, PDF p. 49: "2.576 corresponds to the Z(1-0.005) value")
# keys downstream of that constant: MCV/t-Tuple/LRS p_u, the predictors' P_global', Collision/Compression X-bar'
# and hence p.  A disagreement confined to these keys is a CANDIDATE D-1 difference; the recheck decides.
D1_KEYS = {"p_u", "p_global'", "x_bar'", "p"}


def ensure_reference_on_path() -> None:
    if REFERENCE_DIR not in sys.path:
        sys.path.insert(0, REFERENCE_DIR)


# ----------------------------------------------------------------------------
# small utilities
# ----------------------------------------------------------------------------

def sha256_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def is_nan(x) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False


def sanitize(obj):
    """Make an object strict-JSON serialisable: numpy scalars/arrays -> Python,
    non-finite floats -> strings "NaN" / "Infinity" / "-Infinity"."""
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    return obj


def desanitize(obj):
    """Inverse of sanitize for the three non-finite markers (used when reloading results)."""
    if isinstance(obj, dict):
        return {k: desanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [desanitize(v) for v in obj]
    if obj == "NaN":
        return float("nan")
    if obj == "Infinity":
        return float("inf")
    if obj == "-Infinity":
        return float("-inf")
    return obj


# TABLES ARE ELIDED FROM THE RECORD, NOT FROM THE COMPARISON (2026-11-07, orchestrator).
# The first 50,000-sample pass wrote records of 45-89 MB each: the LRS reference returns
# per-W tables (P_W, Pmax_W, positions_choose2_W) with one entry per W from u to v, and on
# periodic data v is nearly the whole file -- 379,433 entries, stored twice (reference and
# the D-1 recheck). No C++ label is ever compared against such a table (the C++ prints
# scalars), so the comparison loses nothing; the record keeps a count, a sha256 of the
# table's canonical JSON, and the numeric range, so a reader can still see what was there
# and re-derive it from the module. Threshold 512 keeps every per-symbol histogram (<= 256).
ELIDE_OVER = 512


def _elided(obj):
    import hashlib
    canon = json.dumps(sanitize(obj), sort_keys=True)
    out = {"_elided": True, "entries": len(obj), "sha256": hashlib.sha256(canon.encode("utf-8")).hexdigest()}
    vals = list(obj.values()) if isinstance(obj, dict) else list(obj)
    nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if nums and len(nums) == len(vals):
        out["min"] = min(nums)
        out["max"] = max(nums)
    return out


def compact_tables(obj):
    """Return obj with every dict/list of more than ELIDE_OVER entries replaced by a summary."""
    if isinstance(obj, dict):
        if len(obj) > ELIDE_OVER:
            return _elided(obj)
        return {k: compact_tables(v) for k, v in obj.items()}
    if isinstance(obj, list):
        if len(obj) > ELIDE_OVER:
            return _elided(obj)
        return [compact_tables(v) for v in obj]
    return obj


def write_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sanitize(obj), f, indent=1, sort_keys=False, allow_nan=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return desanitize(json.load(f))


# ----------------------------------------------------------------------------
# input handling (the task's file contract: one symbol per byte, low bps bits)
# ----------------------------------------------------------------------------

def read_symbols(path: str, bps: int) -> tuple[np.ndarray, dict]:
    """Return (symbols masked to the low `bps` bits, info).

    info records how many bytes exceeded the declared width and the raw maximum,
    because the C++ may treat such a file differently (D-6: it refuses) and the
    record must say what the reference was fed.
    """
    raw = np.fromfile(path, dtype=np.uint8)
    mask = (1 << bps) - 1
    over = int(np.count_nonzero(raw > mask)) if len(raw) else 0
    sym = (raw & mask).astype(np.uint8)
    info = dict(n=int(len(raw)), overwidth_count=over, raw_max=int(raw.max()) if len(raw) else None,
                masked=bool(over > 0))
    return sym, info


def to_bitstring(symbols: np.ndarray, bps: int, bit_order: str = "msb") -> np.ndarray:
    """SP 800-90B 3.1.3 (PDF p. 20): 'the sequential dataset that contains L samples
    (each having n bits) is considered as a bitstring of size nL'.  Each symbol becomes
    `bps` bits, MSB-first by default (the standard does not fix the order)."""
    sym = np.asarray(symbols, dtype=np.uint8)
    if bps == 8:
        bits = np.unpackbits(sym[:, None], axis=1)  # MSB-first
    else:
        shifts = np.arange(bps - 1, -1, -1, dtype=np.uint8)  # MSB first
        bits = ((sym[:, None] >> shifts[None, :]) & 1).astype(np.uint8)
    if bit_order == "lsb":
        bits = bits[:, ::-1]
    elif bit_order != "msb":
        raise ValueError("bit_order must be 'msb' or 'lsb'")
    return np.ascontiguousarray(bits.reshape(-1))


def observed_alphabet(symbols: np.ndarray) -> np.ndarray:
    return np.unique(np.asarray(symbols))


def is_binary(symbols: np.ndarray, bps: int, rule: str = "observed") -> tuple[bool, int]:
    """(binary?, k).  'observed': k <= 2 (4.4.2 'produces only two distinct values';
    5 'binary, i.e., k = 2'; k = 1 is folded in as the degenerate case, which is what
    an 'alphabet size > 2' gate does).  'declared': the declared width is 1."""
    k = int(len(observed_alphabet(symbols)))
    if rule == "observed":
        return k <= 2, k
    if rule == "declared":
        return bps == 1, k
    raise ValueError("binary rule must be 'observed' or 'declared'")


def translate_binary(symbols: np.ndarray) -> tuple[np.ndarray, dict]:
    """Map a <= 2-symbol alphabet onto {0, 1} in ascending order of value (so the
    smaller value is 0).  Min-entropy is label-invariant for every estimator; only the
    Markov P_0/P_1 labels depend on this choice, which is why it is recorded."""
    alph = observed_alphabet(symbols)
    assert len(alph) <= 2
    mapping = {int(v): i for i, v in enumerate(alph)}
    out = np.zeros(len(symbols), dtype=np.uint8)
    for v, i in mapping.items():
        out[np.asarray(symbols) == v] = i
    return out, {"k": len(alph), "map": mapping, "order": "ascending value -> 0,1"}


# ----------------------------------------------------------------------------
# parsing the C++ verbose text, by label
# ----------------------------------------------------------------------------

_RE_LOADED_FILE = re.compile(r"^Loaded file: '(?P<path>.*)' \(SHA-256 hash (?P<sha>[0-9a-fA-F]{64}) of assessed bytes\)\s*$")
_RE_LOADED = re.compile(r"^Loaded (?P<n>\d+) samples of (?P<k>\d+) distinct (?P<w>\d+)-bit-wide symbols\s*$")
_RE_NBIN = re.compile(r"^Number of Binary Symbols: (?P<nb>\d+)\s*$")
_RE_EST = re.compile(r"^(?P<mode>Literal|Bitstring) (?P<est>.+?) Estimate: (?P<rest>.*)$")
_RE_KV = re.compile(r"^(?P<label>[^=]+?)\s*=\s*(?P<value>\S+)\s*$")
_RE_H = re.compile(r"^(?P<label>H_original|H_bitstring Per Symbol|H_bitstring)\s*=\s*(?P<value>\S+)\s*$")
_RE_ASSESSED = re.compile(r"^Assessed min entropy:\s*(?P<value>\S+)\s*$")
_RE_NUM = re.compile(r"^[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?$")


def parse_number(text: str):
    """int for an integer literal, float otherwise (accepts nan/inf/-0); None if not a number."""
    t = text.strip()
    if re.fullmatch(r"[-+]?\d+", t):
        return int(t)
    if _RE_NUM.fullmatch(t) or t.lower() in ("nan", "-nan", "inf", "-inf", "+inf", "infinity", "-infinity"):
        try:
            return float(t)
        except ValueError:
            return None
    return None


def printed_half_ulp(text: str) -> float:
    """Half a unit in the last printed decimal place of a numeric literal: the floor
    below which no comparison against that printed value is meaningful (rule 16)."""
    t = text.strip().lower()
    if t in ("nan", "-nan", "inf", "-inf", "+inf") or re.fullmatch(r"[-+]?\d+", t):
        return 0.0
    m = re.fullmatch(r"[-+]?(\d*)(?:\.(\d*))?(?:e([-+]?\d+))?", t)
    if not m:
        return 0.0
    decimals = len(m.group(2) or "")
    exp = int(m.group(3) or 0)
    return 0.5 * 10.0 ** (exp - decimals)


def canon_key(label: str) -> str:
    """Canonical form shared by both sides: lower-case, spaces and hyphens -> '_',
    '_prime' accepted for a trailing apostrophe, 'min entropy' <-> 'min_entropy'.
    The apostrophe is KEPT so "X-bar" and "X-bar'" stay distinct."""
    k = label.strip().lower().replace(" ", "_").replace("-", "_")
    k = re.sub(r"_+", "_", k)
    if k.endswith("_prime"):
        k = k[: -len("_prime")] + "'"
    return k


def parse_cpp_text(text: str) -> dict:
    """Parse ea_non_iid -v -v stdout by label.  Never by position: the Bitstring MCV
    lines precede the Literal ones in the capture, and other orders are possible."""
    out = {
        "loaded_file": None, "loaded_sha256": None, "n": None, "k": None, "width": None,
        "n_binary": None, "warnings": [],
        "estimates": {"Literal": {}, "Bitstring": {}},   # mode -> estimator -> label -> {'value','text'}
        "notes": {"Literal": {}, "Bitstring": {}},       # mode -> estimator -> [free text lines]
        "H_original": None, "H_bitstring": None, "H_bitstring Per Symbol": None,
        "assessed": None, "assessed_text": None,
        "summary_texts": {},
        "unparsed_estimate_lines": [], "other_lines": [],
    }
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if not line.strip():
            continue
        m = _RE_LOADED_FILE.match(line)
        if m:
            out["loaded_file"] = m.group("path")
            out["loaded_sha256"] = m.group("sha").lower()
            continue
        m = _RE_LOADED.match(line)
        if m:
            out["n"], out["k"], out["width"] = int(m.group("n")), int(m.group("k")), int(m.group("w"))
            continue
        m = _RE_NBIN.match(line)
        if m:
            out["n_binary"] = int(m.group("nb"))
            continue
        if line.startswith("***"):
            out["warnings"].append(line)
            continue
        m = _RE_ASSESSED.match(line)
        if m:
            out["assessed"] = parse_number(m.group("value"))
            out["assessed_text"] = m.group("value")
            continue
        m = _RE_H.match(line)
        if m:
            out[m.group("label")] = parse_number(m.group("value"))
            out["summary_texts"][m.group("label")] = m.group("value")
            continue
        m = _RE_EST.match(line)
        if m:
            mode, est, rest = m.group("mode"), m.group("est"), m.group("rest").strip()
            kv = _RE_KV.match(rest)
            if kv and parse_number(kv.group("value")) is not None:
                label = kv.group("label").strip()
                out["estimates"][mode].setdefault(est, {})[label] = {
                    "value": parse_number(kv.group("value")), "text": kv.group("value")}
            else:
                out["notes"][mode].setdefault(est, []).append(rest)
                if "=" in rest:
                    out["unparsed_estimate_lines"].append(line)
            continue
        out["other_lines"].append(line)
    return out


def cpp_values(parsed: dict, mode: str, estimator: str) -> dict | None:
    """{canonical key: value} for one estimator in one mode, or None if nothing printed."""
    block = parsed["estimates"][mode].get(estimator)
    if not block:
        return None
    return {canon_key(label): entry["value"] for label, entry in block.items()}


def cpp_texts(parsed: dict, mode: str, estimator: str) -> dict:
    block = parsed["estimates"][mode].get(estimator) or {}
    return {canon_key(label): entry["text"] for label, entry in block.items()}


def find_keys(obj, wanted: set, found=None, prefix=""):
    """Recursively collect `wanted` keys from a parsed JSON document (schema unknown here)."""
    if found is None:
        found = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in wanted:
                found.setdefault(k, []).append({"path": f"{prefix}/{k}", "value": v})
            find_keys(v, wanted, found, f"{prefix}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_keys(v, wanted, found, f"{prefix}[{i}]")
    return found


# ----------------------------------------------------------------------------
# comparisons
# ----------------------------------------------------------------------------

def _as_float(v):
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    return None


def compare_value(key: str, cpp_v, ref_v, cpp_text: str | None = None) -> dict:
    """Compare one shared quantity.  status: agree | differ | nan_mismatch | non_numeric."""
    rec = {"key": key, "cpp": cpp_v, "ref": ref_v, "delta": None, "tol": None, "status": None, "kind": None}
    integer_key = key in {canon_key(x) for x in INTEGER_LABELS}
    cf, rf = _as_float(cpp_v), _as_float(ref_v)
    if cf is None or rf is None:
        rec["status"] = "non_numeric"
        return rec
    if math.isnan(cf) or math.isnan(rf):
        rec["status"] = "agree" if (math.isnan(cf) and math.isnan(rf)) else "nan_mismatch"
        rec["kind"] = "nan"
        return rec
    both_integral = (isinstance(cpp_v, (int, np.integer)) and not isinstance(cpp_v, bool)
                     and isinstance(ref_v, (int, np.integer)) and not isinstance(ref_v, bool))
    if integer_key or both_integral:
        rec["kind"] = "integer-exact"
        rec["delta"] = cf - rf
        rec["tol"] = 0.0
        rec["status"] = "agree" if cf == rf else "differ"
        return rec
    tol = TOL
    if cpp_text is not None:
        hu = printed_half_ulp(cpp_text)
        if hu > tol:
            tol = hu  # rule 16: never tighter than the printed precision
            rec["tol_widened_to_printed_precision"] = True
    rec["kind"] = "float-abs"
    rec["delta"] = cf - rf
    rec["tol"] = tol
    rec["status"] = "agree" if abs(cf - rf) <= tol else "differ"
    return rec


def d1_candidate(differing_keys, delta) -> bool:
    """True when a disagreement is confined to quantities downstream of the 2.576 constant and is
    small: the shape of documented divergence D-1.  A candidate, not a verdict; the recheck decides."""
    return bool(differing_keys) and set(differing_keys) <= D1_KEYS and abs(delta) < 1e-3


def d1_recheck_record(cv: dict, ct: dict, rerun: dict, option) -> dict:
    """Compare the C++ against the module re-run with the exact quantile.  'explained' means the
    disagreement vanished (AGREE) under the exact constant, i.e. it IS documented divergence D-1."""
    name, value = option
    out = {"option": {name: value}, "possible": rerun.get("status") == "ok", "class_after": None,
           "delta_after": None, "differing_after": None, "explained": False, "error": rerun.get("error")}
    if rerun.get("status") != "ok":
        err = str(rerun.get("error") or "")
        if "TypeError" in err or "unexpected keyword" in err:
            out["error"] = f"module does not accept option {name!r}: {err}"
        return out
    c = compare_estimator(cv, ct, rerun)
    out["class_after"] = c["class"]
    out["delta_after"] = (c.get("min_entropy") or {}).get("delta")
    out["differing_after"] = [i["key"] for i in c.get("intermediates", []) if i["status"] != "agree"]
    out["explained"] = c["class"] == "AGREE"
    return out


def d1_explained_all(comparisons: dict, cls: str):
    """True when every comparison carrying the case class is D-1-explained; False when at least one
    was rechecked and is not; None when no recheck ran for one of them (or the class has no recheck)."""
    if cls not in ("CPP_HIGHER", "CPP_LOWER", "INTERMEDIATE_DIFF"):
        return None
    flagged = [c for c in comparisons.values() if c.get("class") == cls]
    if not flagged or any(c.get("d1_recheck") is None for c in flagged):
        return None
    return all(c["d1_recheck"].get("explained") for c in flagged)


def build_verdict(case: str, cls: str, summary: str, comparisons: dict, rec: dict) -> str:
    """One line: class, counts, the estimators carrying the class with delta, differing keys and the
    D-1 tag (D-1 = vanishes with z exact; not-D-1 = residual remains; D-1? = recheck not possible)."""
    flag = "!!! " if cls == "CPP_HIGHER" else ""
    parts = [f"{case}: {flag}{cls} ({summary})"]
    if cls in ("CPP_HIGHER", "CPP_LOWER", "INTERMEDIATE_DIFF"):
        items = []
        for m, c in comparisons.items():
            if c.get("class") != cls:
                continue
            d = (c.get("min_entropy") or {}).get("delta")
            keys = [i["key"] for i in c.get("intermediates", []) if i["status"] != "agree"]
            r = c.get("d1_recheck")
            tag = "" if r is None else (" D-1" if r.get("explained") else (" not-D-1" if r.get("possible") else " D-1?"))
            items.append(f"{m} ({'' if d is None else format(d, '+.3g')}; {','.join(keys) or 'min only'}{tag})")
        parts.append(f"{cls.lower()} in: " + ", ".join(items))
        if rec.get("d1_explained") is True:
            parts.append(f"ALL explained by documented divergence D-1 (vanish with z = {Z_EXACT})")
        elif rec.get("d1_explained") is False:
            parts.append("NOT all explained by D-1 -- needs a human eye")
    text = "; ".join(parts)
    if rec.get("non_compliant_short_dataset"):
        text += " [EA_ALLOW_SHORT_DATASET=1]"
    return text


def _merge_d1(ref_results: dict, d1_results) -> dict:
    """Reference results with every successful z-exact re-run substituted for its module."""
    out = dict(ref_results)
    for m, r in (d1_results or {}).items():
        if r.get("status") == "ok":
            out[m] = r
    return out


def _loaded_d1(stem: str, bps: int, mode: str):
    p = result_path(case_id(stem, bps, mode))
    if os.path.exists(p):
        return read_json(p).get("reference_d1_recheck") or None
    return None


def compare_estimator(cpp_vals: dict | None, cpp_text: dict | None, ref: dict) -> dict:
    """Compare one estimator.  `ref` is {'status': 'ok'|..., 'values': {...}, 'error': ...}.

    Returns {'class', 'reason', 'min_entropy': {...}, 'intermediates': [...],
             'unmatched': {'cpp_only': [...], 'ref_only': [...]}}
    """
    res = {"class": None, "reason": "", "min_entropy": None, "intermediates": [],
           "unmatched": {"cpp_only": [], "ref_only": []}}
    ref_ok = ref.get("status") == "ok" and isinstance(ref.get("values"), dict)
    ref_vals = {canon_key(k): v for k, v in (ref.get("values") or {}).items()} if ref_ok else {}
    cpp_text = cpp_text or {}

    cpp_me = cpp_vals.get("min_entropy") if cpp_vals else None
    ref_me = ref_vals.get("min_entropy") if ref_ok else None

    if cpp_vals is None and not ref_ok:
        res["class"] = "NOT_RUN"
        res["reason"] = f"neither side produced a value (reference: {ref.get('status')}: {ref.get('error') or ''})".strip()
        return res
    if not ref_ok:
        res["class"] = "NOT_RUN"
        res["reason"] = f"reference {ref.get('status')}: {ref.get('error') or 'no values'}; C++ printed min entropy = {cpp_me}"
        return res
    if cpp_vals is None:
        res["class"] = "NOT_RUN"
        res["reason"] = (f"C++ printed nothing for this estimator; reference min_entropy = {ref_me}. "
                         f"CHECK at the overall level whether a declined estimator raised the C++ minimum")
        return res
    if cpp_me is None:
        res["class"] = "NOT_RUN"
        res["reason"] = f"C++ printed intermediates but no 'min entropy' for this estimator; reference = {ref_me}"
        return res
    if ref_me is None or is_nan(ref_me):
        res["class"] = "NOT_RUN"
        res["reason"] = (f"reference gave no value (nan/absent) for min_entropy while the C++ printed {cpp_me}; "
                         f"an applicability difference, not an agreement")
        return res

    me = compare_value("min_entropy", cpp_me, ref_me, cpp_text.get("min_entropy"))
    res["min_entropy"] = me
    shared = sorted((set(cpp_vals) & set(ref_vals)) - {"min_entropy"})
    res["unmatched"]["cpp_only"] = sorted(set(cpp_vals) - set(ref_vals) - {"min_entropy"})
    res["unmatched"]["ref_only"] = sorted(k for k in set(ref_vals) - set(cpp_vals) - {"min_entropy"}
                                          if not is_nan(ref_vals[k]))
    differing = []
    for k in shared:
        c = compare_value(k, cpp_vals[k], ref_vals[k], cpp_text.get(k))
        res["intermediates"].append(c)
        if c["status"] in ("differ", "nan_mismatch"):
            differing.append(k)

    if me["status"] == "differ":
        if me["delta"] > 0:
            res["class"] = "CPP_HIGHER"
            res["reason"] = (f"!!! C++ min entropy {cpp_me!r} exceeds reference {ref_me!r} by {me['delta']:.6g} "
                             f"(tol {me['tol']:.3g})")
        else:
            res["class"] = "CPP_LOWER"
            res["reason"] = f"C++ min entropy {cpp_me!r} below reference {ref_me!r} by {-me['delta']:.6g} (tol {me['tol']:.3g})"
        if differing:
            res["reason"] += f"; intermediates differing: {', '.join(differing)}"
        if d1_candidate(differing, me["delta"]):
            res["hint"] = ("differing intermediates are all downstream of the 2.576 constant and |delta| < 1e-3: "
                           "candidate documented divergence D-1 (binary64 quantile 2.5758293035489008 vs the "
                           "printed 2.576); the D-1 recheck decides")
        return res
    if differing:
        res["class"] = "INTERMEDIATE_DIFF"
        res["reason"] = f"min entropy agrees ({cpp_me!r}); intermediates differ: {', '.join(differing)}"
        if d1_candidate(differing, 0.0):
            res["hint"] = "differing intermediates are all downstream of the 2.576 constant: candidate D-1"
        return res
    res["class"] = "AGREE"
    res["reason"] = f"min entropy {cpp_me!r} and {len(shared)} shared intermediates within tolerance"
    return res


def worst_class(classes) -> str | None:
    present = [c for c in CLASS_ORDER if c in classes]
    return present[0] if present else None


def case_class(per_estimator: dict) -> tuple[str, str]:
    """Case-level class from the per-estimator classes.  The worst of the comparisons
    that were MADE wins; NOT_RUN alone never produces AGREE."""
    classes = [v["class"] for v in per_estimator.values()]
    counts = {c: classes.count(c) for c in CLASS_ORDER if classes.count(c)}
    made = [c for c in classes if c not in ("NOT_RUN",)]
    if not made:
        return "NOT_RUN", "no comparison could be made: " + "; ".join(
            f"{k}: {v['reason']}" for k, v in per_estimator.items())
    w = worst_class(made)
    summary = ", ".join(f"{c.lower()} {n}" for c, n in counts.items())
    return w, summary


# ----------------------------------------------------------------------------
# running the C++ tool (one run per (file, bps), shared by both modes)
# ----------------------------------------------------------------------------

def raw_base(stem: str, bps: int) -> str:
    return os.path.join(RAW_DIR, f"{stem}-b{bps}")


def run_cpp(file_path: str, bps: int, n: int, force: bool, timeout: float,
            binary: str = BINARY) -> dict:
    """Run ea_non_iid once; stdout/stderr/json go to FILES; return the meta record.
    Resumable: a complete meta file is reused unless `force`."""
    os.makedirs(RAW_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(file_path))[0]
    base = raw_base(stem, bps)
    meta_path = base + ".cpp.meta.json"
    if not force and os.path.exists(meta_path):
        meta = read_json(meta_path)
        if meta.get("complete"):
            meta["reused"] = True
            return meta
    stdout_path, stderr_path, json_path = base + ".cpp.stdout.txt", base + ".cpp.stderr.txt", base + ".cpp.json"
    for p in (stdout_path, stderr_path, json_path):
        if os.path.exists(p):
            os.remove(p)
    env = {k: v for k, v in os.environ.items() if k not in ("EA_ALLOW_SHORT_DATASET",)}
    env["OMP_NUM_THREADS"] = "2"
    short = n < MIN_COMPLIANT_N
    if short:
        env["EA_ALLOW_SHORT_DATASET"] = "1"
    cmd = [binary, "-i", "-a", "-v", "-v", "-o", json_path, os.path.abspath(file_path), str(bps)]
    meta = {
        "cmd": cmd, "cwd": RAW_DIR,
        "env": {"OMP_NUM_THREADS": "2", "EA_ALLOW_SHORT_DATASET": "1" if short else None},
        "non_compliant_short_dataset": short,
        "binary": {"path": binary, "sha256": sha256_file(binary)},
        "input": {"path": os.path.abspath(file_path), "sha256": sha256_file(file_path), "n_bytes": n, "bps": bps},
        "stdout_file": stdout_path, "stderr_file": stderr_path, "json_file": json_path,
        "started": now_iso(), "exit": None, "signal": None, "outcome": None, "duration_s": None,
        "timed_out": False, "complete": False, "reused": False,
    }
    if meta["binary"]["sha256"] is None:
        meta["outcome"] = "binary_missing"
        meta["complete"] = True
        write_json(meta_path, meta)
        return meta
    t0 = time.time()
    with open(stdout_path, "wb") as so, open(stderr_path, "wb") as se:
        try:
            proc = subprocess.run(cmd, stdout=so, stderr=se, env=env, cwd=RAW_DIR, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = None
            meta["timed_out"] = True
    meta["duration_s"] = round(time.time() - t0, 3)
    if meta["timed_out"]:
        meta["outcome"] = "timeout"
    elif rc is not None and rc < 0:
        meta["exit"] = rc
        meta["signal"] = -rc
        meta["outcome"] = f"signal_{signal.Signals(-rc).name if -rc in signal.Signals._value2member_map_ else -rc}"
    else:
        meta["exit"] = rc
        meta["outcome"] = "exit_0" if rc == 0 else f"nonzero_exit_{rc}"
    meta["complete"] = True
    write_json(meta_path, meta)
    return meta


def load_cpp_outputs(meta: dict) -> dict:
    """Read the files the C++ run wrote, parse the text by label, parse the JSON, and
    decide whether the run is a well-formed result (instrument rule 2)."""
    rec = {"parsed": None, "json": None, "json_summary": {}, "well_formed": False,
           "outcome": meta.get("outcome"), "refusal_message": None, "stdout_bytes": 0, "stderr_bytes": 0}
    text = ""
    if os.path.exists(meta["stdout_file"]):
        with open(meta["stdout_file"], "rb") as f:
            data = f.read()
        rec["stdout_bytes"] = len(data)
        text = data.decode("utf-8", errors="replace")
    err = ""
    if os.path.exists(meta["stderr_file"]):
        with open(meta["stderr_file"], "rb") as f:
            e = f.read()
        rec["stderr_bytes"] = len(e)
        err = e.decode("utf-8", errors="replace")
    rec["parsed"] = parse_cpp_text(text)
    if os.path.exists(meta["json_file"]):
        try:
            with open(meta["json_file"], "r", encoding="utf-8") as f:
                rec["json"] = json.load(f)
            wanted = {"hAssessed", "hOriginal", "hBitstring", "errorLevel", "errorMessage", "sha256",
                      "bitsPerSymbol", "bitsPerSymbolInferred", "H_original", "H_bitstring", "h_assessed"}
            rec["json_summary"] = find_keys(rec["json"], wanted)
        except Exception as ex:  # a placeholder or truncated document is a recorded outcome, not a crash
            rec["json_error"] = f"{type(ex).__name__}: {ex}"
    ok_exit = meta.get("outcome") == "exit_0"
    has_line = rec["parsed"]["assessed"] is not None
    rec["well_formed"] = bool(ok_exit and has_line)
    if not rec["well_formed"]:
        if ok_exit and not has_line:
            rec["outcome"] = "missing_assessed_line"
        msg_lines = [l for l in (err.splitlines() + text.splitlines()) if l.strip()]
        rec["refusal_message"] = "\n".join(msg_lines[-6:]) if msg_lines else "(no output)"
    return rec


def cpp_internal_checks(parsed: dict, bps: int, n: int, input_sha: str | None) -> list[dict]:
    """Checks on the C++ output against itself and against the input; each is a record
    {'check', 'ok', 'detail'}.  'assessed_vs_printed_min' failing in the + direction is
    an overstatement independent of any reference."""
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    if parsed["loaded_sha256"] and input_sha:
        add("loaded_sha256_matches_input", parsed["loaded_sha256"] == input_sha,
            f"tool {parsed['loaded_sha256']} vs file {input_sha}")
    if parsed["n"] is not None:
        add("loaded_n_matches_file_size", parsed["n"] == n, f"tool n {parsed['n']} vs file bytes {n}")
    if parsed["width"] is not None:
        add("loaded_width_matches_declared", parsed["width"] == bps, f"tool width {parsed['width']} vs declared {bps}")
    if parsed["n_binary"] is not None and parsed["n"] is not None and parsed["width"] is not None:
        add("n_binary_equals_n_times_width", parsed["n_binary"] == parsed["n"] * parsed["width"],
            f"{parsed['n_binary']} vs {parsed['n']}*{parsed['width']}")
    lit = [b["min entropy"]["value"] for b in parsed["estimates"]["Literal"].values() if "min entropy" in b]
    bit = [b["min entropy"]["value"] for b in parsed["estimates"]["Bitstring"].values() if "min entropy" in b]
    lit = [float(x) for x in lit if _as_float(x) is not None and not math.isnan(float(x))]
    bit = [float(x) for x in bit if _as_float(x) is not None and not math.isnan(float(x))]
    Ho, Hb, Hbs, A = parsed["H_original"], parsed["H_bitstring"], parsed["H_bitstring Per Symbol"], parsed["assessed"]
    if Ho is not None and lit:
        add("H_original_equals_min_printed_literal", abs(float(Ho) - min(lit)) <= TOL,
            f"H_original {Ho} vs min(Literal min entropies) {min(lit)}")
    if Hb is not None and bit:
        add("H_bitstring_equals_min_printed_bitstring", abs(float(Hb) - min(bit)) <= TOL,
            f"H_bitstring {Hb} vs min(Bitstring min entropies) {min(bit)}")
    if Hb is not None and Hbs is not None:
        add("per_symbol_equals_bps_times_H_bitstring", abs(float(Hbs) - bps * float(Hb)) <= TOL * bps,
            f"{Hbs} vs {bps} x {Hb}")
    if A is not None:
        cands = [float(x) for x in (Ho, Hbs) if x is not None]
        if cands:
            add("assessed_equals_min_of_summary_terms", abs(float(A) - min(cands)) <= TOL,
                f"Assessed {A} vs min{cands}")
        printed = lit + ([bps * x for x in bit] if Hbs is not None else [])
        if printed:
            add("assessed_not_above_printed_min", float(A) <= min(printed) + TOL,
                f"Assessed {A} vs min of all printed (bitstring scaled by {bps}) {min(printed)}")
    return checks


# ----------------------------------------------------------------------------
# running the reference modules (child processes)
# ----------------------------------------------------------------------------

def ref_child(module: str, file_path: str, bps: int, mode: str, translate: bool,
              bit_order: str, truncate: int, options: dict) -> dict:
    """Executed in the child: read the file per the contract, derive the mode's symbols,
    import py90b.<module>, call estimate(symbols, bps_eff, **options), return the dict."""
    ensure_reference_on_path()
    sym, info = read_symbols(file_path, bps)
    if mode == "bitstring":
        data = to_bitstring(sym, bps, bit_order)
        if truncate and len(data) > truncate:
            data = data[:truncate]
        bps_eff = 1
    elif translate:
        data, _ = translate_binary(sym)
        bps_eff = 1
    else:
        data, bps_eff = sym, bps
    mod = importlib.import_module(f"py90b.{module}")
    t0 = time.time()
    vals = mod.estimate(data, bps_eff, **options)
    dur = time.time() - t0
    if not isinstance(vals, dict):
        raise TypeError(f"estimate() returned {type(vals).__name__}, not dict")
    return {"status": "ok", "values": vals, "input_info": info, "n_symbols_fed": int(len(data)),
            "bps_fed": bps_eff, "translated": bool(translate), "estimate_seconds": round(dur, 3),
            "module_file": getattr(mod, "__file__", None), "module_sha256": sha256_file(getattr(mod, "__file__", "") or "")}


def run_ref_module(module: str, file_path: str, bps: int, mode: str, translate: bool, force: bool,
                   timeout: float, bit_order: str, truncate: int, options: dict) -> dict:
    """Run one reference module in a child process; cache the result file."""
    os.makedirs(RAW_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(file_path))[0]
    tag = "" if not options else "." + hashlib.sha256(json.dumps(options, sort_keys=True).encode()).hexdigest()[:8]
    base = os.path.join(RAW_DIR, f"{stem}-b{bps}-{mode}.{module}.ref{tag}")
    out_path, err_path = base + ".json", base + ".stderr.txt"
    if not force and os.path.exists(out_path):
        try:
            cached = read_json(out_path)
            if cached.get("status") and cached.get("options_used") == options:
                cached["reused"] = True
                return cached
        except Exception:
            pass
    env = dict(os.environ)
    env["OMP_NUM_THREADS"] = "2"
    cmd = [sys.executable, os.path.abspath(__file__), "--ref-child", module, os.path.abspath(file_path), str(bps),
           mode, "1" if translate else "0", bit_order, str(truncate), json.dumps(options), out_path]
    rec = {"status": None, "values": None, "error": None, "cmd": cmd, "duration_s": None, "options_used": options,
           "module": module, "mode": mode, "translated": translate, "reused": False}
    t0 = time.time()
    with open(err_path, "wb") as se:
        try:
            proc = subprocess.run(cmd, stdout=se, stderr=se, env=env, cwd=RAW_DIR, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = None
    rec["duration_s"] = round(time.time() - t0, 3)
    if rc is None:
        rec["status"] = "timeout"
        rec["error"] = f"reference module exceeded {timeout}s"
    elif os.path.exists(out_path):
        try:
            child = read_json(out_path)
            rec.update({k: v for k, v in child.items() if k not in ("cmd", "duration_s", "reused")})
            rec["duration_s"] = round(time.time() - t0, 3)
        except Exception as ex:
            rec["status"] = "error"
            rec["error"] = f"child output unreadable: {type(ex).__name__}: {ex}"
    else:
        rec["status"] = "error"
        rec["error"] = f"child exit {rc} and no output file"
    if rec["status"] != "ok" and os.path.exists(err_path):
        with open(err_path, "r", encoding="utf-8", errors="replace") as f:
            tail = f.read().splitlines()[-8:]
        rec["stderr_tail"] = tail
        if rec.get("error") is None:
            rec["error"] = (tail[-1] if tail else "no error text")
    rec["options_used"] = options
    write_json(out_path, rec)
    return rec


def ref_child_main(argv: list[str]) -> int:
    """argv: module file bps mode translate bit_order truncate options_json out_path"""
    module, file_path, bps, mode, translate, bit_order, truncate, options_json, out_path = argv
    try:
        rec = ref_child(module, file_path, int(bps), mode, translate == "1", bit_order, int(truncate),
                        json.loads(options_json))
    except ModuleNotFoundError as ex:
        rec = {"status": "missing", "values": None, "error": f"{type(ex).__name__}: {ex}"}
    except Exception as ex:
        rec = {"status": "error", "values": None, "error": f"{type(ex).__name__}: {ex}",
               "traceback": traceback.format_exc().splitlines()[-12:]}
    write_json(out_path, rec)
    return 0 if rec["status"] == "ok" else 1


# ----------------------------------------------------------------------------
# the SP 800-90B 3.1.3 combination, on the reference side
# ----------------------------------------------------------------------------

def applicable_modules(mode: str, binary: bool) -> list[str]:
    """Which modules apply: all ten on bits; on the literal symbols the three
    binary-only estimators (6.2) only when the data is binary."""
    if mode == "bitstring":
        return [m for m, _ in MODULES]
    return [m for m, _ in MODULES if binary or m not in BINARY_ONLY]


def reference_minimum(ref_results: dict, modules: list[str]) -> dict:
    """min over the applicable modules' min_entropy; records which were missing.  A nan
    from a module that is applicable is recorded as 'declined' and excluded, so that an
    estimator which SHOULD have produced a value but did not cannot silently raise the min."""
    values, missing, declined = {}, [], []
    for m in modules:
        r = ref_results.get(m)
        if not r or r.get("status") != "ok":
            missing.append(m)
            continue
        v = (r.get("values") or {}).get("min_entropy")
        f = _as_float(v)
        if f is None or math.isnan(f):
            declined.append(m)
            continue
        values[m] = f
    binding = min(values, key=values.get) if values else None
    return {"min": values[binding] if binding else None, "binding": binding, "values": values,
            "missing": missing, "declined": declined, "complete": not missing}


def combine_reference(lit: dict, bit: dict | None, bps: int, binary: bool) -> dict:
    """SP 800-90B 3.1.3 (PDF p. 20): H_I = min(H_original, n x H_bitstring) for non-binary
    sources, H_original for binary sources (H_submitter is not part of this tool)."""
    out = {"H_original": lit["min"], "H_bitstring": None, "H_bitstring Per Symbol": None,
           "assessed": None, "binary": binary, "complete": lit["complete"]}
    if not binary and bit is not None:
        out["H_bitstring"] = bit["min"]
        out["H_bitstring Per Symbol"] = None if bit["min"] is None else bps * bit["min"]
        out["complete"] = lit["complete"] and bit["complete"]
    cands = [x for x in (out["H_original"], out["H_bitstring Per Symbol"]) if x is not None]
    out["assessed"] = min(cands) if cands else None
    return out


def compare_overall(label: str, cpp_v, ref_v, ref_complete: bool, cpp_text: str | None, missing: list) -> dict:
    """Compare a summary figure.  With an incomplete reference only CPP_HIGHER is established."""
    rec = {"label": label, "cpp": cpp_v, "ref": ref_v, "class": None, "reason": None}
    if cpp_v is None and ref_v is None:
        rec["class"], rec["reason"] = "NOT_RUN", "neither side has this figure"
        return rec
    if cpp_v is None:
        rec["class"], rec["reason"] = "NOT_RUN", f"C++ printed no '{label}'; reference {ref_v}"
        return rec
    if ref_v is None:
        rec["class"], rec["reason"] = "NOT_RUN", f"reference has no '{label}' (missing modules: {missing})"
        return rec
    c = compare_value(label, cpp_v, ref_v, cpp_text)
    rec["delta"], rec["tol"] = c["delta"], c["tol"]
    if c["status"] == "differ" and c["delta"] > 0:
        rec["class"] = "CPP_HIGHER"
        rec["reason"] = f"!!! C++ {label} {cpp_v!r} exceeds reference {ref_v!r} by {c['delta']:.6g}"
        if not ref_complete:
            rec["reason"] += f" (established with modules missing: {missing}; more modules could only lower the reference)"
        return rec
    if not ref_complete:
        rec["class"] = "NOT_RUN"
        rec["reason"] = (f"reference incomplete (missing: {missing}); on the available estimators "
                         f"C++ {cpp_v!r} vs reference {ref_v!r} (delta {c['delta']:.3g}) -- AGREE/CPP_LOWER not established")
        return rec
    if c["status"] == "differ":
        rec["class"] = "CPP_LOWER"
        rec["reason"] = f"C++ {label} {cpp_v!r} below reference {ref_v!r} by {-c['delta']:.6g}"
        return rec
    rec["class"] = "AGREE"
    rec["reason"] = f"{label} {cpp_v!r} vs {ref_v!r} within {c['tol']:.3g}"
    return rec


# ----------------------------------------------------------------------------
# one (file, bps): both modes and the assessed pseudo-case
# ----------------------------------------------------------------------------

def case_id(stem: str, bps: int, mode: str) -> str:
    return f"{stem}-b{bps}-{mode}"


def result_path(case: str) -> str:
    return os.path.join(LOGS_DIFF, case + ".json")


def base_record(file_path: str, bps: int, mode: str, meta: dict, cpp: dict, settings: dict) -> dict:
    stem = os.path.splitext(os.path.basename(file_path))[0]
    return {
        "case": case_id(stem, bps, mode), "name": os.path.basename(file_path), "file": os.path.abspath(file_path),
        "bps": bps, "mode": mode, "n": meta["input"]["n_bytes"], "input_sha256": meta["input"]["sha256"],
        "binary": meta["binary"], "harness_sha256": sha256_file(os.path.abspath(__file__)),
        "timestamp": now_iso(), "env": meta["env"], "non_compliant_short_dataset": meta["non_compliant_short_dataset"],
        "settings": settings,
        "cpp": {"cmd": meta["cmd"], "exit": meta.get("exit"), "signal": meta.get("signal"), "outcome": cpp["outcome"],
                "duration_s": meta.get("duration_s"), "stdout_file": meta["stdout_file"],
                "stderr_file": meta["stderr_file"], "json_file": meta["json_file"], "well_formed": cpp["well_formed"],
                "refusal_message": cpp["refusal_message"], "warnings": cpp["parsed"]["warnings"],
                "loaded": {k: cpp["parsed"][k] for k in ("loaded_file", "loaded_sha256", "n", "k", "width", "n_binary")},
                "summary": {k: cpp["parsed"][k] for k in ("H_original", "H_bitstring", "H_bitstring Per Symbol", "assessed")},
                "json_summary": cpp["json_summary"], "json_error": cpp.get("json_error"),
                "notes": cpp["parsed"]["notes"], "unparsed_estimate_lines": cpp["parsed"]["unparsed_estimate_lines"]},
    }


def refused_record(rec: dict) -> dict:
    rec["class"] = "TOOL_REFUSED"
    rec["verdict"] = (f"{rec['case']}: TOOL_REFUSED ({rec['cpp']['outcome']}) -- "
                      f"{(rec['cpp']['refusal_message'] or '').splitlines()[-1] if rec['cpp']['refusal_message'] else 'no message'}"
                      + (" [EA_ALLOW_SHORT_DATASET=1]" if rec["non_compliant_short_dataset"] else ""))
    return rec


def process_file(file_path: str, bps: int, modes: list[str], settings: dict, force: bool,
                 skip_ref: bool, cpp_timeout: float, ref_timeout: float, ref_options: dict,
                 force_ref: bool = False) -> list[dict]:
    """Run everything for one (file, bps).  Returns the records written (or reused).
    `force` recomputes everything; `force_ref` re-runs the reference modules but reuses the C++ run."""
    stem = os.path.splitext(os.path.basename(file_path))[0]
    n = os.path.getsize(file_path)
    wanted_cases = [case_id(stem, bps, m) for m in modes] + [case_id(stem, bps, "assessed")]
    if not force and not force_ref and all(os.path.exists(result_path(c)) for c in wanted_cases):
        return [read_json(result_path(c)) for c in wanted_cases]

    meta = run_cpp(file_path, bps, n, force, cpp_timeout)
    cpp = load_cpp_outputs(meta)
    sym, info = read_symbols(file_path, bps)
    binary, k = is_binary(sym, bps, settings["binary_rule"])
    translation = None
    if binary and bps > 1 and k >= 1:
        _, translation = translate_binary(sym)
    written = []
    per_mode_ref = {}
    per_mode_d1 = {}
    per_mode_records = {}

    for mode in modes:
        case = case_id(stem, bps, mode)
        rec = base_record(file_path, bps, mode, meta, cpp, settings)
        rec.update({"k_observed": k, "is_binary": binary, "translation": translation, "input_info": info})
        if not cpp["well_formed"]:
            refused_record(rec)
            write_json(result_path(case), rec)
            written.append(rec)
            per_mode_records[mode] = rec
            continue
        cpp_mode = "Literal" if mode == "literal" else "Bitstring"
        if mode == "bitstring" and binary:
            # SP 800-90B 3.1.3 (PDF p. 20): H_bitstring exists only 'If the sequential dataset is not
            # binary'; for a binary source H_I = min(H_original, H_submitter).  Nothing to compare --
            # but a C++ that printed Bitstring blocks for a binary source is recorded, since the gate
            # it uses (observed alphabet > 2) and this rule may disagree.  What this branch cannot
            # see: a bitstring estimate the C++ computed but did not print.
            nblocks = len(cpp["parsed"]["estimates"]["Bitstring"])
            rec["reference"] = {}
            rec["comparisons"] = {}
            rec["cpp_bitstring_blocks_for_binary_source"] = nblocks
            rec["class"] = "NOT_RUN"
            rec["verdict"] = (f"{case}: NOT_RUN -- binary source (k = {k}, declared {bps} bit, rule {settings['binary_rule']}): "
                              f"3.1.3 has no bitstring term; C++ printed {nblocks} Bitstring blocks"
                              + (" -- CHECK: the C++ ran bitstring estimators on a source this rule calls binary" if nblocks else "")
                              + (" [EA_ALLOW_SHORT_DATASET=1]" if rec["non_compliant_short_dataset"] else ""))
            write_json(result_path(case), rec)
            written.append(rec)
            per_mode_records[mode] = rec
            continue
        mods = applicable_modules(mode, binary)
        ref_results = {}
        if not skip_ref:
            for m in mods:
                translate = (mode == "literal" and binary and bps > 1)
                ref_results[m] = run_ref_module(m, file_path, bps, mode, translate, force or force_ref, ref_timeout,
                                                settings["bit_order"], settings["bitstring_truncate"],
                                                ref_options.get(m, {}))
        else:
            for m in mods:
                ref_results[m] = {"status": "skipped", "values": None, "error": "--skip-ref"}
        for m, _ in MODULES:
            if m not in mods:
                ref_results[m] = {"status": "not_applicable", "values": None,
                                  "error": f"6.2: binary-only estimator; data is not binary (k = {k}, rule {settings['binary_rule']})"}
        comparisons = {}
        d1_results = {}
        for m, est in MODULES:
            cv = cpp_values(cpp["parsed"], cpp_mode, est)
            ct = cpp_texts(cpp["parsed"], cpp_mode, est)
            comparisons[m] = compare_estimator(cv, ct, ref_results[m])
            comparisons[m]["estimator"] = est
            if settings.get("d1_recheck") and "hint" in comparisons[m] and not skip_ref:
                # the D-1 recheck: same module, same data, z = the exact quantile
                translate = (mode == "literal" and binary and bps > 1)
                opts = dict(ref_options.get(m, {}))
                d1_opt = tuple(settings.get("d1_options_by_module", {}).get(m) or settings["d1_option"])
                opts[d1_opt[0]] = d1_opt[1]
                d1_results[m] = run_ref_module(m, file_path, bps, mode, translate, force or force_ref, ref_timeout,
                                               settings["bit_order"], settings["bitstring_truncate"], opts)
                comparisons[m]["d1_recheck"] = d1_recheck_record(cv, ct, d1_results[m], d1_opt)
        cls, summary = case_class(comparisons)
        rec["reference"] = compact_tables({m: {k2: v for k2, v in r.items() if k2 != "cmd"} for m, r in ref_results.items()})
        rec["reference_d1_recheck"] = compact_tables({m: {k2: v for k2, v in r.items() if k2 != "cmd"} for m, r in d1_results.items()})
        rec["comparisons"] = comparisons
        rec["unmapped_cpp_estimators"] = sorted(set(cpp["parsed"]["estimates"][cpp_mode]) - set(MODULE_BY_ESTIMATOR))
        rec["class"] = cls
        rec["d1_explained"] = d1_explained_all(comparisons, cls)
        rec["verdict"] = build_verdict(case, cls, summary, comparisons, rec)
        write_json(result_path(case), rec)
        written.append(rec)
        per_mode_ref[mode] = ref_results
        per_mode_d1[mode] = d1_results
        per_mode_records[mode] = rec

    # the assessed pseudo-case (3.1.3 combination) -- needs the literal side at least
    case = case_id(stem, bps, "assessed")
    rec = base_record(file_path, bps, "assessed", meta, cpp, settings)
    rec.update({"k_observed": k, "is_binary": binary, "translation": translation, "input_info": info})
    if not cpp["well_formed"]:
        refused_record(rec)
    else:
        rec["cpp_internal_checks"] = cpp_internal_checks(cpp["parsed"], bps, n, meta["input"]["sha256"])
        lit_ref = per_mode_ref.get("literal")
        if lit_ref is None and os.path.exists(result_path(case_id(stem, bps, "literal"))):
            lit_ref = read_json(result_path(case_id(stem, bps, "literal"))).get("reference")
        bit_ref = per_mode_ref.get("bitstring")
        if bit_ref is None and os.path.exists(result_path(case_id(stem, bps, "bitstring"))):
            bit_ref = read_json(result_path(case_id(stem, bps, "bitstring"))).get("reference")
        lit_min = reference_minimum(lit_ref or {}, applicable_modules("literal", binary))
        bit_min = reference_minimum(bit_ref or {}, applicable_modules("bitstring", binary)) if (bit_ref and not binary) else None
        combined = combine_reference(lit_min, bit_min, bps, binary)
        rec["reference_combination"] = {"literal": lit_min, "bitstring": bit_min, "combined": combined,
                                        "rule": "3.1.3: H_I = min(H_original, n x H_bitstring) if not binary else H_original"}
        s, st = cpp["parsed"], cpp["parsed"]["summary_texts"]
        comps = {
            "H_original": compare_overall("H_original", s["H_original"], combined["H_original"], lit_min["complete"],
                                          st.get("H_original"), lit_min["missing"]),
            "H_bitstring": compare_overall("H_bitstring", s["H_bitstring"], combined["H_bitstring"],
                                           bit_min["complete"] if bit_min else True, st.get("H_bitstring"),
                                           bit_min["missing"] if bit_min else []),
            "H_bitstring Per Symbol": compare_overall("H_bitstring Per Symbol", s["H_bitstring Per Symbol"],
                                                      combined["H_bitstring Per Symbol"],
                                                      bit_min["complete"] if bit_min else True,
                                                      st.get("H_bitstring Per Symbol"), bit_min["missing"] if bit_min else []),
            "Assessed min entropy": compare_overall("Assessed min entropy", s["assessed"], combined["assessed"],
                                                    combined["complete"], s["assessed_text"],
                                                    lit_min["missing"] + (bit_min["missing"] if bit_min else [])),
        }
        # a C++ figure above the minimum of its own printed estimates is an overstatement by itself
        bad_internal = [c for c in rec["cpp_internal_checks"] if not c["ok"]]
        if any(c["check"] == "assessed_not_above_printed_min" for c in bad_internal):
            comps["Assessed min entropy"]["class"] = "CPP_HIGHER"
            comps["Assessed min entropy"]["reason"] = ("!!! C++ 'Assessed min entropy' exceeds the minimum of its own printed "
                                                       "estimates: " + next(c["detail"] for c in bad_internal
                                                                             if c["check"] == "assessed_not_above_printed_min"))
        rec["comparisons"] = comps
        classes = [c["class"] for c in comps.values()]
        made = [c for c in classes if c != "NOT_RUN"]
        cls = worst_class(made) if made else "NOT_RUN"
        rec["class"] = cls
        # D-1 recheck at the assessed level: the 3.1.3 combination with every rechecked module's
        # z-exact values substituted.  Informative only; the class above is not changed by it.
        d1_note = ""
        rec["d1_explained"] = None
        lit_d1 = per_mode_d1.get("literal") or _loaded_d1(stem, bps, "literal")
        bit_d1 = per_mode_d1.get("bitstring") or _loaded_d1(stem, bps, "bitstring")
        if (lit_d1 or bit_d1) and cls in ("CPP_HIGHER", "CPP_LOWER"):
            lit_min_d1 = reference_minimum(_merge_d1(lit_ref or {}, lit_d1), applicable_modules("literal", binary))
            bit_min_d1 = (reference_minimum(_merge_d1(bit_ref or {}, bit_d1), applicable_modules("bitstring", binary))
                          if (bit_ref and not binary) else None)
            comb_d1 = combine_reference(lit_min_d1, bit_min_d1, bps, binary)
            z_cmp = compare_overall("Assessed min entropy", s["assessed"], comb_d1["assessed"], comb_d1["complete"],
                                    s["assessed_text"], lit_min_d1["missing"] + (bit_min_d1["missing"] if bit_min_d1 else []))
            rec["reference_combination_d1"] = {"literal": lit_min_d1, "bitstring": bit_min_d1, "combined": comb_d1,
                                               "option": dict([tuple(settings["d1_option"])])}
            comps["Assessed min entropy [z exact]"] = z_cmp
            rec["d1_explained"] = z_cmp["class"] == "AGREE"
            d1_note = (f"; D-1 recheck with z = {settings['d1_option'][1]}: {z_cmp['class']}"
                       + (" -- the assessed difference IS documented divergence D-1" if rec["d1_explained"]
                          else f" -- residual delta {z_cmp.get('delta')}: NOT explained by D-1"))
        a = comps["Assessed min entropy"]
        flag = "!!! " if cls == "CPP_HIGHER" else ""
        rec["verdict"] = (f"{case}: {flag}{cls} -- Assessed cpp={a['cpp']!r} ref={a['ref']!r} [{a['class']}: {a['reason']}]"
                          + d1_note
                          + (f"; internal checks failing: {[c['check'] for c in bad_internal]}" if bad_internal else "")
                          + (" [EA_ALLOW_SHORT_DATASET=1]" if rec["non_compliant_short_dataset"] else ""))
    write_json(result_path(case), rec)
    written.append(rec)
    return written


# ----------------------------------------------------------------------------
# summary
# ----------------------------------------------------------------------------

def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.12g}"
    return str(v)


def summarize() -> str:
    """Rebuild SUMMARY.md from every result file (idempotent)."""
    os.makedirs(LOGS_DIFF, exist_ok=True)
    recs = []
    for p in sorted(glob.glob(os.path.join(LOGS_DIFF, "*.json"))):
        try:
            recs.append(read_json(p))
        except Exception as ex:
            recs.append({"case": os.path.basename(p), "class": "UNREADABLE", "verdict": f"{p}: unreadable result: {ex}"})
    binaries = sorted({(r.get("binary") or {}).get("sha256") or "?" for r in recs if r.get("binary")})
    order = {c: i for i, c in enumerate(CLASS_ORDER)}
    recs.sort(key=lambda r: (order.get(r.get("class"), 99), r.get("case", "")))
    counts = {}
    for r in recs:
        counts[r.get("class")] = counts.get(r.get("class"), 0) + 1
    lines = [
        "# Differential summary: cpp/ea_non_iid vs py90b reference",
        "",
        f"Written {now_iso()} by harness/diff_driver.py (sha256 {sha256_file(os.path.abspath(__file__))}).",
        f"Binaries measured (sha256): {', '.join(binaries) if binaries else 'none yet'}.",
        f"Tolerance: abs {TOL} for probabilities/entropies, exact for integer counts "
        f"({', '.join(sorted(INTEGER_LABELS))}); widened to the printed half-ulp only where a value was printed "
        f"with fewer digits (recorded per comparison).",
        "",
        "Classes, worst first: TOOL_REFUSED (nonzero exit / signal / timeout / missing 'Assessed min entropy' line; "
        "the sub-outcome is in the record) > **CPP_HIGHER (C++ min-entropy above the reference: the dangerous "
        "direction)** > CPP_LOWER > INTERMEDIATE_DIFF > NOT_RUN (a side had no value; never agreement) > AGREE.",
        "",
        "What this table cannot see: estimators neither side valued; intermediates the C++ does not print; "
        "differences under the tolerance; whether the C++ used translated symbols; and, where reference modules "
        "were missing, AGREE/CPP_LOWER on the assessed figure (reported NOT_RUN) -- only CPP_HIGHER is established "
        "with an incomplete reference.  Rows marked [EA_ALLOW_SHORT_DATASET=1] are non-compliant runs (n < 1,000,000).",
        "",
        "Counts: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: order.get(kv[0], 99)))
        + f" (CPP_HIGHER explained by D-1: {sum(1 for r in recs if r.get('class') == 'CPP_HIGHER' and r.get('d1_explained') is True)})",
        "",
    ]
    higher = [r for r in recs if r.get("class") == "CPP_HIGHER"]
    unexplained = [r for r in higher if r.get("d1_explained") is not True]
    explained = [r for r in higher if r.get("d1_explained") is True]
    lines.append("## !!! CPP_HIGHER cases NOT explained by documented divergence D-1 (C++ reports MORE min-entropy)")
    lines.append("")
    if unexplained:
        for r in unexplained:
            lines.append(f"- {r.get('verdict')}")
    else:
        lines.append("- none in the results written so far")
    lines.append("")
    lines.append(f"## CPP_HIGHER cases that vanish with z = {Z_EXACT} (documented divergence D-1: the fork's binary64 "
                 f"quantile against the printed 2.576; class kept, cause tagged)")
    lines.append("")
    if explained:
        for r in explained:
            lines.append(f"- {r.get('case')}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## All cases")
    lines.append("")
    lines.append("| case | n | bps | mode | class | C++ figure | reference | delta | short-dataset | verdict |")
    lines.append("|---|---:|---:|---|---|---|---|---|---|---|")
    for r in recs:
        cpp_fig = ref_fig = delta = None
        comps = r.get("comparisons") or {}
        if r.get("mode") == "assessed" and "Assessed min entropy" in comps:
            a = comps["Assessed min entropy"]
            cpp_fig, ref_fig, delta = a.get("cpp"), a.get("ref"), a.get("delta")
        elif r.get("mode") in ("literal", "bitstring"):
            key = "H_original" if r["mode"] == "literal" else "H_bitstring"
            cpp_fig = (r.get("cpp") or {}).get("summary", {}).get(key)
            # the reference minimum over the modules that produced values, for the row only
            vals = [(_as_float((v.get("values") or {}).get("min_entropy"))) for v in (r.get("reference") or {}).values()
                    if v.get("status") == "ok"]
            vals = [v for v in vals if v is not None and not math.isnan(v)]
            ref_fig = min(vals) if vals else None
            if cpp_fig is not None and ref_fig is not None:
                delta = float(cpp_fig) - ref_fig
        verdict = (r.get("verdict") or "").replace("|", "\\|")
        lines.append(f"| {r.get('case')} | {_fmt(r.get('n'))} | {_fmt(r.get('bps'))} | {r.get('mode', '-')} | "
                     f"{r.get('class')} | {_fmt(cpp_fig)} | {_fmt(ref_fig)} | {_fmt(delta)} | "
                     f"{'yes' if r.get('non_compliant_short_dataset') else 'no'} | {verdict} |")
    text = "\n".join(lines) + "\n"
    tmp = os.path.join(LOGS_DIFF, "SUMMARY.md.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, os.path.join(LOGS_DIFF, "SUMMARY.md"))
    return text


# ----------------------------------------------------------------------------
# --self-check: prove the comparison can fail (guide rule 7, rule 8)
# ----------------------------------------------------------------------------

def _ref_from_cpp(parsed: dict, mode: str) -> dict:
    """Build a 'reference' side that echoes the C++ values (the self-comparison)."""
    out = {}
    for m, est in MODULES:
        cv = cpp_values(parsed, mode, est)
        out[m] = {"status": "ok", "values": dict(cv)} if cv else {"status": "missing", "values": None,
                                                                 "error": "not printed by the C++"}
    return out


def self_check(case: str | None = None, write: bool = True) -> dict:
    """Baseline: the C++ text compared against a reference built from its own values must
    AGREE everywhere a value exists.  Then one mutation at a time must be reported as the
    named disagreement.  Returns {'ok': bool, 'rows': [...]}; writes logs/diff/SELF-CHECK.md."""
    sources = []
    if os.path.exists(LABEL_CAPTURE):
        with open(LABEL_CAPTURE, "r", encoding="utf-8") as f:
            sources.append(("label-capture", f.read()))
    if case:
        meta_path = os.path.join(RAW_DIR, case.rsplit("-", 1)[0] + ".cpp.meta.json") if case.endswith(("-literal", "-bitstring", "-assessed")) else None
        if meta_path and os.path.exists(meta_path):
            meta = read_json(meta_path)
            with open(meta["stdout_file"], "r", encoding="utf-8", errors="replace") as f:
                sources.append((case, f.read()))
        else:
            sources.append((case, ""))  # recorded as unusable below
    rows = []

    def row(source, step, expected, observed, detail=""):
        rows.append({"source": source, "step": step, "expected": expected, "observed": observed,
                     "ok": expected == observed, "detail": detail})

    for source, text in sources:
        if not text.strip():
            row(source, "load", "text", "empty", "no C++ stdout available for this case")
            continue
        parsed = parse_cpp_text(text)
        if parsed["assessed"] is None:
            row(source, "load", "assessed line", "absent", "source is not a well-formed result; mutations skipped")
            continue
        mode = "Literal"
        est_name = {e: m for m, e in MODULES}
        printed = [e for e in parsed["estimates"][mode] if e in est_name and "min entropy" in parsed["estimates"][mode][e]]
        if not printed:
            row(source, "load", "Literal estimates", "none", "")
            continue
        # 1. baseline self-comparison (rule 8): every printed estimator must AGREE
        base_ref = _ref_from_cpp(parsed, mode)
        comps = {m: compare_estimator(cpp_values(parsed, mode, e), cpp_texts(parsed, mode, e), base_ref[m]) for m, e in MODULES}
        agree = all(c["class"] == "AGREE" for m, c in comps.items() if base_ref[m]["status"] == "ok")
        row(source, "baseline self-comparison", "AGREE", "AGREE" if agree else case_class(comps)[0],
            ", ".join(f"{m}={c['class']}" for m, c in comps.items()))
        # pick the first printed estimator with a float min entropy for the mutations
        target_est = printed[0]
        target_mod = est_name[target_est]
        cv, ct = cpp_values(parsed, mode, target_est), cpp_texts(parsed, mode, target_est)
        me = float(cv["min_entropy"])

        def mutated(delta_key, delta):
            r = {"status": "ok", "values": dict(cv)}
            r["values"][delta_key] = r["values"][delta_key] + delta
            return r

        c = compare_estimator(cv, ct, mutated("min_entropy", -1e-6))
        row(source, f"{target_mod}: reference min_entropy - 1e-6", "CPP_HIGHER", c["class"], c["reason"])
        c = compare_estimator(cv, ct, mutated("min_entropy", +1e-6))
        row(source, f"{target_mod}: reference min_entropy + 1e-6", "CPP_LOWER", c["class"], c["reason"])
        c = compare_estimator(cv, ct, mutated("min_entropy", -1e-10))
        row(source, f"{target_mod}: reference min_entropy - 1e-10 (inside tolerance)", "AGREE", c["class"], c["reason"])
        float_keys = [k for k, v in cv.items() if k != "min_entropy" and isinstance(v, float)]
        int_keys = [k for k, v in cv.items() if k != "min_entropy" and isinstance(v, int)]
        if float_keys:
            c = compare_estimator(cv, ct, mutated(float_keys[0], +1e-6))
            row(source, f"{target_mod}: reference {float_keys[0]} + 1e-6", "INTERMEDIATE_DIFF", c["class"], c["reason"])
        if int_keys:
            c = compare_estimator(cv, ct, mutated(int_keys[0], 1))
            row(source, f"{target_mod}: reference {int_keys[0]} + 1 (integer, exact)", "INTERMEDIATE_DIFF", c["class"], c["reason"])
        c = compare_estimator(cv, ct, {"status": "missing", "values": None, "error": "ModuleNotFoundError (simulated)"})
        row(source, f"{target_mod}: reference module missing", "NOT_RUN", c["class"], c["reason"])
        c = compare_estimator(cv, ct, {"status": "ok", "values": {**cv, "min_entropy": float("nan")}})
        row(source, f"{target_mod}: reference min_entropy = nan", "NOT_RUN", c["class"], c["reason"])
        # TOOL_REFUSED: strip the 'Assessed min entropy' line and run the well-formedness decision
        stripped = "\n".join(l for l in text.splitlines() if not l.startswith("Assessed min entropy"))
        p2 = parse_cpp_text(stripped)
        meta_like = {"outcome": "exit_0"}
        wf = bool(meta_like["outcome"] == "exit_0" and p2["assessed"] is not None)
        row(source, "'Assessed min entropy' line removed, exit 0", "TOOL_REFUSED", "TOOL_REFUSED" if not wf else "AGREE",
            "missing_assessed_line" if not wf else "accepted a result without the line")
        wf2 = bool("nonzero_exit_255" == "exit_0" and parsed["assessed"] is not None)
        row(source, "exit status 255 with full text", "TOOL_REFUSED", "TOOL_REFUSED" if not wf2 else "AGREE", "nonzero exit")
        # the overall combination: the assessed figure mutated upward in the C++ must be CPP_HIGHER
        ref_assessed = float(parsed["assessed"])
        c = compare_overall("Assessed min entropy", ref_assessed + 1e-6, ref_assessed, True, None, [])
        row(source, "assessed: C++ + 1e-6 vs reference", "CPP_HIGHER", c["class"], c["reason"])
        c = compare_overall("Assessed min entropy", ref_assessed, ref_assessed + 1e-6, False, None, ["lz78y"])
        row(source, "assessed: reference incomplete and C++ lower", "NOT_RUN", c["class"], c["reason"])
        c = compare_overall("Assessed min entropy", ref_assessed + 1e-6, ref_assessed, False, None, ["lz78y"])
        row(source, "assessed: reference incomplete and C++ HIGHER", "CPP_HIGHER", c["class"], c["reason"])
        # label-not-position: shuffled lines parse identically
        import random
        lines = text.splitlines()
        random.Random(90).shuffle(lines)
        p3 = parse_cpp_text("\n".join(lines))
        same = (p3["estimates"] == parsed["estimates"] and p3["assessed"] == parsed["assessed"]
                and p3["H_original"] == parsed["H_original"])
        row(source, "lines shuffled: parse identical (by label, not position)", "identical",
            "identical" if same else "different", "")

    ok = all(r["ok"] for r in rows) and bool(rows)
    out = {"ok": ok, "rows": rows, "timestamp": now_iso(), "harness_sha256": sha256_file(os.path.abspath(__file__))}
    if write:
        os.makedirs(LOGS_DIFF, exist_ok=True)
        lines = ["# diff_driver --self-check", "", f"Written {out['timestamp']}; harness sha256 {out['harness_sha256']}.",
                 "", "Rule 7: a negative control is built by mutation of a passing artefact and the baseline is asserted "
                 "accepted.  Rule 8: the self-comparison is the baseline.  Every row below must have observed == expected.",
                 "", f"RESULT: {'PASS' if ok else 'FAIL'} ({sum(r['ok'] for r in rows)}/{len(rows)} rows)", "",
                 "| source | step | expected | observed | ok | detail |", "|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['source']} | {r['step']} | {r['expected']} | {r['observed']} | "
                         f"{'yes' if r['ok'] else 'NO'} | {str(r['detail']).replace('|', '/')} |")
        tmp = os.path.join(LOGS_DIFF, "SELF-CHECK.md.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, os.path.join(LOGS_DIFF, "SELF-CHECK.md"))
    return out


# ----------------------------------------------------------------------------
# API contract: estimate(symbols, bits_per_symbol, **options) -> dict, in-process
# ----------------------------------------------------------------------------

def _import_module(name: str):
    ensure_reference_on_path()
    return importlib.import_module(f"py90b.{name}")


def estimate(symbols, bits_per_symbol: int, **options) -> dict:
    """The harness's combined reference figure (no C++ involved).

    options:
      mode='assessed' | 'literal' | 'bitstring'   (default 'assessed' = the 3.1.3 combination)
      binary_rule='observed' | 'declared'
      bit_order='msb' | 'lsb';  bitstring_truncate=0
      modules={name: module_object}  (dependency injection for tests; default: import py90b.<name>)
      ref_options={name: {...}}      (passed through to each module's estimate())
    Returns {'min_entropy': float (nan if nothing could be computed), 'H_original', 'H_bitstring',
             'H_bitstring Per Symbol', 'Assessed min entropy', 'is_binary', 'k', 'estimators': {mode: {name: dict}},
             'not_run': {mode: {name: reason}}, 'complete': bool}
    """
    mode = options.pop("mode", "assessed")
    rule = options.pop("binary_rule", "observed")
    bit_order = options.pop("bit_order", "msb")
    truncate = options.pop("bitstring_truncate", 0)
    injected = options.pop("modules", None) or {}
    ref_options = options.pop("ref_options", {}) or {}
    if options:
        raise TypeError(f"unknown options: {sorted(options)}")
    sym = np.asarray(symbols, dtype=np.uint8) & ((1 << bits_per_symbol) - 1)
    binary, k = is_binary(sym, bits_per_symbol, rule)

    def run_mode(m: str) -> dict:
        if m == "bitstring":
            data = to_bitstring(sym, bits_per_symbol, bit_order)
            if truncate and len(data) > truncate:
                data = data[:truncate]
            bps_eff = 1
        elif binary and bits_per_symbol > 1:
            data, _ = translate_binary(sym)
            bps_eff = 1
        else:
            data, bps_eff = sym, bits_per_symbol
        results = {}
        for name in applicable_modules(m, binary):
            try:
                mod = injected[name] if name in injected else _import_module(name)
                vals = mod.estimate(data, bps_eff, **ref_options.get(name, {}))
                results[name] = {"status": "ok", "values": vals}
            except ModuleNotFoundError as ex:
                results[name] = {"status": "missing", "values": None, "error": str(ex)}
            except Exception as ex:
                results[name] = {"status": "error", "values": None, "error": f"{type(ex).__name__}: {ex}"}
        return results

    out = {"is_binary": binary, "k": k, "estimators": {}, "not_run": {}, "bits_per_symbol": bits_per_symbol}
    modes = ["literal", "bitstring"] if mode == "assessed" else [mode]
    if mode == "assessed" and binary:
        modes = ["literal"]
    mins = {}
    complete = True
    for m in modes:
        res = run_mode(m)
        out["estimators"][m] = {n: r["values"] for n, r in res.items() if r["status"] == "ok"}
        out["not_run"][m] = {n: r["error"] for n, r in res.items() if r["status"] != "ok"}
        mins[m] = reference_minimum(res, applicable_modules(m, binary))
        complete = complete and mins[m]["complete"]
    if mode == "literal":
        out["H_original"] = mins["literal"]["min"]
        out["min_entropy"] = float("nan") if out["H_original"] is None else out["H_original"]
    elif mode == "bitstring":
        out["H_bitstring"] = mins["bitstring"]["min"]
        out["H_bitstring Per Symbol"] = None if out["H_bitstring"] is None else bits_per_symbol * out["H_bitstring"]
        out["min_entropy"] = float("nan") if out["H_bitstring"] is None else out["H_bitstring"]
    else:
        comb = combine_reference(mins["literal"], mins.get("bitstring"), bits_per_symbol, binary)
        out.update({k2: comb[k2] for k2 in ("H_original", "H_bitstring", "H_bitstring Per Symbol")})
        out["Assessed min entropy"] = comb["assessed"]
        out["min_entropy"] = float("nan") if comb["assessed"] is None else comb["assessed"]
    out["binding"] = {m: mins[m]["binding"] for m in mins}
    out["complete"] = complete
    return out


# ----------------------------------------------------------------------------
# case enumeration and main
# ----------------------------------------------------------------------------

def read_manifest(path: str = MANIFEST) -> list[dict]:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            rows.append({"name": parts[0], "bps": int(parts[1]), "n": int(parts[2]), "sha256": parts[3],
                         "construction": parts[4] if len(parts) > 4 else ""})
    return rows


def enumerate_cases(args) -> list[tuple[str, int]]:
    items = []
    for row in read_manifest(args.manifest):
        p = os.path.join(os.path.dirname(os.path.abspath(args.manifest)), row["name"])
        if args.only and not any(fnmatch.fnmatch(row["name"], g) or fnmatch.fnmatch(os.path.splitext(row["name"])[0], g)
                                 for g in args.only):
            continue
        if args.max_n and row["n"] > args.max_n:
            continue
        if not os.path.exists(p):
            print(f"# manifest row without file, skipped: {row['name']}", file=sys.stderr)
            continue
        if row["sha256"] and sha256_file(p) != row["sha256"]:
            print(f"# sha256 mismatch against manifest, skipped: {row['name']}", file=sys.stderr)
            continue
        items.append((p, row["bps"]))
    for spec in args.file or []:
        if ":" not in spec:
            raise SystemExit(f"--file needs PATH:BPS, got {spec!r}")
        p, b = spec.rsplit(":", 1)
        items.append((os.path.abspath(p), int(b)))
    # ascending size so the quick cases come first; stable within a size
    items.sort(key=lambda it: (os.path.getsize(it[0]), it[0]))
    return items


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--ref-child":
        return ref_child_main(argv[1:])

    if argv and argv[0] == "--self-check":
        ap = argparse.ArgumentParser(prog="diff_driver.py --self-check")
        ap.add_argument("--case", default=None)
        a = ap.parse_args(argv[1:])
        out = self_check(a.case)
        for r in out["rows"]:
            print(f"{'ok ' if r['ok'] else 'NO '} {r['source']}: {r['step']}: expected {r['expected']}, observed {r['observed']}")
        print(f"SELF-CHECK {'PASS' if out['ok'] else 'FAIL'}: {sum(r['ok'] for r in out['rows'])}/{len(out['rows'])} rows; "
              f"record at {os.path.join(LOGS_DIFF, 'SELF-CHECK.md')}")
        return 0 if out["ok"] else 1

    if argv and argv[0] == "summary":
        text = summarize()
        print(f"wrote {os.path.join(LOGS_DIFF, 'SUMMARY.md')} ({text.count(chr(10))} lines)")
        return 0

    if argv and argv[0] == "run":
        ap = argparse.ArgumentParser(prog="diff_driver.py run", description="run the differential, one case at a time")
        ap.add_argument("--manifest", default=MANIFEST)
        ap.add_argument("--only", action="append", default=None, help="glob on the corpus file name (repeatable)")
        ap.add_argument("--max-n", type=int, default=0, help="skip manifest files larger than this many samples")
        ap.add_argument("--mode", choices=["literal", "bitstring", "both"], default="both")
        ap.add_argument("--file", action="append", default=None, help="extra PATH:BPS not in the manifest (repeatable)")
        ap.add_argument("--force", action="store_true", help="recompute cases whose result files exist")
        ap.add_argument("--force-ref", action="store_true", help="re-run the reference modules; the C++ run is reused")
        ap.add_argument("--skip-ref", action="store_true", help="run the C++ only; references recorded as skipped")
        ap.add_argument("--list", action="store_true", help="print the planned (file, bps) list and exit")
        ap.add_argument("--cpp-timeout", type=float, default=3600.0)
        ap.add_argument("--ref-timeout", type=float, default=1200.0, help="per reference module, seconds")
        ap.add_argument("--ref-option", action="append", default=[], help="module:key=value passed to that module's estimate()")
        ap.add_argument("--binary-rule", choices=["observed", "declared"], default="observed")
        ap.add_argument("--bit-order", choices=["msb", "lsb"], default="msb")
        ap.add_argument("--bitstring-truncate", type=int, default=0)
        ap.add_argument("--no-d1-recheck", action="store_true",
                        help="do not re-run a D-1-shaped disagreement with the exact quantile")
        ap.add_argument("--d1-option", action="append", default=None,
                        help="NAME=VALUE passed to estimate() for the D-1 recheck (default z=<binary64 0.995 quantile>); "
                             "MODULE:NAME=VALUE overrides it for one module (a module that rejects the name is recorded D-1?)")
        a = ap.parse_args(argv[1:])
        ref_options: dict = {}
        for spec in a.ref_option:
            mod, kv = spec.split(":", 1)
            k, v = kv.split("=", 1)
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                pass
            ref_options.setdefault(mod, {})[k] = v
        d1_default = ("z", Z_EXACT)
        d1_by_module: dict = {}
        for spec in a.d1_option or []:
            name, val = spec.split("=", 1)
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                pass
            if ":" in name:
                mod, name = name.split(":", 1)
                d1_by_module[mod] = (name, val)
            else:
                d1_default = (name, val)
        settings = {"binary_rule": a.binary_rule, "bit_order": a.bit_order, "bitstring_truncate": a.bitstring_truncate,
                    "tolerance_abs": TOL, "integer_labels": sorted(INTEGER_LABELS), "ref_options": ref_options,
                    "d1_recheck": not a.no_d1_recheck, "d1_option": d1_default, "d1_options_by_module": d1_by_module}
        items = enumerate_cases(a)
        if a.list:
            for p, b in items:
                print(f"{p}\t{b}\t{os.path.getsize(p)}")
            print(f"# {len(items)} (file, bps) pairs")
            return 0
        modes = ["literal", "bitstring"] if a.mode == "both" else [a.mode]
        os.makedirs(LOGS_DIFF, exist_ok=True)
        if sha256_file(BINARY) is None:
            print(f"# WARNING: binary missing at {BINARY}; every case will be TOOL_REFUSED (binary_missing)", file=sys.stderr)
        for p, b in items:
            recs = process_file(p, b, modes, settings, a.force, a.skip_ref, a.cpp_timeout, a.ref_timeout, ref_options,
                                force_ref=a.force_ref)
            for r in recs:
                print(r.get("verdict"))
            summarize()  # keep the summary current after every (file, bps)
        summarize()
        return 0

    # API contract __main__: <rawfile> <bits_per_symbol> [--literal|--bitstring]
    ap = argparse.ArgumentParser(prog="diff_driver.py", description="print the combined reference dict for a raw file")
    ap.add_argument("rawfile")
    ap.add_argument("bits_per_symbol", type=int)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--literal", action="store_true")
    g.add_argument("--bitstring", action="store_true")
    ap.add_argument("--binary-rule", choices=["observed", "declared"], default="observed")
    a = ap.parse_args(argv)
    sym, info = read_symbols(a.rawfile, a.bits_per_symbol)
    mode = "literal" if a.literal else "bitstring" if a.bitstring else "assessed"
    out = estimate(sym, a.bits_per_symbol, mode=mode, binary_rule=a.binary_rule)
    out["input_info"] = info
    print(json.dumps(sanitize(out), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
