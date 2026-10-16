#!/bin/bash

# HARNESS-AUD-01: every mandatory fixture/reference mutation must make the
# inventory verifier fail. All mutations occur in a disposable copy.

set -u

here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
verifier="$here/verify-fixture-inventory.sh"
manifest="$here/fixture-manifest.txt"
work=$(mktemp -d "${TMPDIR:-/tmp}/ea-reginventory.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT HUP INT TERM

mkdir "$work/bin" "$work/refdata"
cp "$repo"/bin/*.bin "$work/bin/" || exit 2
cp "$here"/refdata/*.res "$work/refdata/" || exit 2

fails=0
expect_failure() {
    label=$1
    if "$verifier" "$manifest" "$work/bin" "$work/refdata" >/dev/null 2>&1; then
        printf '%-48s FAIL (mutation passed)\n' "$label"
        fails=$((fails + 1))
    else
        printf '%-48s PASS (rejected)\n' "$label"
    fi
}

"$verifier" "$manifest" "$work/bin" "$work/refdata" >/dev/null || {
    echo "regression-selftest-inventory: positive control failed" >&2
    exit 2
}

mv "$work/bin/normal.bin" "$work/normal.bin"
expect_failure "missing one fixture"
mv "$work/normal.bin" "$work/bin/normal.bin"

mv "$work/refdata/normal.res" "$work/normal.res"
expect_failure "missing one reference"
mv "$work/normal.res" "$work/refdata/normal.res"

mv "$work/bin/normal.bin" "$work/normal.bin"
mv "$work/refdata/normal.res" "$work/normal.res"
expect_failure "missing one complete pair"
mv "$work/normal.bin" "$work/bin/normal.bin"
mv "$work/normal.res" "$work/refdata/normal.res"

mv "$work/bin/data.pi.bin" "$work/data.pi.bin"
mv "$work/refdata/data.pi.res" "$work/data.pi.res"
mv "$work/bin/normal.bin" "$work/normal.bin"
mv "$work/refdata/normal.res" "$work/normal.res"
expect_failure "missing multiple complete pairs"
mv "$work/data.pi.bin" "$work/bin/data.pi.bin"
mv "$work/data.pi.res" "$work/refdata/data.pi.res"
mv "$work/normal.bin" "$work/bin/normal.bin"
mv "$work/normal.res" "$work/refdata/normal.res"

cp "$work/refdata/normal.res" "$work/original-normal.res"
printf '\nmodified\n' >>"$work/refdata/normal.res"
expect_failure "modified reference output"
mv "$work/original-normal.res" "$work/refdata/normal.res"

mv "$work/bin" "$work/bin.missing"
expect_failure "missing entire fixture directory"
mv "$work/bin.missing" "$work/bin"

mv "$work/refdata" "$work/refdata.missing"
expect_failure "missing entire reference directory"
mv "$work/refdata.missing" "$work/refdata"

if ! "$verifier" "$manifest" "$work/bin" "$work/refdata" >/dev/null; then
    echo "regression-selftest-inventory: restored positive control failed" >&2
    exit 2
fi

if [ "$fails" -eq 0 ]; then
    echo "regression-selftest-inventory: PASS"
    exit 0
fi
echo "regression-selftest-inventory: FAIL ($fails checks)"
exit 1
