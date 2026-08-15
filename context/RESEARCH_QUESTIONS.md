# Research questions

## Algorithm

- Where is the exploitable parallelism inside point addition, modular arithmetic, lookup, and inversion?
- How do ripple-carry, carry-lookahead, and other adders change workspace, critical path, and resource-state burst demand?
- Which coordinate system minimizes architecture-aware runtime rather than only gate count or width?

## Logical operations

- Which sets of Pauli-product measurements can execute concurrently under each code and surgery construction?
- When is a complex logical instruction better than decomposing into generic PPMs and teleportation?
- What are the support, ancilla, routing, and failure costs of each logical operation?

## Processor and memory

- How large should the processor be to retain useful subcircuits and avoid load/store traffic?
- How many memory ports and operation zones are needed before another resource becomes the bottleneck?
- How should long-lived data and short-lived workspace be placed?

## Code

- Which code families are best suited separately for memory, processor, communication, and factories?
- What parallel-operation constraints arise from the logical basis and surgery construction?
- How do decoder throughput and logical-cycle time change the preferred code?

## Factory

- Can factories meet the time-dependent CCZ/T demand rather than only the average demand?
- How much buffering is required, and where should buffers be placed?
- When does factory footprint versus factory throughput dominate the Pareto frontier?

## End-to-end

- Which assumptions explain the gap between multi-day and multi-hundred-day ECDLP-256 estimates?
- For a fixed physical-qubit budget, what architecture minimizes runtime?
- Which new code, gadget, or compiler capability would produce the largest marginal improvement?