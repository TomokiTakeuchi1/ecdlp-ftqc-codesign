---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - decisions
updated: 2026-09-07
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
| 0 | Joint-CCX semantics pass at width 5, but the commutation-aware schedule is not yet built | `T-20260906-002` (`RV-20260907-001` `APPROVED`, 2026-09-07) exactly classifies 36/9 commuting/noncommuting source pairs, validates the 4/3/2/1 unitary groups, and validates full-channel measured cleanup while retaining its six-value outcome-frame support. The 8/6 levels are `CHECK` envelopes and cannot replace the reviewed 12-level baseline yet. | Run `T-20260906-003` (unassigned) across widths 2--8 with every noncommuting edge, Clifford barrier, reaction dependency, and lifetime retained. |
| 0 | H/CNOT logical policy is separated from native realization, but no code-side choice is admitted | `T-20260905-001` proposes frame-conjugated H plus bare CNOT; `RV-20260905-001` is `APPROVED` (Claude, 2026-09-06) after independently confirming the H/Y witness, CNOT closure, width-256 layers, RASCqL citations, and codex's H-teleport citation fix (H is self-derived `NUMERICAL` with an exact four-branch channel check, independently re-derived twice; Xu Figure 11(c) remains only on measurement CNOT). H-SWAP/H teleportation directly implements bare H and can break the Z-only invariant without frame clearing or an H-safe proof; CNOT is axis-safe but addressability, support, routing, and relabel debt remain. The 54/106--111/216 figures are logical-layer envelopes only. | Test either the 3/4 CNOT-layer matrices against a concrete automorphism/SIMD ISA or the 34/68 H masks against H-SWAP packing / whole-event co-design. |
| 0 | Logical compatibility and support are both reviewed, but native execution is absent | The reviewed `T-20260903-002` (`RV-20260903-002`) falsifies outcome-independent support. OOP-256 has an exact maximum possible-support union of 1,003; IP-256 retains a witnessed-union lower bound 935 and sound upper bound 1,006, while one sampled branch reaches weight 509. These logical unions are not connected code supports and may combine different branches. | Implement a coherent native mapper or explicit frame-materialization policy before assigning surgery rounds, runtime, or physical resources; no task ID is claimed for this yet. |
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
