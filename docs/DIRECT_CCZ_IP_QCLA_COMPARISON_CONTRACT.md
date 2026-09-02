# Direct-CCZ in-place versus out-of-place QCLA comparison contract

## Scope

`T-20260901-009` implements Phase D of
`docs/HIGH_RATE_QCLA_PPM_OPTIMIZATION_CYCLE.md`. It connects the reviewed
in-place modulo-`2^n` QCLA source trace directly to the same symbolic
direct-CCZ PPM and conditional-Clifford-frame intermediate representation used
by the reviewed clean OOP trace. It does not pass through the Selinger seven-T
decomposition.

The bounded comparison uses width five. It is a logical dependency and
candidate-batching result, not a code construction or physical schedule.

## Evidence boundary

- `LITERATURE`: both source circuits use the pinned Draper et al. QCLA source.
- `NUMERICAL`: deterministic IP lowering, independent serialized replay,
  exact ANF pair relations, liveness, and the matching 24-level construction.
- `PROVED`: relative to the serialized symbolic trace and the stated logical
  sufficient-condition model, exact ANF nonzero tests decide Y content,
  symplectic commutation, and per-index axis conflicts. The 24-level causal
  path is a lower bound matched by the deterministic candidate construction.
- `CHECK`: seven PPMs with more than 16 outcome variables use a proved
  nonidentity weight lower bound and exact possible-support-union upper bound;
  their distinct branch-observable count is null.
- `OPEN`: every finite operation duration, capacity, placement, memory,
  routing, decoder/reaction service, CCZ delivery/buffer trajectory, physical
  qubit total, and logical failure contribution.

## Shared lowering

Each source Toffoli is represented by the admitted Figure 14(a) event:

1. a target Hadamard basis change;
2. three resource-data `ZZ` PPMs;
3. three resource `X` PPMs;
4. six exact conditional correction-frame updates; and
5. the closing target Hadamard.

Source CNOT and X operations remain explicit implementation-neutral Clifford
instructions. They conjugate the ordered conditional frame as `U C U†` and
carry source dependencies, but receive no duration, routing, memory, or
ancilla cost. The compiler introduces no additional logical ancilla.

The OOP wrapper and serialized width-five OOP trace remain byte-identical to
the reviewed Phase-A artifact.

## Independent semantic replay

The replay module imports neither compiler nor scheduler. From the serialized
IP trace and reviewed source DAG it rebuilds:

- every source operation and all 75 source dependencies;
- all X/CNOT passthrough and injection operation dependencies;
- 1,280 event-local correction truth-table rows;
- 43 source-operation frame transitions across 18 macro layers;
- 14,880 presented-observable probes from 124 deterministic global outcome
  assignments;
- all 1,024 width-five computational-basis input pairs; and
- the independent 64-branch direct-CCZ injection channel.

The global outcome probes are deterministic regression coverage, not an
exhaustive enumeration of `2^120` outcome assignments or a formal global
channel proof.

## Exact compatibility and bounded profile fields

Candidate compatibility continues to use canonical ANF polynomials. A pair is
eligible only when it has no causal or reaction ordering, no consumed-resource
reuse, an identically zero symplectic commutator, identically zero per-index
axis-conflict polynomials, and neither PPM has branch-possible Y.

ANF is a unique Boolean-function representation, so a nonzero axis, Y, or
conflict polynomial is an exact existence certificate without enumerating all
assignments. This keeps all 7,140 IP pair relations exact even when a PPM
depends on as many as 42 outcome variables.

Exact minimum/maximum weight and distinct-observable enumeration is retained
for profiles with at most 16 variables. For the seven larger profiles:

- `minimum_weight = 1` is a proved lower bound because branchwise Clifford
  conjugation cannot turn a nonidentity PPM into identity;
- `maximum_weight` is the size of the exact union of branch-possible logical
  support and is therefore a conservative upper bound; and
- `distinct_branch_observables = null`.

These fields are visibly marked `weight_bounds_exact = false` and do not
affect pair compatibility or ready-frontier selection.

## Width-five comparison

| Quantity | Clean OOP | In-place |
|---|---:|---:|
| Source operations | 23 | 43 |
| Source Toffolis / direct-CCZ events | 10 | 20 |
| Source CNOTs | 13 | 15 |
| Source X gates | 0 | 8 |
| Source macro layers | 9 | 18 |
| Source non-Clifford layers | 6 | 12 |
| Source dependencies | 36 | 75 |
| PPMs / conditional updates | 60 / 60 | 120 / 120 |
| Logical lifetimes | 16 | 15 |
| Candidate levels | 12 | 24 |
| Causal lower bound | 12 | 24 |
| Peak semantic live logicals | 26 | 26 |
| Peak live CCZ resource states | 4 | 4 |
| Singleton fallback demand | 60 | 120 |

The in-place batch sizes are `12, 12, 6, 6`, fourteen groups of `3`, then
`6, 6, 9, 9, 6, 6`. There are no branch-possible-Y PPMs and no fallback calls
inside the general logical construction.

For the 120-vertex IP conflict graph, the artifact records only the proved
single-vertex clique lower bound. Computing a maximum clique is unnecessary
for optimality because the independently rebuilt causal lower bound is already
24 and the construction has 24 levels. The recorded clique value must not be
read as the graph's maximum clique number.

## Cleanup comparison

The machine-readable comparison defines cleanup explicitly:

- OOP: `input_restore` plus `prefix_uncompute` source stages; and
- IP: source steps 7--10, covering reverse carry, final propagate restore,
  initial-generate uncompute, and complement restore.

Under that definition OOP has five cleanup operations including one Toffoli;
IP has 17 cleanup operations including ten Toffolis. These are source-gate
counts, not native costs.

## Finite rejection

Both variants retain the same rejected finite backend. The IP artifact keeps
13 capability fields and 13 backend fields missing, three factory fields
incompatible, and four native-mapper obligations absent. Native schedule,
surgery rounds, runtime, physical qubits, and failure probability remain null.

## Reproduction

Run:

```text
uv --native-tls run python scripts/run_direct_ccz_ip_qcla_cycle.py
```

The manifest is `experiments/manifests/E-20260901-009.yaml`; generated files
are under `experiments/runs/T-20260901-009/`. Generated results must be changed
only through their source, configuration, or generator.
