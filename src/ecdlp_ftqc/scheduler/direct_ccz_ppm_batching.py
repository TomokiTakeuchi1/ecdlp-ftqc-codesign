"""High-rate candidate classification for symbolic direct-CCZ PPM traces.

This module schedules *candidate batch levels*, not surgery rounds.  Exact
Boolean-ANF symplectic relations are separated from finite-backend admission,
and the low-rate fallback is only a semantic singleton order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations, product
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from ecdlp_ftqc.architectures import DirectCczBackendAudit, DirectCczCapability
from ecdlp_ftqc.compiler.direct_ccz_ppm import (
    BooleanPolynomial,
    SymbolicDirectCczPpmTrace,
    SymbolicPauliWord,
    SymbolicPpmMeasurement,
)
from ecdlp_ftqc.metadata import EvidenceStatus

DIRECT_CCZ_PPM_BATCH_SCHEMA_VERSION = 1
GENERAL_CANDIDATE_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-general-candidate-batches"
FINITE_ADMISSION_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-finite-instance-admission"
LOW_RATE_FALLBACK_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-low-rate-fallback"
STRATEGY_FRONTIER_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-strategy-frontier"

GENERAL_OBLIGATIONS = (
    "bounded_degree_measurement_construction",
    "distance_preservation_under_batch_measurement",
    "ldpc_check_weight_and_decoder_service",
)
FINITE_NATIVE_MAPPER_OBLIGATIONS = (
    "consumer.native_operation_family",
    "consumer.logical_basis_mapping",
    "consumer.physical_support_overlap_rule",
    "consumer.ancilla_and_check_construction",
)


class DirectCczPpmBatchingError(ValueError):
    """Raised when a candidate analysis would be incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class PpmObservableProfile:
    """Exact branch profile of one presented symbolic PPM observable."""

    operation_id: str
    source_gate_id: str
    source_algorithmic_layer: int
    injection_layer: int
    outcome_token: str
    variables: tuple[str, ...]
    possible_logical_support: tuple[str, ...]
    axis_options: tuple[tuple[str, tuple[str, ...]], ...]
    y_content: tuple[tuple[str, BooleanPolynomial], ...]
    minimum_weight: int
    maximum_weight: int
    distinct_branch_observables: int

    @property
    def has_possible_y(self) -> bool:
        return bool(self.y_content)


@dataclass(frozen=True, slots=True)
class PpmPairRelation:
    """Exact causal and algebraic relation for one canonically ordered pair."""

    left_operation_id: str
    right_operation_id: str
    causal_order: str
    reaction_dependent: bool
    shared_logical_values: tuple[str, ...]
    shared_resource_values: tuple[str, ...]
    symplectic_commutator: BooleanPolynomial
    axis_conflicts: tuple[tuple[str, BooleanPolynomial], ...]
    left_has_possible_y: bool
    right_has_possible_y: bool

    @property
    def universally_commuting(self) -> bool:
        return self.symplectic_commutator.is_zero

    @property
    def universally_axis_consistent(self) -> bool:
        return not self.axis_conflicts

    @property
    def resource_reuse_conflict(self) -> bool:
        return bool(self.shared_resource_values)

    @property
    def general_high_rate_compatible(self) -> bool:
        return (
            self.causal_order == "none"
            and self.universally_commuting
            and self.universally_axis_consistent
            and not self.left_has_possible_y
            and not self.right_has_possible_y
            and not self.resource_reuse_conflict
        )


@dataclass(frozen=True, slots=True)
class CandidateBatch:
    """One unitless candidate level under the logical sufficient-condition screen."""

    batch_level: int
    operation_ids: tuple[str, ...]
    outcome_tokens: tuple[str, ...]
    source_algorithmic_layers: tuple[int, ...]
    injection_layers: tuple[int, ...]
    execution_class: str
    possible_logical_support: tuple[str, ...]
    live_source_logicals: tuple[str, ...]
    live_resource_logicals: tuple[str, ...]
    total_live_logical_requirement: int
    resource_state_count: int
    maximum_ppm_weight: int
    support_multiplicity: int
    same_axis_overlap_pair_count: int
    causal_predecessor_batch_levels: tuple[int, ...]
    reaction_predecessor_batch_levels: tuple[int, ...]
    unresolved_general_obligations: tuple[str, ...] = GENERAL_OBLIGATIONS


@dataclass(frozen=True, slots=True)
class CandidateSchedule:
    """A constructive architecture-independent candidate batching."""

    schedule_id: str
    trace_id: str
    strategy_id: str
    selection_policy: str
    batches: tuple[CandidateBatch, ...]
    causal_critical_path_lower_bound: int
    conflict_clique_lower_bound: int
    combined_batch_level_lower_bound: int
    fallback_operation_count: int
    optimality_evidence_status: EvidenceStatus
    complete_native_schedule: bool = False

    @property
    def candidate_batch_level_count(self) -> int:
        return len(self.batches)

    @property
    def peak_live_logical_requirement(self) -> int:
        return max(
            (batch.total_live_logical_requirement for batch in self.batches),
            default=0,
        )

    @property
    def peak_resource_state_count(self) -> int:
        return max((batch.resource_state_count for batch in self.batches), default=0)

    @property
    def maximum_ppm_weight(self) -> int:
        return max((batch.maximum_ppm_weight for batch in self.batches), default=0)


@dataclass(frozen=True, slots=True)
class GeneralHighRateCandidateAnalysis:
    """Complete general-candidate relation table and constructive schedules."""

    trace_id: str
    observable_profiles: tuple[PpmObservableProfile, ...]
    pair_relations: tuple[PpmPairRelation, ...]
    optimized_schedule: CandidateSchedule
    source_layer_aligned_schedule: CandidateSchedule


