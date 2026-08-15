# Canonical ECDLP-256 circuit decision support

- Task: `T-20260811-001`
- Prepared by: `codex`
- Evidence cut-off: 2026-08-11
- Working tree: unborn `master`; no repository commit exists
- Decision owner: `human` (`T-BOOT-001`)

## Recommended decision

Use Andre Schrottenloher's space-optimized secp256k1 windowed point-addition circuit as the first canonical source baseline, and retain its gate-optimized configuration as a sibling Pareto point. Pin the paper and artifacts exactly as specified below.

Use Luo et al. arXiv:2607.13816v2 as a second, contrasting baseline after the first trace is working. It is valuable because its low-width construction makes mid-circuit measurement, reset, classical feed-forward, and register recycling unavoidable architecture resources.

This is a qualified recommendation, not the final project decision. The human decision owner must explicitly accept the primary circuit's approximate-arithmetic failure semantics. If exact arithmetic is mandatory for the first baseline, promote Luo et al. instead, subject to resolving its exceptional-point contract and the inconsistent full-algorithm count in v2.

## Why this ordering fits the project milestone

- **LITERATURE:** Schrottenloher publishes the hierarchical construction and an official implementation that can build the circuit and emit decomposed QASM. Its benchmark operation is already a 256-bit windowed affine point addition, the unit requested by the project handoff.
- **LITERATURE:** The implementation exposes space- and gate-optimized variants and both secp256k1-specific and generic-prime arithmetic. This gives controlled algorithmic comparisons without changing the entire workload.
- **CONJECTURE:** Starting from this artifact is the shortest path to a dependency-rich trace that can later separate algorithmic critical path from resource-constrained scheduled depth.
- **LITERATURE:** Luo et al. report neither detailed depth nor aggregate measurement demand. Their circuit is therefore an especially useful second stress test for the project's explicit classical-reaction and memory-lifetime models, but it is a riskier first reproduction target.

## Selection gates

The first canonical source must provide:

1. a precise 256-bit point-addition operation and input promises;
2. a public circuit construction or generator, not only aggregate claims;
3. register roles, arithmetic blocks, and dependencies recoverable at more than one level;
4. an explicit non-Clifford counting convention;
5. a version that can be pinned;
6. enough information to record measurements, resets, classical conditions, and ancilla lifetimes;
7. known differences between a point-addition count and a full Shor estimate.

Published logical width or Toffoli count alone does not satisfy these gates.

## Candidate comparison

| Candidate | Public circuit artifact | Relevant operation | Main strength | Blocking issue for first baseline | Disposition |
|---|---|---|---|---|---|
| Schrottenloher 2026 | Official Qarton implementation and QASM exporter | secp256k1 windowed affine point addition | Modern, explicit, competitive, multiple controlled variants | Approximate arithmetic and empirically characterized failure; no architecture depth | **Recommend first** |
| Luo et al. 2026 v2 | Official Qiskit implementation | Controlled affine point addition with dynamic operations | 835-qubit low-space construction; exact EEA allocation | Exceptional-point circuit contract unclear; unpinned Qiskit; inconsistent full count | **Recommend second** |
| Haner et al. 2020 | Paper describes a Q# implementation | Affine Weierstrass point addition/full ECDLP | Established width/depth/T trade-offs | Older toolchain and no pinned official artifact located in this task | Legacy comparator |
| Roetteler et al. 2017 | Published LIQUi|> implementation methodology | Exact affine point addition/full ECDLP | Foundational exact circuit estimate | Legacy language and much older arithmetic | Legacy comparator |
| Chevignard--Fouque--Schrottenloher 2026 | Detailed construction | Compressed RNS/projective computation of a Legendre-symbol bit | Important low-space Pareto point | Not a representative full affine point-addition workload; 22-run semantics | Later Pareto study |
| Babbush et al. 2026 | Aggregate claim backed by a zero-knowledge proof; logical circuit undisclosed | secp256k1 attack estimate | Competitive external target | Dependency DAG and instruction semantics unavailable | Count-only validation target |

## Primary baseline contract

### Source and artifact pin

