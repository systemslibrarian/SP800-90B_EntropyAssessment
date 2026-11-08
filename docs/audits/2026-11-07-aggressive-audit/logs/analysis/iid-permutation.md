# IID permutation testing (SP 800-90B §5.1) — analysis-phase record

Audit: 2026-11-07 aggressive audit, branch `audit/2026-11-07`. Component: the §5.1
permutation battery — the 11 statistic families (19 statistics), Conversions I/II,
the Fisher–Yates shuffle, the randomness source and seeding, and the C_i,0/C_i,1
counting rule. Files read in full: `cpp/iid/permutation_tests.h` (742 lines),
`cpp/iid/permutation_test_result.h`, `cpp/shared/TestRunUtils.h`, `cpp/iid_main.cpp`,
plus the called code in `cpp/shared/utils.h` (`data_t`, `PERMS`, `seed`, `xoshiro256starstar`,
`xoshiro_jump`, `randomRange64`, `FYshuffle`, `sum`, `divide`, `calc_stats`,
`read_file_subset`), `cpp/iid/iid_test_case.h`, `cpp/iid/iid_test_run.h`, the N-01 region
of `cpp/iid/chi_square_tests.h`, and the two `permutation_tests()` call sites in
`cpp/restart_main.cpp`.

Spec text: `reference/sp800-90b.pages.txt`, PDF p37–43. All quotes below are from it.

Binary measured against (instrument rule 4):
`cpp/ea_iid` sha256 `22f1319ae347ab4e187953c9161219893310569965234876fdbd6a73daba7349`
(`logs/analysis-iid-perm-binary.sha256`). Platform: Darwin arm64, Apple clang 21,
`OMP_NUM_THREADS=2`, `EA_ALLOW_SHORT_DATASET=1` on every probe (all probes are 20,000
samples; every run is therefore marked non-compliant by the tool itself).

**Headline.** On three probe inputs (binary width 1; k = 8 width 3; two-valued {3,200}
width 8) all **57 of 57** unpermuted statistics printed by the C++ at `-vvv` equal an
independent Python transcription of §5.1.1–§5.1.11 that itself reproduces the spec's
Examples 1–10 and both conversion examples (`logs/analysis-iid-perm-compare.log`,
`logs/analysis-iid-perm-ref-selftest.log`). The counting rule is proved equivalent to
Figure 4 (below). The shuffle draw is exhaustively unbiased and the loop is textbook
Fisher–Yates. Two runs on identical input differ in **19 of 19** counter rows, so the
seed is live and the verdict is nondeterministic by design. **No CRITICAL or HIGH
defect was found in this component.** What was found: one confirmed code-vs-comment
defect in the per-thread RNG jump (neutral), two latent fail-open mechanisms that are
unreachable at the target profile on this host (compression failure → vacuous pass;
LLP64 `unsigned long` covariance wrap), and several LOW reporting/robustness notes.

---

## 1. The spec's algorithm, step by step

### 1.1 Generic structure — SP 800-90B §5.1, Figure 4 (PDF p. 37)

> 1. For each test i
>    1.1. Assign the counters Ci,0 and Ci,1 to zero.
>    1.2. Calculate the test statistic Ti on S.
> 2. For j = 1 to 10 000
>    2.1. Permute S using the Fisher-Yates shuffle algorithm.
>    2.2. For each test i
>        2.2.1. Calculate the test statistic T on the permuted data.
>        2.2.2. If (T > Ti), increment Ci,0. If (T = Ti), increment Ci,1.
> 3. If ((Ci,0+Ci,1≤5) or (Ci,0 ≥ 9995)) for any i, reject the IID assumption; else, assume that
>    the noise source outputs are IID.

Constants: exactly **10 000** permutations; cutoffs **≤ 5** and **≥ 9995**; comparison
operators **strict >** for C_i,0 and **equality** for C_i,1. Direction: a very HIGH rank
of the original (few permutations exceed or tie it) fails via C0+C1 ≤ 5; a very LOW rank
fails via C0 ≥ 9995. Ties count toward C1 only, and C1 protects against BOTH failure
conditions (it adds to C0+C1 and it is excluded from C0).

Note an internal inconsistency of the standard (PDF p. 38 prose): "If the sum of Ci,0 and
C i,1 is **less than** 5 ... conversely, if Ci,0 is **greater than** 9995". Figure 4 says
≤ 5 and ≥ 9995. The figure is the algorithm; the prose is looser by one. "The cutoff
values ... are calculated using a type I error probability of 0.001."

### 1.2 The shuffle — §5.1, Figure 5 (PDF p. 38)

> 1. for i from L downto 1 do
>    a. Generate a random integer j such that 1≤ j ≤ i.
>    b. Swap sj and si

So j is uniform on the closed range [1, i] (1-based), i.e. the running element may be
swapped with itself. The standard does not name a randomness source.

### 1.3 Conversions for binary input — §5.1 (PDF p. 38)

