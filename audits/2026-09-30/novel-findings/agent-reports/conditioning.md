# Area report: conditioning (ea_conditioning, ea_transpose)

Upstream source at 87c104d. SCR = /tmp/claude-1000/-workspaces-SP800-90B-EntropyAssessment/cea834b3-fb2b-48af-9a72-01cd2c25f909/scratchpad. Work dir SCR/audit/work/conditioning/. Release binaries: SCR/audit/rel/cpp; ASan/UBSan binaries: SCR/audit/asan/cpp (ASAN_OPTIONS=detect_leaks=0). Extra builds I made (work dir only): `ndebug/ea_conditioning_ndebug` (release flags + `-DNDEBUG`), `ndebug/ea_conditioning_ndebug_asan` and `ndebug/ea_cond_nd_asan_rec` (ASan/UBSan + `-DNDEBUG`, the second with `-fsanitize-recover=address`).

The SP 800-90B text was not in the repo. I worked from the Jan 2018 text as I know it: §3.1.5.1.2 Output_Entropy steps 1-6 and §3.1.5.2 `h_out = min(Output_Entropy(...), 0.999·n_out, h'·n_out)` with h' measured per bit. The formula in the tool's own usage text matches that reading.

## 1. Scope actually covered

Read in full: `cpp/conditioning_main.cpp` (print_usage, inputLongDoubleOption, inputUnsignedOption, calculateEpsilon, computeEntropyWithPrecision, computeEntropyOfConditionedData, main), `cpp/transpose_main.cpp`, `cpp/shared/utils.h:read_file_subset`, `cpp/shared/most_common.h`, the JSON classes (`non_iid_test_case.h`, `non_iid_test_run.h`, `test_case_base.h`, `test_run_base.h`), `TestRunUtils.h:sha256_file`, and `restart_main.cpp` (column construction, to check that it matches ea_transpose). For dedup I used SCR/gh/all.md, AUDIT-2026-09-30.md and SCR/audit/reports/exclusion-map.md.