@dataclass(frozen=True, slots=True)
class FiniteInstanceAdmission:
    """Fail-closed verdict for one coherent finite-backend candidate."""

    trace_id: str
    capability_id: str
    backend_audit_id: str
    backend_candidate_id: str
    event_lowering_admitted: bool
    high_rate_capability_admitted: bool
    finite_backend_admitted: bool
    capability_missing_fields: tuple[str, ...]
    backend_missing_fields: tuple[str, ...]
    backend_incompatible_fields: tuple[str, ...]
    native_mapper_missing_fields: tuple[str, ...]
    verdict: str
    evidence_status: EvidenceStatus
    native_schedule_emitted: bool = False


@dataclass(frozen=True, slots=True)
class LowRateFallbackOrder:
    """A semantic singleton PPM order with every finite cost left open."""

    trace_id: str
    operation_ids: tuple[str, ...]
    reaction_boundaries: tuple[tuple[str, tuple[str, ...]], ...]
    semantic_evidence_status: EvidenceStatus
    finite_cost_status: EvidenceStatus = EvidenceStatus.OPEN
    complete_native_schedule: bool = False


@dataclass(frozen=True, slots=True)
class StrategyAssessment:
    """One strategy row in the checked candidate frontier."""

    strategy_id: str
    disposition: str
    evidence_status: EvidenceStatus
    candidate_batch_levels: int | None
    peak_live_logical_requirement: int | None
    added_materialization_ancillas: int | None
    low_rate_fallback_calls: int | None
    maximum_ppm_weight: int | None
    admitted_transform_count: int
    screened_candidate_count: int
    pareto_nondominated: bool | None
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyFrontier:
    """Deterministic strategy comparison without native timing."""

    trace_id: str
    objective_order: tuple[str, ...]
    strategies: tuple[StrategyAssessment, ...]


@dataclass(frozen=True, slots=True)
class DirectCczPpmBatchAnalysis:
    """All three separated Phase-B outputs plus the strategy frontier."""

    general: GeneralHighRateCandidateAnalysis
    finite: FiniteInstanceAdmission
    fallback: LowRateFallbackOrder
    frontier: StrategyFrontier


@dataclass(frozen=True, slots=True)
class _DependencyModel:
    predecessors: dict[str, frozenset[str]]
    ppm_ancestors: dict[str, frozenset[str]]
    reaction_ppm_ancestors: dict[str, frozenset[str]]
    topological_ppm_order: tuple[str, ...]
    node_order: dict[str, int]


def _component_map(
    components: tuple[tuple[str, BooleanPolynomial], ...],
) -> dict[str, BooleanPolynomial]:
    return dict(components)


def _component(
    components: dict[str, BooleanPolynomial],
    logical: str,
) -> BooleanPolynomial:
    return components.get(logical, BooleanPolynomial.zero())


def symbolic_symplectic_polynomial(
    left: SymbolicPauliWord,
    right: SymbolicPauliWord,
) -> BooleanPolynomial:
    """Return the exact ANF commutation parity of two symbolic Pauli words."""

    left_x = _component_map(left.x_components)
    left_z = _component_map(left.z_components)
    right_x = _component_map(right.x_components)
    right_z = _component_map(right.z_components)
    result = BooleanPolynomial.zero()
    for logical in sorted(set(left_x) | set(left_z) | set(right_x) | set(right_z)):
        local = _component(left_x, logical).multiply(
            _component(right_z, logical)
        ).xor(
            _component(left_z, logical).multiply(_component(right_x, logical))
        )
        result = result.xor(local)
    return result


def symbolic_axis_conflicts(
    left: SymbolicPauliWord,
    right: SymbolicPauliWord,
) -> tuple[tuple[str, BooleanPolynomial], ...]:
    """Return every logical index with a branch-possible X/Y/Z axis mismatch."""

    left_x = _component_map(left.x_components)
    left_z = _component_map(left.z_components)
    right_x = _component_map(right.x_components)
    right_z = _component_map(right.z_components)
    conflicts = []
    for logical in sorted(set(left_x) | set(left_z) | set(right_x) | set(right_z)):
        conflict = _component(left_x, logical).multiply(
            _component(right_z, logical)
        ).xor(
            _component(left_z, logical).multiply(_component(right_x, logical))
        )
        if not conflict.is_zero:
            conflicts.append((logical, conflict))
    return tuple(conflicts)


def symbolic_y_content(
    word: SymbolicPauliWord,
) -> tuple[tuple[str, BooleanPolynomial], ...]:
    """Return exact ANFs for branch-possible Y content at each logical index."""

    x = _component_map(word.x_components)
    z = _component_map(word.z_components)
    result = []
    for logical in sorted(set(x) | set(z)):
        y = _component(x, logical).multiply(_component(z, logical))
        if not y.is_zero:
            result.append((logical, y))
    return tuple(result)


def _observable_profile(ppm: SymbolicPpmMeasurement) -> PpmObservableProfile:
    word = ppm.presented_observable
    variables = tuple(
        sorted(
            {
                variable
                for _, polynomial in (*word.x_components, *word.z_components)
                for variable in polynomial.variables
            }
            | set(word.sign.variables)
        )
    )
    if len(variables) > 16:
        raise DirectCczPpmBatchingError(
            f"{ppm.operation_id} has {len(variables)} axis variables; exact branch "
            "profiling is limited to 16 variables in this bounded optimizer"
        )
    assignments = (
        ({name: bit for name, bit in zip(variables, bits, strict=True)} for bits in product((0, 1), repeat=len(variables)))
        if variables
        else iter(({},))
    )
    axis_options: dict[str, set[str]] = {}
    weights: list[int] = []
    distinct: set[tuple[int, tuple[tuple[str, str], ...]]] = set()
    for assignment in assignments:
        sign, support = word.evaluate(assignment)
        weights.append(len(support))
        distinct.add((sign, support))
        for logical, axis in support:
            axis_options.setdefault(logical, set()).add(axis)
    return PpmObservableProfile(
        operation_id=ppm.operation_id,
        source_gate_id=ppm.source_gate_id,
        source_algorithmic_layer=ppm.source_algorithmic_layer,
        injection_layer=ppm.injection_layer,
        outcome_token=ppm.outcome_token,
        variables=variables,
        possible_logical_support=tuple(sorted(axis_options)),
        axis_options=tuple(
            (logical, tuple(sorted(axes)))
            for logical, axes in sorted(axis_options.items())
        ),
        y_content=symbolic_y_content(word),
        minimum_weight=min(weights),
        maximum_weight=max(weights),
        distinct_branch_observables=len(distinct),
    )


