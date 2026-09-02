# Direct-CCZ QCLA scaling contract

## Scope

Task `T-20260901-010` extends the reviewed width-five OOP/IP comparison in two
strictly separated modes:

1. exact symbolic anchors at widths 5 and 8; and
2. compact structural analysis through widths 255, 256, and 257.

The structural sweep evaluates the generated width directly. It does not fit
or interpolate a width-five result. Its coordinates are source layers and PPM
dependency levels, never QEC cycles, surgery rounds, or wall-clock time.

## Main results

The exact anchors close as follows:

| Variant | Width | CCZ events | PPMs | Materialized pairs | Candidate levels | Causal lower bound | Peak semantic logicals | Peak live CCZ states |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OOP | 5 | 10 | 60 | 1,770 | 12 | 12 | 26 | 4 |
| IP | 5 | 20 | 120 | 7,140 | 24 | 24 | 26 | 4 |
| OOP | 8 | 19 | 114 | 6,441 | 14 | 14 | 44 | 7 |
| IP | 8 | 38 | 228 | 25,878 | 28 | 28 | 44 | 7 |

All four candidates contain no fallback PPM and meet their exact causal lower
bound. This is `PROVED` only within the exact logical candidate model at those
two widths.

The direct width-256 structural result is:

| Quantity | OOP | IP |
|---|---:|---:|
| Source operations | 1,995 | 3,987 |
| Direct-CCZ events | 1,229 | 2,458 |
| PPMs | 7,374 | 14,748 |
| Theoretical pair records | 27,184,251 | 108,744,378 |
| Non-Clifford source layers | 17 | 34 |
| Weighted causal lower bound | 34 | 68 |
| Cleanup operations / Toffolis | 495 / 240 | 1,738 / 1,229 |
| Peak source-layer events / PPMs | 255 / 1,530 | 255 / 1,530 |

The IP event count, non-Clifford source-layer count, and causal lower bound are
twice OOP at every selected width. This is a `NUMERICAL` observation over the
recorded sweep, not a proof for arbitrary width. Around each tested power of
two from 8 through 256, the causal bound is unchanged from `2^k-1` to `2^k`
and rises immediately at `2^k+1`; the exact boundary rows are serialized so
the pattern can be replayed rather than inferred from prose.

## Selected widths

The deterministic sweep is

`5, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 65, 127, 128, 129, 255, 256, 257`.

The windows around powers of two expose changes in the prefix construction.
Widths 5 and 8 additionally materialize every symbolic PPM pair and run the
existing exact candidate optimizer. Wider points never materialize pair
records.

## Structural quantities

For each OOP/IP trace, the compact mode records exact deterministic counts of
source gates, dependencies, source layers, Toffolis, direct-CCZ events, CCZ
states consumed, PPMs, conditional-frame updates, cleanup operations, and
per-source-layer injection demand. Storage counts retain distinct kinds:
OOP reports fully resident source values, while IP reports source ancillas.
They are not presented as the same capacity metric. The direct event adapter is executed, so
the result checks the admitted one-Toffoli-to-one-event and six-PPM mapping
rather than merely multiplying a closed-form gate formula.

The reported theoretical pair count is `P(P-1)/2` for `P` PPMs. It describes
the size that an all-pairs artifact would have had; it is not a claim that the
pairs were classified.

## Causal lower bound

Each source Toffoli maps to an ordered ZZ injection layer followed by a
resource-X layer. Assign weight two to Toffoli nodes and weight zero to source
Cliffords, then compute the longest weighted path in the source dependency
DAG. This is a `PROVED` lower bound on the number of PPM dependency levels
relative to the admitted injection semantics.

The compact record also shows twice the number of non-Clifford source layers
as a source two-phase injection envelope. It is `CHECK`, not a schedule. At a
large width the symbolic Clifford frame may create compatibility constraints
that the structural traversal does not classify. The width-256 candidate
batch count therefore remains `OPEN`, even when the envelope numerically
equals the causal lower bound.

The singleton PPM count is a semantic low-rate order only. Its finite cost is
also `OPEN`.

## Exact anchors and scalability boundary

At widths 5 and 8, the full Boolean-ANF presented observables and all PPM pair
relations are materialized. The optimized construction must meet the exact
causal lower bound, contain no fallback PPM, and retain a negative finite
admission. These anchors test the compact counts and show that the reviewed
small-width batching behavior persists through width 8; they do not prove
that it persists to width 256.

All-pairs storage grows quadratically. At width 256 it would contain
27,184,251 OOP relations and 108,744,378 IP relations. The structural mode is
therefore the canonical large-width representation.

## Finite-resource gate

Finite results require one coherent backend with compatible values for the
consumer operation family and duration, processor capacity and routing,
memory traffic and latency, reaction and decoder service, CCZ factory delivery
and buffering, error accounting, and a concrete native mapper. The selected
capability and backend audit do not close those fields.

Consequently the artifacts keep native schedule, surgery rounds, memory
traffic, routing cost, reaction latency, decoder service, CCZ buffer
trajectory, runtime, physical qubits, and failure probability visibly null.
No structural level count may be substituted for any of them.

## Independent replay

The replay module imports neither the compiler nor a scheduler. It rebuilds
every source trace, independently recomputes gate and cleanup counts,
per-layer demand, the weighted longest path, and theoretical pair count, then
checks the exact-anchor summaries and negative finite gate. Tests mutate the
pair count, exact batch count, and finite runtime field to ensure that each
form of overclaim is detected.

## Reproduction

Run:

```text
uv --native-tls run python scripts/run_direct_ccz_ppm_scaling_cycle.py
```

The manifest is `experiments/manifests/E-20260901-010.yaml`; generated files
are under `experiments/runs/T-20260901-010/`. Generated results must be changed
only through their source, configuration, or generator.
