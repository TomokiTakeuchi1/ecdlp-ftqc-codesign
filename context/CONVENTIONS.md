# Conventions

## Scientific status labels

`PROVED`, `NUMERICAL`, `LITERATURE`, `CONJECTURE`, `OPEN`, `CHECK`, `FALSIFIED`, `INCONCLUSIVE`.

## Units

- Physical time: seconds in canonical data; display units may be ns, us, ms, hours, or days.
- Logical cycle: an architecture-defined quantity that must always be accompanied by its physical duration.
- Qubit counts: explicitly distinguish physical, data, ancilla, logical, encoded-block, processor-resident, and memory-resident qubits.
- Operation counts: explicitly name the instruction set, such as Toffoli, CCZ consumption, T state, PPM, syndrome cycle, load, or store.

## Naming

- Python package: `ecdlp_ftqc`.
- Configuration IDs: `<layer>-<family>-<variant>-v<integer>`.
- Experiment IDs: `E-YYYYMMDD-NNN`.
- Task IDs: `T-YYYYMMDD-NNN`; bootstrap tasks may use `T-BOOT-NNN`.
- Result IDs: `R-YYYYMMDD-NNN`.

## Separation of concepts

Keep these quantities distinct:

- circuit depth versus critical-path length versus scheduled runtime;
- algorithmic parallelism versus backend-supported parallelism;
- factory average throughput versus peak/burst service capability;
- processor capacity versus operation throughput versus cycle time;
- lower bound versus heuristic estimate versus realizable upper bound;
- logical operation error versus total algorithm failure probability.

## Numerical precision

- Store full machine-readable precision in result files.
- Round only in reports.
- Record tolerance and solver termination status for optimization results.