> "for some of the tests, the number of distinct sample values, denoted k ..., significantly
> affects the distribution of the test statistics ... one of the following conversions is
> applied to the input data, when the input is binary, i.e., k = 2."

> "Conversion I partitions the sequences into eight-bit non-overlapping blocks, and counts the
> number of ones in each block. Zeroes are appended when the last block has less than eight
> bits. For example, let the 20-bit input be (1,0,0,0,1,1,1,0,1,1,0,1,1,0,1,1,0,0,1,1). ... The
> output sequence is (4, 6, 2)."

> "Conversion II partitions the sequences into eight-bit non-overlapping blocks, and
> calculates the integer value of each block. ... The integer values of the first two blocks are
> 142, and 219. ... the last block becomes (0,0,1,1,0,0,0,0) with an integer value of 48. The
> output sequence is (142, 219, 48)."

142 = 0b10001110 from (1,0,0,0,1,1,1,0): the FIRST bit is the most-significant bit.

### 1.4 The eleven statistics (§5.1.1–§5.1.11, PDF p. 39–43)

| § | statistic | definition (quoted/condensed) | binary handling |
|---|---|---|---|
| 5.1.1 | Excursion | "X̄ = (s1 + … + sL)/L ... di = \|Σ_{j≤i} sj − i × X̄\| ... T = max(d1,…,dL)". Ex.1: S=(2,15,4,10,9) → T=6 | "no additional conversion steps are required" |
| 5.1.2 | Number of directional runs | S′_i = −1 if s_i > s_{i+1}, +1 if s_i ≤ s_{i+1}, i=1..L−1; "T is the number of runs in S′". Ex.2 → T=3 | Conversion I |
| 5.1.3 | Length of directional runs | same S′; "T is the length of the longest run". Ex.3 → T=6 | Conversion I |
| 5.1.4 | Number of increases and decreases | same S′; "T = max (number of –1's, number of +1's)". Ex.4 → T=8 | Conversion I |
| 5.1.5 | Number of runs based on the median | "Find the median X̃ of S"; S′_i = −1 if s_i < X̃, +1 if s_i ≥ X̃, i=1..L; T = number of runs. Ex.5 → 5 | "the median of the input data is assumed to be 0.5. No additional conversion" |
| 5.1.6 | Length of runs based on median | same S′; T = longest run. Ex.6 → 2 | median 0.5, no conversion |
| 5.1.7 | Average collision | "i = 1. While i < L: a. Find the smallest j such that (si, …, si+j-1) contains two identical values. If no such j exists, break ... b. Add j to the list C. c. i = i + j." T = average of C. Ex.7: S=(2,1,1,2,0,1,0,1,1,2) → C=[3,4,2], T=3 | Conversion II |
| 5.1.8 | Maximum collision | same C; T = max. Ex.8 → 4 | Conversion II |
| 5.1.9 | Periodicity | "lag parameter p ... p < L ... For i = 1 to L − p: If (si = si+p), increment T". p ∈ {1,2,8,16,32}. Ex.9 (p=2) → 5 | Conversion I |
| 5.1.10 | Covariance | "For i = 1 to L – p: T = T + (si × si+p)". p ∈ {1,2,8,16,32}. Ex.10 (p=2) → 164 | Conversion I |
| 5.1.11 | Compression | "Encode the input data as a character string containing a list of values separated by a single space, e.g., 'S = (144, 21, 139, 0, 0, 15)' becomes '144 21 139 0 0 15'. 2. Compress ... with the bzip2 compression algorithm ... 3. T is the length of the compressed string, in bytes." | "applied directly to binary data, with no conversion required" |

Bounds/termination: there is no tolerance, no iteration cap other than 10 000, no
rounding. Everything is integer except the excursion (real) and the collision average
(rational). No log is taken anywhere in §5.1.

---

## 2. Map to the C++ (file:function:lines), with every disagreement quoted

### 2.1 Driver — `permutation_tests.h:permutation_tests` (578–742)

