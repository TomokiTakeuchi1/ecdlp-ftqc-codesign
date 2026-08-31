# Direct-CCZ capability gate and clean OOP-QCLA trace contract

- Task: `T-20260831-002`
- Experiment: `E-20260831-002`
- Claim boundary: source-trace generation and capability rejection only; no
  executable high-rate schedule, wall-clock runtime, or physical-qubit total.

## Scientific question

Can the pinned literature close enough direct-`|CCZ>` injection and finite
high-rate fields to admit a native event trace for clean out-of-place QCLA?
Independently, does a generated clean modulo-`2^n` OOP-QCLA trace reproduce the
source arithmetic, gate-count, depth, and workspace formulas?

## Source audit

The capability record separates four inputs:

1. Cain et al. Appendix E gives a single-resource-state skeleton: three
   resource-data `ZZ` PPMs, followed by three resource `X` PPMs and conditional
   `CZ` corrections. Appendix C gives a concrete ten-`|CCZ>` factory estimate.
2. Cain Appendix F assumes `P` simultaneous CCZ consumptions and three parallel
   PPM/fixup layers, but explicitly describes the result as an approximate
   estimate rather than a concrete circuit or instruction set.
3. Bhardwaj et al. Appendix E/Figure 6 provides a finite parallel `|T>`-state
   injection construction. It is not direct-`|CCZ>` injection.
4. Zheng et al. Definition V.6/Figure 5 provides column-parallel `|T>`-state
   injection. It is not direct-`|CCZ>` injection.

The architecture record therefore preserves the single-event PPM skeleton as
`LITERATURE`, but records the exact Boolean correction map and the finite
high-rate direct-CCZ backend as `OPEN`.

## Clean OOP-QCLA semantics

The source trace implements

```text
(A, B, Z=0, prefix_scratch=0)
    -> (A, B, Z=A+B mod 2^n, prefix_scratch=0).
```

It follows Draper--Kutin--Rains--Svore Sections 4.1 and 5.1. The modulo
construction runs the reviewed carry network on the low `n-1` bits, writes the
low sum, restores the temporary propagate values in `B`, and folds the two most
significant input bits into the high output bit. `Z` is an output register, not
clean workspace.

The OOP frontend reuses the forward prefix gates emitted by the already-reviewed
in-place frontend. It does not copy or independently reinterpret the
`P/G/C/P^-1` round generator.

For width `n`, let `L=n-1`, `w(L)` be Hamming weight, and
`floorlog(L)=floor(log2(L))`. The admitted formulas are:

- Toffoli count: `5n - 3w(L) - 3floorlog(L) - 6`;
- CNOT count: `3n - 2`;
- clean prefix scratch: `L - w(L) - floorlog(L)`; and
- normal-size source depth:
  `floorlog(L) + floorlog(L/3) + 7`.

Section 3 says its carry-depth expression overcounts carry lengths at most
three. Because the modulo trace uses length `n-1`, the implementation validates
the closed-form source depth from width five onward rather than silently
promoting the printed Section-5.1 `n>=4` boundary over that caveat.

## Direct-CCZ capability schema

`configs/architectures/direct_ccz_high_rate_capability_v1.yaml` records:

- exact source IDs, local PDF hashes, and audited PDF pages;
- the six PPM role supports for one injection;
- correction family and exact-map status;
- finite factory observations separately from delivery/buffering;
- admitted versus merely assumed batch/timing fields;
- decoder, reaction, port, capacity, and routing fields; and
- derived event-lowering and high-rate-schedule admission flags.

The loader recomputes both admission flags. A configuration cannot enable an
admission Boolean while leaving its required fields absent.

## Fail-closed event adapter

A source CCX would be emitted as:

```text
H(target)
CCZ_INJECT(
    data=(control_0, control_1, target),
    resource=(ccz_0, ccz_1, ccz_2),
    ppms=(ZZ_0, ZZ_1, ZZ_2, X_0, X_1, X_2),
    outcomes=(...),
    correction_frame=(exact Boolean map),
    resource_consumed=true,
)
H(target)
```

The current source-qualified configuration cannot emit this event because its
exact outcome-to-CZ/Pauli correction map is not machine encoded with admissible
evidence. Unit tests use an explicitly synthetic complete correction map only
to verify the type and support mapping; that fixture is not a scientific
backend claim.

High-rate scheduling additionally requires admitted batch sizes, finite PPM
duration/error, decoder throughput, classical reaction latency, injection-port
capacity, processor logical capacity, routing, delivery latency, buffer
capacity, and storage error. All are checked independently of single-event
admission.

## Validation contract

- Widths 2--6: exhaustive computational-basis replay over every input pair.
- Widths 5/8/16/17/32/256: formula, source-depth, topology, and all-ones-plus-one
  structural checks.
- Width 256: 1,229 source Toffolis, 766 CNOTs, 20 source layers, 240 prefix
  scratch values, and 1,008 fully resident source values.
- The peak of 255 source Toffolis belongs to layer 1, the OOP initial-generate
  layer. It is not attributed to the isolated carry-status network.
- Widths 16 and 17 expose 56 and 62 fully resident source values. This is a
  source-value capacity diagnostic only; direct-CCZ state, port, routing, and
  operation-zone resources are excluded.

## Evidence labels and exit

- Arithmetic circuit and closed forms: `LITERATURE`.
- Generated counts, dependencies, demand trace, and bounded basis replay:
  `NUMERICAL` after deterministic artifact generation.
- Exact direct-CCZ correction map: `OPEN`.
- Finite high-rate direct-CCZ backend: `OPEN`.
- Cain's `P`-way three-surgery-cycle model: `CHECK` architecture estimate, not
  an admitted duration.

This cycle succeeds when the OOP trace reproduces its bounded validation suite
and the incomplete physical capability is rejected with an explicit gap list.
It does not require the scientific answer to the high-rate admission question
to be positive.
