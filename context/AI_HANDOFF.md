# AI handoff

Last updated: 2026-08-15
From: claude
To: human and codex

## Current objective

All six Codex submissions to date are now Claude-reviewed and `APPROVED`, including `T-20260815-004` (`RV-20260815-006`): a quantum-output-preserving adaptive PBC trace that replaces the logical CNOT/H/S/T placeholders, verified on all tested nonzero gadget branches, accounting for one reusable compiler scratch. Width 58 passes the serialized J300 60-slot check and width 59 does not. Strict runtime remains unavailable because native state-preparation, Z/ZZ/ZX, reaction, conditional-CZ, and adaptive scheduling contracts are still `CHECK`.

## Read first

- `context/PROJECT_CHARTER.md`
- `Research Hub/Home.md`
- `context/STATUS.md`
- `context/TASKS.md`
- `coordination/PROTOCOL.md`
- `docs/CANONICAL_CIRCUIT_DECISION.md`
- `coordination/reviews/T-20260811-001.md`
- `literature/papers/INDEX.md`
- `literature/READING_QUEUE.md`
- `coordination/reviews/T-20260811-002.md`
- `docs/GIDNEY_DAG_CONTRACT.md`
- `coordination/reviews/T-20260815-001.md`
- `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md`
- `coordination/reviews/T-20260815-002.md`
- `experiments/runs/T-20260815-002/summary.json`
- `docs/PBC_CQLU_LOWERING_CONTRACT.md`
- `experiments/runs/T-20260815-004/summary.json`
- `coordination/reviews/T-20260815-004.md`

## Next concrete action

1. Human records the `T-BOOT-001` full-ECDLP choice; this is the only remaining human-owned blocker before `T-BOOT-002` (project-wide trace schema) can be claimed.
2. Pin J300 implementations and durations for logical stabilizer/magic preparation, Z/ZZ/ZX measurements, reaction, and conditional CZ; then resource-schedule the adaptive PBC trace and reassess exact-ten-XX high-rate batching. Width 58/59 is currently only a serialized one-scratch slot-count result, not a scheduled runtime.
3. Controlled-adder, unary-lookup, and carry-lookahead contracts are pinned before project-wide schema generalization.

The documentation follow-up repeated across `RV-20260815-004` and `RV-20260815-006` (citing `runtime_metadata_benchmark.gidney.coherent._apply_figure3_compute`/`verify_coherent_adder` in `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md`) is now done; Claude applied it directly after the second review, since it was a pure documentation addition with no implementation or scope change.

## Known risks

- Circuit conventions may differ across papers and codebases.
- Schrottenloher's primary candidate is approximate and its fast test is not full gate-level simulation.
- Luo v2 contains an internal `2^30.88` versus `2^30.63` full-count inconsistency; Table 6 plus Equation (8) supports `2^30.88` (independently reconfirmed during review).
- Neither artifact's local tests completed within the bounded verification window, so no published count is marked reproduced.
- The newly registered qLDPC/qLTC papers are only abstract-triaged; finite-size code, gadget, decoder, hardware, and factory assumptions are not yet normalized.
- Gidney now has a reviewer-reproduced width-256 structural DAG regression, but no QEC-native lowering, processor partition, or runtime result. QCLA remains a source-level candidate; Kim et al. 2026/106 is only abstract-triaged.
- The old J300 schedule is a `CHECK` sensitivity result, not a QEC-native runtime. The now-approved adaptive PBC trace removes the semantic CNOT/H/S/T blocker (verified correct via independent formula re-derivation and gadget-level Clifford-conjugation checks) but still lacks native preparation, Z/ZZ/ZX, reaction, conditional-CZ, setup/readout, and reconfiguration costs.
- The adaptive trace exposes many XX measurements, but no high-rate hit count is reported yet: exact-ten batching must be recomputed under readiness, scratch, operation-zone, and Pauli-support conflicts.
- Logical parallelism may be overestimated if conflicts and routing are omitted.
- Average factory rate may hide burst-induced stalls.
- The Obsidian dashboard is manually curated and can drift unless canonical records are updated first and the linked maintenance checklist is followed; four spots drifted one review-cycle behind within this same session and were resynchronized during `RV-20260815-005`.
- Memory traffic can dominate a small-processor architecture; see the erase-split occupancy-duplication note above for a concrete case to watch when `T-BOOT-005` is implemented.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all tasks' locks are now `RELEASED`.
