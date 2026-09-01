# Direct-CCZ PPM audit-atlas contract

## Scope

`T-20260901-008` turns the reviewed width-five clean out-of-place QCLA
symbolic trace (`T-20260901-006`) and candidate batching (`T-20260901-007`)
into a deterministic, human-auditable static atlas.

The atlas is a projection, not a compiler or scheduler. Its batch coordinate is
exactly:

`candidate_batch_level_not_time`

Every SVG therefore states that candidate levels are not time, surgery rounds,
or native simultaneous execution.

## Evidence boundary

- `LITERATURE`: the source QCLA structure and direct-CCZ injection skeleton
  inherited from the reviewed input trace.
- `NUMERICAL`: the atlas JSON and SVGs are a deterministic projection of the
  reviewed serialized artifacts.
- `PROVED`: relative to those serialized artifacts, the atlas covers every
  source operation, PPM, correction update, source dependency, batch
  membership, and cross-level pair certificate exactly once where applicable.
- `OPEN`: finite native operation construction, duration, routing, memory,
  reaction latency, decoder service, CCZ delivery/buffering/storage, physical
  space, and failure probability.

No visual element upgrades an inherited evidence label.

## Canonical inputs

The experiment regenerates its inputs from source rather than trusting earlier
generated files:

1. `build_oop_qcla_trace(5)`;
2. the reviewed symbolic direct-CCZ PPM lowering;
3. the reviewed exact candidate-batching analysis;
4. the reviewed negative finite-backend admission.

The Phase-A and Phase-B independent replays must pass before the atlas is
built. The atlas records canonical SHA-256 fingerprints of the three serialized
input objects:

- symbolic PPM/frame trace;
- general logical candidate analysis;
- finite-instance admission record.

## Atlas data model

The canonical JSON schema is
`ecdlp-ftqc/direct-ccz-ppm-atlas`, version 1.

### Overview

The overview preserves these reviewed width-five values:

| Quantity | Value | Interpretation |
|---|---:|---|
| Source macro-layers | 9 | Algorithmic source layers, not time |
| Source operations | 23 | 10 Toffoli/CCX and 13 CNOT |
| Direct-CCZ injections | 10 | One per source Toffoli |
| Presented PPMs | 60 | Six per injection |
| Outcome-conditioned frame updates | 60 | Six per injection |
| Source dependencies | 36 | Exact source-DAG edges |
| Candidate batch levels | 12 | Unitless logical candidate coordinate |
| Batch sizes | 12, 12, 6, 6, then eight groups of 3 | Complete one-time PPM coverage |
| Peak semantic live logicals | 26 | Stated logical-liveness coordinate only |
| Peak live CCZ resource states | 4 | Not factory buffer capacity |
| Maximum presented PPM weight | 7 | Symbolic branch maximum |

### Macro-layer panels

There is one panel for every source macro-layer, including the three layers
with no PPMs. Hiding empty PPM layers would hide the implementation-neutral
CNOT/frame transitions and would distort the source overview.

| Source layer | Source operations | PPMs | Frame terms in -> out |
|---:|---:|---:|---:|
| 1 | 4 | 24 | 0 -> 24 |
| 2 | 3 | 0 | 24 -> 24 |
| 3 | 1 | 6 | 24 -> 30 |
| 4 | 2 | 12 | 30 -> 42 |
| 5 | 1 | 6 | 42 -> 48 |
| 6 | 1 | 6 | 48 -> 54 |
| 7 | 1 | 6 | 54 -> 60 |
| 8 | 5 | 0 | 60 -> 60 |
| 9 | 5 | 0 | 60 -> 60 |

Each source-operation record includes:

- exact source gate ID, kind, stage, support, and frame signatures;
- exact source predecessor IDs and logical-value reasons;
- injection-event ID when the source operation is a Toffoli;
- all six presented PPM IDs, outcome tokens, symbolic observable labels,
  weight range, possible logical support, and candidate-batch membership;
- all six conditional frame-update IDs, gate labels, Boolean conditions,
  outcome dependencies, and resulting frame signatures.

### Cross-level separation certificates

For every PPM pair assigned to different candidate levels, the later PPM stores
a certificate naming the earlier PPM and all applicable exact relation flags:

