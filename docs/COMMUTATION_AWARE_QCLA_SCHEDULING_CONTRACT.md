# Commutation-aware clean OOP-QCLA scheduling contract

## Scope and coordinate

This contract defines the architecture-independent scheduling model used by
`T-20260906-003` for clean out-of-place QCLA traces of widths 2 through 8.  A
CCX macro-layer contributes one direct-CCZ resource--data `ZZ` candidate level
and one fresh-resource `X`-readout candidate level.  These are logical
candidate levels, not QEC cycles or seconds.

The source-aligned trace is immutable and is emitted beside both transformed
variants.  Native support, placement, routing, port capacity, storage,
decoding, reaction latency, physical qubits, and logical failure probability
are not supplied by this model.  Every corresponding finite output remains
null.

## Pairwise dependency relation

Let `g_i` and `g_j` be positive-control CCX events in source order, with
`i < j`.  The model adds the directed edge `g_i -> g_j` when either condition
holds:

1. one event's target is a control of the other, so the two CCX permutations
   do not commute; or
2. at least one source CNOT layer lies strictly between their source layers.

The first condition is `PROVED` by exhaustive Boolean truth-table equality for
the union of the two three-bit supports.  It admits disjoint, shared-control,
and shared-target pairs and rejects both target--control orientations.  The
second condition deliberately preserves the source Clifford barrier instead
of assuming that a later frame rewrite can cross it.

Every ordered pair is classified.  Thus a same-macro pair is admitted exactly
when it commutes and has no intervening source Clifford barrier.  Each admitted
macro-set uses the common incoming Clifford frame and one globally fresh
three-qubit CCZ resource state per event, as established by
`T-20260906-002` / `RV-20260907-001`.

## Exact logical macro-depth theorem

For this complete ordered-pair dependency graph, assign each event the rank

`rank(g) = 1 + max(rank(p) for p -> g)`, with rank 1 for a source.

Events of equal rank form one macro-layer.  Every dependency increases rank,
and every same-rank pair is admitted by the complete pair classification, so
the grouping is feasible in this model.  The predecessor chain that determines
the maximum rank is a critical-path lower bound of the same length.  The
constructed schedule attains that lower bound.  Therefore its macro-depth is
`PROVED` optimal **within this stated logical model**.  This theorem is not a
claim of physical schedulability or optimal wall-clock time.

## Reactions and Pauli-product axes

Within one macro-layer there is no event-to-event classical reaction edge.
Every direct-CCZ event has a Z-type resource--data phase followed by an X-only
resource readout.  The common-frame correction channel factorizes across all
admitted events.

Between adjacent macro-layers the serialized schedule retains a conservative
reaction frontier containing all six outcome tokens of every predecessor CCX.
The exact minimal outcome subset is `CHECK`, and reaction duration is null.
These boundaries occur between macro-layers that are already separated by the
dependency model, so they do not alter the proved macro-layer count; they do
block conversion of that count to time.

Source CNOT layers remain barriers.  This cycle therefore does not choose a
physical implementation for bare logical CNOT or frame-conjugated H.  It only
preserves the logical policy established by the preceding H/CNOT trade study.

## Measurement-uncompute variant

A prefix-uncompute CCX may be replaced only when all of the following hold:

- the matching prefix producer is identified;
- the prefix target has an intervening quantum use;
- the cleanup is its final quantum use;
- destructive X measurement releases the prefix target exactly once; and
- outcome `m` installs the conditional frame update `CZ(c0,c1)^m`.

The frame is propagated through every later source Clifford and its final
support upper bound is recorded.  No later PPM may use the released target.
The independent verifier reconstructs this lifecycle without importing the
scheduler and checks both measurement branches, including relative phases.

Measurement cleanup does not imply a depth reduction in general.  Removing a
cleanup event shortens the exact macro-depth only when that event lies on every
remaining critical path of maximum length.

## Exact small-width results

| width | source CCX | source layers / levels | unitary macro / levels | measured CCX | cleanups | measured macro / levels |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1 | 1 / 2 | 1 / 2 | 1 | 0 | 1 / 2 |
| 3 | 3 | 2 / 4 | 2 / 4 | 3 | 0 | 2 / 4 |
| 4 | 5 | 3 / 6 | 3 / 6 | 5 | 0 | 3 / 6 |
| 5 | 10 | 6 / 12 | 4 / 8 | 9 | 1 | 3 / 6 |
| 6 | 12 | 6 / 12 | 4 / 8 | 11 | 1 | 4 / 8 |
| 7 | 17 | 7 / 14 | 5 / 10 | 15 | 2 | 4 / 8 |
| 8 | 19 | 7 / 14 | 5 / 10 | 17 | 2 | 5 / 10 |

The macro-depth and two-phase level counts are `PROVED` for the stated logical
dependency model.  Preservation of the clean OOP-QCLA arithmetic and the
measurement-uncompute channels is `NUMERICAL` at widths 2--8: the independent
replay checks 776 serialized pair decisions, 39,824 pair truth-table rows,
174,752 arithmetic input runs, 337,920 measured branch columns, and 337,908
phase-sensitive relative pairs with zero mismatch.

The table shows the critical-path qualification directly: cleanup reduces the
macro-depth at widths 5 and 7, but not at widths 6 and 8.  No monotone or
width-256 cleanup advantage is inferred from these bounded results.

## Stop gate

These results may become the structural input to a width-256 study only after
cross-review.  A width-256 depth, native-cycle, runtime, or footprint claim
requires a separate admitted dependency construction plus explicit physical
capacity and latency models.
