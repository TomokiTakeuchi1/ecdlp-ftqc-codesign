# Bravyi, Smith, and Smolin 2016: Pauli-based computation

- Task: `T-20260815-004`
- Source: <https://arxiv.org/abs/1506.01396v1>
- Version: arXiv:1506.01396v1, submitted 2015-06-03; published in PRX 6, 021043 (2016)
- Reading status: Theorem 2 and Figure 4 audited for the adaptive CQLU lowering

## Source-reported claims

- **LITERATURE:** Theorem 2 converts a Clifford+T circuit with `m` T gates to a Pauli-based computation on `m` qubits for sampling the circuit's final classical output distribution.
- **LITERATURE:** Figure 4 implements a T gate using a `|T>` ancilla, a nondestructive ZZ measurement, and an X measurement of the magic ancilla.
- **LITERATURE:** The four measurement branches produce T or T-dagger with Pauli byproducts; the stated corrections include an outcome-dependent S.

## Derived project relevance

- **CHECK:** Theorem 2's final-output simulation is not automatically a quantum-output-preserving CQLU subroutine. A live arithmetic output requires an explicit remaining Clifford frame or a physical correction gadget.
- **NUMERICAL:** `T-20260815-004` composes Figure 4 with adaptive one-bit Clifford teleportation, eliminating the S/S-dagger frame before returning the logical value. All nonzero branches are checked numerically.
- **CHECK:** The identity does not specify Mitten state-preparation, PPM, decoder, or classical-reaction durations.

## Open interpretation questions

- **OPEN:** Can a source-pinned auto-corrected T gadget reduce the additional stabilizer preparation and reaction path while preserving a live quantum output?
- **OPEN:** Can groups of the generated XX measurements be scheduled by Mitten high-rate surgery without increasing simultaneous scratch occupancy beyond the processor limit?
