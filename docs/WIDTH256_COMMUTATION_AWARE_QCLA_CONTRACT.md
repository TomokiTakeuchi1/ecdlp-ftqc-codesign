# Width-256 commutation-aware clean OOP-QCLA contract

Task: `T-20260906-004`  
Experiment: `E-20260906-004`
Review: `RV-20260907-003` `APPROVED` (Claude, 2026-09-07)

## Scope and selected result

This contract scales the reviewed positive-control CCX dependency rule from
widths 2--8 to the exact width-256 clean OOP-QCLA source trace. It preserves
the source-aligned baseline and reports a separate commutation-aware result.
All depths below are architecture-independent logical coordinates, not QEC
cycles or elapsed time.

The selected result is the commutation-aware **unitary** schedule:

| quantity | source-aligned baseline | selected unitary result |
|---|---:|---:|
| source CCX / direct-CCZ events | 1,229 | 1,229 |
| CCX macro-depth | 17 | 15 |
| two-phase candidate levels | 34 | 30 |

The fifteen-layer construction has a fifteen-event predecessor chain. Hence
construction and lower bound coincide and the value is `PROVED` within the
stated unlimited-capacity logical model. It does not prove that a high-rate
code can execute any level in one surgery round.

## Compact dependency certificate

For source-ordered CCXs `L` and `R`, retain `L -> R` exactly when either:

1. `target(L)` is a control of `R`, or `target(R)` is a control of `L`; or
2. a source CNOT layer lies strictly between their source layers.

The first condition is the reviewed positive-control CCX noncommutation
theorem. The second is the unchanged Clifford barrier policy.

Within one barrier segment, the rank of a new gate can be computed from only:

- the deepest prior gate targeting either new control; and
- the deepest prior gate controlling the new target.

At a new segment, the deepest gate from the preceding segments is also a
candidate. The emitted certificate stores one node and one selected
predecessor per CCX. It is therefore linear in CCX count.

A separate validation pass nevertheless scans all `754,606` width-256 CCX
pairs. It recomputes every dependency, the complete-pair decision-stream
hash, and the longest-path parent without serializing the quadratic table.
The compact and full-oracle ranks agree exactly. The same compact recurrence
also reproduces the approved unitary/measured raw-removal macro-depth pairs
for widths 2--8: `1/1, 2/2, 3/3, 4/3, 4/4, 5/4, 5/5`.

## Joint direct-CCZ logical demand

Each selected CCX macro-layer uses the reviewed common incoming frame:

- one fresh `|CCZ>` resource per CCX;
- three frame-conjugated resource--data Z-type PPMs per CCX;
- three fresh-resource X readouts per CCX;
- no event-to-event reaction edge inside the macro; and
- one opening and one closing frame-conjugated H per distinct target, not per
  event when targets are shared.

The complete workload therefore retains `1,229` fresh CCZ states and `7,374`
direct-injection PPMs. The peak logical burst is `255` CCZ states, `765` PPMs
in either phase, and `255` distinct target-H operations. The explicit bare
CNOT barriers contain `254`, `256`, and `256` CNOTs in source layers 2, 19,
and 20. Their physical implementation and duration remain unresolved.

Every inter-macro boundary conservatively retains all six outcomes per CCX in
the preceding macro. This is a dependency upper envelope: the minimal subset
and reaction duration remain `CHECK`/null.

## Macro-entry support certificate

Support is recomputed at the common frame entering each new macro. Events in
one macro all see that same frame; no earlier event in the macro is allowed to
change a later event's presented observable. After the two measurement
phases, all event corrections are folded into the outgoing frame in source
order, and source CNOT barriers conjugate the support map exactly.

The existing exact Boolean-ANF ZDD engine certifies each nonzero support
component. The independent replay repeats the macro-entry traversal and
reconstructs all thirty level aggregates. Across the selected unitary result:

- maximum individual PPM possible-weight upper bound: `1,003`;
- maximum candidate-level possible-support union: `1,647` logical values,
  including fresh resource values;
- maximum possible per-value contact within one level: `54`; and
- all possible supports are exact in the logical hypergraph coordinate.

The union is taken across branch-possible supports and different PPMs. It is
explicitly **not** the weight of one simultaneous branch and not connected
physical surgery geometry. Contact is multiplicity in the logical
hypergraph, not an admitted per-block port count.

## Live-value accounting

The source has `768` persistent input/output values and `240` clean prefix
scratch values, or `1,008` values under fully resident allocation. In macro
coordinates, scratch is counted live from its producer through coherent
uncompute. The exact peak is `1,004` live source values. Fresh three-value CCZ
resources are reported separately by level and are not folded into this
source-value count. Neither number is a physical-qubit footprint.

## Measurement-cleanup stop result

The local identity from `T-20260906-002` remains valid: after the last quantum
use of a prefix product `p=c0*c1`, destructive logical `X(p)` plus
`CZ(c0,c1)^m` implements coherent cleanup up to a branch-independent scalar.
That identity alone is insufficient to admit width-256 cleanup into the
current high-rate family.

There are 240 source prefix-uncompute candidates. The earliest candidates are
followed by as many as 236 other CCX events, so their conditional-CZ frame
updates must be propagated into later PPMs. More decisively, the last CCX that
uses each `p` as a control leaves a control--control correction term

`CZ(p,q)^{m_cc}`.

On the branch where only `m_cc=1`, the presented cleanup observable is

`CZ(p,q) X(p) CZ(p,q) = X(p) Z(q)`.

Thus every one of the 240 cleanup candidates has a concrete mixed-axis
witness. A logical `X(p)` measurement is not an X-only PPM under the retained
frame. Admitting it would require at least one of:

- materializing or clearing the relevant conditional Clifford frame;
- a code-level mixed-axis PPM construction; or
- a new joint protocol that incorporates cleanup and its incoming frame.

None is available in the current Z-only/X-only high-rate contract. The
cleanup proposal is therefore `FALSIFIED` **for this PPM family**, no cleanup
CCX is removed, and the reported measured alternative fails closed to the
same 15-macro/30-level unitary schedule. This does not falsify the abstract
measurement-uncompute channel.

## Independent replay and stop gates

The verifier independently rebuilds the source trace, scans all pairs,
derives the longest path, reconstructs macro support, checks scratch
lifetimes, and regenerates all 240 mixed-axis witnesses. It rejects mutations
to a rank, cleanup-axis admission, or any finite backend output.

The following remain null:

- native surgery or syndrome cycles;
- seconds;
- physical qubits;
- failure probability.

A later physical cycle may proceed only with a coherent high-rate code domain
that supplies addressable support, multiplicity/ports, placement/routing,
H/CNOT execution, reaction/decoder service, CCZ delivery and buffering,
memory service, timing, and an integrated failure budget.
