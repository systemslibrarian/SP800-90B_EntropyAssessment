# MANIFEST — phase2-focused

Every committed file in this directory, with its source, SHA-256 and what it supports.

## Regeneration and exclusions

Generated `.bin` inputs are not committed. They regenerate byte-identically (verified); original hashes are in `PHASE2-WORKING-PRESERVATION/MANIFEST.md`:

```sh
python3 generators/gen_w.py w
python3 generators/gen_mission_e.py w e
python3 generators/gen_mission_h.py e
python3 generators/extract_spec_text.py NIST.SP.800-90B.pdf spec.txt   # PDF: see the parent README
```

Mutant builds: apply `repro/issue272/mutant*.diff` to upstream `87c104d` `cpp/non_iid_main.cpp`, or run `repro/issue272/repro.sh`, which clones upstream and applies them itself.

Not committed:

- packaging tools and file lists;

- the raw issue/PR snapshot (re-fetchable with `gh`);

- the `#272` API JSON;

- the local #272 draft, which differs from the filed text in one table cell: mutant 2 on `normal.bin` was filed as 4.10009578311034, exact value 4.1000957831103371.


## Files

| Path | Original path | Bytes | SHA-256 | Supports | Description |
|---|---|---:|---|---|---|
| `REPORT.md` | `git 3087ff4:audits/2026-09-30-phase2-focused-audit.md` | 12913 | `c662504e332fa21cad596d635e1fe2fdd9c48cdfefba0f2d531a65e0c0015176` | NOVEL-01…NOVEL-03, Missions A–J | The complete phase-2 focused audit report, byte-identical to the committed version. |
| `generators/extract_spec_text.py` | `PHASE2-WORKING-PRESERVATION/generators/extract_spec_text.py` | 395 | `0c60be11184119299b91e6cd83f5fcb2b73792cc1c07b78d091e25268854689c` | all | Regenerates spec.txt from the SP 800-90B PDF (pypdf). |
| `generators/gen_mission_e.py` | `PHASE2-WORKING-PRESERVATION/generators/gen_mission_e.py` | 979 | `e8a0f6ddb28a9e4f58530f8c807e14c7e92628e0cca375fdd4e5a3bf18ad534e` | Mission E | Regenerates the 15 Mission E datasets byte-for-byte. |
| `generators/gen_mission_h.py` | `PHASE2-WORKING-PRESERVATION/generators/gen_mission_h.py` | 498 | `73b35b313e716914cf15218408ee7ae38f67561f2515108a695a457ee2c95a9b` | Mission H | Regenerates the 3 Mission H inputs byte-for-byte. |
| `generators/gen_w.py` | `PHASE2-WORKING-PRESERVATION/generators/gen_w.py` | 1580 | `e79762b98fca695f07f75a225e7486ad1b6c3d9fd876b565e07d1d852187424b` | Missions A/C, N-01, R-1 | Regenerates the 16 w/*.bin datasets byte-for-byte. |
| `logs/evidence/build_asan_ubsan.log` | `PHASE2-WORKING-PRESERVATION/evidence/logs/build_asan_ubsan.log` | 1129 | `3e0c18c000faae9119b8b474882db333ee58e51240ba2252d66aec29fe2022f2` | sanitizers | ASan/UBSan build command lines. |
| `logs/evidence/build_release.log` | `PHASE2-WORKING-PRESERVATION/evidence/logs/build_release.log` | 933 | `d1bd619e72093fce65696623079d05200d990fe78182e262783188f4175c1896` | baseline | Stock Makefile build log. |
| `logs/evidence/json/a1.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/a1.json` | 436 | `4f3a70ad5ad06bb09fdde0fc8b717a447f6ea6fb5591fc4eab8fa05901fbc4b5` | Sanitizer matrix | ASan/UBSan build, ea_restart -i width error (R-3). |
| `logs/evidence/json/a2.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/a2.json` | 418 | `e96373bd6ff5710ca24e786ef61aaaf83b0be55778d6d9e9c5627dcaabac3f4f` | Sanitizer matrix | ASan/UBSan build, ea_restart -n missing file. |
| `logs/evidence/json/a3.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/a3.json` | 3223 | `e44685e591400782449bb0dd1a50f2b4821cee226c3ebec3604289f8d76cdb20` | Sanitizer matrix | ASan/UBSan build, ea_iid on iid_p002.bin: clean. |
| `logs/evidence/json/empty.bin.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/empty.bin.json` | 490 | `a71b6e2ec4d0ec53aefc42a52c3a87ad28f95a0b0e57408f49d482e16064dbc7` | Mission A | ea_restart on an empty file: errorLevel -1, message with literal "%s". |
| `logs/evidence/json/h.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/h.json` | 507 | `b2553991ab8f8f0700fa877d31fbf57345a92d008a0356617eb9109cf6b47d77` | N-04 (rediscovery) | JSON left by the ea_restart H_I fuzz run. |
| `logs/evidence/json/iid_c_r8.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/iid_c_r8.json` | 3184 | `a5c06a8bbd6096bbe50c23b5434e7bff2c6a6ea9ca8b97d38934b806a3926171` | NOVEL-02 | ea_iid -c JSON: hOriginal 8.0 placeholder (never computed). |
| `logs/evidence/json/iid_p002.1.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/iid_p002.1.json` | 3228 | `8cac7522a1a1d65fe685e93b96f5bf699eb541791d57907a2153632c5c1795d7` | N-01 (independent rediscovery), NOVEL-02 | ea_iid JSON on Bernoulli(0.002045): all IID tests pass (m=1 chi-square), hBitstring 1.0 placeholder. |
| `logs/evidence/json/iid_p002.2.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/iid_p002.2.json` | 3227 | `ed7830585053b05e33610d67d7d1815584b462fced070219aa3524fbbd234e1c` | N-01 (independent rediscovery), NOVEL-02 | Second ea_iid run, same file: same verdict. |
| `logs/evidence/json/ne.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/ne.json` | 445 | `ef32b1133fedc301d8adf466d2e6c2e3214cbc94812112807ef9bffedbf708db` | N-06 | ea_restart -n on a missing file: sha256 field is uninitialised stack bytes. |
| `logs/evidence/json/nei.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/nei.json` | 363 | `641afc255a71381d7bab868361e54b46810ade39855eee6832d2b09de1181455` | R-3, N-06 | ea_restart -i on a missing file: errorLevel 0. |
| `logs/evidence/json/rst_i.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/rst_i.json` | 5539 | `3d756d5acd017874777c19518de95256648e24f120479a2d89b4fa23b41cfc82` | NOVEL-03 | ea_restart -i JSON: 6 permutation blocks labelled iteration 0,1,2,0,1,2 (row/column untagged); mean/median 0.0 (N-10). |
| `logs/evidence/json/s1001.bin.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/s1001.bin.json` | 536 | `79ad2c78a6ceb77930716dee91238b797109f61caba181184d2b3c6ebc368822` | Mission A | ea_restart 1000×1001: refused. |
| `logs/evidence/json/s999.bin.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/s999.bin.json` | 532 | `085353da7eacf7974d3e175b46ca39d09f900d26777ec06cfd8b72ab50603d13` | Mission A | ea_restart 999×1000: refused. |
| `logs/evidence/json/w4i.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/w4i.json` | 435 | `7f855faa28e7f1d7d5057c7830c685fc180bd0bce61f424257992f621ff6ea00` | R-3 | ea_restart -i on a width error: errorLevel 0 while exit 255. |
| `logs/evidence/json/w4n.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/w4n.json` | 555 | `613960c58876166a9722ecb35ca557810ace1e6ca61834d1ccc59fd57a04d5b3` | R-3 (control) | ea_restart -n on the same width error: errorLevel -1. |
| `logs/evidence/json/zero.bin.json` | `PHASE2-WORKING-PRESERVATION/evidence/json/zero.bin.json` | 524 | `cc39301ac1e937f67de41f090c94350a186e7da48bccb75333b7cde237fb8820` | Mission A | ea_restart constant matrix: "1 symbol, no entropy awarded". |
| `logs/evidence/restart_HI_fuzz.log` | `PHASE2-WORKING-PRESERVATION/evidence/logs/restart_HI_fuzz.log` | 513 | `9321fbaa24ab055e327e344d6328cfb39ee80d1ce653db9389ff5924403200ef` | N-04 (rediscovery) | ea_restart H_I fuzz (nan → SIGSEGV). |
| `logs/evidence/selftest_baseline.log` | `PHASE2-WORKING-PRESERVATION/evidence/logs/selftest_baseline.log` | 638 | `0654506107a2fb692f5037723e85a6db8abf52c5783906f0fcd7e476687487af` | baseline | Upstream selftest on clean 87c104d (max delta ≤ 1.0e-13). |
| `logs/issue272/mutant1_outputs/biased-random-bits.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/biased-random-bits.res` | 3785 | `7e286ae56bf074493b2f00d4b48864dcbc2d2737c0dce6667f11ae5da1928483` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/biased-random-bytes.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/biased-random-bytes.res` | 6313 | `6fbd9b7f7ebfc48f0eab9aef7ad8fd37d2c24763470a3df8411165e9ef594b46` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/data.pi.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/data.pi.res` | 3766 | `a23b503cf2bf164244b47f9d73fbf5f8fd84e185bcce50d3eee4be9abd648c8d` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/normal.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/normal.res` | 6340 | `53dc7927a81b6d3895a90fd71e907144ac358af63ca09118851dda44ed8120a8` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/rand1_short.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/rand1_short.res` | 3795 | `f5f45653327c3e5dfb87dd4af5483270a8efbd11172192baf8771c52f2c0231a` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/rand4_short.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/rand4_short.res` | 6333 | `81bb6dde41b09c93c8ddee963506f0dc9aba073a5cc3294e3a1ca98f471913ee` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/rand8_short.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/rand8_short.res` | 6324 | `282065414bf544c91f0b56396683bbfb94e4f22bf23e7b6ddae4781ad173f671` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/ringOsc-nist.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/ringOsc-nist.res` | 3758 | `c1464dd4df01a29c837fd57de529a74e461a8fc72a6c8e315240c4793622557a` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/truerand_1bit.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/truerand_1bit.res` | 3762 | `20e9a5fbd5fb79513425e815f2d32473d3f05a3ff2f14aee4d7996933ed1d01c` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/truerand_4bit.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/truerand_4bit.res` | 6334 | `bfed57547433920a3f0d72cbab219d4d1594c357c085b6c5369c148ccdb866a3` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant1_outputs/truerand_8bit.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1_outputs/truerand_8bit.res` | 6341 | `6fe0566835342ce157322b82508a37c0769a5efb030fa3deff16a9e101960d9a` | NOVEL-01 | ea_non_iid -vv output from the mutant1 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/biased-random-bits.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/biased-random-bits.res` | 3766 | `abb9faf8dca88717ea4a41bbee5edbf52b3a7621fd616d786e511050c74f722a` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/biased-random-bytes.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/biased-random-bytes.res` | 6313 | `a5ab4d101ded8df0b2f8d9eb08b044aa501a7dda8d5c0466cab96e4608d19ed9` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/data.pi.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/data.pi.res` | 3748 | `41680dfd237ab2abb41288e42085345aad9e72ddbb7bc02cc9b7f2be21c659b6` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/normal.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/normal.res` | 6341 | `db62cb5f9ea6f55bb49cdaf078eaf4d4e7c7e1ad363285036f22fa35e5e8e286` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/rand1_short.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/rand1_short.res` | 3777 | `7a4001a1d9f84cd705363fd898a0605682df61dd51ffcfba05571b1929c2282c` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/rand4_short.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/rand4_short.res` | 6333 | `022099c9aaa1ef708da7a56adf92cf32bac508a9573afc9a3132036b1c9c8bb5` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/rand8_short.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/rand8_short.res` | 6324 | `42d91aa4610f4c7f320c50388b01f092f4180a5db4efcfabbb744517017e29cf` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/ringOsc-nist.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/ringOsc-nist.res` | 3740 | `a5e03cb9b23d34554f539de3d48cf166f5cc39055191097d0949d2af715e9ff8` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/truerand_1bit.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/truerand_1bit.res` | 3744 | `d9931e45e5337acce55aa9444aa028729b85ca8274e1b4d12f48b9bfc198347b` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/truerand_4bit.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/truerand_4bit.res` | 6334 | `471d2966ea53ae3adf42eb60df2bafaf41d4ea5fa953039da400a552cd2a2a03` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/mutant2_outputs/truerand_8bit.res` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2_outputs/truerand_8bit.res` | 6340 | `e28d2190b8b2a5b4e6da0349cddad6a4c9a0cc9d56026349133fbe9c984645a7` | NOVEL-01 | ea_non_iid -vv output from the mutant2 build (changed Assessed line). |
| `logs/issue272/scratch_mutant1_selftest.log` | `PHASE2-WORKING-PRESERVATION/issue272/scratch_mutant1_selftest.log` | 594 | `46bd6ec89cc65d29bd1e87022d0a8ac41681c2ea286408a7cc97d177b7ded619` | NOVEL-01 | Selftest output under mutant 1 (identical to baseline, exit 0). |
| `logs/issue272/scratch_mutant2_selftest.log` | `PHASE2-WORKING-PRESERVATION/issue272/scratch_mutant2_selftest.log` | 594 | `46bd6ec89cc65d29bd1e87022d0a8ac41681c2ea286408a7cc97d177b7ded619` | NOVEL-01 | Selftest output under mutant 2 (identical to baseline, exit 0). |
| `logs/oracle/bijection/out_bij01_1000000.bin_1.txt` | `PHASE2-WORKING-PRESERVATION/oracles/bijection/out_bij01_1000000.bin_1.txt` | 496 | `2cbb5bd0be1e94ea48e59c75dc290d3f47669914de4ef459438b2750c7bc16ef` | Mission E (bijection; #253 confirm) | Filtered ea_non_iid -vv output. |
| `logs/oracle/bijection/out_bij17_1000000.bin.txt` | `PHASE2-WORKING-PRESERVATION/oracles/bijection/out_bij17_1000000.bin.txt` | 496 | `83d2dc0f944af383030105ce2d5c92ead453c9e1741a1ac822f89ca0a043cdbc` | Mission E (bijection; #253 confirm) | Filtered ea_non_iid -vv output. |
| `logs/oracle/bijection/out_bij17_1000000.bin_8.txt` | `PHASE2-WORKING-PRESERVATION/oracles/bijection/out_bij17_1000000.bin_8.txt` | 496 | `83d2dc0f944af383030105ce2d5c92ead453c9e1741a1ac822f89ca0a043cdbc` | Mission E (bijection; #253 confirm) | Filtered ea_non_iid -vv output. |
| `logs/oracle/bijection/out_two0255_1000000.bin_8.txt` | `PHASE2-WORKING-PRESERVATION/oracles/bijection/out_two0255_1000000.bin_8.txt` | 496 | `83d2dc0f944af383030105ce2d5c92ead453c9e1741a1ac822f89ca0a043cdbc` | Mission E (bijection; #253 confirm) | Filtered ea_non_iid -vv output. |
| `logs/oracle/oracle_compare_L1e6.log` | `PHASE2-WORKING-PRESERVATION/oracles/oracle_compare_L1e6.log` | 257 | `1d85641a6a673f8781a3a347b2a24732b18bc4d0f3e14da436f2b0c49393147c` | Mission E | Oracle vs tool at L=10⁶: 0 mismatches (worst relative difference 3.7e-11). |
| `logs/oracle/oracle_compare_L64_L4096.log` | `PHASE2-WORKING-PRESERVATION/oracles/oracle_compare_L64_L4096.log` | 488 | `e9b3e46f7ce3191ea8f3425ae9fe748e8ca492e901432a432d45583787dbd63d` | Mission E | Oracle vs tool at L=64 and 4096: 0 mismatches. |
| `logs/oracle/oracle_worked_examples.log` | `PHASE2-WORKING-PRESERVATION/oracles/oracle_worked_examples.log` | 769 | `108d1fa9a6149fc1a6ef1b899b1a086f04efcda96a1d9733b3857e0be3ae688a` | Mission E | Worked-example validation output (all printed spec values reproduced). |
| `notes/PROGRESS.md` | `PHASE2-WORKING-PRESERVATION/notes/PROGRESS.md` | 2670 | `b5df131e999d1425492aac4927652cd8e8dcbcdb7b0d9ecb8fc51d8e709c9ff9` | phase-2 audit | Working notes, including the pause/resume point and the parallel-audit exclusions. |
| `oracle/cmp.py` | `PHASE2-WORKING-PRESERVATION/oracles/cmp.py` | 1575 | `708c3a91e105708f16e83efbbe267aefc3917776a057ca6a917bb18ab3cb799d` | Mission E | Diffs ea_non_iid -vv intermediate values against oracle.py. Edit its hard-coded S= path before reuse. |
| `oracle/oracle.py` | `PHASE2-WORKING-PRESERVATION/oracles/oracle.py` | 6690 | `32c4827228d2e2413a053401d5183d5e3d5d0304a8d5070d59bd3dee1b26ce0f` | Mission E | PDF-derived oracles for MCV/Markov/t-Tuple/LRS/Lag/LZ78Y incl. P_global′/P_local (x₁₀). |
| `oracle/oracle_worked_examples.py` | `PHASE2-WORKING-PRESERVATION/oracles/oracle_worked_examples.py` | 1231 | `f30a667a18d6bbb0542386b887c7460f90b6a37127f19894cc0174411245660c` | Mission E | Validates oracle.py on the SP 800-90B worked examples. |
| `repro/issue272/issue272_posted_body.md` | `PHASE2-WORKING-PRESERVATION/issue272/issue272_posted_body.md` | 5379 | `313d03e972fdc1e1201ab795bf6f14b3bea140703b3b2b4a56fad3f1a98417ec` | NOVEL-01 / #272 | Body of upstream issue #272 exactly as filed. |
| `repro/issue272/mutant1.diff` | `PHASE2-WORKING-PRESERVATION/issue272/mutant1.diff` | 391 | `c5bf1f2fbf83e5dae5428bb5892dd3e28e20f68320c997d95cd6ddc3d5628f5f` | NOVEL-01 | Mutant 1: n×H_bitstring term removed. |
| `repro/issue272/mutant2.diff` | `PHASE2-WORKING-PRESERVATION/issue272/mutant2.diff` | 452 | `3ee5b45d24c0b38cd0671dcc1ee115a81db48e1397fd1427f8c74d1d9b0cc57b` | NOVEL-01 | Mutant 2: H_original fold removed. |
| `repro/issue272/refdata_edit.diff` | `PHASE2-WORKING-PRESERVATION/issue272/refdata_edit.diff` | 625 | `8e6882cc34f874dcfd02a3182bbc988af6c7e44a06feafa5b70bcec379b7ae98` | NOVEL-01 | First-file refdata edit used to show the exit status comes from the last file only. |
| `repro/issue272/repro.log` | `PHASE2-WORKING-PRESERVATION/issue272/repro.log` | 4246 | `0021e2e1513c3e8c7bd7b19a208f181f9351a40f1a138acdb3a3a0be396f0b1c` | NOVEL-01 / #272 | Full trace of repro.sh (all selftests exit 0 while the Assessed figures change). |
| `repro/issue272/repro.sh` | `PHASE2-WORKING-PRESERVATION/issue272/repro.sh` | 1356 | `1fe90154c6e732f4b03033a78cce7c581512d5c815261a8b1cbb83818621d85f` | NOVEL-01 / #272 | Exact script run on a fresh upstream clone: baseline, mutant 1, mutant 2, first-file refdata edit. |
| `repro/rtime.py` | `PHASE2-WORKING-PRESERVATION/tools/rtime.py` | 352 | `69bc052a2ecffd3d97484327ee8ce50013ab19c7bd7be72ed8d85a00db21ca5f` | Mission H | Wall-time / child max-RSS wrapper for the resource runs. |

Total files (excluding this manifest): 67.
