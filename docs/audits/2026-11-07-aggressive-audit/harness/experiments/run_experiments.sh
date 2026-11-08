#!/bin/bash
# run_experiments.sh -- the EXACT execution-phase commands of PLAN.md, one experiment at a time.
#
#   run_experiments.sh X1|X2|X3|X4|X5|X6|X7|X7-refusals|checks
#   OPTIONAL=1 run_experiments.sh X7      also runs the very heavy ea_iid / ea_restart acceptances
#   REF=1      run_experiments.sh X1|X2|X4  also runs the py90b differential driver on the files
#              (hours at 1e6 symbols / 8e6 bits per module; run only after the main differential
#              has finished -- the driver shares logs/diff/ and SUMMARY.md with it)
#
# Every tool invocation goes through run_one.sh (files, never pipes; binary sha256 recorded;
# OMP_NUM_THREADS=2; NO EA_ALLOW_SHORT_DATASET -- every input here is compliant-size, so a refusal
# is a refusal).  Each experiment's runs are SERIAL: one heavy job at a time (brief rule 4).
# After the runs, check_run.py writes <name>.check.json and prints the labelled one-line summary.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
aud="$(cd "$here/../.." && pwd)"
repo="$(cd "$aud/../../.." && pwd)"
V="${PY:-/private/tmp/claude-501/-Users-gmcas-repos-SP800-90B-EntropyAssessment/204b56c2-3645-487d-aa86-fccec9fd2701/scratchpad/venv/bin/python}"
T="$repo/cpp/ea_non_iid"; I="$repo/cpp/ea_iid"; S="$repo/cpp/ea_restart"
D="$aud/corpus/experiments"; L="$aud/logs/experiments"
R="$here/run_one.sh"; CK="$here/check_run.py"; DD="$aud/harness/diff_driver.py"
TRUTH_X2=1.0640216541153495
mkdir -p "$L"
export PYTHONPATH="$aud/reference${PYTHONPATH:+:$PYTHONPATH}"

ck() { "$V" "$CK" "$1" --json "$L/$1.json" ${2:+--tool $2}; }
ckn() { "$V" "$CK" "$1" ${2:+--tool $2}; }   # no JSON report expected

case "${1:-}" in
X1)
  "$R" x1-msbdead-inferred  -- "$T" -i -a -v -v -o "$L/x1-msbdead-inferred.json"  "$D/x1-uniform7-msbdead-8bit-1000000.bin"
  "$R" x1-msbdead-declared8 -- "$T" -i -a -v -v -o "$L/x1-msbdead-declared8.json" "$D/x1-uniform7-msbdead-8bit-1000000.bin" 8
  "$R" x1-lsbdead-inferred  -- "$T" -i -a -v -v -o "$L/x1-lsbdead-inferred.json"  "$D/x1-uniform7-lsbdead-8bit-1000000.bin"
  "$R" x1-lsbdead-declared8 -- "$T" -i -a -v -v -o "$L/x1-lsbdead-declared8.json" "$D/x1-uniform7-lsbdead-8bit-1000000.bin" 8
  for n in x1-msbdead-inferred x1-msbdead-declared8 x1-lsbdead-inferred x1-lsbdead-declared8; do ck $n; done
  echo "--- X1 decision: inferred vs declared (F02 direction), and each vs the truth 7"
  "$V" "$CK" --compare x1-msbdead-declared8 x1-msbdead-inferred --truth 7
  echo "--- X1 control: lsbdead inferred vs declared must be identical"
  "$V" "$CK" --compare x1-lsbdead-inferred x1-lsbdead-declared8 --truth 7
  if [ "${REF:-0}" = 1 ]; then
    "$V" "$DD" run --file "$D/x1-uniform7-msbdead-8bit-1000000.bin:7" --file "$D/x1-uniform7-msbdead-8bit-1000000.bin:8" \
                   --file "$D/x1-uniform7-lsbdead-8bit-1000000.bin:8" --ref-timeout "${REF_TIMEOUT:-7200}" \
                   --d1-option ttuple:z_variant=exact --d1-option collision:z_alpha=2.5758293035489008
  fi ;;
