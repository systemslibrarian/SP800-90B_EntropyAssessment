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

---

# Part 4 — batch correlation, and a correction to Part 3 (2026-10-15)

Availability, verified: **Crowd Supply, $39 + $8 US shipping, "Orders placed now
ship Jan 29, 2027", pre-order.** Manufactured by **leetronics UG** (Wiesbaden);
"Sold and shipped by Crowd Supply", i.e. Crowd Supply is a *distributor* for the
same manufacturer as `leetronics.de`. Ordering the second unit now means both
arrive together, so **Tier 2 costs no schedule**.

## First, a correction to Part 3's residual risk

Part 3 said that if a shared design flaw put both units at 0.4 rather than
0.696, "you'd never know from the output." **That was too strong, and the
correction sharpens what the real risk is.**

SP 800-90B min-entropy estimation is **empirical, not model-based**: the ten
estimators compute statistics of the sample stream itself. They do not consult
`DESIGN_K` or any device model. So a fault that genuinely *reduces* the stream's
entropy — a resistor out of tolerance lowering the gain `K`, hence lowering
log2(K) per bit — would show up as a **lower measured figure**. That failure is
detectable, and it is detectable on a single unit.

(The *driver's* health check is the model-based one — a predictor against
`DESIGN_K`, `libinfnoise.c:44`. That is a different mechanism from the
assessment and would mis-report if `K` drifted. But it is not what the Tier 2
figure rests on.)

**So the undetectable risk is narrower and more specific than Part 3 stated:**
it is **shared source structure lying in the SP 800-90B estimator battery's
blind spot.** The battery covers a particular family of dependencies — i.i.d.
deviation, Markov, compressibility, predictability. A structure outside that
family (a periodic modulation from a switching supply, a long-range correlation)
reads high on all ten estimators. If both units share that structure, both read
high and both are wrong — and **the blind spot is a property of the estimator,
not of the unit, so no amount of measuring either unit reveals it.**

That is the risk CG cannot absorb, and it is what design or batch commonality
can deliver.

## Batch correlation is not design correlation

They differ in origin, permanence, examinability and mitigation, and collapsing
them loses all four distinctions.

| | **Design correlation** | **Batch correlation** |
|---|---|---|
| Origin | the schematic, topology, component choices | a production run: resistor lot out of tolerance, mis-set gain trim, a comparator reel |
| Present in | **every unit ever made** | only units from that run |
| Permanence | **permanent** | contingent |
| Examinable by | **reading the schematic and BOM** — open hardware, so this is possible today, before purchase | **only by comparing units from different runs** |
| Mitigated by | a different *design* — i.e. mechanism diversity, which is what criterion 2 was protecting | units from different *batches* |
| Status for this plan | **dominant, and accepted as the named gap** | second-order, and addressable later |

The practical asymmetry: design correlation can be *investigated now* — the
Infinite Noise is open hardware, so the schematic and BOM are readable, and a
careful look at the gain-setting resistor pair and the comparator stage is
available for free before anything is bought. Batch correlation cannot be
investigated at all without two units from two runs.

## Can the measurement distinguish them? No — and here is what follows

If both units read 0.70 and the truth is 0.55, **nothing in either figure says
whether the cause is the design or the batch.** Both hypotheses predict the same
observation. One pair of units cannot separate them.

But the two figures are not therefore uninformative:

- **If the two units' measured figures differ materially**, that is direct
  evidence of unit-to-unit variation — which bounds how tight the component
  tolerances actually are, and therefore how plausible a batch-wide
  out-of-tolerance fault is.
- **If they agree closely**, that is weak evidence that unit variation is small.
  It is **not** evidence that the design is sound, because a design-caused
  structure would make them agree closely *and* both be wrong.

So close agreement is the ambiguous outcome and disagreement is the informative
one — which is the opposite of the intuition that matching figures are
reassuring.

### Measurement requirement: record separately, never average

**Both units' figures must be recorded and compared individually, before any
combination.** Averaging is wrong for two independent reasons:

1. **It destroys the differential signal** — the one piece of batch evidence a
   single pair can give.
2. **More fundamentally, CG requires *each* source to exceed the threshold, not
   their mean.** If unit A reads 0.72 and unit B reads 0.58, the average 0.65
   looks comfortable while unit B sits 0.08 above the 0.5 floor. The governing
   quantity is the **minimum of the two**, so an average actively conceals the
   binding constraint.

"Two units measured as one pair" is a measurement that cannot be taken apart
afterwards, and the quantity CG needs is not recoverable from it.

## Is cross-batch sourcing worth doing? Re-derived — no, and for a reason beyond schedule

The proposal suspects design correlation dominates and batch diversity is not
worth a schedule risk. **That conclusion holds, and the strongest argument for
it is not the schedule.**

**1. The intended diversity probably would not materialise.** Crowd Supply is a
*distributor for leetronics UG*, the same manufacturer as `leetronics.de`.
Buying one from each gives two units from one manufacturer, and the ship windows
coincide (`leetronics` 3-4 months ≈ Jan–Feb 2027; Crowd Supply Jan 29 2027), so
both are plausibly fulfilled from **the same production run**. Paying extra
shipping and accepting a vaguer second date for *possibly zero* batch diversity
is a bad trade on its own terms, independent of schedule. **Batch diversity is
not obtained by buying from two distributors of one manufacturer** — it would
require confirming distinct production runs, which neither storefront exposes.

**2. Batch diversity says nothing about the dominant risk.** Even if genuinely
different batches were obtained, they share the design. The permanent,
examinable-from-source, mechanism-level risk is untouched.

**3. Desynchronised arrival delays the claim.** Both units arriving together
means one calibration session in January. Split arrival means the second figure
lands months later and the Tier 2 claim waits on it.

**4. There is a cheaper way to get the batch evidence, later and for free.**
Once the first two units are calibrated and their individual figures recorded, a
**third unit bought from a later production run** gives a genuine cross-batch
comparison against two already-characterised units — stronger evidence than a
two-unit cross-batch pair would have given, at no schedule cost now, and only if
the first comparison suggests it is worth having. Defer it.

**Recommendation: buy the second unit from Crowd Supply now, same batch, both
arriving 2027-01-29.** Accept batch correlation as a *contingent* risk recorded
separately from the design gap, obtain the differential evidence by measuring the
two units separately, and hold the third-unit option in reserve.

## Added to the January calibration list

Before any combination, extraction, or Tier 2 claim:

1. **Record each unit's serial number and any batch or date markings** on the
   PCB and packaging, photographed. If no markings exist, record that — absence
   of batch identification is itself a limit on what can be reconstructed later.
2. **Capture and assess each unit entirely separately**, raw (`--raw`), with no
   shared whitening, no `/dev/random`, no shared Keccak instance.
3. **Record each unit's min-entropy figure individually**, with the full
   per-estimator breakdown, not just the minimum. Never average the two.
4. **Compare the two figures explicitly** and record the difference. A material
   difference is evidence about unit variation; close agreement is the ambiguous
   outcome, not the reassuring one.
5. **Record the binding constraint as the minimum of the two**, since that is
   what CG requires.
6. **Run the cross-correlation test between the two raw streams** (Part 3,
   requirement 2) — built and shown failing on deliberately coupled input first.