| spec step | code | verdict |
|---|---|---|
| 1.1 zero counters | 595–602: `C[i][0]=C[i][1]=C[i][2]=0; t[i]=-1; test_status[i]=true;` | matches (a third counter C2 = #(T < Ti) is added) |
| 1.2 Ti on S | 606 `seed(...)`; 608 `run_tests(dp, dp->symbols, dp->rawsymbols, rawmean, median, t, test_status)` | matches |
| 2. j = 1..10 000 | 652 `for(int i = 0; i < PERMS; ++i)` with `#define PERMS 10000` (utils.h:43) | matches |
| 2.1 Fisher–Yates | 657 `FYshuffle(data, rawdata, dp->len, xoshiro256starstarSeed)` — shuffles the translated and raw copies with the SAME random indices (utils.h:869–879) | matches (alignment of the two views preserved) |
| 2.2.1 T on permuted | 658 `run_tests(dp, data, rawdata, ...)` | matches |
| 2.2.2 counters | 665–671: `if(tp[j] > t[j]) C[j][0]++; else if(tp[j] == t[j]) C[j][1]++; else C[j][2]++;` | matches (strict >, exact ==) |
| 3. verdict | 735–739: `if((C[i][0] + C[i][1] <= 5) \|\| (C[i][1] + C[i][2] <= 5)) return false;` | **equivalent**, see proof below |

**Early termination (code only, not in the spec), 672–674:**
```c
if((C[j][0] + C[j][1] > 5) && (C[j][1] + C[j][2] > 5)) {
    test_status[j] = false;
}
```
Once a statistic is decided it is no longer computed (every `*_tests` helper checks
`test_status[k]` before computing, 344–440), and 653 `if(passed_count < 19)` skips the
whole permutation once all 19 are decided.

*Proof of equivalence with Figure 4.* Let N_j = C0+C1+C2 be the number of permutations
counted for statistic j. If N_j = 10 000 then C1+C2 ≤ 5 ⇔ C0 ≥ 9995, so the code's test is
Figure 4's test verbatim. If the statistic stopped early at some N_j < 10 000, both
C0+C1 > 5 and C1+C2 > 5 held at that moment; both sums are non-decreasing in further
permutations, so under the full 10 000 the spec would have C0+C1 ≥ 6 (no high-rank
failure) and C1+C2 ≥ 6 ⇒ C0 ≤ 9994 (no low-rank failure): PASS. The code passes it too.
A statistic that never satisfies both is counted for all 10 000 (nothing else skips it —
the skip at 664 is `if(test_status[j])`, which only becomes false by 673). Hence the
verdict is identical to the spec's for every statistic. The counts REPORTED differ (they
are partial), see §2.9.

**Randomness source and seeding** (`utils.h:seed`, 794–810):
```c
if((infp=fopen("/dev/urandom", "rb"))==NULL) {
    perror("Can't open random source. Reverting to a deterministic seed.");
    exit(-1);
}
if(fread(xoshiro256starstarState, sizeof(uint64_t), 4, infp)!=4) { perror(...); exit(-1); }
```
256 bits straight from `/dev/urandom` into the xoshiro256** state; failure is
`exit(-1)` (fail-closed; with `-o` the C14 placeholder stays in place). The path is a
literal: **`EA_TEST_RANDOM_SOURCE` does NOT reach `seed()`** — it is read only at
`TestRunUtils.h:129–130` and used only for the temp-file suffix in `writeJsonReport`
(478). No environment variable, option or data byte influences the shuffle seed
(`grep getenv cpp/` → only `EA_TEST_INPUT_IDENTITY_MARKER`, `EA_ALLOW_SHORT_DATASET`,
`EA_TEST_RANDOM_SOURCE`). The seed is not recorded anywhere, so a verdict cannot be
replayed (§2.9). The perror text promises a fallback that does not exist (§3 note L6).

