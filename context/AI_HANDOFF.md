# AI handoff

Last updated: 2026-08-24
From: claude
To: human and codex

## Current objective

All eleven Codex submissions to date are Claude-reviewed and `APPROVED`,
including `T-20260824-003` (`RV-20260824-003`): the source-pinned Draper
in-place QCLA DAG needed before any high-rate-surgery or memory timing is
assigned.

The width-256 QCLA trace has 2,458 Toffolis, 1,019 CNOTs, 510 NOTs, 495
logical circuit ancillas, 40 source algorithmic layers, and a peak source-layer
demand of 255 Toffolis. These are circuit quantities, not executable QEC
cycles, factory service, wall-clock time, or a physical-qubit total.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `coordination/reviews/T-20260824-003.md`
- `docs/QCLA_DAG_CONTRACT.md`
- `literature/notes/algorithms/draper_et_al_2006_qcla.md`
- `configs/circuits/qcla_inplace_mod2n_v1.yaml`
- `experiments/runs/T-20260824-003/summary.json`
- `experiments/runs/T-20260824-003/qcla_width256_toffoli_demand.json`
- `docs/TELEPORTATION_BRIDGE_RIPPLE_CONTRACT.md`
- `docs/MEMORY_IO_EXECUTION_CONTRACT.md`
- `docs/PBC_CQLU_LOWERING_CONTRACT.md`
- `docs/J300_PBC_SCHEDULING_CONTRACT.md`

## Next concrete action

1. Claim a separate cycle that source-pins one QCLA Toffoli or prefix
   primitive lowering to exact Pauli/resource-state supports. Compare
   source demand with executable high-rate eligibility under finite processor
   and memory resources; do not reuse source-layer depth as backend time.
2. Human records the `T-BOOT-001` full-ECDLP choice. This remains the human-
   owned blocker before project-wide `T-BOOT-002` is claimed.
3. In parallel research planning, continue pinning native J300/HGP operation,
   bridge, routing, reaction, and memory-transfer contracts.

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
- High-rate eligibility has not been derived from the QCLA gate supports; no
  result claims that an entire Toffoli layer maps to one supported surgery
  batch.
- Average factory rate can hide the source demand bursts; retry, buffer,
  routing, and backlog are all absent.
- The older Gidney integration suite still has two known checkout-pin failures:
  expected sibling HEAD `8c16388`, observed `75a6e83`. Relevant source paths
  were previously reviewed as identical; the QCLA task does not use that
  checkout.
- Strict J300 duration evidence remains incomplete for preparation,
  Z/ZZ/ZX/full extraction, reaction, conditional CZ, and memory transfer.
- The Obsidian dashboard is manually curated and must follow canonical records.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all tasks' locks are now `RELEASED`.
