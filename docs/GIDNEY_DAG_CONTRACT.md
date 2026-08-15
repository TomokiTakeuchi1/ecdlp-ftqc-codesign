# Gidney QEC-neutral DAG contract

Task: `T-20260815-001`  
Schema: `ecdlp-ftqc/qec-neutral-dag`, version 1  
External source: `runtime-metadata-benchmark` commit
`8c1638805e7246c30117a0251526661039df1369`

## Scope

This contract adapts the verified, uncontrolled in-place Gidney ripple-carry
adder into an architecture-independent causal DAG. The external repository
remains the source of truth for circuit generation, logical-value lifetimes,
operation-atomic memory and occupancy supports, and phase-verification
provenance. This repository does not copy or modify the Gidney generator.

The adapter consumes the external canonical oracle JSON boundary:

- schema `runtime-metadata-benchmark/oracle`, version 3;
- generator `runtime_metadata_benchmark.gidney`;
- semantic mapping version 4;
- decomposition `operation_atomic_live_local_v1`;
- phase status `verified_for_runtime_contract`.

Any mismatch is rejected at the adapter boundary.

## Layer boundary

The version-1 DAG contains circuit semantics only:

- source operation identity and arithmetic region;
- ordered logical operands and control/target roles;
- direct wire and logical-value support;
- logical values modified by the operation;
- X-Pauli support for the explicit temporary-ancilla measurement;
- measurement outcomes and classical conditions;
- logical-value lifetime, initialization, release, and residency metadata;
- source memory support and processor-occupancy support.

The following properties belong to later QEC/backend records and are not
invented by this adapter:

- code block and architecture-zone assignment;
- automorphism, transversal, surgery, or injection gadget selection;
- syndrome-round duration and physical-qubit occupancy;
- decoder latency, resource conflicts, routing, and bridge use;
- CCZ or magic-state lowering and factory demand.

In particular, the external sequential model's four-PPM
`toffoli_accounting` coefficient is not a phase-exact Pauli-support
decomposition. The temporary-AND compute node therefore has no fabricated
Pauli-product list. A later backend must select and evidence an executable
lowering.

## Temporary-AND erase expansion

Each source `temporary_and_erase(control_0, control_1, temporary)` operation is
expanded into two nodes:

1. X-basis measurement of `temporary`, producing a named classical result;
2. conditional CZ/Clifford-frame update on `control_0` and `control_1` when the
   result is one.

The measurement-result edge is classified as `classical_feed_forward`. The
temporary can be released after its measurement without waiting for the
control-frame update. A later operation on either control remains ordered
after that update. A backend may subsequently implement the correction
physically or absorb it into a valid Clifford-frame contract.

Both nodes produced by the erase split retain the source operation's control
residency by design. This is one continuous residence interval, not evidence
for two independent loads; a future memory-I/O backend must compare residency
transitions under its replacement policy rather than sum per-node occupancy.

## Causal-edge construction

Source-list adjacency is not treated as dependency. The adapter creates an
edge only when one of the following holds:

- two expanded nodes are consecutive on the same quantum wire
  (`quantum_order`);
- allocation/use or last-use/release ordering is required
  (`value_lifetime`);
- a measurement result controls a correction
  (`classical_feed_forward`).

Shared-resource conflicts, memory-transfer dependencies, and decoder/controller
dependencies will be added by later compiler and scheduler layers. They must
not be confused with algorithmic causality.

## Regression identities

The following values are `NUMERICAL` regression observations from the pinned
frontend and adapter. The critical path assigns unit weight to every semantic
node; it is not a syndrome-round or wall-clock runtime.

| Width | Source operations | DAG nodes | Edges | Lifetimes | Classical results | Unit-node critical path |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 7 | 8 | 8 | 5 | 1 | 6 |
| 3 | 17 | 19 | 25 | 8 | 2 | 14 |
| 4 | 27 | 30 | 42 | 11 | 3 | 22 |
| 256 | 2,547 | 2,802 | 4,326 | 767 | 255 | 2,038 |

Widths 2--4 inherit exhaustive coherent-regression provenance and are labeled
`NUMERICAL`. Width 256 inherits the paper-general-construction provenance with
the locally verified gadget/invariants and is labeled `LITERATURE`; no
256-qubit state-vector claim is made.

## Reproduction

Small-width source fixtures and their SHA-256 manifest live under
`tests/fixtures/gidney_oracle/`. Regenerate them only with
`scripts/generate_gidney_oracle_fixtures.py`, which verifies the pinned commit
and rejects uncommitted changes in the external generator, IR, PPM, and
scheduling source paths.

The 13 MB width-256 source oracle is deliberately not copied into this
repository. Its integration regression is generated from the pinned sibling
checkout and validates 2,802 nodes, 4,326 edges, 767 logical-value lifetimes,
255 measurement results, and a unit-node critical path of 2,038.

## Known limitations

- This is an uncontrolled adder only; controlled addition, unary lookup, and
  carry-lookahead remain separate adapters.
- The DAG is flat at the source-operation level. Arithmetic subroutine nesting
  will require a later hierarchical-call extension.
- Memory I/O, processor-capacity partitioning, QEC-native gadgets, and resource
  conflicts are outside this task.
- A source commit field is provenance, not proof of the currently imported
  Python package. Published artifact generation must independently verify the
  checkout, as the fixture generator does.
