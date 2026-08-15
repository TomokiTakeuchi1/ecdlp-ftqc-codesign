---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - progress
updated: 2026-08-15
---

# Research Progress Log

[[Research Hub/Home|← Home]] · [[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]]

This page explains the research in plain language. Evidence, assumptions, and exact counts live in the linked canonical records.

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
