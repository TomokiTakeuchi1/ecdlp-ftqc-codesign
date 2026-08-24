---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - progress
updated: 2026-08-24
---

# Research Progress Log

[[Research Hub/Home|← Home]] · [[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]]

This page explains the research in plain language. Evidence, assumptions, and exact counts live in the linked canonical records.

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
