# AI handoff

Last updated: 2026-08-31
From: claude
To: human and codex

## Current objective

`T-20260831-002` completed the first bounded cycle proposed by the reviewed
direct-CCZ plan. It generated and replay-validated a clean out-of-place
modulo-\(2^{256}\) QCLA trace with 1,229 Toffolis, 766 CNOTs, 20 source layers,
240 clean prefix-scratch values, and 1,008 fully resident source values. These
are architecture-neutral circuit quantities, not runtime.

The same cycle audited the pinned direct-CCZ and high-rate sources into a
machine-readable capability record. The sources establish a six-PPM
single-injection skeleton and a separate ten-CCZ/120-cycle factory observation,
but not the exact outcome-to-correction map or a finite high-rate direct-CCZ
backend. The adapter therefore rejects before emitting any source-qualified
event. Implementation commit `deebfc4` is `RV-20260831-002` `APPROVED`
(Claude review, 2026-08-31). The reviewer wrote an independent from-scratch
classical-reversible simulator (bypassing the repository's own
`replay_oop_qcla`) and confirmed every closed-form count and the fail-closed
capability/adapter logic; see `coordination/reviews/T-20260831-002.md` for
the complete finding list. The `OPEN` capability conclusion itself is
unchanged by the review -- the exact correction map and finite high-rate
backend remain absent from the literature.

`T-20260825-002` converted the reviewed width-256 QCLA adaptive-PBC trace from
a resident-capacity rejection into an independently replayed, fixed-order
60-slot J300 memory schedule. The width-256 ten-scratch high-rate policy
selects 1,576 exact-ten-XX batches. Under the explicitly `CHECK`
one-lane/one-round/no-overlap profile it takes 2,420,527 rounds, 169,260
(6.54%) below one-scratch serial despite 7,433 more reloads. This is not
executable time. The complete shifted T-demand trace sums to 17,206 but has
no factory service, buffer, routing, or stalls.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `coordination/reviews/T-20260831-002.md`
- `docs/DIRECT_CCZ_CAPABILITY_AND_OOP_QCLA_CONTRACT.md`
- `configs/architectures/direct_ccz_high_rate_capability_v1.yaml`
- `experiments/runs/T-20260831-002/summary.json`
- `experiments/runs/T-20260831-002/direct_ccz_capability_gap.json`
- `coordination/reviews/T-20260825-002.md`
- `docs/QCLA_MEMORY_IO_CONTRACT.md`
- `docs/QCLA_PBC_LOWERING_CONTRACT.md`
- `configs/architectures/qcla_j300_memory_io_v1.yaml`
- `experiments/runs/T-20260825-002/summary.json`
- `experiments/runs/T-20260825-002/qcla_width256_t_state_demand.json`
- `context/RESULT_LEDGER.md`
- `docs/HIGH_RATE_QCLA_DIRECT_CCZ_RESEARCH_CYCLE.md`
- `coordination/reviews/T-20260831-001.md`

## Next concrete action

1. Close the exact single-CCZ outcome-to-CZ/Pauli correction map from a pinned primary circuit. Only then may source Toffolis become typed direct-CCZ events.
2. Pin a finite high-rate backend covering reaction, decoder, ports, capacity, routing, delivery, buffer, storage, and logical error before constructing conservative or frame-tracked schedules.
3. Add factory service, finite buffer, routing, and backlog to the width-256
   adaptive-PBC T-demand series as a separate, comparison track; report stalls
   separately from the current ideal-supply timeline.
4. Human records the `T-BOOT-001` full-ECDLP circuit choice before project-wide
   `T-BOOT-002` is claimed.

## Known risks

- The clean QCLA source-ancilla allocation/release boundaries are validated
  from source reuse epochs, but their physical preparation/reset/routing time
  remains `CHECK` and adds no separate duration in this cycle.
- The capacity-relaxed adaptive-PBC pass selects an order only. The second pass
  enforces 60 slots, but the order and Belady retention are heuristic and are
  neither optimal nor lower bounds.
- Transfer prefetch/overlap, finite memory capacity, routing, bridge occupancy,
  decoder throughput, logical failure, and wall-clock conversion are absent.
- The QCLA is uncontrolled in-place addition modulo `2^n`, without carry-in or
  overflow; it is not yet the controlled arithmetic needed by scalar
  multiplication.
- Direct CCZ injection may dominate the seven-T baseline in space or time.
- The high-rate source presently supports a finite XX PPM demonstration, not an admitted direct-CCZ batch; this is an explicit input gap, not a scaling assumption.
- The clean OOP trace is validated on computational-basis replay and structural identities; it is not an independent coherent-phase proof of the full arithmetic circuit.
- The capability record's exact correction map is intentionally null. The synthetic complete map in tests verifies software typing only and must not be promoted to evidence.
- Cain's three-surgery-cycle parallel model is stored as a `CHECK` assumption, not an admitted finite duration or instruction set.
- The older Gidney integration suite retains two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. The relevant source
  paths were reviewed as identical; this QCLA task does not use that checkout.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; `T-20260831-002` is `RELEASED` (reviewed and approved). No task currently holds an active `REVIEW`/`ACTIVE` lock.
