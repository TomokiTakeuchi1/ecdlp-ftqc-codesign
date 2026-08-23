# J300 adaptive-PBC scheduling contract

- Task: `T-20260815-005`
- Experiment: `E-20260815-003`
- Backend: `configs/codes/mitten_j300_pbc_v2.yaml`
- Source trace: `ecdlp-ftqc/adaptive-pauli-measurement-trace` version 1
- Primary architecture source: Bhardwaj et al., arXiv:2607.28795v1

## Scope

This cycle maps the reviewed, quantum-output-preserving Gidney PBC trace to
one `[[300,60,14]]` J300 Mitten processor. It enforces causal and classical
dependencies, compiler-scratch occupancy, logical-carrier conflicts, one
processor operation zone, and the directly simulated ten-product high-rate XX
rule.

The Factory is ideal and never stalls the schedule, but resource-state demand
is retained as a time series. Memory I/O, bridge operations, routing,
preparation/readout around merged codes, decoder-tail latency, wall-clock
conversion, and total failure probability are outside this cycle.

## Source-audited native-operation matrix

The time and space columns have independent evidence labels. A table entry for
gadget size is not used as evidence for an unreported duration.

| Adaptive-PBC action | Selected implementation | Rounds | Added physical qubits | Evidence and qualification |
|---|---|---:|---:|---|
| Stabilizer preparation | provisional preparation | 14 | 0 | time `CHECK`; space `CHECK` |
| Logical T-state preparation | provisional injection | 14 | 0 | time `CHECK`; space `CHECK`; Figure 6 injects all 60 ports rather than reporting a single-state cost |
| X | J300 seed surgery | 11 | 87 | time `LITERATURE`, Figure 2; space `LITERATURE`, Table II |
| Y | J300 seed surgery | 14 | 201 | time `CHECK`; space `LITERATURE`, Table II |
| Z | J300 seed surgery | 14 | 87 | time `CHECK`; space `LITERATURE`, Table II; the Figure 2 Z experiment is J500 |
| XX | J300 seed surgery | 13 | 201 | time `LITERATURE`, Figure 2; space `LITERATURE`, Table II |
| ZZ | J300 seed surgery | 14 | 201 | time `CHECK`; space `LITERATURE`, Table II |
| Ten disjoint XX products | J300 high-rate surgery | 13 | 1,212 | time `LITERATURE`, Figure 2; space `LITERATURE`, Table III |
| Mixed/general product such as ZX | J300 full extractor | 14 | 1,534 | time `CHECK`; space `LITERATURE`, Table IV |
| Pauli-frame bookkeeping | controller update | 0 | 0 | `PROVED` as zero quantum rounds; reaction delay is separate |
| Conditional CZ | provisional physical action | 14 | 0 | time `CHECK`; space `CHECK` |
| Release/rebind | compiler bookkeeping | 0 | 0 | `PROVED` within this trace; physical reset/reload is excluded |
| Measurement-to-use reaction | dependency-edge latency | 1 | n/a | `CHECK` sensitivity value; Table X gives an average decoder latency, not a deterministic J300 surgery reaction bound |

The J300 base contains 300 data qubits and 240 check ancillas. Added gadget
space counts both the listed gadget data ancillas and one ancilla for each new
independent check. The resulting physical count is a known-component lower
bound, not a complete processor or machine total.

## Scheduling rules

1. A PBC operation starts only after every quantum predecessor finishes.
2. A classical-feed-forward edge adds the configured reaction latency before
   the consumer can start.
3. The source peak occupancy plus requested live compiler scratch slots must
   not exceed 60 logical qubits.
4. A scratch slot is allocated at the lifetime's preparation node and released
   only at its explicit release or output-rebinding node.
5. Operations sharing a logical carrier or live scratch slot cannot overlap.
6. Quantum gadgets occupy the single processor operation zone. Frame and
   bookkeeping actions use the classical controller.
7. High-rate surgery is selected only for exactly ten ready XX operations with
   pairwise-disjoint logical supports and ten distinct live scratch slots.
8. When fewer than ten XX operations are ready, the deterministic greedy rule
   preferentially advances other ready operations to expose a possible batch.
   The result is a realizable heuristic upper bound, not an optimal schedule.

Strict mode rejects every used operation whose time or space is `CHECK`, and
also rejects a `CHECK` reaction latency. Sensitivity mode emits a schedule but
sets `strict_executable=false` and does not convert syndrome rounds to seconds.

## Numerical results

`NUMERICAL`, using the pinned Gidney source commit
`8c1638805e7246c30117a0251526661039df1369`:

| Width | Dependency-only critical path | Scheduled rounds | One-scratch occupancy | Ten-scratch occupancy | Eligible ten-XX batches |
|---:|---:|---:|---:|---:|---:|
| 2 | 635 | 846 | 4 | 13 | 0 |
| 4 | 2,207 | 2,868 | 6 | 15 | 0 |
| 16 | 11,639 | 15,000 | 18 | 27 | 0 |
| 32 | 24,215 | 31,176 | 34 | 43 | 0 |

Because all nonzero-duration processor gadgets share one operation zone, the
scheduled time equals the serialized operation sum in these sensitivity runs.
Adding ten scratch slots alone does not reduce it. No exact ten-XX batch becomes
eligible in the four Gidney workloads under the combined readiness, support,
and scratch rules.

As a scheduler witness, ten independent CNOT traces do expose ten disjoint XX
measurements. With ten scratch slots, enabling the high-rate rule selects one
batch and changes the provisional schedule from 550 to 433 rounds, a
`NUMERICAL` factor of 1.2702. This verifies the rule implementation but is not
an adder-runtime claim.

Every examined adder uses the full extractor for mixed ZX products, so the
known-component peak is 2,074 physical qubits (`540 + 1,534`). It remains
incomplete because preparation, injection, conditional-CZ, Factory, routing,
bridge, and memory space are not fixed.

## Reproduction

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_adaptive_pbc_schedule_cycle.py
```

Generated records are under `experiments/runs/T-20260815-005/`. Do not edit
those JSON files manually; change the configuration, trace, or generator and
rerun the experiment.