def _dependency_model(trace: SymbolicDirectCczPpmTrace) -> _DependencyModel:
    emitted = tuple(
        operation_id
        for source in trace.source_operations
        for operation_id in source.emitted_operation_ids
    )
    if len(emitted) != len(set(emitted)):
        raise DirectCczPpmBatchingError("semantic operation IDs must be unique")
    node_order = {operation_id: index for index, operation_id in enumerate(emitted)}
    predecessors: dict[str, set[str]] = {operation_id: set() for operation_id in emitted}

    for instruction in trace.clifford_instructions:
        predecessors[instruction.operation_id].update(
            instruction.predecessor_operation_ids
        )
    for ppm in trace.ppms:
        predecessors[ppm.operation_id].update(ppm.predecessor_operation_ids)
    outcome_producer = {ppm.outcome_token: ppm.operation_id for ppm in trace.ppms}
    update_ids = {update.update_id for update in trace.correction_updates}
    for update in trace.correction_updates:
        predecessors[update.update_id].update(
            outcome_producer[token] for token in update.outcome_dependencies
        )
    completion_ids = {injection.completion_id for injection in trace.injections}
    for injection in trace.injections:
        predecessors[injection.completion_id].update(
            injection.completion_predecessor_ids
        )

    represented = {
        *(item.operation_id for item in trace.clifford_instructions),
        *(item.operation_id for item in trace.ppms),
        *update_ids,
        *completion_ids,
    }
    if represented != set(emitted):
        raise DirectCczPpmBatchingError("source emissions do not match semantic nodes")
    unknown = {
        predecessor
        for values in predecessors.values()
        for predecessor in values
        if predecessor not in predecessors
    }
    if unknown:
        raise DirectCczPpmBatchingError(
            "semantic dependencies reference unknown nodes: " + ", ".join(sorted(unknown))
        )

    successors: dict[str, set[str]] = {operation_id: set() for operation_id in emitted}
    indegree = {operation_id: len(values) for operation_id, values in predecessors.items()}
    for successor, values in predecessors.items():
        for predecessor in values:
            successors[predecessor].add(successor)
    ready = sorted(
        (operation_id for operation_id, count in indegree.items() if count == 0),
        key=node_order.__getitem__,
    )
    topological: list[str] = []
    while ready:
        node = ready.pop(0)
        topological.append(node)
        for successor in sorted(successors[node], key=node_order.__getitem__):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort(key=node_order.__getitem__)
    if len(topological) != len(emitted):
        raise DirectCczPpmBatchingError("semantic operation graph contains a cycle")

    ppm_ids = {ppm.operation_id for ppm in trace.ppms}
    ppm_ancestors: dict[str, frozenset[str]] = {}
    reaction_ancestors: dict[str, frozenset[str]] = {}
    for node in topological:
        ordinary: set[str] = set()
        reaction: set[str] = set()
        for predecessor in predecessors[node]:
            ordinary.update(ppm_ancestors[predecessor])
            reaction.update(reaction_ancestors[predecessor])
            if predecessor in ppm_ids:
                ordinary.add(predecessor)
            if node in update_ids:
                reaction.update(ppm_ancestors[predecessor])
                if predecessor in ppm_ids:
                    reaction.add(predecessor)
        ppm_ancestors[node] = frozenset(ordinary)
        reaction_ancestors[node] = frozenset(reaction)
    return _DependencyModel(
        predecessors={key: frozenset(value) for key, value in predecessors.items()},
        ppm_ancestors=ppm_ancestors,
        reaction_ppm_ancestors=reaction_ancestors,
        topological_ppm_order=tuple(node for node in topological if node in ppm_ids),
        node_order=node_order,
    )


def _resource_values(trace: SymbolicDirectCczPpmTrace) -> frozenset[str]:
    return frozenset(
        value for lifetime in trace.resource_lifetimes for value in lifetime.resource_values
    )


def _pair_relation(
    left: SymbolicPpmMeasurement,
    right: SymbolicPpmMeasurement,
    left_profile: PpmObservableProfile,
    right_profile: PpmObservableProfile,
    dependency: _DependencyModel,
    resource_values: frozenset[str],
) -> PpmPairRelation:
    if left.operation_id in dependency.ppm_ancestors[right.operation_id]:
        causal_order = "left_before_right"
        reaction = left.operation_id in dependency.reaction_ppm_ancestors[
            right.operation_id
        ]
    elif right.operation_id in dependency.ppm_ancestors[left.operation_id]:
        causal_order = "right_before_left"
        reaction = right.operation_id in dependency.reaction_ppm_ancestors[
            left.operation_id
        ]
    else:
        causal_order = "none"
        reaction = False
    left_support = set(left_profile.possible_logical_support)
    right_support = set(right_profile.possible_logical_support)
    shared = tuple(sorted(left_support & right_support))
    return PpmPairRelation(
        left_operation_id=left.operation_id,
        right_operation_id=right.operation_id,
        causal_order=causal_order,
        reaction_dependent=reaction,
        shared_logical_values=shared,
        shared_resource_values=tuple(
            logical for logical in shared if logical in resource_values
        ),
        symplectic_commutator=symbolic_symplectic_polynomial(
            left.presented_observable,
            right.presented_observable,
        ),
        axis_conflicts=symbolic_axis_conflicts(
            left.presented_observable,
            right.presented_observable,
        ),
        left_has_possible_y=left_profile.has_possible_y,
        right_has_possible_y=right_profile.has_possible_y,
    )


