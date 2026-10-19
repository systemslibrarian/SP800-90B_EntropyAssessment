#!/bin/bash

# HARNESS-AUD-01: every mandatory fixture/reference mutation must make the
# inventory verifier fail. All mutations occur in a disposable copy.
#
# 2026-10-19: the landing of each mutation is now asserted mechanically through
# mutation-lib.sh rather than assumed. Before this, a mutation that silently did
# not apply -- an `mv` onto a path that already existed, a target renamed
# upstream -- produced "FAIL (mutation passed)", blaming the verifier for a
# broken harness. A mutation that does not land now reports
# MUTATION-DID-NOT-APPLY and nothing else. See mutation-lib.sh for why.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
. "$here/mutation-lib.sh"

verifier="$here/verify-fixture-inventory.sh"
manifest="$here/fixture-manifest.txt"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-reginventory.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT HUP INT TERM

mkdir "$work/bin" "$work/refdata"
cp "$repo"/bin/*.bin "$work/bin/" || exit 2
cp "$here"/refdata/*.res "$work/refdata/" || exit 2

verify() { "$verifier" "$manifest" "$work/bin" "$work/refdata" >/dev/null 2>&1; }

mut_expect_pass "positive control: the complete corpus is accepted" verify || {
    echo "regression-selftest-inventory: positive control failed; nothing below is interpretable" >&2
    exit 2
}

# Each block: snapshot the target, mutate it, require the verifier to reject,
# restore. mut_expect_fail refuses to judge the verifier unless the snapshot
# shows the target actually changed.
mut_begin "missing one fixture" "$work/bin"
mv "$work/bin/normal.bin" "$work/normal.bin"
mut_expect_fail "missing one fixture" verify
mv "$work/normal.bin" "$work/bin/normal.bin"

mut_begin "missing one reference" "$work/refdata"
mv "$work/refdata/normal.res" "$work/normal.res"
mut_expect_fail "missing one reference" verify
mv "$work/normal.res" "$work/refdata/normal.res"

mut_begin "missing one complete pair" "$work"
mv "$work/bin/normal.bin" "$work/normal.bin"
mv "$work/refdata/normal.res" "$work/normal.res"
mut_expect_fail "missing one complete pair" verify
mv "$work/normal.bin" "$work/bin/normal.bin"
mv "$work/normal.res" "$work/refdata/normal.res"

mut_begin "missing multiple complete pairs" "$work"
mv "$work/bin/data.pi.bin" "$work/data.pi.bin"
mv "$work/refdata/data.pi.res" "$work/data.pi.res"
mv "$work/bin/normal.bin" "$work/normal.bin"
mv "$work/refdata/normal.res" "$work/normal.res"
mut_expect_fail "missing multiple complete pairs" verify
mv "$work/data.pi.bin" "$work/bin/data.pi.bin"
mv "$work/data.pi.res" "$work/refdata/data.pi.res"
mv "$work/normal.bin" "$work/bin/normal.bin"
mv "$work/normal.res" "$work/refdata/normal.res"

mut_begin "modified reference output" "$work/refdata/normal.res"
cp "$work/refdata/normal.res" "$work/original-normal.res"
printf '\nmodified\n' >>"$work/refdata/normal.res"
mut_expect_fail "modified reference output" verify
mv "$work/original-normal.res" "$work/refdata/normal.res"

mut_begin "missing entire fixture directory" "$work/bin"
mv "$work/bin" "$work/bin.missing"
mut_expect_fail "missing entire fixture directory" verify
mv "$work/bin.missing" "$work/bin"

mut_begin "missing entire reference directory" "$work/refdata"
mv "$work/refdata" "$work/refdata.missing"
mut_expect_fail "missing entire reference directory" verify
mv "$work/refdata.missing" "$work/refdata"

mut_expect_pass "restored control: the corpus is accepted again" verify || {
    echo "regression-selftest-inventory: the corpus was not restored; the mutations above leaked" >&2
    exit 2
}

mut_summary "regression-selftest-inventory"