X2)
  for v in a-chain-lag1 b-chain-lag20; do
    "$R" x2$v-packed7-inferred  -- "$T" -i -a -v -v -o "$L/x2$v-packed7-inferred.json"  "$D/x2$v-p09-packed7-1000000.bin"
    "$R" x2$v-packed7-declared8 -- "$T" -i -a -v -v -o "$L/x2$v-packed7-declared8.json" "$D/x2$v-p09-packed7-1000000.bin" 8
    "$R" x2$v-lsbpad-inferred   -- "$T" -i -a -v -v -o "$L/x2$v-lsbpad-inferred.json"   "$D/x2$v-p09-lsbpad-8bit-1000000.bin"
    for n in x2$v-packed7-inferred x2$v-packed7-declared8 x2$v-lsbpad-inferred; do ck $n; done
    echo "--- X2 $v decision: 7-bit (inferred) vs padded, each vs the conditional truth $TRUTH_X2"
    "$V" "$CK" --compare x2$v-packed7-inferred x2$v-lsbpad-inferred --truth $TRUTH_X2
    echo "--- X2 $v: pad-first (declared 8 on packed7) vs pad-last (lsbpad) -- same bits, two pad positions"
    "$V" "$CK" --compare x2$v-packed7-declared8 x2$v-lsbpad-inferred --truth $TRUTH_X2
  done
  if [ "${REF:-0}" = 1 ]; then
    "$V" "$DD" run --file "$D/x2b-chain-lag20-p09-lsbpad-8bit-1000000.bin:8" --file "$D/x2b-chain-lag20-p09-packed7-1000000.bin:7" \
                   --file "$D/x2a-chain-lag1-p09-lsbpad-8bit-1000000.bin:8" --file "$D/x2a-chain-lag1-p09-packed7-1000000.bin:7" \
                   --ref-timeout "${REF_TIMEOUT:-7200}" --d1-option ttuple:z_variant=exact --d1-option collision:z_alpha=2.5758293035489008
  fi ;;
X3)
  for v in naive-P32-b17-q0 gadget-P32-b17-q4; do
    short=${v%%-*}
    "$R" x3-$short-tool  -- "$T" -i -a -v -v -o "$L/x3-$short-tool.json" "$D/x3-mmc-orphan-$v-8bit-1000000.bin" 8
    ck x3-$short-tool
    # the spec-literal reference (py90b, k = observed alphabet as the tool uses) -- stdout IS the JSON
    "$R" x3-$short-ref   -- "$V" -m py90b.multimmc "$D/x3-mmc-orphan-$v-8bit-1000000.bin" 8 --k-mode=observed
    # the two models at the real cap (heavy: ~1 GB, minutes); stdout is JSON with text_model / cpp_model
    "$R" x3-$short-model -- "$V" "$here/x3_multimmc_orphans.py" --model "$D/x3-mmc-orphan-$v-8bit-1000000.bin"
    echo "--- X3 $short: Literal MultiMMC as printed by the tool"
    grep -E "^Literal MultiMMC Prediction Estimate: (C|r|N|P_global|P_global'|P_local|min entropy)" "$L/x3-$short-tool.stdout"
    echo "--- X3 $short: reference C, r, min entropy (py90b)"
    "$V" -c "import json,sys; d=json.load(open(sys.argv[1])); print({k:d[k] for k in ('C','r','N','P_global',\"P_global'\",'P_local','min_entropy','winner','cap_bound')})" "$L/x3-$short-ref.stdout"
    echo "--- X3 $short: models (text == reference? cpp == tool?)"
    "$V" -c "import json,sys; d=json.load(open(sys.argv[1])); print('text', {k:d['text_model'][k] for k in ('C','r','min_entropy')}); print('cpp ', {k:d['cpp_model'][k] for k in ('C','r','min_entropy')}); print('delta C text-cpp', d['delta_C_text_minus_cpp'])" "$L/x3-$short-model.stdout"
  done ;;