7. **Record the build provenance of the assessing binary** for every figure, per
   `XR-04`. A figure without it is uninterpretable, and that applies to both
   units equally.
8. ~~**Read the schematic and BOM for the gain-setting resistor pair and the
   comparator stage** before January.~~ **DONE 2026-10-15 — see Part 5.** It
   cost nothing and needed no hardware, as predicted. Outcome: K = 1.82
   confirmed on both channels; **tolerances absent from the BOM**, so the
   unit-to-unit yardstick is a derived band (±0.013 bit at 1 %, ±0.065 bit at
   5 %) rather than a known one; and it found a mechanism the brief did not
   anticipate — **`VREF` is a VCC33/2 divider shared by *both* comparators with a
   3 kHz corner, on a rail the FT240X's own I/O shares.** Items 9-11 follow from
   that.
9. **Run the host-supply experiment** specified in **Part 6**: three conditions
   (laptop on battery / same laptop on mains / powered hub), both units captured
   simultaneously, 5 × 1,000,000 samples per unit per condition. **The decision
   rule is pre-registered in Part 6 and is not to be revised after seeing the
   data** — 3 × the pooled within-condition SD *and* an absolute floor of
   0.013 bit, the latter because below the component-tolerance band a difference
   is uninterpretable however significant it looks.
10. **Record each unit's figures per condition, never averaged across units**,
    and record the inter-unit peak coherence per condition — that second
    statistic is the sharper test, because independence is what CG needs and
    coupling is what breaks it.
11. ~~**Build the outside-the-battery checks**~~ **DONE 2026-10-15 — built,
    calibrated and shown failing: `tools/outside-battery-check.cpp`, Part 10 /
    `OC-17`.** It is no longer a January item but a January *input*: run it on
    every raw capture in items 2, 9 and 10, alongside the battery, and **treat a
    firing as disqualifying regardless of what the battery reports.** Note its
    recorded limits — linear correlation only, lags tested only, thresholds
    calibrated for 1,000,000 one-bit samples — so a pass is never written up as
    "verified independent". Original item text, which the measurement overtook:
    **build the outside-the-battery checks** — long-lag autocorrelation to ~10⁵
    lags and a power spectrum of the raw stream. **Part 5 established that the
    estimator battery's frequency floor is 73.3 Hz** (MultiMCW's 4095-sample
    window at ~0.3 Mbit/s), so **mains at 50 Hz (6000 samples) and 60 Hz (5000
    samples) sits in the blind spot while the rectified second harmonic does
    not.** Per **Part 7** this is a *software* item, needs no purchase and no
    schedule, is available now, and is plausibly the **highest-value item on the
    whole Tier 2 list** — ahead of the second unit it would be assessing, because
    no purchase can close an estimator blind spot.

Physical items remain **NOT RUN**. No figure here is measured; the 0.696 remains
one unit's prior measurement and uninterpretable pending build provenance.
Item 8 is the only item on this list that is now DONE, and it is a paper
finding: it changes what to measure, and measures nothing.

---

# Part 5 — the schematic read, done now (2026-10-15)

Source: `waywardgeek/infnoise`, `eagle/infnoise.sch` (Eagle 7.1.0 **XML**, so
greppable) and `eagle/infnoise_SBA_BOM.csv`. Netlist extracted by parsing the
`<net>` elements. This cost nothing and needed no hardware.

## The complete parts list

| ref | part | role |
|---|---|---|
| `AMP1` | **TSV912IQ2T** | dual rail-to-rail op-amp — the two amplifier channels |
| `COMP1` | **TC75W57FK** | **dual** comparator — both channels' decisions, one package |
| `SW1`, `SW2` | **MC74VHC1G66** ×2 | analog switches — the switched-capacitor phases |
| `USB1` | **FT240XQ** | USB FIFO, and the 3.3 V supply |
| `L1` | ferrite bead 0603 | EMI filter on the 5 V input — **not** a power inductor |
| R1,R2 27Ω · R3,R4,R5,R8,R9 10K · R6,R7 8.2K | | USB termination, VREF divider, gain network |
| C1,C7 10nF · C2 4.7µF · C3,C6 100nF · C4,C5 47pF · C8,C9 220pF | | |

**No switching regulator. No charge pump. No crystal or oscillator part.**

## Question 1 — switching elements: none unintended, but switching is intrinsic

There is no buck, boost, or charge pump anywhere. `L1` is a ferrite bead on the
USB 5 V input, not an inductor in a switching topology. The FT240X uses its
internal oscillator, so there is no separate clock part.

**But the design is a switched-capacitor circuit by construction**, and the
switches sit directly in the analog signal path:

```
SW1EN  (2): SW1.IN, USB1.D2          <- bit-bang pin drives the switch
SW2EN  (2): SW2.IN, USB1.D0
AMP1OUT(4): AMP1.OUT1, R6.2, R9.1, SW2.COM
A      (4): AMP1.IN1+, C8.2, COMP1.IN1+, SW1.NO
```

So periodic switching at the sample-clock rate is the mechanism, not an
artefact. The question that matters is whether that periodicity reaches the
decision, and **Question 2 shows a path by which it does.**

## Question 2 — supply topology: regulated, and that is not the end of it

**Better than the worst case: the analog section does *not* run off raw USB
5 V.** The netlist is unambiguous:

```
VCCIN (3): C1.1, L1.1, X1.VCC                        <- USB 5 V in
VCC   (4): C2.1, C3.1, L1.2, USB1.VCC                <- 5 V after the bead
VCC33 (10): AMP1.VCC, COMP1.VDD, SW1.VCC, SW2.VCC,
            R3.1, R9.2, C6.1, USB1.3V3OUT,
            USB1.VCCIO, USB1.RESET#
```

Everything analog — op-amp, comparator, both switches, the VREF divider — runs
from **`USB1.3V3OUT`, the FT240X's internal 3.3 V LDO**, decoupled by C6 = 100nF
alone.

**Three consequences the schematic establishes:**

1. **The FT240X's own I/O rail shares that node.** `USB1.VCCIO` is on `VCC33`.
   So every bit-bang transition — including the `SW1EN`/`SW2EN` lines that drive
   the switches — draws I/O current from the same regulator node that sets the
   comparator's supply, with 100nF of local decoupling and no RC isolation
   between the digital and analog rails. Design-shared, present in every unit,
   periodic at the sample clock.

2. **`VREF` is a divider off `VCC33`, shared by *both* comparators, filtered by
   only 10nF:**

   ```
   VREF (5): C7.1, COMP1.IN1-, COMP1.IN2-, R3.2, R4.2
   ```

   R3 = R4 = 10K, so VREF = VCC33/2, with τ = 10nF × (10K∥10K) = **50 µs**, a
   corner near **3 kHz**. Any ripple on VCC33 **below ~3 kHz passes essentially
   unattenuated into the threshold of both comparators simultaneously.**

3. **So the host-dependence reading is supported.** Host supply ripple that the
   FT240X's internal LDO does not reject appears on VCC33, passes the 3 kHz
   corner into VREF, and modulates both channels' decisions in common mode. The
   LDO attenuates, and its PSRR falls with frequency and is not a precision
   part's. **Testable consequence, exactly as proposed: the same two units
   should read differently on hosts with different power sources.** That is now
   a prediction from the netlist, not a guess — see Part 6.

## Question 3 — the gain network and the comparator

