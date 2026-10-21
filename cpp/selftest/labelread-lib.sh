# labelread-lib.sh -- sourced. Instrument rule 5, mechanised (OC-73).
#
# "A labelled read is never a positional read." Where the output carries a
# label, anchor to the label and make a missing label an error -- never a
# fallback to position. `head -1` after a label match is a positional read
# wearing a label: it silently takes the first of however many lines matched,
# so a layout change that adds a second matching line is read as if nothing
# happened.
#
# The instance that produced the rule: entropy_floor.py read testCases[0] and
# computed a floor from the Most Common Value estimator instead of the case
# labelled "Overall" -- 0.983 where the answer is 0.904 (OC-35).
#
# WHY A HELPER RATHER THAN A CONVENTION. The sites are in scripts that do not
# set -e, so a failing read inside $(...) does not stop anything; the caller
# must check. lr_one makes the check one line and makes the failure loud.
#
# USAGE
#   . "$(dirname "$0")/labelread-lib.sh"
#   got=$(printf '%s\n' "$out" | sed -n 's/^Assessed min entropy: //p' \
#         | lr_one "Assessed min entropy") || exit 1
#
# lr_one reads stdin, requires EXACTLY ONE line, prints it, and returns 1 with
# a message naming the label and the count when it is anything else. Zero lines
# is as much a failure as two: a label that did not appear is instrument rule 2
# (a conclusion from absence), and this is where that surfaces for figures.

lr_one() { # lr_one <label> -- stdin must hold exactly one line
    local label=${1:-unnamed} v n
    v=$(cat)
    if [ -z "${v}" ]; then n=0; else n=$(printf '%s\n' "${v}" | grep -c ''); fi
    if [ "${n}" -ne 1 ]; then
        printf 'LABELLED READ FAILED: %s matched %s line(s), expected exactly 1.\n' \
            "${label}" "${n}" >&2
        if [ "${n}" -eq 0 ]; then
            printf '  Zero matches is not a value. The label did not appear, so nothing\n' >&2
            printf '  about it can be read -- that is instrument rule 2, not a default.\n' >&2
        else
            printf '  More than one match means position was standing in for the label:\n' >&2
            printf '%s\n' "${v}" | sed 's/^/    /' >&2
        fi
        return 1
    fi
    printf '%s\n' "${v}"
}

# lr_count <label> <expected> -- the same assertion where N > 1 is correct
lr_count() {
    local label=${1:-unnamed} want=${2:?expected count} v n
    v=$(cat)
    if [ -z "${v}" ]; then n=0; else n=$(printf '%s\n' "${v}" | grep -c ''); fi
    if [ "${n}" -ne "${want}" ]; then
        printf 'LABELLED READ FAILED: %s matched %s line(s), expected %s.\n' \
            "${label}" "${n}" "${want}" >&2
        return 1
    fi
    printf '%s\n' "${v}"
}
