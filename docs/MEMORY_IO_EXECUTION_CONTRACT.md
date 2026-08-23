# Memory-I/O execution contract

- Task: `T-20260823-001`
- Experiment: `E-20260823-001`
- Schema: `ecdlp-ftqc/memory-io-overlay` version 1
- Source import: `docs/RUNTIME_METADATA_IMPORT_MANIFEST.md`

## Scope

This bounded cycle connects the reviewed Gidney QEC-neutral DAG and adaptive
PBC schedule to explicit memory--processor logical-state movement. It adds
deterministic placement, load/store actions, processor occupancy, transfer
lanes, and independent replay without changing DAG schema v1.

The cycle does not implement Bell carry teleportation, carry lookahead,
factory stalls, routing, wall-clock conversion, or a jointly optimized
parallel circuit-and-I/O schedule. It does not close project-wide
`T-BOOT-002` or `T-BOOT-005`.

## State and transfer semantics

A logical state has one usable location. A load moves it from memory into the
processor; a store moves it back. Placement cannot treat the pre-move source
as a second usable copy.

Strict memory values are input/inout values whose residency or preservation
obligation requires external memory. Gidney carry temporaries are created in
the processor, remain local while live, may be spilled at a partition
boundary, and are consumed without a terminal store when released in the
same partition.

The adapter fails closed on an unknown origin, missing creation/release
boundary, dirty or borrowed state without restoration evidence, or a mismatch
between memory and occupancy support.

## Placement policies

### Fixed-order persistent Belady v1

For a supplied deterministic unit order, the policy:

- loads only values required by the current unit;
- retains resident values when capacity permits;
- evicts the value with the farthest next use, using value ID as a canonical
  tie-breaker;
- reduces available memory capacity by live local occupancy;
- prefetches nothing; and
- returns every final resident strict-memory value.

This is exact for the admitted fixed order and action space. It is not an
optimal ordering of a parallel DAG.

### Maximal-prefix partition reference v1

A partition is the longest source-operation prefix whose memory-interface
union plus peak local occupancy fits the processor. Widths 2--4 use exhaustive
dynamic programming over retained boundary values. Its action ledger separates
baseline interface transfers, partition spills, and partition reloads.

The exact reference rejects widths above four. Large-width event-order
placement uses the scalable fixed-order policy and remains a heuristic result.

## Adaptive-PBC integration

The reviewed adaptive-PBC scheduler selects its event order before memory
placement. Each PBC event is mapped back through its logical primitive to the
source DAG node. Processor-generated lifetimes are then remapped onto that
event order, including carry values allocated early by independent branches.

The current timing overlay reserves the requested scratch slots, applies
Belady to the remaining logical capacity, and inserts stores before loads at
each boundary. Configuration v1 forbids prefetch and transfer/compute overlap.
Consequently the result is a realizable conservative upper bound for the fixed
event order, not a globally optimized schedule.

Zero-duration transfers are a regression boundary only. They must preserve
every reviewed PBC event start and end exactly.

## Timing evidence

`configs/architectures/j300_memory_io_v1.yaml` assigns one round to load and
store with one transfer lane. Both durations are `CHECK` sensitivity values.
The J300 literature audit does not supply memory-transfer duration, bridge
preparation, routing, setup/readout, or reaction-tail evidence.

Strict mode therefore rejects every nonempty schedule using this timing
profile. Sensitivity mode records transfer counts and a conditional makespan
but does not convert rounds to seconds.

## Reproduced legacy reference

`NUMERICAL`, source commit
`75a6e83d5acde37f0987ab867352ee8b2c6afd10`:

| Width | Capacity | Partitions | Loads | Stores |
|---:|---:|---:|---:|---:|
| 2 | 5 | 1 | 4 | 4 |
| 2 | 3 | 3 | 6 | 6 |
| 3 | 8 | 1 | 6 | 6 |
| 3 | 6 | 3 | 8 | 8 |
| 3 | 4 | 5 | 10 | 10 |
| 4 | 11 | 1 | 8 | 8 |
| 4 | 8 | 3 | 11 | 11 |
| 4 | 5 | 7 | 14 | 14 |

These are exact small-width transfer references, not runtime results.

## PBC I/O sensitivity

`CHECK`, one lane, one round per load/store, no prefetch or compute overlap:

| Width | Base rounds | Loads | Stores | Added rounds | Combined rounds |
|---:|---:|---:|---:|---:|---:|
| 2 | 846 | 4 | 4 | 8 | 854 |
| 4 | 2,868 | 8 | 8 | 16 | 2,884 |
| 16 | 15,000 | 32 | 32 | 64 | 15,064 |
| 32 | 31,176 | 100 | 100 | 200 | 31,376 |

Width 32 exceeds the full-retention capacity available after reserving one
scratch slot, so its fixed adaptive-PBC event order causes eviction and reload.
This is a workload/order/policy observation, not a lower bound on all possible
width-32 schedules.

All four workloads still have zero exact-ten-XX high-rate batches. The cycle
does not claim that I/O prevents a future teleportation-ripple or QCLA trace
from exposing high-rate batches.

## Validation requirements

Every accepted schedule must satisfy:

1. no load before processor creation or before a recorded spill;
2. no load of an already resident value;
3. no store of a non-resident value;
4. all required operands resident before execution;
5. processor occupancy within capacity;
6. no overlap on one transfer lane;
7. all boundary transfers complete before the consuming event;
8. all required final values returned; and
9. deterministic canonical serialization.

## Reproduction

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_memory_io_cycle.py
```

The generated result is
`experiments/runs/T-20260823-001/summary.json`. Generated files must be changed
through the source, configuration, or generator rather than manual editing.
