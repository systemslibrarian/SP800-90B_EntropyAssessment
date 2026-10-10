# Baseline checkpoint

- Start time/date: 2026-10-09, America/New_York.
- Checkout: `/Users/gmcas/repos/SP800-90B_EntropyAssessment`.
- Branch: `master`.
- Starting SHA: `106d31c4b010d9cd4ae94c0db14d9dcf11aeb353`.
- Worktree at start: clean; branch matched `origin/master` after fetch.
- Fork remote: `https://github.com/systemslibrarian/SP800-90B_EntropyAssessment.git`.
- Fetched fork SHA: `106d31c4b010d9cd4ae94c0db14d9dcf11aeb353`.
- Upstream remote: `https://github.com/usnistgov/SP800-90B_EntropyAssessment.git`.
- Fetched upstream SHA: `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`.
- Common ancestor: `87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289`.
- Divergence count (`upstream/master...master`): upstream 0, fork 55.
- Host: macOS 26.6.2 (25G83), Darwin 25.6.0, arm64, Apple M5.
- Compiler: Apple clang 21.0.0 (`clang-2100.3.34.2`).
- Build tools: GNU Make 3.81, Git 2.54.0 (Apple Git-157), Python 3.14.7,
  Perl 5.34.1.
- Dependencies used: jsoncpp 1.9.8, libdivsufsort 2.0.1, libomp 23.1.2,
  OpenSSL 3.6.4, and macOS SDK bzip2 1.0.8.
- Release compiler flags: C++11, OpenMP, `-O2`, and `-ffloat-store`, plus
  Homebrew include/library paths. Apple clang warns that it ignores
  `-ffloat-store`.
- Repository `AGENTS.md`: none found.
- Adjacent TruePad checkout: accessible at `/Users/gmcas/repos/TruePad`, SHA
  `186a3376deca2e1608dbd1c8114c84113b048091`, with pre-existing untracked
  review documents; treated read-only.

The fork documentation says TruePad ships the patched fork, while the current
TruePad qualification implementation and lock file require upstream commit
`87c104d`. This conflict is an audit subject, not resolved by assumption.

The 55-commit fork delta touches 632 paths and is dominated by preserved audit
evidence and documentation. Relevant runtime differences are the macOS
Makefile support, intake/report/file guards, estimator and IID corrections,
restart error handling, and 14 discovered regression scripts catalogued by the
canonical tracker. Upstream has no commit after the merge base in the fetched
history, so there is no upstream-only source change to merge or audit.

TruePad actually invokes `ea_non_iid` for an initial non-IID estimate and
`ea_restart -n` for restart testing. It does not invoke `ea_iid`,
`ea_conditioning`, or `ea_transpose`. The first three supported repository
programs (`ea_non_iid`, `ea_iid`, and `ea_restart`) were nevertheless built
explicitly as required by this audit.

Three detached disposable worktrees were used under
`/tmp/sp80090b-audit-20261009.5WcSLl/`: `source` (release fork), `asan`
(ASan/UBSan fork), and `upstream-tools` (exact upstream). Existing user-owned
worktrees were not altered. Generated binary fixtures and experimental
executables remained under that temporary root.

The final fetch at report sealing resolved the same fork and upstream SHAs,
merge base, branch, and clean production-source state as the start. The only
new checkout path was this untracked audit directory. The adjacent TruePad
checkout still had exactly its five pre-existing untracked review documents
and no tracked modification.

The preserved official January 2018 PDF is 1,043,696 bytes with SHA-256
`9b0dd77131ade3617a91cd8457fa09e0dc354c273bb2220a6afeaca16e5defe7`.
The official CSRC potential-errata PDF was retrieved from its current URL: one
page, last updated 2025-05-29, 107,606 bytes, SHA-256
`af99ae20161aeed6e8eab88badf650e08c9f5ac455b71cf1095c289c104a5128`.
Its own metadata/text says the proposed corrections are not official changes.
