# Finite direct-CCZ backend audit

- Task: `T-20260831-004`
- Experiment: `E-20260831-004`
- Candidate: `cain-ecc256-p20-time-efficient-direct-ccz-v1`
- Machine-readable record:
  `configs/architectures/direct_ccz_finite_backend_audit_v1.yaml`

## Result

- **OPEN:** No finite high-rate direct-CCZ backend is admitted.
- **NUMERICAL:** The deterministic gate finds 13 required fields without a
  source-qualified finite value and three finite factory fields from an
  incompatible architecture domain.
- **NUMERICAL:** No schedule artifact is emitted after rejection.
- **LITERATURE:** The exact Figure 14(a) single-event contract remains admitted
  as portable semantics under the separately reviewed `T-20260831-003`. This
  does not transfer physical timing, capacity, or error guarantees.

This is a successful negative research result: it identifies exactly why the
next schedule would be scientifically premature and makes accidental
cross-architecture substitution machine-detectable.

## Admission rule

The gate requires one value for each of 17 fields:

1. event semantics, consumer batch size, parallel PPM layers, duration, and
   logical error per batch;
2. decoder throughput and reaction latency;
3. injection-port capacity, processor logical capacity, and routing;
4. factory batch size, production cycles, output error, delivery latency,
   buffer capacity, and storage error; and
5. a factory-to-consumer adapter.

The event semantics may be portable. Every physical value must have
`PROVED`, `NUMERICAL`, or `LITERATURE` evidence and the same compatibility
domain as the selected backend. A value from another domain remains visible
but cannot close the field. The recorded admission Boolean is recomputed and a
forged value is rejected.

## Candidate field matrix

| Layer | Field | Source-reported information | Gate result |
|---|---|---|---|
| Consumer | event semantics | Exact six-measurement Figure 14(a) event and conditional correction map | admitted as portable only |
| Consumer | batch size | `P=20` concurrency target for the ECC-256 estimate | `OPEN`; estimate parameter, not finite construction |
| Consumer | PPM layers | one parallel `ZZ` layer plus two fixup layers | `OPEN`; explicitly approximate |
| Consumer | duration | three surgery cycles with `d=20` | `OPEN`; not a decoded finite duration bound |
| Consumer | logical error | none for the complete batch | `OPEN` |
| Controller | decoder throughput | none for the selected batch | `OPEN` |
| Controller | reaction latency | none for conditional CZ/Pauli fixups | `OPEN` |
| Processor | injection ports | no finite `P=20` direct-CCZ port construction | `OPEN` |
| Processor | logical capacity | `P=20`, but concrete processor code omitted | `OPEN` |
| Processor | routing | no placement/routing path for factory, ancilla, and data supports | `OPEN` |
| Factory | batch size | 10 CCZ states | incompatible `cain-bb18-space-balanced-v1` domain |
| Factory | production | 120 processor-code cycles | incompatible `cain-bb18-space-balanced-v1` domain |
| Factory | output error | approximately `1e-10` per state | incompatible `cain-bb18-space-balanced-v1` domain |
| Factory | delivery | none | `OPEN` |
| Factory | buffer | none | `OPEN` |
| Factory | storage error | none | `OPEN` |
| Compatibility | factory-to-consumer adapter | none | `OPEN` |

## Primary-source compatibility audit

### Cain system estimate

- **LITERATURE:** Appendix C reports the finite `bb18` estimate of ten CCZ
  states in 120 processor-code cycles at approximate per-state error `1e-10`.
- **CHECK:** Those values belong to the space-efficient or balanced `bb18`
  factory regime. They are not a delivery-inclusive service contract for the
  time-efficient ECC-256 `P=20` candidate.
- **LITERATURE:** Appendix F assumes `P` simultaneous CCZ consumptions and
  three surgery cycles, while stating that the estimate does not specify a
  concrete instruction set.

### Magic tricycles

- **LITERATURE:** Finite tricycle blocks implement constant-depth logical CCZ
  action and include circuit-level magic-state generation studies plus a
  neutral-atom syndrome-extraction layout.
- **CHECK:** The headline error values are memory-performance proxies and do
  not include errors from the CCZ circuit in the final magic-state fidelity.
- **OPEN:** Selective logical initialization and concrete gate teleportation
  from the tricycle code to a target computation code remain unresolved in the
  source. Therefore these data do not supply the missing Figure 14 consumer
  adapter, delivery, buffer, or consumer timing fields.

### Batched high-rate qLDPC operations

- **LITERATURE:** The general construction provides batched high-rate qLDPC
  operations and asymptotic global non-Clifford constructions while assuming
  fast classical computation.
- **CHECK:** Its finite self-dual BB path implements global T gates through
  parallel cultivation. It is not a finite Figure 14 direct-CCZ consumer and
  does not close the selected backend's reaction or delivery contract.

### Finite T- and Y-state interfaces

- **LITERATURE:** The mitten J300 and canonical-LP sources provide finite
  parallel T-state interfaces; the in-situ CSS construction simulates multiple
  logical Y-state injections within one block.
- **CHECK:** Resource type is part of the native contract. These interfaces
  cannot be relabeled as direct CCZ injection. The in-situ source also notes a
  generally nonlocal, deep Clifford preparation caveat.

## Reproducible artifacts

- `experiments/runs/T-20260831-004/direct_ccz_backend_audit.json`
- `experiments/runs/T-20260831-004/summary.json`
- `experiments/runs/T-20260831-004/reproducibility.json`

The source hashes, configuration hash, implementation bindings, environment,
task ID, working-tree state, and deterministic no-seed declaration are recorded
in the run directory.

## Next research step

- **OPEN:** Construct or source-qualify one finite factory-to-consumer adapter
  in a single code/architecture domain. It must include decoded batch duration
  and failure, reaction latency, finite ports and routing, delivery, buffering,
  and stored-state error. Only after that gate closes should the width-256
  direct-CCZ event trace be scheduled.
