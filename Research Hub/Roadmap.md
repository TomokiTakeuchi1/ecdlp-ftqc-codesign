---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - roadmap
updated: 2026-08-15
---

# Research Roadmap

[[Research Hub/Home|← Home]] · [[Research Hub/Progress Log|Progress Log]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]]

## Month 1 — Arithmetic to executable schedules

**Status: ACTIVE**

<progress max="15" value="6"></progress> 6 of 15 listed Month-1 milestones are complete; 1 more is in review.

### Completed or reviewed

- [x] Build and review the primary-source literature corpus.
- [x] Convert the pinned Gidney ripple-carry oracle into a QEC-neutral causal DAG.
- [x] Preserve erase measurements and classical feed-forward explicitly.
- [x] Add a conditional Mitten lowering and deterministic greedy scheduler.
- [x] Complete cross-review of the Mitten scheduler (`RV-20260815-004`).
- [x] Complete cross-review of the adaptive PBC/CQLU trace (`RV-20260815-006`).

### Active

- [ ] Complete cross-review of the adaptive J300 resource scheduler (`RV-20260815-007`).

### Still required for the full Month-1 goal

- [ ] Controlled ripple-carry adder.
- [ ] Carry-lookahead and controlled carry-lookahead adders with prefix-tree parallelism preserved.
- [ ] Unary lookup.
- [ ] Processor-capacity partitioner.
- [ ] Memory load/store, teleportation, inter-block PPM, and bridge model.
- [ ] Canonical LP backend and LP-memory/Mitten-processor hybrid schedule.
- [ ] Comparable runtime, physical-qubit, communication, and T/CCZ-demand outputs.
- [ ] Replace `CHECK` J300 preparation/Z/ZZ/ZX/reaction/conditional-CZ sensitivity times with source-pinned or explicitly validated contracts.

## Month 2 — Full ECDLP-256 Shor estimate

**Status: NOT STARTED**

Connect the Month-1 subcircuits into a hierarchical workload:

Adder → modular arithmetic → field multiplication/inversion → controlled point addition → scalar multiplication/phase estimation → Full Shor.

Main outputs will be resource-constrained schedules, physical-qubit-count–runtime curves excluding factory construction, and a time-dependent T/CCZ demand specification for Month 3.

## Month 3 — Factory design and end-to-end feasibility

**Status: NOT STARTED**

Design and validate the resource-state factories needed by the Month-2 demand trace. Include throughput, bursts, buffers, routing, spare factories, failure budgets, and the resulting schedule stalls.

The final question is not merely “How many T states?” but “Which architecture assumptions are sufficient to reach the target qubit count and runtime?”

## Gates between months

| Gate | Required evidence | Current state |
|---|---|---|
| Month 1 → Month 2 | Reproducible subcircuit library and architecture schedules | Not yet satisfied |
| Month 2 → Month 3 | Full-Shor demand trace and factory requirement specification | Not started |
| Month 3 → final report | Factory-inclusive qubits, runtime, and failure budget | Not started |
