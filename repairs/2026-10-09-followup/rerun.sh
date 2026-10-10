#!/bin/bash

set -eu

repo=$(cd "$(dirname "$0")/../.." && pwd)
cd "$repo"

code_revision=876ba05da68f741df33d32ade7fb52611d4852e5
git cat-file -e "${code_revision}^{commit}"
git merge-base --is-ancestor "$code_revision" HEAD

make -C cpp clean
make -C cpp -j4

set +e
cpp/selftest/run-all-checks.sh
strict_status=$?
set -e
if [ "$(uname -s)/$(uname -m)" = "Darwin/arm64" ]; then
    test "$strict_status" -eq 1
else
    test "$strict_status" -eq 0
fi

cpp/selftest/run-all-checks.sh --allow-known-platform-deltas

san_dir=$(mktemp -d "${TMPDIR:-/tmp}/ea-c01-followup.XXXXXX")
trap 'rm -rf "$san_dir"' EXIT HUP INT TERM
clang++ -std=c++11 -Xpreprocessor -fopenmp \
    -I/opt/homebrew/opt/libomp/include -O1 -g \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I/usr/include/jsoncpp -I/opt/homebrew/include \
    -I/opt/homebrew/opt/openssl@3/include cpp/restart_main.cpp \
    -o "$san_dir/ea_restart" -L/opt/homebrew/lib \
    -L/opt/homebrew/opt/openssl@3/lib -lbz2 -lpthread \
    -ldivsufsort -ldivsufsort64 -L/opt/homebrew/opt/libomp/lib \
    -lomp -ljsoncpp -lcrypto
EA_RESTART_SANITIZER_BIN="$san_dir/ea_restart" \
    cpp/selftest/sanitizer-restart-c01.sh

echo "2026-10-09 follow-up rerun: PASS"
