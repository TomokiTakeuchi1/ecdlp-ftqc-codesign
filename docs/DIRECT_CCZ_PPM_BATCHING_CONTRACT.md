# Direct-CCZ symbolic PPM batching contract

Task: `T-20260901-007`

## Scope

This contract implements Phase B of
`docs/HIGH_RATE_QCLA_PPM_OPTIMIZATION_CYCLE.md` for the reviewed width-5 clean
out-of-place QCLA symbolic trace from `T-20260901-006`. It classifies exact
logical relations and constructs unitless candidate batch levels. It does not
construct a native qLDPC operation, surgery schedule, or runtime.

The cycle has three outputs that must never be collapsed:

1. an architecture-independent general-high-rate candidate classification;
2. a fail-closed verdict for one finite backend candidate; and
3. a semantic singleton low-rate fallback order whose finite cost is `OPEN`.

## Evidence boundary

- `PROVED`: Boolean-ANF identities, per-index symplectic relations, exact
  causal closure of the serialized operation DAG, the stated candidate-model
  lower bounds, and optimality when a constructive upper bound meets one of
  those lower bounds.
- `NUMERICAL`: the deterministic width-5 profiles, batch construction,
  liveness counts, strategy metrics, and independent serialized replay.
- `LITERATURE`: the source QCLA and direct-CCZ event semantics inherited from
  the reviewed inputs.
- `INCONCLUSIVE`: measured-operator-product rewrites, because this trace does
  not yet carry a transported-stabilizer and resource-lifetime certificate for
  such a rewrite.
- `OPEN`: selective Clifford materialization, finite native operation family,
  code-basis mapping, physical support, ancilla/check construction, capacity,
  routing, duration, decoder and reaction service, factory delivery and
  buffering, memory traffic, physical qubits, and failure probability.

Every `PROVED` statement is relative to the reviewed serialized symbolic
trace and the candidate rules below. It is not a proof that a physical code
implements a candidate batch.

## Exact symbolic relation screen

For symbolic Hermitian Pauli words `P` and `Q`, let `x_i(P)` and `z_i(P)` be
their exact ANF component functions at logical index `i`. The local axis
conflict polynomial is

```text
s_i(P,Q) = x_i(P) z_i(Q) XOR z_i(P) x_i(Q).
```

The global symplectic commutator is the XOR of `s_i` over all indices. Because
ANF is a unique representation of a Boolean function, an empty polynomial is
identically zero and a nonempty polynomial has at least one Boolean assignment
where it evaluates to one. The classification therefore makes no statistical
or sampled commutation decision.

The two tests are intentionally distinct:

- global commutation requires `XOR_i s_i = 0`;
- logical-index axis consistency requires every individual `s_i = 0`.

Thus `X X` and `Z Z` commute globally but fail the index-axis screen at both
indices. Conversely, two observables may overlap on one or more logical
indices and remain compatible when their axes agree. Logical support overlap
alone is not a conflict.

Possible `Y` content at index `i` is the exact polynomial
`x_i(P) z_i(P)`. The current general candidate model has no qualified
Y-assisted construction, so a nonzero Y polynomial requires low-rate fallback
or a later backend-specific construction. The sign polynomial is preserved
in branch profiling but does not alter commutation.

For each of the 60 PPMs, all assignments of the variables appearing in that
one presented observable are enumerated. The largest local profile has nine
variables, so the largest local enumeration is 512 assignments. This derives
minimum and maximum weight, possible axes, possible support, and the number of
distinct signed observables. It is not a global enumeration of `2^60`
outcome histories.

## Causal and reaction graph

The scheduler reconstructs the Phase-A semantic DAG from:

- Clifford and PPM predecessor operation IDs;
- each correction update's outcome dependencies; and
- each injection completion barrier's predecessor IDs.

Correction-update edges are marked as classical reaction paths. PPM ancestor
closure is computed through all zero-duration semantic nodes. Those nodes are
not assigned zero physical time; they are omitted from the unitless PPM-level
objective because their native cost is `OPEN`.

Two PPMs can share a candidate level only if:

- neither is a causal ancestor of the other;
- their global commutator polynomial is identically zero;
- every per-index axis-conflict polynomial is identically zero;
- neither has branch-possible Y content under the current screen; and
- they do not reuse the same consumed CCZ resource logical.

Each ready frontier is packed by an exact maximum-clique search in the
compatibility graph with deterministic lexicographic tie breaking. This is
exact for each frontier. Global optimality is claimed only when the resulting
constructive level count meets an independently computed global lower bound.

## Candidate lower and upper bounds

Two exact lower bounds are reported:

1. the maximum number of PPM nodes on a causal path through the complete
   semantic DAG; and
2. the maximum clique in the graph whose edges mean that two PPMs cannot
   share a general candidate level.

Their maximum is the combined candidate-level lower bound. The deterministic
batching is a constructive architecture-independent upper bound. It is not a
realizable native-cost upper bound. Each schedule therefore records:

```text
unit = candidate_batch_level_not_time
complete_native_schedule = false
realizable native cost = OPEN
```

No candidate field is named a round, cycle, or second.

## Logical liveness coordinate

Candidate liveness uses source semantic layers and just-in-time clean-value
allocation:

- source inputs are live from the start through their last source use;
- clean output/prefix values are live from their first through last source
  use; and
