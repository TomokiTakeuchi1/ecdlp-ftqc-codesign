---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - decisions
updated: 2026-08-15
---

# Decisions and Blockers

[[Research Hub/Home|← Home]] · [[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Progress Log|Progress Log]]

## One decision needed from the researcher

> [!question] Select the canonical full ECDLP-256 circuit (`T-BOOT-001`)
> **Recommended starting contract:** Schrottenloher 2026 as the primary source baseline, with Luo et al. v2 as a dynamic/low-space contrast.  
> **Alternative:** require exact arithmetic first and promote Luo v2 only after resolving its exceptional-point and count-contract checks.  
> Record the choice in [[docs/CANONICAL_CIRCUIT_DECISION|Canonical Circuit Decision]].

Why this blocks progress: controlled point-addition counts, success semantics, exceptional points, measurements, and uncomputation all propagate into the Full-Shor workload.

## Technical blockers

| Priority | Blocker | Why it matters | Next evidence-producing action |
|---:|---|---|---|
| 0 | Phase-exact PBC/CQLU lowering is missing | Provisional CNOT/H/S/T times cannot establish an executable Mitten runtime. | Select one explicit compilation and record Pauli supports, ancillas, adaptive measurements, and frame reactions. |
| 1 | Processor capacity excludes compiler ancillas | Width 59 currently saturates all 60 source slots. | Recompute occupancy after strict lowering. |
| 1 | Memory–Processor I/O is absent | A small processor may spend more time moving states than computing. | Implement load/store, bridge occupancy, and communication resources. |
| 1 | Parallel-surgery legality is narrow | Circuit parallelism is not automatically executable high-rate surgery. | Generate exact Pauli supports and conflict/resource constraints. |

## Open research questions

- When should an automorphism or (fold-)transversal gate be executed instead of tracking a Clifford frame?
- Is circuit-level-noise simulation of a high-rate factory feasible, or is validated extrapolation required?
- Should cat-based computation be included as an alternative logical processor?
- Can LP-code surgery achieve useful amortized constant time at non-asymptotic sizes?
- Which canonical resource state should the project optimize: T, CCZ, or a mixed supply?

Canonical list: [[context/OPEN_QUESTIONS|Open Questions]]

## Decision hygiene

Use the project evidence labels consistently:

- `PROVED`: deductive result under stated assumptions.
- `NUMERICAL`: computed result with reproducibility metadata.
- `LITERATURE`: supported by a cited source.
- `CHECK`: plausible but still requires verification.

A conditional claim should use one of the allowed evidence labels and state its unresolved condition explicitly.

Do not promote a provisional schedule to a wall-clock or total-qubit result merely because it is numerically precise.
