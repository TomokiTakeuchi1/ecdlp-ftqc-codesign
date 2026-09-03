---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - decisions
updated: 2026-09-03
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
| 0 | Width-256 logical compatibility is reviewed; native execution is still absent | The reviewed `T-20260903-001` (`RV-20260903-001`) proves 34/68 OOP/IP unitless candidate levels by frame-generator closure without materializing 27,184,251/108,744,378 global pairs, and matches the causal lower bounds. The proof is only for the logical same-axis/no-Y/causality/resource screen. It supplies no physical support, routing, duration, capacity, decoder/reaction, factory/buffer, or failure contract. | Implement one coherent native mapper/backend before assigning surgery rounds, runtime, or physical resources; no task ID is claimed for this yet. |
| 0 | Several PBC native durations remain unresolved | Adaptive resource scheduling now exists, but state preparation, Z/ZZ/ZX/full-extractor time, reaction, and conditional-CZ costs remain `CHECK`. | Pin or validate those J300 contracts; strict mode already rejects placeholders. |
| 1 | Factory service is absent from QCLA demand | The in-review width-256 overlay conserves 17,206 time-stamped T demands, but assumes ideal no-stall supply; average rate cannot establish burst feasibility. | Add explicit factory output, buffer, backlog, routing, and stall events to the emitted demand timeline. |
| 1 | QCLA memory/high-rate timing remains provisional | Width 256 now fits an independently replayed 60-slot fixed order and exposes 1,576 ten-XX batches, but transfer/native/clean-lifecycle times remain `CHECK` and the order is not optimal. | Cross-review the ownership/capacity result, then pin timing/routing contracts and compare placement orders. |
| 1 | Memory and Bell-bridge schedules are separate | Memory I/O and carry teleportation now have distinct replayable contracts, but their shared occupancy, routing, and timing have not been jointly scheduled. | Add an explicit architecture adapter only after finite bridge timing and routing evidence are pinned. |
| 1 | Parallel-surgery legality is narrow | Exact-ten disjoint-XX readiness, scratch, carrier, and operation-zone constraints are implemented, but only this source-supported family is enabled. | Audit other source-supported families before expanding the native high-rate gate set. |
| 1 | AutoCCZ adapter lacks complete finite service | The reviewed `T-20260901-001` (`RV-20260901-001`) identifies one source-native surface-code factory/fixup/consumer adapter, but complete service has nine missing fields and one `d1=15,d2=31` output-error value incompatible with selected `d1=17,d2=27`. | Close same-distance output/transport/consumer error, decoder/reaction, finite output buffer/storage, processor capacity, and the integrated failure budget. |

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