def _maximum_clique(
    vertices: tuple[str, ...],
    adjacency: dict[str, frozenset[str]],
    order: dict[str, int],
) -> tuple[str, ...]:
    """Find the lexicographically first maximum clique exactly."""

    graph = nx.Graph()
    ordered = tuple(sorted(vertices, key=order.__getitem__))
    graph.add_nodes_from(ordered)
    graph.add_edges_from(
        (left, right)
        for left, right in combinations(ordered, 2)
        if right in adjacency[left]
    )
    one_maximum, maximum_size = nx.algorithms.clique.max_weight_clique(
        graph,
        weight=None,
    )
    target = int(maximum_size)
    if target == 0:
        return ()

    def first_of_size(
        selected: tuple[str, ...],
        candidates: tuple[str, ...],
    ) -> tuple[str, ...] | None:
        if len(selected) == target:
            return selected
        if len(selected) + len(candidates) < target:
            return None
        for index, vertex in enumerate(candidates):
            tail = tuple(
                other
                for other in candidates[index + 1 :]
                if other in adjacency[vertex]
            )
            found = first_of_size((*selected, vertex), tail)
            if found is not None:
                return found
        return None

    result = first_of_size((), ordered)
    if result is None:
        # The exact NetworkX bound guarantees existence. Keep the witness in
        # the error to make a dependency-version regression diagnosable.
        raise DirectCczPpmBatchingError(
            f"maximum-clique witness search failed for {sorted(one_maximum)}"
        )
    return result


def _longest_ppm_path(
    dependency: _DependencyModel,
    ppm_ids: frozenset[str],
) -> int:
    scores: dict[str, int] = {}
    for node in sorted(dependency.node_order, key=dependency.node_order.__getitem__):
        weight = 1 if node in ppm_ids else 0
        scores[node] = weight + max(
            (scores[predecessor] for predecessor in dependency.predecessors[node]),
            default=0,
        )
    return max(scores.values(), default=0)


def _schedule_groups(
    trace: SymbolicDirectCczPpmTrace,
    profiles: dict[str, PpmObservableProfile],
    relations: dict[frozenset[str], PpmPairRelation],
    dependency: _DependencyModel,
    policy: str,
) -> tuple[tuple[str, ...], ...]:
    ppm_by_id = {ppm.operation_id: ppm for ppm in trace.ppms}
    order = {operation_id: index for index, operation_id in enumerate(dependency.topological_ppm_order)}
    pending = set(ppm_by_id)
    completed: set[str] = set()
    groups: list[tuple[str, ...]] = []

    def pair_compatible(left: str, right: str) -> bool:
        return relations[frozenset((left, right))].general_high_rate_compatible

    while pending:
        ready = tuple(
            sorted(
                (
                    operation_id
                    for operation_id in pending
                    if dependency.ppm_ancestors[operation_id] <= completed
                ),
                key=order.__getitem__,
            )
        )
        if not ready:
            raise DirectCczPpmBatchingError("PPM candidate scheduler reached a deadlock")
        selected: tuple[str, ...]
        if policy == "singleton":
            selected = (ready[0],)
        else:
            eligible = ready
            if policy == "source_layer_aligned":
                earliest_layer = min(
                    ppm_by_id[operation_id].source_algorithmic_layer
                    for operation_id in ready
                )
                eligible = tuple(
                    operation_id
                    for operation_id in ready
                    if ppm_by_id[operation_id].source_algorithmic_layer == earliest_layer
                )
            adjacency = {
                operation_id: frozenset(
                    other
                    for other in eligible
                    if other != operation_id
                    and pair_compatible(operation_id, other)
                )
                for operation_id in eligible
            }
            eligible_non_y = tuple(
                operation_id
                for operation_id in eligible
                if not profiles[operation_id].has_possible_y
            )
            selected = _maximum_clique(eligible_non_y, adjacency, order)
            if not selected:
                selected = (eligible[0],)
        groups.append(selected)
        pending.difference_update(selected)
        completed.update(selected)
    return tuple(groups)


