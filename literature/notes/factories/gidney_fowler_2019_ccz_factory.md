# Gidney and Fowler 2019: efficient CCZ factory

- Task: `T-20260901-001`
- Source: <https://arxiv.org/abs/1812.01238v3>
- Version: arXiv:1812.01238v3; *Quantum* 3, 135 (2019)
- DOI: `10.22331/q-2019-04-30-135`
- Local PDF: `literature/papers/1812.01238v3.pdf`
- Official assets: `1812.01238v3-calculator-CCZ-2T-resources.ods`,
  `1812.01238v3-model-ccz.skp`
- Reading status: factory layouts, routing discussion, and official workbook
  inspected directly for `T-20260901-001`

## Source-reported claims

- **LITERATURE:** The base two-level surface-code factory produces one CCZ
  state every `5.5d` cycles before the AutoCCZ paper's later `5d` improvement.
- **LITERATURE:** The layout exposes finite routing constraints and discusses
  qualitative surplus level-1 T-state storage.
- **NUMERICAL:** The official workbook reports a CCZ output-error estimate
  `5.33332e-11` for its `d1=15,d2=31`, physical-error-`10^-3` example.

## Project interpretation

- **CHECK:** Small hallways for surplus T states and unused target waiting
  space are not a finite output-CCZ buffer service contract.
- **INCONCLUSIVE:** The workbook's `d1=15,d2=31` output-error cell cannot be
  transferred to the AutoCCZ paper's `d1=17,d2=27` example without a new
  same-configuration calculation.
- **OPEN:** Delivery latency, output-buffer capacity, stored-state error, and
  an end-to-end factory-to-consumer failure budget remain absent.

## Model mapping

- `configs/architectures/autoccz_surface_code_adapter_v1.yaml`
- `docs/AUTOCCZ_SURFACE_CODE_ADAPTER.md`
