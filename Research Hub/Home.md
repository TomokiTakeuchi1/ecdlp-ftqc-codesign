---
aliases:
  - Research Dashboard
cssclasses:
  - research-dashboard
tags:
  - dashboard
updated: 2026-08-25
---

# ECDLP-256 FTQC Research Hub

> [!abstract] Current snapshot — 2026-08-25
> **Phase:** Month 1 — arithmetic circuit to QEC schedule  
> **Current focus:** Partition width-256 QCLA across processor and memory without assuming free I/O, then jointly schedule I/O, scratch, high-rate surgery, and factory demand.
> **Long-term target:** ECDLP-256 in roughly 10,000–tens of thousands of physical qubits and days–tens of days, with every assumption made explicit.

[[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Progress Log|Progress Log]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]] · [[Research Hub/Architecture Map.canvas|Architecture Map]] · [[Research Hub/Glossary|Glossary]] · [[Research Hub/How to Update|How to Update]]

## At a glance

| Workstream | Status | Human-friendly summary |
|---|---|---|
| Literature baseline | ✅ Reviewed | 15 primary-source PDFs are indexed locally, including the reviewed Selinger CCX source. |
| Gidney adder DAG | ✅ Reviewed | The ripple-carry adder is converted to a QEC-independent causal DAG and checked at small widths and width 256. |
| Mitten scheduling prototype | ✅ Reviewed | Claude approved the conditional scheduler (`RV-20260815-004`); its operation times are still not an executable-runtime result. |
| Adaptive PBC/CQLU lowering | ✅ Reviewed | Claude approved the quantum-output-preserving trace (`RV-20260815-006`); exact CNOT/H/S/T/T-dagger Pauli supports and compiler ancillas are generated, while native duration evidence remains open. |
| Adaptive J300 scheduling | ✅ Reviewed | Claude approved the resource-constrained scheduler (`RV-20260815-007`); scratch, carrier, reaction, and exact-ten-XX rules are enforced, but strict runtime remains blocked by missing native evidence. |
| Canonical full ECDLP circuit | 🔵 Human decision | `T-BOOT-001` still requires selection of the first full-circuit contract. |
| Memory–Processor I/O | ✅ Reviewed | Claude approved the replayable memory-I/O overlay (`RV-20260823-001`); it reproduces exact width-2--4 partition references, but bridge occupancy, prefetch, and transfer timing remain open. |
| Bell-bridge ripple adder | ✅ Reviewed | Claude approved the source-pinned workload (`RV-20260824-001`); it separates carry teleportation from memory I/O, replays bridge ownership, and exposes exact-ten-XX sensitivity, but finite timing and full phase reconstruction remain open. |
| Carry-lookahead adder | ✅ Reviewed | Claude approved the source-pinned Draper QCLA (`RV-20260824-003`); it preserves prefix rounds and ancilla reuse, passes exhaustive widths 2--6, and exposes a width-256 Toffoli-demand trace, but no backend timing has been assigned. |
| QCLA adaptive PBC | ✅ Reviewed | Claude approved the exact seven-T CCX lowering (`RV-20260825-001`); resident width 14 exposes nine ten-XX batches, while width 256 fails the 60-slot check before scheduling. |
| Full Shor estimate | ⚪ Not started | Month 2 begins after the arithmetic and architecture contracts are stable. |
| Factory validation | ⚪ Not started | Month 3 will turn the T/CCZ demand trace into an explicit factory design. |

## What is trustworthy today?

> [!success] Reviewed foundation
> The Gidney adapter preserves logical-value lifetimes, quantum dependencies, X-basis erase measurements, and classical feed-forward. Claude approved this bounded prototype in `RV-20260815-003`. Claude also approved the conditional Mitten lowering and greedy scheduler in `RV-20260815-004`, including an independent gate-by-gate check of the Figure-3 trace against the pinned source's exhaustively verified circuit. Claude further approved the adaptive PBC/CQLU trace in `RV-20260815-006` after independently re-deriving its operation-count formulas and hand-checking the CNOT/H/S/T/T-dagger gadgets' Clifford-conjugation algebra. Claude also approved the J300 resource-constrained scheduler in `RV-20260815-007` after hand-verifying its high-rate round-savings arithmetic and scratch-slot allocation logic. Claude approved the memory-I/O overlay in `RV-20260823-001`, confirming its independent replay engine recomputes every placement from scratch rather than trusting the placement algorithm's own bookkeeping. Claude approved the Bell-bridge ripple cycle in `RV-20260824-001`, confirming the generic-bridge circuit is the standard teleportation decomposition and that its branch probability lands at essentially exactly 1/4 across 32 random states, as the no-signaling property predicts. Claude approved the Draper QCLA DAG in `RV-20260824-003`, hand-deriving the width-2 circuit by symbolic Boolean algebra and independently exhaustively replaying an untested width plus five untested random widths. Claude most recently approved the QCLA adaptive-PBC lowering in `RV-20260825-001`, independently rebuilding the full 8x8 Selinger CCX unitary from scratch and finding it matches ideal CCX with zero global-phase correction needed.