**K = 1.82 confirmed from the netlist, on both channels:**

```
FB1 (3): AMP1.IN1-, R5.2, R6.1        R5 = 10K (from COMP1.OUT1), R6 = 8.2K (from AMP1.OUT1)
FB2 (3): AMP1.IN2-, R7.2, R8.1        R7 = 8.2K, R8 = 10K          <- symmetric
COMP1 (3): COMP1.OUT1, R5.1, USB1.D1  <- comparator output feeds back through R5
```

Gain `1 + R6/R5 = 1 + 8.2/10 = 1.82`, so the theoretical rate is
`log2(1.82) = 0.8638` bit/bit. This matches `DESIGN_K` in the driver and sits
above the 0.696 measured after margin, consistently.

**Tolerances are NOT in the BOM — this cannot be settled on paper.** The
expected unit-to-unit spread, which is the yardstick for reading a difference
between the two units:

| resistor tolerance | K range | entropy/bit range | spread |
|---|---|---|---|
| ±1% | 1.804 – 1.836 | 0.851 – 0.877 | **±0.013 bit** |
| ±5% | 1.738 – 1.902 | 0.797 – 0.928 | **±0.065 bit** |

So a measured difference between the two units **below ~0.013 bit is consistent
with 1% parts and says nothing**; a difference above ~0.065 bit exceeds even 5%
parts and demands explanation.

**One finding the BOM made visible: `COMP1` is a *dual* comparator in a single
package** (TC75W57FK). Both channels' comparators share a die, a supply pin and
the single VREF node. So the two channels **within** a unit are not independent
— and since the driver interleaves them into even and odd bit positions
(`libinfnoise.c:100-101`), any offset mismatch produces a **period-2 structure**
in the output. That one is comfortably inside the estimator battery's reach
(Markov lag-1, Lag predictor), so it would be caught. Worth knowing that the
"two channels" are not two sources.

## Question 4 — time constants against what the estimators actually probe

**What the battery probes**, computed at the Infinite Noise's ~0.3 Mbit/s:

| estimator | lag reach | = time | frequency floor | source |
|---|---:|---:|---:|---|
| Markov §6.3.3 (first order) | 1 | 0.003 ms | 300 kHz | `markov_test.h:18-23` |
| MultiMMC §6.3.9 (depth) | 16 | 0.053 ms | 18.8 kHz | `multi_mmc_test.h:4` `D_MMC 16` |
| LZ78Y §6.3.10 (prefix) | 16 | 0.053 ms | 18.8 kHz | `lz78y_test.h:4` `B_len 16` |
| Lag predictor §6.3.8 | 128 | 0.427 ms | 2.34 kHz | `lag_test.h:4` `D_LAG 128U` |
| **MultiMCW §6.3.7 (longest window)** | **4095** | **13.65 ms** | **73.3 Hz** | `multi_mcw_test.h:9` `W[] = {63,255,1023,4095}` |

**These five are read from this repository's source, not inferred** — the
load-bearing claim of Parts 5-7 is that 4095 is the largest window anywhere in
the battery, so it was checked rather than recalled. Two notes from doing so:

- **Markov's reach really is lag 1.** It accumulates only `C_00` and `C_10` over
  `data[i]` → `data[i+1]` (`markov_test.h:18-23`), so it is a first-order chain
  and **cannot represent a lag-2 dependency at all.** The `128.0` in that file is
  not a lag: `H_min = 128.0` is a sentinel for a running minimum and
  `H_min/128.0` (`:105`) normalises the most-likely-128-sequence probability back
  to per-bit. The estimator spans 128 samples but models only adjacent pairs.
- **MultiMCW's smallest window is 63**, so the four windows are 63/255/1023/4095
  and there is no coverage between 4095 and the data length.

### The obvious objection, answered: don't t-tuple and LRS reach further?

**Yes, and it does not rescue the battery.** `t_tuple_test` and `len_LRS_test`
have **no fixed window** — LRS finds the longest repeated substring in the whole
input, which on 1,000,000 samples can be far longer than 4095. So the claim
"nothing in the battery looks past 4095" would be false as stated, and the
reason it does not matter is a difference in *kind*, not in reach:

| estimator family | what it detects | reach |
|---|---|---|
| MultiMCW / Lag / MultiMMC / LZ78Y | **predictability** — a model that forecasts the next symbol | bounded: 4095 max |
| t-tuple / LRS §6.3.5-6.3.6 | **exact repetition** — the same substring occurring twice | unbounded |
| compression §6.3.4 | general redundancy, via bzip2 | unbounded, insensitive |

A 50/60 Hz modulation of a shared comparator threshold does **not** produce
exact repeated substrings. It produces a slowly oscillating *bias* — P(1) drifts
a fraction of a percent above and below 0.5 with a 5000-6000 sample period —
while the sample-to-sample values stay random. There is no repeated substring to
find, because no substring repeats; only its *distribution* shifts. So:

- **LRS and t-tuple are blind to it** because it is not repetition.
- **The predictors could model it** — a bias oscillation is predictable
  structure — **but only within their window**, and the window stops at 4095
  while the period is 5000-6000.
- **Compression would need the bias excursion to be large** before bzip2's
  estimate moves measurably; it is the least sensitive member of the battery.

That is the precise shape of the gap: **the estimator with the right *kind* of
sensitivity has the wrong reach, and the estimators with unbounded reach have
the wrong kind of sensitivity.** Neither half is individually wrong, and nothing
in the standard composes them. This is `SHAPE-07` in `DEFECT-SHAPES.md`.

A long-lag autocorrelation closes it directly, because autocorrelation measures
exactly the quantity that is varying — the mean — at exactly the lags nothing
else examines.

**No time constant in the design exceeds that reach.** VREF's 50 µs is ~15
samples; C8/C9 at 220pF are sub-sample; C6 and C2 filter only high frequencies.
So the blind spot is **not** reached by any RC in the circuit.

**It is reached by external periodicity, and the margin is uncomfortably tight:**

| source | period | verdict |
|---|---:|---|
| USB frame, 1 kHz | 300 samples | within 4095 — visible |
| rectified ripple, 120 Hz | 2500 samples | within 4095 — visible |
| rectified ripple, 100 Hz | 3000 samples | within 4095 — visible |
| **mains fundamental, 60 Hz** | **5000 samples** | **BEYOND 4095 — blind** |
| **mains fundamental, 50 Hz** | **6000 samples** | **BEYOND 4095 — blind** |

> ## ⚠ CORRECTED BY MEASUREMENT — see Part 8
>
> **The two tables above are wrong, and I refuted them myself by running the
> battery instead of reasoning about it a third time.** The error: I assumed a
> window must be **≥** the period to see a periodic effect. For a *slow bias
> drift* the opposite holds — a **short** window tracks it better, because
> W = 63 on a period-5000 oscillation sees a nearly-constant local bias and
> predicts it successfully.
>
> **Measured (Part 8): a period-5000 bias oscillation is DETECTED, strongly.**
> MultiMCW fell 0.998 → 0.835, a drop of 0.163, despite its longest window being
> 4095 < 5000. Compression fell 0.235, Collision 0.128, t-tuple 0.104. There is
> no 73.3 Hz blind spot for bias drift, so **the VREF mechanism this schematic
> read identified is visible to the battery** — which is good news for the
> hardware and relocates the risk.
>
> **The blind spot is real but it is a different thing**, and the bounded-reach
> half of the argument did survive: on a long-lag correlation with *no* local
> bias, every predictor was blind (all drops < 0.004). What makes it invisible in
> the *reported figure* is not reach at all — it is the **minimum-of-ten
> aggregation discarding the one estimator that detected it.** Part 8 has the
> measurement; `DEFECT-SHAPES.md` `SHAPE-07` has the corrected general form.
>
> The schematic read's value is undiminished — it identified a real mechanism and
> the frequency — but the claim that the battery cannot see that mechanism was
> mine, was arithmetic, and was wrong.

