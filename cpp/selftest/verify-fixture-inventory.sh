#!/bin/bash

# Verify the complete, authoritative self-test corpus. Do not infer what is
# required from whatever files happen to remain in bin/ or refdata/.

set -u

if [ "$#" -ne 3 ]; then
    echo "usage: $0 MANIFEST BIN_DIRECTORY REFERENCE_DIRECTORY" >&2
    exit 2
fi

manifest=$1
bin_dir=$2
ref_dir=$3

if [ ! -f "$manifest" ] || [ ! -d "$bin_dir" ] || [ ! -d "$ref_dir" ]; then
    echo "fixture-inventory: manifest, input directory, and reference directory must all exist" >&2
    exit 1
fi

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "fixture-inventory: no SHA-256 utility is available" >&2
        return 2
    fi
}

work=$(mktemp -d "${TMPDIR:-/tmp}/ea-fixture-inventory.XXXXXX") || exit 2
trap 'rm -rf "$work"' EXIT HUP INT TERM
inputs="$work/inputs"
references="$work/references"
: >"$inputs"
: >"$references"

line_number=0
while IFS=' ' read -r kind name expected extra; do
    line_number=$((line_number + 1))
    case "$kind" in ''|'#'*) continue ;; esac
    if [ -n "${extra:-}" ] || ! printf '%s' "$expected" | grep -Eq '^[0-9a-f]{64}$' ||
       ! printf '%s' "$name" | grep -Eq '^[A-Za-z0-9._-]+$'; then
        echo "fixture-inventory: malformed manifest line $line_number" >&2
        exit 1
    fi
    case "$kind" in
        input) directory=$bin_dir; list=$inputs; suffix=.bin ;;
        reference) directory=$ref_dir; list=$references; suffix=.res ;;
        *) echo "fixture-inventory: unknown kind '$kind' on line $line_number" >&2; exit 1 ;;
    esac
    case "$name" in *"$suffix") ;; *) echo "fixture-inventory: $kind '$name' has the wrong suffix" >&2; exit 1 ;; esac
    if grep -Fqx "$name" "$list"; then
        echo "fixture-inventory: duplicate $kind '$name'" >&2
        exit 1
    fi
    printf '%s\n' "$name" >>"$list"
    candidate="$directory/$name"
    if [ ! -f "$candidate" ]; then
        echo "fixture-inventory: missing mandatory $kind '$name'" >&2
        exit 1
    fi
    actual=$(hash_file "$candidate") || exit $?
    if [ "$actual" != "$expected" ]; then
        echo "fixture-inventory: $kind '$name' SHA-256 mismatch" >&2
        exit 1
    fi
done <"$manifest"

input_count=$(wc -l <"$inputs" | tr -d ' ')
reference_count=$(wc -l <"$references" | tr -d ' ')
if [ "$input_count" -ne 11 ] || [ "$reference_count" -ne 11 ]; then
    echo "fixture-inventory: expected 11 inputs and 11 references, found $input_count and $reference_count" >&2
    exit 1
fi

while IFS= read -r input; do
    reference=${input%.bin}.res
    if ! grep -Fqx "$reference" "$references"; then
        echo "fixture-inventory: input '$input' has no inventoried reference '$reference'" >&2
        exit 1
    fi
done <"$inputs"

while IFS= read -r reference; do
    input=${reference%.res}.bin
    if ! grep -Fqx "$input" "$inputs"; then
        echo "fixture-inventory: reference '$reference' has no inventoried input '$input'" >&2
        exit 1
    fi
done <"$references"

for candidate in "$bin_dir"/*.bin; do
    [ -e "$candidate" ] || { echo "fixture-inventory: no input fixtures discovered" >&2; exit 1; }
    name=$(basename "$candidate")
    grep -Fqx "$name" "$inputs" || { echo "fixture-inventory: unexpected input '$name'" >&2; exit 1; }
done
for candidate in "$ref_dir"/*.res; do
    [ -e "$candidate" ] || { echo "fixture-inventory: no reference outputs discovered" >&2; exit 1; }
    name=$(basename "$candidate")
    grep -Fqx "$name" "$references" || { echo "fixture-inventory: unexpected reference '$name'" >&2; exit 1; }
done

manifest_hash=$(hash_file "$manifest") || exit $?
echo "fixture-inventory: PASS (11 inputs, 11 references; manifest SHA-256 $manifest_hash)"
