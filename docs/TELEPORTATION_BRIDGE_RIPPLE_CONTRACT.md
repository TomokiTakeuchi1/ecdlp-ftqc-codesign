# Teleportation Bell-bridge ripple-carry contract

Task: `T-20260824-001`  
Experiment: `E-20260824-001`  
Trace schema: `ecdlp-ftqc/bell-bridge-ripple-trace`, version 1  
Timing schema: `ecdlp-ftqc/bridge-ripple-timing-config`, version 1

## Claim boundary

This cycle turns the Bell-bridge Gidney adder in Xu et al. Figure 6 into a
deterministic dependency and resource-sensitivity workload. It does not yet
provide an executable HGP, active-volume, or J300 backend.

| Claim | Evidence | Qualification |
|---|---|---|
| A generic Bell bridge transports an arbitrary one-qubit state after branch-dependent Pauli correction | `NUMERICAL` | 32 seeded states, all four Bell outcomes, maximum density-matrix Frobenius error `6.641107900062999e-16` |
| Widths 2--4 implement classical-basis in-place addition modulo `2^n` | `NUMERICAL` | All 16, 64, and 256 input pairs pass the explicit full-adder projection |
| Xu Figure 6 is a phase-correct parallel Gidney-adder construction | `LITERATURE` | The project has not independently reconstructed and compared the complete Figure-6 quantum channel |
| Finite schedules in this cycle represent executable logical time | `CHECK` | False at present: the unit is only `normalized_sensitivity_step`, and strict mode rejects it |

The classical-basis projection is intentionally weaker than a full coherent
adder proof. It checks bit and carry semantics but cannot detect every relative
phase error. No result below promotes it to a phase/channel proof of the full
source circuit.

## Pinned sources

- Xu et al., arXiv:2407.18490v1, Figure 6, local SHA-256
  `F50363822EE43C0DD0BCB4D0ACB502AA11207FC37B5175E60EADEBF892D38C05`.
  The source uses `k-1` temporary-AND Toffolis, Bell pairs between adjacent
  segments, five HGP data-patch families `a`--`e`, and six reactive ancilla
  patches. Segment bodies are parallel while the final reactive measurements
  remain sequential. The reported finite-size form is
  `c1 sqrt(k) log(k) + c2 k` logical cycles, without constants sufficient for
  this project's executable schedule.
- Litinski and Nickerson, arXiv:2211.15465v1, Figures 10, 16, and 24, local
  SHA-256
  `BF305E578AEFC986F4E74110EF55155E7C9711401B7D4E18BCB63BE304D2BC45`.
  Figure 10 supplies the generic bridge pattern. Figures 16 and 24 supply the
  segmented Gidney-adder structure and first/last-segment accounting. The
  source reports `n-1` CCZ consumptions, active volume
  `(n-1)(22+C_CCZ)-3`, and reaction depth `2n-3` for the sequential
  active-volume adder.

Active-volume blocks, HGP logical cycles, J300 syndrome rounds, and wall-clock
time are different units. This cycle does not convert among them.

## Architecture-neutral event contract

For an `n`-bit adder, `build_bridge_ripple_trace(n)` emits `n` segment events,
`n-1` carry bridges, `n-1` resource-state demands, and `6n-4` total macro
events. Each bridge connects only adjacent segments and has three distinct
logical carriers: the sender output, the receiver's speculative Bell half, and
the stored Bell half.

The lifecycle is:

1. prepare the receiver and stored halves of a Bell pair;
2. let the receiver segment use its half while the sender segment computes its
   output;
3. destructively measure the sender output and stored half in separate `XX`
   and `ZZ` components;
4. wait for both classical outcomes and receiver completion, then rebind the
   receiver carrier;
5. execute the source-ordered reactive measurement chain; and
6. finalize the output only after the last segment, last rebind, and last
   reaction.

The colloquial source description of teleporting a result “back in time” is
represented by this acyclic prepare/use/measure/rebind graph. There is no
reverse-time dependency edge.

Bell carry communication is also not a memory load or store. The three bridge
carriers have their own lifecycle and resource accounting; no processor-memory
residency or free-copy semantics are imported from the memory-I/O overlay.

## Independent replay

`replay_bridge_lifecycle` consumes only the trace and an event order. It
reconstructs bridge state rather than trusting scheduler bookkeeping and
rejects, among other cases:

- receiver use before Bell-pair preparation;
- Bell measurement before the sender output or stored half exists;
- rebind before both Bell outcomes and receiver completion;
- duplicate lifecycle actions; and
- a final trace with an unrebound bridge.

For width 256, replay accepts 255 bridges and 1,532 events, reaches a peak of
765 bridge carriers, and finishes with zero live provisional bridge carriers.
The peak equals three carriers per bridge because the source-parallel workload
can make all bridge lifecycles live together. It is a logical-carrier count,
not a physical-qubit estimate.

## Normalized scheduling sensitivity

Configuration `configs/architectures/bridge_ripple_sensitivity_v1.yaml`
assigns one normalized step to Bell-pair preparation, a segment, one Bell
component, and one reactive measurement. It uses 64 Bell-pair lanes, 64 segment
lanes, one reactive lane, and a swept number of Bell-measurement lanes.

The optional high-rate adapter reserves consecutive source-order groups of
exactly ten pairwise-disjoint `XX` Bell components. One reserved group consumes
one Bell-measurement lane for one normalized step; leftovers and all `ZZ`
components remain singletons. This imports only the exact-ten-disjoint-`XX`
eligibility shape from the J300 study. It does not establish a compatible
HGP-to-J300 carrier layout, compiler scratch allocation, finite duration, or
physical implementation.

The deterministic scheduler chooses the earliest-start candidate after this
reservation and enforces source dependencies, carrier exclusion, lane
capacity, and the serial reactive chain. An independent validator rechecks
coverage, dependencies, interval conflicts, exact batch size, pairwise support
disjointness, demand totals, and lifecycle replay. Any request for strict
execution rejects the `CHECK` timing profile.

## Reproduced sensitivity results

With one Bell-measurement lane:

| Width | Dependency critical path | High rate off | High rate on | Saved | Exact-ten batches |
|---:|---:|---:|---:|---:|---:|
| 4 | 5 | 8 | 8 | 0 | 0 |
| 8 | 9 | 16 | 16 | 0 | 0 |
| 11 | 12 | 22 | 13 | 9 | 1 |
| 16 | 17 | 32 | 23 | 9 | 1 |
| 32 | 33 | 64 | 37 | 27 | 3 |

For width 32, two or more Bell-measurement lanes give 34 steps with high rate
either disabled or enabled. Under this normalized model, the bottleneck has
already moved to the dependency/reaction structure, so the three admitted
batches no longer reduce makespan. This is a policy sensitivity, not a lower
bound and not proof that batching is useless under another circuit layout or
backend.

Width 32 consumes 31 modeled resource states in total. With high rate enabled,
the timestamped demand peak is 30 at one normalized step. The model records
this burst but assumes ideal supply; it does not yet simulate factory backlog,
buffers, routing, or stalls.

The width-256 structural trace has 255 bridges and 255 resource-state demands.
Its source-level segment macro depth is 1 versus an `n`-segment sequential
reference, while the executable critical path remains reaction- and
resource-dependent. The reported 1,280 logical coordinates are `5 x 256`
coordinates across the five source patch families; they are not a one-block
capacity claim.

## Reproducibility

Run:

```text
uv --native-tls run python scripts/run_bridge_ripple_cycle.py
```

The generator checks both source-PDF hashes before producing:

- `experiments/runs/T-20260824-001/summary.json`;
- `experiments/runs/T-20260824-001/bridge_width4_trace.json`;
- `experiments/runs/T-20260824-001/bridge_width32_lane1_schedule.json`; and
- `experiments/runs/T-20260824-001/width32_resource_state_demand.json`.

The summary records the task, Git state, input configuration, code/config
hashes, random seed, software environment, source hashes, validation status,
and every sweep point.

## Deliberately unresolved

- full phase/channel equivalence of the complete Xu Figure-6 adder;
- finite HGP/J300 bridge preparation, measurement, routing, and reaction costs;
- a compatible physical/code layout and failure budget;
- memory-I/O and bridge co-scheduling;
- factory production, retry, buffer, and stall behavior;
- controlled adders and carry-lookahead adders; and
- wall-clock and total physical-qubit estimates.

These are inputs to later cycles, not quantities inferred from the normalized
numbers above.
