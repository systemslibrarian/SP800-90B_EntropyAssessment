# A-1 correction — N-10 pre-fix failure count

Date: 2026-10-10  
Reviewed PR head: `baa51b352928db83f0620c2559cb1641914127e0`

The hostile review found that the committed N-10 IID JSON regression produces
three pre-fix failures, while `REPORT.md` said two. This directory preserves
the correction evidence. It changes no production source or regression test.

## Exact parent reproduction

The procedure transports only the regression from the fix commit onto its
parent:

```sh
git worktree add --detach /tmp/sp800-a1-correction/parent \
  031d7eefe6801c8370c9882cb81348d7cf1df388
git -C /tmp/sp800-a1-correction/parent checkout \
  094189cdc6dd2b2d975abcbe00d7018628c50bee -- \
  cpp/selftest/regression-iid-json.sh
make -C /tmp/sp800-a1-correction/parent/cpp iid
(cd /tmp/sp800-a1-correction/parent && \
  cpp/selftest/regression-iid-json.sh)
```

Identities:

- source SHA: `031d7eefe6801c8370c9882cb81348d7cf1df388`;
- test commit: `094189cdc6dd2b2d975abcbe00d7018628c50bee`;
- test blob: `ddbfb3acd6c3196c20cfbae5c25507a072437c98`;
- test SHA-256:
  `db1fd5caf8ee438e1afededd64ad84e9950aeb19c77c85e1df8b543326d83b06`;
- exit status: 1;
- summary: `regression-iid-json: FAIL (3 checks)`.

The failures are:

1. ambiguous or missing JSON statistic fields;
2. stdout still labels the translated-index statistic only as `Median`;
3. the sparse-alphabet control cannot distinguish raw mean 127.5 from
   translated-symbol median 0.5.

See [parent-regression.log](parent-regression.log) for complete output and
[parent-build.log](parent-build.log) for the build command and output.

## Why the old report said two

Git history contains the pre-N-10 test blob `456d9768...` and the committed
three-control blob `ddbfb3ac...`, but no two-control revision. No unreachable
commit supplies one. The original two-check observation was made against an
uncommitted intermediate working-tree test before the sparse-alphabet positive
control was added. That intermediate state has no immutable SHA or preserved
log. It is therefore retained only as a superseded historical statement, not
as the reproducible result of the committed regression. The commands and
results supporting this conclusion are in
[revision-investigation.log](revision-investigation.log).

## Fixed-head controls

At reviewed production head `baa51b3`:

```sh
make -C cpp iid restart
cpp/selftest/regression-iid-json.sh
cpp/selftest/regression-restart.sh
```

Both regressions exit 0. The IID output explicitly records:

```text
N-10 sparse-alphabet domains are distinguishable: raw 127.5, translated 0.5
regression-iid-json: PASS
```

Complete output is in [fixed-iid-json.log](fixed-iid-json.log) and
[fixed-restart.log](fixed-restart.log); build output is in
[fixed-build.log](fixed-build.log). The environment is recorded in
[environment.log](environment.log).

## Scope

A-1 is an evidence-count correction. It does not modify the N-10 repair,
regressions, reference output, R-1 status, supported-build boundary, or
production approval policy. The prior qualified result remains 19/19; strict
mode continues to fail only for the two documented macOS/arm64 upstream #155
reference differences.
