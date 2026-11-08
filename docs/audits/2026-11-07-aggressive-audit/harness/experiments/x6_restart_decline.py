#!/usr/bin/env python3
"""x6_restart_decline.py -- X6: a declined estimator in the restart path (restart.md E5 /
prior-repairs.md E3).

Input: de Bruijn B(100,3), exactly 100^3 = 1,000,000 bytes over the symbols 0..99, produced by
the repository's own generator audits/2026-09-30/novel-findings/generators/restart/gen_debruijn.py
with seed 11 (the call the prior records name: `gen_debruijn.py 100 11`).  Every 3-tuple occurs
at most once and every 2-tuple about 100 times, so on the ROW dataset (the file as one sequence)
SP 800-90B 6.3.6 gives u = 3 (smallest u with the most common u-tuple under 35 occurrences) and
v = 2 (largest v with a repeated v-tuple): "If v < u, this estimate cannot be computed" (PDF
p. 56).  On the COLUMN dataset (the transpose) 3-tuples are symbols 1000 apart and do repeat, so
LRS is computable there.  So the restart run has LRS declined on rows only.

This file is written by calling gen_debruijn.py through the current interpreter (it uses only
random.Random(seed).shuffle, stable across CPython 3.x); the sha256 is recorded, and --check
re-hashes it like every other input.

Decision (PLAN.md X6): `ea_non_iid -i -a -vv -o n.json <file> 8` must carry
"literalEstimateNotRun": true on the "LRS Test" case (F05); `ea_restart -n -v -o r.json <file> 8
0.5/symbol` has NO such field (restart_main.cpp never sets literal_not_run; restart.md S1): the
LRS case's h_r is simply absent while h_c is present, and H_r is the minimum over NINE row
estimators with nothing in the report saying so.  Positive = the restart JSON omits the decline
silently while the ea_non_iid JSON records it.  Direction: neutral for the figure (the declined
estimate has no value to compare); LOW, report completeness.
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X6"
GEN = os.path.join(common.REPO, "audits", "2026-09-30", "novel-findings", "generators", "restart",
                   "gen_debruijn.py")
NAME = "x6-debruijn-k100-seed11-1000000.bin"


def generate() -> None:
    rows = common.read_manifest()
    os.makedirs(common.DATA_DIR, exist_ok=True)
    out = os.path.join(common.DATA_DIR, NAME + ".tmp")
    r = subprocess.run([sys.executable, GEN, "100", "11", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"gen_debruijn.py failed rc={r.returncode}: {r.stderr}")
    with open(out, "rb") as f:
        data = f.read()
    os.remove(out)
    if len(data) != common.N_COMPLIANT:
        raise SystemExit(f"gen_debruijn.py wrote {len(data)} bytes, expected 1,000,000")
    common.write_data_file(NAME, data, 8, EXPERIMENT,
                           f"de Bruijn B(100,3) via gen_debruijn.py 100 11 (generator sha256 "
                           f"{common.sha256_file(GEN)}): 1,000,000 bytes over 0..99, every 3-tuple at most once; "
                           "row LRS u=3 > v=2 declines; declare 8 (warning 'narrower than described' expected)",
                           __file__, rows)
    print("gen_debruijn.py said:", r.stdout.strip())


if __name__ == "__main__":
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