def _candidate_schedule(
    trace: SymbolicDirectCczPpmTrace,
    profiles: dict[str, PpmObservableProfile],
    relations: dict[frozenset[str], PpmPairRelation],
    dependency: _DependencyModel,
    *,
    strategy_id: str,
    policy: str,
) -> CandidateSchedule:
    groups = _schedule_groups(trace, profiles, relations, dependency, policy)
    ppm_by_id = {ppm.operation_id: ppm for ppm in trace.ppms}
    batch_by_operation = {
        operation_id: level
        for level, group in enumerate(groups, start=1)
        for operation_id in group
    }
    resource_intervals: dict[str, tuple[int, int]] = {}
    resource_event: dict[str, str] = {}
    for lifetime in trace.resource_lifetimes:
        first = min(batch_by_operation[item] for item in lifetime.first_ppm_operation_ids)
        last = max(batch_by_operation[item] for item in lifetime.terminal_ppm_operation_ids)
        for value in lifetime.resource_values:
            resource_intervals[value] = (first, last)
            resource_event[value] = lifetime.injection_event_id

    batches = []
    fallback_count = 0
    for level, group in enumerate(groups, start=1):
        group_profiles = tuple(profiles[operation_id] for operation_id in group)
        group_ppms = tuple(ppm_by_id[operation_id] for operation_id in group)
        group_relations = tuple(
            relations[frozenset((left, right))]
            for left, right in combinations(group, 2)
        )
        valid_general = all(not profile.has_possible_y for profile in group_profiles) and all(
            relation.general_high_rate_compatible for relation in group_relations
        )
        execution_class = (
            "general_high_rate_candidate" if valid_general else "low_rate_fallback_required"
        )
        if not valid_general:
            fallback_count += len(group)
        source_layers = tuple(
            sorted({ppm.source_algorithmic_layer for ppm in group_ppms})
        )
        live_source = tuple(
            lifetime.logical_value
            for lifetime in trace.logical_lifetimes
            if any(
                (
                    (1 if lifetime.origin == "source_input" else lifetime.first_source_layer)
                    <= source_layer
                    <= lifetime.last_source_layer
                )
                for source_layer in source_layers
            )
        )
        live_resource = tuple(
            sorted(
                value
                for value, (first, last) in resource_intervals.items()
                if first <= level <= last
            )
        )
        causal_levels = tuple(
            sorted(
                {
                    batch_by_operation[ancestor]
                    for operation_id in group
                    for ancestor in dependency.ppm_ancestors[operation_id]
                }
            )
        )
        reaction_levels = tuple(
            sorted(
                {
                    batch_by_operation[ancestor]
                    for operation_id in group
                    for ancestor in dependency.reaction_ppm_ancestors[operation_id]
                }
            )
        )
        possible_support = tuple(
            sorted(
                {
                    logical
                    for profile in group_profiles
                    for logical in profile.possible_logical_support
                }
            )
        )
        batches.append(
            CandidateBatch(
                batch_level=level,
                operation_ids=group,
                outcome_tokens=tuple(ppm.outcome_token for ppm in group_ppms),
                source_algorithmic_layers=source_layers,
                injection_layers=tuple(
                    sorted({ppm.injection_layer for ppm in group_ppms})
                ),
                execution_class=execution_class,
                possible_logical_support=possible_support,
                live_source_logicals=live_source,
                live_resource_logicals=live_resource,
                total_live_logical_requirement=len(live_source) + len(live_resource),
                resource_state_count=len(
                    {resource_event[value] for value in live_resource}
                ),
                maximum_ppm_weight=max(
                    profile.maximum_weight for profile in group_profiles
                ),
                support_multiplicity=sum(
                    len(profile.possible_logical_support) for profile in group_profiles
                ),
                same_axis_overlap_pair_count=sum(
                    bool(relation.shared_logical_values)
                    and relation.universally_axis_consistent
                    for relation in group_relations
                ),
                causal_predecessor_batch_levels=causal_levels,
                reaction_predecessor_batch_levels=reaction_levels,
            )
        )

    ppm_ids = frozenset(ppm_by_id)
    causal_lower = _longest_ppm_path(dependency, ppm_ids)
    order = {
        operation_id: index
        for index, operation_id in enumerate(dependency.topological_ppm_order)
    }
    conflict_adjacency = {
        operation_id: frozenset(
            other
            for other in ppm_ids
            if other != operation_id
            and not relations[frozenset((operation_id, other))].general_high_rate_compatible
        )
        for operation_id in ppm_ids
    }
    conflict_lower = len(
        _maximum_clique(dependency.topological_ppm_order, conflict_adjacency, order)
    )
    combined_lower = max(causal_lower, conflict_lower)
    upper = len(batches)
    return CandidateSchedule(
        schedule_id=f"{trace.trace_id}:{strategy_id}:candidate-levels-v1",
        trace_id=trace.trace_id,
        strategy_id=strategy_id,
        selection_policy=policy,
        batches=tuple(batches),
        causal_critical_path_lower_bound=causal_lower,
        conflict_clique_lower_bound=conflict_lower,
        combined_batch_level_lower_bound=combined_lower,
        fallback_operation_count=fallback_count,
        optimality_evidence_status=(
            EvidenceStatus.PROVED if upper == combined_lower else EvidenceStatus.INCONCLUSIVE
        ),
    )


def _finite_admission(
    trace: SymbolicDirectCczPpmTrace,
    capability: DirectCczCapability,
    backend_audit: DirectCczBackendAudit,
) -> FiniteInstanceAdmission:
    if capability.capability_id != trace.capability_id:
        raise DirectCczPpmBatchingError("trace and capability identities disagree")
    if not capability.event_lowering_admitted:
        raise DirectCczPpmBatchingError("the input trace lacks admitted event semantics")
    if capability.high_rate_schedule_admitted or backend_audit.candidate.backend_admitted:
        raise DirectCczPpmBatchingError(
            "a finite backend is admitted, but this Phase-B module has no native mapper; "
            "refusing to emit or reject a schedule without that implementation"
        )
    return FiniteInstanceAdmission(
        trace_id=trace.trace_id,
        capability_id=capability.capability_id,
        backend_audit_id=backend_audit.audit_id,
        backend_candidate_id=backend_audit.candidate.candidate_id,
        event_lowering_admitted=True,
        high_rate_capability_admitted=False,
        finite_backend_admitted=False,
        capability_missing_fields=capability.missing_for_high_rate_schedule,
        backend_missing_fields=backend_audit.candidate.missing_fields,
        backend_incompatible_fields=backend_audit.candidate.incompatible_fields,
        native_mapper_missing_fields=FINITE_NATIVE_MAPPER_OBLIGATIONS,
        verdict="REJECTED_MISSING_OR_INCOMPATIBLE_FINITE_BACKEND_EVIDENCE",
        evidence_status=EvidenceStatus.OPEN,
    )


def _low_rate_fallback(
    trace: SymbolicDirectCczPpmTrace,
    dependency: _DependencyModel,
) -> LowRateFallbackOrder:
    reactions = tuple(
        (
            operation_id,
            tuple(
                sorted(
                    dependency.reaction_ppm_ancestors[operation_id],
                    key=dependency.node_order.__getitem__,
                )
            ),
        )
        for operation_id in dependency.topological_ppm_order
        if dependency.reaction_ppm_ancestors[operation_id]
    )
    return LowRateFallbackOrder(
        trace_id=trace.trace_id,
        operation_ids=dependency.topological_ppm_order,
        reaction_boundaries=reactions,
        semantic_evidence_status=EvidenceStatus.NUMERICAL,
    )


