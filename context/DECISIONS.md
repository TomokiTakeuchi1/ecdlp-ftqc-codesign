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

## D-0015: Fail closed at the direct-CCZ capability boundary

- Status: ACCEPTED (`RV-20260831-002` approved 2026-08-31)
- Date: 2026-08-31
- Decision: Keep the clean out-of-place QCLA as an architecture-neutral X/CNOT/Toffoli trace and lower a source Toffoli to a typed direct-CCZ event only when the capability record contains an exact outcome-to-correction map with admissible evidence. Admit a finite high-rate schedule only under the strictly larger set of explicit timing, error, decoder, reaction, port, capacity, routing, delivery, buffer, and storage fields.
- Rationale: The audited sources establish a single-CCZ PPM skeleton, one concrete factory production estimate, and approximate parallelism assumptions, but not one closed finite high-rate backend. Separating event admission from batch-schedule admission prevents an XX- or T-injection construction, an average factory rate, or source-layer parallelism from silently becoming a direct-CCZ runtime claim.
- Consequences: The current source-qualified configuration rejects event emission and lists every missing field. Synthetic complete maps may test type/support plumbing only and cannot be cited as physical capability. The 1,229-event width-256 demand trace remains an architecture-neutral input for a later source-completion cycle.

## D-0016: Admit exact direct-CCZ single events without admitting high-rate service

- Status: ACCEPTED (`RV-20260831-003` approved 2026-08-31)
- Date: 2026-08-31
- Decision: Admit one typed direct-CCZ injection event only when the capability uses the canonical Litinski--Nickerson Figure 14(a) outcome-to-CZ/Pauli map, the explicit convention `0 -> +1` and `1 -> -1`, and an independent all-64-branch operator verification. Preserve source-gate dependencies in event-trace schema v2. Continue to reject finite high-rate scheduling unless the separate timing, error, decoder, reaction, port, capacity, routing, delivery, buffer, and storage contract closes.
- Rationale: The primary circuit diagram and an implementation-independent six-qubit projector reconstruction now agree on every measurement branch, so the single-event semantic blocker can close without inventing an architecture. A correct isolated channel does not determine whether many events can be routed, decoded, supplied, or reacted to concurrently.
- Consequences: The clean width-256 OOP-QCLA trace can emit 1,229 source-qualified injection events with exact event-local corrections and 3,955 preserved source dependencies. The resulting artifact is semantic demand only: it has no native duration, finite processor assignment, factory/buffer trajectory, physical-qubit total, failure probability, or runtime.

## D-0017: Require one compatibility domain for finite direct-CCZ admission

- Status: ACCEPTED (`RV-20260831-004` approved 2026-08-31)
- Date: 2026-08-31
- Decision: Treat the reviewed Figure 14(a) event semantics as a portable contract, but admit physical high-rate service only when every consumer, controller, processor, factory, and adapter field has source-qualified finite evidence in one compatibility domain. Preserve qualified values from other domains as explicit incompatibilities rather than substituting them.
- Rationale: The current corpus contains useful but noncomposable pieces: a finite `bb18` CCZ factory estimate, approximate Cain `P=20` consumption, finite mitten/canonical-LP T ports, finite in-situ Y injection, tricycle CCZ generation, and batched high-rate qLDPC operations. Combining their best values would create an architecture that no source constructs or validates.
- Consequences: `E-20260831-004` rejects the selected candidate with 13 missing fields and three incompatible finite factory fields, emits no schedule, and identifies a finite decoded factory-to-consumer adapter as the next evidence-producing step.

## D-0018: Admit a source-native AutoCCZ adapter separately from complete service

- Status: ACCEPTED (`RV-20260901-001` approved 2026-09-01)
- Date: 2026-09-01
- Decision: Admit the Gidney--Fowler surface-code path from one CCZ-factory output through its three delayed-choice-CZ fixup box to one Toffoli consumer as a source-native adapter. Keep source-stated physical timing as `CHECK`, and admit complete service only when the same `d1=17,d2=27` domain also supplies consumer/error, decoder, processor capacity, delivery, output buffer/storage, and integrated failure-budget evidence.
- Rationale: The primary source and official layouts close the previously absent factory-to-consumer resource-type and local-routing link without cross-architecture substitution. They do not close burst service or failure, and the official calculator's finite output-error value belongs to a different `d1=15,d2=31` factory example.
- Consequences: `E-20260901-001` admits the adapter and rejects complete service with nine missing and one incompatible field. No width-256 QCLA schedule, runtime, machine-size total, or failure result may be emitted from this configuration.

## D-0019: Preserve direct-CCZ outcomes in a canonical symbolic Clifford frame

