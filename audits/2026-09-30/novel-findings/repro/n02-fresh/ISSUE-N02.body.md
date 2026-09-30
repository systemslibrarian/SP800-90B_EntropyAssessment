The README describes `-c` as:

> `-c`: Indicates the data is conditioned, and should only be assessed as a bitstring.

SP 800-90B says the same about the conditioned sequential dataset:

> §3.1.1, item 2: "The output of the conditioning component shall be concatenated in the order in which it was generated and treated as a binary string for testing purposes."
>
> §3.1.5.2: "The output of the conditioning component (n_out) shall be treated as a binary string, for purposes of the entropy estimation."

## What happens

Under `ea_iid -c`, `h'` is computed from the bitstring, but the three IID test batteries are run on the multi-bit symbols as read from the file (line numbers at 87c104d):

- `cpp/iid_main.cpp:282`: `H_bitstring = most_common(data.bsymbols, data.blen, 2, ...)` (the bitstring)
- `cpp/iid_main.cpp:316`: `chi_square_tests(data.symbols, sample_size, alphabet_size, ...)`
- `cpp/iid_main.cpp:334`: `len_LRS_test(data.symbols, sample_size, alphabet_size, ...)`
- `cpp/iid_main.cpp:352`: `permutation_tests(&data, ...)`, which tests `dp->symbols` (`cpp/iid/permutation_tests.h:605`)

With `bits_per_symbol > 1`, the IID decision is made on the multi-bit symbols, not on the bitstring whose `h'` is reported. Dependence between bits within a symbol is therefore not visible to the IID tests.

## Reproduction

Upstream `master` at 87c104d0ed4cbc96103e7b8b38d6f2c7e0a6b289, unmodified Makefile (`make iid non_iid`), Ubuntu 24.04, g++ 13.3.0, x86-64.

`gen.py` writes 1,000,000 bytes, each `(x << 4) | x` for a uniform 4-bit `x`. The high nibble duplicates the low nibble, so the bytes take exactly 16 equiprobable values: 4 bits of min-entropy per 8-bit byte, i.e. 0.5 bit/bit by construction. It also writes the same data as a bitstring, one bit per byte, MSB first:

```python
import random
r = random.Random(4242)
data = bytes(((x << 4) | x) for x in (r.randrange(16) for _ in range(1000000)))
open('nibdup.bin', 'wb').write(data)
open('nibdup_bits.bin', 'wb').write(bytes((b >> k) & 1 for b in data for k in range(7, -1, -1)))
```

```
sha256  nibdup.bin       4f043adf8eafe4ed8667b16e99c19dabdfe57c1a49cd46deca7d02ffb6e2fc25
sha256  nibdup_bits.bin  f90b9c48fd0fadae4143a892f75525b3764c86dab86356f8cc91fb8690a13299

./ea_iid -c -v nibdup.bin 8           # conditioned data as 8-bit symbols
./ea_non_iid -c -v nibdup.bin 8       # same data, non-IID track
./ea_iid -c -v nibdup_bits.bin 1      # same data supplied as a bitstring
```

## Actual

`./ea_iid -c -v nibdup.bin 8` (exit 0; JSON `"passedChiSquareTests": true`, `"passedLongestRepeatedSubstringTest": true`, `"passedIidPermutationTests": true`):

```
Loaded 1000000 samples of 16 distinct 8-bit-wide symbols
Number of Binary samples: 8000000
...
h': 0.998640
Chi square independence
	score = 291.754474
	degrees of freedom = 240
	p-value = 0.012514
Chi square goodness of fit
	score = 130.884476
	degrees of freedom = 135
	p-value = 0.584088
** Passed chi square tests
...
	Length of LRS: 9
	Pr(X >= 1): 0.999308
** Passed length of longest repeated substring test
...
** Passed IID permutation tests
```

`./ea_non_iid -c -v nibdup.bin 8` (exit 0), the non-IID track's estimate, conservative relative to the 0.5 bit/bit of the construction:

```
h': 0.403507
```

`./ea_iid -c -v nibdup_bits.bin 1`, the same bits supplied directly:

```
Loaded 8000000 samples of 2 distinct 1-bit-wide symbols
...
h': 0.998640
igamc: UNDERFLOW
Chi square independence
	score = 2613463.648964
	degrees of freedom = 2046
	p-value = 0.000000
Chi square goodness of fit
	score = 14.884770
	degrees of freedom = 9
	p-value = 0.094150
** Failed chi square tests
...
	Length of LRS: 75
	Pr(X >= 1): 0.000000
** Failed length of longest repeated substring test
```

(I stopped this run during the permutation stage, which on 8,000,000 samples was projected to take many hours; the chi-square and LRS results above already fail.)

## Expected

With `-c`, the IID tests are applied to the conditioned-output bitstring, the same bits `h'` is computed from. For this data, the conditioned-output bitstring fails both the chi-square and LRS tests (third command). `ea_iid -c nibdup.bin 8` should therefore not report the dataset as passing the IID tests.

## Notes

- Supplying the conditioned output at 1 bit per sample avoids the problem (third command). However, `-c` currently accepts wider symbols without a warning, even though the README says conditioned data "should only be assessed as a bitstring".
- The JSON `hAssessed` field shows 8.0 for the first command at this verbosity. That is the separate #251. The figure compared above is `h'` (JSON `hBitstring`).

## Possible remedies

Either of these would remove the mismatch:

1. When `-c` is given, run the chi-square, LRS and permutation tests on the bitstring (`data.bsymbols`, `data.blen`) rather than on `data.symbols`.
2. Reject `-c` when `bits_per_symbol > 1`, with a message asking for the conditioned output as one bit per sample.

Found during an AI-assisted audit; independently reproduced on a clean build of upstream 87c104d0ed4c and verified against the implementation and SP 800-90B.
