# Width-256 commutation-aware in-place QCLA contract

## Scope

Task `T-20260907-001` applies the reviewed common-incoming-frame joint
direct-CCZ model to the source-pinned Draper in-place QCLA at width 256.  The
arithmetic contract is

```text
(A, B) -> (A, A + B mod 2^256).
```

This is modulo a power of two.  It is not reduction modulo the secp256k1
prime, a controlled modular adder, or a complete ECDLP arithmetic block.

The result is an architecture-independent logical scheduling certificate.
Macro layers and their two PPM phases are not surgery rounds, physical
simultaneity, or elapsed time.

## Inputs retained unchanged

- `LITERATURE`: the reviewed source trace contains 3,987 gates: 2,458 CCXs,
  1,019 CNOTs, and 510 X gates in 40 source layers.
- `NUMERICAL`: exact Figure-14(a) direct-CCZ lowering maps every CCX to one
  fresh CCZ state, three resource-data Z-type PPMs, three resource-X
  measurements, and the reviewed conditional Clifford frame.
- `PROVED`: admitted positive-control CCXs can share one macro entry frame
  when neither target is a control of the other; shared controls and shared
  targets alone do not order them.
- `CHECK`: every inter-macro boundary conservatively retains all six outcome
  tokens per predecessor event.  The minimal reaction subset and its physical
  duration remain unresolved.

The coherent reverse network is retained.  Source steps 7--10 contain 1,229
CCXs and are not replaced by a measurement-cleanup shortcut.

## Dependency rule

For every ordered pair of source CCXs, add an edge when either condition holds:

1. one CCX target is a control of the other, so the positive-control CCXs do
   not commute; or
2. at least one source X or CNOT layer lies strictly between the two CCXs.

The X layers are essential IP barriers.  Although X does not change Z-support,
it does not in general commute through a CCX whose control or target it
touches.  Treating only CNOT layers as barriers would therefore be an invalid
IP generalization of the OOP scheduler.

Within a barrier segment, the streaming longest-path certificate retains the
deepest preceding target for each new control and the deepest preceding
control for the new target.  Across segments it retains the deepest preceding
event.  A separate complete pair scan reconstructs every edge and parent.

## Exact logical schedule

The complete width-256 pair audit contains:

| Quantity | Result | Status |
|---|---:|---|
| CCX vertices | 2,458 | `LITERATURE` source count |
| Ordered source pairs | 3,019,653 | `PROVED` |
| Dependency pairs | 2,012,691 | `PROVED` |
| Same-macro admissions | 1,006,962 | `PROVED` |
| Noncommuting target--control pairs | 12,996 | `PROVED` |
| Pairs crossing an X or CNOT barrier | 2,007,181 | `PROVED` |
| Source-aligned macro/candidate levels | 34 / 68 | `NUMERICAL` baseline |
| Commutation-aware macro/candidate levels | 30 / 60 | `PROVED` in this logical model |

The thirty macro sizes are:

```text
255, 253, 126, 64, 34, 23, 20, 28, 40, 61, 66, 72, 53, 70, 64,
253, 126, 64, 34, 23, 20, 28, 40, 61, 66, 72, 53, 70, 64, 255
```

The constructed depth equals an explicit thirty-event critical path.  This
proves optimality only for the stated pairwise logical dependency model.  It
does not prove a native high-rate schedule.

The width-2--8 `(source macro depth, commutation-aware macro depth)` bridge is
`(2,2), (4,4), (6,6), (12,8), (12,8), (14,10), (14,10)`.  Independent replay
executes all 87,376 input pairs after reordering and recovers exact in-place
addition with clean ancillas.

## Demand and support envelopes

The selected logical schedule consumes 2,458 fresh CCZ states and exposes
14,748 PPMs.  It contains 4,916 target-H applications, with peak macro demand
255 fresh CCZ states and 255 distinct target-Hs.  Source liveness has 495
ancilla values, including 240 reusable prefix-scratch values, and peaks at all
495 source ancillas.  With 512 input values, the fully resident source count is
1,007 logical values.  This liveness is reported in source-layer coordinates,
not as a native placement result.

Large-IP support is not promoted to exact Boolean-ANF evidence.  The same 512
deterministic branch witnesses as the reviewed scalable support study are
propagated through the new common-frame macro order, alongside a monotone
may-support upper envelope:

| Quantity | Result | Interpretation |
|---|---:|---|
| Maximum single-PPM weight upper bound | 1,006 | sound may-support bound |
| Maximum sampled single-branch PPM weight | 509 | concrete lower witness |
| Maximum level may-support union | 1,770 | upper envelope, not one branch weight |
| Maximum witnessed level support union | 1,770 | union of sampled incidences, not necessarily simultaneous |
| Maximum witnessed / may contact | 633 / 634 | sampled lower / sound upper |
| Unwitnessed may-incidences over all levels | 118,038 | unresolved gap |

Consequently the overall support envelope is `CHECK`, even though the 30/60
dependency depth is `PROVED` within its logical model.  A possible or witnessed
union is not a realizable code geometry and does not imply that all listed
supports occur in one branch.

## Fail-closed native boundary

The experiment fixes all of the following fields to null:

- native cycles and wall-clock runtime;
- connected-code support and addressability;
- placement, routing, ports, and storage;
- decoder and classical-reaction service;
- CCZ factory delivery and finite buffering;
- physical-qubit count and logical failure probability.

The next mapper must consume the 60 candidate levels and their branch-dependent
support bounds without equating a candidate level with a surgery round.

## Reproduction

```text
uv --native-tls run python scripts/run_width256_ip_commutation_aware_qcla_cycle.py
```

The generator writes the complete study, compact level table, independent
replay, summary, and source/output hashes under
`experiments/runs/T-20260907-001/`.
