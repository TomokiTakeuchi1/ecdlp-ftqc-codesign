# Scalable direct-CCZ QCLA PPM compatibility contract

Task: `T-20260903-001`  
Experiment: `E-20260903-001`  
Coordinate: `candidate_batch_level_not_time`

## Claim boundary

This task certifies the source-aligned two-phase construction under the
architecture-independent logical screen fixed by `A-0036`:

1. no causal order between PPMs in one batch;
2. universal commutation;
3. one Pauli axis per shared logical index;
4. no branch-possible `Y`;
5. no consumed-resource reuse.

The certificate does **not** construct a code-level simultaneous-measurement
gadget. Candidate levels are not surgery rounds, source CNOTs and basis
changes have no admitted finite cost, and no placement, memory, routing,
decoder, reaction, factory, buffer, physical-qubit, runtime, or failure result
is produced.

## Why the global pair table is unnecessary

The reviewed symbolic compiler keeps deferred corrections in
`ordered-conditional-cliffords-with-anf-conditions-v1`. At an injection
boundary its possible generators are `X`, `Z`, `CNOT`, and `CZ`:

- Figure-14(a) contributes conditional `CZ`, `Z`, and `X` corrections;
- target-touching pre-H `CZ` corrections become `CNOT` at the event boundary;
- source pass-through operations conjugate the frame only by `X` or `CNOT`.

These generators preserve the Z-type Pauli subspace branch by branch. `X` and
`Z` change at most the sign of a Z-type word, `CNOT` maps a Z-type word to
another Z-type word, and `CZ` fixes it. Conditional selection between the
original and conjugated branches therefore also remains Z type.

This gives two proof cases for every source Toffoli layer:

- **Injection phase 1:** all three resource-data measurements per event are
  bare `ZZ`. After any incoming frame they remain branchwise Z type. Shared
  support can therefore only use the same Z axis; commutation and no-Y follow
  without comparing pairs.
- **Injection phase 2:** all three readouts per event are single-resource `X`.
  Resource values are globally fresh, appear once in this phase, and never
  enter a deferred frame generator. These measurements are disjoint X
  observables.

The source trace separately guarantees disjoint gate support inside each
algorithmic layer. The certificate checks that all source dependencies advance
to a later layer, that every source Toffoli maps to one canonical six-PPM
event, that all resources are unique, and that the event DAG is an exact copy
of the source DAG. Consequently the three phase-1 PPMs per event can occupy
one logical candidate level and the three phase-2 PPMs the next. Processing
source layers in order gives a valid logical construction with two candidate
levels per non-Clifford source layer.

The argument is generator closure, not an empirical extrapolation from small
widths. Its machine certificate has linear size
`O(source gates + source dependencies + PPMs)` and stores batch-membership
hashes and implicit pair counts, never pair records.

## Optimality inside the logical model

The existing weighted causal bound assigns weight two to every source
Toffoli and zero to source Cliffords. Each direct-CCZ event necessarily orders
its `ZZ` phase before its resource-`X` phase. When the two-phase construction
equals this longest-path bound, it is both a constructive upper bound and a
matching lower bound.

For every selected OOP/IP width
`5, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 128, 129, 255, 256, 257`,
the equality holds. The resulting candidate count is therefore `PROVED` only
inside the stated logical screen.

At width 256:

| Variant | Direct-CCZ events | PPMs | Global pairs not materialized | Candidate levels | Causal lower bound |
|---|---:|---:|---:|---:|---:|
| clean OOP | 1,229 | 7,374 | 27,184,251 | 34 | 34 |
| in-place | 2,458 | 14,748 | 108,744,378 | 68 | 68 |

The maximum candidate batch contains 765 PPMs (255 events times three), while
the earlier 1,530-PPM number is the combined demand of both ordered phases in
one source layer.

## Exact-anchor bridge

Widths 5 and 8 retain the full symbolic Boolean-ANF classifier. For both OOP
and IP variants, the experiment compares every compact batch-membership digest
with the exact source-layer-aligned schedule and checks every materialized
within-batch pair against the full compatibility predicate. It also confirms
that all exact profiles are Y-free and that the compact, exact source-aligned,
and exact optimized candidate counts all equal the causal lower bound.

This bounded bridge is `NUMERICAL`; the generator-closure theorem and each
validated structural certificate are `PROVED` relative to their explicit
logical premises.

## Fail-closed behavior

A malformed PPM axis, non-CSS deferred-frame generator, reused resource,
source/event mismatch, or dependency violation returns `FALSIFIED` with the
first deterministic width/layer/gate/event witness and no candidate count.
The independent replay reconstructs all source-layer memberships and hashes
without importing the compiler, certifier, or any scheduler. Mutated hashes
and fabricated finite runtimes fail validation.

## Reproduction

```text
uv --native-tls run python scripts/run_direct_ccz_ppm_compatibility_cycle.py
uv --native-tls run pytest -q tests/unit/test_direct_ccz_ppm_compatibility_certificate.py
```

Canonical outputs are under `experiments/runs/T-20260903-001/`.
