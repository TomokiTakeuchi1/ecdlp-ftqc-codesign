---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - decisions
updated: 2026-10-01
---

# Decisions and Blockers

[[Research Hub/Home|← Home]] · [[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Progress Log|Progress Log]]

## One decision needed from the researcher

Latest LP checkpoint (T-20261001-004, `RV-20261001-004` `APPROVED`): a two-stage mask
provides the300+2 logical X family with certified constituent distances>=3.
The algebraic protected-code construction is now concrete; the unresolved
bottleneck is FT uniform preparation/check extraction/readout and decoding,
not simply existence of a homomorphic map. Preparation auxiliary carriers
are18675 before QEC ancillas. Do not price this as a native factory or reopen
QCLA optimization until those costs are addressed. D-0037 is ACCEPTED following
the approved cross-review; strict300 residual preservation is still OPEN.

> [!question] Select the canonical full ECDLP-256 circuit (`T-BOOT-001`)
> **Recommended starting contract:** Schrottenloher 2026 as the primary source baseline, with Luo et al. v2 as a dynamic/low-space contrast.  
> **Alternative:** require exact arithmetic first and promote Luo v2 only after resolving its exceptional-point and count-contract checks.  
> Record the choice in [[docs/CANONICAL_CIRCUIT_DECISION|Canonical Circuit Decision]].

Why this blocks progress: controlled point-addition counts, success semantics, exceptional points, measurements, and uncomputation all propagate into the Full-Shor workload.

## Technical blockers

LP/GHZ update (T-20261001-001, `RV-20261001-001` `APPROVED`): the fixed homomorphic map is algebraically
available, but both explicit 525-qubit helpers have d_Z=1. An explicit protected
helper or repeated-measurement/decoder construction is required before FT
runtime or physical-factory claims. Strict300 additionally needs extraction of
two weight-75 checks. See
[[docs/LP_GHZ_HOMOMORPHIC_PREPARATION_CONTRACT|LP GHZ construction]].

| Priority | Blocker | Why it matters | Next evidence-producing action |
|---:|---|---|---|
| 0 | Hybrid H-tracking/bare-CNOT has no native automorphism mapper | Approved `T-20260927-001` (`RV-20260927-001`) completes 66-branch logical/capacity profiling: unlimited-support general service matches full tracking, while finite S=512 offers only a paired median 1 unit for extra CNOT/X work. Four source layers do not imply four constant-time native gates. | Independently review the hybrid semantics and budgets before selecting any code-specific automorphism or ancilla construction; keep addressability, duration and endpoints explicit. |
| 0 | Legacy Clifford execution cost and feasibility remain unknown | Approved `T-20260926-002` (`RV-20260926-002`) computes paired PPM savings, including 18 IP cells refined to 512 hashes; Bcrit is an additional serial Clifford-time budget, not a native implementation | Synthesize one realizable conjugated-H/bare-CNOT service and pair its branch-dependent total B with Bcrit |
| 0 | Both OOP and IP width-256 structures and the shared branch audit are reviewed; native execution is still absent | OOP `T-20260906-004` (`RV-20260907-003` `APPROVED`) is exact model-relative 15/30. IP `T-20260907-001` (`RV-20260907-004` `APPROVED`) is 30/60. The reviewed shared branch audit (`T-20260907-002`, `RV-20260907-005` `APPROVED`) gives p95 168/188 and hashed-assignment maxima 223/248 beneath separate ceilings 1,003/1,006. | Implement one frame-materialization/native-mapping policy against both workloads (no task ID claimed yet). Do not assign physical time from logical candidate counts or sampled weights. |
| 0 | H/CNOT logical policy is separated from native realization, but no code-side choice is admitted | `T-20260905-001` proposes frame-conjugated H plus bare CNOT; `RV-20260905-001` is `APPROVED` (Claude, 2026-09-06) after independently confirming the H/Y witness, CNOT closure, width-256 layers, RASCqL citations, and codex's H-teleport citation fix (H is self-derived `NUMERICAL` with an exact four-branch channel check, independently re-derived twice; Xu Figure 11(c) remains only on measurement CNOT). H-SWAP/H teleportation directly implements bare H and can break the Z-only invariant without frame clearing or an H-safe proof; CNOT is axis-safe but addressability, support, routing, and relabel debt remain. The 54/106--111/216 figures are logical-layer envelopes only. | Test either the 3/4 CNOT-layer matrices against a concrete automorphism/SIMD ISA or the 34/68 H masks against H-SWAP packing / whole-event co-design. |
| 0 | Tracked-frame low-rate profile has no physical support model | `T-20260926-001` (`RV-20260926-001` `APPROVED`) shows K/weight/support trade-offs and excludes all-one witnesses at weight 512; maximum weight is regularization-order sensitive. T-20260926-002 completes the selected 512-hash boundary refinement and is approved (`RV-20260926-002`, 2026-09-27) | Calibrate physical representatives, ancilla preparation and controller service with a finite code/hardware model; the refinement does not establish native feasibility |
| 0 | Frame-materialization policies are profiled but none is selected | `T-20260909-001` (`RV-20260909-001` `APPROVED`, 2026-09-26) shows partial clearing saves literal CNOTs (3,843 versus 4,250 median) yet lengthens the serialized layer envelope (380 versus 270) and widens PPM support (11/16 versus 2); the CNOT-batch metric also depends on ASAP direction | Resynthesize the materialized Clifford globally and map it onto one finite code-native H/CNOT/surgery model before choosing; keep all outputs as logical envelopes until then |
| 0 | Logical branch distributions exist, but no probability law or native geometry is admitted | `T-20260907-002` (`RV-20260907-005` `APPROVED`, 2026-09-07) separates p50/p95/p99, hashed maxima, forced boundary branches, and ceilings. The full maximum 509 is an all-one boundary witness, while hashed maxima are 223/248. These branch-dependent logical weights are not occurrence probabilities, connected code support, simultaneous physical contacts, or time. | Preserve both distributions and ceilings while comparing direct, full-frame-clear, and selective-materialization policies; add a probability model only if measurement-outcome correlations are explicitly justified. |
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
