#!/usr/bin/env python3
"""Generate deterministic, public SP 800-90B audit fixtures.

Every ordinary fixture contains 1,000,000 sample bytes.  The subset source
contains 2,000,000 sample bytes so a 1,000,000-sample subset remains valid.
These are software test vectors, not physical entropy captures.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from pathlib import Path

N = 1_000_000
SEED = 0x90B20261009


def prf_bytes(label: str, size: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < size:
        out.extend(hashlib.sha256(f"{SEED}:{label}:{counter}".encode()).digest())
        counter += 1
    return bytes(out[:size])


def bernoulli(label: str, one_probability: float) -> bytes:
    rng = random.Random(f"{SEED}:{label}")
    return bytes(rng.random() < one_probability for _ in range(N))


def markov(label: str, stay_probability: float) -> bytes:
    rng = random.Random(f"{SEED}:{label}")
    value = rng.randrange(2)
    out = bytearray(N)
    for i in range(N):
        if rng.random() >= stay_probability:
            value ^= 1
        out[i] = value
    return bytes(out)


def write(root: Path, name: str, data: bytes, width: int, description: str, manifest: list[dict]) -> None:
    path = root / name
    path.write_bytes(data)
    counts = {str(value): data.count(value) for value in sorted(set(data))}
    manifest.append({
        "file": name,
        "samples": len(data),
        "sampleWidthBits": width,
        "sha256": hashlib.sha256(data).hexdigest(),
        "description": description,
        "counts": counts,
    })


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: valid_fixtures.py OUTPUT_DIRECTORY")
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    write(root, "constant-1bit.bin", bytes(N), 1, "constant zero", manifest)
    near = bytearray(N)
    near[-1] = 1
    write(root, "near-constant-1bit.bin", bytes(near), 1, "one final one among zeros", manifest)
    write(root, "biased-p01-1bit.bin", bernoulli("biased-p01", 0.01), 1, "Bernoulli p(1)=0.01", manifest)
    uniform = bytes(value & 1 for value in prf_bytes("uniform-binary", N))
    write(root, "uniform-1bit.bin", uniform, 1, "SHA-256 counter stream, low bit", manifest)
    write(root, "alternating-1bit.bin", bytes(i & 1 for i in range(N)), 1, "period 01", manifest)
    period = bytes((0, 0, 1, 0, 1, 1))
    write(root, "period6-1bit.bin", (period * math.ceil(N / len(period)))[:N], 1, "period 001011", manifest)
    write(root, "markov-stay99-1bit.bin", markov("markov99", 0.99), 1, "binary Markov P(stay)=0.99", manifest)
    drift = bernoulli("drift-low", 0.1)[: N // 2] + bernoulli("drift-high", 0.9)[: N // 2]
    write(root, "drift-1bit.bin", drift, 1, "first half p(1)=0.1, second half p(1)=0.9", manifest)
    block = bytes(value & 1 for value in prf_bytes("repeated-block", 4096))
    write(root, "repeated-block-1bit.bin", (block * math.ceil(N / len(block)))[:N], 1, "repeated 4096-sample block", manifest)

    sparse_raw = prf_bytes("sparse-three", N)
    sparse_symbols = (0, 17, 255)
    sparse = bytes(sparse_symbols[value % 3] for value in sparse_raw)
    write(root, "uniform-sparse-8bit.bin", sparse, 8, "approximately uniform alphabet {0,17,255}", manifest)
    for width in range(2, 9):
        # Preserve the labels (and therefore bytes) of the original width-4 and
        # width-8 fixtures while filling the other supported symbol widths.
        raw = prf_bytes(f"uniform-width{width}", N)
        values = raw if width == 8 else bytes(value & ((1 << width) - 1) for value in raw)
        write(
            root,
            f"uniform-{width}bit.bin",
            values,
            width,
            f"approximately uniform alphabet 0..{(1 << width) - 1}",
            manifest,
        )

    subset = bernoulli("subset-first", 0.05) + bernoulli("subset-second", 0.5)
    write(root, "subset-source-1bit.bin", subset, 1, "2M samples: p(1)=0.05 then p(1)=0.5", manifest)
    (root / "manifest.json").write_text(json.dumps({"generatorSeed": hex(SEED), "fixtures": manifest}, indent=2) + "\n")


if __name__ == "__main__":
    main()
