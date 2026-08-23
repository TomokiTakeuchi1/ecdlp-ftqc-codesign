# Runtime-metadata I/O import manifest

- Task: `T-20260823-001`
- Source repository: `runtime-metadata-benchmark`
- Source commit: `75a6e83d5acde37f0987ab867352ee8b2c6afd10`
- Import mode: source-pinned adaptation; no runtime dependency on the sibling checkout

## Imported scientific contracts

The bounded import retains the following reviewed semantics:

1. A memory load or store is a teleportation move. Memory and processor do
   not retain free simultaneous usable copies of one logical state.
2. Memory support and processor occupancy support are distinct.
3. Unknown value origin or lifetime obligations fail closed.
4. Fixed-order persistent retention uses deterministic farthest-next-use
   eviction with no prefetch or voluntary early return.
5. Maximal-prefix partitions use the union of their strict memory interface
   plus peak live local occupancy.
6. Processor-generated temporaries can be spilled only after creation and
   reloaded only after a recorded spill.
7. Every action stream must reproduce its placements, counts, objective, and
   final locations under independent replay.

These memory--processor moves are not the Bell carry teleportation proposed
for a future teleportation-parallel ripple-carry adder. The schemas and event
types remain separate.

## Source bindings

| Source path | SHA-256 | Local use |
|---|---|---|
| `src/runtime_metadata_benchmark/ir/model.py` | `51347B0DC5AB847993FC34880BD30B1AF99349552A57112077A59A039C9B8E3F` | Value origin, lifetime, memory/occupancy separation |
| `src/runtime_metadata_benchmark/scheduling/common.py` | `02A31F72F2AD28C144F790AD00AB2E8E3821F9404683D283DE5E3B5A47E05A9E` | Transfer actions, placements, validation boundary |
| `src/runtime_metadata_benchmark/scheduling/replay.py` | `60AB66243F83D995FF512E5B3784B64703B5C84685C9857AD9ADD202FCF23F74` | Independent action-stream replay |
| `src/runtime_metadata_benchmark/scheduling/persistent_belady.py` | `D103AB64106525245FE607D0D41D88473810B4E4EE73B36A0C9CBE7996EF9B4B` | Fixed-order retention policy |
| `src/runtime_metadata_benchmark/evaluation/partition_execution.py` | `EB7E7CBAB44C0E012DD8479595202E56BAC57F8B658349FBD86ADE7C933FF2AA` | Maximal-prefix layout and exact small-width origin-aware reference |

The source checkout was clean when the import was generated. Its Gidney
frontend and oracle model have no diff between the previously reviewed commit
`8c1638805e7246c30117a0251526661039df1369` and the import commit above.

## Adaptations in this repository

- Wrapper ID classes were replaced with canonical string IDs already used by
  the QEC-neutral DAG.
- The memory model is an overlay referencing DAG source operations; DAG schema
  v1 is unchanged.
- Expanded erase measurement and conditional-frame nodes are collapsed only
  for source-operation I/O accounting. Their causal DAG and PBC dependencies
  remain intact.
- The exact partition dynamic program remains restricted to widths 2--4.
- The scalable PBC integration uses fixed-order Belady on the already selected
  PBC event order. It is a deterministic heuristic upper bound, not a joint
  circuit-placement optimum.
- Transfer timing is supplied by a separate evidence-qualified configuration.

## Regression authority

`tests/fixtures/memory_io/legacy_partition_reference.json` records the
source-produced width-2--4 partition counts. Tests recompute the circuits,
layouts, transfers, and independent replay rather than inserting the expected
values into the scheduling implementation.
