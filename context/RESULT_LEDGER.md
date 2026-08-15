# Result ledger

| Result ID | Status label | Task | Summary | Inputs/config | Commit | Validation | Report |
|---|---|---|---|---|---|---|---|
| R-20260815-001 | NUMERICAL | T-20260815-001 | Pinned Gidney width 2/3/4/256 oracles produce respectively 8/19/30/2,802 expanded semantic nodes, 8/25/42/4,326 causal edges, and unit-node critical paths 6/14/22/2,038; erase measurements produce 1/2/3/255 explicit classical results | External oracle schema v3; mapping v4; source `8c1638805e7246c30117a0251526661039df1369`; DAG schema v1; no QEC backend or Factory | repository unborn; working-tree implementation | 13 pytest tests; Ruff; strict mypy; deterministic fixture regeneration; pending `RV-20260815-003` | `docs/GIDNEY_DAG_CONTRACT.md` |

A result enters this ledger only when it is reproducible or clearly marked otherwise.
