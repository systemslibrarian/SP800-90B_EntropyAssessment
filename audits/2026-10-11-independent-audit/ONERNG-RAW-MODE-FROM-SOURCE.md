# OneRNG raw mode, settled from firmware source

Research note, 2026-10-15. Commissioned to replace a search-summary claim with
primary source before any hardware purchase. **The summary turned out to be
correct, and reading the source found two things the summary did not contain,
one of which constrains how a harness must capture.**

Source: `github.com/OneRNG/firmware`, file `cdc_app.c`, repository last pushed
**2015-06-18**, fetched via `gh api` (read-only). Line numbers are that file's.

## What the organisation actually hosts

`gh api orgs/OneRNG/repos` returns eight repositories. The two that matter:

| repo | language | last push |
|---|---|---|
| **`firmware`** | C | **2015-06-18** |
| **`hardware`** | Eagle | 2017-01-30 |

So the firmware **is** published. The raw-mode question is answerable from
source and does not need a vendor email or a purchase.

## 1. The mode table — primary-sourced, and it is a bitmask not an enumeration

`cdc_app.c:348-375`:

```c
if (a >= '0' && a <= '9') {
    a -= '0';
set:            // a is 4 bit mask
                //   - bit 0 - disables CRC whitening
                //   - bit 1 - enables RF source
                //   - bit 2 - disables avalanche source
    if (a&1) { no_crc = 1; }       else { no_crc = 0; }
    if (a&2) { … rf_source = 1 … } else { rf_source = 0; rf_running = 0; … }
    if (a&4) { no_avalanche = 1; } else { no_avalanche = 0; }
}
```

Hex digits are also accepted (`a`-`f`, `A`-`F`, both `goto set`), so the
argument range is 0-15; bit 3 is parsed and ignored.

This **confirms the previously-unverified table** and explains it:

| cmd | bits | whitener | RF | avalanche | meaning |
|---|---|---|---|---|---|
| `cmd0` | 000 | **on** | off | on | avalanche, whitened — **the power-up default** |
| **`cmd1`** | 001 | **off** | off | on | **raw avalanche — what an assessment needs** |
| `cmd2` | 010 | on | on | on | avalanche + RF, whitened |
| `cmd3` | 011 | off | on | on | raw avalanche + RF |
| `cmd4`/`cmd5` | 100/101 | — | off | **off** | no noise source |
| `cmd6` | 110 | on | on | off | RF only, whitened |
| `cmd7` | 111 | off | on | off | raw RF only |

**RF can be held off independently.** It is bit 1, orthogonal to the whitener
(bit 0) and the avalanche source (bit 2). `cmd1` gives raw avalanche with RF
disabled, which is the required configuration — the RF source is a
shared-environment channel and must stay off for a two-source independence
claim.

**Is raw mode "test-only"?** The firmware imposes **no** restriction: the
bitmask is parsed uniformly with no gating, no privilege, no warning. The
"intended for testing and validating the hardware" characterisation comes from
the OpenBSD `uonerng(4)` man page — that is the *driver author's* description of
intent, not a firmware constraint. **Supported-versus-test-only is a vendor
policy question, not a code question**, and the code permits it freely.

## 2. The whitener is the CC111x hardware CRC16, and raw really is raw

`cdc_app.c:161-166`:

```asm
mov  _RNDH, dpl          //  RNDH = x;      // through the crc16
jb   _no_crc, 0200$      //  if (!no_crc) { // whiten the data
     mov dpl, _RNDH      //      x = RNDH;  // hardware
                         //  }
0200$:
```

Every sample byte is written into `RNDH`, the CC111x's hardware CRC16 register.
When whitening is **enabled** the value read back from `RNDH` *replaces* the
sample. When `no_crc` is set the original byte passes through **unmodified** —
the CRC register is still written as a side effect, but its output is discarded.

So `cmd1` output is the unconditioned sample stream. This confirms
`go-onerng`'s `DisableWhitener` documentation ("disables the on-board CRC16
generator") against the source, and identifies the transform exactly: a CRC16,
a linear mixer, not a hash and not a CSPRNG.

## 3. A second conditioning path the summaries do not mention

**This is the finding that reading the source produced.** `queue_pool_data` has
two branches, and the whitener setting does not affect either:

```asm
                    // if (pool_count == POOL_SIZE) {
                    //     // the pool is full, keep stiring it
*pool_update++ ^= x //     *pool_update++ ^= x;
                    // } else {
*pool_in++ = x      //     *pool_in++ = x;
```

- **Pool not full** → the byte is stored verbatim. Genuinely raw.
- **Pool full** → the byte is **XORed into an existing stored byte**.

`POOL_SIZE = 7168` (`Makefile:61`, `-DPOOL_SIZE=7168`).

**Why this matters for assessment.** XOR-combining two independent samples
*raises* apparent entropy per bit. So a capture that lets the pool overflow is
assessing XOR-mixed data and will measure a min-entropy rate **higher than the
source deserves** — permissive, in exactly the direction that matters. And it
happens with `cmd1` set, because the whitener bit does not gate this path.

**The margin is small.** At 0.35 Mbit/s ≈ 43,750 B/s, a 7,168-byte pool fills in

> 7168 / 43750 ≈ **0.164 s — about 160 ms**

