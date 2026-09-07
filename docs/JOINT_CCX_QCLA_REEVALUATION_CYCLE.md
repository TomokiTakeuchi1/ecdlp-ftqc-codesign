# Joint-CCX validation and width-256 QCLA re-evaluation cycle

Task: `T-20260906-001`

## Purpose

This cycle tests whether the reviewed direct-`|CCZ>` QCLA trace is
over-serialized by its inherited nearest-use wire-order dependencies.  It
does not weaken the reviewed baseline.  It introduces a separate
commutation-aware candidate only after the logical channel, adaptive frame,
ancilla lifetime, and measurement-uncompute rules have been checked at small
width.

The order of work is:

1. validate joint CCX semantics at width 5;
2. construct and replay a commutation-aware dependency model at small widths;
3. re-evaluate width 256 structurally;
4. attempt a finite-backend mapping only in a later, separately admitted
   cycle.

## Evidence boundary at cycle entry

- `PROVED`: in the existing source-aligned dependency model, OOP QCLA at
  width 5 has ten CCX events, six Toffoli-bearing source layers, and twelve
  unitless direct-CCZ candidate levels.  Width 256 has 1,229 CCX events,
  seventeen Toffoli-bearing source layers, and thirty-four unitless candidate
  levels.
- `PROVED`: within the current architecture-independent screen, same-axis
  logical support overlap is not itself a conflict.  A candidate batch must
  still have exact commutation, per-index axis consistency, no branch-possible
  Y, no causal relation, and no consumed-resource reuse.
- `CHECK`: the current QCLA DAG adds nearest-use wire-order edges whenever two
  operations share a logical value.  Some of these edges may be conservative
  for commuting controlled-X operations.
- `CONJECTURE`: commuting CCX events with compatible shared controls, and
  possibly compatible shared targets, can be lowered jointly under one common
  incoming Clifford frame without introducing event-to-event reaction edges.
- `CONJECTURE`: the final clean prefix-AND uncompute can be replaced by an
  X-basis measurement and a conditional CZ-frame update, reducing the width-5
  unitary Toffoli depth from four to three.
- `OPEN`: neither the proposed depth reduction nor the current candidate-level
  count establishes code-level simultaneous support, surgery cycles, seconds,
  physical qubits, or failure probability.

The existing reviewed width-5 and width-256 artifacts remain immutable
baselines.  New outputs must use distinct model and schema identifiers.

## Width-5 claims to test

The clean OOP width-5 source contains these ten CCX events:

- four initial-generate events `CCX(a_i,b_i;z_{i+1})`, for `i=0,...,3`;
- one prefix-propagate event `CCX(b_2,b_3;p_{1,1})`;
- two prefix-generate events `CCX(z_1,b_1;z_2)` and
  `CCX(z_3,b_3;z_4)`;
- one long-prefix event `CCX(z_2,p_{1,1};z_4)`;
- one carry event `CCX(z_2,b_2;z_3)`;
- one uncompute event `CCX(b_2,b_3;p_{1,1})`.

The first alternative to verify is the following four-layer unitary grouping:

- `T1`: the four initial-generate events;
- `T2`: the prefix-propagate event and both prefix-generate events;
- `T3`: `CCX(z_2,p_{1,1};z_4)` and `CCX(z_2,b_2;z_3)`;
- `T4`: the prefix-propagate uncompute.

This grouping preserves the intervening source-CNOT barrier before `T2`.
Within `T2` and `T3`, the overlaps are control--control.  `T4` remains after
`T3` because `p_{1,1}` is a control of the long-prefix event and the target of
the uncompute; those controlled-X operations do not commute.

If the common-frame joint injection is valid, the provisional consequence is
eight unitless PPM candidate levels: one resource-data `ZZ` level and one
fresh-resource `X` readout level per CCX macro-layer.

The second alternative replaces `T4` by destructive X measurement of
`p_{1,1}` and a conditional `CZ(b_2,b_3)` Clifford-frame update.  If its whole
circuit channel and lifecycle checks pass, the provisional consequence is
nine CCX events, three CCX macro-layers, six unitless PPM candidate levels,
and a separately accounted cleanup measurement/frame update.

These values are hypotheses until the validation gates below close.

## Validation gate A: logical commutation and causality

- Derive or exhaustively verify the exact commutation condition for every
  overlapping pair of controlled-X gates on the union of their supports.
- Classify control--control, target--control, control--target, and
  target--target overlap separately.  Do not infer causality from a changed
  frame signature alone.
- For each prior measurement outcome, test whether the next presented
  observable `F^dagger P F` changes.  Add a reaction edge exactly when the
  executable observable, its sign, its basis-changing gate, or its required
  correction depends on that outcome.
