# Cross-repository findings — for the TruePad session to act on

Findings verified **in this repository** that have consequences **in TruePad**.
A finding may cross repos; a commit may not. Nothing here has been changed in
`~/repos/TruePad`, and nothing here should be fixed from a session scoped to
this fork — the earlier `3f27453` was exactly that mistake.

---

## XR-01 — a failed run leaves the previous run's report on disk, reporting success

**Verified by execution in this repository, on `master` `f069898` and on the
repair branch `2d4b135` — identical on both.** Cluster `C14`, member
`output-automation-contracts-4`.

### Why TruePad needs this

TruePad's desktop harness invokes these tools and reads their output files. If
it reads `RESULT.json` **without first checking the tool's exit status**, it
will silently consume a stale number from a previous run. The number looks
completely valid — it is a real assessment, of different data.

### What was demonstrated

```
# 1. a good run writes a real report
ea_non_iid -q -o RESULT.json uniform-1bit.bin 1
  rc=0        RESULT.json: errorLevel 0, hAssessed 0.8389091522985468

# 2. a FAILING run against the same -o path
ea_non_iid -l 5,0 -o RESULT.json uniform-1bit.bin 1
  rc=255
  "Error: -l requires a sample count greater than zero."
  (usage dump follows)

# 3. what is on disk afterwards
RESULT.json is BYTE-IDENTICAL to the previous successful run
```

**What a consumer reading the file rather than the status sees:**

| Field | Value it reads | Truth |
|---|---|---|
| `errorLevel` | `0` | the run failed |
| `hAssessed` | `0.8389091522985468` | nothing was assessed |
| `filename`, `sha256` | the **previous** run's | not what was submitted |
| `dateTimeStamp`, `commandline` | the **previous** run's | not this invocation |

The tool writes **nothing** on this path — it does not truncate, does not write
an error report, and does not remove the file. The error goes to stdout/stderr
and the exit status only.

### Direction

**Unknown, leaning permissive.** Whether the stale figure is higher or lower
than the truth depends entirely on what ran before. The dangerous case — a
stale figure *higher* than the data deserves — is as likely as the safe one,
and a consumer has no way to tell from the file's contents alone that it is
reading history.

### What the TruePad session can do about it, in order of strength

1. **Check the exit status.** This is the complete fix on the consumer side and
   costs nothing. `255` means the file is not this run's.
2. **Cross-check provenance.** The stale file carries the *previous* run's
   `filename` and `sha256`. A consumer that compares those against the input it
   actually submitted catches this even without the exit status. That is a
   second, independent check and worth having regardless.
3. **Delete the output path before invoking the tool.** Then a missing file is
   itself the error signal, and there is no stale state to read.

Fixing it on the tool side (truncate or write an error report on every error
path) belongs to this fork and is tracked under `C14`. It is not fixed here —
`C14` has eight members and only this one is verified.

### Scope of this verification

- **Correct and verified**: the stale file survives, the exit status is 255, the
  contents are byte-identical, and a consumer reading the file sees
  `errorLevel 0` with a complete figure. Demonstrated on both branches.
- **Not verified**: the other seven members of `C14` (no exit status
  distinguishes statistical rejection from invalid input; `-q` suppressing
  verdict lines; three file problems collapsing to one message; non-atomic
  writes; `--version` anywhere in argv short-circuiting). Those remain
  finder claims.
- **Not established**: whether TruePad's harness actually reads the file without
  checking status. That is a question about TruePad's code, which this session
  did not read. The finding states the hazard; confirming the exposure is the
  TruePad session's to do.

---

## XR-02 — `gen-sbom.sh` can record an empty patch digest, and `--check` will agree with it

**Reported, not fixed.** From the dead-guard sweep, instance 12.

`ios/scripts/gen-sbom.sh:249`:

```sh
PATCH_DIGEST="$(file_digest "$VENDOR/EXPECTED-PATCH.diff" 2>/dev/null || echo "")"
```

`file_digest` is `shasum -a 256 "$1" | awk '{print $1}'` under `set -euo
pipefail`, so a missing `EXPECTED-PATCH.diff` fails the pipeline; `|| echo ""`
catches it — which also prevents `set -e` from aborting — and `PATCH_DIGEST`
becomes empty. It is emitted unchecked at `:314` as
`{ "name": "truepad:patch-digest", "value": "" }`.

Because `gen-sbom.sh --check` compares a regenerated SBOM against the committed
one, a missing patch file yields empty on **both** sides and the comparison
passes. The digest that would detect a changed vendored patch can be absent
while the SBOM check reports agreement.

The fix has the same shape as the one already applied to `run-audit.sh` in
`3f27453`: assert the digest is non-empty before emitting it. **Left for the
TruePad session.**

---

## Note on `3f27453`

That commit (TruePad `master`, `audit-scripts/run-audit.sh`, the evidence
manifest check) was made from this fork's session and was a scope error. It is
left in place rather than reverted, on instruction. The TruePad session should
take ownership of it, review it, and decide whether to keep, amend or drop it.
Its commit message records the mechanism — `grep -c .` printing `0` while
exiting `1`, so a `|| echo 0` fallback fires alongside a successful print — so
the broken form is not reintroduced.
