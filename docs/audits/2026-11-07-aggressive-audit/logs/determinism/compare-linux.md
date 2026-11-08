# macOS host vs Linux-matched reference -- compare_linux.py

Written 2026-11-08T17:04:24-05:00. Reference side: **refdata** (cpp/selftest/refdata, which the strict x86-64 CI suite matched to 1e-10 (06-run-all-checks-strict.log: selftest PASS)). Host side: every run under /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/non_iid/.

Platform block requested: uname -s `Darwin`, uname -m `arm64`, compiler `Apple clang version 21.0.0 (clang-2100.4.1.1)` -> MATCHED block `platform Darwin arm64 Apple clang` with 8 rows

| class | count | meaning |
|---|---|---|
| EXACT | 2040 | identical decimal text |
| FORMAT | 192 | same double, different print width (17 vs 22 significant digits); not a numeric difference |
| SUBTHRESHOLD | 292 | 0 < delta < 1e-10: inside the band in which Linux itself was matched; not attributable |
| KNOWN | 32 | in the manifest for this platform, within tolerance |
| NEW / EXCEEDS / STRUCTURAL / varying | 0 | **FLAGGED** |
| MISSING manifest rows | 0 | listed rows never observed (completeness) |

Cases compared: 8 of 11 bin/ files; host runs read: 32. The four corpus cases have no refdata and are host-only (RESULTS.md).

## KNOWN platform deltas observed (manifest rows), with headroom

| case | host run | estimator | field | reference | host | perl delta | tolerance | observed-in-manifest | headroom tol/delta |
|---|---|---|---|---|---|---|---|---|---|
| biased-random-bytes | t1-r1 | Bitstring Lag Prediction Estimate | min entropy | `0.042001643639251546` | `0.042001643772653606` | 1.33402e-10 | 1e-09 | 1.33402e-10 | 7.5x |
| biased-random-bytes | t1-r1 | Bitstring MultiMCW Prediction Estimate | P_local | `0.9713579012997926` | `0.97135790142486211` | 1.2507e-10 | 1e-09 | 1.2507e-10 | 8.0x |
| biased-random-bytes | t1-r1 | Bitstring MultiMCW Prediction Estimate | min entropy | `0.041925133646315872` | `0.04192513346055822` | 1.85758e-10 | 1e-09 | 1.85758e-10 | 5.4x |
| biased-random-bytes | t1-r1 | Bitstring MultiMMC Prediction Estimate | P_local | `0.9713578878098017` | `0.97135788805618295` | 2.46381e-10 | 1e-09 | 2.46381e-10 | 4.1x |
| biased-random-bytes | t1-r1 | Bitstring MultiMMC Prediction Estimate | min entropy | `0.041925153682126653` | `0.041925153316192523` | 3.65934e-10 | 1e-09 | 3.65934e-10 | 2.7x |
| biased-random-bytes | t1-r1 | Literal Lag Prediction Estimate | P_local | `0.72383949597417785` | `0.72383949613215592` | 1.57978e-10 | 1e-09 | 1.57978e-10 | 6.3x |
| biased-random-bytes | t1-r1 | Literal Lag Prediction Estimate | min entropy | `0.46625826502784795` | `0.46625826471297949` | 3.14868e-10 | 1e-09 | 3.14868e-10 | 3.2x |
| biased-random-bytes | t10-r1 | Bitstring Lag Prediction Estimate | min entropy | `0.042001643639251546` | `0.042001643772653606` | 1.33402e-10 | 1e-09 | 1.33402e-10 | 7.5x |
| biased-random-bytes | t10-r1 | Bitstring MultiMCW Prediction Estimate | P_local | `0.9713579012997926` | `0.97135790142486211` | 1.2507e-10 | 1e-09 | 1.2507e-10 | 8.0x |
| biased-random-bytes | t10-r1 | Bitstring MultiMCW Prediction Estimate | min entropy | `0.041925133646315872` | `0.04192513346055822` | 1.85758e-10 | 1e-09 | 1.85758e-10 | 5.4x |
| biased-random-bytes | t10-r1 | Bitstring MultiMMC Prediction Estimate | P_local | `0.9713578878098017` | `0.97135788805618295` | 2.46381e-10 | 1e-09 | 2.46381e-10 | 4.1x |
| biased-random-bytes | t10-r1 | Bitstring MultiMMC Prediction Estimate | min entropy | `0.041925153682126653` | `0.041925153316192523` | 3.65934e-10 | 1e-09 | 3.65934e-10 | 2.7x |
| biased-random-bytes | t10-r1 | Literal Lag Prediction Estimate | P_local | `0.72383949597417785` | `0.72383949613215592` | 1.57978e-10 | 1e-09 | 1.57978e-10 | 6.3x |
| biased-random-bytes | t10-r1 | Literal Lag Prediction Estimate | min entropy | `0.46625826502784795` | `0.46625826471297949` | 3.14868e-10 | 1e-09 | 3.14868e-10 | 3.2x |
| biased-random-bytes | t10-r2 | Bitstring Lag Prediction Estimate | min entropy | `0.042001643639251546` | `0.042001643772653606` | 1.33402e-10 | 1e-09 | 1.33402e-10 | 7.5x |
| biased-random-bytes | t10-r2 | Bitstring MultiMCW Prediction Estimate | P_local | `0.9713579012997926` | `0.97135790142486211` | 1.2507e-10 | 1e-09 | 1.2507e-10 | 8.0x |
| biased-random-bytes | t10-r2 | Bitstring MultiMCW Prediction Estimate | min entropy | `0.041925133646315872` | `0.04192513346055822` | 1.85758e-10 | 1e-09 | 1.85758e-10 | 5.4x |
| biased-random-bytes | t10-r2 | Bitstring MultiMMC Prediction Estimate | P_local | `0.9713578878098017` | `0.97135788805618295` | 2.46381e-10 | 1e-09 | 2.46381e-10 | 4.1x |
| biased-random-bytes | t10-r2 | Bitstring MultiMMC Prediction Estimate | min entropy | `0.041925153682126653` | `0.041925153316192523` | 3.65934e-10 | 1e-09 | 3.65934e-10 | 2.7x |
| biased-random-bytes | t10-r2 | Literal Lag Prediction Estimate | P_local | `0.72383949597417785` | `0.72383949613215592` | 1.57978e-10 | 1e-09 | 1.57978e-10 | 6.3x |
| biased-random-bytes | t10-r2 | Literal Lag Prediction Estimate | min entropy | `0.46625826502784795` | `0.46625826471297949` | 3.14868e-10 | 1e-09 | 3.14868e-10 | 3.2x |
| biased-random-bytes | t2-r1 | Bitstring Lag Prediction Estimate | min entropy | `0.042001643639251546` | `0.042001643772653606` | 1.33402e-10 | 1e-09 | 1.33402e-10 | 7.5x |
| biased-random-bytes | t2-r1 | Bitstring MultiMCW Prediction Estimate | P_local | `0.9713579012997926` | `0.97135790142486211` | 1.2507e-10 | 1e-09 | 1.2507e-10 | 8.0x |
| biased-random-bytes | t2-r1 | Bitstring MultiMCW Prediction Estimate | min entropy | `0.041925133646315872` | `0.04192513346055822` | 1.85758e-10 | 1e-09 | 1.85758e-10 | 5.4x |
| biased-random-bytes | t2-r1 | Bitstring MultiMMC Prediction Estimate | P_local | `0.9713578878098017` | `0.97135788805618295` | 2.46381e-10 | 1e-09 | 2.46381e-10 | 4.1x |
| biased-random-bytes | t2-r1 | Bitstring MultiMMC Prediction Estimate | min entropy | `0.041925153682126653` | `0.041925153316192523` | 3.65934e-10 | 1e-09 | 3.65934e-10 | 2.7x |
| biased-random-bytes | t2-r1 | Literal Lag Prediction Estimate | P_local | `0.72383949597417785` | `0.72383949613215592` | 1.57978e-10 | 1e-09 | 1.57978e-10 | 6.3x |
| biased-random-bytes | t2-r1 | Literal Lag Prediction Estimate | min entropy | `0.46625826502784795` | `0.46625826471297949` | 3.14868e-10 | 1e-09 | 3.14868e-10 | 3.2x |
| ringOsc-nist | t1-r1 | Literal MultiMCW Prediction Estimate | min entropy | `0.29051922736594488` | `0.290519227211259` | 1.54686e-10 | 1e-09 | 1.54686e-10 | 6.5x |
| ringOsc-nist | t10-r1 | Literal MultiMCW Prediction Estimate | min entropy | `0.29051922736594488` | `0.290519227211259` | 1.54686e-10 | 1e-09 | 1.54686e-10 | 6.5x |
| ringOsc-nist | t10-r2 | Literal MultiMCW Prediction Estimate | min entropy | `0.29051922736594488` | `0.290519227211259` | 1.54686e-10 | 1e-09 | 1.54686e-10 | 6.5x |
| ringOsc-nist | t2-r1 | Literal MultiMCW Prediction Estimate | min entropy | `0.29051922736594488` | `0.290519227211259` | 1.54686e-10 | 1e-09 | 1.54686e-10 | 6.5x |