- Preserve source order for noncommuting operations and preserve all
  preparation, use, measurement, release, and source-Clifford barriers.
- Emit minimal witnesses for every rejected overlap class.

Exit criterion: the pair classifier agrees with independent truth-table or
matrix checks for all width-5 event pairs and for targeted synthetic examples
covering all four overlap orientations.

## Validation gate B: joint direct-CCZ lowering

- Lower a causally ready commuting CCX set relative to one common incoming
  frame, rather than serially feeding each event's corrections into the next
  event.
- Use fresh resource triples for every CCX.  Test a first phase containing all
  resource-data `ZZ` measurements and a second phase containing all fresh
  resource-`X` readouts.
- Verify all outcome branches directly when tractable; otherwise use a proved
  factorization together with exhaustive low-cardinality anchors.
- Check that the joint corrected channel equals the simultaneous ideal product
  of the CCX gates up to the declared final Clifford/Pauli frame.
- Test shared-control and shared-target commuting cases independently.  A
  result for shared controls must not be generalized to shared targets without
  its own proof.
- Check common or shared target-H handling explicitly under the selected
  frame-conjugated-H policy.

Exit criterion: an implementation-independent verifier reproduces the joint
channel for every admitted width-5 macro-layer and rejects a mutated outcome,
correction, event order, or resource-reuse record.

## Validation gate C: measurement uncompute

- Verify the local temporary-AND identity consisting of destructive X
  measurement of the target and the outcome-conditioned CZ on its controls.
- Replay the complete width-5 OOP channel, not only the isolated gadget.
- Confirm that `p_{1,1}` is no longer required quantumly, is measured only
  after its last use, and is released exactly once.
- Represent the conditional CZ as an ordered Clifford-frame update and expose
  any later observable whose basis or support depends on its outcome.
- Compare the unitary-uncompute and measurement-uncompute variants on every
  computational-basis input and on phase-sensitive superposition tests.

Exit criterion: both variants implement the same declared OOP addition
channel, return all required clean ancillas, and have independently replayed
reaction/frame records.

## Small-width commutation-aware dependency model

Only after gates A--C close should a new dependency builder be introduced.
It must not delete all shared-wire edges.  It must instead:

- retain the relative order of overlapping noncommuting gates;
- remove an inherited wire-order edge only when the joint-channel rule admits
  the pair or macro-set under the same incoming frame;
- preserve classical reaction dependencies, source-Clifford barriers, and
  value lifetimes;
- distinguish unitary cleanup from measurement cleanup;
- emit the old source-aligned model beside the new model for comparison.

Widths 2 through 8 must pass exhaustive classical reversible semantics,
phase-sensitive channel anchors, trace determinism, dependency acyclicity,
lifetime replay, and exact schedule optimality where brute force is feasible.
The width-5 targets are:

| Variant | CCX count | CCX macro-depth | Unitless PPM candidate levels | Status at cycle entry |
|---|---:|---:|---:|---|
| reviewed source-aligned | 10 | 6 | 12 | `PROVED` in the existing model |
| commutation-aware unitary | 10 | 4 | 8 | `CONJECTURE` |
| commutation-aware measured cleanup | 9 | 3 | 6 plus cleanup | `CONJECTURE` |

## Width-256 structural re-evaluation

Width 256 is admitted only after the small-width gates pass.  The rerun must
report, separately for the source-aligned, commutation-aware unitary, and
measurement-uncompute variants:

- exact logical CCX, CNOT, H, measurement, and conditional-frame demand;
- algorithmic CCX macro-depth and the dependency-chain witness attaining it;
- unitless direct-CCZ PPM candidate levels with a matching lower bound or an
  explicit optimality gap;
- every candidate level's event count and peak simultaneous `|CCZ>` demand;
- resource-data and resource-readout PPM counts, maximum support-union
  envelopes, per-logical-index multiplicity, and possible-contact summaries;
- all new branch-dependent supports and reaction edges introduced by measured
  cleanup;
- maximum live logical values, temporary-prefix lifetimes, and cleanup demand;
- deterministic hashes and an independent replay using a linear-size
  structural certificate rather than a global quadratic pair table.

The comparison must keep the reviewed source-aligned width-256 values
`1,229 CCX`, `17` Toffoli-bearing source layers, and `34` candidate levels as
the baseline.  No reduced width-256 depth is to be quoted before the rerun
produces its exact witness.

## Finite-backend stop gate