- Paper: Andre Schrottenloher, *Optimized Point Addition Circuits for Elliptic Curve Discrete Logarithms*, arXiv:2606.02235v1, 2026-06-01; IACR ePrint 2026/1128.
- Paper URL: <https://arxiv.org/abs/2606.02235>
- IACR URL: <https://eprint.iacr.org/2026/1128>
- Official implementation: <https://gitlab.inria.fr/capsule/qarton-projects/ec-point-addition>
- Implementation commit: `9b23c9170a636a7097a02afb3a3d6cbb6425c9f4` (official `master` observed 2026-08-11).
- Qarton: release/tag `1.0.0`, commit `d55356bab03c5b7454915683e052defd9c0f48f6`; do not silently substitute current Qarton `main`.
- License boundary: paper CC BY 4.0; implementation AGPL-3.0-or-later. Do not vendor implementation code without a separate licensing decision.

### Workload identity

- Curve: secp256k1 over `q = 2^256 - 4294968273`.
- Field width: `n = 256`.
- Point representation: affine coordinates plus the implementation's point-at-infinity convention.
- Window width: `w = 16`.
- Logical map: `|i>|R> -> |i>|R + P_i>`.
- Primary configuration: space-optimized, secp256k1-specific arithmetic (`build_circuit.py` default).
- Sibling comparison: gate-optimized, secp256k1-specific arithmetic (`build_circuit.py --gate_efficient`).
- Do not mix the generic-prime configuration into the primary baseline.

### Scope and published counts

| Scope | Space-optimized | Gate-optimized | Evidence |
|---|---:|---:|---|
| Point-addition arithmetic reported in Table 1 | 1192 qubits; `2^21.19` Toffoli-metric operations | 1446 qubits; `2^20.83` Toffoli-metric operations | **LITERATURE** |
| Window register and three lookups excluded from Table 1 | add 16 qubits and `3 * 2^16` Toffoli-metric operations | same addition | **LITERATURE** |
| Full Shor estimate using 28 windowed additions | 1208 qubits; `2^26.11` Toffoli-metric operations | 1462 qubits; `2^25.78` Toffoli-metric operations | **LITERATURE** |

The canonical trace's first benchmark unit is one complete windowed addition, including the 16-bit index register and all three lookups. Store the Table 1 arithmetic core as a named child region so that its count can be checked independently. A full-Shor multiplication factor must remain metadata outside the single-addition trace until the repeated schedule is explicitly generated.

### Counting and correctness semantics

- **LITERATURE:** The paper's "Toffoli" metric counts each CCX, CCZ, and AND operation as one item. These operations do not have identical FTQC implementations, so the trace must preserve the original opcode instead of replacing all three with one generic gate.
- **LITERATURE:** The construction uses measurement-based uncomputation and other Clifford operations. A Toffoli-only stream is not a sufficient architecture trace.
- **LITERATURE:** The circuit is approximate. The paper reports failure probability at most `2^-13.3` after success on 10,000 random inputs; its fast test replaces exact arithmetic subcircuits with classical functions rather than performing a full gate-level simulation.
- **CHECK:** Record the sampled-input distribution, seed, number of trials, success criterion, and every approximation parameter before treating a rerun as comparable to the paper.
- **LITERATURE:** The affine formula neglects doubling and other cases described as negligible for the intended random-input Shor execution, while `i = 0` is handled as the point at infinity. These promises belong in the semantic contract, not in an informal test note.

## Secondary baseline contract

### Source and artifact pin

- Paper: Han Luo et al., *Quantum Algorithm for Elliptic Curve Discrete Logarithms with Space-Efficient Point Addition*, arXiv:2607.13816v2, 2026-08-09. It supersedes arXiv:2604.02311.
- Paper URL: <https://arxiv.org/abs/2607.13816>
- Official implementation: <https://github.com/ZeroWang030221/Quantum-Algorithm-for-Elliptic-Curve-Discrete-Logarithms-with-Space-Efficient-Point-Addition>
- Implementation commit: `b5e4c664de212bdb0981d93d70964a1dca1a0ec9` (official `main` observed 2026-08-11).
- **CHECK:** No release/tag or dependency lock was found. Pin the exact Python and Qiskit versions when the artifact is admitted.

### Published circuit properties