def _dominates(left: CandidateSchedule, right: CandidateSchedule) -> bool:
    left_metrics = (
        left.candidate_batch_level_count,
        left.peak_live_logical_requirement,
        left.fallback_operation_count,
        left.maximum_ppm_weight,
    )
    right_metrics = (
        right.candidate_batch_level_count,
        right.peak_live_logical_requirement,
        right.fallback_operation_count,
        right.maximum_ppm_weight,
    )
    return all(a <= b for a, b in zip(left_metrics, right_metrics, strict=True)) and any(
        a < b for a, b in zip(left_metrics, right_metrics, strict=True)
    )


def _strategy_frontier(
    trace: SymbolicDirectCczPpmTrace,
    profiles: tuple[PpmObservableProfile, ...],
    relations: tuple[PpmPairRelation, ...],
    singleton: CandidateSchedule,
    source_aligned: CandidateSchedule,
    optimized: CandidateSchedule,
) -> StrategyFrontier:
    schedules = (singleton, source_aligned, optimized)
    nondominated = {
        schedule.strategy_id: not any(
            other is not schedule and _dominates(other, schedule) for other in schedules
        )
        for schedule in schedules
    }
    causal_commuting_pairs = sum(
        relation.causal_order != "none" and relation.universally_commuting
        for relation in relations
    )
    changed_from_bare = 0
    ppm_by_id = {ppm.operation_id: ppm for ppm in trace.ppms}
    for profile in profiles:
        ppm = ppm_by_id[profile.operation_id]
        bare = SymbolicPauliWord.from_terms(ppm.logical_support, ppm.pauli_terms)
        if ppm.presented_observable != bare:
            changed_from_bare += 1

    def schedule_assessment(
        schedule: CandidateSchedule,
        disposition: str,
    ) -> StrategyAssessment:
        return StrategyAssessment(
            strategy_id=schedule.strategy_id,
            disposition=disposition,
            evidence_status=EvidenceStatus.NUMERICAL,
            candidate_batch_levels=schedule.candidate_batch_level_count,
            peak_live_logical_requirement=schedule.peak_live_logical_requirement,
            added_materialization_ancillas=0,
            low_rate_fallback_calls=schedule.fallback_operation_count,
            maximum_ppm_weight=schedule.maximum_ppm_weight,
            admitted_transform_count=0,
            screened_candidate_count=len(trace.ppms),
            pareto_nondominated=nondominated[schedule.strategy_id],
            limitations=(
                "candidate batch levels are not surgery rounds",
                "bounded-degree, routing, decoder, and finite-capacity obligations remain OPEN",
            ),
        )

    return StrategyFrontier(
        trace_id=trace.trace_id,
        objective_order=(
            "candidate_or_reaction_batch_levels",
            "peak_live_logical_requirement",
            "added_materialization_ancillas",
            "low_rate_fallback_calls",
            "maximum_ppm_weight",
        ),
        strategies=(
            schedule_assessment(singleton, "FULLY_FRAME_FOLDED_SINGLETON_BASELINE"),
            schedule_assessment(source_aligned, "SOURCE_LAYER_ALIGNED_CANDIDATE"),
            StrategyAssessment(
                strategy_id="measured_operator_product_rewrites",
                disposition="SCREENED_NOT_ADMITTED",
                evidence_status=EvidenceStatus.INCONCLUSIVE,
                candidate_batch_levels=None,
                peak_live_logical_requirement=None,
                added_materialization_ancillas=None,
                low_rate_fallback_calls=None,
                maximum_ppm_weight=None,
                admitted_transform_count=0,
                screened_candidate_count=causal_commuting_pairs,
                pareto_nondominated=None,
                limitations=(
                    "no transported-stabilizer certificate is encoded",
                    "resource-lifetime preservation is not established",
                    "no independent full-trace semantic replay exists for a rewrite",
                ),
            ),
            StrategyAssessment(
                strategy_id="selective_clifford_materialization",
                disposition="SCREENED_NOT_ADMITTED",
                evidence_status=EvidenceStatus.OPEN,
                candidate_batch_levels=None,
                peak_live_logical_requirement=None,
                added_materialization_ancillas=None,
                low_rate_fallback_calls=None,
                maximum_ppm_weight=None,
                admitted_transform_count=0,
                screened_candidate_count=changed_from_bare,
                pareto_nondominated=None,
                limitations=(
                    "minimal frame subset and resulting downstream frame are not certified",
                    "finite Clifford operation family, routing, ancillas, and cost are OPEN",
                ),
            ),
            schedule_assessment(optimized, "EXACT_READY_FRONTIER_BATCH_SPLITTING"),
            StrategyAssessment(
                strategy_id="low_rate_singleton_fallback",
                disposition="SEMANTIC_FALLBACK_ONLY",
                evidence_status=EvidenceStatus.NUMERICAL,
                candidate_batch_levels=len(trace.ppms),
                peak_live_logical_requirement=None,
                added_materialization_ancillas=None,
                low_rate_fallback_calls=len(trace.ppms),
                maximum_ppm_weight=max(profile.maximum_weight for profile in profiles),
                admitted_transform_count=0,
                screened_candidate_count=len(trace.ppms),
                pareto_nondominated=None,
                limitations=(
                    "finite low-rate PPM operation family and duration are OPEN",
                    "the order is semantic and has no physical time coordinate",
                ),
            ),
        ),
    )


