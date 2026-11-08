# PROV-16 control.txt  2026-11-07 21:56:19 -0500  host=Darwin 25.6.0 arm64
# env: EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 -- every tool run below is a NON-COMPLIANT short-dataset run unless stated
# repo=/Users/gmcas/repos/SP800-90B_EntropyAssessment  git=1151b22 branch=audit/2026-11-07
binary sha256 1ad1568c083b277490ea358ddb6e7f11d0da464d1c9391bd8e4c50eb37e6e16f  /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid  (mtime 2026-11-07 19:28:57)
input sha256 9da53e09266ff711b1168d2f8a01153c0d0c749ab856552f450d331358aab652  (20,000 samples: 19,990 x 0x00, ten 0x01 at seeded positions; width 1)
$ /Users/gmcas/repos/SP800-90B_EntropyAssessment/cpp/ea_non_iid -vvv -o /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/c_z.json /Users/gmcas/repos/SP800-90B_EntropyAssessment/docs/audits/2026-11-07-aggressive-audit/repro/PROV-16/out/ten-in-20000.bin 1
rc[vvv]=0  stdout=c_z.out stderr=c_z.err
JSON MCV hOriginal = 0.00013391324219584911 ; lines with '-0' in the JSON: 5
RESULT: CONTROL-OK -- with p_u < 1 the MCV estimate is positive (0.00013391324219584911); the negative zero in run.sh is the clamp's -log2(1.0)
