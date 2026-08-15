# Project charter

## Objective

Develop a reproducible end-to-end estimator and co-design framework for fault-tolerant quantum execution of Shor's algorithm for a 256-bit elliptic-curve discrete logarithm problem.

## Core scientific question

How much of the parallelism present in the arithmetic and elliptic-curve circuit can be converted into wall-clock speedup after accounting for realistic logical-operation support, processor capacity, memory traffic, factory supply, routing, decoding, and classical feed-forward?

## Layers under joint optimization

1. Algorithm and arithmetic decomposition.
2. Circuit dependency structure and metadata.
3. Logical instruction set and fault-tolerant gadgets.
4. Processor, memory, communication, and operation zones.
5. Quantum error-correcting code selection and code parameters.
6. Magic/resource-state production, buffering, and injection.
7. Decoder, controller, and reaction latency.
8. Physical hardware timing and error assumptions.

## Primary metrics

- physical qubit count;
- wall-clock runtime;
- spacetime volume;
- logical failure probability;
- processor occupancy and utilization;
- memory load/store traffic;
- PPM or logical-operation throughput;
- resource-state demand, backlog, and buffer size;
- decoder and controller utilization.

## Required output classes

- analytic lower bounds;
- reproducible baseline estimates;
- realizable or explicitly qualified upper bounds;
- cross-layer Pareto frontiers;
- bottleneck attribution;
- architecture design recommendations.

## Non-goals for the first phase

- designing a new qLDPC code before identifying the dominant bottleneck;
- relying on one scalar gate count as the runtime estimator;
- presenting idealized parallel depth as an implementable schedule;
- mixing literature assumptions from incompatible architectures without an explicit adapter model.