# AI handoff

Last updated: 2026-08-25
From: claude
To: human and codex

## Current objective

All twelve Codex submissions to date are Claude-reviewed and `APPROVED`,
including `T-20260825-001` (`RV-20260825-001`): it lowers the reviewed Draper
QCLA through a pinned exact seven-T CCX and the reviewed adaptive-PBC/J300
sensitivity layers.

Width 256 expands to 40,857 logical primitives and 17,206 T-state demands but
needs 1,008 logical slots with one compiler scratch, so k=60 J300 rejects the
fully resident model before scheduling. Resident widths 11 and 14 expose seven
and nine exact-ten-XX batches, but their finite rounds remain `CHECK`.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `coordination/reviews/T-20260824-003.md`
- `coordination/reviews/T-20260825-001.md`
- `docs/QCLA_DAG_CONTRACT.md`
- `docs/QCLA_PBC_LOWERING_CONTRACT.md`
- `experiments/runs/T-20260825-001/summary.json`
- `experiments/runs/T-20260825-001/capacity_boundaries.json`
- `literature/notes/algorithms/draper_et_al_2006_qcla.md`
- `configs/circuits/qcla_inplace_mod2n_v1.yaml`
- `experiments/runs/T-20260824-003/summary.json`
- `experiments/runs/T-20260824-003/qcla_width256_toffoli_demand.json`
- `docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT.md`
- `docs/MEMORY_IO_EXECUTION_CONTRACT.md`
- `docs/PBC_CQLU_LOWERING_CONTRACT.md`
- `docs/J300_PBC_SCHEDULING_CONTRACT.md`

## Next concrete action

1. Claim a memory-partition cycle for width-256 QCLA and jointly schedule
   I/O, PBC scratch, high-rate surgery, and factory demand; continue pinning
   native J300/HGP operation, routing, reaction, and transfer contracts.
2. Human records the `T-BOOT-001` full-ECDLP choice. This remains the human-
   owned blocker before project-wide `T-BOOT-002` is claimed.
3. Investigate the direct-CCZ-injection comparator left `OPEN` in `D-0012`,
   since it may dominate the seven-T route in space or time.

## Known risks

- The QCLA cycle covers only uncontrolled in-place addition modulo `2^n`, with
  no carry-in or overflow. Controlled QCLA remains unresolved for scalar
  multiplication.
- The width-256 255-Toffoli burst may be sharply serialized by operation-zone,
  scratch/carrier, routing, memory, or factory constraints.
- The 495 QCLA ancillas are source-level logical values. Processor residency
  and resulting load/store traffic have not been optimized or replayed.
- Small-width exhaustive basis replay is strong for the phase-free reversible
  instruction set but remains finite numerical evidence, not a general proof.
- High-rate eligibility is now derived for the selected PBC supports at
  resident widths only; no result claims that an entire Toffoli layer maps to
  one supported surgery batch or that width 256 is executable.
- Average factory rate can hide the source demand bursts; retry, buffer,
  routing, and backlog are all absent.
- The older Gidney integration suite still has two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. Relevant source paths
  were previously reviewed as identical (re-confirmed via a direct empty
  `git diff` in review); the QCLA task does not use that checkout.
- Strict J300 duration evidence remains incomplete for preparation,
  Z/ZZ/ZX/full extraction, reaction, conditional CZ, and memory transfer.
- The Obsidian dashboard is manually curated and must follow canonical records.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all tasks' locks are now `RELEASED`.