## What the schematic establishes, rules out, and cannot settle

**Establishes:** no switching regulator; the analog rail is the FT240X internal
LDO; VCCIO shares that rail with no isolation; VREF is a VCC33/2 divider shared
by both comparators with a 3 kHz corner; K = 1.82 on both channels; the two
channels share one comparator die and interleave into even/odd bits; no design
time constant exceeds 4095 samples.

**Rules out:** an unintended switcher or charge pump as the periodic-modulation
source; raw-5 V operation of the analog section; a long design RC as the
blind-spot mechanism.

**Cannot settle on paper:** resistor tolerances (absent from the BOM); the
FT240X LDO's actual PSRR at mains frequencies; whether ripple reaching VREF is
large enough to move comparator decisions measurably; and the actual layout
coupling between the digital and analog sections, which is a `.brd` question and
a measurement question, not a netlist one.

## Is the signature detectable outside the battery? Yes, and cheaply

This is the check worth building **before** January, not after:

- **Autocorrelation of the raw stream out to ~10⁵ lags.** Covers mains
  fundamental (5000–6000), its harmonics, and slower drift. The battery stops at
  4095, so everything beyond is new information.
- **A power spectrum of the raw bit stream.** A line at 50/60 Hz or at the
  host's switching frequency is a direct observation of the mechanism this
  schematic read predicts, and needs no hardware beyond the units themselves.
- **Cross-spectrum between the two units**, per Part 3's requirement 2. Common
  modulation shows as coherence at the offending frequency, which per-stream
  tests cannot see at all.

None of these are in SP 800-90B, which is the point: the blind spot belongs to
the battery, so only a check outside it can look there.

---

# Part 6 — the host-supply experiment, pre-registered

Free, tests the dominant risk directly, and the netlist in Part 5 predicts a
specific outcome. **Registered in advance so the result cannot be read
selectively.**

## Hypothesis

Host-supply ripple below ~3 kHz reaches VREF (Part 5, Question 2) and modulates
both comparators' thresholds in common mode. If so, measured figures and/or
inter-unit coupling will depend on the host's power source.

## Conditions, in this order

| # | condition |
|---|---|
| A | laptop on **battery** (no mains path at all) |
| B | the **same laptop on mains**, same USB ports, same session |
| C | **powered hub with its own supply**, laptop on battery |

Both units captured **simultaneously** in every condition — that is what makes
the coupling measurable.

## Captures and quantities

- **5 captures per unit per condition**, 1,000,000 samples each, `--raw`, no
  whitening, no `/dev/random`. 2 units × 3 conditions × 5 = **30 captures**.
- Per capture record: the SP 800-90B minimum-of-ten figure, **the full
  per-estimator breakdown**, and the assessing binary's build provenance
  (`XR-04`).
- Per condition record, **per unit, never averaged across units**: the mean and
  sample standard deviation of the 5 figures.
- Per condition also record: **cross-correlation between the two units' streams**
  at lags 0 to 10⁵, and the **peak coherence** between them.

## Decision rule, fixed now

Let `s_w` be the pooled within-condition standard deviation of the per-unit
figures across the 5 repeats.

- **Evidence of host-supply dependence** iff, for either unit, the
  between-condition difference in mean figure exceeds **3 × s_w** *and* exceeds
  an absolute floor of **0.013 bit** — the ±1% resistor-tolerance band from Part
  5, below which a difference is not interpretable regardless of its
  significance.
- **Evidence of host-induced coupling** iff peak inter-unit coherence in
  condition B exceeds condition A's by more than **3 ×** the within-condition
  spread of that statistic. This is the sharper test: independence is what CG
  needs, and coupling is the thing that breaks it.
- **A null result** is `A ≈ B ≈ C` on both measures within those bounds. It is
  evidence that mains ripple does not measurably reach the decision — **not**
  evidence that the units are independent, since a design-shared structure
  present in all three conditions would be invisible to this experiment by
  construction.

Pre-registering the floor at 0.013 bit matters because without it any
sufficiently repeatable experiment eventually clears 3 σ on noise that the
component tolerances already explain.

## Guard shown failing, before the result is trusted

The cross-correlation and coherence code must be **demonstrated detecting a
known coupling** before it is used in anger: inject a synthetic common-mode
sinusoid at 60 Hz-equivalent lag into two otherwise independent captured
streams, at descending amplitude, and record the smallest amplitude it detects.
A test that has never been shown to fire proves nothing — and a coupling
detector that cannot find a coupling you planted is worse than no detector,
because it produces a null result that reads as reassurance.

---

# Part 7 — correction to the cross-check idea

The proposal earlier suggested a different device family could cross-check the
entropy figure and close the estimation-error gap. **Part 3's correction narrows
that, and the narrowing is right: if the blind spot belongs to the estimator
rather than the unit, measuring a different device with the same battery
inherits the same blind spot.**

So the cross-check survives, weaker, and **only via disagreement**:

- Device A carries blind-spot structure, device B does not → A reads high, B
  reads correctly, **they disagree** → informative.
- Both carry it → **they agree and both are wrong** → the agreement is worthless.

Which is Part 4's inversion again, and it generalises: **disagreement is the
informative outcome; agreement is ambiguous.** Recorded as detecting
*design-specific* structure, not estimator blind spots in general.

**And the conclusion that follows, which is the most important item on the Tier 2
list: nothing purchasable closes the estimator blind spot.** No second device, no
third device, no mechanism diversity. Only a check *outside* the battery can look
there — a spectrum, a long-lag autocorrelation, or an estimator family the
standard does not include.

**That is a software item, not a hardware one, it costs nothing but time, it
needs no purchase and no schedule, and it is available now.** On the evidence of
Part 5 — which identified a specific mechanism (VREF on an unisolated rail), a
specific frequency (mains, 5000–6000 samples), and a specific reason the battery
cannot see it (floor 73.3 Hz) — it is plausibly the highest-value thing on the
whole Tier 2 list, ahead of the second unit it would be assessing.

---

# Part 8 — OC-15: the battery measured against known defects

**Parts 5-7 rested on an arithmetic argument about what the estimators can see.
Standing rule: suspect the instrument before the thing measured. So I tested the
instrument, and it refuted my own claim.**

Testing an estimator with synthetic input is the **one** legitimate use of
synthetic data here, and it does not breach *no claim upgrades from synthetic
evidence*: that rule governs claims about an **entropy source**. This is
instrument calibration — a known input is the only way to establish what a
detector detects. **No claim about any Infinite Noise unit is upgraded by any
number below.**

## Method

