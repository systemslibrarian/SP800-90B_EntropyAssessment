## Summary

`cpp/selftest/selftest` is the shipped regression check for `ea_non_iid`, but it has two gaps:

1. **It never compares the final figures.** `H_original`, `H_bitstring` and `Assessed min entropy` are never checked against `refdata`, even though their reference values are in the `.res` files. Only the per-estimator lines are compared.
2. **Its exit status reflects only the last file.** A mismatch in any of the first ten reference files still ends with exit status 0.

As a result, a build that computes the final §3.1.3 combination wrongly passes the selftest with output identical to a correct build, including when the reported entropy goes **up**.

## Where

`cpp/selftest/compareresults.pl`, `resultsHash` (lines 65-66), keeps a line only if it contains `Estimate:` or `Assessed` **and** matches `^label = number$`. The three summary lines printed by `ea_non_iid -vv` (`non_iid_main.cpp:511, 516, 519`) all fail that filter:

```
H_bitstring = 0.90423268189731187       <- no "Estimate:"/"Assessed" keyword
H_original = 7.8651180028995897         <- no keyword
Assessed min entropy: 7.233861455178495 <- has "Assessed", but uses ':' instead of ' = '
```

The comparator drops them from both the new output and the reference. On `truerand_8bit.res`, 94 per-estimator lines are compared and these 3 never are.

`cpp/selftest/selftest` calls `compareresults.pl` once per file inside a `for` loop and never combines the return codes, so the script's exit status is that of the final `truerand_8bit` comparison.

## Reproduction

Fresh clone of master `87c104d`, Linux x86-64, g++ 13.3, stock Makefile:

```sh
git clone https://github.com/usnistgov/SP800-90B_EntropyAssessment.git && cd SP800-90B_EntropyAssessment/cpp
make non_iid
cd selftest && ./selftest; echo "exit=$?"; cd ..      # baseline: 11 x "Maximum delta" (<= 1.0e-13), exit 0

# Mutant 1: drop the n x H_bitstring term from the final assessment
sed -i 's/h_assessed = min(h_assessed, H_bitstring \* data.word_size);/\/\/ mutant 1/' non_iid_main.cpp
make non_iid && cd selftest && ./selftest; echo "exit=$?"
grep -h '^Assessed min entropy' refdata/normal.res normal.res
cd .. && git checkout non_iid_main.cpp

# Mutant 2: drop H_original from the final assessment
perl -0pi -e 's/    if \(initial_entropy\) \{\n        h_assessed = min\(h_assessed, H_original\);\n    \}\n/    \/\/ mutant 2\n/' non_iid_main.cpp
make non_iid && cd selftest && ./selftest; echo "exit=$?"
grep -h '^Assessed min entropy' refdata/ringOsc-nist.res ringOsc-nist.res
cd .. && git checkout non_iid_main.cpp && make non_iid

# Exit status: a mismatch in the first file only
cd selftest && sed -i 's/^\(Literal Most Common Value Estimate: p_u = \).*/\10.9/' refdata/biased-random-bits.res
./selftest; echo "exit=$?"; git checkout refdata/
```

## Result

**Both mutants.** The selftest output is byte-for-byte the same as the baseline: the same 11 `Maximum delta` lines, no `Significant difference`, exit 0. Meanwhile the reported figure changes:

| File | refdata `Assessed` | Mutant 1 | Mutant 2 |
|---|---|---|---|
| normal.bin | 4.1000957831103086 | **5.529117785448844** | 4.10009578311034 |
| truerand_8bit.bin | 7.233861455178495 | **7.8651180028995897** | 7.233861455178495 |
| biased-random-bytes.bin | 0.25774087100648113 | **0.29115980449860812** | 0.25774087100648113 |
| rand8_short.bin | 5.8608937444852494 | **6.6364412870839109** | 5.8608937444852494 |
| ringOsc-nist.bin | 0.12644573619605429 | 0.12644573619604868 | **1** |
| biased-random-bits.bin | 0.017766579116465196 | 0.017766579116465193 | **1** |
| truerand_1bit.bin | 0.82967708323406131 | 0.82967708323411438 | **1** |

- Mutant 1 raises 6 of the 11 reference figures.
- Mutant 2 sets all 5 binary reference files to 1.0.
- Neither is detected.

**Edited `refdata`.** The script prints `biased-random-bits.res: Significant difference for Literal Most Common Value Estimate: p_u (... delta: 0.0803487222429431)` and then exits **0**.

## Expected

- `H_original`, `H_bitstring` and `Assessed min entropy` are compared like the other values. The reference values are already present in `refdata/*.res`.
- A significant difference, or a missing value, in **any** file makes `./selftest` exit non-zero.

## Why it matters

The per-estimator checks protect each estimator, but nothing protects the step that turns them into the reported H_I (§3.1.3): the `min()` over estimators, the `n × H_bitstring` term, and which estimators are included. Changes to exactly that step (for example the fix proposed for #253) currently pass the selftest regardless of what they do to the reported figure. Users who run the selftest from a script and check its exit status also miss failures in 10 of the 11 files.

The estimator code is not affected. This concerns only the regression check.

## Possible fix

- In `resultsHash`, also accept `label: value`, so `Assessed min entropy`, `H_original` and `H_bitstring` are matched, or match those three labels explicitly.
- Consider treating keys present only in the new output as failures too.
- In `selftest`, accumulate the status, for example `./compareresults.pl ... || status=1` inside the loop and `exit $status` at the end.

Either mutant above then makes `./selftest` exit non-zero.

Found during an AI-assisted audit; independently reproduced on a fresh clone of upstream 87c104d0ed4c with the commands above.
