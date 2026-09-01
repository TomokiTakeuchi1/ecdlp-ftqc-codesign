# Symbolic direct-CCZ PPM trace contract

## Scope

`T-20260901-006` implements Phase A of
`docs/HIGH_RATE_QCLA_PPM_OPTIMIZATION_CYCLE.md`. It lowers the reviewed clean
out-of-place QCLA at width 5 directly through the admitted six-measurement
`|CCZ>` injection. It does not use the Selinger seven-`T` decomposition.

The result is an architecture-independent symbolic program. It preserves the
source dependency graph, measurement outcomes, correction dependencies,
Clifford frames, and lifetimes needed by the Phase-B batch optimizer. It is
not a surgery schedule.

## Evidence boundary

- `LITERATURE`: the OOP-QCLA source semantics and the Litinski--Nickerson
  Figure 14(a) six-PPM injection pattern.
- `NUMERICAL`: the deterministic width-5 lowering, independent replay, exact
  local channel checks, and counts reported below.
- `CHECK`: propagating explicit source CNOTs as materialized Clifford-frame
  conjugations is the Phase-A semantic convention.
- `OPEN`: finite CNOT realization, high-rate batch admission, operation time,
  memory and routing, decoder and reaction service, factory delivery and
  buffering, physical space, and failure probability.

No source macro layer is called a surgery round. No generated artifact has a
native start time, processor assignment, duration, or physical-qubit count.
`complete_native_schedule` is required to be `false` by both the compiler and
the independent replay.

## Source and output identity

The input is `build_oop_qcla_trace(5)` under the reviewed clean
`(A,B,0) -> (A,B,A+B mod 2^n)` contract. The capability input is
`configs/architectures/direct_ccz_single_event_capability_v1.yaml`.

The output schema is
`ecdlp-ftqc/symbolic-direct-ccz-ppm-trace`, version 1. The deterministic trace
ID extends the source trace ID with `symbolic-direct-ccz-ppm-v1`. Source PDF,
configuration, compiler, verifier, and generator hashes are recorded in the
experiment reproducibility artifact.

## Lowering rules

Each source CCX produces:

1. a target-H basis-change record;
2. three resource--data `ZZ` PPMs in injection layer 1;
3. three resource `X` readout PPMs in injection layer 2;
4. six outcome-dependent frame updates; and
5. the closing target-H basis-change record and a symbolic completion barrier.

Layer-1 PPMs depend on the opening H. Layer-2 PPMs depend on all three layer-1
PPMs. The closing H also depends on the three layer-1 outcomes; it need not
wait for the disjoint resource-X readouts. The three pre-H CZ corrections are
deferred through that H into the event-boundary frame. The completion barrier
depends on the closing H and all six frame updates; the last three updates
depend on the resource-X outcomes. Each frame update names exactly the outcome
variables in its Boolean condition. Downstream source gates depend on the
completion barrier, so reaction causality remains visible without assigning a
finite latency.

Each source CNOT remains an implementation-neutral logical Clifford. It has
the exact source predecessors and updates the symbolic frame by `U C U†`.
Its finite time, space, routing, and memory cost are `OPEN`.

For a direct-CCZ injection, the opening/closing logical H records and every
PPM are presented under the incoming correction frame, implementing the
frame-conjugated event while retaining `C_in`. The event-local branch
correction is then appended to the stored circuit so the output
correction-to-apply is `C_new C_in`. This avoids attempting to push an
arbitrary Clifford frame through CCX as though CCX were itself Clifford.

## Canonical symbolic frame

Outcome conditions use algebraic normal form over GF(2). Monomials and
variables have one canonical order; XOR is symmetric difference and AND is
polynomial multiplication. A frame is an ordered list of conditional
primitive Clifford circuits. Its canonical JSON representation is hashed to
form the frame signature at every source-operation and macro-layer boundary.

The frame stores the correction-to-apply circuit `C`: the uncorrected physical
state is `C†|logical>`. The convention is therefore:

