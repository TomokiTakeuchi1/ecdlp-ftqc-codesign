# Schrottenloher 2026: optimized point-addition circuits

- Task: `T-20260811-001`
- Evidence status: primary paper and official artifact inspected 2026-08-11
- Paper: <https://arxiv.org/abs/2606.02235> (v1, 2026-06-01)
- IACR: <https://eprint.iacr.org/2026/1128>
- Artifact: <https://gitlab.inria.fr/capsule/qarton-projects/ec-point-addition>

## Artifact identity

- Point-addition repository commit: `9b23c9170a636a7097a02afb3a3d6cbb6425c9f4`.
- Required Qarton version: tag `1.0.0`, commit `d55356bab03c5b7454915683e052defd9c0f48f6`.
- Paper license: CC BY 4.0. Code license: AGPL-3.0-or-later.

## Circuit semantics

- **LITERATURE:** The main unit is a windowed affine point addition `|i>|R> -> |i>|R + P_i>` over secp256k1, with `n = 256` and `w = 16`.
- **LITERATURE:** It loads precomputed coordinates three times and uses approximate modular arithmetic around two in-place multiplication/inverse-multiplication calls and a controlled squaring.
- **LITERATURE:** The construction handles `i = 0` as the point at infinity but neglects doubling and other events argued to be negligible on random Shor inputs.
- **LITERATURE:** Measurement-based uncomputation is present. The paper's Toffoli metric aggregates CCX, CCZ, and AND, which must remain distinct trace opcodes.

## Published counts

| Configuration | Table 1 arithmetic core | Complete Shor estimate |
|---|---:|---:|
| Space-optimized secp256k1 | 1192 qubits; `2^21.19` Toffoli metric | 1208 qubits; `2^26.11` |
| Gate-optimized secp256k1 | 1446 qubits; `2^20.83` Toffoli metric | 1462 qubits; `2^25.78` |
| Space-optimized generic prime | 1192 qubits; `2^21.78` Toffoli metric | 1208 qubits; `2^26.66` |
| Gate-optimized generic prime | 1446 qubits; `2^21.42` Toffoli metric | 1462 qubits; `2^26.33` |

- **LITERATURE:** Table 1 excludes the 16-qubit window and three `2^16`-cost lookups. The full estimate uses 28 complete windowed additions.
- **LITERATURE:** The reported failure probability is at most `2^-13.3` after success on 10,000 random inputs.
- **CHECK:** The provided fast correctness test replaces exact arithmetic blocks with classical functions; it is not full gate-level simulation.

## Reproduction notes

- Entry points: `build_circuit.py`, `build_circuit.py --gate_efficient`, generic-prime flags, and `qasm_output.py`.
- **CHECK:** Qarton 1.0.0 imports `frozendict`, but the package metadata does not declare it. The official test collection failed until `frozendict` was supplied explicitly.
- **INCONCLUSIVE:** With the dependency supplied, the full suite exceeded 300 seconds and `util_test.py` exceeded 60 seconds on the local Windows/Python 3.12.13 environment.
- **OPEN:** Counts, a flattened trace, dynamic-operation counts, and depth have not been reproduced in this repository.

## Baseline use

Recommend the space-optimized secp256k1 configuration as the first source baseline, with a trace scope that includes the 16-bit window and all three lookups. Keep the arithmetic core as a named region and retain the gate-optimized configuration as a paired comparison.
