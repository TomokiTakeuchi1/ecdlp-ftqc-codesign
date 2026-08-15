---
aliases:
  - Research Dashboard
cssclasses:
  - research-dashboard
tags:
  - dashboard
updated: 2026-08-15
---

# ECDLP-256 FTQC Research Hub

> [!abstract] Current snapshot — 2026-08-15
> **Phase:** Month 1 — arithmetic circuit to QEC schedule  
> **Current focus:** Turn the verified Gidney adder DAG into a strict, executable Mitten/Canonical-LP schedule.  
> **Long-term target:** ECDLP-256 in roughly 10,000–tens of thousands of physical qubits and days–tens of days, with every assumption made explicit.

[[Research Hub/Roadmap|Roadmap]] · [[Research Hub/Progress Log|Progress Log]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]] · [[Research Hub/Architecture Map.canvas|Architecture Map]] · [[Research Hub/Glossary|Glossary]] · [[Research Hub/How to Update|How to Update]]

## At a glance

| Workstream | Status | Human-friendly summary |
|---|---|---|
| Literature baseline | ✅ Reviewed | 14 primary-source PDFs are indexed locally and the corpus review is approved. |
| Gidney adder DAG | ✅ Reviewed | The ripple-carry adder is converted to a QEC-independent causal DAG and checked at small widths and width 256. |
| Mitten scheduling prototype | ✅ Reviewed | Claude approved the conditional scheduler (`RV-20260815-004`); its operation times are still not an executable-runtime result. |
| Adaptive PBC/CQLU lowering | ✅ Reviewed | Claude approved the quantum-output-preserving trace (`RV-20260815-006`); exact CNOT/H/S/T/T-dagger Pauli supports and compiler ancillas are generated, but native durations and adaptive scheduling remain open. |
| Canonical full ECDLP circuit | 🔵 Human decision | `T-BOOT-001` still requires selection of the first full-circuit contract. |
| Memory–Processor I/O | ⚪ Not implemented | Load/store, bridge occupancy, and communication scheduling remain Month-1 work. |
| Full Shor estimate | ⚪ Not started | Month 2 begins after the arithmetic and architecture contracts are stable. |
| Factory validation | ⚪ Not started | Month 3 will turn the T/CCZ demand trace into an explicit factory design. |

## What is trustworthy today?

> [!success] Reviewed foundation
> The Gidney adapter preserves logical-value lifetimes, quantum dependencies, X-basis erase measurements, and classical feed-forward. Claude approved this bounded prototype in `RV-20260815-003`. Claude also approved the conditional Mitten lowering and greedy scheduler in `RV-20260815-004`, including an independent gate-by-gate check of the Figure-3 trace against the pinned source's exhaustively verified circuit. Claude further approved the adaptive PBC/CQLU trace in `RV-20260815-006` after independently re-deriving its operation-count formulas and hand-checking the CNOT/H/S/T/T-dagger gadgets' Clifford-conjugation algebra.

> [!warning] Provisional sensitivity result — `CHECK`
> For the current width-59 Gidney trace, the provisional J300 Mitten profile gives **15,270 syndrome rounds**, source occupancy **60**, and **zero high-rate hits**. This excludes Memory I/O, bridge, factory construction, routing, decoder tail, setup/readout, and wall-clock conversion. It is **not** a days-level runtime or total-qubit claim.

> [!danger] Strict-runtime blocker
> The phase-exact, reviewed Pauli-based CQLU trace now exists, but strict J300 durations for state preparation, Z/ZZ/ZX measurements, reaction, and conditional CZ are still missing. The adaptive trace has not yet been resource-constrained scheduled.

## Next three decisions/actions

1. **Human:** close `T-BOOT-001` by choosing the canonical ECDLP circuit contract in [[docs/CANONICAL_CIRCUIT_DECISION|Canonical Circuit Decision]].
2. **Backend:** pin J300 preparation, Z/ZZ/ZX, reaction, and conditional-CZ contracts, then schedule the reviewed adaptive PBC trace and reassess exact-ten-XX high-rate batches.
3. **Documentation:** cite `runtime_metadata_benchmark.gidney.coherent._apply_figure3_compute` as the cross-checked source of the Figure-3 gate sequence in [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Mitten Lowering]] (non-blocking suggestion repeated across two reviews).

## Quick access to canonical records

- Project truth: [[context/STATUS|Project Status]] · [[context/TASKS|Task Board]] · [[context/AI_HANDOFF|AI Handoff]]
- Scientific records: [[context/DECISIONS|Decisions]] · [[context/RESULT_LEDGER|Result Ledger]] · [[context/ASSUMPTIONS|Assumptions]]
- Review state: [[coordination/REVIEW_QUEUE|Review Queue]]
- Technical contracts: [[docs/GIDNEY_DAG_CONTRACT|Gidney DAG]] · [[docs/MITTEN_GIDNEY_LOWERING_CONTRACT|Mitten Lowering]] · [[docs/PBC_CQLU_LOWERING_CONTRACT|Adaptive PBC/CQLU]]
- Source corpus: [[literature/papers/INDEX|Paper Index]] · [[literature/READING_QUEUE|Reading Queue]]

> [!info] Status language
> **Reviewed** means cross-review completed. **In review** means implemented but not yet accepted. **CHECK** means a numerical or modelling assumption still needs validation. This dashboard summarizes the project; the linked canonical records remain authoritative.
