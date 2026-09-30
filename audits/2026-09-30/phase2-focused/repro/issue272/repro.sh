set -x
git clone -q https://github.com/usnistgov/SP800-90B_EntropyAssessment.git && cd SP800-90B_EntropyAssessment/cpp
git rev-parse HEAD
make non_iid >/dev/null
cd selftest && ./selftest; echo "baseline exit=$?"; cd ..

# Mutant 1: drop the n x H_bitstring term from the final assessment
sed -i 's/h_assessed = min(h_assessed, H_bitstring \* data.word_size);/\/\/ mutant 1/' non_iid_main.cpp
git diff --stat
make non_iid >/dev/null && cd selftest && ./selftest; echo "mutant1 exit=$?"
grep -h '^Assessed min entropy' refdata/normal.res normal.res refdata/truerand_8bit.res truerand_8bit.res
cd .. && git checkout -q non_iid_main.cpp

# Mutant 2: drop H_original from the final assessment
perl -0pi -e 's/    if \(initial_entropy\) \{\n        h_assessed = min\(h_assessed, H_original\);\n    \}\n/    \/\/ mutant 2\n/' non_iid_main.cpp
git diff --stat
make non_iid >/dev/null && cd selftest && ./selftest; echo "mutant2 exit=$?"
grep -h '^Assessed min entropy' refdata/ringOsc-nist.res ringOsc-nist.res refdata/biased-random-bits.res biased-random-bits.res
cd .. && git checkout -q non_iid_main.cpp && make non_iid >/dev/null

# Exit status: a mismatch in the first file only
cd selftest && sed -i 's/^\(Literal Most Common Value Estimate: p_u = \).*/\10.9/' refdata/biased-random-bits.res
./selftest; echo "refdata-edit exit=$?"
git checkout -q refdata/
