# Luo et al. 2026: space-efficient point addition

- Task: `T-20260811-001`
- Evidence status: primary paper v2 and official artifact inspected 2026-08-11
- Paper: <https://arxiv.org/abs/2607.13816> (v2, 2026-08-09)
- Artifact: <https://github.com/ZeroWang030221/Quantum-Algorithm-for-Elliptic-Curve-Discrete-Logarithms-with-Space-Efficient-Point-Addition>
- Artifact commit: `b5e4c664de212bdb0981d93d70964a1dca1a0ec9`

The paper supersedes arXiv:2604.02311. No release/tag or Python/Qiskit dependency lock was found at the inspected commit.

## Circuit semantics

- **LITERATURE:** The construction gives an exact shared-register EEA allocation and a controlled affine point-addition schedule using `3n + 6 floor(log2 n) + 19` logical qubits.
- **LITERATURE:** In-place division and multiplication measure the obsolete `n`-qubit `Y` register in the Hadamard basis, reset it, use it as EEA workspace, reconstruct the discarded value, apply measurement-conditioned Pauli-Z corrections, and uncompute.
- **LITERATURE:** The implementation also uses measurement-based Gidney arithmetic, so two top-level `n`-qubit measurement rounds are not the total measurement count.
- **OPEN:** Aggregate measurements, resets, classical conditions, reaction latency, and detailed circuit depth are not reported.
- **CHECK:** The prose says exceptional elliptic-curve cases use standard group rules, whereas the displayed division interface assumes a nonzero divisor and the counted point-addition schedule does not expose guard costs.

## Published 256-bit counts

| Scope | Logical qubits | Toffoli/CCX | CNOT |
|---|---:|---:|---:|
| Modular inversion | `2n + 6 floor(log2 n) + 19` | 30.59 million | 43.39 million |
| Controlled affine point addition | 835 | 70.10 million | 108.09 million |

- **LITERATURE:** Counts are produced by compiling reusable Qiskit blocks into `{CCX, CX, X}` and assembling the point-addition count blockwise with exact multiplicities; full flat expansion is described as impractical.
- **LITERATURE:** Detailed depth analysis is explicitly left open.

## Full-ECDLP arithmetic check

- **NUMERICAL:** Equation (8) with `Q_A = 70.10e6` gives `28 * (5 * 2^16 + Q_A) = 1,971,975,040`, or `2^30.87699`; this matches the abstract, overview, and Table 2 value `2^30.88`.
- **CHECK:** The sentence following Equation (8) instead says `2^30.63`. Treat this as a stale-value/erratum candidate.
- **CHECK:** Table 2 also uses an obsolete P-224 result for its Chevignard et al. secp256k1 row; cross-paper rows are not reliable baseline metadata.

## Reproduction notes

- **INCONCLUSIVE:** A reduced strict point-addition test with the 256-bit case and report generation skipped exceeded 300 seconds on the local Windows/Python environment.
- **OPEN:** Exact Qiskit version, point-addition counts, dynamic-operation totals, and a flattened trace have not been reproduced in this repository.

## Baseline use

Recommend this as the second baseline because it directly exercises measurement, reset, classical reaction, and live-register recycling. Promote it to the first baseline only if exact arithmetic is mandatory and its exceptional-point and count-contract checks are resolved.
