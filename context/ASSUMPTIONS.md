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

Every experiment manifest must reference the assumption IDs it uses.
