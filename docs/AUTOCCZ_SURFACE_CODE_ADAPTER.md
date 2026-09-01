# AutoCCZ surface-code factory-to-consumer adapter

- Task: `T-20260901-001`
- Experiment: `E-20260901-001`
- Candidate: `gidney-fowler-autoccz-surface-code-d17-d27-v1`
- Configuration: `configs/architectures/autoccz_surface_code_adapter_v1.yaml`

## Result

- **LITERATURE:** Gidney--Fowler Figures 3--6 define a source-native
  surface-code adapter from one CCZ-factory output, through a three-fixup
  AutoCCZ box and six routing qubits, to one Toffoli consumer block. The local
  adapter is therefore admitted without importing Cain, qLDPC, J300, or
  tricycle values.
- **NUMERICAL:** Treating each of the three delayed-choice cells as the
  source-proved `CZ`/identity carrier, an implementation independent of the
  loader and compiler reconstructs all 64 measurement branches. Every branch
  is nonzero with probability `1/64`; the maximum probability error is
  `2.2551405187698492e-17` and the maximum ideal-CCX operator Frobenius error
  is `0.0`.
- **NUMERICAL under CHECK inputs:** With the paper's example values
  `d1=17`, `d2=27`, six level-1 factories, one-microsecond surface-code cycles,
  and ten-microsecond reaction, the recomputed effective level-1 and level-2
  intervals are `130.33333333333334` and `135` cycles per CCZ. The level-2
  rate is `7407.407407407407 Hz`; meeting a `100000 Hz` average
  reaction-limited demand requires 14 factories.
- **OPEN:** The complete finite service is rejected. Nine required fields are
  absent and one apparently finite output-error value belongs to another
  distance/factory configuration. No width-256 schedule is emitted.

## Primary-source audit

The two PDFs and four official ancillary files are pinned by full SHA-256 in
the configuration. The relevant PDF pages were rendered at 600 DPI and
inspected directly rather than relying only on extracted text.

The AutoCCZ figures show:

1. a delayed-choice cell whose measurement choice activates or skips a CZ;
2. three such cells attached to one CCZ state, using two routing qubits per
   possible fixup;
3. construction of the fixup box while the factory output is routed; and
4. one explicit Toffoli-consumer interface.

The base-factory figures show the source-native lattice-surgery layout,
interleaved level-1/level-2 stages, a routing bottleneck, and qualitative
internal surplus-T storage. They do not specify a finite output-AutoCCZ
buffer, delivery bound, or stored-state error model.

## Factory arithmetic

For the selected AutoCCZ example:

```text
level-1 effective cycles/CCZ = 5.75 * 17 * 8 / 6 = 130.33333333333334
level-2 cycles/CCZ           = 5 * 27 = 135
factory rate                 = 1 / (135 * 1 us) = 7407.407407407407 Hz
reaction demand              = 1 / 10 us = 100000 Hz
factories required           = ceil(100000 / 7407.407407407407) = 14
```

These are deterministic consequences of source-stated example assumptions,
not measured hardware performance or a proof that demand bursts can be served.
The reported approximately 2.6 million physical qubits for fourteen factories
is a factory footprint; it is not processor logical capacity or a total
width-256 machine size.

## Calculator incompatibility

The official `1812.01238v3` workbook was inspected across the used cells. Its
published examples use `d1=15,d2=31` or `d1=19,d2=31`, never the selected
AutoCCZ `d1=17,d2=27`. In particular, the calculator value
`5.33332e-11` is tied to the older `d1=15,d2=31`, `5.5d` factory. The audit
preserves that value as source-qualified but incompatible; it cannot close the
selected model's output-error field.

## Fail-closed service matrix

The schema requires exactly 17 fields. The source-native adapter closes event
semantics, resource type, one consumer port, local routing, factory batch size,
production interval, and the factory-to-consumer adapter. Complete service
remains false because these nine fields have no admitted finite value:

1. `consumer.consumption_interval_cycles`
2. `consumer.logical_error_per_event`
3. `controller.decoder_throughput`
4. `controller.reaction_latency_seconds`
5. `processor.logical_capacity`
6. `factory.delivery_latency_cycles`
7. `factory.buffer_capacity`
8. `factory.storage_error_per_cycle`
9. `compatibility.same_domain_failure_budget`

The tenth blocker is incompatible rather than missing:

- `factory.output_error_probability`: qualified only for
  `gidney-fowler-ccz-factory-d15-d31-v3`, not the selected
  `gidney-fowler-autoccz-surface-code-d17-d27-v1` domain.

The loader recomputes both admission flags and every derived rate. Recorded
claims cannot force admission, omit fields, refer to unknown sources, or move
the calculator error into the selected compatibility domain.

## Reproducibility

The runner verifies the two PDF, two SKP, one ODS, and one additional SKP hash;
loads the strict configuration; reconstructs all branches; and writes:

- `experiments/runs/T-20260901-001/autoccz_service_audit.json`
- `experiments/runs/T-20260901-001/autoccz_channel_verification.json`
- `experiments/runs/T-20260901-001/summary.json`
- `experiments/runs/T-20260901-001/reproducibility.json`

It also fails if the current incomplete candidate is admitted or if a schedule
artifact exists after rejection.

## Scope boundary and next step

This cycle does not claim a width-256 schedule, runtime, algorithm failure
probability, physical-qubit total, finite decoder, or burst-feasible factory
service. The next evidence-producing cycle should close a same-distance
AutoCCZ output/transport/consumer error model and a decoded finite buffer and
reaction contract before coupling the adapter to the QCLA demand trace.
