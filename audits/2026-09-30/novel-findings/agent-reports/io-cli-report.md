# Area report: io-cli-report (shared input, CLI and report layer, all five executables)

Upstream `87c104d`. Release tree `SCR/audit/rel/cpp` (Makefile flags), ASan/UBSan tree `SCR/audit/asan/cpp`. Work files: `SCR/audit/work/io/`. All reproduction commands below are written as run from the upstream `cpp/` directory with the NIST samples in `../bin/`. Nothing in the git repo was modified; no `gh` calls were made.

## 1. Scope actually covered

Read in full: `shared/utils.h` (`read_file_subset`, `read_file`, width inference, symbol translation / map-down, bitstring conversion, `calc_stats`, `sum`, `FYshuffle`, `recreateCommandLine`), `shared/TestRunUtils.h` (`getCurrentTimestamp`, `sha256_file`, `sha256_hash_string`), `shared/test_run_base.h`, `shared/test_case_base.h`, `shared/TestCase.h`, `shared/most_common.h`, `iid/iid_test_run.h`, `iid/iid_test_case.h`, `iid/permutation_test_result.h`, `iid/permutation_tests.h` (`populateTestCase`, length types), `non_iid/non_iid_test_run.h`, `non_iid/non_iid_test_case.h`, and every `main`: `non_iid_main.cpp`, `iid_main.cpp`, `restart_main.cpp` (incl. `simulateBound`/`simulateCount` as far as H_I intake reaches them), `conditioning_main.cpp` (option parsing, `inputUnsignedOption`, `inputLongDoubleOption`, `computeEntropyOfConditionedData`, JSON), `transpose_main.cpp`. jsoncpp 1.9.5 (system) serialisation behaviour checked.

Spec (SP 800-90B, Jan 2018, from knowledge of the text; not in the repo): §3.1.1, §3.1.2 (IID track incl. bullet 3), §3.1.3, §3.1.4.1–§3.1.4.3, §3.1.5.1.2, §3.1.5.2.