| Section | Algorithm/Test | Step | Code location | Matches? | Notes |
|---|---|---|---|---|---|
| 3.1.5.1.2 | Output_Entropy | 1: P_high = 2^-h_in | conditioning_main.cpp:185-186 | Yes | Rounded up (RNDU). ψ is non-decreasing in P_high, so rounding up is conservative. |
| 3.1.5.1.2 | Output_Entropy | 1: P_low = (1-P_high)/(2^n_in - 1) | :200-221 | Yes | 2^n_in-1 is checked for exactness (diff == 1), otherwise precision doubles. With tiny h_in, 1-P_high loses relative precision, but that direction is conservative (see §6). |
| 3.1.5.1.2 | Output_Entropy | 2: n = min(n_out, nw) | :581-582 | Yes, plus nw=min(nw,n_in) | Maintainer position #65/#87; conservative. |
| 3.1.5.1.2 | Output_Entropy | 3: ψ = 2^(n_in-n)·P_low + P_high | :237-247 | Yes | RNDU. Clamped to ≤1 at :265 (exact ψ ≤ 1 anyway). |
| 3.1.5.1.2 | Output_Entropy | 4: U = 2^(n_in-n) + sqrt(2n·2^(n_in-n)·ln2) | :273-285 | Yes | RNDU throughout. `2UL*n` is 64-bit on LP64 (LLP64 is out of scope per #155/#170). |
| 3.1.5.1.2 | Output_Entropy | 5: ω = U·P_low | :288 | Yes | Clamped to ≤1 at :300. The spec formula gives negative values when n_in-n is tiny (e.g. 1,1,1,1 gives -0.122), and the tool reports 0. |
| 3.1.5.1.2 | Output_Entropy | 6: -log2(max(ψ,ω)) | :308-317 | Yes | log2 RNDZ, so the result is conservative. Converted to long double with RNDN at :348, which the code admits can round up by at most half an ulp (measured ≤ 6.7e-20 relative). |
| 3.1.5.1.2 | vetted h_out | h_out = Output_Entropy | :637-642 | Yes | No 0.999 cap, which is correct for vetted. The IG D.K Res. 19 message is gated on h_in ≥ n_out+64 and > 0.999·n_out (PR #225). |
| 3.1.5.2 | non-vetted h_out | min(OE, 0.999·n_out, h'·n_out) | :657-667 | Yes | All three terms present. h' is per bit and is multiplied by n_out. 0.999L·n_out prints 255.7439999999999999946 (below 255.744). |
| 3.1.5.2 | h' from data (-i) | bitstring estimators (§6.3.1-6.3.10), MCV only if IID | :356-442 | Yes, same battery as `ea_non_iid -c` | Differential h' agrees to within 7e-15 (§2). Skip semantics (#255), inferred width (#254) and the tiny-input asserts (#261/#257/#264) are inherited; see §5. The `-c iid` option is not in the usage text. |
| 3.1.5.2 / 3.1.1 | conditioned dataset size | ≥ 1,000,000 | none | No check or warning at all | #255 family (§5). |
| — | CLI | n_in, n_out, nw ≥ 1; 0 < h_in ≤ n_in; 0 < h' ≤ 1 | :536-576 | Mostly | NaN, inf, ERANGE and trailing characters are rejected. strtoul base 0 accepts octal/hex and wraps negatives (COND-03). h' = 0 on the CLI is refused, though 0 is a legitimate value (§6). |
| — | JSON | report fields | :510-523, :673-692 | Partly | Provenance and track are misreported (COND-02, COND-04). |
| 3.1.4 / 3.1.2 | ea_transpose | column dataset = transpose of the 1000×1000 row matrix | transpose_main.cpp:103-110 | Yes | Same orientation as restart_main.cpp:461-470. Writes raw bytes, so width inference does not affect the output. |

## 2. Tests actually run

- **Vetted reference grid.** `ref.py` (venv mpmath 1.4.1, prec = 4·max(n_in,n_out,nw)+256) against `ea_conditioning -v … -o`. 1849 cases: n_in ∈ {1,2,3,8,16,63,64,65,128,256,512,1024,4096}; n_out ∈ {1, n_in/2, n_in, 2n_in, 64, 128, 256}; nw ∈ {n_out, n_in, 1, 2max}; h_in ∈ {1e-30, 1e-300, 0.5, 1, n_out, n_out+64, n_in, n_in-1e-9}. Result: no case where text or JSON exceeds the reference by more than 2^-63 relative. The maximum relative excess is 6.74e-20 (the admitted RNDN at :348). JSON exceeds the reference by at most 7.8e-20 absolute, only where the long double rounded to n_out (e.g. 4096/256/·/320 prints 256 against a true 255.99999999999999999992). 182 cases come out LOW, all with h_in ∈ {1e-30, 1e-300}, by up to 3.97 % (e.g. 2 1 1 1e-30: 3.2009e-31 vs 3.3333e-31). For realistic h_in the minimum relative error is -2.9e-20. The table is in `grid/grid.tsv`.
- **Non-vetted reference.** `ref_nv.py`: 131 cases (11 hand-picked, 120 random seed 11), reference min(OE, 0.999·n_out, h'·n_out). 0 flagged, max relative excess 1.87e-20.
- **Large n / tiny h_in.** 65536 256 256 300 takes 3.0 s. 2^20 takes 93 s, 2^21 106 s, 2^22 486 s, and 2^24 is still running after 120 s. 64 1048576 64 64 takes 123 s: the precision is driven by n_out although n ≤ n_in = 64. h_in = 1e-4900 retries to 27136 bits in 0.25 s and gives the correct value. 3.6e-4951 and 1e-4940 are refused (ERANGE). n_in or n_out ≥ 2^30-1 hits `assert(mpfr_get_emax() > maxval)` at :602 (SIGABRT). The NDEBUG build instead aborts with "GNU MP: Cannot allocate memory".
- **Hostile CLI (release + ASan/UBSan, 33 cases, `asanlogs/c*.log`).** No sanitizer report on any argument vector. Refused: 0 values, h_in > n_in, NaN, inf, 1e308, h' > 1, h' = -0, trailing space, empty string, 4294967296, missing and extra positionals, unknown option. Accepted with a changed value: `010` → 8, `0256` → 174, `0x200` → 512, `+16`, ` 16`, `-- -18446744073709551615` → 1 (COND-03). `512.0000000000000000001` becomes 512 (toward zero) and `1.0000000000000000001` becomes 1 (both conservative). `-o /nonexistent/dir/x.json` and `-o /dev/full` exit 0 without writing JSON (a shared pattern, see §4).
- **-i path, tiny and degenerate files (release + ASan).** empty file: refused. 1-byte 0x00/0x01: MCV `assert(len > 1)` because width inference gives 0 or 1 bits. 0xff (8 bits): LZ78Y assert in release; ASan heap-buffer-overflow at multi_mmc_test.h:38 (#257). 2-3 byte files: lrs/multi_mmc asserts, collision divide-by-zero under UBSan (#261/#264). **1,000 and 1,000,000 all-zero bytes: abort (COND-01).**
- **Differential h'** from `ea_conditioning -n … -i f` against `ea_non_iid -c -a -vvv f` on 10 files: tr8 125 kB, tr4, rand8_short, rand1_short, truerand_1bit, biased-random-bits, ringOsc/normal/pi first 125 kB, a 0.7-persistence Markov chain, and a noisy 20-tap LFSR. Largest disagreement is |Δ| ≤ 7.0e-15, in both directions. The source is the process-wide `fesetround(FE_TOWARDZERO)` at :459 (see §6).
- **ea_transpose.** Compared against a Python transpose for random 1000×1000 matrices (alphabets 256, 16, 2), all-zero and all-one: all MATCH, release and ASan. `-l 0/1/2` on a 3-block file: MATCH the right block. Short (999,999), long (1,000,001), 3,000,000 without -l, /dev/null, a missing output directory and /dev/full are refused (rc 255). `-l abc`, `-l ""`, `-l 1x`, `-l 2junk` are accepted (TRANS-01). A failure in the final `fclose` flush is ignored (TRANS-02). No sanitizer reports.
- **Thread count:** not applicable (no OpenMP on these paths).

## 3. CONFIRMED NOVEL findings

### COND-01 — An all-zero conditioned dataset (any length, including ≥1,000,000 bytes) crashes `ea_conditioning -n -i` instead of giving h' = 0; in an `-DNDEBUG` build it becomes a heap over-read plus a wild write

Category D (shipped build: assert abort) / B (NDEBUG build: memory-unsafe). Confidence HIGH on reproduction, MEDIUM on novelty (adjacent to #261 and #254). Affected executable: ea_conditioning. Source: conditioning_main.cpp:computeEntropyOfConditionedData:364-384 (no degenerate-data guard), shared/utils.h:read_file_subset:265-277 and :325 (width inferred as 0, so blen = len·0 = 0), shared/most_common.h:14 (`assert(len > 1)`). NDEBUG: non_iid/markov_test.h:48 reads `data[len-1]` = data[-1]; non_iid/lag_test.h:53 does `ringBuffers[S[0]]` on a malloc(0) buffer. SP 800-90B §3.1.5.2 (h' of the conditioned sequential dataset). Valid ≥1,000,000-sample case: **yes**. DIRECTION: none (no figure). The spec value is h' = 0 and h_out = 0; the tool returns no result.

**Root cause.** When the width is inferred, an all-zero file gets `word_size = 0`, so the bitstring has length 0. `ea_iid` and `ea_non_iid` stop in this state with "Symbol alphabet consists of 1 symbol. No entropy awarded…". `computeEntropyOfConditionedData` has no such guard and passes blen = 0 straight to `most_common`. A stuck-at-zero conditioner is exactly the failure this assessment should report as 0.

**Minimal reproduction.**
```
python3 -c "open('zero1e6.bin','wb').write(bytes(1000000))"
SCR/audit/rel/cpp/ea_conditioning -n 512 256 256 300 -i zero1e6.bin -o z.json; echo rc=$?
```
**Actual (run twice, identical).** `ea_conditioning: shared/most_common.h:14: double most_common(...): Assertion 'len > 1' failed.`, rc=134, no z.json. The same happens with `-c iid`. In the NDEBUG build (`g++ … -DNDEBUG conditioning_main.cpp`) the plain run prints `free(): invalid next size (fast)` and aborts. Under ASan+NDEBUG: `heap-buffer-overflow … READ of size 1 … markov_test.h:48`, then with recover enabled `lag_test.h:53:27: runtime error: store to address … with insufficient space` and `SEGV lag_test.h:53`. (The NDEBUG `-c iid` path runs only MCV and prints h' = -0, h_out = -0.)

**Expected.** Per §3.1.5.2 an all-zero bitstring has MCV p̂ = 1, so h' = 0 and h_out = min(…, 0·n_out) = 0. At minimum the tool should refuse with a JSON error, as the sibling executables do.

**Impact.** The shipped build cannot assess a stuck-at-zero conditioner: it core-dumps with no JSON, from a full-size dataset. A hardened (NDEBUG) downstream build writes out of bounds. It never produces a too-high figure.

**Deduplication proof.** all.md greps: "all zero", "all-zero" (only #195, a restart width assert), "0-bit" (#41, unrelated), "No entropy awarded", "alphabet consists" (#70 #96 #97 #123, all showing 2 or 256 symbols), "single symbol", "stuck", "blen", "len > 1" (#139, the -t truncation), "computeEntropyOfConditionedData" (#211, leaks only), "most_common.h" (#187 #270). None covers this. Related but distinct:
- #261/#257 are "no minimum-length validation" on tiny or repeat-free inputs. Here the input has 1,000,000 samples and passes any length check; the empty bitstring comes from inferring width 0, and the missing piece is the single-symbol guard that the other mains already have.
- #254 is about width narrowing changing figures. Its suggested fix (JSON recording or requiring a width) would not add this guard; ea_conditioning has no width argument at all.
- If the coordinator applies the "no length validation → #261" rule strictly, fold this into #261 as a new trigger. The ≥1e6 reproducer and the zero-width mechanism are the new facts.

**Suggested fix direction.** In computeEntropyOfConditionedData, return h' = 0 when `data.blen == 0` or the bitstring has a single value (mirror the non_iid_main.cpp alph_size==1 path), or refuse with errorLevel ≠ 0 and write JSON. Independently, stop inferring a zero width (use 8, or require a width).

**Regression test.** `ea_conditioning -n 512 256 256 300 -i zero1e6.bin -o z.json` exits 0 with `"h_p": 0` and `"h_out": 0` (or a non-zero errorLevel with a message); the ASan+NDEBUG build is clean.

### COND-02 — JSON records the `-i` file's name and SHA-256 when h' did not come from that file (CLI h' given too, or vetted mode)

Category C (assessment integrity / provenance). Confidence HIGH on behaviour, MEDIUM on severity. Affected executable: ea_conditioning. Source: conditioning_main.cpp:main:515-523 hashes and records whenever `-i` is present, before and regardless of the mode and argument count; :558-576 uses the CLI h' whenever argc == 5. SP 800-90B §3.1.5.2 (h' is the estimate of the conditioned sequential dataset). Valid ≥1,000,000-sample case: yes (any file). DIRECTION: TOO HIGH relative to the dataset named in the report. In the example, h_out is 253.44 against 213.63 from that file's own h' (+18.6 %). The size depends on the CLI h' the operator typed.

**Root cause.** The usage offers `[h' | -i filename]` as alternatives, but the parser accepts both. It silently prefers the CLI h' while `testRunNonIid.filename`/`sha256` still bind the file to the result. It also records a file in `-v` mode, where no data is used. Nothing in the JSON says where h_p came from.

**Minimal reproduction.**
```
python3 -c "import random;r=random.Random(8);open('cond8.bin','wb').write(bytes(r.randrange(256) for _ in range(125000)))"
ea_conditioning -n 512 256 256 300 -i cond8.bin -o measured.json
ea_conditioning -n 512 256 256 300 0.99 -i cond8.bin -o both.json
ea_conditioning -v 512 256 256 300 -i cond8.bin -o vet.json
```
**Actual (run twice, identical).**
- measured.json: `filename cond8.bin, sha256 efdc75dc…0859, errorLevel 0, h_p 0.8344735428256201, h_out 213.62522696335876`.
- both.json: the **same filename and sha256**, `errorLevel 0, h_p 0.99, h_out 253.44`, with no warning on stdout or in the JSON.
- vet.json: the same filename and sha256 attached to a vetted result that used no data.

**Expected.** Refuse `h'` together with `-i` (the usage shows them as alternatives) and refuse or ignore `-i` under `-v`, or at least record the source of h_p and leave the dataset hash out when the dataset was not used.

**Impact.** A reviewer reading the JSON (filename + SHA-256 + h_p, errorLevel 0) would take h_p as measured from that hashed dataset. The `commandline` field does show the positional 0.99, so the misattribution is detectable, but only by parsing argv. It requires contradictory input.

**Deduplication proof.** Greps: "sha256" (#182 #201-#206 #218 #247 #259 #260 #266 #267: build fixes, hang, subset hash, missing hash), "provenance" (none), "filename" (#1 #146 #167 #182 #2 #37: none about conditioning), "-i filename" (none), "both h" (#182 #233: unrelated). #218 ("Missing SHA256 hash in output for conditioning") added the hash; it is not about misattribution. #260 is the ea_non_iid `-l` subset hash, a different mechanism.

**Suggested fix direction.** In main, after getopt: `if (!vetted && argc == 5 && !inputfilename.empty())` → usage error; `if (vetted && !inputfilename.empty())` → usage error, or skip the hash. Add a JSON field for the h' source (cli/file, IID/non-IID track).

**Regression test.** The both.json command exits non-zero, or its JSON carries no sha256 plus an explicit `"hpSource": "commandline"`.

### COND-03 — Integer arguments parsed with `strtoul(…, 0)`: leading-zero decimals are read as octal (`0256` → 174), hex is accepted, and some negatives wrap to small positives

Category D (robustness, wrong accepted value). Confidence HIGH. Affected executable: ea_conditioning. Source: conditioning_main.cpp:inputUnsignedOption:104 (base 0, no sign check). SP 800-90B §3.1.5.1.2 (n_in, n_out, nw). Valid ≥1,000,000-sample case: n/a (CLI). DIRECTION: **TOO LOW** or refused. Output_Entropy, 0.999·n_out and h'·n_out are all non-decreasing in n_in, n_out and nw, and octal reading always gives a smaller value (checked numerically, below).

**Minimal reproduction (run twice, identical).**
```
ea_conditioning -v 512 0256 256 300   -> n_out = 174 … (Vetted) h_out = 174   (JSON "n_out" : 174.0) + "Full Entropy if … security strength is >= 174"
ea_conditioning -v 512 256 256 300    -> (Vetted) h_out = 255.9999999999999179961
ea_conditioning -v 0512 256 256 300   -> n_in = 330 … h_out = 255.9999999998022518626
ea_conditioning -n 512 0256 256 300 0.9 -> n_out = 174 … (Non-vetted) h_out = 156.6   (vs 230.4 with 256)
ea_conditioning -v 08 8 8 7           -> "Non-integer characters in n_in: '8'" (refused)
ea_conditioning -v -- -18446744073709551615 8 8 1 -> n_in = 1, h_out = -0
```
**Expected.** Decimal only. A leading zero should be decimal or refused, and a sign should be refused. #102 made these inputs integer-only, but the base-0 radix was never discussed.

**Impact.** Zero-padded inputs (e.g. from `printf %04d` in a lab script) silently assess a different, smaller conditioner. The JSON shows the misparsed value, so it is traceable. The result is conservative, never inflated.

**Deduplication proof.** Greps: "octal", "leading zero", "base 0", "strtoul", "inputUnsignedOption" all have 0 hits. #102 (non-integer values) is fixed and is a different defect.

**Suggested fix direction.** `strtoul(input, &end, 10)`, reject a leading '-' or '+', and check errno for ERANGE.

**Regression test.** `-v 512 0256 256 300` either reports n_out = 256 or is refused; `-- -18446744073709551615` is refused.

### COND-04 — Conditioning JSON hard-codes `"IID": false` and records neither the vetted/non-vetted mode nor the h' track

Category E (reporting). Confidence HIGH. Affected executable: ea_conditioning. Source: non_iid_test_run.h:94 (`const bool IID = false`, reused per the TODO at conditioning_main.cpp:509), :676 (`//tcOverallnonIid.vetted = vetted;` commented out), and the `-c iid` handling at :497-498 (not in the usage text). SP 800-90B §3.1.5.2 (h' by the IID track (MCV only) or the non-IID track). Valid ≥1,000,000-sample case: yes. DIRECTION: none in the numbers. The report under-describes the less conservative choice: `-c iid` gave h' = 0.9944 vs 0.8345 for the same file.

**Reproduction (run twice, identical).** `ea_conditioning -n -c iid 512 256 256 300 -i cond8.bin -o iid.json` prints h' = 0.9943846792929877942412, and the JSON has `"IID": false, "h_p": 0.9943846792929878`, with no vetted or track field.

**Expected.** The JSON should state the track used for h' (IID/MCV-only vs non-IID) and whether the component was treated as vetted.

**Deduplication proof.** Greps: `"IID"` (#182 is ea_non_iid JSON output, #186 is the `optarg=="iid"` compare, fixed), `vetted"` (none), "vetted" (#136/#168 example outputs only). No item about conditioning JSON fields.

**Fix direction.** A dedicated ConditioningTestRun that carries `vetted` and `hpTrack`.

**Regression test.** The JSON of the `-c iid` run contains `"hpTrack":"IID"` and `"vetted":false`.

### TRANS-01 — `ea_transpose -l` accepts non-numeric or partly numeric indices (`abc`, `""` → block 0; `1x` → block 1) and exits 0

Category D. Confidence HIGH. Affected executable: ea_transpose. Source: transpose_main.cpp:main:57-60, `strtoull(optarg, NULL, 0)` with no end-pointer check. glibc does not set EINVAL when there are no digits, so the `errno == EINVAL` test never fires, and errno is not reset. SP 800-90B §3.1.4.1/§3.1.2 (column dataset). Valid ≥1,000,000-sample case: yes. DIRECTION: none (the wrong restart block is transposed).

**Reproduction (run twice, identical).**
```
python3 -c "import random;r=random.Random(4);open('rows3.bin','wb').write(bytes(r.randrange(256) for _ in range(3*10**6)))"
ea_transpose -v -l abc rows3.bin c.col    # rc=0, "reading block 0"; c.col == transpose of block 0
ea_transpose -v -l 2junk rows3.bin c.col  # rc=0, "reading block 2"
ea_transpose -v -l "" rows3.bin c.col     # rc=0, "reading block 0"
```
**Expected.** Refuse, as ea_iid and ea_non_iid refuse an index not followed by ','.

**Impact.** A typo silently produces a column file for a different restart block than requested. LOW.

**Deduplication proof.** Greps: "strtoull(optarg", "non-numeric", "garbage", "trailing" (#204 is sha256 code). "ea_transpose" and "transpose_main" hit #118 #121 #162 #166, none about parsing. #260 covers `-l` offset overflow and whole-file hash, and #191 a `-l` segfault; both are different root causes. The `%ld` printing of the unsigned index is noted in #260 and is not re-reported.

**Fix direction.** Use an end pointer, reject `*end != '\0'` and `end == optarg`, and reset errno.

**Regression test.** `-l abc` and `-l 1x` exit non-zero.

### TRANS-02 — `ea_transpose` ignores the result of `fclose()`; if the final buffered flush fails, a truncated column file is left and the exit status is 0

Category D. Confidence HIGH (demonstrated with a file-size limit). Affected executable: ea_transpose. Source: transpose_main.cpp:112, `fclose(fp);` unchecked. Per-byte `fwrite` is checked, but the last 1,000,000 mod 4096 = 576 bytes are flushed only at fclose. SP 800-90B §3.1.2 (column dataset must be 1,000,000 samples). Valid ≥1,000,000-sample case: yes. DIRECTION: none. Downstream, the §5 tests on the column dataset run on 999,424 samples with only a stdout warning (the #255 family).

**Reproduction (run twice, identical).**
```
python3 -c "import random;r=random.Random(1);open('rows.bin','wb').write(bytes(r.randrange(256) for _ in range(10**6)))"
( trap '' XFSZ; ulimit -f 976; ea_transpose rows.bin t.col; echo rc=$? )   # rc=0
stat -c %s t.col   # 999424 = an exact prefix of the correct transpose
```
**Expected.** A non-zero exit and an error message when fclose (the final flush) fails.

**Impact.** It needs a full disk or quota at exactly the final flush, so the trigger is rare. The failure is silent. LOW.

**Deduplication proof.** Greps: "fclose" (#196 user code, #204/#206 the sha256_file double fclose), "truncated" (#34 #70 #125 #127 #139, the -t semantics), "partial write", "EFBIG", "No space", "ulimit": none.

**Fix direction.** `if (fclose(fp) != 0) { perror(...); exit(-1); }`. Optionally write to a temporary file and rename it.

**Regression test.** The ulimit command above exits non-zero.

## 4. Suspected findings needing more work / cross-area observations

- **Unchecked JSON write (all executables, probably the io area).** `-o /nonexistent/dir/x.json` and `-o /dev/full` exit 0 and silently produce no or partial JSON. `ofstream.open` and the write are unchecked in conditioning_main.cpp:550/569/688, and the same pattern is in iid_main.cpp and restart_main.cpp. all.md has no hit for "ofstream", "is_open" or "/dev/full". Left to the io owner as a shared root cause.
- **Ignored `sha256_file` return (all executables).** On failure (e.g. `-i <directory>`: "Error reading file for hashing: Is a directory") `hash[]` is left uninitialized and copied into `testRun.sha256` (conditioning_main.cpp:519-522; same at non_iid_main.cpp:179, iid_main.cpp:199, restart_main.cpp:247). This reads uninitialized stack memory into a std::string. In ea_conditioning the subsequent read fails, so no JSON is written; I found no path that emits it. Shared with io/#259 territory, so not claimed.
- **Precision/resource sizing.** `precision = 2·max(53, n_in, n_out, nw)` (:595-599) is driven by n_out even though n ≤ n_in (n_in = 64, n_out = 2^20 takes 123 s for a 64-bit computation). Runtime is superlinear in n_in (2^22 takes 486 s). n_in or n_out ≥ 2^30-1 hits an assert abort, and NDEBUG gets a GMP OOM abort. These parameters are far outside realistic conditioners, and maintainers chose full MPFR (#136), so I class this as expected-expensive, not a confirmed defect.

## 5. EXCLUDED AS ALREADY KNOWN

- `-i` path width inference: 7-bit values in bytes give h' = 0.8257 and h_out = 211.39. One byte with the MSB set flips the width to 8, giving h' = 0.5656 and h_out = 144.80 (+46 %). ea_conditioning has no width override at all. → **#254** (F02 already names the -c h'×n_out effect).
- `-i` path accepts conditioned datasets far below 1,000,000 bits with no warning at all (e.g. rand8_short = 80,000 bits), and skipped (−1) estimators are dropped silently. → **#255** family (and #238).
- `-i` on tiny files: MCV/LZ78Y/MultiMMC/LRS asserts (1-3 bytes) → **#261**. ASan heap-buffer-overflow multi_mmc_test.h:38 (1-byte 0xff) → **#257** (PR #268). UBSan collision divide-by-zero (2-3 bytes) → **#264**.
- `-i /dev/zero`, FIFO hash hang → **#259**.
- NaN from an unguarded estimator (MCV/collision/Markov) would be dropped by `std::min` in the h' fold and in `std::min(bound90B, statBound)` (h' = NaN would give h_out = min(OE, 0.999·n_out)). No producer is reachable in the shipped build: tiny inputs abort first, and NDEBUG + blen = 0 gives h' = 0 via `min(1.0, NaN)`. → **F13** family (no upstream item). Not re-reported.
- `ea_conditioning` h' forced to 1.0 / IID wrong → **#210** (fixed; the current code runs the bitstring battery, and the two-valued {0,255} file gives h' = 0, so #253 does not apply to this path).
- n = min(n_out, nw, n_in) → **#65** (maintainer position 29). Precision near full entropy / MPFR → **#128/#136**. nan h_out (4096 64 64 64 1) → **#168**: now gives 63, fixed by #136, though the issue is still open. IG D.K Res. 19 wording → **#225**. Non-integer n_in etc. → **#102**. `optarg=="iid"` → **#186**. The `2UL*n` width on LLP64 → **#155/#170** (unsupported platforms).

## 6. No-finding areas (attacked and held)

- **Output_Entropy numerics (1849 vetted and 131 non-vetted mpmath cases).** No figure is too high beyond the admitted half-ulp long-double RNDN (≤ 6.7e-20 relative). JSON double conversion runs under FE_TOWARDZERO, so it is never above the long double. Every MPFR rounding direction was checked analytically: ψ, U and ω use RNDU, log2 uses RNDZ, and P_high rounded up only lowers ω where ψ dominates. The retry recursion always terminates for n_in < 2^30-1, and 2^n_in-1 is exact before use.
- **Tiny h_in.** The result is too LOW by up to 4 % for h_in ≈ 1e-30 (and about 1e-8 for 1e-300). The cause: the retry checks only that P_high < 1, not the relative accuracy of 1-P_high. The direction is conservative and the case is irrelevant in practice.
- **Spec-formula artefacts.** For n_in-n ≈ 0 with small n, ω > 1 and the literal spec gives a negative h_out. The tool clamps to 0 and prints `-0` (a signed-zero cosmetic; the JSON shows `-0.0`). This is a spec limitation, not a code defect.
- **"Close to n_out/h_in" display.** When h_out rounds to n_out in long double, ε < 2^-64, which already meets the ≤2^-64 / h_in ≥ n_out+64 definitions. The full-entropy message cannot be triggered by rounding alone.
- **Non-vetted min.** All three terms are present. h' is per bit and is multiplied by n_out. 0.999L·n_out rounds downward.
- **`fesetround(FE_TOWARDZERO)` leaking into the h' estimators.** The deltas against `ea_non_iid -c` are ≤ 7e-15 over 10 datasets, well within the maintainers' 1e-10 cross-platform tolerance (position 23).
- **CLI refusals.** Refusals hold for NaN, inf, ERANGE, trailing garbage, out-of-range values, missing or extra arguments and unknown options. There were no sanitizer reports on 33 hostile argument vectors.
- **h' = 0 on the CLI** is refused (`h_p <= 0` → usage). It is conservative to refuse, but a legitimate h' = 0 must go through `-i`. Noted only.
- **ea_transpose core function.** The transpose is exact and orientation-consistent with restart_main.cpp for alphabets 2, 16 and 256 and for constant data. The size is enforced at exactly 1,000,000. `-l` in range reads the right block. Out-of-range, negative and overflowing `-l` values fail safely (fseek error or "empty"). Output-open and per-byte write errors are caught. Raw bytes are written, so there is no width or bits_per_symbol distortion. Clean under ASan/UBSan.
