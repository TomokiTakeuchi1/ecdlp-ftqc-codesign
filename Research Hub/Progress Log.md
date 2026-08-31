---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - progress
updated: 2026-08-31
---

# Research Progress Log

[[Research Hub/Home|← Home]] · [[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]]

This page explains the research in plain language. Evidence, assumptions, and exact counts live in the linked canonical records.

## 2026-08-31 — Clean OOP-QCLA and direct-CCZ capability gate

**Status:** In review (`T-20260831-002`, `RV-20260831-002`)

What changed:

- Generated a deterministic clean out-of-place modulo-`2^n` QCLA trace and
  replayed every computational-basis input through width 6.
- Audited the pinned direct-CCZ, high-rate injection, and factory sources into
  one machine-readable capability record.
- Added a typed direct-CCZ adapter that refuses to emit events until the exact
  correction map is source-qualified; high-rate scheduling has a separate,
  stricter field gate.

What we learned:

- Width 256 has 1,229 Toffolis, 766 CNOTs, 20 source layers, 240 clean prefix
  scratch values, and 1,008 fully resident source values.
- A single-injection six-PPM skeleton is literature-supported, but the exact
  outcome-to-CZ/Pauli map is still `OPEN` in the executable schema.
- Cain's ten-CCZ/120-cycle factory observation does not close delivery,
  buffering, routing, decoder, reaction, ports, or storage. The current
  high-rate schedule is therefore correctly absent.

> [!warning] Interpretation
> The generated source-layer CCZ-candidate demand is `NUMERICAL`; the native
> capability conclusion is `OPEN`. No QEC-cycle, wall-clock, physical-qubit,
> or success-probability result was produced.

