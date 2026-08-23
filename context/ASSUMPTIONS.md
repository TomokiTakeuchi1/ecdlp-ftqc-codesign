# Assumption ledger

| ID | Status | Layer | Assumption | Evidence/source | Used by | Sensitivity tested? |
|---|---|---|---|---|---|---|
| A-0001 | OPEN | hardware | Physical gate, measurement, movement, and reset times | TBD | 窶・| No |
| A-0002 | OPEN | code | Logical-cycle definition and logical error model | TBD | 窶・| No |
| A-0003 | OPEN | logical operations | Supported parallel PPM family | TBD | 窶・| No |
| A-0004 | OPEN | factory | Resource-state output process and retry model | TBD | 窶・| No |
| A-0005 | OPEN | controller | Decoder and classical reaction latency | TBD | 窶・| No |
| A-0006 | CHECK | architecture | Backend v1 has one exclusive processor operation-zone slot; parallelism occurs only inside a selected high-rate gadget | `configs/codes/mitten_j300_k60_d14_v1.yaml` | T-20260815-002 | Synthetic 10-versus-9 XX regression |
| A-0007 | CHECK | logical operations | Unresolved intra-block CNOT/H/S/T and T-preparation costs are provisionally 14 syndrome rounds with unknown physical ancilla overhead | Backend v1 sensitivity parameters; not a literature gadget | E-20260815-001 | No |
| A-0008 | LITERATURE | logical operations | Backend v1 selects high-rate surgery only for an exact batch of ten disjoint XX products | Bhardwaj et al. 2026 Figure 2 and Table III | T-20260815-002 | Yes, 10 and 9 products |
| A-0009 | LITERATURE | logical operations | J300 single-X uses 11 merged-code rounds; XX seed and ten-product high-rate XX use 13 | Bhardwaj et al. 2026 Figure 2 | T-20260815-002 | No |
| A-0010 | CHECK | controller | Conditional CZ frame reaction is one round and measured-temporary release is zero rounds in the provisional profile | Backend v1 sensitivity parameters | E-20260815-001 | No |
| A-0011 | LITERATURE | compiler | CNOT uses Xu et al. Figure 11(c); T/T-dagger use Bravyi--Smith--Smolin Figure 4 plus one-bit Clifford teleportation so a live quantum output is retained with explicit Pauli corrections | arXiv:2407.18490v1; arXiv:1506.01396v1; `docs/PBC_CQLU_LOWERING_CONTRACT.md` | T-20260815-004, E-20260815-002 | Branchwise small-system channel tests |
| A-0012 | CHECK | architecture | A single serialized operation zone reuses one compiler scratch carrier; parallel execution may require additional simultaneous scratch slots | `src/ecdlp_ftqc/compiler/pbc_lowering.py`; J300 one-operation-zone configuration | E-20260815-002 | Width 58/59 slot-count boundary |
| A-0013 | CHECK | logical operations | Unreported J300 stabilizer/T preparation, Z/Y/ZZ/full-extractor, and conditional-CZ durations use 14-round sensitivity values; unknown added space is not silently filled in | `configs/codes/mitten_j300_pbc_v2.yaml`; Bhardwaj et al. 2026 source audit | E-20260815-003 | Strict mode rejects every used `CHECK` time or space |
| A-0014 | CHECK | controller | Each classical feed-forward edge adds one syndrome round in the sensitivity schedule | `configs/codes/mitten_j300_pbc_v2.yaml`; Table X is average memory decoding, not a reaction bound | E-20260815-003 | Explicit two-node reaction regression |
| A-0015 | CHECK | architecture | High-rate ten-XX selection additionally requires ten ready, pairwise-disjoint products on ten distinct live compiler scratch slots | Figure 2/Table III source rule plus `docs/J300_PBC_SCHEDULING_CONTRACT.md` executable-resource contract | E-20260815-003 | One/ten-scratch and synthetic ten-CNOT regressions |
| A-0016 | LITERATURE | memory I/O | A memory--processor transfer is a logical-state teleportation move, so source and destination do not retain free simultaneous usable copies | Cain et al. 2026 Appendix E as recorded and reviewed in `runtime-metadata-benchmark`; `docs/RUNTIME_METADATA_IMPORT_MANIFEST.md` | T-20260823-001, E-20260823-001 | Independent replay rejects duplicate loads and stores of non-resident values |
| A-0017 | CHECK | memory I/O | J300 memory load and store each take one round on one transfer lane | `configs/architectures/j300_memory_io_v1.yaml`; sensitivity placeholder, not a source-derived duration | E-20260823-001 | Zero-duration regression and one-/two-lane tests |
| A-0018 | CHECK | scheduling | The reviewed adaptive-PBC event order is fixed before Belady placement; memory transfers do not prefetch or overlap compute | `docs/MEMORY_IO_EXECUTION_CONTRACT.md`; bounded deterministic upper-bound policy | E-20260823-001 | Zero-latency schedule preservation and finite-latency sensitivity |

Every experiment manifest must reference the assumption IDs it uses.
