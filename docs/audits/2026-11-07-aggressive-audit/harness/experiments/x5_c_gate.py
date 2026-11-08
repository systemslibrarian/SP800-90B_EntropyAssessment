#!/usr/bin/env python3
"""x5_c_gate.py -- X5: what the >= 1,000,000 intake counts under `-c` (intake.md E10 / 2.5).

SP 800-90B 3.1.1 item 2 (PDF p. 19): "a conditioned sequential dataset of at least 1 000 000
consecutive conditioning component outputs".  The tool's gate (utils.h dataset_meets_minimum)
counts BYTES loaded, under -i and -c alike.  For a 256-bit conditioner 1,000,000 bytes are
31,250 outputs -- 32x fewer than the text requires.

Files:
  x5-sha256-outputs-31250-1000000.bin   SHA-256(KEY || counter) for counter = 0..31249,
                                        concatenated: exactly 1,000,000 bytes = 31,250 outputs
                                        of a 256-bit conditioning function.
  x5-sha256-outputs-31250-999999.bin    the first 999,999 bytes of the same stream: one byte
                                        short of the tool's gate (31,249.97 outputs) -- the
                                        negative control that shows the gate counts bytes.

Decision (PLAN.md X5): the 1,000,000-byte file under `-c ... 8` is ACCEPTED (exit 0, JSON
errorLevel 0, no nonCompliantShortDataset) although it holds 31,250 conditioner outputs; the
999,999-byte file is REFUSED with the 3.1.1 message.  Positive = the first is accepted.  This
is a compliance question (direction neutral in the arithmetic), not an overstatement; the owner
decides whether -c should take n_out or count bits.
"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

EXPERIMENT = "X5"
N = common.N_COMPLIANT
OUTPUTS = N // 32          # 31,250 SHA-256 outputs


def generate() -> None:
    rows = common.read_manifest()
    key = common.KEY_PREFIX + b"x5-conditioner"
    out = bytearray()
    for c in range(OUTPUTS):
        out += hashlib.sha256(key + c.to_bytes(8, "big")).digest()
    assert len(out) == N
    data = np.frombuffer(bytes(out), dtype=np.uint8)
    common.write_data_file("x5-sha256-outputs-31250-1000000.bin", data, 8, EXPERIMENT,
                           f"{OUTPUTS} consecutive SHA-256(KEY||counter) outputs = 1,000,000 bytes; "
                           "run `-c` with 8: accepted although 31,250 < 1,000,000 conditioner outputs?",
                           __file__, rows)
    common.write_data_file("x5-sha256-outputs-31250-999999.bin", data[:N - 1], 8, EXPERIMENT,
                           "the first 999,999 bytes of the same stream: negative control, must be refused "
                           "(shows the gate counts bytes)", __file__, rows)


if __name__ == "__main__":
    sys.exit(common.standard_main(sys.argv[1:], EXPERIMENT, generate))