def analyze_direct_ccz_ppm_batches(
    trace: SymbolicDirectCczPpmTrace,
    capability: DirectCczCapability,
    backend_audit: DirectCczBackendAudit,
) -> DirectCczPpmBatchAnalysis:
    """Classify and batch one symbolic trace without claiming native execution."""

    if trace.complete_native_schedule:
        raise DirectCczPpmBatchingError("input must be an unscheduled symbolic trace")
    dependency = _dependency_model(trace)
    profiles = tuple(_observable_profile(ppm) for ppm in trace.ppms)
    profile_by_id = {profile.operation_id: profile for profile in profiles}
    ppm_by_id = {ppm.operation_id: ppm for ppm in trace.ppms}
    resource_values = _resource_values(trace)
    relations = tuple(
        _pair_relation(
            ppm_by_id[left_id],
            ppm_by_id[right_id],
            profile_by_id[left_id],
            profile_by_id[right_id],
            dependency,
            resource_values,
        )
        for left_id, right_id in combinations(dependency.topological_ppm_order, 2)
    )
    relation_by_pair = {
        frozenset((relation.left_operation_id, relation.right_operation_id)): relation
        for relation in relations
    }
    singleton = _candidate_schedule(
        trace,
        profile_by_id,
        relation_by_pair,
        dependency,
        strategy_id="fully_frame_folded_singleton",
        policy="singleton",
    )
    source_aligned = _candidate_schedule(
        trace,
        profile_by_id,
        relation_by_pair,
        dependency,
        strategy_id="source_layer_aligned",
        policy="source_layer_aligned",
    )
    optimized = _candidate_schedule(
        trace,
        profile_by_id,
        relation_by_pair,
        dependency,
        strategy_id="high_rate_batch_splitting",
        policy="maximum_ready_compatible_subset",
    )
    return DirectCczPpmBatchAnalysis(
        general=GeneralHighRateCandidateAnalysis(
            trace_id=trace.trace_id,
            observable_profiles=profiles,
            pair_relations=relations,
            optimized_schedule=optimized,
            source_layer_aligned_schedule=source_aligned,
        ),
        finite=_finite_admission(trace, capability, backend_audit),
        fallback=_low_rate_fallback(trace, dependency),
        frontier=_strategy_frontier(
            trace,
            profiles,
            relations,
            singleton,
            source_aligned,
            optimized,
        ),
    )


def _polynomial_to_data(polynomial: BooleanPolynomial) -> dict[str, Any]:
    return {
        "anf_monomials": [list(monomial) for monomial in polynomial.monomials],
        "expression": polynomial.to_expression(),
        "variables": list(polynomial.variables),
    }


def _schedule_to_data(schedule: CandidateSchedule) -> dict[str, Any]:
    return {
        "batches": [
            {
                "batch_level": batch.batch_level,
                "causal_predecessor_batch_levels": list(
                    batch.causal_predecessor_batch_levels
                ),
                "execution_class": batch.execution_class,
                "injection_layers": list(batch.injection_layers),
                "live_resource_logicals": list(batch.live_resource_logicals),
                "live_source_logicals": list(batch.live_source_logicals),
                "maximum_ppm_weight": batch.maximum_ppm_weight,
                "operation_ids": list(batch.operation_ids),
                "outcome_tokens": list(batch.outcome_tokens),
                "possible_logical_support": list(batch.possible_logical_support),
                "reaction_predecessor_batch_levels": list(
                    batch.reaction_predecessor_batch_levels
                ),
                "resource_state_count": batch.resource_state_count,
                "same_axis_overlap_pair_count": batch.same_axis_overlap_pair_count,
                "source_algorithmic_layers": list(batch.source_algorithmic_layers),
                "support_multiplicity": batch.support_multiplicity,
                "total_live_logical_requirement": (
                    batch.total_live_logical_requirement
                ),
                "unresolved_general_obligations": list(
                    batch.unresolved_general_obligations
                ),
            }
            for batch in schedule.batches
        ],
        "candidate_batch_level_count": schedule.candidate_batch_level_count,
        "complete_native_schedule": schedule.complete_native_schedule,
        "constructive_upper_bound_evidence_status": EvidenceStatus.NUMERICAL.value,
        "cost_interpretation": (
            "architecture_independent_candidate upper bound; realizable native cost OPEN"
        ),
        "fallback_operation_count": schedule.fallback_operation_count,
        "lower_bounds": {
            "causal_critical_path_batch_levels": (
                schedule.causal_critical_path_lower_bound
            ),
            "combined_batch_levels": schedule.combined_batch_level_lower_bound,
            "conflict_clique_batch_levels": schedule.conflict_clique_lower_bound,
            "evidence_status": EvidenceStatus.PROVED.value,
        },
        "maximum_ppm_weight": schedule.maximum_ppm_weight,
        "optimality_evidence_status": schedule.optimality_evidence_status.value,
        "peak_live_logical_requirement": schedule.peak_live_logical_requirement,
        "peak_resource_state_count": schedule.peak_resource_state_count,
        "schedule_id": schedule.schedule_id,
        "selection_policy": schedule.selection_policy,
        "strategy_id": schedule.strategy_id,
        "trace_id": schedule.trace_id,
        "unit": "candidate_batch_level_not_time",
    }


