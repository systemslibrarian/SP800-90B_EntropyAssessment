#!/usr/bin/env python3
"""Independent SP 800-90B section 6.3.1 most-common-value oracle."""

from __future__ import annotations

import collections
import hashlib
import json
import math
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: mcv_oracle.py FILE [BITS_PER_SAMPLE]")
    path = Path(sys.argv[1])
    width = int(sys.argv[2]) if len(sys.argv) == 3 else 8
    mask = (1 << width) - 1
    raw = path.read_bytes()
    values = bytes(value & mask for value in raw)
    counts = collections.Counter(values)
    length = len(values)
    xmax = max(counts.values())
    p_hat = xmax / length
    # SP 800-90B (2018), 6.3.1 step 2.  The 2025 potential errata changes
    # only the worked example's arithmetic, not this formula.
    sigma = math.sqrt(p_hat * (1.0 - p_hat) / (length - 1))
    p_u = min(1.0, p_hat + 2.576 * sigma)
    entropy = -math.log2(p_u)
    # The implementation deliberately uses the full normal quantile rather
    # than the publication's printed 2.576.  That choice is the pre-existing
    # F07 / upstream #22 disposition, so report both instead of silently
    # treating either one as novel evidence.
    full_quantile = 2.5758293035489008
    p_u_full = min(1.0, p_hat + full_quantile * sigma)
    entropy_full = -math.log2(p_u_full)
    print(json.dumps({
        "file": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "samples": length,
        "bitsPerSample": width,
        "alphabetSize": len(counts),
        "maximumCount": xmax,
        "pHat": p_hat,
        "pUpperPrinted2576": p_u,
        "minEntropyPrinted2576": entropy,
        "pUpperFullQuantile": p_u_full,
        "minEntropyFullQuantile": entropy_full,
        "fullMinusPrintedEntropy": entropy_full - entropy,
    }, indent=2))


if __name__ == "__main__":
    main()
