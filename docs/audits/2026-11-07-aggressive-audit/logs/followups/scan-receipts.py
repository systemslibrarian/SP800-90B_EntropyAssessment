#!/usr/bin/python3
import json, os, glob, datetime, sys, zoneinfo
est = zoneinfo.ZoneInfo("America/New_York")
rows = []
for d in sorted(glob.glob("/opt/homebrew/Cellar/*/*/")):
    parts = d.rstrip("/").split("/")
    formula, ver = parts[-2], parts[-1]
    rp = os.path.join(d, "INSTALL_RECEIPT.json")
    if not os.path.exists(rp):
        rows.append(dict(formula=formula, version=ver, receipt="MISSING")); continue
    with open(rp) as f:
        r = json.load(f)
    t = r.get("time")
    tl = datetime.datetime.fromtimestamp(t, est).strftime("%Y-%m-%d %H:%M:%S %Z") if t else None
    tu = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if t else None
    rows.append(dict(formula=formula, version=ver, time=t, time_local=tl, time_utc=tu,
        installed_as_dependency=r.get("installed_as_dependency"),
        installed_on_request=r.get("installed_on_request"),
        stable=(r.get("source") or {}).get("versions",{}).get("stable"),
        runtime_dependencies=[(x.get("full_name"), x.get("version")) for x in (r.get("runtime_dependencies") or [])],
        homebrew_version=r.get("homebrew_version"), poured_from_bottle=r.get("poured_from_bottle")))
json.dump(rows, open(sys.argv[1], "w"), indent=1)
# window: 2026-11-07 19:20..19:35 EST
w0 = datetime.datetime(2026,11,7,19,20,tzinfo=est).timestamp()
w1 = datetime.datetime(2026,11,7,19,35,tzinfo=est).timestamp()
print("window epochs", int(w0), int(w1))
print("total kegs", len(rows))
print("\n== KEGS IN WINDOW ==")
for r in rows:
    if r.get("time") and w0 <= r["time"] <= w1:
        print(f"{r['formula']:18s} {r['version']:14s} epoch={r['time']} local={r['time_local']} utc={r['time_utc']} as_dep={r['installed_as_dependency']} on_req={r['installed_on_request']} stable={r['stable']}")
        print("    runtime_deps:", ", ".join(f"{n} {v}" for n,v in r['runtime_dependencies']))
print("\n== KEGS 2026-11-07 (any time) or 2026-11-08 ==")
for r in rows:
    if r.get("time_local") and (r["time_local"].startswith("2026-11-07") or r["time_local"].startswith("2026-11-08")):
        print(f"{r['formula']:18s} {r['version']:14s} {r['time_local']}  as_dep={r['installed_as_dependency']}")
print("\n== FORMULAE WITH MULTIPLE KEGS ==")
from collections import defaultdict
m = defaultdict(list)
for r in rows: m[r["formula"]].append((r["version"], r.get("time_local")))
for k,v in sorted(m.items()):
    if len(v)>1: print(k, v)
print("\n== ALL KEGS SORTED BY TIME (last 40) ==")
for r in sorted([r for r in rows if r.get("time")], key=lambda r:r["time"])[-40:]:
    print(f"{r['time_local']}  {r['formula']:22s} {r['version']:14s} as_dep={r['installed_as_dependency']} on_req={r['installed_on_request']}")