- Binary: `cpp/ea_non_iid`, built from commit `dd2996f` with the repository's own
  `cpp/Makefile` flags — Apple clang, arm64, `-O2 -ffloat-store`, **`NDEBUG`
  absent so asserts are live.** This is build provenance by construction (known
  commit, known flags), which the canary's own header calls strictly stronger
  than the canary.
- Five streams, 1,000,000 one-bit samples each, from
  `generators/blindspot_streams.py` (seeded; digests printed, rerun confirmed
  byte-identical). **All five are globally unbiased**, so the most-common-value
  estimator cannot separate any of them from a fair coin — every effect lives in
  the correlation.
- Five *additional independent* fair-coin controls to establish the battery's own
  run-to-run spread before attributing any difference to a defect.

## Result 1 — slow bias drift is detected, and my claim was wrong

Per-estimator, `-v`, drop versus control:

| estimator | control | bias T=5000 | bias T=500 | lag-5000 (strong) |
|---|---:|---:|---:|---:|
| MCV | 0.995221 | −0.000 | +0.001 | −0.000 |
| Collision | 0.920578 | **−0.128** | **−0.134** | +0.017 |
| Markov | 0.999225 | −0.028 | −0.027 | −0.000 |
| Compression | 0.847017 | **−0.235** | **−0.143** | +0.003 |
| t-Tuple | 0.934685 | **−0.104** | −0.077 | −0.013 |
| LRS | 0.995382 | −0.020 | −0.052 | **−0.377** |
| MultiMCW | 0.998217 | **−0.163** | **−0.123** | −0.003 |
| Lag | 0.994685 | −0.026 | −0.025 | +0.000 |
| MultiMMC | 0.996185 | −0.054 | −0.053 | −0.003 |
| LZ78Y | 0.996437 | −0.027 | −0.028 | −0.000 |

**A period-5000 bias oscillation is caught hard**, MultiMCW included, with its
longest window at 4095 < 5000. The 73.3 Hz floor does not exist for bias drift.

**And the reach argument survived its half:** against the lag-5000 correlation,
**every predictor was blind** — MultiMCW −0.003, Lag +0.000, MultiMMC −0.003,
LZ78Y −0.000, Markov −0.000 — exactly as the window bounds predict. **LRS caught
it at −0.377**, because that construction copies `x_{i-5000}` and therefore
creates exact repeated substrings. My own "obvious objection" section named that
loophole and the measurement walked straight into it.

## Result 2 — the real blind spot, and it is not about reach

So the genuine gap needs structure that is at once **beyond predictor reach**,
**not local bias**, and **not exact repetition**. Stream E: `x_i = x_{i-5000}`
with probability 0.04, else a fair coin. P(agree) = 0.5203 — a **+40.4 σ**
autocorrelation signal (control: +0.8 σ) with almost no exact repetition.

| estimator | control | **E (40 σ defect)** | drop |
|---|---:|---:|---:|
| MCV | 0.995221 | 0.995187 | −0.0000 |
| Collision | 0.920578 | 0.909693 | −0.0109 |
| Markov | 0.999225 | 0.997835 | −0.0014 |
| **Compression (binding)** | **0.847017** | **0.856713** | **+0.0097** (= +0.23 sd: noise) |
| t-Tuple | 0.934685 | 0.916625 | −0.0181 |
| LRS | 0.995382 | 0.973087 | −0.0223 |
| MultiMCW | 0.998217 | 0.997076 | −0.0011 |
| Lag | 0.994685 | 0.996103 | +0.0014 |
| MultiMMC | 0.996185 | 0.995699 | −0.0005 |
| LZ78Y | 0.996437 | 0.994725 | −0.0017 |

**`H_original` on E was 0.856713, against this control's 0.847017.** The figure
did **not** rise — see the correction below; 0.0097 is inside Compression's own
run-to-run spread, so the honest statement is **no reduction**, not an increase.

Against the battery's own spread, from five independent clean fair-coin streams:

| | Compression (= the binding minimum in all five) |
|---|---:|
| control 0 | 0.847017 |
| control 1 | 0.843936 |
| control 2 | 0.861222 |
| control 3 | 0.855238 |
| control 4 | 0.865774 |
| mean / sd | 0.854637 / **0.009224** |
| **E, 40 σ defect** | **0.856713 — inside [0.843936, 0.865774]** |

**E's figure lands in the middle of the clean range** — +0.23 sd from the clean
mean. The defect is not merely undetected, it is *undetectable from the figure*:
it moves the verdict by less than the battery's own sampling noise.

**Correction to my first reading of this.** I initially wrote that the figure
"went UP". It did not: +0.0097 is 0.23 sd of Compression's clean spread
(sd = 0.0092), so noise explains it entirely and claiming an increase would be
reading a direction into noise — the same error in the opposite direction from
the one the audit exists to catch. **The correct claim is NO REDUCTION:** a 40 σ
defect produced a verdict statistically indistinguishable from clean. That is
the finding, and it does not need the figure to have risen.

## Why — and this is the finding

Not reach. **The minimum-of-ten rule discards the only estimator that saw it.**

- LRS detected E, at −0.0223 — the largest true detection in the table.
- LRS on E reads **0.973087**, which is **0.1164 bit ABOVE** E's binding minimum.
- Compression binds instead, in every control and in E, and its own run-to-run
  sd is **0.0092** — larger than LRS's entire detection.

So a detection only reaches the verdict **if the detecting estimator is the
minimum.** An estimator that reliably sits far above the minimum can detect
anything at all and never change the reported figure. The aggregation throws its
evidence away by construction, and the figure's resolution is set by whichever
estimator is *most pessimistic*, not by whichever is *most sensitive*.

That is strictly worse than a reach bound, because adding estimators does not
fix it: a new, sensitive estimator that is not the minimum contributes nothing.

## What this changes

1. **Part 5's 73.3 Hz blind spot is withdrawn.** Bias drift is detected. The
   schematic's VREF mechanism is visible to the battery — a hardware risk
   relieved.
2. **Part 6 (host-supply experiment) survives and is now better grounded.** If
   mains ripple reaches VREF it produces bias drift, and Result 1 shows the
   battery responds to bias drift strongly (MultiMCW −0.163). The experiment's
   figures are a real instrument for that mechanism. **Keep the pre-registered
   0.013 bit floor** — Result 2 shows the binding estimator's sd is 0.0092, so a
   floor near 0.013 was the right order by luck as much as judgement, and it
   should now be read as *just above* the instrument's own noise.
3. **Part 7's conclusion is confirmed, by measurement rather than argument.** A
   trivial autocorrelation found at **40 σ** what the entire battery missed, and
   the gap is in the *aggregation*, which no purchase can change. The
   outside-the-battery check is not a nice-to-have; it is the only thing in this
   document shown to detect a defect the standard's own figure reports as clean.
4. **New, and it generalises past this hardware:** any consumer treating
   `H_original` as a sensitive defect detector is relying on a statistic whose
   resolution is its most pessimistic estimator's sampling noise. **Record the
   full per-estimator breakdown, not the minimum** — the breakdown contains
   LRS's −0.0223 and the minimum does not. That is `XR-04`'s sibling and it is
   free.

## Status

**VERIFIED as an instrument property**, reproducibly, from this repository's own
source and binary. Claims about hardware: **unchanged and still NOT RUN.** The
0.696 remains uninterpretable pending build provenance. Reproduce with
`generators/blindspot_streams.py`; every digest is in that file's output.

---

