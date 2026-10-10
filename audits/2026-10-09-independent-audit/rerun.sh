#!/bin/bash
# Minimal, isolated rerun for the central audit evidence.
# Usage: ./rerun.sh OUTPUT_DIRECTORY [TRUEPAD_ROOT]

set -u
set -o pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 OUTPUT_DIRECTORY [TRUEPAD_ROOT]" >&2
    exit 2
fi

out=$1
truepad_root=${2:-}
if [ -e "$out" ]; then
    echo "refusing existing output path: $out" >&2
    exit 2
fi
mkdir -p "$out" || exit 2
out=$(cd "$out" && pwd)

audit_dir=$(cd "$(dirname "$0")" && pwd)
repo=$(git -C "$audit_dir" rev-parse --show-toplevel) || exit 2
expected=106d31c4b010d9cd4ae94c0db14d9dcf11aeb353
upstream_expected=87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289
scratch=$(mktemp -d "${TMPDIR:-/tmp}/sp80090b-rerun.XXXXXX") || exit 2
fork_wt="$scratch/fork"
upstream_wt="$scratch/upstream"

cleanup() {
    if [ -d "$fork_wt" ]; then git -C "$repo" worktree remove --force "$fork_wt" >/dev/null 2>&1 || true; fi
    if [ -d "$upstream_wt" ]; then git -C "$repo" worktree remove --force "$upstream_wt" >/dev/null 2>&1 || true; fi
    if [ -d "$scratch" ]; then find "$scratch" -depth -delete >/dev/null 2>&1 || true; fi
}
trap cleanup EXIT HUP INT TERM

git -C "$repo" cat-file -e "$expected^{commit}" || exit 2
git -C "$repo" worktree add --detach "$fork_wt" "$expected" >"$out/worktree.log" 2>&1 || exit 2

(
    cd "$fork_wt/cpp" || exit 2
    make clean
    make non_iid iid restart
) >"$out/build.log" 2>&1
build_status=$?
echo "$build_status" >"$out/build.status"
[ "$build_status" -eq 0 ] || exit "$build_status"

(
    cd "$fork_wt/cpp/selftest" || exit 2
    ./run-all-checks.sh
) >"$out/strict-suite.log" 2>&1
strict_status=$?
echo "$strict_status" >"$out/strict-suite.status"
if [ "$strict_status" -ne 0 ] && [ "$strict_status" -ne 1 ]; then exit "$strict_status"; fi

fixtures="$scratch/fixtures"
python3 "$audit_dir/generators/valid_fixtures.py" "$fixtures" || exit 2
cp "$fixtures/manifest.json" "$out/fixture-manifest.json" || exit 2
python3 "$audit_dir/oracles/mcv_oracle.py" "$fixtures/biased-p01-1bit.bin" 1 >"$out/mcv-oracle.json" || exit 2
"$fork_wt/cpp/ea_non_iid" -q -o "$out/alternating.json" "$fixtures/alternating-1bit.bin" 1
alternating_status=$?
echo "$alternating_status" >"$out/alternating.status"
[ "$alternating_status" -eq 0 ] || exit "$alternating_status"
python3 -c 'import json,sys; v=json.load(open(sys.argv[1])); o=next(x for x in v["testCases"] if x.get("testCaseDesc")=="Overall"); assert o["hAssessed"] == 0' "$out/alternating.json" || exit 2

if [ -n "$truepad_root" ]; then
    truepad_root=$(cd "$truepad_root" && pwd) || exit 2
    git -C "$repo" cat-file -e "$upstream_expected^{commit}" || exit 2
    git -C "$repo" worktree add --detach "$upstream_wt" "$upstream_expected" >>"$out/worktree.log" 2>&1 || exit 2
    node "$audit_dir/reproducers/truepad-unattested-tools.mjs" \
        "$truepad_root" "$upstream_wt" "$scratch/truepad" \
        >"$out/truepad-unattested-tools.log" 2>&1
    echo "$?" >"$out/truepad-unattested-tools.status"
fi

(
    cd "$out" || exit 2
    find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 shasum -a 256 >SHA256SUMS
) || exit 2

echo "build=$build_status strict=$strict_status alternating=$alternating_status"
echo "The strict status is preserved; it may be 1 on macOS arm64 because of upstream #155."
exit 0
