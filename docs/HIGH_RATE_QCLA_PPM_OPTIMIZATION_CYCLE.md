# High-rate-aware QCLA-to-PPM implementation cycle

Task: `T-20260901-005`

## Purpose

Turn the reviewed clean out-of-place QCLA and exact single-event direct-CCZ
injection into a human-auditable, machine-checkable PPM program before
assigning a high-rate-surgery runtime. The first bounded target is `n=5`.
The compiler should then be reusable for the reviewed in-place QCLA without
passing through the existing seven-T CCX decomposition.

This document is a dependency plan. It creates no new circuit, runtime,
physical-qubit, or failure-probability result.

## Starting point

- `LITERATURE` / `NUMERICAL`: the source-pinned IP-QCLA and clean OOP-QCLA
  traces exist and pass exhaustive small-width basis replay.
- `NUMERICAL`: the isolated six-outcome direct-CCZ event passes all 64 local
  outcome branches against ideal CCX under the recorded convention.
- `CHECK`: the existing `n=5` OOP figures are source-aligned explanatory
  views, not a propagated or optimized PPM schedule.
- `OPEN`: no finite qLDPC backend currently closes timing, decoding,
  reaction, routing, factory-delivery, buffering, storage, and logical-error
  fields in one compatible contract.

## Required separation

The implementation must not use one Boolean named only
`high_rate_eligible`. Each candidate batch needs three separately reported
interpretations.

1. **General high-rate candidate.** Record pairwise commutation, Y content,
   logical-index-wise X/Z consistency, support multiplicity, bounded-degree
   construction requirements, and distance/LDPC obligations. Passing a
   logical sufficient-condition screen is not a finite gadget or runtime
   guarantee.
2. **Finite-instance candidate.** Test the exact native operation family,
   batch-size limit, logical-basis mapping, physical-support overlap,
   ancilla/check construction, rounds, decoder, and evidence status of one
   selected code instance. Internal noiseless Gross-code observations remain
   `CHECK` until captured in a reproducible record or primary source.
3. **Low-rate fallback.** Preserve a valid execution path for unsupported
   mixed-axis, Y-containing, heavy, or conflicting PPMs. A fallback may be
   semantically valid while its finite cost remains unresolved.

## Phase A: symbolic OOP direct-CCZ PPM trace (`T-20260901-006`)

Use the reviewed OOP source non-Clifford layers as macro-layer boundaries,
not as claimed surgery rounds. Lower each CCX directly with one `|CCZ>`
resource and retain CX as an explicit implementation-neutral Clifford unless
a later optimization chooses to fold or materialize it.

The trace must expose:

- injection-coupling PPMs and terminal resource measurements;
- measurement outcomes and reaction dependencies;
- conditional CZ and Pauli corrections;
- a canonical symbolic Clifford frame at every macro-layer boundary;
- the conjugated Pauli word actually presented to the next measurement;
- data, resource, and compiler-ancilla lifetimes;
- source-operation provenance and deterministic serialization.

Outcome-dependent frames should be represented symbolically or by canonical
equivalence classes. A global exponential enumeration of measurement
branches is not the intended representation. Local injection semantics and
small complete circuits still require independent channel or replay checks.

## Phase B: high-rate-aware batch optimization (`T-20260901-007`)

Build separate conflict relations for:

- causal or classical reaction dependency;
- Pauli anticommutation;
- an X/Z axis conflict on a shared logical index;
- Y content when the backend lacks a qualified Y-assisted construction;
- processor or live-logical capacity;
- resource-ancilla reuse;
- code-specific physical support, routing, or gadget limits.

Logical support overlap alone must not force serialization. Same-axis overlap
is retained as a general candidate and rejected only when a stricter finite
backend requires disjoint support. The optimizer should compare at least:

- fully frame-folded baseline;
- source-layer-aligned direct-CCZ injection;
- measured-operator-product rewrites using known outcomes;
- selective Clifford materialization;
- high-rate batch splitting;
- low-rate fallback.

For `n=5`, use deterministic exact search or a checked exhaustive frontier
where practical. The objective must prioritize scheduled reaction/surgery
depth under a named backend contract, then peak live logicals, added ancilla
space, low-rate calls, and PPM weight. PPM count alone is not the objective.

## Phase C: auditable visualization (`T-20260901-008`)

Retain the existing source overview and add one panel per macro-layer. Each
panel should show frame-in, source operations, injection PPMs, outcome arrows,
batch membership, split reasons, frame-out, and two separate general/finite
eligibility markers. The figure must be generated from the same trace used by
the verifier and scheduler.

## Phase D: in-place reuse and comparison (`T-20260901-009`)

Connect the reviewed IP-QCLA source trace to the same direct-CCZ PPM/frame
intermediate representation. Do not route this comparison through the
existing Selinger seven-T lowering. Report OOP and IP differences in:

- CCZ demand and source non-Clifford depth;
- symbolic reaction boundaries and scheduled PPM batches;
- cleanup/uncomputation overhead;
- live logical and prefix-scratch demand;
- high-rate candidate fraction and fallback demand.

## Phase E: scaling and finite resource integration (`T-20260901-010`)

Only after Phases A--D should width scaling be used for a width-256 estimate.
Sweep small and intermediate widths to identify discontinuities caused by
processor capacity, conflict coloring, frame growth, and finite batch limits.
Report direct width-256 structural scheduling when feasible; label any
interpolation and validate it out of sample.

A physical runtime requires one compatible backend contract containing:

- operation durations and parallel-throughput limits;
- memory load/store latency and bandwidth;
- routing and inter-block operation costs;
- controller reaction and decoder throughput;
- time-stamped CCZ demand, factory production, delivery, buffer, and stalls;
- physical-qubit accounting and a complete logical failure budget.

The final comparison must keep a general-high-rate optimistic bound, a
finite-instance estimate, and a low-rate-fallback estimate separate.

## Cycle exit criterion

The bounded `n=5` cycle is complete when one reproducible artifact contains
the source trace, symbolic direct-CCZ PPM trace, verified frame transitions,
candidate rewrites, three-way eligibility decisions, optimized batch
schedule, and matching human-readable figures. It must identify every
reaction boundary and every unsupported backend cost. Runtime and physical
resources remain unreported unless a finite capability gate admits them.

