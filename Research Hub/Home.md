---
aliases:
  - Research Dashboard
cssclasses:
  - research-dashboard
tags:
  - dashboard
updated: 2026-09-01
---

# ECDLP-256 FTQC Research Hub

> [!abstract] Current snapshot — 2026-09-01
> **Phase:** Month 1 — arithmetic circuit to QEC schedule  
> **Current focus:** Cross-review the width-5 symbolic direct-CCZ PPM/frame trace, then classify high-rate candidates without implying a native schedule.
> **Long-term target:** ECDLP-256 in roughly 10,000–tens of thousands of physical qubits and days–tens of days, with every assumption made explicit.

[[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Progress Log|Progress Log]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]] · [[Research Hub/Architecture Map.canvas|Architecture Map]] · [[Research Hub/Glossary|Glossary]] · [[Research Hub/How to Update|How to Update]]

## At a glance

| Workstream | Status | Human-friendly summary |
|---|---|---|
| Literature baseline | ✅ Reviewed | 21 primary-source PDFs are indexed locally, including the two Gidney--Fowler PDFs and four official assets reviewed in `RV-20260901-001`. |
| Gidney adder DAG | ✅ Reviewed | The ripple-carry adder is converted to a QEC-independent causal DAG and checked at small widths and width 256. |
| Mitten scheduling prototype | ✅ Reviewed | Claude approved the conditional scheduler (`RV-20260815-004`); its operation times are still not an executable-runtime result. |
| Adaptive PBC/CQLU lowering | ✅ Reviewed | Claude approved the quantum-output-preserving trace (`RV-20260815-006`); exact CNOT/H/S/T/T-dagger Pauli supports and compiler ancillas are generated, while native duration evidence remains open. |
| Adaptive J300 scheduling | ✅ Reviewed | Claude approved the resource-constrained scheduler (`RV-20260815-007`); scratch, carrier, reaction, and exact-ten-XX rules are enforced, but strict runtime remains blocked by missing native evidence. |
| Canonical full ECDLP circuit | 🔵 Human decision | `T-BOOT-001` still requires selection of the first full-circuit contract. |
| Memory–Processor I/O | ✅ Reviewed | Claude approved the replayable memory-I/O overlay (`RV-20260823-001`); it reproduces exact width-2--4 partition references, but bridge occupancy, prefetch, and transfer timing remain open. |
| Bell-bridge ripple adder | ✅ Reviewed | Claude approved the source-pinned workload (`RV-20260824-001`); it separates carry teleportation from memory I/O, replays bridge ownership, and exposes exact-ten-XX sensitivity, but finite timing and full phase reconstruction remain open. |
| Carry-lookahead adder | ✅ Reviewed | Claude approved the source-pinned Draper QCLA (`RV-20260824-003`); it preserves prefix rounds and ancilla reuse, passes exhaustive widths 2--6, and exposes a width-256 Toffoli-demand trace, but no backend timing has been assigned. |
| QCLA adaptive PBC | ✅ Reviewed | Claude approved the exact seven-T CCX lowering (`RV-20260825-001`); resident width 14 exposes nine ten-XX batches, while width 256 fails the 60-slot check before scheduling. |
| QCLA memory/high-rate schedule | ✅ Reviewed | Claude approved the epoch-aware memory overlay (`RV-20260825-002`); it independently replays width 256 within 60 logical slots and exposes 1,576 ten-XX batches, but its one-round transfer/native timing and ideal factory remain `CHECK`. |
| Direct-CCZ single-event semantics | ✅ Reviewed | Claude approved the exact Figure 14(a) correction map (`RV-20260831-003`); width 256 emits 1,229 typed events, but finite high-rate service remains `OPEN`. |
| Symbolic direct-CCZ PPM/frame trace | ✅ Reviewed | Claude approved the width-5 canonical ANF frame trace (`RV-20260901-005`); it emits 60 exact PPMs and 60 conditional frame updates with independent replay; it is deliberately not a surgery schedule. |
| Finite direct-CCZ backend audit | ✅ Reviewed | Claude approved the 17-field compatibility gate (`RV-20260831-004`); it rejects the selected backend with 13 missing and three incompatible fields, and no schedule is emitted. |
| AutoCCZ surface-code adapter | ✅ Reviewed | Claude approved the source-native factory/fixup/consumer adapter (`RV-20260901-001`); complete service remains `OPEN` with nine missing and one distance-incompatible field, so no width-256 schedule exists. |
| Full Shor estimate | ⚪ Not started | Month 2 begins after the arithmetic and architecture contracts are stable. |
| Factory validation | ⚪ Not started | Month 3 will turn the T/CCZ demand trace into an explicit factory design. |

## What is trustworthy today?

