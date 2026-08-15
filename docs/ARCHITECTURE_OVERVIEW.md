# Software architecture overview

## Canonical flow

1. Circuit generator or importer.
2. Architecture-independent semantic circuit.
3. Typed dependency and metadata trace.
4. Optional lowering to a logical instruction set.
5. Resource-constrained scheduler.
6. Code, factory, I/O, decoder, and hardware timing models.
7. Reliability and physical-qubit estimator.
8. Experiment manifest and result report.

## Separation rule

Circuit semantics must not embed one architecture's timing assumptions. Backend constraints must remain explicit configuration or model objects.