The structural rerun must leave surgery rounds, wall-clock time, physical
qubits, and logical failure probability null.  A later finite mapping may fill
them only after one coherent code/architecture domain specifies:

- the admitted simultaneous same-axis PPM family, including repeated logical
  participation and per-block port/check constraints;
- placement, bridge, routing, and distance preservation;
- cycle time, decoding service, and classical reaction latency;
- direct-CCZ delivery rate, burst buffering, storage, and retry policy;
- memory load/store service and live-capacity constraints;
- native operation and memory error models with one integrated failure budget.

## Dependency-ordered implementation tasks

- `T-20260906-002`: prove and replay the joint direct-CCZ and measurement-
  uncompute semantics at width 5.
- `T-20260906-003`: build the commutation-aware OOP-QCLA dependency model and
  validate exact schedules through width 8.
- `T-20260906-004`: re-evaluate the width-256 OOP-QCLA structural demand using
  only the verified rules.

## Cycle completion criterion

The cycle closes only when the new width-5 channel and cleanup variants pass
independent verification, the small-width dependency builder passes every
semantic and lifetime check, and width 256 has a deterministic structural
certificate.  A failure at any earlier gate is a valid result: the existing
12-level width-5 and 34-level width-256 source-aligned candidates remain the
admitted baselines.

## T-20260906-002 semantic-gate result — approved

The first implementation task passes its bounded logical-semantic gates. This
does not close the scheduling or width-scaling parts of the cycle.

- **Gate A (`PROVED` under the positive-control CCX model):** exact Boolean
  permutation replay classifies all 45 pairs of the ten width-5 source CCXs.
  Thirty-six commute and nine do not. Two CCXs commute exactly when neither
  target is a control of the other; the test set includes disjoint,
  shared-control, shared-target, and both target-control orientations.
- **Gate B (`NUMERICAL`):** the four proposed unitary macro-groups have sizes
  4/3/2/1 and contain ten admitted within-group pairs. Common-frame
  factorization, ten fresh resource triples, all 64 single-event branches,
  two actual shared-control anchors, and one synthetic shared-target anchor
  pass. No event-to-event reaction edge is admitted.
- **Gate C (`NUMERICAL`):** replacing the final CCX uncompute by destructive
  `X(p:1:1)` and outcome-conditioned `CZ(b:2,b:3)` preserves all 1,024
  width-5 computational-basis columns and both measurement outcomes, with
  2,046 relative-phase comparisons. The outcome-dependent frame is retained,
  propagated through four later CNOTs, and conservatively reaches
  `{a:2,a:3,b:2,b:3,z:2,z:3}`; it is not treated as free cleanup.

Consequently, the 4-layer unitary and 3-layer measured-cleanup groupings may be
used as semantic inputs to `T-20260906-003`. Their corresponding 8- and
6-level two-phase values remain `CHECK` envelopes, not schedules, lower
bounds, surgery rounds, or time. The reviewed 12-level width-5 and 34-level
width-256 baselines remain unchanged, and every finite-backend output remains
null. Assumption identifiers were normalized at task entry because the plan
had reused `A-0045`: H teleportation retains `A-0045`, joint direct CCZ uses
`A-0046`, and measurement uncompute uses `A-0047`.

## T-20260906-003 small-width scheduling result — approved

The separate dependency model closes the bounded logical scheduling gate at
widths 2--8 and is approved as `RV-20260907-002`.

- **Exact model-relative schedule (`PROVED`):** every ordered CCX pair is
  classified. A dependency is retained for noncommuting target--control
  overlap or an intervening source CNOT layer. Earliest longest-path ranks
  form legal common-frame macro-layers and attain the explicit critical-path
  lower bound.
- **Unitary result (`PROVED` in that model):** macro-depth through widths 2--8
  is `1,2,3,4,4,5,5`, corresponding to two-phase candidate levels
  `2,4,6,8,8,10,10`.
- **Measured cleanup (`NUMERICAL` semantics, `PROVED` schedule conditional on
  that transformation):** macro-depth is `1,2,3,3,4,4,5`. Cleanup reduces
  depth at widths 5 and 7, but not at 6 or 8 because another critical path
  dominates.
- **Reaction boundary (`CHECK`):** all six predecessor-event outcomes are
  conservatively retained between macros. The minimal subset and duration are
  unresolved.

Independent replay covers 776 pair decisions, 39,824 pair truth-table rows,
174,752 arithmetic runs, 337,920 measurement-branch columns, and 337,908
relative-phase pairs without mismatch. Width 256 remains unchanged at its
reviewed source-aligned 34 candidate levels until `T-20260906-004`; no native
cycles, seconds, physical qubits, or failure probability are inferred.