Canonical record: [[docs/DIRECT_CCZ_CAPABILITY_AND_OOP_QCLA_CONTRACT|Capability/OOP-QCLA contract]] · [[context/RESULT_LEDGER#R-20260831-002|OOP result]] · [[context/RESULT_LEDGER#R-20260831-003|Capability gap]]

## 2026-08-31 — Direct-CCZ high-rate QCLA research plan

**Status:** Reviewed and approved (`T-20260831-001`, `RV-20260831-001`)

Human-directed planning record, not an implementation. It selects clean out-of-place modulo-\(2^{256}\) QCLA as the first workload for studying direct \(|CCZ\rangle\) injection (as opposed to the already-reviewed seven-\(T\) route), and requires a pinned native injection/reaction/factory/routing/failure contract before any runtime is reported.

What we learned:

- At \(n=256\), the isolated carry-status prefix network needs 974 CCXs; the clean out-of-place adder needs 1,229 (974 plus 255 initial-generate gates); the already-reviewed in-place adder needs 2,458. All three numbers were independently re-derived from the Draper formulas during review and matched exactly.
- Direct CCZ injection capability and parallel high-rate batching beyond the demonstrated ten-XX case remain `OPEN` -- no runtime, physical-qubit, or success-probability claim is made.

Canonical record: [[docs/HIGH_RATE_QCLA_DIRECT_CCZ_RESEARCH_CYCLE|Direct-CCZ research cycle]] · [[context/DECISIONS#D-0014|Decision D-0014]]

## 2026-08-26 — Width-256 QCLA memory and high-rate schedule

**Status:** Reviewed and approved (`T-20260825-002`, `RV-20260825-002`)

What changed:

- Split QCLA clean workspace into reviewed reuse epochs while keeping `A/B`
  inputs and outputs as strict memory values.
- Added deterministic farthest-next-use placement and an independent replay
  that rejects free copies, use before origin, invalid returns, or occupancy
  above the 60-slot J300 budget.
- Compared one-scratch serial, ten-scratch serial, and ten-scratch high-rate
  schedules and emitted the complete shifted width-256 T-demand timeline.

What we learned:

- One-scratch serial uses 46,355 loads/stores; ten-scratch serial uses 53,514,
  exposing the traffic cost of shrinking source payload from 59 to 50 slots.
- Ten-scratch high-rate selects 1,576 exact-ten-XX batches. Its provisional
  schedule is 2,420,527 rounds, 169,260 (6.54%) below one-scratch serial even
  though it performs 7,433 more reloads.
- All three policies conserve total T-state demand 17,206, but the emitted
  timeline assumes ideal supply and contains no factory service or stalls.

> [!warning] Interpretation
> Placement/action invariants are exact under the contract, while the generated
> counts are `NUMERICAL` and the transfer/native/clean-lifecycle timing is
> `CHECK`. This fixed order is neither optimal nor a lower bound, and it excludes
> routing, decoding, failure, factory buffering, and wall-clock conversion.

Canonical record: [[context/RESULT_LEDGER#R-20260825-002|Placement result]] · [[context/RESULT_LEDGER#R-20260825-003|Timing sensitivity]] · [[docs/QCLA_MEMORY_IO_CONTRACT|QCLA memory-I/O contract]]

## 2026-08-25 — QCLA adaptive-PBC and resident high-rate boundary

**Status:** Reviewed and approved (`T-20260825-001`, `RV-20260825-001`)

What changed:

- Pinned Selinger circuit (1) as an exact, ancilla-free seven-T-family CCX and
  independently reconstructed its complete three-qubit channel.
- Preserved every QCLA gate's layer, prefix stage, direction, and exact CCX
  column while re-deriving dependencies from expanded wire use.
- Reused the reviewed adaptive-PBC compiler and J300 scheduler, adding only a
  deterministic X-frame expression and a fail-closed resident-capacity gate.

What we learned:

- The CCX reconstruction agrees with ideal Toffoli to
  `2.220446049250313e-16` maximum absolute error (`NUMERICAL`).
- Width 14 fits with ten scratch slots (58/60) and exposes nine ten-XX batches;
  its `CHECK` schedule changes from 94,161 to 93,108 provisional rounds.
- Width 256 expands to 40,857 primitives and 17,206 T-state demands, but needs
  1,008 resident slots with one scratch and is rejected before scheduling.

> [!warning] Interpretation
> The seven-T path is a comparison baseline, not a claim over direct CCZ.
> Width-256 memory traffic is handled by the following cycle; routing, factory
> service, decoding, failure, and wall-clock time remain open.

Canonical record: [[context/RESULT_LEDGER#R-20260825-001|Result R-20260825-001]] · [[docs/QCLA_PBC_LOWERING_CONTRACT|QCLA PBC contract]]

## 2026-08-24 — Source-pinned carry-lookahead DAG

**Status:** Reviewed and approved (`T-20260824-003`, `RV-20260824-003`)

What changed:

- Audited the exact in-place, modulo-`2^n`, no-carry-in variant directly from
  Draper et al. and reconstructed its ten reversible steps.
- Preserved the `P/G/C/P^-1` prefix rounds and their bounded-fan-out overlaps,
  while deriving DAG edges from actual wire use rather than source-list order.
- Added explicit carry/prefix-ancilla lifetimes, including two scratch-reuse
  epochs, and an independent X/CNOT/Toffoli basis replay.
- Generated a fail-closed, deterministic width-256 structure and layerwise
  Toffoli-demand artifact.

What we learned:

- All 5,456 basis-input pairs across widths 2--6 pass with `A` preserved,
  `B=A+B mod 2^n`, and every ancilla cleaned.
- Width 256 uses 2,458 Toffolis, 1,019 CNOTs, 510 NOTs, and 495 source
  ancillas. Its source schedule and dependency critical path are both 40.
- Peak demand is 255 Toffolis in one source layer, making burst service and
  processor capacity central questions for the next lowering cycle.

> [!warning] Interpretation
> The 40 layers are not QEC cycles, and 495 logical circuit ancillas are not a
> physical-qubit total. No high-rate-surgery legality, memory traffic, factory
> supply, routing, decoding, or failure budget is included yet.

Canonical record: [[context/RESULT_LEDGER#R-20260824-004|Result R-20260824-004]] · [[docs/QCLA_DAG_CONTRACT|QCLA DAG contract]]

## 2026-08-24 — Bell-bridge teleportation ripple adder

**Status:** Reviewed and approved (`T-20260824-001`, `RV-20260824-001`)

What changed:

- Pinned Xu et al. Figure 6 and the Active Volume bridge/adder figures by PDF
  hash, then represented the carry links as acyclic prepare, use, Bell-measure,
  rebind, and reaction events.
- Kept Bell carry carriers separate from memory load/store ownership and added
  an independent lifecycle replay that rejects premature use or rebind.
- Added exhaustive width-2--4 classical-basis addition checks and a branchwise
  arbitrary-state check for the generic Bell bridge.
- Added a normalized lane sweep with optional exact-ten-disjoint-`XX` batches,
  strict rejection of unresolved timing, and time-stamped resource-state
  demand.

What we learned:

- Width 32 changes from 64 to 37 normalized steps on one Bell-measurement lane
  when three ten-`XX` batches are admitted.
- With two or more Bell-measurement lanes, both policies take 34 steps, so the
  reaction/dependency chain becomes the bottleneck in this model.
- The width-256 structural trace has 255 bridges, 1,532 events, and a peak of
  765 provisional bridge carriers; this is not a physical-qubit count.

> [!warning] Interpretation
> The complete Xu Figure-6 phase channel has not been independently
> reconstructed. All finite times are `CHECK` normalized steps, not HGP/J300
> cycles or wall-clock time, and ideal supply does not model factory stalls.

Canonical record: [[context/RESULT_LEDGER#R-20260824-001|Result R-20260824-001]] · [[context/RESULT_LEDGER#R-20260824-002|Result R-20260824-002]] · [[docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT|Bell-bridge contract]]

## 2026-08-23 — Memory–processor I/O overlay

**Status:** Reviewed and approved (`T-20260823-001`, `RV-20260823-001`)

What changed:

- Ported the reviewed `runtime-metadata-benchmark` memory-I/O semantics (value origin, fixed-order Belady retention, maximal-prefix partitioning, and independent replay) as a source-pinned overlay on the existing Gidney DAG, without changing the DAG schema itself.
- Connected the overlay to the reviewed adaptive-PBC event order: memory transfers are scheduled around a fixed compute order rather than jointly optimized with it.
- Added an independent replay engine that recomputes every load/store decision from scratch and rejects duplicate loads, stores of non-resident values, or any leftover processor occupancy at the end.

What we learned:

- All admitted legacy width-2--4 exact partition reference cells reproduce exactly (e.g. width 2 needs 4 loads/4 stores at generous capacity, or 6/6 at tighter capacity).
- Under a one-lane, one-round-per-transfer sensitivity profile with no prefetch, the reviewed width-32 J300 schedule grows from 31,176 to 31,376 rounds, using 100 loads and 100 stores.
- Zero-duration transfers preserve every reviewed compute event's start and end exactly, confirming the overlay does not silently change the already-approved schedule when I/O is idealized away.

> [!warning] Interpretation
> Memory-transfer duration and the fixed-order/no-prefetch policy are `CHECK` sensitivity choices, not literature-backed executable architecture. The 100-load/100-store width-32 figure is a policy/order observation, not a placement lower bound.

Canonical record: [[context/RESULT_LEDGER#R-20260823-001|Result R-20260823-001]] · [[context/RESULT_LEDGER#R-20260823-002|Result R-20260823-002]] · [[docs/MEMORY_IO_EXECUTION_CONTRACT|Memory I/O contract]]

## 2026-08-15 — J300 adaptive-PBC scheduling

**Status:** Reviewed and approved (`T-20260815-005`, `RV-20260815-007`)

What changed:

- Connected the reviewed adaptive Pauli trace to explicit J300 operation-zone, scratch-slot, carrier, and classical-reaction resources.
- Separated source-supported operation size from source-supported operation time.
- Made strict mode reject every unresolved time or space entry instead of silently using a placeholder.
- Tested the exact-ten-disjoint-XX high-rate rule with one and ten compiler scratch slots.

What we learned:

- Gidney widths 2, 4, 16, and 32 expose zero eligible ten-XX batches under the current trace and greedy resource rules.
- A synthetic ten-independent-CNOT trace does produce one batch, changing the sensitivity schedule from 550 to 433 rounds (`NUMERICAL`).
- The width-32 sensitivity schedule is 31,176 syndrome rounds, but unresolved J300 timings make this `CHECK`, not an executable runtime.
- The 2,074 physical-qubit figure is only the known J300-plus-full-extractor component peak; it excludes several unresolved components.

Canonical record: [[context/RESULT_LEDGER#R-20260815-004|Result R-20260815-004]] · [[docs/J300_PBC_SCHEDULING_CONTRACT|J300 scheduling contract]]

## 2026-08-15 — Adaptive PBC/CQLU lowering

**Status:** Reviewed and approved (`T-20260815-004`, `RV-20260815-006`)

What changed:

- Replaced placeholder CNOT/H/S/T names with explicit state preparations, Pauli measurements, classical dependencies, and Pauli-frame updates.
- Kept arithmetic outputs quantum rather than applying a final-classical-output PBC theorem outside its contract.
- Checked every nonzero branch of the CNOT, H, S, T, and T-dagger gadgets on fixed and seeded small states.

What we learned:

- The maximum channel-check error was below `1e-15` (`NUMERICAL`).
- The compiler needs one reusable scratch logical slot in a serialized operation zone.
- Width 58 fits the J300 60-slot count exactly; width 59 now requires 61 slots.
- Strict runtime is still blocked by state preparation, Z/ZZ/ZX durations, reaction time, conditional CZ, and adaptive scheduling.

Canonical record: [[context/RESULT_LEDGER#R-20260815-003|Result R-20260815-003]] · [[docs/PBC_CQLU_LOWERING_CONTRACT|PBC/CQLU contract]]

## 2026-08-15 — Obsidian Research Hub

**Status:** Reviewed and approved (`T-20260815-003`, `RV-20260815-005`)

- Added a plugin-free visual entry point for the project.
- Separated reviewed work, work under review, human decisions, and provisional `CHECK` results.
- Linked the human-readable views directly to the canonical task, evidence, review, and technical records.

## 2026-08-15 — First Mitten scheduling cycle

**Status:** Reviewed and approved (`T-20260815-002`, `RV-20260815-004`)

What changed:

- Expanded the Gidney temporary logical AND into a phase-exact Clifford+T trace.
- Encoded a finite-size Mitten processor configuration with parameters `n=300`, `k=60`, and `d=14`.
- Added deterministic greedy scheduling and an explicit strict/provisional boundary.
- Limited high-rate surgery to the directly supported batch of ten disjoint XX measurements.

What we learned:

- The direct Gidney erase operations are single-X measurements, so the current high-rate ten-XX rule has no hits.
- Width 59 fills all 60 source-residency slots; width 60 is rejected at source occupancy 61.
- The eventual executable boundary may be lower because the future PBC compiler can require additional logical ancillas.

> [!warning] Interpretation
> The 15,270-round width-59 result is a `CHECK` sensitivity result under placeholder operation times, not a verified physical runtime.

Canonical record: [[context/RESULT_LEDGER#R-20260815-002|Result R-20260815-002]] · [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Lowering contract]]

## 2026-08-15 — QEC-neutral Gidney DAG

**Status:** Reviewed and approved (`T-20260815-001`, `RV-20260815-003`)

What changed:

- Connected the pinned, independently verified Gidney implementation through a versioned read-only interface.
- Generated a causal DAG without baking in a QEC architecture.
- Represented X-basis erasure measurement and conditional Clifford correction as separate nodes connected by a classical dependency.
- Checked exact small-width fixtures and the width-256 circuit structure.

Why it matters:

The scheduler can now distinguish mathematical circuit parallelism from parallelism that an actual code and processor can execute.

Canonical record: [[context/RESULT_LEDGER#R-20260815-001|Result R-20260815-001]] · [[docs/GIDNEY_DAG_CONTRACT|DAG contract]]

## 2026-08-11 to 2026-08-15 — Literature and baseline preparation

**Status:** Reviewed and approved (`T-20260811-001`, `T-20260811-002`)

- Indexed 14 verified primary-source PDFs with local metadata and reading notes.
- Compared candidate ECDLP-256 circuits and recorded mismatched count conventions and unresolved semantic checks.
- Recommended Schrottenloher 2026 as the first source baseline and Luo et al. v2 as a dynamic-circuit contrast, pending the human-owned final selection.

Canonical record: [[docs/CANONICAL_CIRCUIT_DECISION|Circuit decision support]] · [[literature/papers/INDEX|Paper index]]