- Status: ACCEPTED (`RV-20260901-005` approved 2026-09-01)
- Date: 2026-09-01
- Decision: Lower each OOP-QCLA CCX directly to the admitted six-PPM `|CCZ>` event, encode every correction condition in canonical algebraic normal form, and retain the resulting ordered conditional-Clifford frame across source gates and macro-layer boundaries. Keep source CNOTs explicit and implementation-neutral, and reject any Phase-A claim of a native schedule.
- Rationale: Enumerating the global measurement tree grows as `2^(6N)`, while dropping the outcomes would erase the reaction and presented-observable structure that a high-rate optimizer must respect. Canonical symbolic propagation preserves those dependencies without choosing a code or physical schedule.
- Consequences: `E-20260901-006` produces an independently replayable width-5 PPM/frame trace and no `schedule.json`. Phase B may classify candidate batches from this trace, but finite timing, routing, memory, reaction, decoder, factory, space, and failure claims remain unavailable until a compatible backend closes them.

## D-0020: Separate exact PPM candidate levels from finite native execution

- Status: ACCEPTED (`RV-20260901-006` approved 2026-09-01)
- Date: 2026-09-01
- Decision: Classify symbolic PPM pairs with exact ANF symplectic and per-index axis polynomials, allow same-axis logical overlap, and pack causally ready frontiers into unitless candidate levels. Emit a finite schedule only through both the direct-CCZ capability gate and the coherent finite-backend audit; otherwise keep the native schedule null and retain a separate singleton semantic fallback.
- Rationale: Global commutation can hide cancelling local X/Z conflicts, while support overlap can be harmless when axes agree. Neither algebraic screen establishes a code construction, and values from an incompatible factory or T/XX gadget cannot supply a direct-CCZ backend contract.
- Consequences: `E-20260901-007` may prove optimality inside its explicit logical candidate model when a construction meets an exact lower bound, but it cannot call that level count surgery depth or runtime. Measured-product rewrites and selective materialization remain unadmitted until they have exact frame/lifetime certificates and independent semantic replay.

## D-0021: Make audit figures deterministic projections of reviewed artifacts

- Status: ACCEPTED (`RV-20260901-007` approved 2026-09-02)
- Date: 2026-09-01
- Decision: Generate the width-five PPM atlas only from the serialized Phase-A trace, Phase-B general candidate, and negative finite-admission record. Preserve exact machine IDs and full signatures in the atlas/SVG metadata, label all batch coordinates as non-temporal, retain PPM-free CNOT layers, and independently replay both atlas JSON and static SVG coverage.
- Rationale: A human-readable figure can hide omitted layers, relabel a logical grouping as physical simultaneity, or drift from the machine trace even when the underlying scheduler is correct. Treating the figure as a checked projection makes those presentation errors detectable without creating another source of scheduling truth.
- Consequences: `E-20260901-008` may report exact projection/coverage counts and deterministic document hashes, but it adds no native construction, time, space, routing, factory, or failure evidence. Any future atlas change must be made in the generator or reviewed input and regenerated; generated SVGs must not be edited manually.

## D-0022: Reuse one symbolic direct-CCZ IR for in-place and out-of-place QCLA

- Status: ACCEPTED (`RV-20260901-008` approved 2026-09-02)
- Date: 2026-09-02
- Decision: Adapt the reviewed in-place QCLA directly to the same six-PPM direct-CCZ and ordered conditional-Clifford-frame IR as the OOP trace. Treat fixed source X and CNOT gates as explicit implementation-neutral frame conjugations, retain exact ANF compatibility tests, and permit a proved causal lower bound to close candidate-level optimality without solving a redundant large maximum-conflict-clique problem.
- Rationale: Routing the comparison through the seven-T baseline would change the logical instruction semantics, while silently materializing fixed Cliffords would import unavailable native costs. The 120-PPM IP instance has a matching 24-level causal lower bound and construction; an exact maximum conflict clique cannot improve that equality. Seven late-frame PPMs exceed bounded branch enumeration, so their weight and distinct-count fields must be weakened explicitly without weakening exact pair compatibility.
- Consequences: `E-20260901-009` may compare width-five OOP/IP source demand, frame/reaction structure, candidate levels, cleanup, and semantic liveness under one logical model. It must label seven weight profiles `CHECK`, keep distinct counts null there, use only a proved one-vertex conflict lower bound for the large instance, and continue to emit null native schedule, runtime, physical-qubit, and failure outputs.

## D-0023: Scale direct-CCZ QCLA with exact anchors and compact structural points

- Status: ACCEPTED (`RV-20260901-009` approved 2026-09-03)
- Date: 2026-09-03
- Decision: Materialize exact Boolean-ANF PPM pair tables only at widths 5 and 8. For larger OOP/IP widths, traverse the generated source and direct-event traces to record exact counts and a two-weight Toffoli longest-path lower bound without constructing the quadratic relation table. Treat the source two-phase injection envelope as `CHECK`, keep large-width candidate compatibility `OPEN`, and route all finite outputs through the coherent-backend and native-mapper gate.
- Rationale: Width-256 OOP/IP would require 27,184,251/108,744,378 pair records, while source/event counts, layer bursts, and causal lower bounds do not require those records. Equality between exact candidates and the causal bound at widths 5 and 8 is useful validation but does not prove width-256 compatibility.
- Consequences: `E-20260901-010` may report direct width-256 demand and model-relative causal lower bounds, but cannot report a width-256 candidate batch count, surgery rounds, memory/routing cost, runtime, physical qubits, or failure probability. A later native mapper or structural compatibility proof must close those fields before finite integration.

