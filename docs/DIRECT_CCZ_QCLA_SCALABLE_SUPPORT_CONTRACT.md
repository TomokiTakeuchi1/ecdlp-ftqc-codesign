# Scalable direct-CCZ QCLA PPM support contract

## Scope

This contract refines the architecture-independent compatibility certificate by
exposing the logical Pauli support of each source-aligned PPM candidate.  A
support hyperedge is a set of logical value names.  It is not a placement,
connected surgery region, native operation, surgery round, or duration.

## Pinned support propagation

For every source-trace logical value `q`, the certificate propagates
`C† Z(q) C` through the ordered source gates and through the reviewed
direct-CCZ correction frame.  Source `X` gates do not change Z support.  A
source `CNOT(control,target)` applies the exact binary conjugation on both sides
of the support map.  Of the six canonical Figure 14(a) corrections, only
`CZ(c2,target)^a` and `CZ(c1,target)^b` change Z support after the target basis
change; they become conditional CNOT support updates.  The other conditional
CZ and Pauli corrections preserve Z support.

Each phase-one PPM adds its fresh resource value to the propagated data-column
support.  Each phase-two PPM is the singleton X support of that fresh resource.
The correction tuple must match the reviewed canonical map exactly; otherwise
the certificate fails closed.

## Exact and bounded modes

OOP traces at every selected width, and OOP/IP exact anchors at widths 5 and 8,
use canonical Boolean algebraic normal forms (ANFs).  Their possible-support
unions are exact, although a union is only the set of values that can occur in
some branch and need not occur simultaneously in one branch.

For IP widths above 8, the certificate propagates two objects independently:

- a sound may-support set, which is an upper envelope;
- 512 deterministic concrete branch evaluations, which provide lower
  witnesses.

If every may-support coordinate is witnessed, the possible-support union is
exact.  Otherwise the certificate reports the gap and labels the envelope
`CHECK`.  It never upgrades an unwitnessed may-support coordinate to an exact
possibility claim.  A witnessed-support union may combine coordinates seen in
different branches; it is not a simultaneous branch weight.  The separate
`maximum_sampled_branch_weight` field is the largest weight in one of the 512
concrete sampled branches.

## Falsified hypothesis

The hypothesis that every PPM support is independent of earlier measurement
outcomes is `FALSIFIED`.  The first exact OOP width-5 witness is
`direct-ccz:000005:ppm:zz_0`: logical value `a:0` is active exactly when
`direct-ccz:000000:outcome:zz_1 = 1`.  This does not invalidate the earlier
same-axis compatibility result; it shows that native mapping must handle a
branch-dependent logical support hypergraph.

## Explicit non-claims

The certificate does not produce a native mapper, prove connected geometric
supports, admit processor capacity, determine a surgery-round count, calculate
runtime, size a CCZ buffer, or calculate physical qubits or failure
probability.  Those fields remain null until a concrete backend construction
is supplied.