> [!success] Reviewed foundation
> The Gidney adapter preserves logical-value lifetimes, quantum dependencies, X-basis erase measurements, and classical feed-forward. Claude approved this bounded prototype in `RV-20260815-003`. Claude also approved the conditional Mitten lowering and greedy scheduler in `RV-20260815-004`, including an independent gate-by-gate check of the Figure-3 trace against the pinned source's exhaustively verified circuit. Claude further approved the adaptive PBC/CQLU trace in `RV-20260815-006` after independently re-deriving its operation-count formulas and hand-checking the CNOT/H/S/T/T-dagger gadgets' Clifford-conjugation algebra. Claude also approved the J300 resource-constrained scheduler in `RV-20260815-007` after hand-verifying its high-rate round-savings arithmetic and scratch-slot allocation logic. Claude approved the memory-I/O overlay in `RV-20260823-001`, confirming its independent replay engine recomputes every placement from scratch rather than trusting the placement algorithm's own bookkeeping. Claude approved the Bell-bridge ripple cycle in `RV-20260824-001`, confirming the generic-bridge circuit is the standard teleportation decomposition and that its branch probability lands at essentially exactly 1/4 across 32 random states, as the no-signaling property predicts. Claude approved the Draper QCLA DAG in `RV-20260824-003`, hand-deriving the width-2 circuit by symbolic Boolean algebra and independently exhaustively replaying an untested width plus five untested random widths. Claude approved the QCLA adaptive-PBC lowering in `RV-20260825-001`, independently rebuilding the full 8x8 Selinger CCX unitary from scratch and finding it matches ideal CCX with zero global-phase correction needed. Claude approved the clean OOP-QCLA trace and direct-CCZ capability gate in `RV-20260831-002`, writing an independent from-scratch classical-reversible simulator that reproduced every closed-form count and confirmed the capability/adapter logic is genuinely fail-closed against forged admission flags. Claude approved the exact Figure 14(a) single-event correction map in `RV-20260831-003`, rendering the primary source PDF to a 600 DPI image and directly pixel-verifying every wire assignment and correction formula, and independently writing a from-scratch numpy channel reconstruction that reproduced all 64 measurement branches before reading the repository's own verifier. Claude approved the finite direct-CCZ backend compatibility audit in `RV-20260831-004`, pulling the raw Cain PDF text directly and confirming the source itself attributes the incompatible factory figures to a different architecture regime than the selected candidate. Claude approved the AutoCCZ surface-code adapter in `RV-20260901-001`, rendering the primary source's Figures 3/4/6 directly and unzipping the official ODS calculator to independently confirm its output-error cell belongs to a different code-distance example than the selected candidate. Claude most recently approved the symbolic direct-CCZ PPM/frame trace in `RV-20260901-005`, independently verifying every primitive Clifford-conjugation rule against explicit unitary matrices and reconstructing a nontrivial later PPM's presented observable end to end -- catching and fixing a bug in its own first reconstruction attempt before confirming an exact match with the compiler's output.

> [!warning] Provisional sensitivity result — `CHECK`
> For the adaptive width-32 Gidney trace, the J300 sensitivity profile gives **31,176 syndrome rounds**, ten-scratch occupancy **43**, and **zero high-rate hits**. Adding memory I/O (100 loads, 100 stores, one round each, fixed order, no prefetch) brings the combined figure to **31,376 rounds**. This excludes bridge occupancy, factory construction, routing, decoder tail, setup/readout, and wall-clock conversion. It is **not** a days-level runtime or total-qubit claim, and the 100/100 transfer count is a fixed-order/no-prefetch policy result, not a placement lower bound.

> [!warning] Bell-bridge sensitivity — `CHECK`
> In the separate Figure-6 bridge workload, width 32 takes **64 normalized steps** with one Bell-measurement lane and singleton components, or **37 normalized steps** when three exact-ten `XX` batches are admitted. With two or more Bell-measurement lanes both policies take **34 steps**, showing the bottleneck shifts to dependencies/reaction in this model. These units are not syndrome rounds, HGP cycles, active-volume blocks, or wall-clock time.

> [!warning] QCLA source parallelism — `NUMERICAL`, not runtime
> The width-256 Draper trace has **40 source layers**, **495 logical circuit ancillas**, and a peak of **255 Toffolis in one layer**. This is the demand a backend must serve, not evidence that 255 operations can execute simultaneously or that the adder completes in 40 QEC cycles.

> [!warning] QCLA memory/high-rate sensitivity — `NUMERICAL` placement / `CHECK` time
> The fixed-order width-256 overlay now enforces **60 logical slots** and independently replays all value moves. One-scratch serial uses **46,355 loads and 46,355 stores**; ten-scratch high-rate uses **53,788 of each**, selects **1,576 exact-ten-XX batches**, and changes the provisional one-round/one-lane schedule from **2,589,787 to 2,420,527 rounds** (6.54% shorter). This is not a placement optimum or executable runtime; routing, factory service/buffering/stalls, decoding, failure, and wall-clock conversion are excluded.

> [!danger] Strict-runtime blocker
> The adaptive trace is now reviewed, resource-constrained scheduled, and memory-I/O aware, but strict J300 durations for state preparation, Z/ZZ/ZX/full extraction, reaction, conditional CZ, and memory transfer are still missing. Strict mode rejects the resulting schedule.