# Part 9 — OC-16: the detection budget each estimator wastes

Part 8 showed *that* a detection can fail to reach the verdict. This quantifies
it for all ten estimators, from five independent clean fair-coin streams. Same
binary and provenance as Part 8.

**Headroom = an estimator's clean mean minus the clean binding minimum.** It is
the **detection budget that estimator wastes**: a defect must move it by *more*
than its headroom before the verdict changes at all, however statistically
significant the movement is.

| estimator | clean mean | sd | min | max | **headroom** | binds on clean data? |
|---|---:|---:|---:|---:|---:|---|
| MCV | 0.994603 | 0.000464 | 0.993997 | 0.995221 | **+0.1400** | no |
| Collision | 0.914996 | 0.014876 | 0.892528 | 0.931558 | **+0.0604** | no |
| Markov | 0.997987 | 0.001125 | 0.996413 | 0.999225 | **+0.1433** | no |
| **Compression** | **0.854637** | **0.009224** | 0.843936 | 0.865774 | **0 — binds** | **YES, all 5** |
| t-Tuple | 0.925195 | 0.009810 | 0.914226 | 0.936354 | **+0.0706** | no |
| LRS | 0.993369 | 0.002444 | 0.990152 | 0.996220 | **+0.1387** | no |
| MultiMCW | 0.998065 | 0.000725 | 0.997220 | 0.999171 | **+0.1434** | no |
| Lag | 0.995904 | 0.001415 | 0.994685 | 0.997880 | **+0.1413** | no |
| MultiMMC | 0.996306 | 0.000986 | 0.995043 | 0.997472 | **+0.1417** | no |
| LZ78Y | 0.995533 | 0.000673 | 0.994725 | 0.996437 | **+0.1409** | no |

Mean binding minimum **0.854637**. **Compression binds in all five** clean
streams; no other estimator binds in any of them.

## Decorative for verdict purposes on a near-uniform source

**Nine of the ten cannot affect the verdict on clean-ish data.** Each one's
entire clean range sits above Compression's entire clean range, so on a source
near uniform the reported figure is *Compression's reading and nothing else*.
What each would have to overcome:

| estimator | must move more than | largest movement actually observed (B/C/D/E) | reaches the verdict? |
|---|---:|---:|---|
| MCV | 0.1400 | 0.0006 | never, in any test |
| Markov | 0.1433 | 0.0266 | never |
| Lag | 0.1413 | 0.0275 | never |
| LZ78Y | 0.1409 | 0.0264 | never |
| MultiMMC | 0.1417 | 0.0545 | never |
| Collision | 0.0604 | 0.1224 | exceeded its headroom, but Compression fell further |
| t-Tuple | 0.0706 | 0.0946 | exceeded, same reason |
| MultiMCW | 0.1434 | 0.1629 | exceeded, same reason |
| **LRS** | 0.1387 | **0.3754** | **yes — binds on D** |

**Only LRS was ever the binding estimator on any test stream** (on D, the 600 σ
copy-correlation). Five estimators — MCV, Markov, Lag, LZ78Y, MultiMMC — never
came within a factor of five of their own headroom on any defect tested.

## The finding a reader needs

**The battery has ten estimators and the verdict is determined by one.** The
other nine contribute only if they fall by more than a headroom that **nobody
publishes** — it is not in SP 800-90B, not in the tools' output, and not
recoverable from a reported figure. A reader who sees "min-entropy 0.85" has no
way to know that MCV would have had to drop 0.14 bit to matter.

Three consequences:

1. **The figure's resolution is its most pessimistic estimator's sampling
   noise**, here Compression's sd = 0.0092. Nothing finer than that is
   detectable in the verdict, by any estimator, regardless of significance.
2. **Adding estimators does not help.** A new, exquisitely sensitive estimator
   that is not the minimum contributes nothing. This is why the gap is not
   closable by a better battery and not closable by a purchase.
3. **Record the per-estimator breakdown, not the minimum.** The breakdown
   contains LRS's −0.0223 on E; the minimum does not. This is free — the tools
   already print it under `-v` — and it is the single cheapest mitigation in this
   document. `XR-06`.

**Status: VERIFIED as an instrument property.** Synthetic input, deliberately —
see Part 11. No claim about any hardware.

---

# Part 10 — OC-17: the outside-the-battery check, built and calibrated

`tools/outside-battery-check.cpp`. Self-contained C++11, no dependencies (an
inline radix-2 FFT), so a consumer who did not build the rest of the repo can
still run it. **It is not an entropy estimator and emits no entropy figure.** It
answers one question: does this stream carry structure the battery's aggregation
would discard?

## What it tests, and what sets the bounds

**Autocorrelation over lags 1 .. 100,000** (default), via FFT — all lags from one
transform, O(N log N).

- **Lower bound 1.** Overlapping the battery's own range is free and harmless.
- **Upper bound 100,000**, set by two things. *Statistical power:* each lag uses
  N−k pairs, so the standard error grows with lag; the tool clamps `--max-lag` to
  N/2 so every lag keeps at least half the samples. *Physics:* at the Infinite
  Noise's ~0.3 Mbit/s, 100,000 samples is 0.33 s ≈ **3 Hz**, which covers mains
  (50/60 Hz, lags 6000/5000), its harmonics, USB frame rate (1 kHz), and
  switching-regulator ripple, with room to spare. Drift slower than ~3 Hz is a
  trend rather than a periodicity and wants a different instrument.

**Power spectrum** from the same transform, which localises a periodic mechanism
to a *frequency* — the thing the schematic read was actually looking for.

## Pre-registered thresholds, and the false-positive arithmetic

**Autocorrelation: 5.731 σ.** Bonferroni, family-wise α = 0.001 over 100,000
lags — per-lag two-sided α = 5×10⁻⁹. Bonferroni is the right correction because
sample autocorrelations of a white process are asymptotically independent across
lags; it is mildly conservative. **Testing 100,000 lags at an uncorrected 3 σ
would expect ~270 hits on clean data**, which is why the correction is not
optional.

**Spectrum: 30× mean power, and this one is EMPIRICAL because my analytic model
was wrong.** The Exp(1) periodogram model gives `log(K/α)`. Measured on 25 clean
streams, spectral check isolated:

| threshold | source | clean streams fired |
|---|---|---:|
| 18.5× | analytic, α = 0.01 | **2 / 25 (8 %, nominal 1 %)** |
| 20.8× | analytic, α = 0.001 | 0 / 25 — but clean max was 20.3×, a **2 % margin** |
| **30×** | **empirical** | **0 / 25, margin 1.48×** |

The rejection is of the model's **tail shape**, not one threshold: 2× zero-padding
correlates adjacent bins, so observed clean maxima (13.0 .. 20.3) have a fatter
tail than Exp(1) predicts, and no α can be trusted to deliver its stated rate.
α = 0.001 passes on this set by 2 %, which is not a margin to rely on.

## Calibration set

**25 independent clean streams**, 1,000,000 samples each — 5 from Mersenne
Twister and 20 from a **seeded SHA-256 counter-mode** generator, deliberately
two different algorithms so the calibration does not rest on one RNG's quality.

- Autocorrelation max |z|: **3.90 .. 5.01**, mean 4.31, sd 0.25. **0/25** over
  5.731.