X4)
  "$R" x4-alt1  -- "$T" -i -a -v -v -o "$L/x4-alt1.json"  "$D/x4-alternating-1bit-1000000.bin" 1
  "$R" x4-alt8  -- "$T" -i -a -v -v -o "$L/x4-alt8.json"  "$D/x4-alternating-0-255-8bit-1000000.bin" 8
  "$R" x4-two8  -- "$T" -i -a -v -v -o "$L/x4-two8.json"  "$D/x4-two-symbol-0-255-random-8bit-1000000.bin" 8
  "$R" x4-once1 -- "$T" -i -a -v -v -o "$L/x4-once1.json" "$D/x4-one-symbol-once-1bit-1000000.bin" 1
  "$R" x4-once8 -- "$T" -i -a -v -v -o "$L/x4-once8.json" "$D/x4-one-symbol-once-8bit-1000000.bin" 8
  "$R" x4-ctr8  -- "$T" -i -a -v -v -o "$L/x4-ctr8.json"  "$D/x4-counter-mod256-8bit-1000000.bin" 8
  for n in x4-alt1 x4-alt8 x4-two8 x4-once1 x4-once8 x4-ctr8; do ck $n; done
  echo "--- X4 decision per run: DEGENERATE kinds (nan/inf = finding; -0 = record), notRun flags (none expected),"
  echo "    fold-consistency (FAIL = the assessed figure is not the min of the printed estimates), estimate counts:"
  for n in x4-alt1 x4-alt8 x4-two8 x4-once1 x4-once8 x4-ctr8; do
    "$V" -c "import json,sys; d=json.load(open(sys.argv[1])); m=d['text']['min_of_printed']; print(sys.argv[2], 'Literal', m['Literal']['count'], 'Bitstring', m['Bitstring']['count'], 'degenerate', [x['kind'] for x in d['text']['degenerate']], 'notRun', d['json'].get('not_run_flags'))" "$L/$n.check.json" $n
  done
  if [ "${REF:-0}" = 1 ]; then
    "$V" "$DD" run --file "$D/x4-alternating-1bit-1000000.bin:1" --file "$D/x4-alternating-0-255-8bit-1000000.bin:8" \
                   --file "$D/x4-two-symbol-0-255-random-8bit-1000000.bin:8" --file "$D/x4-one-symbol-once-1bit-1000000.bin:1" \
                   --file "$D/x4-one-symbol-once-8bit-1000000.bin:8" --file "$D/x4-counter-mod256-8bit-1000000.bin:8" \
                   --ref-timeout "${REF_TIMEOUT:-7200}" --d1-option ttuple:z_variant=exact --d1-option collision:z_alpha=2.5758293035489008
  fi ;;
X5)
  "$R" x5-c-999999 -- "$T" -c -a -v -v -o "$L/x5-c-999999.json" "$D/x5-sha256-outputs-31250-999999.bin" 8     # control: refused (light)
  "$R" x5-c-1e6    -- "$T" -c -a -v -v -o "$L/x5-c-1e6.json"    "$D/x5-sha256-outputs-31250-1000000.bin" 8    # 31,250 outputs: accepted? (heavy)
  ck x5-c-999999; ck x5-c-1e6
  echo "--- X5 decision: x5-c-1e6 accepted+COMPLIANT (rc 0, errorLevel 0, no nonCompliantShortDataset) = the -c gate counts bytes,"
  echo "    accepting 31,250 conditioner outputs where 3.1.1 item 2 asks for 1,000,000; x5-c-999999 must be refused (control)." ;;
X6)
  "$R" x6-noniid  -- "$T" -i -a -v -v -o "$L/x6-noniid.json" "$D/x6-debruijn-k100-seed11-1000000.bin" 8
  "$R" x6-restart -- "$S" -n -v -o "$L/x6-restart.json" "$D/x6-debruijn-k100-seed11-1000000.bin" 8 0.5/symbol
  ck x6-noniid; ck x6-restart restart
  echo "--- X6 decision: ea_non_iid JSON marks LRS 'literalEstimateNotRun'; the restart JSON's 'LRS Test' case has h_c but no h_r and NO flag:"
  "$V" -c "import json,sys; d=json.load(open(sys.argv[1])); print('non_iid notRun flags:', d['json'].get('not_run_flags'))" "$L/x6-noniid.check.json"
  "$V" -c "import json,sys; d=json.load(open(sys.argv[1])); j=d['json']; print('restart notRun flags:', j.get('not_run_flags')); print('cases with h_r:', j.get('restart_cases_with_h_r')); print('cases with h_c:', j.get('restart_cases_with_h_c')); print('Overall:', j.get('overall')); print('text min(H_r,H_c,H_I):', d['text'].get('restart_min'), 'passed:', d['text'].get('restart_passed'))" "$L/x6-restart.check.json" ;;
