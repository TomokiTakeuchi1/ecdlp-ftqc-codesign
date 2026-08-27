# QCLA memory-I/O and high-rate scheduling contract

Task: `T-20260825-002`

## Scope

This cycle realizes the reviewed phase-exact QCLA adaptive-PBC trace on a
finite 60-logical-slot J300 model. It first selects one deterministic PBC event
order with a capacity-relaxed copy of the reviewed list scheduler, then applies
an explicit no-prefetch, no-compute-overlap memory schedule. The relaxed pass is
only an ordering device. Reported executable occupancy comes from the second
pass and never uses the relaxed capacity.

The result is a realizable upper bound for the fixed order. It is not a lower
bound, a placement optimum, or a joint compute/placement optimum.

## Logical-value origins

- `a:i` and `b:i` are memory input/inout values. Each begins in memory, has one
  usable location at a time, and returns to memory immediately after its final
  PBC use.
- Each QCLA `z` or `p` source ancilla is split into the reuse epochs recorded by
  the source trace. An epoch is prepared locally in a clean state at its first
  use, may be stored and reloaded while live, and is released clean after its
  last use.
- Compiler scratch carriers occupy the requested one or ten J300 logical slots.
  They are never treated as memory values or silently copied.

Local clean allocation/release timing is `CHECK`. The trace semantics prove
where a clean epoch may begin and end, but the reviewed J300 source does not pin
the physical initialization, reset, routing, or reaction-tail costs.

## Capacity and placement

For scratch count `s`, the source-value capacity is exactly `60 - s`. At every
fixed PBC event, all source values in that event's Pauli support must be in the
processor. Missing memory values are loaded; missing clean epochs are created
only at their declared first use. When space is needed, the deterministic policy
stores the non-required resident value whose next use is farthest away.

Stores at a boundary precede loads. Transfers are teleportation moves, not
copies. The independent replay rejects use before origin, free copies,
prefetch, invalid final returns, lost carriers, and occupancy above `60 - s`.

Transfer accounting is separated into:

- compulsory first loads of the `2n` input/inout values;
- reloads following a prior eviction;
- eviction stores, including live clean-ancilla spills;
- final returns of the `2n` data-register outputs.

## Timing and high-rate policy

The three compared policies are one-scratch serial, ten-scratch serial, and
ten-scratch high-rate. This separates the nine-slot payload penalty from the
benefit of exact batches of ten ready, pairwise-disjoint XX products using ten
distinct live scratch slots.

The admitted timing configuration has one transfer lane, one round per load or
store, and no prefetch or compute overlap. These transfer durations and several
native PBC costs remain `CHECK`. A zero-round transfer configuration is used
only as a regression boundary and must preserve every base event start.

## Resource-state demand

Every shifted compute event retains its original resource-state demand. The
artifact aggregates nonzero demand by shifted start round and proves total
demand conservation. Factory service, buffering, backlog, stalls, utilization,
routing, and failure are excluded; `ideal_supply_no_stalls_demand_trace_only`
is therefore a demand-timeline assumption, not a factory construction.

## Evidence limits

- Fixed-order capacity and action-stream replay invariants: `PROVED` by exact
  integer checks and independent deterministic replay.
- Generated counts and schedules: `NUMERICAL` deterministic observations.
- J300 transfer/native durations and clean lifecycle timing: `CHECK`.
- Any claim that high-rate batching improves the selected sensitivity schedule
  is `NUMERICAL`, not a proof for all orders or architectures.