- a later logical PPM `P` is presented physically as `C† P C`, evaluated by
  traversing the stored correction terms in reverse order;
- event-local corrections are appended in stored circuit order. At the
  operator level this makes the combined correction `C_new C_in`, as required
  when the injection measurements and basis changes are presented under the
  incoming frame;
- a pass-through source CNOT conjugates every stored frame circuit by that
  CNOT; and
- the presented Hermitian Pauli keeps exact branch-dependent `X`, `Z`, and
  sign polynomials, including `Y` and minus signs created by Clifford
  conjugation.

Figure 14(a)'s first three conditional CZ corrections occur before the closing
target H. At the event boundary, the two CZs touching the target are therefore
stored as conditional CNOTs by `H_t CZ(c,t) H_t = CNOT(c,t)`. The CZ between
the two controls is unchanged. The three final `Z`, `Z`, and `X` corrections
are already after the H and are stored directly. This is a change of frame
coordinates, not an added physical CNOT schedule.

## Lifetimes

The trace records 16 source logical lifetimes: five `A` values, five `B`
values, five output-workspace `Z` values, and one width-5 prefix scratch value.
Each of the ten injections has a separate three-qubit CCZ resource lifetime,
from its three layer-1 couplings through its three terminal X readouts, with
consumption explicit. The injection contract introduces zero compiler
ancillas. These are logical lifetimes only; no memory placement or resource
storage duration is assigned.

## Width-5 result

`E-20260901-006` emits the following `NUMERICAL` counts:

| Quantity | Count |
|---|---:|
| Source operations | 23 |
| Source CCX / direct-CCZ injections | 10 |
| Pass-through source CNOTs | 13 |
| PPMs | 60 |
| Conditional frame updates | 60 |
| Source dependencies | 36 |
| Source macro layers | 9 |
| Source logical lifetimes | 16 |
| CCZ resource lifetimes | 10 |
| Compiler ancilla lifetimes | 0 |

The nine macro layers are source dependency boundaries only.

## Independent replay

`src/ecdlp_ftqc/verification/direct_ccz_ppm_replay.py` reads serialized JSON
and does not import the symbolic compiler. It independently:

- matches all source operations, supports, stages, and 36 dependencies;
- reconstructs every operation-level predecessor edge and completion barrier;
- checks the six PPM supports and six event-boundary correction gates for each
  injection;
- evaluates all 64 correction truth-table rows for each of ten injections
  (640 rows);
- rebuilds all 23 frame transitions and their canonical signatures;
- evaluates all 60 presented observables on 64 deterministic global outcome
  probes (3,840 checks);
- checks all logical, resource, and compiler-ancilla lifetimes;
- exhaustively replays all 1,024 width-5 computational-basis input pairs; and
- invokes the independent all-64-branch local injection-channel verifier,
  whose maximum ideal-CCX operator residual is `0.0`.

The 64 global probes are a deterministic regression set, not exhaustive
enumeration of `2^60` outcome assignments and not a formal proof. The compiler
retains the exact ANF expressions rather than expanding that global branch
tree. Dedicated tests additionally compare all nonidentity two-qubit Pauli
conjugations by CNOT and CZ against explicit matrices and reject tampered
provenance, conditions, predecessors, observables, missing PPMs, and forged
native-schedule claims.

## Reproduction

Run:

```text
uv --native-tls run python scripts/run_direct_ccz_ppm_cycle.py
```

Canonical outputs are under `experiments/runs/T-20260901-006/`:

- `qcla_oop_n5_symbolic_direct_ccz_ppm.json`;
- `symbolic_direct_ccz_ppm_replay.json`;
- `summary.json`; and
- `reproducibility.json`.

There is intentionally no `schedule.json`. Phase B (`T-20260901-007`) must
consume this trace and report general high-rate candidacy, finite-instance
admission, and low-rate fallback separately.
