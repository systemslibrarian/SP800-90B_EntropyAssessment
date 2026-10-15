# Second entropy source: eliminations, and a fresh search

Research note, 2026-10-15. For the Chor–Goldreich second source. Criteria
reordered after the first pass, where availability decided the answer while
ranked fifth.

**Result of the device search: nothing passes criteria 1 through 4** — the two
criteria that matter most are anti-correlated in this market.

**But see Part 3, added 2026-10-15.** The search omitted the option of a
**second unit of the device already owned**, which passes 1, 3 and 4 and fails
only criterion 2. Assessing it properly changes the recommendation: two Infinite
Noise units support a genuine Tier 2 claim with a named, bounded gap, and are
the cheapest available route to the goal. **Part 3 supersedes Part 2's
recommendation.**

---

## Part 1 — the eliminations, recorded so they survive a storefront reopening

### OneRNG — eliminated on design, not availability

Two disqualifying properties, both established from firmware source
(`github.com/OneRNG/firmware`, `cdc_app.c`; full working in
`ONERNG-RAW-MODE-FROM-SOURCE.md`). Raw mode *does* exist and is genuinely raw —
that question is settled — and the device is eliminated anyway.

**1. The mode is set-only.** Mode state lives in three `__bit` RAM variables
with compile-time initialisers (`no_crc=0`, `no_avalanche=0`, `rf_source=0`), so
the device powers up **whitened**, the selection does not persist across a
power-cycle or re-plug, and **the firmware offers no command to read the current
mode back**. Raw mode can be asserted and never verified, and a reverted mode
produces whitened output that is byte-for-byte indistinguishable from raw.

For a project whose whole method is refusing unverifiable assertions, that is
disqualifying on its own. It is the same shape as the operator-asserted restart
that already has to be caveated — except here the operator cannot even check
after the fact.

**2. `queue_pool_data` XORs into stored bytes on overflow, and the whitener bit
does not gate it.**

```
pool full     ->  *pool_update++ ^= x     // "the pool is full, keep stiring it"
pool not full ->  *pool_in++ = x
```

`POOL_SIZE = 7168` (`Makefile:61`). At the community figure of 0.35 Mbit/s the
pool fills in **≈164 ms**, so any read gap beyond roughly a sixth of a second
silently XOR-mixes samples. XOR of independent samples **raises** apparent
entropy per bit, so an overflowing capture measures *higher* than the source
deserves — the permissive direction — and **nothing in the protocol reports that
it happened**. Unmitigable from the host: there is no overflow flag to read, and
the only defence is never stalling.

**3. The version trap.** The product line has a hardware **"V3 external"**; the
published firmware is **"Version 3"** (`cdc_app.c:1`). These are unrelated and
the coincidence is misleading. The firmware repository stopped at
**2015-06-18** while the hardware repository saw changes into **2017-01-30**, so
the published firmware may not describe a unit one would actually receive —
meaning even the good research above might not apply to the device in hand.
`cmdv` reports the firmware version and would have to be checked on receipt.

Availability (the Shopify store returning HTTP 402) is now the *least*
interesting reason this device is out.

### ChaosKey — eliminated on availability

Out of production per Altus Metrum's own page, with the reason given (slow first
run; per-unit international shipping dominated cost) and *"They might make more
some day, but no promises."* No successor. Secondary market only. Separately,
raw mode was never established: the mainline Linux driver
`drivers/usb/misc/chaoskey.c` has no raw/cooked distinction, so any conditioning
is in firmware, and the vendor pages and Keith Packard's blog do not describe it.

---

## Part 2 — the fresh search

### Criteria, in priority order

1. **Purchasable now** — working checkout, in stock, ships to the US, verified
   by reaching the product page.
2. **Noise mechanism not Johnson–Nyquist thermal.**
3. **Raw output and the whole output path established from source** — including
   what happens under timing pressure.
4. **Mode verifiability** — can the device report its configuration, not merely
   accept one.
