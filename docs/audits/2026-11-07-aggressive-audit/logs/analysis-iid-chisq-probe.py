#!/usr/bin/env python3
"""Analysis-phase probes for the IID chi-square tests (SP 800-90B 5.2.1-5.2.4).

Every input here is far below the 1,000,000-sample minimum of 3.1.1, so each run
sets EA_ALLOW_SHORT_DATASET=1 and is NON-COMPLIANT by construction; the probes
settle structural questions (binning, df, m-selection), not entropy figures.
Outputs go to files under logs/ (brief rule 17); nothing is piped to head/tail.

Probes:
  ex11    SP 800-90B 5.2.1 Example 11 (PDF p. 44): L = 100, k = 3, counts 21/41/38.
          Spec says nbin = 6, bin frequencies 7, 6, 10, 8, 12, 7, T = 3.46, df = 3.
  bin140  SP 800-90B 5.2.3 worked example (PDF p. 46): p1 = 0.14, L = 1000 -> m = 2,
          so the independence df must be 2^2 - 2 = 2 and the GOF df 9.
  ex12    SP 800-90B 5.2.2 Example 12 (PDF p. 45): k = 4, c = 43, 55, 52, 10 (L = 160),
          e = 4.3, 5.5, 5.2, 1.0 -> nbin = 3 -> GOF df = 9 * (3 - 1) = 18.
  dfneg   Suspicion: 5.2.1 says "If the value of degrees of freedom is less than
          one, do not apply the test." L = 2000, counts 1992/4/4 gives (by hand)
          sorted e = 0.004 x4, 1.992 x4, 992.016 -> nbin = 2 -> df = 2 - 3 = -1.
          Expect the tool to print df = -1 and a p-value of 1 (cephes igamc(a<=0)
          returns 1.0) and to count the test as passed.
"""
import hashlib
import os
import random
import subprocess
import sys

ROOT = "/Users/gmcas/repos/SP800-90B_EntropyAssessment"
AUDIT = os.path.join(ROOT, "docs/audits/2026-11-07-aggressive-audit")
CORPUS = os.path.join(AUDIT, "corpus")
LOGS = os.path.join(AUDIT, "logs")
EA_IID = os.path.join(ROOT, "cpp/ea_iid")

os.makedirs(CORPUS, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

EX11 = [2, 2, 3, 1, 3, 2, 3, 2, 1, 3, 1, 1, 2, 3, 1, 1, 2, 2, 2, 3, 3, 2, 3, 2, 3, 1, 2, 2, 3, 3,
        2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 3, 2, 3, 1, 2, 2, 3, 1, 1, 3, 2, 3, 2, 3, 1, 2, 2, 3, 3,
        2, 2, 2, 1, 3, 3, 3, 2, 3, 2, 1, 2, 2, 3, 3, 3, 2, 3, 2, 1, 2, 2, 2, 1, 3, 3, 3, 2, 3, 2,
        1, 3, 2, 3, 1, 2, 2, 3, 1, 1]
assert len(EX11) == 100, len(EX11)
assert (EX11.count(1), EX11.count(2), EX11.count(3)) == (21, 41, 38), (EX11.count(1), EX11.count(2), EX11.count(3))


def place(L, counts, seed):
    """L samples, symbol s appears counts[s] times, positions fixed by seed."""
    r = random.Random(seed)
    data = bytearray(L)
    positions = list(range(L))
    r.shuffle(positions)
    i = 0
    for sym, c in enumerate(counts):
        for _ in range(c):
            data[positions[i]] = sym
            i += 1
    assert i == L
    return bytes(data)


inputs = {
    # name: (bytes, width)
    "ex11": (bytes(EX11), 2),
    "bin140": (place(1000, [860, 140], 140), 1),
    "ex12": (place(160, [43, 55, 52, 10], 12), 2),
    "dfneg": (place(2000, [1992, 4, 4], 2000), 2),
}

manifest = []
for name, (data, width) in inputs.items():
    path = os.path.join(CORPUS, "iid-chisq-%s.bin" % name)
    with open(path, "wb") as f:
        f.write(data)
    manifest.append("%s  %s  L=%d width=%d" % (hashlib.sha256(data).hexdigest(), path, len(data), width))

binsha = hashlib.sha256(open(EA_IID, "rb").read()).hexdigest()
manifest.append("%s  %s  (binary, instrument rule 4)" % (binsha, EA_IID))

env = dict(os.environ)
env["EA_ALLOW_SHORT_DATASET"] = "1"
env["OMP_NUM_THREADS"] = "2"

results = []
for name, (data, width) in inputs.items():
    path = os.path.join(CORPUS, "iid-chisq-%s.bin" % name)
    out = os.path.join(LOGS, "analysis-iid-chisq-%s.out" % name)
    cmd = [EA_IID, "-vvv", path, str(width)]
    with open(out, "wb") as f:
        rc = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=LOGS)
    results.append("%s rc=%d cmd=%s out=%s" % (name, rc, " ".join(cmd), out))

with open(os.path.join(LOGS, "analysis-iid-chisq-probe-manifest.txt"), "w") as f:
    f.write("EA_ALLOW_SHORT_DATASET=1 OMP_NUM_THREADS=2 on every run (non-compliant by construction)\n")
    f.write("\n".join(manifest) + "\n\n")
    f.write("\n".join(results) + "\n")

print("\n".join(manifest))
print("\n".join(results))
