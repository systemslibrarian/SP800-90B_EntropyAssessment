#!/bin/bash
# PROV-21 negative control: swap the order. `-Z --version` is refused (rejectAt < versionAt), exit 255, no banner.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-21 control.txt
record_bin "$NONIID"
run_tool Z_then_version "$out/c_zv.out" "$out/c_zv.err" "$NONIID" -Z --version
banner=$(grep -c -E '^(non_iid|iid|restart) [0-9]+\.[0-9]+' "$out/c_zv.out" || true); ill=$(grepc 'illegal option' "$out/c_zv.err"); usage=$(grepc 'Usage is:' "$out/c_zv.out")
log "  -Z --version: rc=$RC banner=$banner 'illegal option'=$ill usage=$usage"
[ "$RC" -ne 0 ] && [ "$ill" -ge 1 ] && verdict CONTROL-OK "-Z before --version is refused (exit $RC, 'illegal option -- Z'); the same two flags in the other order exit 0"
verdict CONTROL-UNEXPECTED "rc=$RC ill=$ill"