## SUBTHRESHOLD differences (listed, not flagged)

| case | host run | estimator | field | reference | host | abs delta | perl delta |
|---|---|---|---|---|---|---|---|
| biased-random-bits | t1-r1 | Assessed min entropy |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t1-r1 | H_original |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t1-r1 | Literal Collision Estimate | min entropy | `0.028513792826295892` | `0.028513792826254068` | 4.18242e-14 | 4.18242e-14 |
| biased-random-bits | t1-r1 | Literal Collision Estimate | p | `0.98042977738018067` | `0.98042977738020909` | 2.84217e-14 | 2.84217e-14 |
| biased-random-bits | t1-r1 | Literal Collision Estimate | sigma-hat | `0.19380289702168033` | `0.19380289702167994` | 3.88578e-16 | 3.88578e-16 |
| biased-random-bits | t1-r1 | Literal Compression Estimate | min entropy | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t1-r1 | Literal Compression Estimate | p | `0.92877466571109557` | `0.92877466571109946` | 3.88578e-15 | 3.88578e-15 |
| biased-random-bits | t1-r1 | Literal LRS Estimate | min entropy | `0.055881394003087538` | `0.055881394003087531` | 6.93889e-18 | 6.93889e-18 |
| biased-random-bits | t1-r1 | Literal LZ78Y Prediction Estimate | min entropy | `0.028635020154766919` | `0.028635020154766915` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t1-r1 | Literal Lag Prediction Estimate | P_local | `0.97225067522872544` | `0.97225067522318498` | 5.54046e-12 | 5.54046e-12 |
| biased-random-bits | t1-r1 | Literal Lag Prediction Estimate | min entropy | `0.040599763274887825` | `0.040599763283109144` | 8.22132e-12 | 8.22132e-12 |
| biased-random-bits | t1-r1 | Literal Markov Estimate | min entropy | `0.029123023940057065` | `0.029123023940057061` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t1-r1 | Literal Markov Estimate | p-hat_max | `0.075480769220803628` | `0.075480769220803642` | 1.38778e-17 | 1.38778e-17 |
| biased-random-bits | t1-r1 | Literal Most Common Value Estimate | min entropy | `0.028633069781464748` | `0.028633069781464744` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t1-r1 | Literal t-Tuple Estimate | min entropy | `0.026489257053631029` | `0.026489257053631025` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r1 | Assessed min entropy |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t10-r1 | H_original |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t10-r1 | Literal Collision Estimate | min entropy | `0.028513792826295892` | `0.028513792826254068` | 4.18242e-14 | 4.18242e-14 |
| biased-random-bits | t10-r1 | Literal Collision Estimate | p | `0.98042977738018067` | `0.98042977738020909` | 2.84217e-14 | 2.84217e-14 |
| biased-random-bits | t10-r1 | Literal Collision Estimate | sigma-hat | `0.19380289702168033` | `0.19380289702167994` | 3.88578e-16 | 3.88578e-16 |
| biased-random-bits | t10-r1 | Literal Compression Estimate | min entropy | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t10-r1 | Literal Compression Estimate | p | `0.92877466571109557` | `0.92877466571109946` | 3.88578e-15 | 3.88578e-15 |
| biased-random-bits | t10-r1 | Literal LRS Estimate | min entropy | `0.055881394003087538` | `0.055881394003087531` | 6.93889e-18 | 6.93889e-18 |
| biased-random-bits | t10-r1 | Literal LZ78Y Prediction Estimate | min entropy | `0.028635020154766919` | `0.028635020154766915` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r1 | Literal Lag Prediction Estimate | P_local | `0.97225067522872544` | `0.97225067522318498` | 5.54046e-12 | 5.54046e-12 |
| biased-random-bits | t10-r1 | Literal Lag Prediction Estimate | min entropy | `0.040599763274887825` | `0.040599763283109144` | 8.22132e-12 | 8.22132e-12 |
| biased-random-bits | t10-r1 | Literal Markov Estimate | min entropy | `0.029123023940057065` | `0.029123023940057061` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r1 | Literal Markov Estimate | p-hat_max | `0.075480769220803628` | `0.075480769220803642` | 1.38778e-17 | 1.38778e-17 |
| biased-random-bits | t10-r1 | Literal Most Common Value Estimate | min entropy | `0.028633069781464748` | `0.028633069781464744` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r1 | Literal t-Tuple Estimate | min entropy | `0.026489257053631029` | `0.026489257053631025` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r2 | Assessed min entropy |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t10-r2 | H_original |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t10-r2 | Literal Collision Estimate | min entropy | `0.028513792826295892` | `0.028513792826254068` | 4.18242e-14 | 4.18242e-14 |
| biased-random-bits | t10-r2 | Literal Collision Estimate | p | `0.98042977738018067` | `0.98042977738020909` | 2.84217e-14 | 2.84217e-14 |
| biased-random-bits | t10-r2 | Literal Collision Estimate | sigma-hat | `0.19380289702168033` | `0.19380289702167994` | 3.88578e-16 | 3.88578e-16 |
| biased-random-bits | t10-r2 | Literal Compression Estimate | min entropy | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t10-r2 | Literal Compression Estimate | p | `0.92877466571109557` | `0.92877466571109946` | 3.88578e-15 | 3.88578e-15 |
| biased-random-bits | t10-r2 | Literal LRS Estimate | min entropy | `0.055881394003087538` | `0.055881394003087531` | 6.93889e-18 | 6.93889e-18 |
| biased-random-bits | t10-r2 | Literal LZ78Y Prediction Estimate | min entropy | `0.028635020154766919` | `0.028635020154766915` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r2 | Literal Lag Prediction Estimate | P_local | `0.97225067522872544` | `0.97225067522318498` | 5.54046e-12 | 5.54046e-12 |
| biased-random-bits | t10-r2 | Literal Lag Prediction Estimate | min entropy | `0.040599763274887825` | `0.040599763283109144` | 8.22132e-12 | 8.22132e-12 |
| biased-random-bits | t10-r2 | Literal Markov Estimate | min entropy | `0.029123023940057065` | `0.029123023940057061` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r2 | Literal Markov Estimate | p-hat_max | `0.075480769220803628` | `0.075480769220803642` | 1.38778e-17 | 1.38778e-17 |
| biased-random-bits | t10-r2 | Literal Most Common Value Estimate | min entropy | `0.028633069781464748` | `0.028633069781464744` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t10-r2 | Literal t-Tuple Estimate | min entropy | `0.026489257053631029` | `0.026489257053631025` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t2-r1 | Assessed min entropy |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t2-r1 | H_original |  | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t2-r1 | Literal Collision Estimate | min entropy | `0.028513792826295892` | `0.028513792826254068` | 4.18242e-14 | 4.18242e-14 |
| biased-random-bits | t2-r1 | Literal Collision Estimate | p | `0.98042977738018067` | `0.98042977738020909` | 2.84217e-14 | 2.84217e-14 |
| biased-random-bits | t2-r1 | Literal Collision Estimate | sigma-hat | `0.19380289702168033` | `0.19380289702167994` | 3.88578e-16 | 3.88578e-16 |
| biased-random-bits | t2-r1 | Literal Compression Estimate | min entropy | `0.017766579116465196` | `0.017766579116464187` | 1.00961e-15 | 1.00961e-15 |
| biased-random-bits | t2-r1 | Literal Compression Estimate | p | `0.92877466571109557` | `0.92877466571109946` | 3.88578e-15 | 3.88578e-15 |
| biased-random-bits | t2-r1 | Literal LRS Estimate | min entropy | `0.055881394003087538` | `0.055881394003087531` | 6.93889e-18 | 6.93889e-18 |
| biased-random-bits | t2-r1 | Literal LZ78Y Prediction Estimate | min entropy | `0.028635020154766919` | `0.028635020154766915` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t2-r1 | Literal Lag Prediction Estimate | P_local | `0.97225067522872544` | `0.97225067522318498` | 5.54046e-12 | 5.54046e-12 |
| biased-random-bits | t2-r1 | Literal Lag Prediction Estimate | min entropy | `0.040599763274887825` | `0.040599763283109144` | 8.22132e-12 | 8.22132e-12 |
| biased-random-bits | t2-r1 | Literal Markov Estimate | min entropy | `0.029123023940057065` | `0.029123023940057061` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t2-r1 | Literal Markov Estimate | p-hat_max | `0.075480769220803628` | `0.075480769220803642` | 1.38778e-17 | 1.38778e-17 |
| biased-random-bits | t2-r1 | Literal Most Common Value Estimate | min entropy | `0.028633069781464748` | `0.028633069781464744` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bits | t2-r1 | Literal t-Tuple Estimate | min entropy | `0.026489257053631029` | `0.026489257053631025` | 3.46945e-18 | 3.46945e-18 |
| biased-random-bytes | t1-r1 | Bitstring Collision Estimate | min entropy | `0.072705888458523521` | `0.072705888458565959` | 4.24383e-14 | 4.24383e-14 |
| biased-random-bytes | t1-r1 | Bitstring Collision Estimate | p | `0.95085292480837325` | `0.95085292480834527` | 2.79776e-14 | 2.79776e-14 |
| biased-random-bytes | t1-r1 | Bitstring Collision Estimate | sigma-hat | `0.2916165711413341` | `0.29161657114133382` | 2.77556e-16 | 2.77556e-16 |
| biased-random-bytes | t1-r1 | Bitstring Compression Estimate | min entropy | `0.063135493215718444` | `0.063135493215717362` | 1.08247e-15 | 1.08247e-15 |
| biased-random-bytes | t1-r1 | Bitstring Compression Estimate | p | `0.76907011660379809` | `0.76907011660380153` | 3.44169e-15 | 3.44169e-15 |
| biased-random-bytes | t1-r1 | Bitstring LZ78Y Prediction Estimate | P_local | `0.97135789112696946` | `0.97135789116665106` | 3.96816e-11 | 3.96816e-11 |
| biased-random-bytes | t1-r1 | Bitstring LZ78Y Prediction Estimate | min entropy | `0.04192514875535195` | `0.041925148696415449` | 5.89365e-11 | 5.89365e-11 |
| biased-random-bytes | t1-r1 | Bitstring Lag Prediction Estimate | P_local | `0.9713063889472594` | `0.97130638885744536` | 8.9814e-11 | 8.9814e-11 |
| biased-random-bytes | t1-r1 | Bitstring Most Common Value Estimate | min entropy | `0.15182732507652347` | `0.15182732507652344` | 2.77556e-17 | 2.77556e-17 |
| biased-random-bytes | t1-r1 | H_original |  | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t1-r1 | Literal MultiMCW Prediction Estimate | min entropy | `0.3196462537659206` | `0.31964625376592054` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t1-r1 | Literal t-Tuple Estimate | min entropy | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t10-r1 | Bitstring Collision Estimate | min entropy | `0.072705888458523521` | `0.072705888458565959` | 4.24383e-14 | 4.24383e-14 |
| biased-random-bytes | t10-r1 | Bitstring Collision Estimate | p | `0.95085292480837325` | `0.95085292480834527` | 2.79776e-14 | 2.79776e-14 |
| biased-random-bytes | t10-r1 | Bitstring Collision Estimate | sigma-hat | `0.2916165711413341` | `0.29161657114133382` | 2.77556e-16 | 2.77556e-16 |
| biased-random-bytes | t10-r1 | Bitstring Compression Estimate | min entropy | `0.063135493215718444` | `0.063135493215717362` | 1.08247e-15 | 1.08247e-15 |
| biased-random-bytes | t10-r1 | Bitstring Compression Estimate | p | `0.76907011660379809` | `0.76907011660380153` | 3.44169e-15 | 3.44169e-15 |
| biased-random-bytes | t10-r1 | Bitstring LZ78Y Prediction Estimate | P_local | `0.97135789112696946` | `0.97135789116665106` | 3.96816e-11 | 3.96816e-11 |
| biased-random-bytes | t10-r1 | Bitstring LZ78Y Prediction Estimate | min entropy | `0.04192514875535195` | `0.041925148696415449` | 5.89365e-11 | 5.89365e-11 |
| biased-random-bytes | t10-r1 | Bitstring Lag Prediction Estimate | P_local | `0.9713063889472594` | `0.97130638885744536` | 8.9814e-11 | 8.9814e-11 |
| biased-random-bytes | t10-r1 | Bitstring Most Common Value Estimate | min entropy | `0.15182732507652347` | `0.15182732507652344` | 2.77556e-17 | 2.77556e-17 |
| biased-random-bytes | t10-r1 | H_original |  | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t10-r1 | Literal MultiMCW Prediction Estimate | min entropy | `0.3196462537659206` | `0.31964625376592054` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t10-r1 | Literal t-Tuple Estimate | min entropy | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t10-r2 | Bitstring Collision Estimate | min entropy | `0.072705888458523521` | `0.072705888458565959` | 4.24383e-14 | 4.24383e-14 |
| biased-random-bytes | t10-r2 | Bitstring Collision Estimate | p | `0.95085292480837325` | `0.95085292480834527` | 2.79776e-14 | 2.79776e-14 |
| biased-random-bytes | t10-r2 | Bitstring Collision Estimate | sigma-hat | `0.2916165711413341` | `0.29161657114133382` | 2.77556e-16 | 2.77556e-16 |
| biased-random-bytes | t10-r2 | Bitstring Compression Estimate | min entropy | `0.063135493215718444` | `0.063135493215717362` | 1.08247e-15 | 1.08247e-15 |
| biased-random-bytes | t10-r2 | Bitstring Compression Estimate | p | `0.76907011660379809` | `0.76907011660380153` | 3.44169e-15 | 3.44169e-15 |
| biased-random-bytes | t10-r2 | Bitstring LZ78Y Prediction Estimate | P_local | `0.97135789112696946` | `0.97135789116665106` | 3.96816e-11 | 3.96816e-11 |
| biased-random-bytes | t10-r2 | Bitstring LZ78Y Prediction Estimate | min entropy | `0.04192514875535195` | `0.041925148696415449` | 5.89365e-11 | 5.89365e-11 |
| biased-random-bytes | t10-r2 | Bitstring Lag Prediction Estimate | P_local | `0.9713063889472594` | `0.97130638885744536` | 8.9814e-11 | 8.9814e-11 |
| biased-random-bytes | t10-r2 | Bitstring Most Common Value Estimate | min entropy | `0.15182732507652347` | `0.15182732507652344` | 2.77556e-17 | 2.77556e-17 |
| biased-random-bytes | t10-r2 | H_original |  | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t10-r2 | Literal MultiMCW Prediction Estimate | min entropy | `0.3196462537659206` | `0.31964625376592054` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t10-r2 | Literal t-Tuple Estimate | min entropy | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t2-r1 | Bitstring Collision Estimate | min entropy | `0.072705888458523521` | `0.072705888458565959` | 4.24383e-14 | 4.24383e-14 |
| biased-random-bytes | t2-r1 | Bitstring Collision Estimate | p | `0.95085292480837325` | `0.95085292480834527` | 2.79776e-14 | 2.79776e-14 |
| biased-random-bytes | t2-r1 | Bitstring Collision Estimate | sigma-hat | `0.2916165711413341` | `0.29161657114133382` | 2.77556e-16 | 2.77556e-16 |
| biased-random-bytes | t2-r1 | Bitstring Compression Estimate | min entropy | `0.063135493215718444` | `0.063135493215717362` | 1.08247e-15 | 1.08247e-15 |
| biased-random-bytes | t2-r1 | Bitstring Compression Estimate | p | `0.76907011660379809` | `0.76907011660380153` | 3.44169e-15 | 3.44169e-15 |
| biased-random-bytes | t2-r1 | Bitstring LZ78Y Prediction Estimate | P_local | `0.97135789112696946` | `0.97135789116665106` | 3.96816e-11 | 3.96816e-11 |
| biased-random-bytes | t2-r1 | Bitstring LZ78Y Prediction Estimate | min entropy | `0.04192514875535195` | `0.041925148696415449` | 5.89365e-11 | 5.89365e-11 |
| biased-random-bytes | t2-r1 | Bitstring Lag Prediction Estimate | P_local | `0.9713063889472594` | `0.97130638885744536` | 8.9814e-11 | 8.9814e-11 |
| biased-random-bytes | t2-r1 | Bitstring Most Common Value Estimate | min entropy | `0.15182732507652347` | `0.15182732507652344` | 2.77556e-17 | 2.77556e-17 |
| biased-random-bytes | t2-r1 | H_original |  | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t2-r1 | Literal MultiMCW Prediction Estimate | min entropy | `0.3196462537659206` | `0.31964625376592054` | 5.55112e-17 | 5.55112e-17 |
| biased-random-bytes | t2-r1 | Literal t-Tuple Estimate | min entropy | `0.29115980449860829` | `0.29115980449860823` | 5.55112e-17 | 5.55112e-17 |
| data.pi | t1-r1 | Assessed min entropy |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t1-r1 | H_original |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t1-r1 | Literal Collision Estimate | min entropy | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t1-r1 | Literal Collision Estimate | p | `0.67383272785477999` | `0.67383272785477799` | 1.9984e-15 | 1.9984e-15 |
| data.pi | t1-r1 | Literal Collision Estimate | sigma-hat | `0.49655650591493028` | `0.49655650591492989` | 3.88578e-16 | 3.88578e-16 |
| data.pi | t1-r1 | Literal Markov Estimate | min entropy | `0.72318078199004532` | `0.72318078199004543` | 1.11022e-16 | 1.11022e-16 |
| data.pi | t1-r1 | Literal Markov Estimate | p-hat_max | `1.3630576315328927e-28` | `1.3630576315328792e-28` | 1.34525e-42 | 1.34525e-42 |
| data.pi | t10-r1 | Assessed min entropy |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t10-r1 | H_original |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t10-r1 | Literal Collision Estimate | min entropy | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t10-r1 | Literal Collision Estimate | p | `0.67383272785477999` | `0.67383272785477799` | 1.9984e-15 | 1.9984e-15 |
| data.pi | t10-r1 | Literal Collision Estimate | sigma-hat | `0.49655650591493028` | `0.49655650591492989` | 3.88578e-16 | 3.88578e-16 |
| data.pi | t10-r1 | Literal Markov Estimate | min entropy | `0.72318078199004532` | `0.72318078199004543` | 1.11022e-16 | 1.11022e-16 |
| data.pi | t10-r1 | Literal Markov Estimate | p-hat_max | `1.3630576315328927e-28` | `1.3630576315328792e-28` | 1.34525e-42 | 1.34525e-42 |
| data.pi | t10-r2 | Assessed min entropy |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t10-r2 | H_original |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t10-r2 | Literal Collision Estimate | min entropy | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t10-r2 | Literal Collision Estimate | p | `0.67383272785477999` | `0.67383272785477799` | 1.9984e-15 | 1.9984e-15 |
| data.pi | t10-r2 | Literal Collision Estimate | sigma-hat | `0.49655650591493028` | `0.49655650591492989` | 3.88578e-16 | 3.88578e-16 |
| data.pi | t10-r2 | Literal Markov Estimate | min entropy | `0.72318078199004532` | `0.72318078199004543` | 1.11022e-16 | 1.11022e-16 |
| data.pi | t10-r2 | Literal Markov Estimate | p-hat_max | `1.3630576315328927e-28` | `1.3630576315328792e-28` | 1.34525e-42 | 1.34525e-42 |
| data.pi | t2-r1 | Assessed min entropy |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t2-r1 | H_original |  | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t2-r1 | Literal Collision Estimate | min entropy | `0.56953759345777466` | `0.56953759345777899` | 4.32987e-15 | 4.32987e-15 |
| data.pi | t2-r1 | Literal Collision Estimate | p | `0.67383272785477999` | `0.67383272785477799` | 1.9984e-15 | 1.9984e-15 |
| data.pi | t2-r1 | Literal Collision Estimate | sigma-hat | `0.49655650591493028` | `0.49655650591492989` | 3.88578e-16 | 3.88578e-16 |
| data.pi | t2-r1 | Literal Markov Estimate | min entropy | `0.72318078199004532` | `0.72318078199004543` | 1.11022e-16 | 1.11022e-16 |
| data.pi | t2-r1 | Literal Markov Estimate | p-hat_max | `1.3630576315328927e-28` | `1.3630576315328792e-28` | 1.34525e-42 | 1.34525e-42 |
| normal | t1-r1 | Assessed min entropy |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t1-r1 | Bitstring Collision Estimate | sigma-hat | `0.49946189437149541` | `0.49946189437149574` | 3.33067e-16 | 3.33067e-16 |
| normal | t1-r1 | Bitstring Compression Estimate | min entropy | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t1-r1 | Bitstring Compression Estimate | p | `0.11866185634166618` | `0.11866185634166793` | 1.7486e-15 | 1.7486e-15 |
| normal | t1-r1 | Bitstring Compression Estimate | sigma-hat | `1.0488632759418641` | `1.0488632759418639` | 2.22045e-16 | 2.117e-16 |
| normal | t1-r1 | H_bitstring |  | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t1-r1 | H_bitstring Per Symbol |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t10-r1 | Assessed min entropy |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t10-r1 | Bitstring Collision Estimate | sigma-hat | `0.49946189437149541` | `0.49946189437149574` | 3.33067e-16 | 3.33067e-16 |
| normal | t10-r1 | Bitstring Compression Estimate | min entropy | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t10-r1 | Bitstring Compression Estimate | p | `0.11866185634166618` | `0.11866185634166793` | 1.7486e-15 | 1.7486e-15 |
| normal | t10-r1 | Bitstring Compression Estimate | sigma-hat | `1.0488632759418641` | `1.0488632759418639` | 2.22045e-16 | 2.117e-16 |
| normal | t10-r1 | H_bitstring |  | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t10-r1 | H_bitstring Per Symbol |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t10-r2 | Assessed min entropy |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t10-r2 | Bitstring Collision Estimate | sigma-hat | `0.49946189437149541` | `0.49946189437149574` | 3.33067e-16 | 3.33067e-16 |
| normal | t10-r2 | Bitstring Compression Estimate | min entropy | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t10-r2 | Bitstring Compression Estimate | p | `0.11866185634166618` | `0.11866185634166793` | 1.7486e-15 | 1.7486e-15 |
| normal | t10-r2 | Bitstring Compression Estimate | sigma-hat | `1.0488632759418641` | `1.0488632759418639` | 2.22045e-16 | 2.117e-16 |
| normal | t10-r2 | H_bitstring |  | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t10-r2 | H_bitstring Per Symbol |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t2-r1 | Assessed min entropy |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| normal | t2-r1 | Bitstring Collision Estimate | sigma-hat | `0.49946189437149541` | `0.49946189437149574` | 3.33067e-16 | 3.33067e-16 |
| normal | t2-r1 | Bitstring Compression Estimate | min entropy | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t2-r1 | Bitstring Compression Estimate | p | `0.11866185634166618` | `0.11866185634166793` | 1.7486e-15 | 1.7486e-15 |
| normal | t2-r1 | Bitstring Compression Estimate | sigma-hat | `1.0488632759418641` | `1.0488632759418639` | 2.22045e-16 | 2.117e-16 |
| normal | t2-r1 | H_bitstring |  | `0.51251197288878858` | `0.51251197288878503` | 3.55271e-15 | 3.55271e-15 |
| normal | t2-r1 | H_bitstring Per Symbol |  | `4.1000957831103086` | `4.1000957831102802` | 2.84217e-14 | 6.93196e-15 |
| ringOsc-nist | t1-r1 | Assessed min entropy |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t1-r1 | H_original |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t1-r1 | Literal Collision Estimate | min entropy | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t1-r1 | Literal Collision Estimate | p | `0.91608556642948002` | `0.91608556642948358` | 3.55271e-15 | 3.55271e-15 |
| ringOsc-nist | t1-r1 | Literal Collision Estimate | sigma-hat | `0.36201421259803784` | `0.36201421259803818` | 3.33067e-16 | 3.33067e-16 |
| ringOsc-nist | t1-r1 | Literal Compression Estimate | min entropy | `0.15932269772157898` | `0.15932269772157773` | 1.249e-15 | 1.249e-15 |
| ringOsc-nist | t1-r1 | Literal Compression Estimate | p | `0.51550696093402992` | `0.51550696093403259` | 2.66454e-15 | 2.66454e-15 |
| ringOsc-nist | t1-r1 | Literal Compression Estimate | sigma-hat | `1.5895720714868642` | `1.589572071486864` | 2.22045e-16 | 1.39688e-16 |
| ringOsc-nist | t1-r1 | Literal LZ78Y Prediction Estimate | min entropy | `0.25107305682069808` | `0.25107305682069803` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t1-r1 | Literal Lag Prediction Estimate | min entropy | `0.25106695357142894` | `0.251066953571429` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t1-r1 | Literal Markov Estimate | min entropy | `0.2579793924501087` | `0.25797939245010865` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t1-r1 | Literal Markov Estimate | p-hat_max | `1.1470423954118878e-10` | `1.1470423954118935e-10` | 5.68687e-25 | 5.68687e-25 |
| ringOsc-nist | t1-r1 | Literal MultiMCW Prediction Estimate | P_local | `0.81760774776600598` | `0.81760774785366996` | 8.7664e-11 | 8.7664e-11 |
| ringOsc-nist | t10-r1 | Assessed min entropy |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t10-r1 | H_original |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t10-r1 | Literal Collision Estimate | min entropy | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t10-r1 | Literal Collision Estimate | p | `0.91608556642948002` | `0.91608556642948358` | 3.55271e-15 | 3.55271e-15 |
| ringOsc-nist | t10-r1 | Literal Collision Estimate | sigma-hat | `0.36201421259803784` | `0.36201421259803818` | 3.33067e-16 | 3.33067e-16 |
| ringOsc-nist | t10-r1 | Literal Compression Estimate | min entropy | `0.15932269772157898` | `0.15932269772157773` | 1.249e-15 | 1.249e-15 |
| ringOsc-nist | t10-r1 | Literal Compression Estimate | p | `0.51550696093402992` | `0.51550696093403259` | 2.66454e-15 | 2.66454e-15 |
| ringOsc-nist | t10-r1 | Literal Compression Estimate | sigma-hat | `1.5895720714868642` | `1.589572071486864` | 2.22045e-16 | 1.39688e-16 |
| ringOsc-nist | t10-r1 | Literal LZ78Y Prediction Estimate | min entropy | `0.25107305682069808` | `0.25107305682069803` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t10-r1 | Literal Lag Prediction Estimate | min entropy | `0.25106695357142894` | `0.251066953571429` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t10-r1 | Literal Markov Estimate | min entropy | `0.2579793924501087` | `0.25797939245010865` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t10-r1 | Literal Markov Estimate | p-hat_max | `1.1470423954118878e-10` | `1.1470423954118935e-10` | 5.68687e-25 | 5.68687e-25 |
| ringOsc-nist | t10-r1 | Literal MultiMCW Prediction Estimate | P_local | `0.81760774776600598` | `0.81760774785366996` | 8.7664e-11 | 8.7664e-11 |
| ringOsc-nist | t10-r2 | Assessed min entropy |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t10-r2 | H_original |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t10-r2 | Literal Collision Estimate | min entropy | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t10-r2 | Literal Collision Estimate | p | `0.91608556642948002` | `0.91608556642948358` | 3.55271e-15 | 3.55271e-15 |
| ringOsc-nist | t10-r2 | Literal Collision Estimate | sigma-hat | `0.36201421259803784` | `0.36201421259803818` | 3.33067e-16 | 3.33067e-16 |
| ringOsc-nist | t10-r2 | Literal Compression Estimate | min entropy | `0.15932269772157898` | `0.15932269772157773` | 1.249e-15 | 1.249e-15 |
| ringOsc-nist | t10-r2 | Literal Compression Estimate | p | `0.51550696093402992` | `0.51550696093403259` | 2.66454e-15 | 2.66454e-15 |
| ringOsc-nist | t10-r2 | Literal Compression Estimate | sigma-hat | `1.5895720714868642` | `1.589572071486864` | 2.22045e-16 | 1.39688e-16 |
| ringOsc-nist | t10-r2 | Literal LZ78Y Prediction Estimate | min entropy | `0.25107305682069808` | `0.25107305682069803` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t10-r2 | Literal Lag Prediction Estimate | min entropy | `0.25106695357142894` | `0.251066953571429` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t10-r2 | Literal Markov Estimate | min entropy | `0.2579793924501087` | `0.25797939245010865` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t10-r2 | Literal Markov Estimate | p-hat_max | `1.1470423954118878e-10` | `1.1470423954118935e-10` | 5.68687e-25 | 5.68687e-25 |
| ringOsc-nist | t10-r2 | Literal MultiMCW Prediction Estimate | P_local | `0.81760774776600598` | `0.81760774785366996` | 8.7664e-11 | 8.7664e-11 |
| ringOsc-nist | t2-r1 | Assessed min entropy |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t2-r1 | H_original |  | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t2-r1 | Literal Collision Estimate | min entropy | `0.12644573619605429` | `0.12644573619604868` | 5.60663e-15 | 5.60663e-15 |
| ringOsc-nist | t2-r1 | Literal Collision Estimate | p | `0.91608556642948002` | `0.91608556642948358` | 3.55271e-15 | 3.55271e-15 |
| ringOsc-nist | t2-r1 | Literal Collision Estimate | sigma-hat | `0.36201421259803784` | `0.36201421259803818` | 3.33067e-16 | 3.33067e-16 |
| ringOsc-nist | t2-r1 | Literal Compression Estimate | min entropy | `0.15932269772157898` | `0.15932269772157773` | 1.249e-15 | 1.249e-15 |
| ringOsc-nist | t2-r1 | Literal Compression Estimate | p | `0.51550696093402992` | `0.51550696093403259` | 2.66454e-15 | 2.66454e-15 |
| ringOsc-nist | t2-r1 | Literal Compression Estimate | sigma-hat | `1.5895720714868642` | `1.589572071486864` | 2.22045e-16 | 1.39688e-16 |
| ringOsc-nist | t2-r1 | Literal LZ78Y Prediction Estimate | min entropy | `0.25107305682069808` | `0.25107305682069803` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t2-r1 | Literal Lag Prediction Estimate | min entropy | `0.25106695357142894` | `0.251066953571429` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t2-r1 | Literal Markov Estimate | min entropy | `0.2579793924501087` | `0.25797939245010865` | 5.55112e-17 | 5.55112e-17 |
| ringOsc-nist | t2-r1 | Literal Markov Estimate | p-hat_max | `1.1470423954118878e-10` | `1.1470423954118935e-10` | 5.68687e-25 | 5.68687e-25 |
| ringOsc-nist | t2-r1 | Literal MultiMCW Prediction Estimate | P_local | `0.81760774776600598` | `0.81760774785366996` | 8.7664e-11 | 8.7664e-11 |
| truerand_1bit | t1-r1 | Assessed min entropy |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t1-r1 | H_original |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t1-r1 | Literal Collision Estimate | min entropy | `0.90093572690822665` | `0.90093572690824753` | 2.08722e-14 | 2.08722e-14 |
| truerand_1bit | t1-r1 | Literal Collision Estimate | p | `0.53553926972023191` | `0.53553926972022414` | 7.77156e-15 | 7.77156e-15 |
| truerand_1bit | t1-r1 | Literal Collision Estimate | sigma-hat | `0.50000038487257392` | `0.5000003848725737` | 2.22045e-16 | 2.22045e-16 |
| truerand_1bit | t1-r1 | Literal Compression Estimate | min entropy | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t1-r1 | Literal Compression Estimate | p | `0.03172881608928213` | `0.031728816089275136` | 6.99441e-15 | 6.99441e-15 |
| truerand_1bit | t10-r1 | Assessed min entropy |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t10-r1 | H_original |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t10-r1 | Literal Collision Estimate | min entropy | `0.90093572690822665` | `0.90093572690824753` | 2.08722e-14 | 2.08722e-14 |
| truerand_1bit | t10-r1 | Literal Collision Estimate | p | `0.53553926972023191` | `0.53553926972022414` | 7.77156e-15 | 7.77156e-15 |
| truerand_1bit | t10-r1 | Literal Collision Estimate | sigma-hat | `0.50000038487257392` | `0.5000003848725737` | 2.22045e-16 | 2.22045e-16 |
| truerand_1bit | t10-r1 | Literal Compression Estimate | min entropy | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t10-r1 | Literal Compression Estimate | p | `0.03172881608928213` | `0.031728816089275136` | 6.99441e-15 | 6.99441e-15 |
| truerand_1bit | t10-r2 | Assessed min entropy |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t10-r2 | H_original |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t10-r2 | Literal Collision Estimate | min entropy | `0.90093572690822665` | `0.90093572690824753` | 2.08722e-14 | 2.08722e-14 |
| truerand_1bit | t10-r2 | Literal Collision Estimate | p | `0.53553926972023191` | `0.53553926972022414` | 7.77156e-15 | 7.77156e-15 |
| truerand_1bit | t10-r2 | Literal Collision Estimate | sigma-hat | `0.50000038487257392` | `0.5000003848725737` | 2.22045e-16 | 2.22045e-16 |
| truerand_1bit | t10-r2 | Literal Compression Estimate | min entropy | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t10-r2 | Literal Compression Estimate | p | `0.03172881608928213` | `0.031728816089275136` | 6.99441e-15 | 6.99441e-15 |
| truerand_1bit | t2-r1 | Assessed min entropy |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t2-r1 | H_original |  | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t2-r1 | Literal Collision Estimate | min entropy | `0.90093572690822665` | `0.90093572690824753` | 2.08722e-14 | 2.08722e-14 |
| truerand_1bit | t2-r1 | Literal Collision Estimate | p | `0.53553926972023191` | `0.53553926972022414` | 7.77156e-15 | 7.77156e-15 |
| truerand_1bit | t2-r1 | Literal Collision Estimate | sigma-hat | `0.50000038487257392` | `0.5000003848725737` | 2.22045e-16 | 2.22045e-16 |
| truerand_1bit | t2-r1 | Literal Compression Estimate | min entropy | `0.82967708323406131` | `0.82967708323411438` | 5.30687e-14 | 5.30687e-14 |
| truerand_1bit | t2-r1 | Literal Compression Estimate | p | `0.03172881608928213` | `0.031728816089275136` | 6.99441e-15 | 6.99441e-15 |
| truerand_4bit | t1-r1 | Bitstring Collision Estimate | min entropy | `0.92836094530468272` | `0.92836094530464797` | 3.475e-14 | 3.475e-14 |
| truerand_4bit | t1-r1 | Bitstring Collision Estimate | p | `0.52545497545213493` | `0.52545497545214759` | 1.26565e-14 | 1.26565e-14 |
| truerand_4bit | t1-r1 | Bitstring Collision Estimate | sigma-hat | `0.5000000790700484` | `0.50000007907004784` | 5.55112e-16 | 5.55112e-16 |
| truerand_4bit | t10-r1 | Bitstring Collision Estimate | min entropy | `0.92836094530468272` | `0.92836094530464797` | 3.475e-14 | 3.475e-14 |
| truerand_4bit | t10-r1 | Bitstring Collision Estimate | p | `0.52545497545213493` | `0.52545497545214759` | 1.26565e-14 | 1.26565e-14 |
| truerand_4bit | t10-r1 | Bitstring Collision Estimate | sigma-hat | `0.5000000790700484` | `0.50000007907004784` | 5.55112e-16 | 5.55112e-16 |
| truerand_4bit | t10-r2 | Bitstring Collision Estimate | min entropy | `0.92836094530468272` | `0.92836094530464797` | 3.475e-14 | 3.475e-14 |
| truerand_4bit | t10-r2 | Bitstring Collision Estimate | p | `0.52545497545213493` | `0.52545497545214759` | 1.26565e-14 | 1.26565e-14 |
| truerand_4bit | t10-r2 | Bitstring Collision Estimate | sigma-hat | `0.5000000790700484` | `0.50000007907004784` | 5.55112e-16 | 5.55112e-16 |
| truerand_4bit | t2-r1 | Bitstring Collision Estimate | min entropy | `0.92836094530468272` | `0.92836094530464797` | 3.475e-14 | 3.475e-14 |
| truerand_4bit | t2-r1 | Bitstring Collision Estimate | p | `0.52545497545213493` | `0.52545497545214759` | 1.26565e-14 | 1.26565e-14 |
| truerand_4bit | t2-r1 | Bitstring Collision Estimate | sigma-hat | `0.5000000790700484` | `0.50000007907004784` | 5.55112e-16 | 5.55112e-16 |
| truerand_8bit | t1-r1 | Assessed min entropy |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t1-r1 | Bitstring Collision Estimate | min entropy | `0.95840629541836875` | `0.95840629541846956` | 1.00808e-13 | 1.00808e-13 |
| truerand_8bit | t1-r1 | Bitstring Collision Estimate | p | `0.51462509129032696` | `0.51462509129029099` | 3.59712e-14 | 3.59712e-14 |
| truerand_8bit | t1-r1 | Bitstring Collision Estimate | sigma-hat | `0.49999999274063417` | `0.49999999274063472` | 5.55112e-16 | 5.55112e-16 |
| truerand_8bit | t1-r1 | Bitstring Compression Estimate | min entropy | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t1-r1 | Bitstring Compression Estimate | p | `0.023269820763614391` | `0.023269820763600402` | 1.39888e-14 | 1.39888e-14 |
| truerand_8bit | t1-r1 | Bitstring Compression Estimate | sigma-hat | `1.0157985743570803` | `1.0157985743570801` | 2.22045e-16 | 2.18591e-16 |
| truerand_8bit | t1-r1 | H_bitstring |  | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t1-r1 | H_bitstring Per Symbol |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t10-r1 | Assessed min entropy |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t10-r1 | Bitstring Collision Estimate | min entropy | `0.95840629541836875` | `0.95840629541846956` | 1.00808e-13 | 1.00808e-13 |
| truerand_8bit | t10-r1 | Bitstring Collision Estimate | p | `0.51462509129032696` | `0.51462509129029099` | 3.59712e-14 | 3.59712e-14 |
| truerand_8bit | t10-r1 | Bitstring Collision Estimate | sigma-hat | `0.49999999274063417` | `0.49999999274063472` | 5.55112e-16 | 5.55112e-16 |
| truerand_8bit | t10-r1 | Bitstring Compression Estimate | min entropy | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t10-r1 | Bitstring Compression Estimate | p | `0.023269820763614391` | `0.023269820763600402` | 1.39888e-14 | 1.39888e-14 |
| truerand_8bit | t10-r1 | Bitstring Compression Estimate | sigma-hat | `1.0157985743570803` | `1.0157985743570801` | 2.22045e-16 | 2.18591e-16 |
| truerand_8bit | t10-r1 | H_bitstring |  | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t10-r1 | H_bitstring Per Symbol |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t10-r2 | Assessed min entropy |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t10-r2 | Bitstring Collision Estimate | min entropy | `0.95840629541836875` | `0.95840629541846956` | 1.00808e-13 | 1.00808e-13 |
| truerand_8bit | t10-r2 | Bitstring Collision Estimate | p | `0.51462509129032696` | `0.51462509129029099` | 3.59712e-14 | 3.59712e-14 |
| truerand_8bit | t10-r2 | Bitstring Collision Estimate | sigma-hat | `0.49999999274063417` | `0.49999999274063472` | 5.55112e-16 | 5.55112e-16 |
| truerand_8bit | t10-r2 | Bitstring Compression Estimate | min entropy | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t10-r2 | Bitstring Compression Estimate | p | `0.023269820763614391` | `0.023269820763600402` | 1.39888e-14 | 1.39888e-14 |
| truerand_8bit | t10-r2 | Bitstring Compression Estimate | sigma-hat | `1.0157985743570803` | `1.0157985743570801` | 2.22045e-16 | 2.18591e-16 |
| truerand_8bit | t10-r2 | H_bitstring |  | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t10-r2 | H_bitstring Per Symbol |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t2-r1 | Assessed min entropy |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |
| truerand_8bit | t2-r1 | Bitstring Collision Estimate | min entropy | `0.95840629541836875` | `0.95840629541846956` | 1.00808e-13 | 1.00808e-13 |
| truerand_8bit | t2-r1 | Bitstring Collision Estimate | p | `0.51462509129032696` | `0.51462509129029099` | 3.59712e-14 | 3.59712e-14 |
| truerand_8bit | t2-r1 | Bitstring Collision Estimate | sigma-hat | `0.49999999274063417` | `0.49999999274063472` | 5.55112e-16 | 5.55112e-16 |
| truerand_8bit | t2-r1 | Bitstring Compression Estimate | min entropy | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t2-r1 | Bitstring Compression Estimate | p | `0.023269820763614391` | `0.023269820763600402` | 1.39888e-14 | 1.39888e-14 |
| truerand_8bit | t2-r1 | Bitstring Compression Estimate | sigma-hat | `1.0157985743570803` | `1.0157985743570801` | 2.22045e-16 | 2.18591e-16 |
| truerand_8bit | t2-r1 | H_bitstring |  | `0.90423268189731187` | `0.90423268189745631` | 1.4444e-13 | 1.4444e-13 |
| truerand_8bit | t2-r1 | H_bitstring Per Symbol |  | `7.233861455178495` | `7.2338614551796505` | 1.15552e-12 | 1.59738e-13 |