| Section | Algorithm/Test | Step | Code location | Matches? | Notes |
|---|---|---|---|---|---|
| §3.1.1 | Data intake | ≥1,000,000 consecutive samples; the assessed data is the submitted data | `utils.h:read_file_subset` :174, `non_iid_main.cpp:179/211` | Partly | <1e6 only warned (#255). Hash and data read in two separate opens (IO-03). `-l` block chosen by a base-0 parser (IO-04). |
| §3.1.3 | H_I aggregation | min(H_original, n×H_bitstring) | `non_iid_main.cpp:488-497` | Yes (modulo known #253/#254) | JSON identical at -q/-v/-vv (metamorphic check). |
| §3.1.3 | bitstring | each n-bit sample → n bits | `utils.h:302-313`, `:489-500` | Yes | MSB-first, from masked raw values (#71 convention). |
| §3.1.2 b3 | IID tests on restart row & column data | tests run, outcome gates nothing | `restart_main.cpp:740-824` | Tests yes; gating no | #252 family (see §5). |
| §3.1.4.1 | Row/column datasets | 1000×1000 transpose | `restart_main.cpp:449-474`, `transpose_main.cpp:103-110` | Yes | r=c so `i*r+j` indexing is correct. |
| §3.1.4.3 | Sanity check | X_max > X_cutoff → fail | `restart_main.cpp:477-499` | Yes for finite H_I | H_I = NaN is not rejected (IO-07). |
| §3.1.4.2 | Validation | min(H_r,H_c) < H_I/2 → fail | `restart_main.cpp:834-854` | Yes for finite H_I | H_I parsed with `atof` (IO-08). |
| §3.1.5.2 | Non-vetted h_out | min(Output_Entropy, 0.999 n_out, h'·n_out) | `conditioning_main.cpp:657-671` | Yes | h' may come from the command line while JSON names/hashes an unused `-i` file (IO-05). |
| — | Report provenance | sha256, filename, errorLevel, exit status | `test_run_base.h`, every main | No | IO-01, IO-02, IO-03, IO-06. |

## 2. Tests actually run (all reproduced at least twice unless stated)

- **CLI matrix, ea_non_iid** (`-vv`, rand8_short / truerand_1bit): bits_per_symbol ∈ {`8x`, `4.5`, `4294967297`, `4294967304`, ` 8`, `+8`, `0x8`, ``, `1e3`, `8 bits`}; `-l` ∈ {`010,1000`, `10,1000`, `0x2,1000`, `1,1000abc`, `1,01000`, `,1000`, ` 1,1000`, `+1,1000`, `1,abc`, `1,,1000`, `08,1000`, `99999999999999999999999,1000`, `1,99999999999999999999999`, `1,-1000`}; `-o` missing / empty / duplicated / unwritable / `/dev/full` / read-only existing file; `--` with a `-dash.bin` filename; non-UTF-8 and € filenames. Same `-l` parser checked on ea_iid; `-l {abc,010,8,1x}` on ea_transpose; `ea_conditioning 0512 0256 256 300` and `-- -18446744073709551360 …`; ea_restart H_I ∈ {`nan`, `NaN`, `-nan` (after `--`), `abc`, `3,5`, `1.5`}.
- **File matrix** (release and ASan, ea_non_iid/iid/restart/conditioning): nonexistent, directory, empty, 1-byte, `/proc/self/status`, `/dev/null`, 3-byte, non-regular; pipes/FIFO/`/dev/zero` not re-run (known #259).
- **Uninitialised-read check**: `valgrind --track-origins=yes` on ea_non_iid (nonexistent input) and ea_conditioning (`-i` nonexistent + explicit h'): both report "Conditional jump … depends on uninitialised value(s)" in `strlen` ← `std::string::assign` ← `main`, origin "stack allocation in main".
- **TOCTOU**: `strace -e openat` shows two independent `openat()` of the input (hash pass, then read pass). Deterministic demonstration with an `LD_PRELOAD` shim that rewrites (or appends to) the input between the two `fopen()` calls (IO-03). A gdb conditional-breakpoint attempt was abandoned (condition did not fire); the shim is simpler and deterministic.
- **Output-failure check**: `-o` to a missing directory, `""`, `/dev/full`, a read-only stale JSON, and `ulimit -f` with `SIGXFSZ` ignored (truncation) for ea_non_iid/ea_iid/ea_conditioning; `ulimit -f 976` truncation of ea_transpose's output with `strace` showing the `EFBIG` in the final flush.
- **Metamorphic, verbosity invariance of JSON**: ea_non_iid `-q` vs default / `-v` / `-vv` on rand1/4/8_short (and `-c`): identical apart from timestamp/commandline. ea_restart `-q` vs `-vv` on truerand_1bit, H_I 0.8: identical.
- **Differential, rounding mode**: `ea_conditioning -n -i f` (runs under `fesetround(FE_TOWARDZERO)`) vs `ea_non_iid -c -vv f` on 7 files; plus the same binary with an `LD_PRELOAD` constructor setting FE_TOWARDZERO, to attribute per-estimator differences.
- **jsoncpp serialisation**: a 6-line harness with `Json::StyledWriter`: NaN → `null`, ±inf → `±1e+9999`, −0 → `-0.0`, 17 significant digits. Python `json` parses all of them.
- **Sanitizer runs**: an 18-command ASan matrix (errors, `-l` variants, bits variants, conditioning, transpose, restart error paths). Full ASan ea_restart on truerand_1bit (6 min). ASan ea_restart with H_I=nan.
- **Compiler diagnostics**: `g++ -Wall -Wextra -O2` on all mains, used to see which defects gcc 13.3 already flags (relevant to the open warning-cleanup PR #242).
- Not run: >2^31-sample inputs (they need more than 8 GB RAM; the host has 7 GB and no swap); -m32 and mingw (no multilib or cross toolchain installed).

## 3. CONFIRMED NOVEL findings

### IO-01 — `sha256_file()` failure is ignored; an uninitialised stack buffer is copied into the report's `sha256` (and a successful ea_conditioning run records it with errorLevel 0)

Category C (assessment integrity / provenance) + B (read of uninitialised memory, UB). Confidence HIGH. Affected: ea_non_iid, ea_iid, ea_restart, ea_conditioning. Source: `non_iid_main.cpp:178-181`, `iid_main.cpp:198-200`, `restart_main.cpp:246-259`, `conditioning_main.cpp:519-522`; callee `shared/TestRunUtils.h:sha256_file:62` (returns −1 and leaves `outputBuffer` untouched on any failure). SP 800-90B §3.1.1 (the assessment must be of the submitted data; the hash is the tool's binding of result to data). Valid ≥1,000,000-sample case: yes for the ea_conditioning success path (the numeric result doesn't depend on the file). DIRECTION: none (provenance).

Root cause: `char hash[2*SHA256_DIGEST_LENGTH+1];` is uninitialised and `sha256_file(file_path, hash)`'s return value is discarded in all four mains; `testRun.sha256 = hash` then runs `strlen` over indeterminate bytes (and can read past the 65-byte array if none is NUL). In ea_non_iid/iid/restart the failure paths end with errorLevel −1, but the JSON still carries a garbage `sha256` (and `-vv` prints it). In ea_conditioning, `-i` is hashed but, when h' is given on the command line (or `-v` vetted mode), the file is never opened again, so the run **succeeds**.

Minimal reproduction:
```
./ea_conditioning -n -q -i nope.bin -o c.json 512 256 256 400 0.9 ; echo $?   # nope.bin does not exist
grep -E '"errorLevel"|"filename"|"sha256"' c.json
valgrind --track-origins=yes ./ea_conditioning -n -q -i nope.bin -o c.json 512 256 256 400 0.9
./ea_non_iid -q -o n.json nope.bin 8 ; grep sha256 n.json
```
Actual (three runs; the garbage differs each run and looks like pointer bytes):
```
exit=0   "errorLevel" : 0,   "filename" : "nope.bin",   "sha256" : "�٣�^?"
exit=0   "errorLevel" : 0,   ...                        "sha256" : "�߿^?"
exit=0   "errorLevel" : 0,   ...                        "sha256" : "�@۽^?"
valgrind: Conditional jump or move depends on uninitialised value(s) at strlen … by std::string::assign … by main; Uninitialised value was created by a stack allocation at main
ea_non_iid (twice): exit 255, "errorLevel" : -1, "sha256" : "�\u0011"   (directory input: same garbage with "Error reading file for hashing: Is a directory")
```
Expected: if the hash can't be computed, the run should refuse (or omit `sha256` and set errorLevel ≠ 0). A successful report must never name a file that was not read, with a hash that is not a hash.
Impact: a successful, errorLevel-0 ea_conditioning JSON can carry a nonexistent filename and a non-hash `sha256`, which is non-deterministic. It leaks stack bytes, which look like parts of addresses, into the report. On error paths in the other tools the defect is cosmetic, but it is still UB. It cannot change an entropy figure.
Deduplication: all.md grepped for `sha256_file`, `sha256`, `hash`, `uninitial`, `return value`, `could not open`. Hits: #201–#206 (the 2022 rewrite of `sha256_file`; #204 "errors were not consistently flagged … return code of 0" was about the function's own return codes, and callers ignoring them is not discussed), #218 (conditioning hash added), #259/#266 (unbounded read), #260/#267 (whole-file hash under `-l`), #122 (uninitialised `max_key`, unrelated). None covers the ignored return value or the uninitialised buffer. The exclusion map lists no such item. It is not flagged by `-Wall -Wextra`, so open PR #242 (warning cleanup) is unlikely to cover it.
Fix direction: zero-initialise `hash`; check the return value and refuse (errorLevel −1, message) before reading or assessing; in ea_conditioning, reject `-i` together with an explicit h' or vetted mode (see IO-05).
Regression test: run the nonexistent-`-i` command above; expect exit ≠ 0, or a JSON with no `sha256` and errorLevel ≠ 0. Run under valgrind: no uninitialised-value report.

### IO-02 — JSON (`-o`) and ea_transpose output write failures are never checked: exit 0 with no, stale, or truncated output

Category E (reporting) / C (report integrity). Confidence HIGH. Affected: all five. Source: every `ofstream output; output.open(outputfilename); output << …; output.close();` block (success paths `non_iid_main.cpp:538-543`, `iid_main.cpp:372-377`, `restart_main.cpp:869-879`, `conditioning_main.cpp:687-692`, plus all error-path copies) and `transpose_main.cpp:112` (`fclose(fp)` unchecked). SP 800-90B: n/a (tool report integrity). Valid ≥1e6 case: yes. DIRECTION: none.

Root cause: stream state is never tested after `open`, `<<` or `close`; `fclose` return ignored; all mains `return 0`. With `-q` (the JSON-only mode) ea_non_iid prints no result, so a failed write loses the result entirely while signalling success.
Reproduction (each run twice):
```
./ea_non_iid -q -o /nonexistent_dir/out.json ../bin/rand8_short.bin 8 ; echo $?          # 0, no file
./ea_non_iid -q -o stale.json ../bin/truerand_8bit.bin 8 ; chmod 444 stale.json
./ea_non_iid -q -o stale.json ../bin/rand8_short.bin 8 ; echo $?                          # 0
grep -E '"filename"|"hAssessed"' stale.json      # still truerand_8bit.bin, 7.233861455178495 (previous run)
./ea_non_iid -q -o /dev/full ../bin/rand8_short.bin 8 ; echo $?                           # 0
bash -c "trap '' XFSZ; ulimit -f 1; ./ea_non_iid -q -o trunc.json ../bin/rand8_short.bin 8; echo \$?"   # 0
python3 -c "import json;json.load(open('trunc.json'))"   # JSONDecodeError: Unterminated string … (char 1017); file is 1024 bytes
./ea_conditioning -v -q -o /nonexistent/x.json 512 256 256 400 ; echo $?                   # 0
./ea_iid -q -o /nonexistent/x.json ../bin/rand1_short.bin 1 ; echo $?                      # 0
bash -c "trap '' XFSZ; ulimit -f 976; ./ea_transpose ../bin/truerand_8bit.bin t.col; echo \$?"; ls -l t.col   # 0; 999424 bytes, not 1000000
strace … → write(3, …, 576) = -1 EFBIG   (inside fclose; ignored)
```
Expected: non-zero exit status and a message when the report or output cannot be written completely. Ideally write to a temporary file and `rename()` it, so a stale report is never mistaken for the current one.
Impact: automated pipelines that run `-q -o` and trust exit status get a missing, truncated or stale previous-run report. A truncated `.column` file then fails later tools (<1e6 samples) far from the cause. It does not change a figure.
Deduplication: grepped `ofstream`, `unwritable`, `permission denied`, `disk full`, `is_open`, `output.open`, `stale`, `truncat`, `exit status`, `exit code`, `return code`, `non-zero`. The only JSON-output failure items are #183/#187 ("failure modes produce no JSON", about which error paths write JSON at all, fixed 2022). No item addresses write/close failure or exit status. It is not a gcc warning, so it is outside #242.
Fix direction: check `output.fail()` after `open`, `<<` and `close`, and `fclose()`/`fflush()` results; exit non-zero on failure; write-then-rename.
Regression test: run the `-o /nonexistent_dir/…`, `/dev/full` and `ulimit -f` cases and expect a non-zero exit.

### IO-03 — The recorded SHA-256 and the assessed bytes come from two independent opens of the path; a concurrent rewrite or append makes the report bind one file's hash to another file's figure (whole-file runs, no `-l`)

Category C (assessment integrity / provenance). Confidence HIGH that it reproduces; MEDIUM that maintainers will treat it as distinct from #260. Affected: ea_non_iid, ea_iid, ea_restart, ea_conditioning. Source: `non_iid_main.cpp:179` → `TestRunUtils.h:72` `fopen` (hash pass), then `non_iid_main.cpp:211` → `utils.h:181` `fopen` (`fseek`/`ftell`/`fread`); the same pattern at `iid_main.cpp:199/209`, `restart_main.cpp:247/319`, `conditioning_main.cpp:521/367`. SP 800-90B §3.1.1. Valid ≥1e6 case: yes. DIRECTION: none by itself (the figure is right for the bytes read), but the report can pair a hash with a figure from different data.

Root cause: the hash is never computed from the buffer that is assessed. `strace` shows `openat(input)` in the hash pass, then a second `openat(input)`, `lseek(SEEK_END)`, `read` in the data pass.
Reproduction: an `LD_PRELOAD` shim that, on the 2nd `fopen()` of the input path, rewrites (`wb`) or appends to (`ab`) the file from another file. This models a writer that is still rewriting or appending (acquisition or copy job, watch-folder pipeline).
```c
/* toctou_shim.c:  gcc -shared -fPIC -O2 -o toctou_shim.so toctou_shim.c -ldl */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int count = 0;
FILE *fopen(const char *path, const char *mode) {
    static FILE *(*real)(const char *, const char *) = NULL;
    if (!real) real = (FILE *(*)(const char *, const char *))dlsym(RTLD_NEXT, "fopen");
    const char *t = getenv("TOCTOU_PATH"), *src = getenv("TOCTOU_SRC");
    if (t && src && strcmp(path, t) == 0 && ++count == 2) {
        FILE *in = real(src, "rb"), *out = real(t, getenv("TOCTOU_APPEND") ? "ab" : "wb");
        char buf[65536]; size_t k;
        while ((k = fread(buf, 1, sizeof buf, in)) > 0) fwrite(buf, 1, k, out);
        fclose(in); fclose(out);
    }
    return real(path, mode);
}
```
```
cp ../bin/truerand_8bit.bin t.bin        # sha256 c7e56911…3e3c3
TOCTOU_PATH=t.bin TOCTOU_SRC=../bin/biased-random-bytes.bin LD_PRELOAD=./toctou_shim.so ./ea_non_iid -q -o t.json t.bin 8
grep -E '"sha256"|"hAssessed"' t.json
# growing-file variant:
head -c 500000 ../bin/truerand_1bit.bin > g.bin; tail -c 500000 ../bin/biased-random-bits.bin > tail.bin
TOCTOU_APPEND=1 TOCTOU_PATH=g.bin TOCTOU_SRC=tail.bin LD_PRELOAD=./toctou_shim.so ./ea_non_iid -vv -o g.json g.bin 1
```
Actual (twice, identical):
```
"sha256" : "c7e56911d2657fa9b6e86c03d4477474d6ec698691c5f32d3918ec513713e3c3",   (= truerand_8bit.bin, whose own figure is 7.233861455178495)
"hAssessed" : 0.25774087100648113,                                                (= the figure for biased-random-bytes.bin, sha256 146bd749…508d)
growing: hash 4636be9b… of the 500,000-byte prefix; "Loaded 1000000 samples"; hAssessed 0.028983671140650293; file's final sha256 54b4da40…fa43
```
Expected: the recorded hash identifies exactly the bytes assessed. Hash the in-memory buffer that `read_file_subset` filled (this also fixes #260's `-l` whole-file-hash case), or hash and read through one descriptor in one pass, with `fstat` size and mtime checks.
Impact: provenance only. It needs the input to change during a run (window = the hash pass plus the start of the read, seconds for multi-GB files). Because the JSON has no sample count (#238), a mismatch is undetectable from the report. It is not an attack on the tool, but it undermines the only data-binding field in the ESV-style report.
Deduplication: grepped `TOCTOU`, `race`, `concurrent`, `hash`, `sha256`, `separate`, `two passes`, `same file`. #260 (open) and dup #267 say the `-l` subset run records a whole-file hash, "a hash that does not identify the data actually assessed". Their proposed fix is "hash only the assessed subset **or** state in the report that the hash is of the whole file"; the second option leaves this defect. #266 suggests hashing "after the size check", which is still a separate open. No item discusses whole-file runs, concurrent modification, or the two-open design. Same fix family as #260 part 2, distinct trigger. File as a comment on #260 or as its own item.
Fix direction: compute SHA-256 over `dp->rawsymbols` (the exact bytes read) inside or after `read_file_subset`, and drop the separate `sha256_file` pass. That also fixes #259's hang and IO-01.
Regression test: the shim run above; expect the JSON `sha256` to equal `sha256sum` of the bytes that produced `hAssessed` (e.g. 146bd749…).

### IO-04 — The `-l <index>,<samples>` parser uses `strtoull(…, 0)` (octal/hex prefixes) and doesn't check the end of the second number or reject empty fields, so zero-padded or malformed values silently select a different block; the report can't show which block was assessed

Category C (assessment integrity) / E. Confidence HIGH. Affected: ea_non_iid, ea_iid (identical parser), ea_transpose (weaker parser). Source: `non_iid_main.cpp:119-151`, `iid_main.cpp:111-145` (`strtoull(optarg,&nextOption,0)`, then `strtoull(nextOption, NULL, 0)` with no end-pointer, empty-field or ERANGE check; `errno` never reset), `transpose_main.cpp:56-63` (`strtoull(optarg, NULL, 0)` with no end check at all). SP 800-90B §3.1.1 (which consecutive samples form the dataset). Valid ≥1e6 case: yes (e.g. `-l 010,1000000` on a multi-block file). DIRECTION: none (a figure for a different, valid block).

Reproduction (truerand_1bit.bin; figures from `-vv`, run twice):
```
./ea_non_iid -vv -l 010,1000 ../bin/truerand_1bit.bin 1   → "reading block 8 of size 1000", Assessed 0.4925900276441092  (= -l 8,1000)
./ea_non_iid -vv -l 10,1000  ../bin/truerand_1bit.bin 1   → block 10, Assessed 0.50743623783244041
./ea_non_iid -vv -l 1,01000  …                            → "block 1 of size 512" (octal)
./ea_non_iid -vv -l 1,1000abc …                           → accepted as 1,1000
./ea_non_iid -vv -l ,1000 …                               → accepted as block 0
./ea_non_iid -vv -l 1,abc …   and   -l 1,,1000 …          → samples=0 sentinel: whole file, 1000000 samples, 0.82967708323411438
zero-padded loop 007/008/009/010/011 → block 7 / usage error / usage error / block 8 / block 9
./ea_iid -vv -l 010,1000 …  → "reading block 8";   ./ea_iid -vv -l 2,1000abc … → block 2
./ea_transpose -l abc rows3.bin o.col → "reading block 0" (output byte-identical to -l 0); -l 1x → block 1; -l 010 → block 8
```
The JSON of the `-l 010,1000` run records `"commandline": "... -l 010,1000 ..."` and the whole-file `sha256` f9ea8832… (#260). Nothing in the report reveals that block 8 (sha256 c802ac95…), not block 10 (ff482a37…), was assessed.
Expected: decimal-only parsing (base 10), rejection of empty fields, trailing characters and out-of-range values, and recording the parsed index and samples in the JSON.
Impact: a script that zero-pads block indices (`printf %03d`) silently assesses blocks 8, 9, 10 … for "010", "011", "012" …, gets a usage error for "008"/"009", and assesses block 0 from typos in ea_transpose. Every figure is correct for the data read but attributed to the wrong block. Low to medium, command-line-triggered only.
Deduplication: #191/#192 (getopt `l:` colon missing, fixed), #260/#267 (index×samples overflow, samples=0 sentinel, short final block, whole-file hash, `%ld` sign), #66/#99 (getopt adoption). Grepped `octal`, `leading zero`, `zero-pad`, `base 0`, `0x`, `strtoull`, `strtoul`, `errno`: no hits in upstream items. The samples=0 **sentinel** is known (#260). New here: the parser's base-0 conversion, the missing end-pointer and empty-field checks, and ea_transpose's unchecked `-l` (a non-numeric index becomes block 0).
Fix direction: `strtoull(s,&end,10)` with `errno=0` beforehand; require `end!=s`, `*end==','` for the first number and `*end=='\0'` for the second; reject samples==0; record index and samples in the JSON.
Regression test: `-l 010,1000`, `-l 1,1000abc`, `-l ,1000`, `-l 1,abc` must all be refused; `ea_transpose -l abc` must be refused.

### IO-05 — ea_conditioning writes `filename` and `sha256` for a `-i` file it never assesses (vetted mode, or non-vetted with h' on the command line)

Category C (provenance) / E. Confidence HIGH. Affected: ea_conditioning. Source: `conditioning_main.cpp:493-496` (`-i` stored), `:515-523` (hash and filename recorded unconditionally), `:558-577` (the file is read only when `!vetted && argc == 4`; with `argc == 5` h' comes from `argv[4]`; vetted mode never reads it). Usage text says `[h' | -i filename]` (mutually exclusive), but both are accepted silently. SP 800-90B §3.1.5.2 (h' is the entropy estimate of the conditioned sequential dataset). Valid ≥1e6 case: yes. DIRECTION: none, but the report attributes an h' to data that did not produce it.

Reproduction (twice):
```
./ea_conditioning -n -i cdata.bin -o c3.json 512 256 256 400 0.9     # cdata.bin = copy of truerand_8bit.bin
→ exit 0; JSON "filename":"cdata.bin", "sha256":"c7e56911…3e3c3", "h_p":0.89999999999999991, "h_out":230.39999999999997   (h' came from argv, file never opened again)
./ea_conditioning -v -i cdata.bin -o c4.json 512 256 256 400      → exit 0; same filename/sha256 recorded in a vetted run
```
With a nonexistent `-i` this becomes IO-01's garbage-hash success.
Expected: refuse `-i` together with an explicit h' or `-v`, or omit filename and hash when the file isn't assessed and record the h' source.
Impact: an ESV-style JSON asserts that a conditioned dataset with hash X underlies h' = 0.9 when the tool never measured X (its h' by `-n -i` alone would differ). Reporting only.
Deduplication: #218 (added the conditioning hash), #210 (h' statistic logic), #186 (`-c iid` compare), #102 (integer parsing), #178, #211, #225. Grepped `-i`, `conditioning`, `h'`, `filename`, `sha256`. No item covers recording an unused input file.
Fix direction: make `-i` and h' mutually exclusive (and `-i` invalid with `-v`); hash only when the file is assessed.
Regression test: the two commands above must be refused, or produce JSON without `filename`/`sha256`.

### IO-06 — `ea_restart -i -o …` writes a JSON with `"errorLevel": 0` and no `errorMessage` when the input cannot be read

Category E. Confidence HIGH. Affected: ea_restart (IID mode). Source: `restart_main.cpp:319` passes `&testRunNonIid` to `read_file` (so the message lands there); `:323-328` in the `iid` branch sets `testRunNonIid.errorLevel = -1` and then serialises `testRunIid`, whose errorLevel is still 0. SP 800-90B §3.1.4 (restart test outcome). Valid ≥1e6 case: n/a (error path). DIRECTION: none; the process exit status is 255, but the JSON says no error.

Reproduction (twice, deterministic apart from IO-01's garbage hash):
```
./ea_restart -i -o r.json nope.bin 8 4 ; echo $?   → 255
cat r.json   → "IID" : true, "errorLevel" : 0, "filename" : "nope.bin", "testCases" : null, "type" : "Restart"   (no errorMessage)
./ea_restart -i -o r.json adir 8 1                  → "errorLevel" : 0, "sha256" : "Ȃ\flϜ"
./ea_restart    -o r.json nope.bin 8 4              → correct: "errorLevel" : -1, "errorMessage" : "Error: could not open '%s'\n"
```
Expected: errorLevel −1 with the read error message in IID mode as in non-IID mode.
Impact: a JSON-only consumer sees a restart report with errorLevel 0 for a run that never read data. It has no test cases, so it can't be mistaken for a pass with figures, but it defeats errorLevel-based triage.
Deduplication: #183 (closed; "ea_restart JSON may not flag failure", fixed by #187 in 2022). This error path went through `read_file(…, &testRunNonIid)` later (#221 read errors into JSON). It is a residual wrong-object bug, not re-reported upstream. Grepped `errorLevel`, `restart`, `JSON`, `flag failure`: only #183/#187/#255/#254/#261/#262.
Fix direction: pass the active run object (`iid ? &testRunIid : &testRunNonIid`) to `read_file` and set errorLevel on it.
Regression test: the first command must produce `"errorLevel" : -1` and a message.

### IO-07 — ea_restart accepts H_I = `nan` (`atof`), which slips past both range checks and crashes: UB float→int conversion and an out-of-bounds stack write `counts[INT_MIN]`

Category B (memory safety / UB) + D. Confidence HIGH. Affected: ea_restart. Source: `restart_main.cpp:293-294` (`H_I = atof(argv[0]); if (H_I < 0)`: false for NaN), `:343` (`H_I > word_size`: false for NaN), `simulateBound:127-133` (`p = pow(2,-NaN)`, `k_effective = ceil(1/NaN)` → `(int)NaN`, UB, `INT_MIN` on x86; `assert(k_effective <= k)` passes), `simulateCount:92` (`counts[(int)floor(u/NaN)]++` → `counts[-2147483648]`). SP 800-90B §3.1.4 (H_I input). Valid ≥1e6 case: yes (needs the 1,000,000-sample restart file; the trigger is the argument). DIRECTION: none (crash, no verdict).

Reproduction (twice each):
```
./ea_restart -o r.json ../bin/truerand_1bit.bin 1 nan ; echo $?     → Segmentation fault, 139
./ea_restart -o r.json ../bin/truerand_1bit.bin 1 NaN ; echo $?     → 139
./ea_restart -o r.json -- ../bin/truerand_1bit.bin 1 -nan           → SIGSEGV
ASan/UBSan build: restart_main.cpp:132:23: runtime error: -nan is outside the range of representable values of type 'int'
                  restart_main.cpp:92:26 … ; restart_main.cpp:92:67: runtime error: index -2147483648 out of bounds for type 'short unsigned int [256]'
                  ERROR: AddressSanitizer: SEGV … simulateCount restart_main.cpp:92
```
Expected: reject non-finite H_I (`strtod` with an end check plus `isfinite`), as `ea_conditioning`'s `inputLongDoubleOption` already does.
Impact: a crash with an out-of-bounds stack write reachable from one command-line value. Plausible from a script that pipes a previous tool's printed estimate (e.g. a `nan` from the known #263/#264 NaN producers) into ea_restart. No JSON is written. Low severity, but it is memory corruption, not an assert.
Deduplication: #195 (open; `assert(k_effective <= k)` aborts when a finite H_I implies more symbols than observed; maintainer: lower the claim) has a different root cause and symptom (a finite H_I, a clean assert). Grepped `nan`, `atof`, `H_I`, `simulateBound`, `k_effective`: the NaN hits are #168 (conditioning, fixed by MPFR) and #263/#264/#270 (estimators). None covers NaN H_I.
Fix direction: validate H_I with `strtod` plus end-pointer plus `isfinite` plus `0 ≤ H_I ≤ word_size`; also guard `(int)` conversions in `simulateBound`/`simulateCount`.
Regression test: `ea_restart f 1 nan` must print a usage error and exit non-zero without a signal.

### IO-08 — Positional numeric arguments are parsed with `atoi`/`atof` (and `strtoul` base 0 in ea_conditioning): partial, wrapped or garbage values are silently accepted

Category D (robustness) / E. Confidence HIGH. Affected: ea_non_iid (`non_iid_main.cpp:186` `atoi(argv[1])`), ea_iid (`iid_main.cpp:179`), ea_restart (`:265` `atoi`, `:293` `atof`, `:218` `-s` `strtoul(…,NULL,10)`), ea_conditioning (`inputUnsignedOption:104` `strtoul(…,0)`, octal). SP 800-90B §3.1.3/§3.1.4 (n, H_I inputs). Valid ≥1e6 case: yes. DIRECTION: none to slightly lenient (H_I too low makes the restart test vacuous, but the output min(H_r,H_c,H_I) drops with it, so no entropy overclaim).

Reproduction (twice):
```
./ea_non_iid -vv ../bin/rand8_short.bin 8x         → accepted as 8 (Assessed 5.8608937444852494)
./ea_non_iid -vv ../bin/rand8_short.bin 4294967304 → atoi wraps to 8, accepted;  "8 bits" → 8;  "1e3" → 1;  "4.5" → 4 (then refused by the width check)
./ea_restart -o r.json ../bin/truerand_1bit.bin 1 abc  → "H_I: 0.000000", X_cutoff 1000, "Validation Test Passed...", exit 0, JSON h_i 0.0, errorLevel 0
./ea_restart -o r.json ../bin/truerand_4bit.bin 4 3,5  → H_I parsed as 3.0 (decimal comma), passes at 3.0
./ea_conditioning -v 0512 0256 256 300              → n_in = 330, n_out = 174 (octal)
./ea_conditioning -v -- -18446744073709551360 256 256 200 → n_in = 256 (strtoul negation wrap)
```
Expected: strict decimal parsing with end-pointer and range checks, as ea_conditioning's `inputLongDoubleOption` does for h_in/h'.
Impact: low. A typo or locale-formatted H_I gives a vacuous restart "pass" whose final value is H_I = 0 (conservative), or validates a lower H_I than intended. A malformed width can be accepted. ea_conditioning echoes the parsed values, so its octal surprise is visible.
Deduplication: #102 (closed, "ea_conditioning accepts non-integer n_in…", fixed by PR #99's `inputUnsignedOption`; base 0 and negation-wrap remain), #66/#99 (getopt). Grepped `atoi`, `atof`, `strtoul`, `octal`, `bits_per_symbol`, `invalid`: no item covers the atoi/atof acceptance of partial numbers or `abc` → 0 for H_I.
Fix direction: a shared strict-parse helper (base 10, errno, end-pointer, range, `isfinite`) for every numeric argument.
Regression test: each command above must be refused.

## 4. Suspected findings needing more work

- **ea_iid / IID path truncates sample counts to `int`** (`iid_main.cpp:250` `int sample_size = data.len`; `chi_square_tests`, `len_LRS_test`, `permutation_tests` helpers, `FYshuffle`, `sum`, `calc_proportions` all take `const int`; `permutation_tests.h:446-457` pass `dp->len` into `int` parameters). On LP64 (a supported platform), a file of 2^32 + 10^6 samples would run MCV, chi-square, LRS and the permutation statistics on the first 10^6 samples only, while `calc_stats` divides a 10^6-sample `sum` by the full length. For 2^31 ≤ L < 2^32 the lengths become negative. Not demonstrated: it needs more than 8.6 GB RAM (host 7 GB, no swap). Practically, permutation testing of >2^31 samples is infeasible in time anyway. Adjacent to large-file support #217/#226 (which targeted ea_non_iid) and maintainer position 15.
- **ea_conditioning runs the §6.3 estimators under `fesetround(FE_TOWARDZERO)`** (`conditioning_main.cpp:459`, intended for input parsing), so its h' differs from `ea_non_iid -c` on the same file. Measured: rand8_short 0.7326117180606737 vs 0.73261171806065617 (+1.75e-14, the compression search). truerand_1bit, biased-random-bits, truerand_4bit, normal, rand1/4_short differ by ≤1 ulp. Attributed per estimator with an LD_PRELOAD FE_TOWARDZERO constructor: p̂ = 0.50123749999999989 vs 0.5012375, MCV/collision/compression entropies higher by 2e-16 to 1.8e-14. Direction slightly high, but far below the maintainers' 1e-10 platform tolerance (position 23). Not worth filing unless a case with a larger gap is found (e.g. a solver bracket or an assert that behaves differently).
- **Restart `-i` JSON**: the row and column permutation-test results are appended into one `tcOverallIid.testResults` array as `iteration` 0,1,2,0,1,2 with no row/column label (`restart_main.cpp:791-800`, `permutation_tests.h:570-572`). Report ambiguity introduced with #250. Low; not written up as a finding.

## 5. EXCLUDED AS ALREADY KNOWN

- ea_iid JSON `hAssessed` = word_size at default verbosity (`iid_main.cpp:286-313`) → **#251** (open PR).
- ea_iid (and ea_restart `-i`) report a figure, errorLevel 0, exit 0 and "Validation Test Passed" even when the IID / §3.1.2-bullet-3 tests fail. The ea_iid top-level `"IID": true` is a class constant (`iid_test_run.h`), not a verdict → **#252** family (PR open for ea_iid only; the restart `-i` gating is the same root cause, not re-reported).
- errorMessage strings built with the comma operator (`utils.h:184, :226, :364, :391`: JSON gets the literal `"Error: could not open '%s'\n"`, `"Error: '%s' is empty\n"`) → flagged by gcc 13.3 `-Wunused-value`. Open **PR #242** ("Fixes Wall and Wextra warnings emitted from gcc 13.3"; its review thread discusses rewriting `testRun->errorMsg` with `stringstream`) almost certainly covers it. The PR diff is not in all.md, so "covered" is inferred from the PR text.
- `restart_main.cpp:160` `delete results;` for `new uint16_t[]` (alloc/dealloc mismatch, UB) → flagged by gcc 13.3 `-Wmismatched-new-delete` → presumably covered by **PR #242**. Practical note for other agents: **every ASan run of ea_restart aborts at restart_main.cpp:160 right after the cutoff simulation** (`alloc-dealloc-mismatch`, observed after a 6-min run). Use `ASAN_OPTIONS=alloc_dealloc_mismatch=0` to sanitize the rest of ea_restart.
- "Narrower than described" warning set in `errorMsg` but lost from JSON (errorLevel 0); ea_iid and restart-IID JSON carry no `dataWordSize` → **#254** family.
- No sample count, `-t`, `-l`, `-s`, X_cutoff or X_max in JSON; figures from <1e6 samples with errorLevel 0 → **#238 / #255**.
- `-l` samples=0 sentinel, index×samples wrap, whole-file hash under `-l`, `%ld` printing of `unsigned long` → **#260** (dup #267).
- Hang on `/dev/zero`, `/dev/urandom`, FIFO → **#259** (dup #266). Pipes from `<(cat f)` give a clean "fseek failed" refusal after the hash pass, the same root family.
- Assert aborts with no JSON: ea_conditioning `-i` on an all-zero file (inferred width 0, `blen` 0 → `most_common.h:14` `assert(len > 1)`) or a 1-byte file (`multi_mmc_test.h:21`) → **#261** + **#254** (inference); ea_conditioning writes no JSON when the `-i` read fails → **#183** family.
- ea_restart `assert(k_effective <= k)` → **#195**.
- Text `%f` 6-decimal round-to-nearest can print above the computed value (non_iid, iid, restart "min(H_r, H_c, H_I): %f") → **F23**.
- LLP64 / 32-bit: `long len`/`blen` (e.g. `dp->blen = dp->len * dp->word_size` overflows for 8-bit files ≥ 256 MiB, then heap writes via the wrapped `i*word_size` index), `ftell` 2 GiB limit, `unsigned long` `-l` offsets → maintainer stance **#155/#170/#212** (J: "codebase presumes long is 64-bit … may yield incorrect results in Windows") + #267's LLP64 note. Not re-reported: no -m32 or mingw toolchain here, and the platform is unsupported.
- NaN/Inf in JSON: jsoncpp 1.9.5 writes NaN as `null`, ±inf as `±1e+9999` (valid JSON); the only reachable producers are the known tiny-input **#263/#264** estimators (and IO-07, which crashes before any JSON).

## 6. No-finding areas (attacked and held)

- Symbol translation (`symbol_map_down_table`) is order-preserving and applied after the bitstring is built from masked raw values. The mask never drops set bits because a declared width narrower than the data is refused. `rawsymbols` keeps unmasked bytes, which ea_transpose writes. Transpose indexing (`rawsymbols + c*j + i`) is correct, and so is restart's `i*r+j` (r = c).
- Empty file, `/dev/null`, `/proc` files (ftell 0), and 3-byte restart input are refused with errorLevel −1 and exit 255. A directory makes `ftell` return LONG_MAX, the allocation fails, and the run is refused. Under ASan that is an allocation-size abort, not a memory error. Filenames with spaces, € and a leading `-` (after `--`) work. Non-UTF-8 filename bytes become U+FFFD in JSON `filename` and `commandline` (lossy but harmless; the hash identifies content). `commandline` is unquoted (cosmetic).
- `-o` duplicated: the last one wins. `-o` without an argument: getopt refuses. `-o` equal to the input path overwrites the input when the report is written (user-directed).
- JSON faithfulness across verbosity: ea_non_iid (`-i` and `-c`) and ea_restart (non-IID) JSON are byte-identical apart from timestamp and commandline for -q, default, -v and -vv. ea_iid's verbosity dependence is #251.
- jsoncpp writes 17 significant digits (round-trip exact) and valid JSON for NaN, inf and −0.
- `errorLevel = 0` reset at the end of each main does not mask any earlier error, because every path that sets −1 exits.
- ea_conditioning `inputLongDoubleOption` rejects nan, inf, trailing characters and out-of-range values correctly. `h_in ≤ n_in` is enforced. The `-c iid` string compare is correct (fixed #186).
- `TESTCASE_H` include-guard collision between `test_case_base.h` and `TestCase.h`: in iid and restart builds `TestCase.h` is silently skipped, but `permutation_tests.h` uses nothing from it (dead include, no runtime effect).
- ASan matrix (18 I/O and CLI error-path commands across all five tools): no sanitizer reports other than the known restart alloc/dealloc mismatch, IO-07 and the directory allocation-size abort.
