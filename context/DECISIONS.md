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

## D-0008: Keep J300 strict evidence separate from schedule sensitivity

- Status: ACCEPTED (`RV-20260815-007` approved 2026-08-15)
- Date: 2026-08-15
- Decision: Store timing and added-space evidence independently, reject every used `CHECK` entry in strict mode, and permit high-rate J300 surgery only for the source-supported exact ten-XX batch with pairwise-disjoint supports and ten distinct live scratch slots.
- Rationale: Tables II--IV report more finite-size space constructions than operation durations, and average decoder latency is not a deterministic feed-forward bound. A precise schedule under substituted times must not be mistaken for an executable runtime.
- Consequences: `E-20260815-003` is a `CHECK` sensitivity schedule. Its zero high-rate hits for Gidney widths 2/4/16/32 and 2,074 known-component physical-qubit peak are reproducible but do not establish wall-clock time or total machine size.

## D-0009: Add memory I/O as a source-pinned overlay and preserve transfer semantics

- Status: ACCEPTED (`RV-20260823-001` approved 2026-08-23)
- Date: 2026-08-23
- Decision: Adapt the reviewed `runtime-metadata-benchmark` memory-I/O contracts at commit `75a6e83d5acde37f0987ab867352ee8b2c6afd10` into a separate overlay referencing QEC-neutral DAG source operations. Keep memory--processor teleportation moves distinct from future Bell carry teleportation. Apply scalable Belady placement only after the adaptive-PBC event order is selected in this bounded cycle.
- Rationale: The existing DAG already preserves circuit causality, while the old implementation supplies reviewed value-origin, memory/occupancy, partition, and replay semantics. A separate overlay avoids changing DAG schema v1 and prevents a fixed-order I/O policy from being mistaken for a parallel-DAG optimizer.
- Consequences: Widths 2--4 admit an exact partition reference; larger PBC traces receive a deterministic fixed-order heuristic upper bound. One-round transfer timing and no-overlap assumptions remain `CHECK`, strict mode rejects them, and later teleportation-ripple/QCLA work must introduce separate communication events and joint scheduling if required.

## D-0010: Represent Bell carry teleportation as a separate acyclic lifecycle

- Status: ACCEPTED (`RV-20260824-001` approved 2026-08-24)
- Date: 2026-08-24
- Decision: Record each adjacent carry bridge as Bell-pair preparation, speculative receiver use, split `XX`/`ZZ` Bell components, carrier rebind, and classical reaction. Keep these carriers and resources separate from processor-memory load/store semantics. Permit exact-ten-disjoint-`XX` batching only in a normalized `CHECK` sensitivity adapter, with strict execution rejected.
- Rationale: The source's “back in time” description is a teleportation construction, not an acausal dependency. Separating the lifecycle exposes carrier ownership, Bell-measurement throughput, and demand bursts without importing incompatible HGP, active-volume, J300, or memory-I/O timing.
- Consequences: `E-20260824-001` can compare dependency depth with finite lane sensitivity and independently replay bridge ownership. It cannot establish a QEC-native runtime, physical-qubit count, full Figure-6 phase equivalence, or memory/bridge joint schedule.

## D-0011: Preserve QCLA prefix structure before backend lowering

- Status: ACCEPTED (`RV-20260824-003` approved 2026-08-24)
- Date: 2026-08-24
- Decision: Admit Draper et al.'s in-place, no-carry-in addition modulo `2^n` as a separate architecture-neutral trace. Retain its `P/G/C/P^-1` source rounds, bounded-fan-out layer overlaps, exact logical supports, and reusable prefix-ancilla epochs before selecting PBC, surgery, memory, or factory implementations.
- Rationale: A scalar logarithmic-depth formula hides the width and burst structure that determines whether an FTQC backend can realize the algorithmic parallelism. The selected register contract also matches the existing uncontrolled modular-addition comparison without silently importing another QCLA variant.
- Consequences: `E-20260824-003` reports gate-DAG and source-layer demand only. The 40-layer width-256 result and 255-Toffoli peak are not QEC cycles or service capacity; a later adapter must lower exact supports and jointly enforce processor, memory, routing, factory, reaction, and failure constraints.

## D-0012: Use an exact seven-T CCX as the first QCLA PBC baseline

- Status: ACCEPTED (`RV-20260825-001` approved 2026-08-25)
- Date: 2026-08-25
- Decision: Expand each source QCLA Toffoli with Selinger circuit (1), preserve its exact wire order and source provenance, and compile the resulting X/CNOT/H/S/T/T-dagger primitives through the reviewed quantum-output-preserving adaptive-PBC layer. Keep direct CCZ injection as an `OPEN` comparator.
- Rationale: A source-pinned exact decomposition gives auditable Pauli supports and resource-state demand without assuming a direct CCZ factory or treating source-layer depth as backend execution time. The ancilla-free form avoids silently changing the resident-capacity comparison.
- Consequences: Width 256 has a reproducible 17,206-T-state structural demand but fails the fully resident J300 slot inequality before scheduling. Smaller widths can test real ten-XX readiness, while all finite schedule rounds remain `CHECK` until native timing, memory, routing, and factory contracts are supplied.

## D-0013: Separate QCLA clean epochs from memory input/output values

- Status: ACCEPTED (`RV-20260825-002` approved 2026-08-26)
- Date: 2026-08-26
- Decision: Treat `A/B` data as memory input/inout values, split every QCLA source ancilla by its reviewed clean reuse epoch, and permit live epochs to spill without extending the Gidney generated-temporary contract. Select a deterministic adaptive-PBC order with relaxed capacity, then call only the independently replayed 60-slot placement/timing overlay executable under the stated sensitivity assumptions.
- Rationale: QCLA clean workspace is neither a strict memory input nor a Gidney temporary that must remain processor-resident for its full lifetime. An explicit epoch origin prevents free copies and stale-state carryover while allowing width 256 to be evaluated without pretending its 1,007 source values are simultaneously resident.
- Consequences: `E-20260825-002` is a fixed-order realizable upper bound, not a placement optimum. Clean allocation/release, native operations, and transfer durations remain `CHECK`; the emitted T-demand timeline has no factory service, buffer, routing, or stalls.

## D-0014: Start the direct-CCZ high-rate QCLA study with a clean out-of-place workload

- Status: ACCEPTED (human-directed planning decision; record cross-reviewed and approved as `RV-20260831-001` on 2026-08-31)
- Date: 2026-08-31
- Decision: Use a clean modulo-\(2^n\), out-of-place QCLA as the first workload for the direct \(|CCZ\rangle\)-injection and high-rate-surgery study. Keep direct CCZ injection separate from the seven-\(T\) PBC path. Study the carry-status network first as an isolated prefix diagnostic and the in-place QCLA only as a later cleanup differential under the same native-operation contract.
- Rationale: The OOP trace preserves the two inputs and exposes forward prefix parallelism without conflating it with modular reduction or reversible cleanup. At \(n=256\), its source CCX demand/depth are half those of the corresponding in-place trace while fully resident source-value counts are comparable. This selects a workload; it does not claim that a high-rate backend realizes source parallelism.
- Consequences: Direct CCZ PPM/injection semantics, correction dependencies, factory/buffer supply, ports, routing, decoding, and failure budget must be source-pinned before runtime is reported. Initial schedules must retain conservative reaction barriers and outcome/frame-tracked reaction frontiers as distinct assumptions. Results must separate source critical depth from scheduled makespan and must not infer CCZ-batch capacity from an XX-only demonstration.