## Problems (refusals and skipped comparisons)

- rand1_short/t1-r1: host run rc '255', not compared (instrument rule 2)
- rand1_short/t10-r1: host run rc '255', not compared (instrument rule 2)
- rand1_short/t10-r2: host run rc '255', not compared (instrument rule 2)
- rand1_short/t2-r1: host run rc '255', not compared (instrument rule 2)
- rand1_short: no host output to compare (expected t1-r1.stdout.txt under /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/non_iid/rand1_short/)
- rand4_short/t1-r1: host run rc '255', not compared (instrument rule 2)
- rand4_short/t10-r1: host run rc '255', not compared (instrument rule 2)
- rand4_short/t10-r2: host run rc '255', not compared (instrument rule 2)
- rand4_short/t2-r1: host run rc '255', not compared (instrument rule 2)
- rand4_short: no host output to compare (expected t1-r1.stdout.txt under /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/non_iid/rand4_short/)
- rand8_short/t1-r1: host run rc '255', not compared (instrument rule 2)
- rand8_short/t10-r1: host run rc '255', not compared (instrument rule 2)
- rand8_short/t10-r2: host run rc '255', not compared (instrument rule 2)
- rand8_short/t2-r1: host run rc '255', not compared (instrument rule 2)
- rand8_short: no host output to compare (expected t1-r1.stdout.txt under /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/logs/determinism/non_iid/rand8_short/)