5. Price and throughput, last. The Infinite Noise's 0.3 Mbit/s gates the pair,
   so anything at or above it wastes nothing.

### Results

| Device | 1 purchasable | 2 non-thermal | 3 path from source | 4 verifiable | price |
|---|---|---|---|---|---|
| **BitBabbler Black/White** | ✗ stock claim is 2021-vintage; email-only ordering | ✓ avalanche | ✓ **no firmware** + open host source | ✓ nothing to verify | AUD$99 / $199 |
| **TectroLabs SwiftRNG** | ✓ **live checkout** | ✓ avalanche (zener) | ✗ **encrypted firmware** | ? | $299 (LE $199 sold out, Pro $499) |
| **ubld.it TrueRNGpro** | ✗ seller "on a break" | ✓ avalanche junction | ✗ closed firmware | partial — modes, readback unknown | $99 |
| OneRNG | ✗ | ✓ | ✓ | ✗ **disqualifying** | $40 |
| ChaosKey | ✗ out of production | ✓ | ✗ | ? | — |

### BitBabbler — passes 2, 3 and 4; fails 1 only on staleness

The strongest candidate on the criteria that came out of the OneRNG work, and it
sidesteps OneRNG's defect by construction.

- **Criterion 3.** Vendor design statement, their own page: *"our design
  requirements called for there to be **no firmware hidden on the device**, we
  just needed to connect the **raw output bitstream** to whatever people wanted
  to use to consume it."* And the XOR folding is **host-side and explicit** —
  the Debian `seedd.1` man page: *"Set the number of times to fold the
  BitBabbler output before adding it to the pool. Each fold will take the first
  half of the block that was read and XOR it with the bits in the second half."*
  Host-side, operator-selected, applied before the *host* pool. **There is no
  device-side pool to overflow**, so timing pressure cannot silently introduce
  mixing. That is exactly the property OneRNG lacks.
- **Criterion 4.** With no device-side configuration there is **no device mode
  to verify** — the configuration is host software state, which the operator
  sets and can inspect directly. That is a stronger answer than "the device can
  report its mode", because there is nothing that can silently disagree.
- **Criterion 2.** Avalanche noise. Non-thermal.
- **Presumed DORMANT, not merely stale (recorded 2026-10-15).** Verified
  externally: Ron Lee's last visible Debian upload is **2018-12-17**; `opus` has
  been maintained by another developer since **2023**; `bit-babbler` was removed
  from unstable **2023-05-27** after a final upload in **November 2021**; and
  several of his other packages carry RC bugs or failing CI. Combined with every
  `bitbabbler.org` page being `Last-Modified 2021-12-03`, the reasonable
  inference is a dormant project rather than a live vendor with a stale website.
  The email is still worth sending — it costs nothing — but it should not be
  expected to succeed, and the plan should not wait on it.
- **Criterion 1 — where it fails.** `bitbabbler.org` is reachable (its TLS chain
  is misconfigured; plain HTTP works) and `buy.html` states *"White devices in
  stock ready for immediate shipping"* at **AUD$199 White / AUD$99 Black**. But
  **every page returns `Last-Modified: Fri, 03 Dec 2021`** and the blog's most
  recent entry is 2021. So the stock statement is a **five-year-old static
  page, not live inventory** — the same class of stale assertion that made
  `awesome-hwrng` list two dead devices as available. Ordering is by email to
  `sales@bitbabbler.org`; there is no checkout. Debian removed the package from
  unstable on **2023-05-27** and from testing on **2022-08-29**, and it is in no
  current Debian release — a further liveness signal, though the hardware needs
  no updates precisely because it has no firmware.

### TectroLabs SwiftRNG — the only verified live checkout, and it fails criterion 3

