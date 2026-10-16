## Summary

Repairs the independently verified HARNESS-AUD-01, C-01, N-07 and upstream
#153/#252 defects without modifying the sealed audit evidence.

- makes the 11-pair selftest inventory authoritative and hash-bound;
- pairs restart simulation arrays with `delete[]` and adds a proven ASan/UBSan
  control;
- hashes the exact loaded assessment bytes and adds a deterministic pathname
  replacement control;
- performs the IID LRS decision in the log domain and fails closed without
  exposing final entropy when a required IID suite fails;
- covers exact one-million-sample inputs at widths 1–8 plus binary/nonbinary
  positive controls.

## Verification

- clean `ea_non_iid`, `ea_iid`, `ea_restart` build: pass;
- strict suite: 18 pass / 1 documented macOS #155 reference delta / 17
  regressions;
- documented macOS mode: 19 pass / 0 fail / 17 regressions;
- fixed C-01 ASan/UBSan control: pass;
- vulnerable parent: expected ASan abort, status 134.

Repair-engineering evidence and rerun commands are under
`repairs/2026-10-09-verified-defects/`. Independent verification is still
required; no claim of NIST approval or physical entropy validation is made.
