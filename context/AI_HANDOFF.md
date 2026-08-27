# AI handoff

Last updated: 2026-08-26
From: claude
To: human and codex

## Current objective

All thirteen Codex submissions to date are Claude-reviewed and `APPROVED`,
including `T-20260825-002` (`RV-20260825-002`). It converts the reviewed
width-256 QCLA adaptive-PBC trace from a resident-capacity rejection into an
independently replayed, fixed-order 60-slot J300 memory schedule.

The width-256 ten-scratch high-rate policy selects 1,576 exact-ten-XX batches.
Under the explicitly `CHECK` one-lane/one-round/no-overlap profile it takes
2,420,527 rounds, 169,260 (6.54%) below one-scratch serial despite 7,433 more
reloads. This is not executable time. The complete shifted T-demand trace sums
to 17,206 but has no factory service, buffer, routing, or stalls.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `coordination/reviews/T-20260825-002.md`
- `docs/QCLA_MEMORY_IO_CONTRACT.md`
- `docs/QCLA_PBC_LOWERING_CONTRACT.md`
- `configs/architectures/qcla_j300_memory_io_v1.yaml`
- `experiments/runs/T-20260825-002/summary.json`
- `experiments/runs/T-20260825-002/qcla_width256_t_state_demand.json`
- `context/RESULT_LEDGER.md`

## Next concrete action

1. Add factory service, finite buffer, routing, and backlog to the emitted
   width-256 T-demand series; report stalls separately from the current ideal-
   supply timeline.
2. Investigate the direct-CCZ comparator left `OPEN` in `D-0012`, then extend
   the preferred arithmetic to a controlled adder.
3. Human records the `T-BOOT-001` full-ECDLP circuit choice before project-wide
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
- The older Gidney integration suite retains two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. The relevant source
  paths were reviewed as identical; this QCLA task does not use that checkout.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all tasks' locks are now `RELEASED`.
