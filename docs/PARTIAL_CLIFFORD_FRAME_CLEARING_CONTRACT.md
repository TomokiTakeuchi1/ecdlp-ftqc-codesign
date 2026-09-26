# Partial Clifford-frame clearing contract

## Scope and convention

Task `T-20260909-001` evaluates one conservative way to materialize only the
part of a direct-CCZ byproduct frame that can obstruct a simultaneous H layer
in the reviewed in-place modulo-`2^n` QCLA.  It compares five frame policies at
width 5 and 256.  It does not construct a native qLDPC Clifford gadget or a
finite surgery schedule.

This task uses the byproduct convention

```text
physical state = F ideal state.
```

The existing direct-CCZ compiler stores the equivalent recovery frame `C`
with `F = C^dagger`.  If the desired logical Clifford is `U`, an incoming
byproduct frame is `F_in`, and the selected outgoing frame is `F_out`, the
physical Clifford must satisfy

```text
G F_in = F_out U,
G = F_out U F_in^dagger.
```

This equation, rather than a generator-subset heuristic, defines every policy.

## Policies

- Full frame conjugation selects `F_out = F_in`, giving
  `G = F_in U F_in^dagger`.
- Bare H propagation selects `G = U`, giving
  `F_out = U F_in U^dagger`.
- H frame tracking selects `G = I`, giving `F_out = F_in U^dagger`.
- Full frame clearing selects `F_out = I`, giving `G = U F_in^dagger`.
- Target-component partial clearing factorizes `F_in = A R`, where every
  interaction component touching an H target belongs to `A` and every
  disjoint component belongs to `R`.  Since `[R,U]=0`, it selects
  `F_out = R` and physically applies `G = U A^dagger`.

The last policy is deliberately conservative.  It is not claimed to minimize
the materialized Clifford, generator count, or depth.

## Ordered factorization

For each resolved measurement branch, construct an undirected interaction
graph from every active two-qubit `CNOT` and `CZ` frame generator.  Single-
qubit `X` and `Z` generators are assigned to the component containing their
logical qubit.  A component is materialized in full if any of its qubits is an
H target; all other components are retained in the frame.

Generators from distinct components have disjoint support and commute.
Therefore their original interleaving may be stably regrouped as `F_in = A R`
without changing the Clifford.  `R` is disjoint from the simultaneous H layer,
so `[R,U]=0`.  It follows exactly that

```text
(U A^dagger) F_in = U R = R U.
```

Removing an arbitrary set of CNOT generators would not provide this guarantee.
The implementation keeps generator order within each component and reverses
the materialized sequence when implementing `A^dagger`.

## Logical quantities reported

Every Toffoli macro layer has an opening and a closing target-H layer and two
direct-CCZ PPM candidate phases.  The reviewed commutation-aware IP schedules
contain 8 macro layers at width 5 and 30 at width 256.  All five policies are
evaluated on the same macro schedule and deterministic branch assignments.

The output reports:

- literal H, CNOT, and CZ generator occurrences;
- logical ASAP CNOT/two-qubit batch envelopes with same-wire serialization;
- a serialized logical-layer envelope after adding the two PPM candidate
  phases per macro;
- residual and peak frame-generator counts;
- the maximum presented phase-one PPM support weight;
- phase-one PPMs that leave the currently admitted Z/X-only no-Y family.

These are unsynthesized generator-circuit envelopes.  Only adjacent identical
self-inverse generators are cancelled.  They are neither minimum Clifford
circuits nor code-native H/CNOT schedules.  A lower literal CNOT count need not
produce a lower logical ASAP depth because the retained component changes the
order and support of later materializations.

## Branch protocol and evidence

Branch zero forces every correction condition to zero, branch one forces every
raw outcome variable to one, and remaining assignments use the deterministic
seed `T-20260903-002-support-witnesses-v1`.  The canonical run uses 16 branches
at width 5 and 32 at width 256.  Quantiles and maxima describe only those fixed
witnesses; they are not a population model, confidence interval, or exhaustive
maximum.

At width 5, every replayed macro and branch checks three Clifford identities
on both `X` and `Z` for every logical qubit, up to global phase:

- `F_in = A R`;
- `(U A^dagger) F_in = R U`;
- `U R = R U`.

The ordered factorization and commutation argument is `PROVED`; the concrete
width-5 operator replay and width-256 branch profiles are `NUMERICAL`.
An independent verifier reconstructs the macro schedule from a complete-pair
dependency oracle and replays every stored distribution summary and hash.

## Width-256 result

The following entries are nearest-rank medians over the fixed 32-branch set;
`PPM max` is the maximum over that same set.  The layer column adds the 60 PPM
candidate levels to the unsynthesized logical-generator ASAP envelope.

| Policy | Literal CNOTs p50 | CNOT batches p50 | Logical layers p50 | Presented PPM weight p50 / max | Z/X-only admitted |
|---|---:|---:|---:|---:|---|
| Full frame conjugation | 253,684 | 4,052 | 4,114 | 134 / 509 | yes |
| Bare H propagation | 0 | 0 | 120 | 300 / 572 | no |
| H frame tracking | 0 | 0 | 60 | 300 / 572 | no |
| Full frame clearing | 4,250 | 176 | 270 | 2 / 2 | yes |
| Target-component partial clearing | 3,843 | 284 | 380 | 11 / 16 | yes |

Relative to full clearing, the partial policy reduces median literal CNOT
occurrences by 9.58%, but increases the median CNOT-batch envelope from 176 to
284 and leaves a larger final residual frame (median 1,862 versus 1,273
generators).  Relative to retaining the full frame, it sharply reduces the
witnessed downstream PPM support while preserving the Z/X-only family.  The
result is therefore a three-way tradeoff among generator count, serialized
logical depth, and presented PPM support—not evidence that partial clearing is
already the fastest native strategy.

The full-conjugation count is especially important to interpret correctly: it
is a literal repeated expansion of the active target component around every H,
not a minimum Clifford synthesis.  Global resynthesis, native automorphisms,
and frame-cleaning surgery could change all count and depth comparisons.

## Fail-closed native boundary

This experiment does not supply:

- a native implementation of the materialized multi-qubit Clifford;
- addressable H or CNOT automorphisms;
- connected surgery support, placement, routing, contacts, ports, or capacity;
- decoder or classical-reaction latency;
- CCZ factory throughput, buffering, storage, or delivery;
- native cycles, runtime, physical qubits, or failure probability.

All finite native fields remain null.  The partial-clearing result is useful as
an intermediate compiler profile only; it cannot yet establish an advantage
over RASCqL or another architecture.

## Reproduction

```text
uv --native-tls run python scripts/run_qcla_partial_frame_clearing_cycle.py
```

The generator writes complete study vectors, independent replay, a compact
summary, and reproducibility hashes under
`experiments/runs/T-20260909-001/`.