`shop.tectrolabs.com` is live with a working cart and card/PayPal/Bitcoin
payment: **SwiftRNG $299**, Pro $499, Zn $399, MicroRNG $149, AlphaRNG $549,
with **SwiftRNG LE $199 marked "Sold Out"**. Avalanche breakdown in zener
diodes — non-thermal. Raw samples are offered (the Pro's optional output
includes *"1000000 RAW random bytes retrieved from the first and second noise
sources"*), and the host API is source-available with RCT/APT health tests run
host-side.

**But the device uses "secure booting from an encrypted firmware image, with
device access and debugging disabled."** So what happens to a sample between the
noise source and the USB endpoint **cannot be established from source**. Whether
there is a pool, whether it mixes under timing pressure, whether "RAW" is raw —
all rest on vendor assertion. Given that reading OneRNG's source is exactly what
found its disqualifying XOR path, accepting a vendor assertion here would be
adopting the posture this project rejects everywhere else.

### ubld.it TrueRNGpro — purchasability failed at the checkout

Avalanche effect in a semiconductor junction; dual independently shielded
generators; **explicit Whitened / Raw / Diagnostic mode selection**, advertised
as *"allowing for independent verification of the raw data stream"* — which is
the right feature. >3.2 Mbit/s, $99.

Its Tindie page says **"Currently on a break — the seller is not accepting
orders at this time"** and *"This item does not ship to [selected country]"*.
The vendor's own `ubld.it/products/` page shows no prices, no add-to-cart and no
checkout, with several products marked Discontinued. Firmware openness is not
established and is presumably closed, so criterion 3 fails regardless.

### Cast wider — what the industry/quantum tier looks like

TectroLabs is the industry-facing end of what is reachable at this price class,
and AlphaRNG at $549 is its newer part. Beyond that, photonic and quantum
modules (ID Quantique, Quside, QuintessenceLabs and similar) are B2B
quote-driven rather than checkout, an order of magnitude more expensive, and
uniformly closed-firmware — so they fail criterion 3 harder, not softer, while
costing more. Devices named as noise sources in SP 800-90B validation
submissions are overwhelmingly **chips inside products** (CPU and SoC TRNG
blocks), not purchasable USB devices, so that route does not yield a candidate
either.

---

## Why nothing passes

The two criteria that matter most are **anti-correlated in this market**:

- Devices whose output path can be read from source are **open hobbyist
  projects** — and all three found (OneRNG, ChaosKey, BitBabbler) are dormant or
  out of production, with stock claims dated 2021 or earlier.
- Devices that are **purchasable today** are commercial products with encrypted
  or closed firmware, where the output path is a vendor claim.

There is no device in this search that is both buyable and readable. That is a
property of the market in October 2026, not a gap in the search, and a further
search is unlikely to change it without relaxing one of the two criteria.

## Recommendation

**Do not buy anything yet, and do not relax criterion 3 to make a purchase
possible.**

1. **Email BitBabbler** (`sales@bitbabbler.org`) — the single action worth
   taking. It is the only candidate that passes 2, 3 and 4, and it fails 1 only
   because its site has not been touched since 2021. If Ron Lee still ships, it
   passes everything and the question is closed at AUD$99. Ask: current stock,
   shipping to the US, and whether the design is unchanged from the 0.9 source.
   Unlike the OneRNG email, this one can actually change the outcome.

2. **If BitBabbler is dead, the honest position is Tier 1.** SwiftRNG is
   purchasable and would give a genuinely different noise mechanism, but
   accepting it means accepting a vendor assertion about the output path — the
   exact posture that reading OneRNG's firmware just proved unsafe, where a
   published-source device turned out to XOR-mix under timing pressure with no
   host-visible signal. Buying a closed device and *hoping* its RAW mode is raw
   would be a claim upgrade on vendor evidence.

3. **State the consequence rather than papering over it.** Tier 2 needs a second
   device that meets this project's evidentiary standard. If none is
   purchasable, the product sits at **Tier 1 with the computational premise
   stated** — which is where it already sits. That is a finding about the goal,
   not a deficiency in the search, and it is a better outcome than a Tier 2
   claim resting on a device whose output path nobody can read.

## Claims recorded as claims

No min-entropy-per-bit figure for any candidate is treated as measured. No
vendor entropy claim is accepted. Throughput figures are vendor or community
numbers. The only measured entropy figure in this project remains the Infinite
Noise's **0.696** after margin, and per `XR-04` even that is uninterpretable
until the assessing binary's build provenance is established.

| Claim | Status |
|---|---|
| OneRNG mode set-only, no read-back, no persistence | **Primary source** — firmware |
| OneRNG XOR-on-overflow, `POOL_SIZE 7168` | **Primary source** — firmware + Makefile |
| OneRNG ≈164 ms overflow margin | **Derived** from a community throughput figure |
| BitBabbler "no firmware hidden on the device" | **Vendor design statement**, their own page — not independently verified in silicon |
| BitBabbler fold is host-side | **Primary source** — Debian `seedd.1` man page |
| BitBabbler stock, AUD$99/$199 | **Vendor page, last modified 2021-12-03** — stale |
| bit-babbler absent from current Debian | **Primary source** — Debian package tracker |
| SwiftRNG encrypted firmware, debugging disabled | **Vendor statement** |
| SwiftRNG shop live, prices, LE sold out | **Verified** — reached the shop page |
| TrueRNGpro seller on a break | **Verified** — reached the Tindie page |
| ChaosKey out of production | **Vendor statement**, Altus Metrum's own page |
| Any device's min-entropy rate | **No claim found for any candidate** |

---

# Part 3 — two Infinite Noise units, assessed properly (2026-10-15)

The search did not consider buying a **second unit of the device already in
hand**. Assessed here rather than dismissed on mechanism. **Conclusion: this
supports a genuine Tier 2 claim, with one named gap and three procedural
requirements — and it is the cheapest available route to the goal.** But two
parts of the proposal's reasoning need correcting, one in its favour.

## First, a correction to the premise

The proposal says criteria 1, 3 and 4 "pass trivially" because the driver has
already been read. **It had not been** — this session read the SP 800-90B tools,
not the Infinite Noise driver. Criterion 3 therefore had to be established, and
now has been, from `waywardgeek/infnoise`:

| fact | source |
|---|---|
| **No microcontroller on the device**; it "only returns raw data, direct from the noise source" | project documentation |
| USB interface is an **FT240X**, driven via `libftdi` | `software/libinfnoise.c` |
| Device is driven in **`BITMODE_SYNCBB`** — synchronous bit-bang | `libinfnoise.c:258` |
| Host writes alternating **`SWEN1`/`SWEN2`** phase bytes; reads back **`COMP1`/`COMP2`** | `libinfnoise.c:31-32, 100-101, 357, 363` |
| Whitening is **host-side**, a Keccak/SHA3 sponge with 1600-bit state, and optional | `libinfnoise.c:283-286` |
| **`--raw`** option exists | `infnoise.c:51` |
| Health check is host-side, predictor-based against `DESIGN_K`, and gates output | `libinfnoise.c:44, 107, 114` |

So criterion 3 does pass, and for the strongest possible reason: **there is no
firmware on the device at all**, so there is no hidden output path — the same
property that made BitBabbler attractive. Criterion 4 passes the same way: with
no device-side configuration there is no device mode to verify.

**Criterion 1, measured:** €30 incl. VAT at `leetronics.de`, working
add-to-cart, ships from Germany with US distributors named (Enhanced Radio
Devices, Crowd Supply) — but **"available on backorder with 3-4 month delivery
time"**. Purchasable, with a lead time, not in stock.

## Was criterion 2 the right criterion?

**The proposal is formally right and incompletely right.**

Right: Chor–Goldreich requires two **independent** sources each above the
min-entropy threshold. Independence is a property of the joint distribution,
`P(X,Y) = P(X)·P(Y)`. Nothing in CG requires different physical mechanisms.
Two separate resistors undergo separate thermal agitation; Johnson–Nyquist noise
arises from carrier motion within a specific resistor and there is no coupling
mechanism between two resistors in two enclosures at the relevant scale. **The
entropy injected at each step is genuinely independent between devices.** That
part of the argument holds.

Incomplete: criterion 2 was a proxy, but for something real, and not for
correlated noise. **Mechanism diversity hedges against correlated *estimation
error*, not against correlated noise.** CG's guarantee is *conditional* on each
source actually having its claimed min-entropy. If two units share a design
flaw — the op-amp gain `K` lower in practice than `DESIGN_K`, a comparator
offset, a layout sensitivity — then both sources' min-entropy is overstated **by
the same amount**, measured with the same model, and CG's conclusion fails while
every measurement still reads fine. Two *different* designs make a shared
overestimate far less likely.

So the reframing is correct that CG needs independence rather than diversity,
but the thing diversity was protecting is the **premise**, not the
independence. That distinction is what the rest of this assessment turns on.

## Correlated failure modes, from the source

One item on the proposal's list is **absent for this device**, and that is worth
stating because it was offered as a risk:

- ~~**shared firmware behaviour**~~ — **there is no firmware.** No
  microcontroller, no onboard state machine, nothing to carry a shared bug. The
  only shared code is host-side, where it is readable and controllable.

The remaining modes, in descending order of how much they threaten the claim:

**1. Shared USB supply — the only channel that plausibly creates genuine
statistical dependence.** Both units draw the same 5 V rail. The device
amplifies thermal noise through an op-amp and digitises it with a comparator;
supply ripple modulates both the gain and the comparator threshold. The *same
external signal* is then injected into *both* mappings from noise to bits, which
can correlate the two output streams at the ripple frequency. This is the
strongest candidate for breaking independence rather than merely degrading the
estimate.

**2. Host-clocked entropy loop.** Confirmed: the multiplier advances only while
the host writes `SWEN1`/`SWEN2` phases. One host process driving both devices
is a shared timing dependency that two devices with independent interfaces would
not have.

*But the channel is narrower than it first appears.* In `BITMODE_SYNCBB` the
FT240X clocks the pattern out at its **own** configured rate from its **own**
oscillator, and the host supplies 512-byte buffers. So per-step timing is
chip-local and independent per unit; what the host shares is **buffer refill**.
A host stall therefore starves both devices at the same moment — plausibly
producing simultaneous stuck-phase runs — rather than correlating individual
bits. Real, bounded, and detectable.

**3. Shared design sensitivity to temperature.** Johnson noise power is
proportional to T, so a room-temperature excursion moves both units' noise
amplitude together. This changes **how much entropy each has**, identically — it
does not make the bit streams correlated. Affects the estimate, not independence.

**4. Shared host driver, and a procedural trap.** The driver's Keccak sponge and
its `/dev/random` feed are both host-side. If two daemons feed the kernel pool,
"two sources" becomes meaningless — the pool mixes them and CG has nothing to
work with. Worse, a *shared* sponge instance across both streams would couple
them catastrophically. This is not a device property; it is a way to destroy the
claim by capturing wrongly.

**5. Shared health-check blindness.** Both units run the same predictor-based
check against the same `DESIGN_K`. A failure mode that check does not detect
goes undetected on both. Correlated blindness, not correlated noise.

## Detectable from the output, or not

| mode | detectable? | consequence |
|---|---|---|
| Host-stall starvation (2) | **Yes** — simultaneous runs/bias in both streams; cross-correlation reveals it | **monitoring requirement** |
| Supply-ripple coupling (1) | **Yes in principle** — cross-correlation at the ripple frequency. **No existing health check does this**: the driver's checks are per-stream | **new monitoring requirement** |
| Temperature-driven entropy loss (3) | **Yes** — per-stream min-entropy falls and the driver's own check gates output | monitoring, already implemented |
| Capture error (4) | **Yes** — by construction, if the capture path is audited | procedural requirement |
| **Shared design flaw inflating both estimates (5)** | **NO** | **permanent caveat** |

The last row is the whole of the residual risk. If the shared design overstates
each unit's min-entropy, both measurements agree, both health checks pass, both
streams look independent, cross-correlation finds nothing — and CG's premise is
false. **Nothing in the output can reveal it, because the error is in the model
used to interpret the output, and both units share the model.**

## What claim does this actually support?

Re-derived rather than adopted. **A genuine Tier 2, with a documented
mechanism-diversity gap, conditional on three requirements** — not an unqualified
Tier 2, and not "no Tier 2".

The three requirements are not optional caveats; without them the claim is
false rather than weak:

1. **Two separate raw captures.** `--raw` per device, no Keccak, no
   `/dev/random`, no shared sponge, no kernel-pool mixing. The extraction is
   ours to perform on two independent byte streams.
2. **Cross-correlation monitoring between the two streams.** This does not exist
   today — the driver's health checks are per-stream and would not notice two
   streams moving together. It is the only defence against the supply-ripple and
   host-stall channels, and it has to be built.
3. **Independent power if achievable.** A separately-regulated powered hub, or
   the second unit on a different host, cuts the strongest dependence channel at
   source. Worth the cost of a hub.

And one honest statement in the claim itself: **two instances of one design do
not give what two designs would give.** They give independence of the noise and
shared exposure to a design error in the estimate. The claim should say that
rather than implying parity with mechanism diversity.

Against the proposal's own framing: yes, "genuine Tier 2 with a named residual
risk" — but the residual risk is specifically **correlated estimation error**,
which is the one thing CG is structurally unable to absorb, and it deserves
naming in those terms rather than as a generic common-mode caveat.

## Honest comparison

| route | purchasable | output path | independence | min-entropy premise |
|---|---|---|---|---|
| **Two Infinite Noise** | ✓ €30, **3-4 month backorder** | ✓ **no firmware**, open host source, `--raw` | ✓ noise independent; one real coupling channel, detectable | ⚠ **shared design → shared overestimate, undetectable** |
| One device, Tier 1 | — already owned | ✓ same | n/a | computational premise stated |
| SwiftRNG or similar | ✓ live checkout, $299 | ✗ **encrypted firmware, vendor claim** | ✓ different mechanism | ⚠ independent design, but path unreadable |

**Two Infinite Noise units beat SwiftRNG** on the criterion that this audit has
repeatedly shown to be decisive: the output path is readable. Reading OneRNG's
firmware found an XOR-on-overflow path that inflates measured entropy with no
host-visible signal — precisely the class of defect a vendor datasheet would
never disclose. Accepting SwiftRNG means accepting that risk unexamined, in
exchange for mechanism diversity that hedges a *different* risk. Given this
project's method, the readable path is worth more.

**Two Infinite Noise units beat Tier 1** because Tier 1 states a computational
premise, while two units support an information-theoretic claim with a named and
bounded gap. A bounded gap that is written down is a better position than an
unbounded premise.

## Recommendation — replaces Part 2's

**Buy a second Infinite Noise unit.** €30, working checkout, 3-4 month
backorder, or sooner via the named US distributors. It is the cheapest route to
a real Tier 2 claim and the only one whose output path this project can read.

Conditions, all of which must be met before the claim is made:

1. Separate raw captures, no shared whitening or pool.
2. Cross-correlation monitoring built and shown failing on deliberately coupled
   input before it is trusted.
3. Independent power where achievable.
4. The claim states the mechanism-diversity gap explicitly: two instances of one
   design, shared exposure to a design error in the min-entropy estimate,
   undetectable from the output.

**If a third mechanism later becomes purchasable with a readable path, it
upgrades this claim rather than replacing it** — a third source would let the
shared-design risk be cross-checked against different physics, which is the only
thing that closes the gap named above.

Physical items remain **NOT RUN**. The 0.696 figure is one unit's measurement,
and per `XR-04` it is uninterpretable until the assessing binary's build
provenance is established — which applies with equal force to a second unit.
