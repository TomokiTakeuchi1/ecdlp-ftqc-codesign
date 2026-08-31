# AI handoff

Last updated: 2026-08-31
From: codex
To: claude and human

## Current objective

`T-20260831-003` implementation commit `75effd5` awaits `RV-20260831-003`.
Litinski--Nickerson Figure 14(a) now supplies the exact
single-event conditional-CZ/post-H Pauli map under the explicit measurement
convention `0 -> +1`, `1 -> -1`. A verifier that imports neither the capability
nor compiler reconstructs the six-qubit projector channel and finds all 64
branches nonzero at probability `1/64`, with maximum probability error
`2.2551405187698492e-17` and zero operator Frobenius residual at floating-point
precision. The real capability therefore admits isolated event lowering.

The width-256 clean OOP-QCLA lowers to 1,229 direct-CCZ injection events,
7,374 PPM/outcome records, 3,955 preserved source dependencies, and 766
pass-through CNOTs. Event-trace schema v2 explicitly remains
`complete_native_schedule=false`. High-rate admission remains false: finite
timing, error, decoder, reaction, port, capacity, routing, factory delivery,
buffer, and storage evidence is still absent. No runtime or physical-resource
result was created.

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
- `coordination/reviews/T-20260831-003.md`
- `docs/DIRECT_CCZ_SINGLE_EVENT_CONTRACT.md`
- `configs/architectures/direct_ccz_single_event_capability_v1.yaml`
- `experiments/runs/T-20260831-003/summary.json`
- `experiments/runs/T-20260831-003/direct_ccz_injection_channel_verification.json`
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

1. Claude cross-reviews `T-20260831-003`, independently checking the Figure 14(a) convention/map, all-branch reconstruction, event substitution/dependencies, fail-closed admission split, tests, and deterministic artifacts.
2. After approval, pin one finite high-rate backend covering reaction, decoder, ports, capacity, routing, delivery, buffer, storage, and logical error before constructing conservative or frame-tracked schedules.
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
- The legacy T-20260831-002 capability record intentionally remains null and fail-closed. Only the new Figure-14-qualified configuration admits isolated events.
- The branch reconstruction is `NUMERICAL`, not a formal proof, and it does not establish any finite high-rate architecture.
- Cain's three-surgery-cycle parallel model is stored as a `CHECK` assumption, not an admitted finite duration or instruction set.
- The older Gidney integration suite retains two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. The relevant source
  paths were reviewed as identical; this QCLA task does not use that checkout.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; `T-20260831-003` holds a `REVIEW` lock on
the listed files until Claude completes `RV-20260831-003`.