def general_high_rate_candidate_to_data(
    analysis: GeneralHighRateCandidateAnalysis,
) -> dict[str, Any]:
    """Return deterministic general-candidate data with exact relation certificates."""

    return {
        "evidence_boundary": {
            "algebraic_and_causal_classification": EvidenceStatus.PROVED.value,
            "bounded_width_construction_and_schedule": EvidenceStatus.NUMERICAL.value,
            "finite_backend_realizability": EvidenceStatus.OPEN.value,
        },
        "logical_overlap_policy": (
            "overlap alone is allowed; exact per-index axis conflict, causal order, "
            "Y content, or resource reuse can split a batch"
        ),
        "observable_profiles": [
            {
                "axis_options": [
                    {"axes": list(axes), "logical_value": logical}
                    for logical, axes in profile.axis_options
                ],
                "distinct_branch_observables": profile.distinct_branch_observables,
                "has_possible_y": profile.has_possible_y,
                "injection_layer": profile.injection_layer,
                "maximum_weight": profile.maximum_weight,
                "minimum_weight": profile.minimum_weight,
                "operation_id": profile.operation_id,
                "outcome_token": profile.outcome_token,
                "possible_logical_support": list(profile.possible_logical_support),
                "source_algorithmic_layer": profile.source_algorithmic_layer,
                "source_gate_id": profile.source_gate_id,
                "variables": list(profile.variables),
                "y_content": [
                    {
                        "logical_value": logical,
                        "polynomial": _polynomial_to_data(polynomial),
                    }
                    for logical, polynomial in profile.y_content
                ],
            }
            for profile in analysis.observable_profiles
        ],
        "optimized_schedule": _schedule_to_data(analysis.optimized_schedule),
        "pair_relations": [
            {
                "axis_conflicts": [
                    {
                        "logical_value": logical,
                        "polynomial": _polynomial_to_data(polynomial),
                    }
                    for logical, polynomial in relation.axis_conflicts
                ],
                "causal_order": relation.causal_order,
                "general_high_rate_compatible": (
                    relation.general_high_rate_compatible
                ),
                "left_has_possible_y": relation.left_has_possible_y,
                "left_operation_id": relation.left_operation_id,
                "reaction_dependent": relation.reaction_dependent,
                "resource_reuse_conflict": relation.resource_reuse_conflict,
                "right_has_possible_y": relation.right_has_possible_y,
                "right_operation_id": relation.right_operation_id,
                "shared_logical_values": list(relation.shared_logical_values),
                "shared_resource_values": list(relation.shared_resource_values),
                "symplectic_commutator": _polynomial_to_data(
                    relation.symplectic_commutator
                ),
                "universally_axis_consistent": (
                    relation.universally_axis_consistent
                ),
                "universally_commuting": relation.universally_commuting,
            }
            for relation in analysis.pair_relations
        ],
        "schema": GENERAL_CANDIDATE_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_BATCH_SCHEMA_VERSION,
        "source_layer_aligned_schedule": _schedule_to_data(
            analysis.source_layer_aligned_schedule
        ),
        "trace_id": analysis.trace_id,
    }


def finite_instance_admission_to_data(
    admission: FiniteInstanceAdmission,
) -> dict[str, Any]:
    """Return a finite-instance verdict with an explicitly null schedule."""

    return {
        "backend_audit_id": admission.backend_audit_id,
        "backend_candidate_id": admission.backend_candidate_id,
        "backend_incompatible_fields": list(admission.backend_incompatible_fields),
        "backend_missing_fields": list(admission.backend_missing_fields),
        "capability_id": admission.capability_id,
        "capability_missing_fields": list(admission.capability_missing_fields),
        "event_lowering_admitted": admission.event_lowering_admitted,
        "evidence_status": admission.evidence_status.value,
        "failure_probability": None,
        "finite_backend_admitted": admission.finite_backend_admitted,
        "high_rate_capability_admitted": admission.high_rate_capability_admitted,
        "native_schedule_emitted": admission.native_schedule_emitted,
        "native_mapper_missing_fields": list(admission.native_mapper_missing_fields),
        "physical_qubits": None,
        "runtime_seconds": None,
        "schedule": None,
        "schema": FINITE_ADMISSION_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_BATCH_SCHEMA_VERSION,
        "trace_id": admission.trace_id,
        "verdict": admission.verdict,
    }


def low_rate_fallback_to_data(fallback: LowRateFallbackOrder) -> dict[str, Any]:
    """Return the semantic singleton order without any time coordinate."""

    reaction_by_operation = dict(fallback.reaction_boundaries)
    return {
        "complete_native_schedule": fallback.complete_native_schedule,
        "finite_cost_status": fallback.finite_cost_status.value,
        "operation_count": len(fallback.operation_ids),
        "operations": [
            {
                "operation_id": operation_id,
                "reaction_predecessor_operation_ids": list(
                    reaction_by_operation.get(operation_id, ())
                ),
                "semantic_order": index,
            }
            for index, operation_id in enumerate(fallback.operation_ids, start=1)
        ],
        "schema": LOW_RATE_FALLBACK_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_BATCH_SCHEMA_VERSION,
        "semantic_evidence_status": fallback.semantic_evidence_status.value,
        "trace_id": fallback.trace_id,
        "unit": "semantic_singleton_order_not_time",
    }


def strategy_frontier_to_data(frontier: StrategyFrontier) -> dict[str, Any]:
    """Return the strategy frontier with unavailable quantities left null."""

    return {
        "objective_order": list(frontier.objective_order),
        "ppm_count_is_objective": False,
        "schema": STRATEGY_FRONTIER_SCHEMA,
        "schema_version": DIRECT_CCZ_PPM_BATCH_SCHEMA_VERSION,
        "strategies": [
            {
                "added_materialization_ancillas": item.added_materialization_ancillas,
                "admitted_transform_count": item.admitted_transform_count,
                "candidate_batch_levels": item.candidate_batch_levels,
                "disposition": item.disposition,
                "evidence_status": item.evidence_status.value,
                "limitations": list(item.limitations),
                "low_rate_fallback_calls": item.low_rate_fallback_calls,
                "maximum_ppm_weight": item.maximum_ppm_weight,
                "pareto_nondominated": item.pareto_nondominated,
                "peak_live_logical_requirement": (
                    item.peak_live_logical_requirement
                ),
                "screened_candidate_count": item.screened_candidate_count,
                "strategy_id": item.strategy_id,
            }
            for item in frontier.strategies
        ],
        "trace_id": frontier.trace_id,
    }


def dumps_phase_b_artifact(value: dict[str, Any]) -> str:
    """Serialize one Phase-B artifact deterministically."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
