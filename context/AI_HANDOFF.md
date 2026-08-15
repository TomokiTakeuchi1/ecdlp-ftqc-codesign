# AI handoff

Last updated: 2026-08-15
From: claude
To: human and codex

## Current objective

All five Codex submissions to date (`T-20260811-001`, `T-20260811-002`, `T-20260815-001`, `T-20260815-002`, `T-20260815-003`) are now Claude-reviewed and `APPROVED`. `T-20260815-002` remains intentionally a conditional single-processor prototype and does not close the human-owned canonical ECDLP decision or the Month-1 Memory--Processor scope. `T-20260815-003`'s Obsidian Research Hub is a manually curated presentation layer; canonical project records remain authoritative and the Hub was resynchronized to the post-review state as part of `RV-20260815-005`.

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

## Next concrete action

1. Human records the `T-BOOT-001` full-ECDLP choice; this is the only remaining human-owned blocker before `T-BOOT-002` (project-wide trace schema) can be claimed.
2. Select and phase-verify one explicit Pauli-based CQLU compilation for intra-block CNOT/H/S/T, including its logical ancilla, adaptive-measurement, and Pauli/Clifford-frame contract. This is the blocker for a strict Mitten runtime. `coordination/reviews/T-20260815-002.md` records a confirmed-correct reference point: the phase-exact Figure-3 AND-compute trace already matches the pinned source's exhaustively verified circuit gate-for-gate, so the CQLU compilation only needs to cover CNOT/H/S/T/T-dagger/measurement-frame primitives, not re-derive the AND gadget itself.
3. Recompute the capacity boundary after CQLU ancillas are included; width 59 currently saturates all 60 source-residency slots and may not remain executable.
4. Non-blocking documentation follow-up: cite `runtime_metadata_benchmark.gidney.coherent._apply_figure3_compute`/`verify_coherent_adder` in `docs/MITTEN_GIDNEY_LOWERING_CONTRACT.md` as the specific cross-checked source of the Figure-3 gate sequence (currently only cited at the paper level).
5. Controlled-adder, unary-lookup, and carry-lookahead contracts are pinned before project-wide schema generalization.

## Known risks

- Circuit conventions may differ across papers and codebases.
- Schrottenloher's primary candidate is approximate and its fast test is not full gate-level simulation.
- Luo v2 contains an internal `2^30.88` versus `2^30.63` full-count inconsistency; Table 6 plus Equation (8) supports `2^30.88` (independently reconfirmed during review).
- Neither artifact's local tests completed within the bounded verification window, so no published count is marked reproduced.
- The newly registered qLDPC/qLTC papers are only abstract-triaged; finite-size code, gadget, decoder, hardware, and factory assumptions are not yet normalized.
- Gidney now has a reviewer-reproduced width-256 structural DAG regression, but no QEC-native lowering, processor partition, or runtime result. QCLA remains a source-level candidate; Kim et al. 2026/106 is only abstract-triaged.
- The new J300 schedule is a `CHECK` sensitivity result, not a QEC-native runtime: CNOT/H/S/T use provisional 14-round placeholders with unknown gadget space, and setup/readout/reconfiguration are not included.
- Direct Gidney erase measurements are single-X, whereas backend v1 only recognizes the directly simulated ten-disjoint-XX high-rate gadget; the measured high-rate hit count is therefore zero until a verified PBC compiler exposes different supports.
- Logical parallelism may be overestimated if conflicts and routing are omitted.
- Average factory rate may hide burst-induced stalls.
- The Obsidian dashboard is manually curated and can drift unless canonical records are updated first and the linked maintenance checklist is followed; four spots drifted one review-cycle behind within this same session and were resynchronized during `RV-20260815-005`.
- Memory traffic can dominate a small-processor architecture; see the erase-split occupancy-duplication note above for a concrete case to watch when `T-BOOT-005` is implemented.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; all reviewed tasks' locks are now `RELEASED`.
