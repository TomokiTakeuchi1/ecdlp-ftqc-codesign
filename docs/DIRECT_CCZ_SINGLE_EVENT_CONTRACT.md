# Exact single-event direct-CCZ correction contract

- Task: `T-20260831-003`
- Experiment: `E-20260831-003`
- Scope: one source Toffoli represented as `H(target)`, CCZ-state consumption,
  exact measurement-conditioned corrections, and `H(target)`.
- Exclusion: no finite high-rate schedule, QEC duration, physical-qubit total,
  factory delivery, routing, decoder, memory, or failure-budget result.

## Source and convention

Litinski--Nickerson Figure 14(a) is the primary circuit. Cain Appendix E points
to the same detailed construction while specifying the three resource-data
`ZZ` PPMs followed by three resource `X` PPMs.

The machine convention is:

```text
measurement bit 0 = +1 eigenvalue
measurement bit 1 = -1 eigenvalue
```

Let `a,b,c` be the `ZZ` bits for data/resource pairs 0, 1, and 2, and let
`x0,x1,x2` be the subsequent resource-`X` bits. Figure 14(a), interpreted under
that convention, gives:

```text
CZ(data_1,data_2)^a
CZ(data_0,data_2)^b
CZ(data_0,data_1)^c
Z(data_0)^(x0 XOR (b AND c))
Z(data_1)^(x1 XOR (a AND c))
X(data_2)^(x2 XOR (a AND b))
```

The final Pauli expressions are after the target Hadamard; hence the target
correction is `X`, not `Z`.

## Independent channel verification

`src/ecdlp_ftqc/verification/direct_ccz_injection.py` deliberately imports
neither the capability loader nor the event compiler. It constructs the
six-qubit state from:

1. an arbitrary three-qubit data input with a target Hadamard;
2. `CCZ|+++>`;
3. three projectors `(I + (-1)^bit Z_data Z_resource)/2`;
4. the three conditional `CZ` operations;
5. the target Hadamard and three resource-`X` projections; and
6. the displayed Pauli correction formula.

For each of the 64 measurement strings, the resulting 8-by-8 branch operator
is compared directly with ideal CCX up to its scalar branch amplitude. All 64
branches are nonzero, each has probability `1/64`, the maximum probability
error is `2.2551405187698492e-17`, and the maximum Frobenius residual is `0.0`
at floating-point precision. This is a `NUMERICAL` reconstruction, not a formal
proof.

## Capability admission

`configs/architectures/direct_ccz_single_event_capability_v1.yaml` records the
six PPM supports, exact Boolean map, outcome convention, source reference, and
verification artifact. The loader recomputes admission and rejects a record
that changes the canonical Figure-14 map while claiming admission.

The admitted states are intentionally split:

- single-event lowering: `true`;
- finite high-rate schedule: `false`.

High-rate admission still requires batch size, parallel PPM layers, duration,
logical error, decoder throughput, reaction latency, injection ports,
processor capacity, routing, factory delivery, buffer capacity, storage error,
and admissible evidence.

## Width-256 event trace

The reviewed clean OOP-QCLA trace lowers deterministically to:

- 1,229 direct-CCZ injection events;
- 7,374 PPM records and 7,374 named outcome dependencies;
- 3,687 conditional-CZ expressions;
- 3,687 Pauli-correction expressions;
- 2,458 target-Hadamard basis changes; and
- 766 pass-through source CNOTs.

The compiler substitutes both actual data-qubit names and event-specific
measurement tokens into every correction expression. Event-trace schema v2
also preserves every architecture-neutral source dependency between the 1,229
injections and 766 pass-through CNOTs. The trace explicitly sets
`complete_native_schedule=false`.

## Exit and next gate

This cycle closes the single-event semantic gap only. The next scheduler cycle
must not begin until one finite backend supplies every remaining high-rate
field under a compatible code, operation-zone, routing, decoder, and factory
contract. Source layer 1 containing 255 CCZ candidates remains demand, not
admitted simultaneous execution.
