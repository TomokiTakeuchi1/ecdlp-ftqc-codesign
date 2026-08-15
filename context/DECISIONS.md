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

## D-0005: Keep phase-exact Clifford+T lowering separate from Mitten gadget selection

- Status: ACCEPTED (`RV-20260815-004` approved 2026-08-15)
- Date: 2026-08-15
- Decision: Expand Gidney's temporary logical AND into the verified Figure 3 logical gate trace before selecting a PPM, surgery, extractor, or injection implementation.
- Rationale: The earlier four-PPM accounting coefficient is not a Pauli-support list, and a logical CNOT inside one multi-logical-qubit Mitten block is not justified as a transversal inter-block CNOT.
- Consequences: Strict scheduling rejects unresolved CNOT/H/S/T compilation. Provisional schedules remain explicitly `CHECK` and cannot establish wall-clock or physical-qubit feasibility.

## D-0006: Restrict the first Mitten high-rate rule to the directly simulated ten-XX batch

- Status: ACCEPTED (`RV-20260815-004` approved 2026-08-15)
- Date: 2026-08-15
- Decision: Configuration v1 selects high-rate surgery only for ten ready pairwise-disjoint XX measurements; other supported Pauli families fall back to reusable seed surgery, and general products fall back to the full extractor.
- Rationale: The primary source directly simulates the ten-product J300 XX gadget, while the current Gidney trace exposes only single-X erase measurements.
- Consequences: The current Gidney schedules have zero high-rate hits. A later PBC compiler may change the Pauli layers, but it must generate exact supports before this rule is generalized.

## D-0007: Preserve quantum outputs through explicit adaptive teleportation

- Status: ACCEPTED (`RV-20260815-006` approved 2026-08-15)
- Date: 2026-08-15
- Decision: Compile CNOT to the Xu et al. measurement circuit and compile H/S/T/T-dagger through one-bit teleportation. Follow the Bravyi--Smith--Smolin T gadget with an adaptive I/S or I/S-dagger teleport so no unpropagated S frame is returned to the arithmetic trace.
- Rationale: The standard PBC compression theorem targets final classical output. Arithmetic subcircuits return live quantum values, so compiler ancillas, adaptive measurements, logical-carrier moves, and the remaining frame must stay explicit.
- Consequences: One reusable scratch slot lowers the serialized J300 slot-count boundary from source-only width 59 to width 58. Exact Pauli supports now exist, but strict runtime remains blocked by state-preparation, Z/ZZ/ZX, reaction, conditional-CZ, and scheduler evidence.
