#!/bin/bash
# Intake analysis probes (2026-11-07). Tiny inputs only (<= 20,000 samples),
# EA_ALLOW_SHORT_DATASET=1 and OMP_NUM_THREADS=2 on every run, every output to
# a file under logs/. Nothing here is a compliant assessment (brief rule 5).
set -u
repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment
aud=$repo/docs/audits/2026-11-07-aggressive-audit
tool=$repo/cpp/ea_non_iid
iid=$repo/cpp/ea_iid
corp=$aud/corpus
logs=$aud/logs
export EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2

python3 - "$corp" <<'PY'
import random, sys
c = sys.argv[1]
# P1: all-zero, inferred width -> word_size 0 path
open(f"{c}/intake-allzero-2000.bin","wb").write(bytes(2000))
# P2: 8-bit, random, LSB forced to 0 (constant non-leading bit); P2b: same values >> 1 (7-bit, no padding)
r = random.Random(20261107)
v = [r.randrange(256) & 0xFE for _ in range(20000)]
open(f"{c}/intake-lsb0-8bit-20000.bin","wb").write(bytes(v))
open(f"{c}/intake-lsb0-shifted-7bit-20000.bin","wb").write(bytes(x >> 1 for x in v))
# P3: skewed bits: each of 7 real bits is 1 w.p. 0.9, LSB constant 0 (padding balances a 1-heavy stream)
r = random.Random(7)
def sk():
    x = 0
    for b in range(7):
        x = (x << 1) | (1 if r.random() < 0.9 else 0)
    return x
w = [sk() for _ in range(20000)]
open(f"{c}/intake-skew09-lsb0-8bit-20000.bin","wb").write(bytes(x << 1 for x in w))
open(f"{c}/intake-skew09-7bit-20000.bin","wb").write(bytes(w))
# P4: two-sample file for the minimum-count crash check under the escape
open(f"{c}/intake-two-01.bin","wb").write(bytes([0,1]))
# P5: 4-bit data (max 0x0F) to be declared 8 -> warning path; JSON shape
r = random.Random(4)
open(f"{c}/intake-4bit-2000.bin","wb").write(bytes(r.randrange(16) for _ in range(2000)))
# P6: 4-bit data with ONE 0x80 byte, declared 4 -> D-6 refusal
d = bytearray(r.randrange(16) for _ in range(2000)); d[1234] = 0x80
open(f"{c}/intake-4bit-one80-2000.bin","wb").write(bytes(d))
PY
shasum -a 256 "$corp"/intake-*.bin > "$logs/analysis-intake-corpus-sha256.log"
shasum -a 256 "$tool" "$iid" > "$logs/analysis-intake-binaries-sha256.log"

run() { # run <label> <args...>
  local label=$1; shift
  "$@" > "$logs/analysis-intake-$label.log" 2>&1
  echo "$label rc=$?" >> "$logs/analysis-intake-exitcodes.log"
}
: > "$logs/analysis-intake-exitcodes.log"
run allzero-inferred        "$tool" -vv "$corp/intake-allzero-2000.bin"
run allzero-declared1       "$tool" -vv "$corp/intake-allzero-2000.bin" 1
run lsb0-8bit-inferred      "$tool" -vv "$corp/intake-lsb0-8bit-20000.bin"
run lsb0-shifted-7bit       "$tool" -vv "$corp/intake-lsb0-shifted-7bit-20000.bin"
run skew09-lsb0-8bit        "$tool" -vv "$corp/intake-skew09-lsb0-8bit-20000.bin"
run skew09-7bit             "$tool" -vv "$corp/intake-skew09-7bit-20000.bin"
run two-samples             "$tool" -vv "$corp/intake-two-01.bin"
run two-samples-iid         "$iid"  -vv "$corp/intake-two-01.bin"
run 4bit-declared8-json     "$tool" -q -o "$logs/analysis-intake-4bit-declared8.json" "$corp/intake-4bit-2000.bin" 8
run 4bit-declared8-vv       "$tool" -vv "$corp/intake-4bit-2000.bin" 8
run 4bit-one80-declared4    "$tool" -vv "$corp/intake-4bit-one80-2000.bin" 4
run 4bit-one80-inferred     "$tool" -vv "$corp/intake-4bit-one80-2000.bin"
run subset-last1            "$tool" -vv -l 1999,1 "$corp/intake-4bit-2000.bin"
run subset-past-end         "$tool" -vv -l 2000,1 "$corp/intake-4bit-2000.bin"
run subset-straddle         "$tool" -vv -l 1,1500 "$corp/intake-4bit-2000.bin"
run bits-0                  "$tool" -vv "$corp/intake-4bit-2000.bin" 0
run bits-9                  "$tool" -vv "$corp/intake-4bit-2000.bin" 9
run empty-file              "$tool" -vv "$corp/intake-empty.bin"
