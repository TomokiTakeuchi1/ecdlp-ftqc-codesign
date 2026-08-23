---
aliases:
  - Research Dashboard
cssclasses:
  - research-dashboard
tags:
  - dashboard
updated: 2026-08-23
---

# ECDLP-256 FTQC Research Hub

> [!abstract] Current snapshot — 2026-08-23
> **Phase:** Month 1 — arithmetic circuit to QEC schedule  
> **Current focus:** Resolve native J300 timing evidence, then begin a Bell-bridge teleportation-based ripple-carry cycle.
> **Long-term target:** ECDLP-256 in roughly 10,000–tens of thousands of physical qubits and days–tens of days, with every assumption made explicit.

[[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Progress Log|Progress Log]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]] · [[Research Hub/Architecture Map.canvas|Architecture Map]] · [[Research Hub/Glossary|Glossary]] · [[Research Hub/How to Update|How to Update]]

## At a glance

| Workstream | Status | Human-friendly summary |
|---|---|---|
| Literature baseline | ✅ Reviewed | 14 primary-source PDFs are indexed locally and the corpus review is approved. |
| Gidney adder DAG | ✅ Reviewed | The ripple-carry adder is converted to a QEC-independent causal DAG and checked at small widths and width 256. |
| Mitten scheduling prototype | ✅ Reviewed | Claude approved the conditional scheduler (`RV-20260815-004`); its operation times are still not an executable-runtime result. |
| Adaptive PBC/CQLU lowering | ✅ Reviewed | Claude approved the quantum-output-preserving trace (`RV-20260815-006`); exact CNOT/H/S/T/T-dagger Pauli supports and compiler ancillas are generated, while native duration evidence remains open. |
| Adaptive J300 scheduling | ✅ Reviewed | Claude approved the resource-constrained scheduler (`RV-20260815-007`); scratch, carrier, reaction, and exact-ten-XX rules are enforced, but strict runtime remains blocked by missing native evidence. |
| Canonical full ECDLP circuit | 🔵 Human decision | `T-BOOT-001` still requires selection of the first full-circuit contract. |
| Memory–Processor I/O | ✅ Reviewed | Claude approved the replayable memory-I/O overlay (`RV-20260823-001`); it reproduces exact width-2--4 partition references, but bridge occupancy, prefetch, and transfer timing remain open. |
| Full Shor estimate | ⚪ Not started | Month 2 begins after the arithmetic and architecture contracts are stable. |
| Factory validation | ⚪ Not started | Month 3 will turn the T/CCZ demand trace into an explicit factory design. |

## What is trustworthy today?

> [!success] Reviewed foundation
> The Gidney adapter preserves logical-value lifetimes, quantum dependencies, X-basis erase measurements, and classical feed-forward. Claude approved this bounded prototype in `RV-20260815-003`. Claude also approved the conditional Mitten lowering and greedy scheduler in `RV-20260815-004`, including an independent gate-by-gate check of the Figure-3 trace against the pinned source's exhaustively verified circuit. Claude further approved the adaptive PBC/CQLU trace in `RV-20260815-006` after independently re-deriving its operation-count formulas and hand-checking the CNOT/H/S/T/T-dagger gadgets' Clifford-conjugation algebra. Claude also approved the J300 resource-constrained scheduler in `RV-20260815-007` after hand-verifying its high-rate round-savings arithmetic and scratch-slot allocation logic. Claude most recently approved the memory-I/O overlay in `RV-20260823-001`, confirming its independent replay engine recomputes every placement from scratch rather than trusting the placement algorithm's own bookkeeping.

> [!warning] Provisional sensitivity result — `CHECK`
> For the adaptive width-32 Gidney trace, the J300 sensitivity profile gives **31,176 syndrome rounds**, ten-scratch occupancy **43**, and **zero high-rate hits**. Adding memory I/O (100 loads, 100 stores, one round each, fixed order, no prefetch) brings the combined figure to **31,376 rounds**. This excludes bridge occupancy, factory construction, routing, decoder tail, setup/readout, and wall-clock conversion. It is **not** a days-level runtime or total-qubit claim, and the 100/100 transfer count is a fixed-order/no-prefetch policy result, not a placement lower bound.

> [!danger] Strict-runtime blocker
> The adaptive trace is now reviewed, resource-constrained scheduled, and memory-I/O aware, but strict J300 durations for state preparation, Z/ZZ/ZX/full extraction, reaction, conditional CZ, and memory transfer are still missing. Strict mode rejects the resulting schedule.

## Next three decisions/actions

1. **Human:** close `T-BOOT-001` by choosing the canonical ECDLP circuit contract in [[docs/CANONICAL_CIRCUIT_DECISION|Canonical Circuit Decision]].
2. **Backend:** pin J300 preparation, Z/ZZ/ZX/full-extractor, reaction, conditional-CZ, and memory-transfer duration contracts.
3. **Next cycle:** begin a separately scoped Bell-bridge teleportation-based ripple-carry cycle with its own communication-timing evidence; do not reuse memory-transfer timing as Bell-bridge timing.

## Quick access to canonical records

- Project truth: [[context/STATUS|Project Status]] · [[context/TASKS|Task Board]] · [[context/AI_HANDOFF|AI Handoff]]
- Scientific records: [[context/DECISIONS|Decisions]] · [[context/RESULT_LEDGER|Result Ledger]] · [[context/ASSUMPTIONS|Assumptions]]
- Review state: [[coordination/REVIEW_QUEUE|Review Queue]]
- Technical contracts: [[docs/GIDNEY_DAG_CONTRACT|Gidney DAG]] · [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Mitten Lowering]] · [[docs/PBC_CQLU_LOWERING_CONTRACT|Adaptive PBC/CQLU]] · [[docs/J300_PBC_SCHEDULING_CONTRACT|J300 scheduling]] · [[docs/MEMORY_IO_EXECUTION_CONTRACT|Memory I/O]]
- Source corpus: [[literature/papers/INDEX|Paper Index]] · [[literature/READING_QUEUE|Reading Queue]]

> [!info] Status language
> **Reviewed** means cross-review completed. **In review** means implemented but not yet accepted. **CHECK** means a numerical or modelling assumption still needs validation. This dashboard summarizes the project; the linked canonical records remain authoritative.
