#!/usr/bin/env python3
"""Compact existing differential records in place (idempotent).

Applies diff_driver.compact_tables to the 'reference' and 'reference_d1_recheck' members of
every logs/diff/*.json record and to the 'values' member of every logs/diff/raw/*.ref.*.json
module output, exactly as the patched driver now writes them. Files modified within the last
--grace seconds are skipped (the driver may still be writing them). Prints bytes before/after.
"""
import argparse, glob, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diff_driver as dd  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--grace", type=int, default=120)
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
AUD = os.path.dirname(HERE)
before = after = 0; touched = skipped = 0
now = time.time()
paths = glob.glob(os.path.join(AUD, "logs/diff/*.json")) + glob.glob(os.path.join(AUD, "logs/diff/raw/*.json"))
for p in sorted(paths):
    sz = os.path.getsize(p); before += sz
    if now - os.path.getmtime(p) < a.grace:
        skipped += 1; after += sz; continue
    with open(p, encoding="utf-8") as f:
        try:
            d = json.load(f)
        except Exception as e:
            print("unparseable, left alone:", p, e); after += sz; continue
    if not isinstance(d, dict):
        after += sz; continue
    changed = False
    for key in ("reference", "reference_d1_recheck", "values"):
        if key in d:
            c = dd.compact_tables(d[key])
            if c != d[key]:
                d[key] = c; changed = True
    if changed and not a.dry_run:
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, allow_nan=True); f.write("\n")
        os.replace(tmp, p); touched += 1
    after += os.path.getsize(p) if not a.dry_run else len(json.dumps(d))
print(f"records: {len(paths)}  rewritten: {touched}  skipped (recent): {skipped}  "
      f"bytes: {before/1048576:.1f} MB -> {after/1048576:.1f} MB")