## Identity matched per case (OC-74 limb)

- biased-random-bits: 1000000 samples / 2 distinct / 1-bit
- biased-random-bytes: 1000000 samples / 256 distinct / 8-bit
- data.pi: 1165666 samples / 2 distinct / 1-bit
- normal: 1000000 samples / 179 distinct / 8-bit
- ringOsc-nist: 1000000 samples / 2 distinct / 1-bit
- truerand_1bit: 1000000 samples / 2 distinct / 1-bit
- truerand_4bit: 1000000 samples / 16 distinct / 4-bit
- truerand_8bit: 1000000 samples / 256 distinct / 8-bit

## What a difference in each class would indicate

- **Same delta at every thread count and repeat on this host, present against Linux**: a compile-time / host-wide property -- `long double` width (x87 80-bit on x86-64 Linux vs IEEE double on arm64 macOS), libm (`expl`, `logl`, `lgammal`, `powl`), or FMA contraction (Apple clang contracts on arm64 by default; the known eight rows are all prediction-estimator `P_local` / `min entropy` values, consistent with the long double `P_local` solver).
- **Delta that varies between host runs at the same thread count**: a data race or non-thread-safe call, never a platform effect; it must be read with RESULTS.md and cannot be excused by a manifest row.
- **Delta that varies with the thread count but not between repeats**: reduction order or partition; `ea_non_iid` has no parallel region, so this would point outside the tool's own code.
- **A difference only at 10 threads and not at 2** therefore never points at `long double` width: a thread count cannot change a compile-time format.

Limits (rule 18): JSON-only fields are not covered; a host-vs-Linux delta below 1e-10 is invisible inside the band; a platform difference that leaves the printed 17 significant digits unchanged is invisible; the refdata's own correctness is not established by this comparison (WHAT-A-GREEN-SUITE-ESTABLISHES.md).