- each three-logical CCZ resource is live from its first coupling PPM batch
  through its terminal X-readout batch.

This is a logical requirement under the stated coordinate, not a processor
capacity admission or a memory placement. A finite backend must independently
close logical capacity, memory, routing, storage, and delivery.

## Strategy comparison

The checked frontier contains all six planned strategies.

### Fully frame-folded singleton baseline

All exact presented observables are retained, one PPM per semantic candidate
level. This supplies a deterministic baseline but no finite low-rate cost.

### Source-layer-aligned direct-CCZ batching

Only ready PPMs from the earliest source macro layer are considered together;
the exact compatibility screen splits them if required. Source layers remain
dependency coordinates, not surgery rounds.

### Measured-operator-product rewrites

Causal, commuting pairs are screened, but zero transforms are admitted. A
known outcome alone is insufficient: a valid rewrite still needs a
transported-stabilizer certificate, accessible logical support over the
relevant lifetime, and independent full-trace semantic replay.

### Selective Clifford materialization

PPMs whose presented observable differs from the bare injection observable are
screened, but zero transforms are admitted. The current trace does not certify
the minimal materialized frame subset or the resulting downstream frame, and
the finite Clifford operation family, routing, ancillas, and cost are `OPEN`.

### High-rate batch splitting

All causally ready PPMs are considered. Each frontier is split into exact
maximum compatible subsets. This is the selected general candidate strategy
for the width-5 result.

### Low-rate singleton fallback

Every PPM appears once in canonical topological order. All recorded reaction
ancestors precede their consumer. This is a semantically valid order only;
the backend operation family and cost are `OPEN`.

PPM count is recorded but is not an optimization objective. The frontier
orders metrics as candidate/reaction levels, peak live logical requirement,
added materialization ancillas, fallback calls, and maximum PPM weight.

## General width-5 result

The following claims are `NUMERICAL`, with exact relation identities and
lower-bound logic replayed independently:

| Quantity | Result |
|---|---:|
| PPM profiles | 60 |
| PPM pairs classified | 1,770 |
| Branch-possible Y PPMs | 0 |
| Pairs with nonzero commutator ANF | 30 |
| Pairs with a nonzero per-index axis-conflict ANF | 30 |
| Causally ordered PPM pairs | 1,206 |
| Pairs connected through a reaction update | 1,116 |
| Compatible pairs sharing logical support | 6 |
| Causal-path lower bound | 12 candidate levels |
| Conflict-clique lower bound | 12 candidate levels |
| Constructed optimized schedule | 12 candidate levels |
| Candidate batch sizes | 12, 12, 6, 6, then eight batches of 3 |
| Candidate fallback PPMs | 0 |
| Maximum presented PPM weight | 7 |
| Peak logical requirement in the stated liveness coordinate | 26 |
| Peak simultaneous live CCZ resource states | 4 |

The 12-level construction meets a 12-level exact lower bound, so it is
`PROVED` optimal inside this general logical candidate model. The number 12 is
not a surgery depth, native reaction depth, or runtime.

The source-layer-aligned and dynamic ready-frontier strategies both produce
12 levels for this instance. This equality is an instance result, not a
general theorem about QCLA widths.

## Finite-instance verdict

The selected finite candidate remains the coherent backend audit from
`T-20260831-004`. It is rejected. The artifact preserves:

- all 13 high-rate fields missing from the portable direct-CCZ capability;
- all 13 fields missing from the selected finite backend audit;
- the three factory values whose evidence belongs to the incompatible bb18
  architecture regime; and
- four Phase-B native-mapper obligations: operation family, logical-basis
  mapping, physical-support overlap rule, and ancilla/check construction.

The finite artifact explicitly contains:

```text
schedule = null
runtime_seconds = null
physical_qubits = null
failure_probability = null
native_schedule_emitted = false
```

The bb18 batch size, production cycles, and output error are not borrowed to
populate the selected time-efficient consumer. Neither the reviewed J300 XX
gadget nor T-state ports from other compatibility domains are used as a
direct-CCZ native operation.

## Independent replay

`src/ecdlp_ftqc/verification/direct_ccz_ppm_batching_replay.py` imports
neither the symbolic compiler nor the scheduler. From serialized data it
independently rebuilds:

- canonical Boolean polynomial operations;
- all 60 branch profiles;
- all 1,770 symplectic and per-index axis relations;
- the semantic DAG, PPM ancestor closure, and reaction closure;
- both 12-level candidate schedules and their liveness;
- the causal and conflict-clique lower bounds;
- the finite missing/incompatible lists and null schedule; and
- the 60-operation singleton fallback and six-strategy frontier.

Tamper tests reject changed commutator certificates and forged finite
schedules. The replay is `NUMERICAL` software verification of serialized
artifacts, not a proof of a physical implementation.

## Reproduction

Run:

```text
uv --native-tls run python scripts/run_direct_ccz_ppm_batching_cycle.py
```

Canonical outputs are under `experiments/runs/T-20260901-007/`:

- `general_candidate_batches.json`;
- `finite_instance_admission.json`;
- `low_rate_fallback_order.json`;
- `strategy_pareto_frontier.json`;
- `independent_replay.json`;
- `summary.json`; and
- `reproducibility.json`.

Phase C (`T-20260901-008`) may visualize these exact candidate levels and
split reasons. It must preserve the same general/finite/fallback separation
and may not relabel candidate levels as physical simultaneity.
