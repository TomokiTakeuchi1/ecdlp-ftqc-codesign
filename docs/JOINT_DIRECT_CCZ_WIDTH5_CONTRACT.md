# Width-5 joint direct-CCZ validation contract

Task: `T-20260906-002`  
Experiment: `E-20260906-002`

## Scope and evidence boundary

This contract validates logical semantics needed by a later
commutation-aware dependency model. It does not replace or edit the reviewed
source-aligned width-5 trace. At entry that baseline remains ten CCX events,
six Toffoli-bearing source layers, and twelve unitless PPM candidate levels.

The proposed four-macro-layer unitary grouping and three-macro-layer measured
cleanup grouping become eligible inputs to `T-20260906-003` only after the
checks below pass. Their eight and six two-phase PPM levels are structural
candidate envelopes, not an exact dependency-model schedule, surgery rounds,
or runtime.

The duplicate assumption identifier found at cycle start is resolved as:

- `A-0045`: reviewed self-derived one-bit H teleportation;
- `A-0046`: joint direct-CCZ common-frame hypothesis;
- `A-0047`: measurement-uncompute hypothesis.

## Exact CCX commutation rule

For positive-control gates

\[
U=\operatorname{CCX}(a,b;t),\qquad
V=\operatorname{CCX}(c,d;u),
\]

the implementation enumerates every computational-basis assignment on the
union of the two supports and compares `UV` with `VU`. The result is
`PROVED` inside this finite Boolean gate model:

> Two CCX gates commute exactly when neither gate's target is a control of the
> other gate.

Consequently disjoint, shared-control, and shared-target pairs commute.
Left-target/right-control, right-target/left-control, and bidirectional
target-control overlaps do not commute. Every rejected class carries the
first exact basis-state witness. The complete width-5 source contributes 45
pairs; the synthetic suite independently covers all six role-sensitive
classes.

## Width-5 macro-layer candidates

The unitary candidate groups the ten reviewed source gates as follows:

| Macro-layer | Source operations | Size | Overlap admitted inside layer |
|---|---|---:|---|
| T1 | four initial-generate CCXs | 4 | disjoint |
| T2 | prefix-propagate plus two short prefix-generate CCXs | 3 | disjoint/shared-control |
| T3 | long-prefix plus carry CCX | 2 | shared-control on `z:2` |
| T4 | prefix-propagate uncompute CCX | 1 | singleton |

The initial-propagate CNOT barrier remains between T1 and T2. T4 is not moved
into T3: `p:1:1` is a control of the long-prefix gate and the target of T4,
which is a noncommuting target-control overlap.

The measured-cleanup candidate retains T1--T3 and replaces T4 by one
destructive `X(p:1:1)` measurement and the conditional frame update
`CZ(b:2,b:3)^m`.

## Common-frame joint-injection identity

Every event receives a fresh three-logical `|CCZ>` resource. Within one
macro-layer all events use the same incoming Clifford frame `C`; no event's
outcome-conditioned correction is inserted into another event's incoming
frame.

For each event and measurement branch `s_i`, the independently reconstructed
single-event channel satisfies

\[
K_i(s_i)=\alpha_i(s_i)\,\operatorname{CCX}_i,
\qquad |\alpha_i|^2=1/64.
\]

For every admitted macro-layer:

1. all resource-data measurements are Z-type and commute;
2. all pre-H conditional fixups are CZ gates and commute;
3. the opening and closing H sets contain each distinct target exactly once;
4. post-H corrections are Z on controls and X on targets;
5. absence of target-control overlap makes corrections from different events
   commute;
6. resource triples are pairwise disjoint and consumed exactly once.

These relations permit the simultaneous protocol to be reordered into the
product of its single-event branch operators. Hence

\[
K_{\mathrm{joint}}(s_1,\ldots,s_k)
=\prod_i K_i(s_i)
=\left(\prod_i\alpha_i(s_i)\right)\prod_i\operatorname{CCX}_i.
\]

Presenting every logical data Pauli as `C^dagger P C` gives the covariant
physical identity

\[
K_{\mathrm{physical}}=C^\dagger K_{\mathrm{joint}}C,
\]

so the derivation is parameterized by one arbitrary common incoming Clifford
frame rather than one particular outcome assignment. Outcome-dependent
corrections remain in the outgoing frame, but no event-to-event reaction edge
is introduced inside the macro-layer.

The replay checks all 64 single-event branches. It also directly executes the
simultaneous statevector protocol for deterministic branch anchors on both
actual width-5 shared-control pairs and an independent shared-target pair.
The larger three- and four-event layers rely on the proved pairwise primitive
factorization instead of enumerating `64^k` outcomes.

## Measurement-uncompute identity

Immediately before the replaced cleanup gate,

\[
p=b_2 b_3.
\]

Destructive X measurement of `p` with outcome `m` contributes the amplitude
`(-1)^(m p)/sqrt(2)`. The conditional update `CZ(b:2,b:3)^m` contributes
`(-1)^(m b_2 b_3)`. Their product is the input-independent scalar
`1/sqrt(2)`, so both branches implement the same isometry as coherent CCX
uncompute after discarding its clean target.

The independent replay checks:

- all four local control assignments and both measurement outcomes;
- every one of the 1,024 width-5 `(A,B)` input basis columns;
- both outcomes for every column;
- all cross-column relative phases, which fixes arbitrary superpositions by
  linearity;
- that `p:1:1` is measured after its last use, never used afterward, and
  released exactly once;
- that the coherent baseline returns `p:1:1` to zero.

There is no later CCX/PPM in this width-5 source trace, so the cleanup outcome
does not change a later measured observable. It does remain as an ordered
Clifford-frame dependency through four intersecting bare CNOTs. The recorded
conservative final support is
`{a:2,a:3,b:2,b:3,z:2,z:3}`; this branch-dependent frame must be consumed by
the next dependency-model task and must not be treated as a free cleanup.

This is a complete finite-width channel check in the declared logical circuit
model. It is not a native QEC implementation or timing claim.

## Fail-closed conditions

Independent replay rejects:

- a changed CCX pair classification or noncommuting macro-layer member;
- a changed Figure-14 correction expression;
- resource aliasing, non-fresh resource values, or non-consumption;
- a changed PPM axis, support, phase, or outcome token;
- an event-to-event reaction edge inside an admitted joint layer;
- an early measurement, wrong conditional CZ, repeated release, or later use
  of the measured scratch;
- any finite native schedule, cycle, runtime, physical-qubit, or failure
  output.

## Interpretation of a passing result

A passing result admits the two width-5 semantic candidates for construction
of a separate dependency trace in `T-20260906-003`:

- unitary: ten CCXs in four macro-layers, with an eight-level two-phase
  structural envelope;
- measured cleanup: nine CCXs in three macro-layers, with a six-level
  two-phase structural envelope plus one cleanup measurement/frame update.

It does not yet prove those level counts optimal under the new dependency
model, and it does not authorize width-256 rescaling. `T-20260906-003` must
retain noncommuting order, source-Clifford barriers, reaction dependencies,
and lifetimes and must compare the new trace beside the immutable baseline.

Native cycles, seconds, physical qubits, and failure probability remain
`OPEN` and serialized as null.

## Reproduction

Run:

```text
uv --native-tls run python scripts/run_joint_direct_ccz_width5_cycle.py
uv --native-tls run pytest -q tests/unit/test_joint_direct_ccz_width5.py
```

Canonical artifacts are written under
`experiments/runs/T-20260906-002/`. The reproducibility record binds the input
trace, source files, environment, working-tree state, artifact hashes, and
validation status. No random seed is used.