> [!warning] Provisional sensitivity result — `CHECK`
> For the adaptive width-32 Gidney trace, the J300 sensitivity profile gives **31,176 syndrome rounds**, ten-scratch occupancy **43**, and **zero high-rate hits**. Adding memory I/O (100 loads, 100 stores, one round each, fixed order, no prefetch) brings the combined figure to **31,376 rounds**. This excludes bridge occupancy, factory construction, routing, decoder tail, setup/readout, and wall-clock conversion. It is **not** a days-level runtime or total-qubit claim, and the 100/100 transfer count is a fixed-order/no-prefetch policy result, not a placement lower bound.

> [!warning] Bell-bridge sensitivity — `CHECK`
> In the separate Figure-6 bridge workload, width 32 takes **64 normalized steps** with one Bell-measurement lane and singleton components, or **37 normalized steps** when three exact-ten `XX` batches are admitted. With two or more Bell-measurement lanes both policies take **34 steps**, showing the bottleneck shifts to dependencies/reaction in this model. These units are not syndrome rounds, HGP cycles, active-volume blocks, or wall-clock time.

> [!warning] QCLA source parallelism — `NUMERICAL`, not runtime
> The width-256 Draper trace has **40 source layers**, **495 logical circuit ancillas**, and a peak of **255 Toffolis in one layer**. This is the demand a backend must serve, not evidence that 255 operations can execute simultaneously or that the adder completes in 40 QEC cycles.

> [!warning] QCLA adaptive-PBC sensitivity — `NUMERICAL` structure / `CHECK` time
> The selected exact CCX route expands width 256 to **40,857 logical primitives** and **17,206 T-state demands**, but fully resident execution needs **1,008 logical slots** with one scratch and is rejected on k=60 J300. At resident width 14, ten scratch slots expose **9 exact-ten-XX batches** and change the provisional schedule from **94,161 to 93,108 rounds**. Memory, routing, and factory stalls are excluded.

> [!danger] Strict-runtime blocker
> The adaptive trace is now reviewed, resource-constrained scheduled, and memory-I/O aware, but strict J300 durations for state preparation, Z/ZZ/ZX/full extraction, reaction, conditional CZ, and memory transfer are still missing. Strict mode rejects the resulting schedule.

## Next three decisions/actions

1. **Human:** close `T-BOOT-001` by choosing the canonical ECDLP circuit contract in [[docs/CANONICAL_CIRCUIT_DECISION|Canonical Circuit Decision]].
2. **Backend:** pin J300 preparation, Z/ZZ/ZX/full-extractor, reaction, conditional-CZ, and memory-transfer duration contracts.
3. **Next cycle:** partition width-256 QCLA across processor and memory, then jointly schedule I/O, scratch, high-rate surgery, and factory demand; separately investigate whether direct CCZ injection dominates the seven-T route.

## Quick access to canonical records

- Project truth: [[context/STATUS|Project Status]] · [[context/TASKS|Task Board]] · [[context/AI_HANDOFF|AI Handoff]]
- Scientific records: [[context/DECISIONS|Decisions]] · [[context/RESULT_LEDGER|Result Ledger]] · [[context/ASSUMPTIONS|Assumptions]]
- Review state: [[coordination/REVIEW_QUEUE|Review Queue]]
- Technical contracts: [[docs/GIDNEY_DAG_CONTRACT|Gidney DAG]] · [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Mitten Lowering]] · [[docs/PBC_CQLU_LOWERING_CONTRACT|Adaptive PBC/CQLU]] · [[docs/J300_PBC_SCHEDULING_CONTRACT|J300 scheduling]] · [[docs/MEMORY_IO_EXECUTION_CONTRACT|Memory I/O]] · [[docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT|Bell-bridge ripple]] · [[docs/QCLA_DAG_CONTRACT|QCLA DAG]] · [[docs/QCLA_PBC_LOWERING_CONTRACT|QCLA adaptive PBC]]
- Source corpus: [[literature/papers/INDEX|Paper Index]] · [[literature/READING_QUEUE|Reading Queue]]

> [!info] Status language
> **Reviewed** means cross-review completed. **In review** means implemented but not yet accepted. **CHECK** means a numerical or modelling assumption still needs validation. This dashboard summarizes the project; the linked canonical records remain authoritative.