## D-0024: Certify source-aligned PPM compatibility by frame-generator closure

- Status: ACCEPTED (`RV-20260903-001` approved 2026-09-03)
- Date: 2026-09-03
- Decision: Replace the large-width `CHECK` two-phase envelope with a linear-size logical compatibility certificate when the source/event trace satisfies the reviewed Figure-14(a) six-PPM shape, globally fresh resource values, strictly layered dependencies, support-disjoint source layers, and the `X/Z/CNOT/CZ` deferred-frame generator set. Retain full Boolean-ANF pair classification at widths 5 and 8 as an exact bridge, not as the scaling mechanism.
- Rationale: Every first-phase `ZZ` observable remains branchwise Z type under the complete deferred-frame generator set, while every second-phase `X` acts on a unique resource absent from that frame. The project's stricter per-index axis condition, commutation, no-Y, causality, and resource-reuse conditions therefore follow without enumerating all pairs.
- Consequences: `E-20260903-001` may report 34 OOP and 68 IP width-256 candidate levels as `PROVED` inside the architecture-independent logical screen because each construction also meets its causal lower bound. This does not admit simultaneous code-level support, native surgery rounds, physical placement, routing, timing, factory/buffer service, decoder/reaction service, physical qubits, or failure probability; every such output remains null.

## D-0025: Expose branch-dependent support envelopes before native mapping

- Status: ACCEPTED (`RV-20260903-002` approved 2026-09-03)
- Date: 2026-09-03
- Decision: Treat logical compatibility and logical support as separate certificates. Preserve exact Boolean-ANF possible-support unions for every selected OOP width and the OOP/IP widths 5 and 8. For IP widths above 8, expose a sound may-support upper envelope, a deterministic 512-branch witnessed-union lower envelope, their unresolved gap, and the maximum weight actually seen in one sampled branch. Do not call a union across different branches a simultaneous support or a native geometric realization.
- Rationale: The reviewed conditional frame preserves Z type but does not preserve support. The exact width-5 trace already contains a one-outcome conditional support term, falsifying outcome independence. Large IP ANFs are output-intensive, while may-support propagation remains sound and concrete sampled branches remain valid lower witnesses.
- Consequences: A native mapper must accept branch-dependent support hypergraphs or explicitly materialize the relevant frame. Width-256 OOP exact possible-support union sizes and IP lower/upper envelopes may be reported, but neither implies connected code support, surgery rounds, time, processor capacity, routing cost, factory service, physical qubits, or failure probability.

## D-0026: Separate logical H/CNOT frame policy from its QEC realization

- Status: PROPOSED (pending `RV-20260905-001`)
- Date: 2026-09-05
- Decision: Use frame-conjugated logical H and bare logical CNOT as the default logical policy for the direct-CCZ QCLA comparison. Compare code co-design, global/SIMD operations, gate teleportation, and surgery as separate realization families. Keep all current-backend durations null until one family supplies compatible addressability, concurrency, routing, reaction, and decoder contracts.
- Rationale: A general bare or tracked H can destroy the proved Z-only/no-Y invariant, whereas all three CNOT policies remain inside the Z-preserving Clifford subgroup. Bare CNOT avoids synthesizing a branch-dependent `C^dagger CNOT C`; its cost is concentrated in only three OOP or four IP source layers, though tracking remains a possible layer-specific optimization if future support growth is bounded.
- Consequences: The project may report exact gate/layer demand and conditional logical-layer envelopes, but native H-SWAP or H teleportation cannot substitute for frame-conjugated H without frame clearing, an H-safe proof, or whole-event co-design. RASCqL timings remain an incompatible-domain comparator, not a direct-CCZ runtime.

## D-0027: Validate a separate commutation-aware QCLA model before rescaling

- Status: PROPOSED (pending `RV-20260906-001`)
- Date: 2026-09-06
- Decision: Preserve the reviewed source-aligned QCLA dependency graph and its width-5/256 candidate levels as the baseline. Build a separate commutation-aware variant that removes a shared-wire ordering edge only after exact controlled-X commutation, common-incoming-frame joint-injection, adaptive-observable, Clifford-barrier, and value-lifetime checks pass at width 5 and widths 2--8. Re-evaluate width 256 only after those gates close.
- Rationale: Same-axis support overlap can be admissible in the general high-rate screen, so nearest-use wire serialization may overstate logical depth. However, logical commutation alone does not prove that sequential teleportation corrections can be batched, that measured cleanup is channel-equivalent, or that any finite code realizes the resulting PPM family.
- Consequences: The proposed width-5 values of four unitary CCX layers/eight candidate levels and three measured-cleanup CCX layers/six candidate levels remain `CONJECTURE`. The existing twelve-level width-5 and thirty-four-level width-256 results are not revised by this planning task. Any eventual width-256 reduction remains a unitless structural result until a coherent finite backend closes simultaneous support, ports, routing, decoding, reaction, factory/buffer, memory, timing, and failure.