X7-refusals|X7)
  # light: every refusal fires before any estimator runs
  for W in 1 8; do
    for tool in non_iid iid; do
      B="$T"; [ $tool = iid ] && B="$I"
      "$R" x7-$tool-${W}bit-999999              -- "$B" -i -a -v -v -o "$L/x7-$tool-${W}bit-999999.json"              "$D/x7-csprng-${W}bit-999999.bin" $W
      "$R" x7-$tool-${W}bit-l1-1000000-on-1000001 -- "$B" -i -a -v -v -l 1,1000000 -o "$L/x7-$tool-${W}bit-l1-1000000-on-1000001.json" "$D/x7-csprng-${W}bit-1000001.bin" $W
      "$R" x7-$tool-${W}bit-l0-999999-on-1000000  -- "$B" -i -a -v -v -l 0,999999  -o "$L/x7-$tool-${W}bit-l0-999999-on-1000000.json"  "$D/x7-csprng-${W}bit-1000000.bin" $W
      "$R" x7-$tool-${W}bit-l1-500000-on-1000000  -- "$B" -i -a -v -v -l 1,500000  -o "$L/x7-$tool-${W}bit-l1-500000-on-1000000.json"  "$D/x7-csprng-${W}bit-1000000.bin" $W
      for n in x7-$tool-${W}bit-999999 x7-$tool-${W}bit-l1-1000000-on-1000001 x7-$tool-${W}bit-l0-999999-on-1000000 x7-$tool-${W}bit-l1-500000-on-1000000; do ck $n $tool; done
    done
    HI=0.9; [ $W = 8 ] && HI=7/symbol
    "$R" x7-restart-${W}bit-999999  -- "$S" -n -v -o "$L/x7-restart-${W}bit-999999.json"  "$D/x7-csprng-${W}bit-999999.bin"  $W $HI
    "$R" x7-restart-${W}bit-1000001 -- "$S" -n -v -o "$L/x7-restart-${W}bit-1000001.json" "$D/x7-csprng-${W}bit-1000001.bin" $W $HI
    ck x7-restart-${W}bit-999999 restart; ck x7-restart-${W}bit-1000001 restart
  done
  if [ "${1}" = X7 ]; then
    # heavy acceptances: ea_non_iid at 1,000,000 and 1,000,001 and -l 0,1000000 (minutes each)
    for W in 1 8; do
      "$R" x7-non_iid-${W}bit-1000000              -- "$T" -i -a -v -v -o "$L/x7-non_iid-${W}bit-1000000.json"              "$D/x7-csprng-${W}bit-1000000.bin" $W
      "$R" x7-non_iid-${W}bit-1000001              -- "$T" -i -a -v -v -o "$L/x7-non_iid-${W}bit-1000001.json"              "$D/x7-csprng-${W}bit-1000001.bin" $W
      "$R" x7-non_iid-${W}bit-l0-1000000-on-1000001 -- "$T" -i -a -v -v -l 0,1000000 -o "$L/x7-non_iid-${W}bit-l0-1000000-on-1000001.json" "$D/x7-csprng-${W}bit-1000001.bin" $W
      for n in x7-non_iid-${W}bit-1000000 x7-non_iid-${W}bit-1000001 x7-non_iid-${W}bit-l0-1000000-on-1000001; do ck $n; done
    done
    if [ "${OPTIONAL:-0}" = 1 ]; then
      # VERY heavy: ea_iid runs the full 5.1 permutation battery (hours each); ea_restart -n at 1e6 (minutes)
      for W in 1 8; do
        "$R" x7-iid-${W}bit-1000000 -- "$I" -i -a -v -v -o "$L/x7-iid-${W}bit-1000000.json" "$D/x7-csprng-${W}bit-1000000.bin" $W
        "$R" x7-iid-${W}bit-1000001 -- "$I" -i -a -v -v -o "$L/x7-iid-${W}bit-1000001.json" "$D/x7-csprng-${W}bit-1000001.bin" $W
        ck x7-iid-${W}bit-1000000 iid; ck x7-iid-${W}bit-1000001 iid
        HI=0.9; [ $W = 8 ] && HI=7/symbol
        "$R" x7-restart-${W}bit-1000000 -- "$S" -n -v -o "$L/x7-restart-${W}bit-1000000.json" "$D/x7-csprng-${W}bit-1000000.bin" $W $HI
        ck x7-restart-${W}bit-1000000 restart
      done
    fi
  fi
  echo "--- X7 decision: every *-999999 and every -l case loading < 1,000,000 is refused (rc 255, errorLevel -1, class input);"
  echo "    every 1,000,000 / 1,000,001 / -l 0,1000000 case is accepted and COMPLIANT; ea_restart refuses 999,999 AND 1,000,001." ;;
checks)
  for f in "$L"/*.rc; do n=$(basename "$f" .rc); case $n in x*-probe-*) continue;; esac; if [ -f "$L/$n.json" ]; then ck $n; else ckn $n; fi; done ;;
*)
  echo "usage: run_experiments.sh X1|X2|X3|X4|X5|X6|X7|X7-refusals|checks   [REF=1] [OPTIONAL=1] [PY=python]" >&2; exit 2 ;;
esac
