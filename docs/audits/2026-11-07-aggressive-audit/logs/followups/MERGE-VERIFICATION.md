# Merge verification record (2026-11-08)

master before: 04c1ccc

## merge 1
commit/tree: 

## merge 2
commit/tree: 

## merge 3
commit/tree: 

4c62713 Merge branch 'fix/restart-notrun'
db1d67c Merge branch 'fix/openssl-pin'
61dbe9b Merge branch 'fix/stale-report'
7d647e6 fix/openssl-pin: read grep's status inline so the dead-guard detector sees it read
ccaab67 fix/openssl-pin: no pipe from the verification grep (dead-guard class D); live instrument count 87 -> 88 in both inventories
745b396 fix(AA-04): ea_restart dropped a declined row or column estimator silently, and no field carried min(H_r, H_c, H_I)
c8b0bc6 fix(PROV-01): claim the -o target from the prescan, so an option error before -o cannot leave a stale success
b62336b fix(PROV-15): the OpenSSL pin was defeated by include/link order

## merge1
f47e0326d98a5825 ea_non_iid
af4ed62abbf2455b ea_iid
abf9126bec7af49f ea_restart
selftest rc=1 selftest: FAIL (2 of 11 files): biased-random-bytes.bin ringOsc-nist.bin
platform-delta checker rc=0
regression-271.sh rc=0 regression-271: PASS
regression-272.sh rc=0 regression-272: PASS
regression-chisquare.sh rc=0 regression-chisquare: PASS
regression-deadguard.sh rc=1 regression-deadguard: FAIL (the flag set moved; rebase deliberately if
    ^ ENVIRONMENTAL, not the merge: the detector walks the repo root and the four fix worktrees under .claude/worktrees/ were full checkouts (200 flags). After `git worktree remove` of the four: PASS, 40 flags (merge1/regression-deadguard-after-worktree-removal.log).
regression-docs.sh rc=0 regression-docs: PASS
regression-estimator-guards.sh rc=0 regression-estimator-guards: PASS
regression-iid-failclosed.sh rc=0 regression-iid-failclosed: PASS
batch time budget reached before regression-iid-json.sh
regression-iid-json.sh rc=0 regression-iid-json: PASS
regression-input-identity.sh rc=0 regression-input-identity: PASS (replacement rejected as result identi
regression-minsize.sh rc=0 regression-minsize: PASS
regression-multimmc.sh rc=0 regression-multimmc: PASS
regression-nonregular.sh rc=0 regression-nonregular: PASS (0 skipped)
regression-notrun.sh rc=0 regression-notrun: PASS
regression-option-order.sh rc=0 regression-option-order: PASS
regression-output-aliasing.sh rc=0 regression-output-aliasing: PASS
regression-output.sh rc=0 regression-output: PASS (3 skipped)
regression-outside-battery.sh rc=0 regression-outside-battery: PASS
regression-platform-deltas.sh rc=0 regression-platform-deltas: PASS
regression-restart.sh rc=0 regression-restart: PASS
regression-selftest-inventory.sh rc=0 regression-selftest-inventory: PASS
regression-stale-report.sh rc=0 regression-stale-report: PASS (29 checks)
regression-subset.sh rc=0 regression-subset: PASS
regression-width.sh rc=0 regression-width: PASS
regression-workflows.sh rc=0 regression-workflows: PASS
regression-constants.sh rc=0 regression-constants: PASS (10 constants, the C22c digest, the sweep, 

## merge2
f47e0326d98a5825 ea_non_iid
af4ed62abbf2455b ea_iid
abf9126bec7af49f ea_restart
selftest rc=1 selftest: FAIL (2 of 11 files): biased-random-bytes.bin ringOsc-nist.bin
platform-delta checker rc=0
regression-271.sh rc=0 regression-271: PASS
regression-272.sh rc=0 regression-272: PASS
regression-chisquare.sh rc=0 regression-chisquare: PASS
regression-deadguard.sh rc=0 regression-deadguard: PASS (flag set unchanged)
regression-docs.sh rc=0 regression-docs: PASS
regression-estimator-guards.sh rc=0 regression-estimator-guards: PASS
regression-iid-failclosed.sh rc=0 regression-iid-failclosed: PASS
regression-iid-json.sh rc=0 regression-iid-json: PASS
regression-input-identity.sh rc=0 regression-input-identity: PASS (replacement rejected as result identi
regression-minsize.sh rc=0 regression-minsize: PASS
regression-multimmc.sh rc=0 regression-multimmc: PASS
regression-nonregular.sh rc=0 regression-nonregular: PASS (0 skipped)
regression-notrun.sh rc=0 regression-notrun: PASS
regression-openssl-pin.sh rc=0 regression-openssl-pin: PASS
regression-option-order.sh rc=0 regression-option-order: PASS
regression-output-aliasing.sh rc=0 regression-output-aliasing: PASS
regression-output.sh rc=0 regression-output: PASS (3 skipped)
regression-outside-battery.sh rc=0 regression-outside-battery: PASS
regression-platform-deltas.sh rc=0 regression-platform-deltas: PASS
regression-restart.sh rc=0 regression-restart: PASS
regression-selftest-inventory.sh rc=0 regression-selftest-inventory: PASS
regression-stale-report.sh rc=0 regression-stale-report: PASS (29 checks)
regression-subset.sh rc=0 regression-subset: PASS
regression-width.sh rc=0 regression-width: PASS
regression-workflows.sh rc=0 regression-workflows: PASS
regression-constants.sh rc=0 regression-constants: PASS (10 constants, the C22c digest, the sweep, 
harness-inventory-mutation-test rc=0 harness-inventory-mutation-test: PASS

## merge3
9379546d6046e716 ea_non_iid
af4ed62abbf2455b ea_iid
7dff23f345ae53d1 ea_restart
selftest rc=1 selftest: FAIL (2 of 11 files): biased-random-bytes.bin ringOsc-nist.bin
platform-delta checker rc=0
regression-271.sh rc=0 regression-271: PASS
regression-272.sh rc=0 regression-272: PASS
regression-chisquare.sh rc=0 regression-chisquare: PASS
regression-deadguard.sh rc=0 regression-deadguard: PASS (flag set unchanged)
regression-docs.sh rc=0 regression-docs: PASS
regression-estimator-guards.sh rc=0 regression-estimator-guards: PASS
regression-iid-failclosed.sh rc=0 regression-iid-failclosed: PASS
regression-iid-json.sh rc=0 regression-iid-json: PASS
regression-input-identity.sh rc=0 regression-input-identity: PASS (replacement rejected as result identi
regression-minsize.sh rc=0 regression-minsize: PASS
regression-multimmc.sh rc=0 regression-multimmc: PASS
regression-nonregular.sh rc=0 regression-nonregular: PASS (0 skipped)
regression-notrun.sh rc=0 regression-notrun: PASS
regression-openssl-pin.sh rc=0 regression-openssl-pin: PASS
regression-option-order.sh rc=0 regression-option-order: PASS
regression-output-aliasing.sh rc=0 regression-output-aliasing: PASS
regression-output.sh rc=0 regression-output: PASS (3 skipped)
regression-outside-battery.sh rc=0 regression-outside-battery: PASS
regression-platform-deltas.sh rc=0 regression-platform-deltas: PASS
regression-restart.sh rc=0 regression-restart: PASS
regression-restart-notrun.sh rc=0 regression-restart-notrun: PASS
regression-selftest-inventory.sh rc=0 regression-selftest-inventory: PASS
regression-stale-report.sh rc=0 regression-stale-report: PASS (29 checks)
regression-subset.sh rc=0 regression-subset: PASS
regression-width.sh rc=0 regression-width: PASS
regression-workflows.sh rc=0 regression-workflows: PASS
regression-constants.sh rc=0 regression-constants: PASS (10 constants, the C22c digest, the sweep, 
harness-inventory-mutation-test rc=0 harness-inventory-mutation-test: PASS

