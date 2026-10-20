# Tag `unrepaired-reference-2026-10-15` — what the tag itself cannot tell you

This file exists because the tag is immutable and its instructions have two
known gaps. Anyone who searches this repository for the tag's name lands here.

**What the tag is.** The last master before `repair/2026-10-09-verified-defects`
was merged (merge commit `d226f18`, 2026-10-15). It builds the **unrepaired**
tool: `C07` (the LRS `p_col^W` underflow — abort with asserts live, a
**fabricated** figure under `-DNDEBUG`) and `C03` (a failed IID battery still
awards a figure) are present. It is kept so the reference tool's own figure
stays reportable beside the repaired fork's ("two figures, always",
`audits/2026-10-11-independent-audit/REPAIR-STRATEGY.md`). Tag object
`0fcdf16c…`, commit `655bd109…`.

**Why the tag was not re-pointed with a corrected message.** It could be: a
forced re-tag of the same commit changes nothing about the commit. But it
replaces the *tag object*, and every clone that has already fetched the tag
keeps the old object unless it force-fetches — including any consumer that
recorded the tag object's hash. A pin that silently differs between two clones
is worse than a pin with a known gap. So the tag stays as cut and this file
carries the corrections.

## The two gaps, found by walking the tag (OC-25)

Followed from a fresh `git clone --branch unrepaired-reference-2026-10-15
--depth 1` with nothing from master, 2026-10-18, every command in
`audits/2026-10-11-independent-audit/logs/merge/tag-walk-2026-10-18.log`:

1. **The macOS quick-start block builds only `ea_non_iid`** (`make non_iid`).
   The reference *IID* tool, which the provenance canary classifies, needs the
   "Running the checks" block's `make non_iid iid restart`.
2. **The quick-start's bare `./selftest` exits 1 — on macOS arm64 only.** It
   reports `FAIL (2 of 11 files): biased-random-bytes.bin ringOsc-nist.bin`.
   Those are the documented upstream #155 platform deltas, explained elsewhere
   in the same `BUILDING.md`, not a build failure; `pin-check.sh
   --prove-nonvacuous` passes, and the invocation that excuses exactly those two
   files is `cpp/selftest/run-all-checks.sh --allow-known-platform-deltas`.
   **The deltas are macOS-only**: measured 2026-10-19 on x86-64 Linux CI, the
   strict suite is a full pass, 20 of 20 (`OC-40`). So someone following the
   tag's instructions on Linux will not hit this, and the gap recorded here is
   the macOS case — which is the platform the walk was done on.

A third observation, recorded as seen: the walk's single
`brew list --versions libomp libdivsufsort jsoncpp openssl@3` printed three
packages and omitted `openssl@3`, though the link against it succeeded; a direct
query shows `openssl@3 3.6.4`. Versions match the tag's own table.

## The command sequence that works, as run

```sh
git clone --branch unrepaired-reference-2026-10-15 --depth 1 \
    https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git unrepaired
cd unrepaired
brew install libomp libdivsufsort jsoncpp openssl@3      # already present on the walk host
cd cpp && make non_iid iid restart                        # exit 0
cd selftest && ./run-all-checks.sh --allow-known-platform-deltas   # instead of bare ./selftest
```

Asserts are live in that build; no Makefile target sets `-DNDEBUG`, and adding
it reproduces the fabrication (`XR-04`).

**Its `ea_restart` is the pre-repair one** (`OC-29`, `OC-30`): it accepts a bare
`H_I` at any scale and accepts `1e-400` as 0, both of which master refuses. Its
sanity-check cutoff is upstream's simulation of the multinomial maximum, which
is the **correct** statistic (upstream issue #56 asked for it); master computes
that same statistic exactly instead, so the two agree within a count or two.
The cutoff this binary reports varies run to run and its report records neither
the cutoff nor `X_max`, so capture the `-v` output if a decision from it has to
be re-checked (`XR-11`).

## Which instrument classified it, so the result is reproducible rather than believed

The canary was re-signatured *after* the tag was cut (`XR-08`, 2026-10-18), so
it is a variable in its own right. The walk used
`tools/build-provenance-canary.sh` as of master commit **`b12247c`** (the
re-signature commit). Commit `157ef7e` later edited that file's header comments
and the INDETERMINATE explanatory text only — `git diff b12247c 157ef7e --
tools/build-provenance-canary.sh` touches no signature logic — so running the
canary from any master commit at or after `b12247c` reproduces:

| tag build | `canary: TREE` | `canary: BUILD` | exit |
|---|---|---|---|
| `make non_iid iid restart` (asserts live) | UNREPAIRED | ASSERTS-LIVE | 0 |
| `make -B CXX="clang++ -DNDEBUG" iid` | UNREPAIRED | NDEBUG | 0 |

Binaries from the walk: `ea_iid 5bece408…`, `ea_non_iid 47796ac9…`,
`ea_restart d88e9d0e…` (SHA-256, full values in the log). Measured on Apple
arm64, where `long double` is IEEE double; the wide `long double` formats are a
bounded argument (`OC-24`).

The repairs on master are self-authored and unreviewed; this tag is the
unrepaired reference, not a reviewed one either.
