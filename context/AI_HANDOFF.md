# AI handoff

Last updated: 2026-08-15
From: claude
To: human and codex

## Current objective

All three pending Codex submissions (`T-20260811-001`, `T-20260811-002`, `T-20260815-001`) are now Claude-reviewed and `APPROVED`. Continue the human-owned canonical circuit decision and three-month architecture program without prematurely combining incompatible assumptions.

## Read first

- `context/PROJECT_CHARTER.md`
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

## Next concrete action

1. Human records the `T-BOOT-001` choice: recommended Schrottenloher primary plus Luo v2 contrast, or exact-first Luo v2 after resolving its checks. This is the only remaining blocker before `T-BOOT-002` (project-wide trace schema) can be claimed.
2. Non-blocking: whoever next touches `docs/GIDNEY_DAG_CONTRACT.md` should add one sentence to "Temporary-AND erase expansion" noting that both nodes produced from a `temporary_and_erase` split retain full control-value memory/occupancy support by design (continuous residency, not two independent loads), so a future `T-BOOT-005` memory-I/O model is written against a diff/replacement-policy accounting rather than a per-node sum. See `coordination/reviews/T-20260815-001.md` for the full reasoning.
3. After `T-BOOT-001` is decided, select and evidence the first executable temporary-AND/mitten lowering for the Gidney adapter; do not reinterpret the sequential four-PPM accounting coefficient as an actual Pauli-support list.
4. Pin controlled-adder, unary-lookup, and carry-lookahead contracts before generalizing the bounded adapter schema into project-wide `T-BOOT-002`.

## Known risks

- Circuit conventions may differ across papers and codebases.
- Schrottenloher's primary candidate is approximate and its fast test is not full gate-level simulation.
- Luo v2 contains an internal `2^30.88` versus `2^30.63` full-count inconsistency; Table 6 plus Equation (8) supports `2^30.88` (independently reconfirmed during review).
- Neither artifact's local tests completed within the bounded verification window, so no published count is marked reproduced.
- The newly registered qLDPC/qLTC papers are only abstract-triaged; finite-size code, gadget, decoder, hardware, and factory assumptions are not yet normalized.
- Gidney now has a reviewer-reproduced width-256 structural DAG regression, but no QEC-native lowering, processor partition, or runtime result. QCLA remains a source-level candidate; Kim et al. 2026/106 is only abstract-triaged.
- Logical parallelism may be overestimated if conflicts and routing are omitted.
- Average factory rate may hide burst-induced stalls.
- Memory traffic can dominate a small-processor architecture; see the erase-split occupancy-duplication note above for a concrete case to watch when `T-BOOT-005` is implemented.

## Files currently safe to modify

Check `coordination/WORK_LOCKS.md`; the reviewed tasks' locks are now `RELEASED`.
