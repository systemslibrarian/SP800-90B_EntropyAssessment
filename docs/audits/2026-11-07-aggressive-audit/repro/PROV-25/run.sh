#!/bin/bash
# PROV-25 (documentation defect in a load-bearing comment): utils.h:1023-1025 states that non_iid_main.cpp
#          refuses a sample count above INT_MAX; it does not (grep INT_MAX: 0 hits). The claim is harmless
#          today only because n_choose_2 is reached solely from the IID 5.2.5 test; it would license a future
#          int-narrowing in ea_non_iid.
set -u
. "$(cd "$(dirname "$0")/.." && pwd)/_lib.sh"
repro_init PROV-25 observed.txt
log "source sha256 $(sha "$repo/cpp/shared/utils.h")  cpp/shared/utils.h ; $(sha "$repo/cpp/non_iid_main.cpp")  cpp/non_iid_main.cpp"
log "the comment (utils.h:1023-1025):"; sed -n 1023,1025p "$repo/cpp/shared/utils.h" | sed 's/^/  | /' | tee -a "$OBS"
n=$(grep -c 'INT_MAX' "$repo/cpp/non_iid_main.cpp" || true)
log "grep -c INT_MAX cpp/non_iid_main.cpp = $n"
log "callers of n_choose_2: $(grep -rn 'n_choose_2(' "$repo/cpp" --include='*.h' --include='*.cpp' | grep -v 'int64_t n_choose_2' | sed "s|$repo/||" | cut -d: -f1,2 | tr '\n' ' ')"
[ "$n" -eq 0 ] && verdict PASS "the comment names non_iid_main.cpp as refusing > INT_MAX samples; non_iid_main.cpp contains no INT_MAX at all"
verdict FAIL "non_iid_main.cpp has $n INT_MAX references"
