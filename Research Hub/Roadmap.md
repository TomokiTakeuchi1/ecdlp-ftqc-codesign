---
cssclasses:
  - research-dashboard
tags:
  - dashboard
  - roadmap
updated: 2026-09-01
---

# Research Roadmap

[[Research Hub/Home|← Home]] · [[Research Hub/Progress Log|Progress Log]] · [[Research Hub/Decisions and Blockers|Decisions & Blockers]]

## Month 1 — Arithmetic to executable schedules

**Status: ACTIVE**

<progress max="21" value="17"></progress> 17 of 21 listed Month-1 milestones are complete or in review; 4 more are required.

### Completed or reviewed

- [x] Build and review the primary-source literature corpus.
- [x] Convert the pinned Gidney ripple-carry oracle into a QEC-neutral causal DAG.
- [x] Preserve erase measurements and classical feed-forward explicitly.
- [x] Add a conditional Mitten lowering and deterministic greedy scheduler.
- [x] Complete cross-review of the Mitten scheduler (`RV-20260815-004`).
- [x] Complete cross-review of the adaptive PBC/CQLU trace (`RV-20260815-006`).
- [x] Complete cross-review of the adaptive J300 resource scheduler (`RV-20260815-007`).
- [x] Add and review a replayable processor-memory I/O overlay (`RV-20260823-001`).
- [x] Add and review a Bell-bridge teleportation ripple cycle (`RV-20260824-001`).
- [x] Source-pin and review a QCLA event/dependency contract (`RV-20260824-003`).
- [x] Lower and review the QCLA/Toffoli adaptive-PBC baseline and resident high-rate boundary (`RV-20260825-001`).
- [x] Implement and review a replayable width-256 QCLA memory partition with I/O, PBC scratch, high-rate surgery, and time-stamped demand (`RV-20260825-002`).
- [x] Implement and review the width-5 symbolic direct-CCZ PPM/frame trace (`RV-20260901-005`).
- [x] Classify and optimize width-5 direct-CCZ PPM candidate levels while keeping finite admission and low-rate fallback separate (`RV-20260901-006`).
- [x] Generate, independently replay, and review one overview plus nine width-5 direct-CCZ PPM audit panels (`T-20260901-008`, `RV-20260901-007`).

### Active

- [ ] Reuse the direct-CCZ PPM compiler for IP-QCLA without the seven-T route (`T-20260901-009`, now `READY`).
- [ ] Add factory service, finite buffer, routing, and backlog to the width-256 QCLA T-demand series.
- [ ] Close the reviewed AutoCCZ adapter's (`RV-20260901-001`) nine missing and one distance-incompatible service fields before scheduling.

### Still required for the full Month-1 goal

- [ ] Controlled ripple-carry adder.
- [ ] Controlled carry-lookahead addition and backend lowering of the reviewed uncontrolled prefix DAG.
- [ ] Unary lookup.
- [ ] Processor-capacity partitioner.
- [ ] Integrate memory load/store with bridge, routing, and inter-block PPM resources in one scheduler.
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