- **LITERATURE:** Point-addition width is `3n + 6 floor(log2 n) + 19`, hence 835 logical qubits at `n = 256`.
- **LITERATURE:** Table 6 reports 70.10 million Toffoli/CCX and 108.09 million CNOT operations for the 256-bit controlled affine point-addition circuit. The modular-inversion sub-block is reported as 30.59 million Toffoli/CCX and 43.39 million CNOT operations.
- **LITERATURE:** The numerical pipeline transpiles reusable blocks to `{CCX, CX, X}` and assembles the 256-bit point-addition total blockwise with exact multiplicities; the paper says flattening the full circuit is impractical.
- **LITERATURE:** In-place division and multiplication measure an old `n`-qubit value in the Hadamard basis, reset the register, run inverse arithmetic, and apply classically controlled Pauli-Z phase corrections. Gidney-style arithmetic in the artifact introduces additional dynamic events.
- **OPEN:** The paper does not report total measurement/reset/classical-condition counts, classical latency, or detailed depth. Extract these from the pinned artifact; two top-level `n`-qubit measurement rounds are only a lower bound on aggregate measurement demand.
- **CHECK:** The text states that exceptional elliptic-curve cases follow standard group rules, but the displayed in-place division interface assumes a nonzero divisor and the resource schedule does not expose the guard cost. The trace contract must state an input promise or include the missing guards.

### Internal v2 count discrepancy

- **NUMERICAL:** Substituting Table 6's `Q_A = 70.10e6` into Equation (8), `28 * (5 * 2^16 + Q_A)`, gives 1,971,975,040 and `log2 = 30.87699`, consistent with `2^30.88` in the abstract, overview, and Table 2.
- **CHECK:** The sentence immediately after Equation (8) says `2^30.63`. Treat this as an internal stale-value/erratum candidate. Do not use `2^30.63` as the baseline expectation without an author correction.
- **CHECK:** Luo et al. Table 2 also reproduces an older P-224 value for the Chevignard et al. secp256k1 comparison. Do not copy cross-paper comparison rows as canonical metadata.

## Other candidates and exclusions

- **LITERATURE:** Chevignard, Fouque, and Schrottenloher's corrected IACR ePrint abstract gives the P-256 point as 1193 qubits, 22 independent runs, and `2^38.98` Toffolis per run. It computes a compressed one-bit observable using RNS/projective arithmetic, so it should be modeled later as a distinct algorithm, not as a cheaper implementation of the same affine point-addition trace.
- **LITERATURE:** Babbush et al. disclose aggregate resource claims but intentionally do not publish the logical circuit. The work can validate an envelope of counts, not dependency, support, lifetime, or scheduling semantics.
- **LITERATURE:** Haner et al. and Roetteler et al. remain important historical comparators. This task found no reason to prefer their older toolchains over a modern, officially published generator for the first trace.

## Minimum schema implications for `T-BOOT-002`

This memo does not implement the schema. It establishes that the schema must at least preserve:

- exact source/artifact/configuration identity and a hierarchical region path;
- original opcode (`CCX`, `CCZ`, `AND`, Clifford, measurement, reset, lookup, classical correction), controls, targets, and Pauli support;
- quantum and classical dependencies, including measurement-result conditions;
- register role, allocation, release, reset, and reuse events;
- logical time only when stated, never inferred from a flat count;
- exact versus approximate semantics, input promises, failure mechanism, and empirical validation metadata;
- count scope (`arithmetic core`, `one complete windowed addition`, `full Shor repetition`) and units;
- generator-versus-flattened status and block multiplicity when full expansion is unavailable.

## Local verification status

- Environment: Windows, bundled Python 3.12.13, `uv 0.10.8`; temporary clones outside the repository; no random seed and no numerical result artifact produced.
- **CHECK:** Schrottenloher's official test collection initially failed because Qarton 1.0.0 imports `frozendict` but does not declare it in package metadata. Supplying `frozendict` removed that collection blocker.
- **INCONCLUSIVE:** The full Schrottenloher suite then exceeded 300 seconds without a result; a targeted `util_test.py` run exceeded 60 seconds without a result.
- **INCONCLUSIVE:** Luo's reduced strict point-addition test (`--skip-n256 --skip-report`) exceeded 300 seconds without a result.
- No published circuit count is marked reproduced by this task. The numerical values above remain `LITERATURE` unless explicitly labeled `NUMERICAL` for arithmetic performed in this memo.

## Human decision required

To close `T-BOOT-001`, record one of the following in `context/DECISIONS.md`:

1. Accept the recommended Schrottenloher primary contract, including its approximate/random-input semantics, and authorize Luo v2 as the second contrast baseline; or
2. Require exact point-addition semantics for the first baseline and promote Luo v2 after resolving its exception-handling and count-contract checks.

Do not start broad scheduler implementation until this choice and the corresponding trace scope are explicit.
