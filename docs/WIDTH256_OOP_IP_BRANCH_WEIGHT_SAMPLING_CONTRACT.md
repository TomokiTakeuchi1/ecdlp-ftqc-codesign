# Width-256 OOP/IP branch-maximum PPM-weight sampling contract

## Scope

Task `T-20260907-002` compares the reviewed compressed width-256 QCLA
workloads in one logical-support coordinate:

- out-of-place (OOP): 1,229 direct-CCZ events in 15 macro layers and 30
  two-phase candidate levels;
- in-place (IP): 2,458 direct-CCZ events in 30 macro layers and 60 two-phase
  candidate levels.

The quantity evaluated for one candidate level and one global branch is the
maximum presented logical PPM support weight among every PPM in that level.
It is not the union of all possible supports, a code contact count, a native
surgery weight, or a physical simultaneous-load result.

## Fixed branch protocol

Both variants use 512 branch indices and the seed
`T-20260903-002-support-witnesses-v1`.  Each support-relevant direct-CCZ
outcome token is assigned a stable SHAKE-256 bit mask.  Branch zero forces all
such bits to zero and branch one forces all such bits to one; the remaining
510 branch assignments are deterministic hash witnesses.  The two forced
branches and 510 hashed branches all participate in the reported order
statistics.

Only the first two Figure-14(a) measurement outcomes change later Z support:
they condition the two target-touching column updates.  The remaining
conditional CZ and Pauli corrections preserve Z support, although they can
change signs or other frame data.  Source CNOTs are applied by the reviewed
binary support-conjugation rule before the next common macro entry.

For every branch and phase-one level, the implementation evaluates each of
the three resource-data Z-type PPMs for every event.  The fresh CCZ resource
contributes one support element.  Phase two consists only of fresh-resource X
readouts, so its maximum weight is exactly one for every branch.

## Statistics and evidence

For each candidate level, preserve the complete 512-entry vector and record:

- minimum;
- nearest-rank p50, p95, and p99;
- sampled maximum;
- the separate all-zero and all-one boundary-branch values and maximum over
  the remaining 510 hashed assignments;
- the reviewed support-weight ceiling and sampled-to-ceiling gap.

Nearest rank selects element `ceil(p N / 100)` of the sorted `N=512` values.
Phase-one statistics and maxima are `NUMERICAL`.  No sampled phase-one maximum
is a true maximum, even when it happens to equal its ceiling.  Phase-two unit
weight is `PROVED` from the fresh-resource singleton construction.

The OOP ceiling remains the reviewed exact possible-support envelope
(`PROVED` as a ceiling).  The IP ceiling remains the reviewed sound
may-support envelope (`CHECK`).  Sampling adds lower witnesses and does not
weaken, replace, or promote either ceiling.

## Width-256 result

The phase-one Z-level headlines are:

| Variant | Z levels | largest p50 | largest p95 | largest p99 | largest hashed-assignment maximum | full sampled maximum | largest reviewed ceiling | largest same-level ceiling gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OOP | 15 | 98 (levels 21/23) | 168 (25) | 198 (25) | 223 (25/27) | 509 (29) | 1,003 (29) | 494 |
| IP | 30 | 122 (59) | 188 (31/43) | 222 (39) | 248 (33/49/51) | 509 (31) | 1,006 (31/59) | 622 |

The full sampled maximum in both variants is controlled by the forced
all-one boundary assignment rather than the 510 hashed assignments.  It must
not be read as an empirical tail estimate.  Within the hashed witnesses, IP's
largest observed branch maximum is 248 versus 223 for OOP.  The IP reverse
half sustains p95 values as high as 188 and p99 values as high as 222, but the
existing may-support ceiling can still reach 1,006.  Thus the reverse network
adds more levels and a moderately higher witnessed typical/tail burden; this
experiment does not establish that the roughly fourfold gap from p99 to the
ceiling is impossible, probable, or natively expensive.

Every X phase has exact unit weight and is omitted from the headline maxima.
Complete per-level values are stored in `level_quantiles.json`; complete
branch vectors are stored in `branch_weight_study.json`.

## Independent replay

The primary implementation packs all 512 assignments into integer bit planes
and counts weights in parallel.  The verifier intentionally imports neither
the primary sampler nor its helpers: it walks one branch at a time with scalar
integer support bitsets, reconstructs every level vector, recomputes all order
statistics and hashes, and verifies both ceilings and exact X phases.

The audit covers 7,374 OOP PPMs and 14,748 IP PPMs in every branch, for
11,326,464 branch--PPM instances.  Mutation tests reject altered sample
vectors, altered quantiles, and any non-null native output.

## Fail-closed native boundary

This task does not provide:

- connected-code support or an addressable surgery construction;
- placement, routing, contacts, ports, storage, or memory transfers;
- H/CNOT materialization time;
- decoder or classical-reaction service;
- CCZ factory delivery, buffering, or stalls;
- native cycles, wall-clock runtime, physical qubits, or failure probability.

All finite native fields therefore remain null.  The results may be input to
a future mapper, but candidate levels must not be relabeled as surgery rounds.

## Reproduction

```text
uv --native-tls run python scripts/run_width256_oop_ip_branch_weight_sampling_cycle.py
```

The generator writes the complete vectors, compact level statistics,
independent replay, summary, and source/output hashes under
`experiments/runs/T-20260907-002/`.