So any read gap over roughly a sixth of a second begins silently XOR-mixing.
A capture tool that stalls on a disk write, a scheduler hiccup, or a log flush
crosses that threshold easily.

*(The 0.35 Mbit/s figure is a community number from the `awesome-hwrng` table,
not a vendor specification, so the 160 ms is an estimate of the right order
rather than a measured constant. The 7168 is exact, from the Makefile.)*

## 4. Power-up default and persistence — the harness hazard, confirmed

`cdc_app.c:45-48`:

```c
__bit no_crc=0;        // whitening ENABLED
__bit no_avalanche=0;  // avalanche ENABLED
__bit rf_source=0;     // RF OFF
```

These are `__bit` variables in RAM with compile-time initialisers. **The device
powers up in `cmd0` — avalanche, whitened** — which matches the OpenBSD man
page calling that "the manufacturer's default mode".

**There is no persistence.** Searching `cdc_app.c` for flash or EEPROM writes of
the mode finds none; the only `flash` symbol in the file is the **status LED**
blink state (`// too many 00s? flash 1 on 3 off - stuck at 0`), not storage. So
a mode selection:

- persists for as long as the device stays powered, and
- **reverts to whitened on any power-cycle, re-plug, or host reset.**

This is precisely the hazard the brief anticipated: **a mode that silently
reverts produces whitened output that looks like raw output.** A harness must
re-send the mode command at the start of every capture session and must not
assume a previously-set mode survived. The firmware provides no way to *read
back* the current mode, so the harness cannot verify it — it can only re-assert
it.

## 5. Firmware version, and a naming trap

- `cdc_app.c:1-2`: `#define VERSION 3` and `__code char version[] = "\r\nVersion 3\r\n"`.
  The device reports this via the `cmdv` command (`:668-671` push `VERSION` and
  `VERSION>>8`).
- `Makefile:21`: `THIS_VERSION = 2  # suota version` — a separate
  downloadable-build counter, incremented per release.

**The trap:** the product line has a hardware **"V3 external"** and the firmware
in this repository is **"Version 3"**. These are different things and the
numbers coinciding is a coincidence. Do not treat a hardware-V3 unit as
confirmed to run this source.

**Not established:** whether a currently-shipping V3 unit runs firmware matching
this 2015 source. The repository has not been pushed to since 2015-06-18 while
the `hardware` repo saw changes into 2017, so the hardware plausibly moved after
the published firmware stopped. **`cmdv` on a received unit is how to check**,
and that check should happen before the unit is trusted for assessment.

One reassuring detail from `README.md`: this firmware is a fork of MoonbaseOtago's
CheapRF code with "the RF and SUOTA bits removed for obvious security reasons" —
i.e. radio transmit and over-the-air update were deliberately stripped. RF
*noise sampling* remains (that is the `cmd2`/`cmd3`/`cmd6`/`cmd7` path); what was
removed is the ability to transmit and to be updated remotely.

## What is primary-sourced versus not

| Claim | Status |
|---|---|
| Mode digit is a bitmask; bit 0 whitener, bit 1 RF, bit 2 avalanche | **Primary source**, `cdc_app.c:348-375` |
| `cmd1` = raw avalanche, RF off, whitener off | **Primary source**, derived from the bitmask |
| RF independently controllable | **Primary source** |
| Whitener is the hardware CRC16 via `RNDH` | **Primary source**, `cdc_app.c:161-166` |
| Raw mode passes samples unmodified | **Primary source** |
| Pool XOR-stirs on overflow; `POOL_SIZE = 7168` | **Primary source**, `cdc_app.c` + `Makefile:61` |
| Power-up default is whitened avalanche | **Primary source**, `cdc_app.c:45-48` |
| Mode is RAM-only and reverts on power-cycle | **Primary source** (absence of any persistence path) |
| No firmware restriction marking raw as test-only | **Primary source** |
| "Test-only" framing | **Driver documentation** (OpenBSD `uonerng(4)`), i.e. author intent |
| ~160 ms overflow margin | **Derived**, using a community throughput figure — order-of-magnitude |
| Whether a current V3 unit runs this firmware | **NOT ESTABLISHED** — check `cmdv` on receipt |
| Min-entropy per bit | **No claim found anywhere.** Waits for the tools, and now also for build provenance (`XR-04`) |

## Consequences

**For the purchase.** The raw-mode question that was going to need a vendor
email is settled from source: raw avalanche with the whitener off and RF off is
`cmd1`, the firmware permits it without restriction, and it is genuinely
unconditioned. The remaining open questions are only **availability** (the
Shopify store returns HTTP 402) and **which firmware a shipped unit carries**.
The email, if sent, no longer needs to ask about raw mode — only about stock, US
shipping, and the firmware version on current units.

**For the harness.** Two hard requirements, both from source, recorded in
`CROSS-REPO-FINDINGS.md` as `XR-05`:

1. Re-send the mode command at the start of **every** capture session. The mode
   is RAM-only, reverts to whitened on re-plug, and cannot be read back.
2. Sustain reads with no gap beyond roughly 160 ms, or the pool overflows and
   the delivered bytes are XOR-mixed — which inflates the measured min-entropy
   rate rather than depressing it.