- Spectrum top line: **12.8 .. 20.2**, mean 14.6, sd 1.5. **0/25** over 30×.

> **Corrected 2026-10-15.** The first calibration used `os.urandom` for the 20
> secondary controls and measured max |z| 5.18 and spectrum max 20.3×. Those
> streams **could not be regenerated**, and a seed that does not reproduce is
> not a pin, so they were replaced with the seeded SHA-256 generator and the
> calibration **re-measured**. The numbers moved in the third decimal, the
> false-positive count stayed 0/25, and no conclusion changed. The five Mersenne
> Twister controls kept their original seeds, so the published `OC-16` baseline
> reproduces byte-for-byte. See Part 13.

## Demonstrated: fires on all four defects, silent on all 25 controls

| stream | autocorr | spectrum | verdict |
|---|---|---|---|
| 25 clean controls | max 5.01 σ | max 20.2× | **silent, 0/25** |
| B, bias T=5000 | 79,644 lags over | **8538.7× at 59.938 Hz** | FOUND |
| C, bias T=500 | 81,145 lags over | 9263.3× at 599.957 Hz | FOUND |
| D, strong lag corr | 24 lags over | 44.5× | FOUND |
| **E, 40 σ weak lag corr** | **40.21 σ at lag 5000 = 60.000 Hz** | 15.7× (**silent**) | **FOUND** |

**B's spectrum recovers the mechanism directly**: 8538.7× at 59.938 Hz, from a
stream whose only structure is a period-5000 bias oscillation. If the VREF path
in Part 5 ever modulates a real unit at mains frequency, this is what it looks
like.

**And the two checks are complementary — neither alone suffices.** E reads
40.21 σ on autocorrelation but **15.7× on the spectrum, below the clean maximum
of 20.2×**: the spectrum does not see E at all. Conversely the spectrum names a
frequency, which autocorrelation does not. Run both; this is why the tool does
both by default.

## Shown failing — three ways

*A check never seen to fail proves nothing.*

1. **Weaken the σ threshold past E's signal:** `--sigma 5.73/20/40` all detect;
   **`--sigma 50` MISSES E** (exit 0). The threshold is load-bearing and the
   margin is 7×.
2. **Remove the multiple-comparison correction:** `--no-correction` (3 σ) fires
   on **5 of 5** clean streams, 160 false lag hits on one control against the
   ~270 predicted. The correction is what makes a quiet result mean anything.
3. **Lower the spectral threshold below the clean maximum:** 30× → 0/25;
   **20× → 2/25**; **13× → 24/25**. The ~1.5× margin is doing real work.

## What it does NOT cover — stated so a pass is not read as closure

- **Linear correlation only.** A stream with `x_i = x_{i-k} XOR x_{i-m}` has zero
  autocorrelation at every lag and passes. Nonlinear and higher-order structure
  needs a different instrument; this tool is blind to it by construction.
- **Only the lags tested.** Structure above `--max-lag` is not examined, and a
  pass does not report it as absent.
- **A pass is not an entropy claim** and not a compliance statement. It is the
  absence of one specific kind of evidence.
- **It says nothing about physical soundness** — a well-shielded broken source
  can be spectrally clean.
- The calibration is for **1,000,000 one-bit samples**. Other lengths or symbol
  widths need recalibrating; the thresholds are not universal constants.

**Status: BUILT and VERIFIED against known input. NOT RUN on hardware** — no
physical unit exists to run it on, and the 0.696 stays uninterpretable.

---

# Part 11 — the synthetic-data distinction, stated for the taxonomy

**This exists so the next reader of the standing constraint does not delete
Parts 8-10 for violating it.**

The standing rule is **"no claim upgrades from synthetic evidence."** Parts 8-10
rest entirely on synthetic streams. That is not a violation, and the reason is a
distinction the rule does not spell out:

| | claim about a **SOURCE** | claim about an **INSTRUMENT** |
|---|---|---|
| example | "this unit delivers 0.87 bit/bit" | "this estimator detects a 40 σ lag correlation" |
| synthetic data | **cannot establish it.** Nothing about generated bits tells you what a physical device does. | **is the correct and only way to establish it.** You cannot characterise a detector without input whose structure you already know. |
| real data | required | insufficient alone — you do not know what is in it, so you cannot tell a miss from a clean sample |

**Measuring a detector requires known input, and known input is synthetic by
definition.** A physical capture cannot calibrate a detector, because its true
structure is exactly what is unknown. So the rule's force is undiminished and its
scope is source claims:

- **Nothing in Parts 8-11 upgrades any claim about any Infinite Noise unit**,
  about the 0.696, or about hardware independence. Every physical item stays
  **NOT RUN**.
- **What Parts 8-10 do establish** is a property of `cpp/ea_non_iid` as built
  from this repository at commit `dd2996f`, and a calibration of
  `tools/outside-battery-check`. Both are instrument claims, both reproducible
  from `generators/blindspot_streams.py`, both independent of any hardware.

The same distinction already governs `tools/build-provenance-canary.sh`, which
classifies a binary using a generated input. Nobody objected to that, for the
same reason.

**The rule that does apply here, and was followed:** *suspect the instrument
before the thing measured.* Part 5 reasoned about the instrument and got it
wrong; Part 8 measured it and found the real mechanism. Instrument calibration is
how that rule gets obeyed rather than merely cited.

---

# Part 12 — OC-18: the case both tools miss. REACHABLE, and confirmed.

Put `OC-16`'s headroom table next to `OC-17`'s limits section and an uncovered
case falls out: a structure that trips only the **decorative** predictors, by
**less than their headroom**, is invisible to the battery's verdict; and if it
also has no linear correlation, it is invisible to the outside check. **Neither
tool sees it and the published figure is unchanged.**

**It is reachable. Here it is.**

## Construction, and the detour that found the mechanism

`x_i = x_{i-a} XOR x_{i-b}` with probability p, else a fair coin. In ±1 terms
XOR is multiplication, so `E[x_i x_{i-d}] = p·E[x_{i-a} x_{i-b} x_{i-d}]`: the
pairwise correlation is a *triple* product, which vanishes unless the three
indices close through the recurrence.

**First attempt, taps (1,2), failed instructively.** I predicted zero linear
correlation and the outside check fired at **50 σ**. Reason: **a+b = 3 is itself
a tap**, so `x_{i-1}x_{i-2}x_{i-3}` closes and a strong linear correlation
appears at lag 3. Measured across tap choices at p = 0.3:

| taps | max \|z\|, lags 1..400 | |
|---|---:|---|
| **(1,2)** | **+50.21 at lag 3** | fires — a+b is a tap |
| (1,3) | −3.51 | silent |
| (2,5) | +3.28 | silent |
| (3,7) | +2.98 | silent |
| (7,16) | −3.17 | silent |
| (11,16) | −2.82 | silent |

**Tap choice decides linear visibility.** (1,2) is the pathological case, kept in
the corpus as `F_xor30` precisely because it is the counterexample.

## The confirmed case: taps (1,3), p = 2 %

`G_xor13_02`. Order 3, so comfortably inside MultiMMC's depth-16 reach; `a+b = 4`
is not a tap, so no linear correlation at any lag.