- `causal_dependency`;
- `reaction_dependency`;
- `symplectic_noncommutation`;
- `logical_axis_conflict`;
- `resource_reuse`.

If an earlier/later pair has none of those direct pair flags, it is labelled
`deterministic_frontier_partition`. This label means only that the reviewed
exact-ready-frontier construction placed the mutually compatible pair in
different levels because of the global frontier partition. It is not a new
physical conflict or a claim of a uniquely necessary split.

The 12 batches contain 186 within-batch unordered pairs:

`2*C(12,2) + 2*C(6,2) + 8*C(3,2) = 186`.

Therefore the 1,770-pair relation table contains exactly 1,584 cross-level pair
certificates. The non-exclusive reason occurrences are:

| Certificate flag | Occurrences |
|---|---:|
| Causal dependency | 1,206 |
| Reaction dependency | 1,116 |
| Deterministic frontier partition | 378 |
| Symplectic noncommutation | 30 |
| Logical-axis conflict | 30 |
| Resource reuse | 30 |

The counts overlap because one pair may carry several certificates.

## Visual grammar

The renderer emits one overview and nine standalone SVG layer panels.

- Batch membership is encoded by a fixed twelve-color palette and an explicit
  `B01`--`B12` label. Meaning never depends on color alone.
- PPM chips show their presented-observable label and measured outcome token.
- Arrows connect the PPM region to the symbolic-frame update region.
- Conditional update rows show the Clifford/Pauli frame gate and a compact
  event-local Boolean condition.
- Frame-in and frame-out bars carry the exact full signature in SVG metadata
  and a shortened human-readable signature in visible text.
- CNOT-only layers explicitly show implementation-neutral pass-through and
  `finite cost OPEN`.
- A separate sidebar reports batch groups and cross-level certificate counts.
- The overview has separate `GENERAL LOGICAL CANDIDATE` and
  `FINITE BACKEND REJECTED` cards.

Every SVG is static XML with no script and no external reference. Machine IDs
are stored in `data-*` attributes independently of visible shortened labels.

## Finite-backend fail-closed rule

Atlas construction rejects its inputs if any of the following is true:

- the symbolic trace claims `complete_native_schedule=true`;
- the optimized schedule does not use `candidate_batch_level_not_time`;
- the finite backend or native schedule is admitted;
- schedule, runtime, physical-qubit, or failure output is non-null;
- the trace, general-candidate, and finite-admission identities disagree.

The overview preserves all current gaps separately:

- 13 portable capability fields missing;
- 13 finite-backend fields missing;
- three incompatible `bb18` factory values;
- four native-mapper obligations missing.

## Independent replay

`direct_ccz_ppm_atlas_replay.py` imports neither the visualization renderer nor
the compiler or scheduler. From serialized inputs it independently rebuilds:

- PPM-to-batch membership;
- every cross-level relation certificate;
- exact source operation, injection, PPM, update, frame, and dependency sets;
- per-panel batch intersections and reason counters;
- general-versus-finite backend status and null finite outputs.

It then parses all ten SVGs with the standard XML parser and checks:

- exact document names and atlas fingerprint;
- static SVG structure with no script or external reference;
- the non-temporal notice in every document;
- one-time coverage of all 23 source IDs, 60 PPM IDs, and 60 update IDs.

Tamper regressions remove one SVG PPM, change one batch membership, and forge a
finite runtime. All must fail closed.

## Reproduction

Run:

```text
uv --native-tls run python scripts/run_direct_ccz_ppm_atlas_cycle.py
```

Outputs are written to `experiments/runs/T-20260901-008/`:

- `atlas.json`;
- `overview.svg`;
- `macro-layer-01.svg` through `macro-layer-09.svg`;
- `independent_replay.json`;
- `summary.json`;
- `reproducibility.json`.

Generated files are never manually edited. Change the trace, batching input,
atlas generator, or renderer and regenerate them.

## Explicit non-claims

The atlas does not provide:

- a qLDPC or surface-code surgery construction;
- a processor placement or routing solution;
- memory load/store traffic;
- reaction or decoder timing;
- CCZ factory service, delivery, buffer occupancy, or stalls;
- physical qubits, logical failure probability, or wall-clock runtime;
- evidence that a same-color group is physically simultaneous.

Those quantities remain gated by a compatible finite backend and native
mapper.