**Per-thread streams** (`permutation_tests.h:647–649`, `utils.h:xoshiro_jump` 765–789):
```c
memcpy(xoshiro256starstarSeed, xoshiro256starstarMainSeed, ...);
//Cause the RNG to jump omp_get_thread_num() * 2^128 calls
xoshiro_jump(omp_get_thread_num(), xoshiro256starstarSeed);
```
```c
void xoshiro_jump(unsigned int jump_count, uint64_t *s) {
    uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;          // declared ONCE
    for(unsigned int j=0; j < jump_count; j++) {
        for(i...) for(b...) { if (JUMP[i] & 1<<b) { s0 ^= s[0]; ... } xoshiro256starstar(s); }
        s[0] = s0; s[1] = s1; s[2] = s2; s[3] = s3;     // accumulators never re-zeroed
    }
}
```
**DEVIATION from the code's own comment (CONFIRMED by model, neutral).** The
Blackman/Vigna `jump()` zeroes its accumulators per call. Here they persist across the
`j` loop, so iteration j computes acc_{j+1} = acc_j ⊕ J(s_j) and the state after k ≥ 2
"jumps" is not J^k(S0). `logs/analysis-iid-perm-rng-model.log`: k=0,1 agree with the
canonical jump; k=2,3,4 do not; k=2 equals S1 ⊕ S2 exactly as predicted. Consequence:
thread 0 and thread 1 are correct; threads 2+ start at a nonzero, J-linear image of the
seed that sits at an effectively random offset in xoshiro256's single 2^256−1 cycle
rather than at k·2^128. The "non-overlapping subsequences" guarantee becomes
probabilistic; with ≤ 10 000 shuffles × ≤ 2^31 draws per thread the overlap probability
is ~threads·2^44/2^256 — nil. No statistical effect is claimable; the shuffle on each
thread is still uniform. Only `OMP_NUM_THREADS ≥ 3` is affected (the production default
on a multi-core host; the audit's 2-thread probes are not). Upstream-inherited.

**Shuffle** (`utils.h:FYshuffle` 869–879):
```c
for (long int i = sample_size - 1; i > 0; --i) {
    r = (long int)randomRange64((uint64_t)i, xoshiro256starstarState);   // [0, i]
    SWAP(data[r], data[i]); SWAP(rawdata[r], rawdata[i]);
}
```
Figure 5 with 0-based indices; the i = 1 iteration of the spec (swap s1 with s1) is the
omitted no-op. `randomRange64(s)` (828–856) is Lemire's nearly-divisionless method on
[0, s]: `s++`, `m = x*s` in 128 bits, `l = low64(m)`, reject while `l < (2^64 − s) mod s`,
return `m >> 64`; `s == UINT64_MAX` returns `x` directly. Exhaustively modelled at L = 8
for every s: every output hit exactly ⌊2^L/s⌋ times — **UNBIASED** (Q2 in the model log).
The Fisher–Yates loop shape reaches all 24 permutations of n = 4 exactly once (Q3). A
`static mutex` serialises the shuffle across threads (performance only; each thread
has its own RNG state). `SWAP` uses an `int` temporary — fine for `uint8_t`.

### 2.2 Conversions — `conversion1` (27–35), `conversion2` (42–50)

```c
vector<uint8_t> ret((sample_size / 8) + ((sample_size%8==0)?0:1), 0);
for(i...) ret[i/8] += data[i];                      // I: ones per block, zero-padded
for(i...) ret[i/8] += data[i] << (7 - i%8);         // II: first bit is MSB
```
Both match the p. 38 examples ((4,6,2) and (142,219,48) reproduced by the Python
transcription of the same rule, `analysis-iid-perm-ref-selftest.log`). Applied to
`dp->symbols`, which for `alph_size == 2` is always {0,1}: `read_file_subset`
(utils.h:542–543) maps down whenever `alph_size < maxsymbol + 1`, and if the raw
values are already {0,1} no map is needed. Conversions are applied AFTER each shuffle
(per permutation, inside `run_tests`), as Figure 4 requires (shuffle S, then compute T).

Which statistic sees which representation (`run_tests` 443–458 and the helpers):

| statistic | k = 2 (binary) | k > 2 | spec |
|---|---|---|---|
| excursion | `rawdata`, `rawmean` (446) | `rawdata` | no conversion ✔ |
| 5.1.2–5.1.4 | `conversion1(symbols)` (352–354) | `symbols` (translated; monotone map preserves > / ≤) | Conv. I ✔ |
| 5.1.5–5.1.6 | `alt_sequence2(symbols, 0.5)` (371) | `alt_sequence2(symbols, median)` (373) | median 0.5 / median ✔ |
| 5.1.7–5.1.8 | `conversion2(symbols)`, k = 256 (387–388) | `symbols`, k = `alph_size` (390) | Conv. II ✔ |
| 5.1.9 | `conversion1(symbols)` (402–407) | `symbols` (equality is translation-invariant) | Conv. I ✔ |
| 5.1.10 | `conversion1(symbols)` (421–427) | `rawdata` (455) | Conv. I ✔ |
| 5.1.11 | `rawdata` (457) | `rawdata` | no conversion ✔ |

The one reading the standard leaves open: a two-valued input whose values are not
{0,1} (probe P3, bytes {3,200}, k = 2). The code converts the translated {0,1} and
applies excursion/compression to the raw values. Excursion on 3 + 197·b is an affine
image of excursion on b, so the ranking is unchanged; compression sees different digit
strings for original and permutations alike. Measured: P3's 19 statistics equal the
Python transcription under the same reading, and the battery passed. Not a deviation;
recorded as a reading.

### 2.3 Excursion — `excursion` (57–72)

```c
running_sum += data[i];
d_i = abs(running_sum - ((i+1) * rawmean));
if(d_i > max) max = d_i;
```
`rawmean = sum(rawsymbols)/len` (utils.h:920, `long int sum`) computed once in
`calc_stats` — permutation-invariant, correct to reuse. `abs` must resolve to the
floating overload: measured P1 excursion = 61.35999999999995 (non-integer), so on this
toolchain it does; `<cmath>` is included via utils.h and `using namespace std` is in
scope, so libstdc++ resolves the same way. Double arithmetic: running sums ≤ 255·2^31
exact; the Python value differs only in the last bits (summation order), 1e-13 relative.

### 2.4 Directional runs and increases/decreases — `alt_sequence1` (80–88), `num_directional_runs` (119–133), `len_directional_runs` (146–169), `num_increases_decreases` (176–187)

`ret[i] = ((data[i] > data[i+1]) ? -1 : 1)` for i < L−1 — exactly S′. Run counting starts
at 1 for a non-empty S′ and increments on sign change; longest run with a final-run
flush; `max(pos, size−pos)`. Examples 2–4 reproduced by the transcription; P1/P2/P3
values equal the C++. No off-by-one: S′ has L−1 elements (`vector<int> ret(sample_size-1)`).

### 2.5 Runs based on the median — `alt_sequence2` (94–102), `calc_stats` (utils.h:917–940)

`ret[i] = ((data[i] < median) ? -1 : 1)` — exactly S′ with the ≥ branch as +1. Median:
`0.5` for `alph_size == 2` (binary rule); otherwise the median of the sorted TRANSLATED
indices, odd L → middle, even L → mean of the two middle values (utils.h:933–938). The
standard says "the median of S" without defining even-L; the mean-of-middle rule is the
usual one. Translation is monotone and no data value lies strictly between the two middle
sorted values, so `s_i < X̃` has the same truth value in raw and translated space (this is
the N-10 repair's premise; it holds). Ex.5/6 reproduced.

### 2.6 Collisions — `find_collisions` (190–224), `avg_collision` (230–233), `max_collision` (239–246)

Traced on Ex.7 (2,1,1,2,0,1,0,1,1,2): pushes 3, 4, 2 and stops when `i + j` reaches n
with no collision — C = [3,4,2], as the spec. `j+1` is the window size at the collision
(comment at 207–208 is right). `i += j; ... ++i` advances to the element after the
collision, i.e. the spec's `i = i + j`. `dups` is sized `k` and indexed by `data[i+j]`:
for k > 2 the translated symbols are in [0, alph_size) and for binary the Conversion II
bytes are in [0, 256) with k = 256 — in bounds. `avg_collision = divide(sum(col_seq),
col_seq.size())` (`double divide(int,int)`, utils.h:1083): sum of window lengths ≤ L ≤
INT_MAX, fine. If C is empty (only possible for inputs shorter than the collision horizon,
impossible at L ≥ 10^6 with k ≤ 256) the result is 0/0 = NaN; NaN compares neither > nor
==, so every permutation lands in C2 and the test FAILS — fail-closed.

### 2.7 Periodicity and covariance — `periodicity` (253–265), `covariance` (272–280)

`for(i = 0; i < n-p; ++i) if(data[i] == data[i+p]) ++T;` and `T += data[i] * data[i+p];`
— exactly L−p terms, 1-based i=1..L−p ⇔ 0-based 0..L−p−1. `assert(n>=p)` guards the
unsigned subtraction (production has no `-DNDEBUG`; Makefile CXXFLAGS checked). Ex.9/10
reproduced. **Type note:** `covariance` returns `unsigned long int`. On LP64 that is 64
bits and the sum (≤ 255²·2^31 ≈ 1.4e14) fits; it is also exact in a 53-bit `long double`
(arm64 macOS) since 1.4e14 < 2^53. On LLP64 (Windows, `unsigned long` = 32 bits) an 8-bit
dataset of 10^6 samples has E[T] ≈ 10^6·127.5² ≈ 1.6e10 > 2^32: **T wraps mod 2^32** and
the ranking compares wrapped values — the five covariance statistics would become
uninformative (effectively random rank, passing with probability ≈ 0.998 regardless of
dependence). **Latent only**: on Windows `seed()` exits before any permutation runs
(`OC-42`/`OC-53` in the record), so it is unreachable today; it is a concrete instance for
C18's "no sweep of the remaining `long` arithmetic has been done". The same applies to
`long int sum(const uint8_t[], int)` feeding `rawmean` (wraps on LLP64 above ~8.4e6
samples of 255).

### 2.8 Compression — `compression` (287–334)

```c
msg = new char[(size_t)(floor(log10(max_symbol))+2.0)*sample_size+1];
res = sprintf(curmsg, "%u ", data[i]); ... curlen += res;      // "144 21 139 0 0 15 "
curmsg--; *curmsg = '\0'; curlen--;                            // drop the trailing space
unsigned int dest_len = ceil(1.01*curlen) + 600;
int rc = BZ2_bzBuffToBuffCompress(dest, &dest_len, msg, curlen, 5, 0, 0);
if(rc == BZ_OK) return dest_len; else return 0;
```
Encoding matches §5.1.11 exactly (values, single spaces, no trailing space); Python's
`bz2.compress(level=5)` gives byte-identical lengths on all three probes (3163, 7809,
3183). `max_symbol` is `dp->maxsymbol` — the largest RAW value — so the buffer sizing
(2/3/4 chars per sample) is right for the raw values printed; `assert(max_symbol > 0)`
holds because `alph_size ≤ 1` is refused before the battery (iid_main.cpp:329) and under
`-c` the view sets `maxsymbol = 1`. Block size 5 (500 kB) and the default work factor are
implementation choices the standard does not fix ([BZ2] names the algorithm only).

**Fail-open on compression failure (suspicion, overstates, low reachability).**
`rc != BZ_OK` returns **0** instead of refusing. If the baseline AND every permutation
fail the same way, every comparison is a tie: C1 reaches 6 after six permutations, both
pass conditions hold, and the compression statistic is **passed vacuously**. (If only the
baseline fails, every permutation exceeds it → C0 = 10 000 → FAIL, so the asymmetric case
is fail-closed.) Reachability: `BZ_MEM_ERROR` under memory exhaustion (per-thread
`msg`+`dest` ≈ 2.02 × chars), or `BZ_OUTBUFF_FULL` when `unsigned int dest_len =
ceil(1.01*curlen)+600` wraps — curlen > ≈ 4.25e9 chars, i.e. > ≈ 1.06e9 samples of
three-digit values under `-i`, or ≈ 2.1e9 bits under `-c` (which is at the `INT_MAX`
guard, iid_main.cpp:393). `curlen` itself is `unsigned int` and wraps at the same scale.
At the target profile (10^6–10^8 samples) the message is ≤ 400 MB and nothing wraps; on a
16 GB host the memory would run out before the wrap is reached. Not reproduced; recorded
as the one fail-open MECHANISM in the component.

### 2.9 Reporting — `print_results` (466–482), `populateTestCase` (484–576), JSON

`print_results` marks `*` with the same rule as the verdict. The JSON
`permutationTestResults` carries `iteration` 0/1/2 = C0/C1/C2 as doubles with
`dataLayout` (`input` | `rows` | `columns`, repair 25fbb54). Because of early
termination these are PARTIAL counts (e.g. P1 `avgCollision` 6/0/39 means 6 of 45, not 6
of 10 000); the number of permutations evaluated per statistic is only recoverable as
C0+C1+C2 and is not named. A consumer reading C0 as "out of 10 000" misreads the rank by
two orders of magnitude. Neutral for the verdict; a reporting note. The 256-bit seed is
not recorded, so a verdict cannot be reproduced or audited after the fact (two runs on
identical input differed in 19/19 counter rows — `analysis-iid-perm-compare.log`,
"seed liveness").

### 2.10 Gating in `iid_main.cpp` (480–546)

`perm_test_pass = false` unless both `chi_square_test_pass && len_LRS_test_pass` (515);
`iid_test_suite_pass = chi && lrs && perm` (529–530); failure → `errorLevel 2`, exit 1, no
`hAssessed` (534–546). Fail-closed; this is the documented fail-closed battery
(FORK-DIVERGENCE §D-5 / #252), not a divergence to report. The N-02 view (378–386)
redirects `symbols`, `rawsymbols`, `len = blen`, `alph_size = 2`, `word_size = 1`,
`maxsymbol = 1` for `-c`; `testdata` is copied AFTER the `-t` truncation of `blen` (343),
so the battery and `h'` use the same bit count. `testdata.len > INT_MAX` is refused (393)
because the battery indexes with `int`. The `-c` view's `maxsymbol = 1` is sound: two
distinct symbols differ in some bit, so both bit values are present.

### 2.11 Concurrency (578–729)

Shared: `C` (written only inside `critical(resultUpdate)`), `t` (read-only after 608),
`test_status` (written inside the critical section at 673, READ outside it by
`run_tests` at 658 and by the helpers), `completed` (incremented inside the critical
section at 679 AND via `#pragma omp atomic` at 722–723 — two different mechanisms on one
variable, so increments can be lost). Private: `data`, `rawdata`, `tp`, the RNG state,
`passed_count`. The `test_status` and `completed` races are formally UB but benign: a
stale `true` only causes a statistic to be computed and then not counted (the critical
section re-checks 664), and `completed` only drives the progress line. A TSan build would
report both. No effect on counts or verdict.

### 2.12 Minimum legal sample count and widths

At L = 10^6: width 1 gives 125 000 Conversion-I/II blocks (p ≤ 32 ≪ 125 000); collisions
are guaranteed (k ≤ 256); compression message ≤ 4 MB; all asserts hold. Width 8 under
`-c -a`: L = 8×10^6 bits, same shapes ×8 (the documented 40-minute cost in the N-02 row).
No statistic is skipped or degenerate at the minimum; no NaN/inf can arise except the
empty-collision case excluded above; no `log` is taken.

---

## 3. Prior repairs touching this component, and how to break each

| repair | where | how I would try to break it |
|---|---|---|
| **N-02** (134d377) `-c` runs §5 on the bitstring | iid_main.cpp:378–414 | `-c -t` on 8-bit data (view must be 10^6 bits, `h'` on the same 10^6); `-c -l idx,n`; `-c` on width-1 input (view ≡ data, verdict distribution must match `-i`); `-c` on a sparse 8-bit alphabet (e.g. {0x0F,0xF0} → `maxsymbol` must be 1 not 0xF0, compression buffer 2 chars/bit); `-c` with `blen` just above `INT_MAX` is refused — check 2^31−8 bits is NOT refused and 2^31+8 is. The regression (regression-271.sh) runs 10 000 samples without `-t`; the `-t` and `-l` variants are uncovered. |
| **N-01** (c8799f4) m = 1 fails the chi-square battery | chi_square_tests.h:488–499, 655–672 (gates the battery) | Outside this file set but it decides whether permutations run. `return true` at :531 on the applied path (checked). Attack: datasets with `min_p^2·(L/2)` straddling 5 (3162 vs 3163 ones in 10^6) — the boundary uses integer division `sample_size / m`; probe L not divisible by m. |
| **#252 / fail-closed battery** (007d0e7, D-5) | iid_main.cpp:514–546; restart_main.cpp:1123–1160 | Restart: rows pass chi/LRS and columns fail → `permutation_tests` must not run at all (it runs only if BOTH pass, 1125); rows perm pass + columns perm fail → `perm_test_pass` false and no IID award (1135–1137). Mutate `perm_test_pass = true` default and confirm regression-iid-failclosed.sh catches it. |
| **N-10** (094189c) median of translated indices | utils.h:917–940 | Even-L half-integer median: exactly 250 000 of each of 4 symbols (sorted middle two are indices 1 and 2 → 1.5); compare `numRunsMedian`/`lenRunsMedian` against the Python transcription. Sparse alphabet {0,7,200,255} width 8 with the same counts: translated median 1.5, raw would be 103.5 — both must give identical S′ (monotonicity argument above). |
| **25fbb54** `dataLayout` labels | permutation_tests.h:484–495 | `ea_restart -i -o` must yield 6 results labelled rows×3 + columns×3; `ea_iid -o` exactly 3 labelled `input`. Label-anchored read (rule 5). |
| **C14 placeholder + seed() exit(-1)** | utils.h:797–800; iid_main.cpp:230 | With `-o` and `/dev/urandom` unreadable the placeholder must remain (errorLevel −1). Untestable without root here; `EA_TEST_RANDOM_SOURCE` does not reach `seed()` (OC-121's hook covers only the temp-file suffix) — a testability gap, not a defect. |
| **OC-53 bit-identity exclusion** of `permutationTestResults` | audits/BUG-REPAIR-GUIDE.md:395–405 | The exclusion rests on "the field varies run to run". Re-measured here: 19/19 rows vary on identical input. The comparator must still be shown to catch a perturbation in the UNPERMUTED statistics if those were ever recorded (they are not; only counts are). |

---

## 4. Edge-case inputs that distinguish a correct from an incorrect implementation

Each names the construction, what a correct implementation does, and what a WRONG one
would do — with the wrong direction marked where it would report higher entropy (an IID
acceptance routes to the IID track's MCV figure, which is above the non-IID minimum).

1. **Two-valued non-{0,1} bytes vs. the same sequence as bits.** `perm-p3` construction
   at 10^6: bytes {3,200} width 8, and the identical Bernoulli sequence as {0,1} width 1.
   Correct: identical 19 unpermuted statistics up to the affine excursion factor 197 and
   the compression digit strings; identical verdict distribution. Wrong: Conversion I/II
   applied to raw 3/200 (block sums 1600, bytes wrapping in `uint8_t`), `dups[200]` out of
   a k = 2 table (memory error). Direction of the wrong case: crash or random.
2. **All-ties statistic.** 10^6 uniform 3-bit symbols: `maxCollision` is k+1 = 9 for the
   original and essentially every permutation (P2 showed C = 0/6/0). Correct: passes that
   statistic after 6 ties (spec: C0+C1 = 10 000 > 5, C0 = 0 < 9995). Wrong: an
   implementation that counts ties as "T ≥ Ti" into C0 would fail it (understates);
   one that excludes ties from C0+C1 would fail it too.
3. **Extreme-low-rank construction that survives the deterministic gates.** 10^6 bits,
   b_i = b_{i−64} with probability 0.75, fresh otherwise (lag 64 bits = 8 Conversion-I
   blocks → `periodicity(8)`/`covariance(8)`; invisible to the m ≤ 11-bit chi-square
   tuples and barely visible to LRS). Correct: periodicity(8) original ≫ every permutation
   → C0 = 0, C1 = 0 → **FAIL** by C0+C1 ≤ 5. Wrong: a reversed comparison (`tp < t` into
   C0) would see C0 = 10 000 and ALSO fail (C0 ≥ 9995) — so pair it with the mirror:
   b_i ≠ b_{i−64} w.p. 0.75 (anti-correlation → original periodicity(8) ≪ permutations →
   correct FAIL via C0 ≥ 9995; an implementation that implemented only the C0+C1 ≤ 5 arm
   would PASS it — **overstates**). Record which stage decided (rule 18).
4. **Boundary of the counting rule.** Not constructible from data (the counts are random),
   but constructible by MUTATION of the binary (rule 7): change `<= 5` to `< 5` at
   permutation_tests.h:736 and confirm the regression that asserts a pass/fail on a
   borderline fixture flips; the baseline must be shown passing first.
5. **Conversion-order check.** 10^6 bits where bit 8j+1 = bit 8j (perfect within-block
   pairing, otherwise fair). Correct (shuffle bits, THEN convert): the original's
   Conversion-II bytes have only 64 distinct values (bits 0/1 equal), so `avgCollision`
   is far below every permutation's → FAIL (if chi-square m = 2 tuples do not already
   reject — they will; so run this one only to observe that the battery was skipped, and
   use it as the negative control for item 3's "reached the permutation stage" claim).
   Wrong (convert, then shuffle bytes): the within-byte structure survives every
   permutation → ties/near-ties → PASS — **overstates**.
6. **Even-length median.** Exactly 250 000 of each of 4 symbols (shuffled with a fixed
   seed), width 2 and width 8 as {0,7,200,255}. Correct: translated median 1.5; S′ as
   the Python transcription. Wrong: median of raw values (103.5) gives the same S′ here —
   so to DISTINGUISH add one extra sample so L is odd and the middle index is 2 → the
   median is a symbol value and `≥` vs `>` at the median matters: 250 000 ×{0,1}, 250 001
   ×{2}, 250 000 ×{3}: S′ must put every 2 into +1.
7. **Minimum legal count.** Exactly 1 000 000 fair bits (width 1) and 1 000 000 uniform
   bytes (width 8) must complete the battery (positive controls, already in
   regression-iid-failclosed.sh); 999 999 must be refused at intake with no battery run
   (negative control for the intake, not for this component).
8. **Thread-count independence.** The same 10^6-bit IID input under `OMP_NUM_THREADS` =
   1, 2, 8: the DISTRIBUTION of C0/C1/C2 over, say, 10 runs each must not depend on the
   thread count. The `xoshiro_jump` defect is the only thread-indexed code; expectation:
   no observable effect (the model shows the states are nonzero and the per-thread shuffle
   is still uniform). This is the measurement that would upgrade or retire the suspicion.
9. **Compression-failure injection (harness, not input).** An `LD_PRELOAD`/`DYLD_INSERT`
   shim making `BZ2_bzBuffToBuffCompress` return `BZ_MEM_ERROR` for every call. Correct
   behaviour per the fail-closed posture of this fork would be a refusal; the code will
   PASS the compression statistic with C = 0/6/0 (vacuous ties) — demonstrating the
   mechanism in §2.8 without needing 10^9 samples. Negative control: the same shim
   failing only the first call → C0 = 10 000 → FAIL.

---

## 5. What this analysis does not establish

- Nothing above the 20 000-sample probes was executed; the 10^6-sample claims are
  derived from the code and from the shapes of the arrays, not measured in this phase.
- The Python transcription is my own, written from the spec text; it is checked against
  the spec's ten worked examples but is not the audit's `py90b` reference.
- The LLP64 and `dest_len`-wrap mechanisms are derived from the declared types and the
  arithmetic, not reproduced; both are unreachable at the target profile on this host.
- The `xoshiro_jump` finding is a code-vs-comment deviation confirmed by a model of the
  code, not by running the binary with ≥ 3 threads; its statistical harmlessness is an
  argument from the generator's single-cycle structure, not a measurement.
- The test power of §5.1 itself (what dependence the 19 statistics cannot see — e.g. a
  lag-3 arithmetic relation s_{i+3} = s_i + 1 mod 256, which no statistic here measures
  and §5.2's pair test does not either) is a property of the standard; see
  memory note "SP 800-90B cannot see a DRBG". It is an attack on the method, not on
  this implementation, and is listed under attack ideas for the execution phase.

## 6. Artefacts

- `logs/analysis/iid-perm-ref.py` — spec transcription + `--selftest` (Examples 1–10,
  conversions): `logs/analysis-iid-perm-ref-selftest.log` (15/15 PASS, exit 0).
- `logs/analysis/iid-perm-gen.py` — probe generator; hashes in
  `logs/analysis-iid-perm-corpus-sha256.log`; inputs in `corpus/perm-p{1,2,3}-*.bin`.
- `logs/analysis-iid-perm-cpp-p1-w1-run{A,B}.log`, `-p2-w3.log`, `-p3-w8.log` — full
  `ea_iid -vvv` output with `exit=` appended (all 0, all 19 statistics present, verdicts
  Passed).
- `logs/analysis-iid-perm-ref-p{1,2,3}-*.json` — Python statistics.
- `logs/analysis/iid-perm-compare.py` → `logs/analysis-iid-perm-compare.log`
  (57/57 ok; 19/19 counter rows differ A vs B; unpermuted statistics identical A vs B).
- `logs/analysis/iid-perm-rng-model.py` → `logs/analysis-iid-perm-rng-model.log`
  (jump k ≥ 2 ≠ canonical; k = 2 = S1 ⊕ S2; Lemire unbiased 255/255; FY 24/24).