| | measurement | against |
|---|---:|---|
| **`H_original`** | **0.860003** | clean range **[0.843936, 0.865774]** — **INSIDE**, +0.6 sd |
| **Compression** (binds) | **+0.0054** | 0.3 × its 2 sd — **noise** |
| **MultiMMC** | **−0.0266** | **9.0 × its 3 sd — strongly real** |
| MultiMMC headroom | 0.1417 | the drop is **5× too small to bind** |
| **outside check, autocorr** | **4.30 σ** | threshold 5.731 — **silent** |
| **outside check, spectrum** | **16.5×** | threshold 30× — **silent** |

**Both tools report clean. MultiMMC shows a 9 σ-equivalent drop. The only place
that drop exists is the per-estimator breakdown.**

Tuning confirms the window rather than a lucky point. The drop scales with p
while Compression tracks MultiMMC at ≈0.76×, so Compression's 20× larger noise
floor opens a band:

| p | `H_original` | inside clean range? | MultiMMC Δ (× its 3 sd) | Compression Δ (× its 2 sd) | outside check |
|---:|---:|---|---:|---:|---|
| **1 %** | 0.865096 | **YES** | −0.0137 (4.6×) | +0.0105 (0.6×) | **silent** |
| **2 %** | 0.860003 | **YES** | −0.0266 (9.0×) | +0.0054 (0.3×) | **silent** |
| 3 % | 0.824439 | no | −0.0411 (13.9×) | −0.0302 (1.6×) | silent |
| 5 % | 0.833548 | no | −0.0699 (23.6×) | −0.0211 (1.1×) | silent |
| 10 % | 0.749411 | no | −0.1387 (46.9×) | −0.1052 (5.7×) | silent |
| 30 % | — | no | — | — | fires (7.40 σ) |

The band is **p ≈ 1–2 %**, bounded below by MultiMMC's noise and above by
Compression's. It is narrow but it is real, and nothing warns you when a device
sits in it.

## What follows

1. **The per-estimator breakdown is not merely useful, it is NECESSARY.** `XR-06`
   previously recommended storing it. This case makes it the *only* place the
   defect is visible: the scalar is clean and the outside check is clean.
2. **And storing it is not enough — it must be COMPARED against a baseline.** A
   reading of `MultiMMC = 0.9697` is unremarkable in isolation. It is only
   meaningful as **−0.0266 against 0.996306 ± 0.000986**. A harness that logs the
   breakdown without a baseline has the evidence and cannot read it.
3. **The combined blind spot is bounded, usefully.** Everything that reaches it
   must be simultaneously below Compression's noise, below every predictor's
   headroom, and linearly uncorrelated. That is a narrow set — a 40 σ defect
   (`E`) escapes the battery but not the outside check; a 2 % third-order
   structure escapes both but costs only ~0.027 bit of a non-binding estimator.
   **Neither case is catastrophic; both are undetectable in the published
   figure**, which is the point.

## Are the clean baselines stable enough to serve? Partly — and NOT per device.

Asked directly, because the recommendation in point 2 depends on it.

**Stable enough as a method.** Over five independent clean streams the predictor
baselines are extremely tight — MultiMMC sd **0.000986**, MCV 0.000464, MultiMCW
0.000725, LZ78Y 0.000673 — so a 0.027 bit drop is 27 sd and trivially
detectable. The power is there.

**But the fair-coin baseline is the WRONG baseline for a real device, for three
reasons:**

1. **A real source is not at 1.0 bit/bit.** The Infinite Noise's design figure is
   ~0.864 and its measured figure ~0.696. At that level the estimators stand in
   different relationships to each other — most obviously, **Compression may no
   longer be the binding estimator**, and if it is not, the entire headroom table
   is recomputed and `OC-16`'s numbers do not transfer. The regression pins this
   assumption so a change is caught rather than assumed away.
2. **The noise floors are not universal.** They were measured at 1,000,000
   samples and 1-bit symbols. Different lengths and symbol widths give different
   estimator bias and spread; Compression's sd (0.0092) is 10–20× the
   predictors', so the band in the table above is a function of the
   configuration, not a constant.
3. **The quantity of interest is CHANGE, which needs that device's own history.**
   The useful comparison is this unit now against this unit when believed
   healthy — a drift detector.

**So: per-device baselines, established from captures whose build provenance is
known (`XR-04`), with the fair-coin baselines retained only as the method's
noise-floor reference.** And a per-device baseline inherits the standing rule:
it is a claim about a source, so it must come from that source's real captures,
never from synthetic input.

---

# Part 13 — OC-19: the regression, and shown failing

`cpp/selftest/regression-outside-battery.sh`. Picked up automatically by
`run-all-checks.sh` (it globs `regression-*.sh`; master has no hand-maintained
count to break). **Fast mode runs in ~3 s**; `OUTSIDE_BATTERY_FULL=1` adds all
25 clean streams and the `ea_non_iid` binding check.

**The corpus is reproducible, which it was not before.** The original
calibration drew 20 of its 25 controls from `os.urandom`. Those cannot be
regenerated, and **a seed that does not reproduce is not a pin**, so they were
replaced with a seeded SHA-256 counter-mode generator — still a second,
genuinely different algorithm from Mersenne Twister — and the calibration was
**re-measured**:

| | published (5 MT + 20 urandom) | re-measured (5 MT + 20 SHA-256) |
|---|---:|---:|
| autocorr max \|z\| | 5.18 | **5.01** |
| spectrum max | 20.3× | **20.2×** |
| false positives | 0/25 | **0/25** |

Third-decimal movement; **no conclusion changed.** The five Mersenne Twister
controls kept their original seeds, so **the published `OC-16` baseline
reproduces byte-for-byte** — verified: the full run returns Compression =
0.847017, 0.843936, 0.861222, 0.855238, 0.865774, exactly the published figures.

**It pins outcomes, not constants**, so a change in the FFT or the correlation
code fails it even with every threshold untouched. Digest mismatch is a
**failure**, not a warning.

## Shown failing — and the coverage division came out cleaner than expected

| perturbation | result | named failure |
|---|---|---|
| bit-reversal permutation broken | **FAIL** | *B spectral peak: got 8538.9x, want 8538.7x* → "the FFT, the mean-centering, or the power normalisation changed" |
| twiddle error 1e-3 | **FAIL** | same check, 8534.1x |
| `sqrt(N)` for `sqrt(N−k)` | **FAIL** | *E: got 40.31 σ, want 40.21* → "the correlation accumulator or the z normalisation changed" |
| spectral threshold 30 → 13 | **FAIL (2)** | 5/5 clean false positives **and** the OC-18 coverage check |
| twiddle error **1e-5 or smaller** | **PASS — NOT CAUGHT** | a real coverage limit, recorded |

**Two things measurement corrected about my assumptions.** First, **E's sigma is
insensitive to every FFT perturbation tried** — because `r = c[k]/c[0]` is a
ratio and the errors cancel. So E pins the *accumulator*, and **B pins the FFT**;
they are not redundant. Second, a twiddle perturbation at 1e-5 or below changes
no pinned outcome and is **not caught**. That magnitude is far below what matters
for these statistics, but it is a limit and it is stated rather than implied.

**And one check exists to catch a false negative, not a false positive:**
`G_xor13_02` must stay **silent**. It is invisible to this tool by construction,
so a future version that starts firing on it has genuinely changed coverage, and
`OC-18` and `XR-06` must be re-documented rather than the change silently
accepted. **A check that fires on everything pins nothing.**
