# AI change log

| Date | Agent | Task | Summary | Commit/review |
|---|---|---|---|---|
| 2026-08-11 | codex | T-20260811-001 | Compared primary-source ECDLP-256 circuit candidates; recommended pinned Schrottenloher primary and Luo v2 dynamic contrast; documented count scopes, semantic caveats, and non-reproduced test status | no commit; `RV-20260811-001` |
| 2026-08-11 | codex | T-20260811-002 | Registered nine unique user-specified FTQC papers with versioned local PDFs, hashes, BibTeX, reading-queue rows, and structured triage notes | no commit; `RV-20260811-002` |
| 2026-08-15 | codex | T-20260811-002 | Extended the corpus with five requested arithmetic/ECDLP PDFs; added Gidney, QCLA, and Kim et al. metadata and triage notes; refreshed hashes and review scope | no commit; `RV-20260811-002` |
| 2026-08-15 | codex | T-20260815-001 | Added a versioned QEC-neutral DAG and a read-only adapter for the pinned Gidney oracle; exposed X-basis erase measurements and conditional-CZ feed-forward; added deterministic fixtures and width-256 structural regression | no commit (unborn repository); `RV-20260815-003` |
| 2026-08-15 | claude | T-20260811-001 | Reviewed canonical-circuit decision support; spot-verified Schrottenloher/Luo/Babbush arXiv metadata directly and reconfirmed the Luo v2 `2^30.88` arithmetic | no commit; `RV-20260811-001` APPROVED |
| 2026-08-15 | claude | T-20260811-002 | Reviewed the 14-PDF literature corpus; spot-verified 3 records against arXiv, confirmed no duplicate entries and correct classification/evidence labels | no commit; `RV-20260811-002` APPROVED |
| 2026-08-15 | claude | T-20260815-001 | Reviewed the Gidney DAG adapter; hand-traced the width-2 fixture to confirm edge/critical-path counts, verified the erase gadget against Gidney (2018), and reproduced pytest (13 passed)/ruff/mypy | no commit; `RV-20260815-003` APPROVED with one non-blocking documentation suggestion |
