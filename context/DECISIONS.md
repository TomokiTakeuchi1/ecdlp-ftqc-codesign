# Decision log

## D-0001: Python package structure

- Status: ACCEPTED
- Date: YYYY-MM-DD
- Decision: Use a Python 3.11+ package with architecture-independent circuit semantics and separate backend schedulers.
- Rationale: This prevents architecture assumptions from leaking into the canonical circuit representation.
- Consequences: Backend-specific transformations must be explicit and testable.

## D-0002: Cross-agent review

- Status: ACCEPTED
- Date: YYYY-MM-DD
- Decision: Codex and Claude Code may implement tasks independently, but every nontrivial implementation should be reviewed by the other agent before being treated as accepted.
- Rationale: The project mixes software correctness and subtle scientific assumptions.
- Consequences: Work locks and review records are mandatory.

## D-0003: Use the verified Gidney oracle JSON as a read-only frontend boundary

- Status: ACCEPTED (`RV-20260815-003` approved 2026-08-15)
- Date: 2026-08-15
- Decision: Consume `runtime-metadata-benchmark` commit `8c1638805e7246c30117a0251526661039df1369` through canonical oracle schema v3 rather than copying its Gidney generator into this repository.
- Rationale: The external implementation already supplies deterministic generation, logical-value lifetimes, memory and occupancy supports, and phase-verification provenance. A serialized versioned boundary prevents the two repositories from silently diverging.
- Consequences: Small-width fixtures record exact source hashes. The width-256 oracle is generated from the pinned checkout instead of checking in a 13 MB duplicate. Artifact generation must verify both the source commit and relevant-path worktree cleanliness.

## D-0004: Separate Gidney erase measurement from its conditional Clifford correction

- Status: ACCEPTED (`RV-20260815-003` approved 2026-08-15)
- Date: 2026-08-15
- Decision: Expand each `temporary_and_erase` into an X-basis measurement node and a conditional-CZ/Clifford-frame-update node connected by an explicit classical-result edge.
- Rationale: Measurement latency and feed-forward must remain visible to later QEC backends. Treating source-list adjacency as causality would also destroy valid circuit parallelism.
- Consequences: The measured temporary may be released after measurement without waiting for the control-frame update, while later operations on either control depend on that update. QEC gadget, decoder, memory, and shared-resource constraints remain separate later-layer records.