> [!warning] Direct-CCZ single-event channel — `NUMERICAL`, reviewed `RV-20260831-003`
> Under the explicit outcome convention `0 -> +1`, `1 -> -1`, all **64** Figure 14(a) measurement branches match ideal CCX with probability **1/64** and zero operator residual at floating-point precision. Width 256 now emits **1,229** typed injections and preserves **3,955** source dependencies. This is semantic demand only: high-rate service, QEC timing, routing, factory buffering, physical qubits, and runtime remain absent.

> [!warning] Symbolic direct-CCZ PPM/frame trace — `NUMERICAL`, reviewed `RV-20260901-005`
> Width 5 now lowers directly to **10 injections**, **60 PPMs**, **60 conditional frame updates**, and **13 implementation-neutral CNOTs**, preserving all **36** source dependencies. Independent replay checks 640 local correction rows, 3,840 presented observables, all 1,024 basis inputs, and the 64-branch local channel. The 64 global probes are regression coverage, not exhaustive `2^60` verification. Source layers are not surgery rounds, CNOT costs remain open, and no schedule was generated.

> [!danger] Finite direct-CCZ backend gate — `OPEN`, reviewed `RV-20260831-004`
> Seven primary sources were mapped into one 17-field compatibility audit. The
> selected Cain `P=20` candidate has **13 missing finite fields**; the available
> batch-10, 120-cycle, approximately-`1e-10` factory values belong to a
> different `bb18` architecture domain and are rejected. Tricycle CCZ
> generation, batched qLDPC operations, finite T ports, and in-situ Y injection
> remain visible alternatives but are not silently composed. No schedule was
> generated.

> [!warning] AutoCCZ adapter — `LITERATURE`/`NUMERICAL`, reviewed `RV-20260901-001`
> Gidney--Fowler's source-native surface-code path connects one CCZ-factory
> output through three delayed-choice CZ cells and six routing qubits to one
> Toffoli consumer. An abstract check matches ideal CCX on all **64** branches.
> Under `CHECK` timing inputs the example yields **135 cycles/CCZ**, about
> **7.407 kHz/factory**, and **14 factories** for 100 kHz average demand.
> Complete service is still rejected: nine finite fields are missing and the
> official `5.33332e-11` error belongs to `d1=15,d2=31`, not the selected
> `d1=17,d2=27`. No schedule was generated.

## Next three decisions/actions

1. **Human:** close `T-BOOT-001` by choosing the canonical ECDLP circuit contract in [[docs/CANONICAL_CIRCUIT_DECISION|Canonical Circuit Decision]].
2. **Compiler:** implement `T-20260901-007` with separate general-candidate, finite-instance, and low-rate-fallback outputs.

## Quick access to canonical records

- Project truth: [[context/STATUS|Project Status]] · [[context/TASKS|Task Board]] · [[context/AI_HANDOFF|AI Handoff]]
- Scientific records: [[context/DECISIONS|Decisions]] · [[context/RESULT_LEDGER|Result Ledger]] · [[context/ASSUMPTIONS|Assumptions]]
- Review state: [[coordination/REVIEW_QUEUE|Review Queue]]
- Technical contracts: [[docs/GIDNEY_DAG_CONTRACT|Gidney DAG]] · [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Mitten Lowering]] · [[docs/PBC_CQLU_LOWERING_CONTRACT|Adaptive PBC/CQLU]] · [[docs/J300_PBC_SCHEDULING_CONTRACT|J300 scheduling]] · [[docs/MEMORY_IO_EXECUTION_CONTRACT|Memory I/O]] · [[docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT|Bell-bridge ripple]] · [[docs/QCLA_DAG_CONTRACT|QCLA DAG]] · [[docs/QCLA_PBC_LOWERING_CONTRACT|QCLA adaptive PBC]] · [[docs/QCLA_MEMORY_IO_CONTRACT|QCLA memory/high rate]] · [[docs/HIGH_RATE_QCLA_DIRECT_CCZ_RESEARCH_CYCLE|Direct-CCZ research plan]] · [[docs/DIRECT_CCZ_CAPABILITY_AND_OOP_QCLA_CONTRACT|Direct-CCZ capability/OOP trace]] · [[docs/DIRECT_CCZ_SINGLE_EVENT_CONTRACT|Direct-CCZ single event]] · [[docs/DIRECT_CCZ_PPM_TRACE_CONTRACT|Symbolic direct-CCZ PPM/frame trace]] · [[docs/DIRECT_CCZ_FINITE_BACKEND_AUDIT|Finite direct-CCZ backend audit]] · [[docs/AUTOCCZ_SURFACE_CODE_ADAPTER|AutoCCZ adapter]]
- Source corpus: [[literature/papers/INDEX|Paper Index]] · [[literature/READING_QUEUE|Reading Queue]]

> [!info] Status language
> **Reviewed** means cross-review completed. **In review** means implemented but not yet accepted. **CHECK** means a numerical or modelling assumption still needs validation. This dashboard summarizes the project; the linked canonical records remain authoritative.
