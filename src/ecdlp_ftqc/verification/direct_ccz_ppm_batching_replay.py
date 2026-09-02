"""Independent replay for direct-CCZ symbolic PPM batch artifacts.

The replay consumes serialized dictionaries and intentionally imports neither
the symbolic compiler nor the Phase-B scheduler.  Boolean polynomials,
dependency closure, profiles, pair relations, liveness, lower bounds, and all
three output classes are reconstructed from JSON fields.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import networkx as nx  # type: ignore[import-untyped]

from ecdlp_ftqc.metadata import EvidenceStatus

_GENERAL_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-general-candidate-batches"
_FINITE_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-finite-instance-admission"
_FALLBACK_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-low-rate-fallback"
_FRONTIER_SCHEMA = "ecdlp-ftqc/direct-ccz-ppm-strategy-frontier"
_FORBIDDEN_GENERAL_TIME_KEYS = frozenset(
    {
        "start_round",
        "end_round",
        "duration_rounds",
        "duration_seconds",
        "runtime_seconds",
        "surgery_rounds",
        "physical_qubits",
        "failure_probability",
    }
)
_FINITE_NATIVE_MAPPER_OBLIGATIONS = (
    "consumer.native_operation_family",
    "consumer.logical_basis_mapping",
    "consumer.physical_support_overlap_rule",
    "consumer.ancilla_and_check_construction",
)

_Poly = frozenset[tuple[str, ...]]


class DirectCczPpmBatchingReplayError(ValueError):
    """Raised when a serialized Phase-B artifact fails independent replay."""


@dataclass(frozen=True, slots=True)
class DirectCczPpmBatchingReplaySummary:
    """Independent replay counts and the negative finite-admission result."""

    trace_id: str
    ppm_count: int
    observable_profile_count: int
    pair_relation_count: int
    symbolic_commutation_checks: int
    symbolic_axis_checks: int
    possible_y_ppm_count: int
    axis_conflict_pair_count: int
    anticommuting_pair_count: int
    causal_pair_count: int
    reaction_pair_count: int
    compatible_overlap_pair_count: int
    optimized_candidate_batch_levels: int
    source_layer_candidate_batch_levels: int
    causal_lower_bound: int
    conflict_clique_lower_bound: int
    low_rate_singleton_count: int
    finite_capability_missing_field_count: int
    finite_backend_missing_field_count: int
    finite_backend_incompatible_field_count: int
    finite_schedule_rejected: bool
    all_passed: bool
    evidence_status: EvidenceStatus = EvidenceStatus.NUMERICAL


@dataclass(frozen=True, slots=True)
class _GraphReplay:
    predecessors: dict[str, frozenset[str]]
    ppm_ancestors: dict[str, frozenset[str]]
    reaction_ancestors: dict[str, frozenset[str]]
    topological_ppms: tuple[str, ...]
    node_order: dict[str, int]


@dataclass(frozen=True, slots=True)
class _ProfileReplay:
    variables: tuple[str, ...]
    possible_support: tuple[str, ...]
    axis_options: tuple[tuple[str, tuple[str, ...]], ...]
    y_content: tuple[tuple[str, _Poly], ...]
    minimum_weight: int
    maximum_weight: int
    distinct_observables: int | None
    weight_bounds_exact: bool


@dataclass(frozen=True, slots=True)
class _PairReplay:
    causal_order: str
    reaction_dependent: bool
    shared_logicals: tuple[str, ...]
    shared_resources: tuple[str, ...]
    commutator: _Poly
    axis_conflicts: tuple[tuple[str, _Poly], ...]
    left_y: bool
    right_y: bool

    @property
    def compatible(self) -> bool:
        return (
            self.causal_order == "none"
            and not self.commutator
            and not self.axis_conflicts
            and not self.left_y
            and not self.right_y
            and not self.shared_resources
        )


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise DirectCczPpmBatchingReplayError(f"{path} must be a string-keyed mapping")
    return value


def _sequence(value: object, path: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DirectCczPpmBatchingReplayError(f"{path} must be a sequence")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise DirectCczPpmBatchingReplayError(f"{path} must be a nonempty string")
    return value


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DirectCczPpmBatchingReplayError(f"{path} must be an integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise DirectCczPpmBatchingReplayError(f"{path} must be Boolean")
    return value


def _strings(value: object, path: str) -> tuple[str, ...]:
    return tuple(
        _string(item, f"{path}[{index}]")
        for index, item in enumerate(_sequence(value, path))
    )


def _poly(value: object, path: str) -> _Poly:
    raw = _mapping(value, path)
    monomials = tuple(
        tuple(
            _string(variable, f"{path}.anf_monomials[{index}][{variable_index}]")
            for variable_index, variable in enumerate(
                _sequence(item, f"{path}.anf_monomials[{index}]")
            )
        )
        for index, item in enumerate(
            _sequence(raw.get("anf_monomials"), f"{path}.anf_monomials")
        )
    )
    if len(monomials) != len(set(monomials)):
        raise DirectCczPpmBatchingReplayError(f"{path} has duplicate monomials")
    if any(tuple(sorted(set(monomial))) != monomial for monomial in monomials):
        raise DirectCczPpmBatchingReplayError(f"{path} has a noncanonical monomial")
    variables = tuple(sorted({name for monomial in monomials for name in monomial}))
    if _strings(raw.get("variables"), f"{path}.variables") != variables:
        raise DirectCczPpmBatchingReplayError(f"{path} variable list disagrees with ANF")
    return frozenset(monomials)


def _poly_xor(left: _Poly, right: _Poly) -> _Poly:
    return left.symmetric_difference(right)


def _poly_multiply(left: _Poly, right: _Poly) -> _Poly:
    parity: set[tuple[str, ...]] = set()
    for left_monomial in left:
        for right_monomial in right:
            monomial = tuple(sorted({*left_monomial, *right_monomial}))
            if monomial in parity:
                parity.remove(monomial)
            else:
                parity.add(monomial)
    return frozenset(parity)


def _poly_evaluate(polynomial: _Poly, assignment: dict[str, int]) -> int:
    value = 0
    for monomial in polynomial:
        term = 1
        for variable in monomial:
            term &= assignment[variable]
        value ^= term
    return value


def _word(value: object, path: str) -> tuple[dict[str, _Poly], dict[str, _Poly], _Poly]:
    raw = _mapping(value, path)

    def components(name: str) -> dict[str, _Poly]:
        result: dict[str, _Poly] = {}
        for index, item in enumerate(
            _sequence(raw.get(name), f"{path}.{name}")
        ):
            entry = _mapping(item, f"{path}.{name}[{index}]")
            logical = _string(
                entry.get("logical_value"),
                f"{path}.{name}[{index}].logical_value",
            )
            if logical in result:
                raise DirectCczPpmBatchingReplayError(
                    f"{path}.{name} repeats {logical}"
                )
            result[logical] = _poly(
                entry.get("coefficient"),
                f"{path}.{name}[{index}].coefficient",
            )
        return result

    return components("x_components"), components("z_components"), _poly(
        raw.get("sign"), f"{path}.sign"
    )


def _component(values: dict[str, _Poly], logical: str) -> _Poly:
    return values.get(logical, frozenset())


def _y_content(word: tuple[dict[str, _Poly], dict[str, _Poly], _Poly]) -> tuple[tuple[str, _Poly], ...]:
    x, z, _ = word
    result = []
    for logical in sorted(set(x) | set(z)):
        y = _poly_multiply(_component(x, logical), _component(z, logical))
        if y:
            result.append((logical, y))
    return tuple(result)


def _commutator(
    left: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
    right: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
) -> _Poly:
    left_x, left_z, _ = left
    right_x, right_z, _ = right
    result: _Poly = frozenset()
    logicals = sorted(set(left_x) | set(left_z) | set(right_x) | set(right_z))
    for logical in logicals:
        local = _poly_xor(
            _poly_multiply(_component(left_x, logical), _component(right_z, logical)),
            _poly_multiply(_component(left_z, logical), _component(right_x, logical)),
        )
        result = _poly_xor(result, local)
    return result


def _axis_conflicts(
    left: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
    right: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
) -> tuple[tuple[str, _Poly], ...]:
    left_x, left_z, _ = left
    right_x, right_z, _ = right
    result = []
    logicals = sorted(set(left_x) | set(left_z) | set(right_x) | set(right_z))
    for logical in logicals:
        conflict = _poly_xor(
            _poly_multiply(_component(left_x, logical), _component(right_z, logical)),
            _poly_multiply(_component(left_z, logical), _component(right_x, logical)),
        )
        if conflict:
            result.append((logical, conflict))
    return tuple(result)


_WordKey = tuple[
    tuple[tuple[str, _Poly], ...],
    tuple[tuple[str, _Poly], ...],
    _Poly,
]


def _poly_restrict(polynomial: _Poly, variable: str, value: int) -> _Poly:
    terms: set[tuple[str, ...]] = set()
    for monomial in polynomial:
        if variable in monomial:
            if value == 0:
                continue
            restricted = tuple(item for item in monomial if item != variable)
        else:
            restricted = monomial
        if restricted in terms:
            terms.remove(restricted)
        else:
            terms.add(restricted)
    return frozenset(terms)


def _word_restrict(word: _WordKey, variable: str, value: int) -> _WordKey:
    x, z, sign = word
    return (
        tuple(
            (logical, restricted)
            for logical, polynomial in x
            if (restricted := _poly_restrict(polynomial, variable, value))
        ),
        tuple(
            (logical, restricted)
            for logical, polynomial in z
            if (restricted := _poly_restrict(polynomial, variable, value))
        ),
        _poly_restrict(sign, variable, value),
    )


def _exact_observables(
    word: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
) -> frozenset[tuple[int, tuple[tuple[str, str], ...]]]:
    start: _WordKey = (
        tuple(sorted(word[0].items())),
        tuple(sorted(word[1].items())),
        word[2],
    )
    memo: dict[
        _WordKey,
        frozenset[tuple[int, tuple[tuple[str, str], ...]]],
    ] = {}

    def visit(current: _WordKey) -> frozenset[tuple[int, tuple[tuple[str, str], ...]]]:
        cached = memo.get(current)
        if cached is not None:
            return cached
        x_items, z_items, sign = current
        variables = sorted(
            {
                variable
                for _, polynomial in (*x_items, *z_items)
                for monomial in polynomial
                for variable in monomial
            }
            | {variable for monomial in sign for variable in monomial}
        )
        if variables:
            selected = variables[0]
            result = visit(_word_restrict(current, selected, 0)) | visit(
                _word_restrict(current, selected, 1)
            )
        else:
            x = {logical for logical, polynomial in x_items if () in polynomial}
            z = {logical for logical, polynomial in z_items if () in polynomial}
            support = []
            for logical in sorted(x | z):
                support.append(
                    (
                        logical,
                        {
                            (True, False): "X",
                            (False, True): "Z",
                            (True, True): "Y",
                        }[(logical in x, logical in z)],
                    )
                )
            result = frozenset(((int(() in sign), tuple(support)),))
        memo[current] = result
        return result

    return visit(start)


def _axis_options_and_support_polynomials(
    word: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
) -> tuple[dict[str, set[str]], tuple[_Poly, ...]]:
    x, z, _ = word
    one: _Poly = frozenset(((),))
    axis_options: dict[str, set[str]] = {}
    support_polynomials = []
    for logical in sorted(set(x) | set(z)):
        x_poly = _component(x, logical)
        z_poly = _component(z, logical)
        y = _poly_multiply(x_poly, z_poly)
        axes = {
            axis
            for axis, polynomial in (
                ("X", _poly_multiply(x_poly, _poly_xor(one, z_poly))),
                ("Y", y),
                ("Z", _poly_multiply(z_poly, _poly_xor(one, x_poly))),
            )
            if polynomial
        }
        if axes:
            axis_options[logical] = axes
        support_polynomials.append(_poly_xor(_poly_xor(x_poly, z_poly), y))
    return axis_options, tuple(support_polynomials)


def _profile(
    word: tuple[dict[str, _Poly], dict[str, _Poly], _Poly],
) -> _ProfileReplay:
    x, z, sign = word
    variables = tuple(
        sorted(
            {
                name
                for polynomial in (*x.values(), *z.values(), sign)
                for monomial in polynomial
                for name in monomial
            }
        )
    )
    polynomial_axes, _ = _axis_options_and_support_polynomials(word)
    if len(variables) <= 16:
        distinct = _exact_observables(word)
        weights = [len(support) for _, support in distinct]
        minimum_weight = min(weights)
        maximum_weight = max(weights)
        distinct_count: int | None = len(distinct)
    else:
        minimum_weight = 1
        maximum_weight = len(polynomial_axes)
        distinct_count = None
    return _ProfileReplay(
        variables=variables,
        possible_support=tuple(sorted(polynomial_axes)),
        axis_options=tuple(
            (logical, tuple(sorted(axes)))
            for logical, axes in sorted(polynomial_axes.items())
        ),
        y_content=_y_content(word),
        minimum_weight=minimum_weight,
        maximum_weight=maximum_weight,
        distinct_observables=distinct_count,
        weight_bounds_exact=len(variables) <= 16,
    )


def _graph(trace: Mapping[str, Any]) -> _GraphReplay:
    source_operations = _sequence(trace.get("source_operations"), "$.source_operations")
    emitted = tuple(
        operation_id
        for source_index, source_value in enumerate(source_operations)
        for operation_id in _strings(
            _mapping(source_value, f"$.source_operations[{source_index}]").get(
                "emitted_operation_ids"
            ),
            f"$.source_operations[{source_index}].emitted_operation_ids",
        )
    )
    if len(emitted) != len(set(emitted)):
        raise DirectCczPpmBatchingReplayError("trace has duplicate semantic operation IDs")
    node_order = {operation_id: index for index, operation_id in enumerate(emitted)}
    predecessors: dict[str, set[str]] = {operation_id: set() for operation_id in emitted}

    for index, value in enumerate(
        _sequence(trace.get("clifford_instructions"), "$.clifford_instructions")
    ):
        item = _mapping(value, f"$.clifford_instructions[{index}]")
        operation_id = _string(
            item.get("operation_id"), f"$.clifford_instructions[{index}].operation_id"
        )
        predecessors[operation_id].update(
            _strings(
                item.get("predecessor_operation_ids"),
                f"$.clifford_instructions[{index}].predecessor_operation_ids",
            )
        )
    ppm_items = _sequence(trace.get("ppms"), "$.ppms")
    outcomes: dict[str, str] = {}
    ppm_ids: set[str] = set()
    for index, value in enumerate(ppm_items):
        item = _mapping(value, f"$.ppms[{index}]")
        operation_id = _string(item.get("operation_id"), f"$.ppms[{index}].operation_id")
        outcome = _string(item.get("outcome_token"), f"$.ppms[{index}].outcome_token")
        ppm_ids.add(operation_id)
        outcomes[outcome] = operation_id
        predecessors[operation_id].update(
            _strings(
                item.get("predecessor_operation_ids"),
                f"$.ppms[{index}].predecessor_operation_ids",
            )
        )
    update_ids: set[str] = set()
    for index, value in enumerate(
        _sequence(trace.get("correction_updates"), "$.correction_updates")
    ):
        item = _mapping(value, f"$.correction_updates[{index}]")
        update_id = _string(
            item.get("update_id"), f"$.correction_updates[{index}].update_id"
        )
        update_ids.add(update_id)
        predecessors[update_id].update(
            outcomes[token]
            for token in _strings(
                item.get("outcome_dependencies"),
                f"$.correction_updates[{index}].outcome_dependencies",
            )
        )
    for index, value in enumerate(
        _sequence(trace.get("injections"), "$.injections")
    ):
        item = _mapping(value, f"$.injections[{index}]")
        completion_id = _string(
            item.get("completion_id"), f"$.injections[{index}].completion_id"
        )
        predecessors[completion_id].update(
            _strings(
                item.get("completion_predecessor_ids"),
                f"$.injections[{index}].completion_predecessor_ids",
            )
        )
    unknown = {
        predecessor
        for values in predecessors.values()
        for predecessor in values
        if predecessor not in predecessors
    }
    if unknown:
        raise DirectCczPpmBatchingReplayError(
            "trace graph references unknown nodes: " + ", ".join(sorted(unknown))
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
        raise DirectCczPpmBatchingReplayError("trace semantic graph is cyclic")
    ancestors: dict[str, frozenset[str]] = {}
    reactions: dict[str, frozenset[str]] = {}
    for node in topological:
        ordinary: set[str] = set()
        reaction: set[str] = set()
        for predecessor in predecessors[node]:
            ordinary.update(ancestors[predecessor])
            reaction.update(reactions[predecessor])
            if predecessor in ppm_ids:
                ordinary.add(predecessor)
            if node in update_ids:
                reaction.update(ancestors[predecessor])
                if predecessor in ppm_ids:
                    reaction.add(predecessor)
        ancestors[node] = frozenset(ordinary)
        reactions[node] = frozenset(reaction)
    return _GraphReplay(
        predecessors={key: frozenset(value) for key, value in predecessors.items()},
        ppm_ancestors=ancestors,
        reaction_ancestors=reactions,
        topological_ppms=tuple(node for node in topological if node in ppm_ids),
        node_order=node_order,
    )


def _assert_poly_data(value: object, expected: _Poly, path: str) -> None:
    if _poly(value, path) != expected:
        raise DirectCczPpmBatchingReplayError(f"{path} does not match exact ANF replay")


def _assert_no_forbidden_keys(value: object, path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            if key in _FORBIDDEN_GENERAL_TIME_KEYS:
                raise DirectCczPpmBatchingReplayError(
                    f"{path} contains forbidden native-result key {key!r}"
                )
            _assert_no_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _assert_no_forbidden_keys(child, f"{path}[{index}]")


def _longest_path(graph: _GraphReplay, ppm_ids: frozenset[str]) -> int:
    scores: dict[str, int] = {}
    for node in sorted(graph.node_order, key=graph.node_order.__getitem__):
        scores[node] = (1 if node in ppm_ids else 0) + max(
            (scores[predecessor] for predecessor in graph.predecessors[node]),
            default=0,
        )
    return max(scores.values(), default=0)


def _clique_lower_bound(
    ppm_order: tuple[str, ...],
    compatible: dict[frozenset[str], bool],
) -> int:
    graph = nx.Graph()
    graph.add_nodes_from(ppm_order)
    graph.add_edges_from(
        (left, right)
        for left, right in combinations(ppm_order, 2)
        if not compatible[frozenset((left, right))]
    )
    return max((len(clique) for clique in nx.find_cliques(graph)), default=0)


def _validate_schedule(
    value: object,
    path: str,
    trace: Mapping[str, Any],
    graph: _GraphReplay,
    profiles: dict[str, _ProfileReplay],
    compatible: dict[frozenset[str], bool],
    *,
    source_aligned: bool,
) -> tuple[int, int, int]:
    schedule = _mapping(value, path)
    if _boolean(schedule.get("complete_native_schedule"), f"{path}.complete_native_schedule"):
        raise DirectCczPpmBatchingReplayError(f"{path} forges a native schedule")
    if schedule.get("unit") != "candidate_batch_level_not_time":
        raise DirectCczPpmBatchingReplayError(f"{path} has an invalid unit")
    batches = _sequence(schedule.get("batches"), f"{path}.batches")
    level_by_operation: dict[str, int] = {}
    batch_records: list[Mapping[str, Any]] = []
    for index, batch_value in enumerate(batches, start=1):
        batch = _mapping(batch_value, f"{path}.batches[{index - 1}]")
        if _integer(batch.get("batch_level"), f"{path}.batches[{index - 1}].batch_level") != index:
            raise DirectCczPpmBatchingReplayError(f"{path} batch levels are not contiguous")
        operation_ids = _strings(
            batch.get("operation_ids"), f"{path}.batches[{index - 1}].operation_ids"
        )
        if not operation_ids:
            raise DirectCczPpmBatchingReplayError(f"{path} contains an empty batch")
        for operation_id in operation_ids:
            if operation_id in level_by_operation:
                raise DirectCczPpmBatchingReplayError(
                    f"{path} repeats PPM {operation_id}"
                )
            level_by_operation[operation_id] = index
        for left, right in combinations(operation_ids, 2):
            if not compatible[frozenset((left, right))]:
                raise DirectCczPpmBatchingReplayError(
                    f"{path} batches incompatible PPMs {left} and {right}"
                )
        if batch.get("execution_class") != "general_high_rate_candidate":
            raise DirectCczPpmBatchingReplayError(
                f"{path} unexpectedly contains a fallback operation"
            )
        source_layers = tuple(
            _integer(item, f"{path}.batches[{index - 1}].source_algorithmic_layers")
            for item in _sequence(
                batch.get("source_algorithmic_layers"),
                f"{path}.batches[{index - 1}].source_algorithmic_layers",
            )
        )
        if source_aligned and len(source_layers) != 1:
            raise DirectCczPpmBatchingReplayError(
                f"{path} violates the source-layer alignment policy"
            )
        batch_records.append(batch)
    if set(level_by_operation) != set(graph.topological_ppms):
        raise DirectCczPpmBatchingReplayError(
            f"{path} does not cover every PPM exactly once"
        )
    for operation_id, level in level_by_operation.items():
        if any(level_by_operation[ancestor] >= level for ancestor in graph.ppm_ancestors[operation_id]):
            raise DirectCczPpmBatchingReplayError(
                f"{path} violates causal order at {operation_id}"
            )

    ppm_items = {
        _string(item.get("operation_id"), "$.ppms[].operation_id"): item
        for item in (
            _mapping(value, "$.ppms[]")
            for value in _sequence(trace.get("ppms"), "$.ppms")
        )
    }
    logical_lifetimes = tuple(
        _mapping(value, "$.logical_lifetimes[]")
        for value in _sequence(trace.get("logical_lifetimes"), "$.logical_lifetimes")
    )
    resource_intervals: dict[str, tuple[int, int]] = {}
    resource_events: dict[str, str] = {}
    for lifetime_value in _sequence(
        trace.get("resource_lifetimes"), "$.resource_lifetimes"
    ):
        lifetime = _mapping(lifetime_value, "$.resource_lifetimes[]")
        first = min(
            level_by_operation[operation_id]
            for operation_id in _strings(
                lifetime.get("first_ppm_operation_ids"),
                "$.resource_lifetimes[].first_ppm_operation_ids",
            )
        )
        last = max(
            level_by_operation[operation_id]
            for operation_id in _strings(
                lifetime.get("terminal_ppm_operation_ids"),
                "$.resource_lifetimes[].terminal_ppm_operation_ids",
            )
        )
        event_id = _string(
            lifetime.get("injection_event_id"),
            "$.resource_lifetimes[].injection_event_id",
        )
        for logical in _strings(
            lifetime.get("resource_values"), "$.resource_lifetimes[].resource_values"
        ):
            resource_intervals[logical] = (first, last)
            resource_events[logical] = event_id

    peak_live = 0
    for index, batch in enumerate(batch_records, start=1):
        operation_ids = _strings(batch.get("operation_ids"), f"{path}.batches[].operation_ids")
        source_layers = tuple(
            sorted(
                {
                    _integer(
                        ppm_items[operation_id].get("source_algorithmic_layer"),
                        "$.ppms[].source_algorithmic_layer",
                    )
                    for operation_id in operation_ids
                }
            )
        )
        expected_source = tuple(
            _string(lifetime.get("logical_value"), "$.logical_lifetimes[].logical_value")
            for lifetime in logical_lifetimes
            if any(
                (
                    (
                        1
                        if lifetime.get("origin") == "source_input"
                        else _integer(
                            lifetime.get("first_source_layer"),
                            "$.logical_lifetimes[].first_source_layer",
                        )
                    )
                    <= source_layer
                    <= _integer(
                        lifetime.get("last_source_layer"),
                        "$.logical_lifetimes[].last_source_layer",
                    )
                )
                for source_layer in source_layers
            )
        )
        expected_resource = tuple(
            sorted(
                logical
                for logical, (first, last) in resource_intervals.items()
                if first <= index <= last
            )
        )
        if _strings(batch.get("live_source_logicals"), f"{path}.batches[].live_source_logicals") != expected_source:
            raise DirectCczPpmBatchingReplayError(f"{path} source liveness mismatch")
        if _strings(batch.get("live_resource_logicals"), f"{path}.batches[].live_resource_logicals") != expected_resource:
            raise DirectCczPpmBatchingReplayError(f"{path} resource liveness mismatch")
        expected_total = len(expected_source) + len(expected_resource)
        if _integer(batch.get("total_live_logical_requirement"), f"{path}.batches[].total_live_logical_requirement") != expected_total:
            raise DirectCczPpmBatchingReplayError(f"{path} total liveness mismatch")
        expected_states = len({resource_events[logical] for logical in expected_resource})
        if _integer(batch.get("resource_state_count"), f"{path}.batches[].resource_state_count") != expected_states:
            raise DirectCczPpmBatchingReplayError(f"{path} resource-state count mismatch")
        peak_live = max(peak_live, expected_total)

    causal_lower = _longest_path(graph, frozenset(graph.topological_ppms))
    lower = _mapping(schedule.get("lower_bounds"), f"{path}.lower_bounds")
    clique_method = lower.get(
        "conflict_clique_bound_method",
        "exact_maximum_conflict_clique",
    )
    if clique_method == "exact_maximum_conflict_clique":
        clique_lower = _clique_lower_bound(graph.topological_ppms, compatible)
    elif clique_method == "single_vertex_proved_lower_bound_large_instance":
        if len(graph.topological_ppms) <= 60:
            raise DirectCczPpmBatchingReplayError(
                f"{path} used the large-instance clique witness below its threshold"
            )
        clique_lower = int(bool(graph.topological_ppms))
    else:
        raise DirectCczPpmBatchingReplayError(
            f"{path} has an unsupported conflict-clique bound method"
        )
    if _integer(lower.get("causal_critical_path_batch_levels"), f"{path}.lower_bounds.causal") != causal_lower:
        raise DirectCczPpmBatchingReplayError(f"{path} causal lower bound mismatch")
    if _integer(lower.get("conflict_clique_batch_levels"), f"{path}.lower_bounds.clique") != clique_lower:
        raise DirectCczPpmBatchingReplayError(f"{path} conflict-clique lower bound mismatch")
    if _integer(schedule.get("candidate_batch_level_count"), f"{path}.candidate_batch_level_count") != len(batches):
        raise DirectCczPpmBatchingReplayError(f"{path} batch count mismatch")
    if _integer(schedule.get("peak_live_logical_requirement"), f"{path}.peak_live_logical_requirement") != peak_live:
        raise DirectCczPpmBatchingReplayError(f"{path} peak liveness mismatch")
    return len(batches), causal_lower, clique_lower


def replay_direct_ccz_ppm_batching(
    trace_data: Mapping[str, Any],
    general_candidate_data: Mapping[str, Any],
    finite_admission_data: Mapping[str, Any],
    fallback_data: Mapping[str, Any],
    frontier_data: Mapping[str, Any],
    capability_data: Mapping[str, Any],
    backend_audit_data: Mapping[str, Any],
) -> DirectCczPpmBatchingReplaySummary:
    """Independently replay every Phase-B artifact and return checked counts."""

    trace = _mapping(trace_data, "$trace")
    general = _mapping(general_candidate_data, "$general")
    finite = _mapping(finite_admission_data, "$finite")
    fallback = _mapping(fallback_data, "$fallback")
    frontier = _mapping(frontier_data, "$frontier")
    capability = _mapping(capability_data, "$capability")
    audit = _mapping(backend_audit_data, "$audit")
    trace_id = _string(trace.get("trace_id"), "$trace.trace_id")
    if general.get("schema") != _GENERAL_SCHEMA or general.get("schema_version") != 1:
        raise DirectCczPpmBatchingReplayError("general artifact schema mismatch")
    if finite.get("schema") != _FINITE_SCHEMA or finite.get("schema_version") != 1:
        raise DirectCczPpmBatchingReplayError("finite artifact schema mismatch")
    if fallback.get("schema") != _FALLBACK_SCHEMA or fallback.get("schema_version") != 1:
        raise DirectCczPpmBatchingReplayError("fallback artifact schema mismatch")
    if frontier.get("schema") != _FRONTIER_SCHEMA or frontier.get("schema_version") != 1:
        raise DirectCczPpmBatchingReplayError("frontier artifact schema mismatch")
    if any(value.get("trace_id") != trace_id for value in (general, finite, fallback, frontier)):
        raise DirectCczPpmBatchingReplayError("Phase-B trace identities disagree")
    if trace.get("complete_native_schedule") is not False:
        raise DirectCczPpmBatchingReplayError("input trace claims a native schedule")
    _assert_no_forbidden_keys(general, "$general")
    _assert_no_forbidden_keys(fallback, "$fallback")
    _assert_no_forbidden_keys(frontier, "$frontier")

    graph = _graph(trace)
    ppm_values = _sequence(trace.get("ppms"), "$trace.ppms")
    ppm_items = tuple(
        _mapping(value, f"$trace.ppms[{index}]")
        for index, value in enumerate(ppm_values)
    )
    ppm_by_id = {
        _string(item.get("operation_id"), "$trace.ppms[].operation_id"): item
        for item in ppm_items
    }
    words = {
        operation_id: _word(
            item.get("presented_observable"),
            f"$trace.ppms[{operation_id}].presented_observable",
        )
        for operation_id, item in ppm_by_id.items()
    }
    replay_profiles = {operation_id: _profile(word) for operation_id, word in words.items()}
    profile_values = _sequence(general.get("observable_profiles"), "$general.observable_profiles")
    if len(profile_values) != len(ppm_items):
        raise DirectCczPpmBatchingReplayError("observable profile count mismatch")
    profile_artifacts: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(profile_values):
        item = _mapping(value, f"$general.observable_profiles[{index}]")
        operation_id = _string(item.get("operation_id"), "$general.observable_profiles[].operation_id")
        expected = replay_profiles[operation_id]
        profile_artifacts[operation_id] = item
        if _strings(item.get("variables"), "$general.observable_profiles[].variables") != expected.variables:
            raise DirectCczPpmBatchingReplayError(f"profile variables mismatch for {operation_id}")
        if _strings(item.get("possible_logical_support"), "$general.observable_profiles[].support") != expected.possible_support:
            raise DirectCczPpmBatchingReplayError(f"profile support mismatch for {operation_id}")
        axes = tuple(
            (
                _string(_mapping(axis, "$general.axis_options[]").get("logical_value"), "$general.axis_options[].logical_value"),
                _strings(_mapping(axis, "$general.axis_options[]").get("axes"), "$general.axis_options[].axes"),
            )
            for axis in _sequence(item.get("axis_options"), "$general.observable_profiles[].axis_options")
        )
        if axes != expected.axis_options:
            raise DirectCczPpmBatchingReplayError(f"profile axes mismatch for {operation_id}")
        if _boolean(item.get("has_possible_y"), "$general.observable_profiles[].has_possible_y") != bool(expected.y_content):
            raise DirectCczPpmBatchingReplayError(f"profile Y flag mismatch for {operation_id}")
        if _integer(item.get("minimum_weight"), "$general.observable_profiles[].minimum_weight") != expected.minimum_weight:
            raise DirectCczPpmBatchingReplayError(f"profile minimum weight mismatch for {operation_id}")
        if _integer(item.get("maximum_weight"), "$general.observable_profiles[].maximum_weight") != expected.maximum_weight:
            raise DirectCczPpmBatchingReplayError(f"profile maximum weight mismatch for {operation_id}")
        observed_distinct = item.get("distinct_branch_observables")
        if observed_distinct is not None:
            observed_distinct = _integer(
                observed_distinct,
                "$general.observable_profiles[].distinct",
            )
        if observed_distinct != expected.distinct_observables:
            raise DirectCczPpmBatchingReplayError(f"profile branch count mismatch for {operation_id}")
        observed_weight_exact = item.get("weight_bounds_exact", True)
        if not isinstance(observed_weight_exact, bool):
            raise DirectCczPpmBatchingReplayError(
                f"profile weight-bound status is invalid for {operation_id}"
            )
        if observed_weight_exact != expected.weight_bounds_exact:
            raise DirectCczPpmBatchingReplayError(
                f"profile weight-bound status mismatch for {operation_id}"
            )
        y_values = _sequence(item.get("y_content"), "$general.observable_profiles[].y_content")
        if len(y_values) != len(expected.y_content):
            raise DirectCczPpmBatchingReplayError(f"profile Y content mismatch for {operation_id}")
        for y_value, (logical, polynomial) in zip(y_values, expected.y_content, strict=True):
            y_item = _mapping(y_value, "$general.y_content[]")
            if y_item.get("logical_value") != logical:
                raise DirectCczPpmBatchingReplayError(f"profile Y index mismatch for {operation_id}")
            _assert_poly_data(y_item.get("polynomial"), polynomial, "$general.y_content[].polynomial")

    resources = frozenset(
        logical
        for value in _sequence(trace.get("resource_lifetimes"), "$trace.resource_lifetimes")
        for logical in _strings(
            _mapping(value, "$trace.resource_lifetimes[]").get("resource_values"),
            "$trace.resource_lifetimes[].resource_values",
        )
    )
    expected_relations: dict[frozenset[str], _PairReplay] = {}
    for left_id, right_id in combinations(graph.topological_ppms, 2):
        if left_id in graph.ppm_ancestors[right_id]:
            causal = "left_before_right"
            reaction = left_id in graph.reaction_ancestors[right_id]
        elif right_id in graph.ppm_ancestors[left_id]:
            causal = "right_before_left"
            reaction = right_id in graph.reaction_ancestors[left_id]
        else:
            causal = "none"
            reaction = False
        shared = tuple(
            sorted(
                set(replay_profiles[left_id].possible_support)
                & set(replay_profiles[right_id].possible_support)
            )
        )
        expected_relations[frozenset((left_id, right_id))] = _PairReplay(
            causal_order=causal,
            reaction_dependent=reaction,
            shared_logicals=shared,
            shared_resources=tuple(logical for logical in shared if logical in resources),
            commutator=_commutator(words[left_id], words[right_id]),
            axis_conflicts=_axis_conflicts(words[left_id], words[right_id]),
            left_y=bool(replay_profiles[left_id].y_content),
            right_y=bool(replay_profiles[right_id].y_content),
        )
    relation_values = _sequence(general.get("pair_relations"), "$general.pair_relations")
    if len(relation_values) != len(expected_relations):
        raise DirectCczPpmBatchingReplayError("pair relation count mismatch")
    seen_pairs: set[frozenset[str]] = set()
    for index, value in enumerate(relation_values):
        item = _mapping(value, f"$general.pair_relations[{index}]")
        left = _string(item.get("left_operation_id"), "$general.pair_relations[].left")
        right = _string(item.get("right_operation_id"), "$general.pair_relations[].right")
        key = frozenset((left, right))
        expected_relation = expected_relations[key]
        seen_pairs.add(key)
        if item.get("causal_order") != expected_relation.causal_order:
            raise DirectCczPpmBatchingReplayError(f"causal relation mismatch for {left}, {right}")
        if _boolean(item.get("reaction_dependent"), "$general.pair_relations[].reaction") != expected_relation.reaction_dependent:
            raise DirectCczPpmBatchingReplayError(f"reaction relation mismatch for {left}, {right}")
        if _strings(item.get("shared_logical_values"), "$general.pair_relations[].shared") != expected_relation.shared_logicals:
            raise DirectCczPpmBatchingReplayError(f"shared support mismatch for {left}, {right}")
        if _strings(item.get("shared_resource_values"), "$general.pair_relations[].resources") != expected_relation.shared_resources:
            raise DirectCczPpmBatchingReplayError(f"resource reuse mismatch for {left}, {right}")
        _assert_poly_data(item.get("symplectic_commutator"), expected_relation.commutator, "$general.pair_relations[].commutator")
        axis_values = _sequence(item.get("axis_conflicts"), "$general.pair_relations[].axis_conflicts")
        if len(axis_values) != len(expected_relation.axis_conflicts):
            raise DirectCczPpmBatchingReplayError(f"axis conflict count mismatch for {left}, {right}")
        for axis_value, (logical, polynomial) in zip(
            axis_values,
            expected_relation.axis_conflicts,
            strict=True,
        ):
            axis_item = _mapping(axis_value, "$general.axis_conflicts[]")
            if axis_item.get("logical_value") != logical:
                raise DirectCczPpmBatchingReplayError(f"axis conflict index mismatch for {left}, {right}")
            _assert_poly_data(axis_item.get("polynomial"), polynomial, "$general.axis_conflicts[].polynomial")
        if _boolean(item.get("general_high_rate_compatible"), "$general.pair_relations[].compatible") != expected_relation.compatible:
            raise DirectCczPpmBatchingReplayError(f"compatibility flag mismatch for {left}, {right}")
    if seen_pairs != set(expected_relations):
        raise DirectCczPpmBatchingReplayError("pair relation identities are incomplete")
    compatible = {key: relation.compatible for key, relation in expected_relations.items()}

    optimized_count, causal_lower, clique_lower = _validate_schedule(
        general.get("optimized_schedule"),
        "$general.optimized_schedule",
        trace,
        graph,
        replay_profiles,
        compatible,
        source_aligned=False,
    )
    source_count, source_causal, source_clique = _validate_schedule(
        general.get("source_layer_aligned_schedule"),
        "$general.source_layer_aligned_schedule",
        trace,
        graph,
        replay_profiles,
        compatible,
        source_aligned=True,
    )
    if (source_causal, source_clique) != (causal_lower, clique_lower):
        raise DirectCczPpmBatchingReplayError("schedule lower bounds disagree")

    capability_admission = _mapping(capability.get("admission"), "$capability.admission")
    audit_admission = _mapping(audit.get("admission"), "$audit.admission")
    capability_missing = _strings(
        capability_admission.get("missing_for_high_rate_schedule"),
        "$capability.admission.missing_for_high_rate_schedule",
    )
    backend_missing = _strings(
        audit_admission.get("missing_fields"), "$audit.admission.missing_fields"
    )
    backend_incompatible = _strings(
        audit_admission.get("incompatible_fields"),
        "$audit.admission.incompatible_fields",
    )
    if finite.get("schedule") is not None or finite.get("runtime_seconds") is not None:
        raise DirectCczPpmBatchingReplayError("finite rejection must keep schedule and runtime null")
    if finite.get("physical_qubits") is not None or finite.get("failure_probability") is not None:
        raise DirectCczPpmBatchingReplayError("finite rejection forged physical outputs")
    if finite.get("native_schedule_emitted") is not False:
        raise DirectCczPpmBatchingReplayError("finite rejection claims a schedule")
    if finite.get("finite_backend_admitted") is not False:
        raise DirectCczPpmBatchingReplayError("finite backend admission disagrees with audit")
    if _strings(finite.get("capability_missing_fields"), "$finite.capability_missing_fields") != capability_missing:
        raise DirectCczPpmBatchingReplayError("finite capability missing-field list mismatch")
    if _strings(finite.get("backend_missing_fields"), "$finite.backend_missing_fields") != backend_missing:
        raise DirectCczPpmBatchingReplayError("finite backend missing-field list mismatch")
    if _strings(finite.get("backend_incompatible_fields"), "$finite.backend_incompatible_fields") != backend_incompatible:
        raise DirectCczPpmBatchingReplayError("finite backend incompatibility list mismatch")
    if _strings(
        finite.get("native_mapper_missing_fields"),
        "$finite.native_mapper_missing_fields",
    ) != _FINITE_NATIVE_MAPPER_OBLIGATIONS:
        raise DirectCczPpmBatchingReplayError(
            "finite native-mapper obligation list mismatch"
        )

    fallback_operations = _sequence(fallback.get("operations"), "$fallback.operations")
    fallback_ids = tuple(
        _string(_mapping(value, "$fallback.operations[]").get("operation_id"), "$fallback.operations[].operation_id")
        for value in fallback_operations
    )
    if fallback_ids != graph.topological_ppms:
        raise DirectCczPpmBatchingReplayError("low-rate fallback is not the canonical topological order")
    for index, value in enumerate(fallback_operations, start=1):
        item = _mapping(value, "$fallback.operations[]")
        operation_id = fallback_ids[index - 1]
        if _integer(item.get("semantic_order"), "$fallback.operations[].semantic_order") != index:
            raise DirectCczPpmBatchingReplayError("low-rate semantic order is not contiguous")
        expected_reactions = tuple(
            sorted(graph.reaction_ancestors[operation_id], key=graph.node_order.__getitem__)
        )
        if _strings(item.get("reaction_predecessor_operation_ids"), "$fallback.operations[].reactions") != expected_reactions:
            raise DirectCczPpmBatchingReplayError(f"low-rate reaction boundary mismatch for {operation_id}")
    if fallback.get("finite_cost_status") != EvidenceStatus.OPEN.value:
        raise DirectCczPpmBatchingReplayError("low-rate finite cost must remain OPEN")

    strategy_values = _sequence(frontier.get("strategies"), "$frontier.strategies")
    strategies = {
        _string(_mapping(value, "$frontier.strategies[]").get("strategy_id"), "$frontier.strategies[].strategy_id"): _mapping(value, "$frontier.strategies[]")
        for value in strategy_values
    }
    required_strategy_ids = {
        "fully_frame_folded_singleton",
        "source_layer_aligned",
        "measured_operator_product_rewrites",
        "selective_clifford_materialization",
        "high_rate_batch_splitting",
        "low_rate_singleton_fallback",
    }
    if set(strategies) != required_strategy_ids:
        raise DirectCczPpmBatchingReplayError("strategy frontier is incomplete")
    if strategies["high_rate_batch_splitting"].get("candidate_batch_levels") != optimized_count:
        raise DirectCczPpmBatchingReplayError("optimized strategy metric mismatch")
    if strategies["source_layer_aligned"].get("candidate_batch_levels") != source_count:
        raise DirectCczPpmBatchingReplayError("source-aligned strategy metric mismatch")
    if strategies["fully_frame_folded_singleton"].get("candidate_batch_levels") != len(ppm_items):
        raise DirectCczPpmBatchingReplayError("singleton baseline metric mismatch")
    for strategy_id in (
        "measured_operator_product_rewrites",
        "selective_clifford_materialization",
    ):
        if strategies[strategy_id].get("admitted_transform_count") != 0:
            raise DirectCczPpmBatchingReplayError(
                f"{strategy_id} claims an unverified transform"
            )

    relations = tuple(expected_relations.values())
    return DirectCczPpmBatchingReplaySummary(
        trace_id=trace_id,
        ppm_count=len(ppm_items),
        observable_profile_count=len(profile_values),
        pair_relation_count=len(relations),
        symbolic_commutation_checks=len(relations),
        symbolic_axis_checks=len(relations),
        possible_y_ppm_count=sum(bool(profile.y_content) for profile in replay_profiles.values()),
        axis_conflict_pair_count=sum(bool(relation.axis_conflicts) for relation in relations),
        anticommuting_pair_count=sum(bool(relation.commutator) for relation in relations),
        causal_pair_count=sum(relation.causal_order != "none" for relation in relations),
        reaction_pair_count=sum(relation.reaction_dependent for relation in relations),
        compatible_overlap_pair_count=sum(
            relation.compatible and bool(relation.shared_logicals) for relation in relations
        ),
        optimized_candidate_batch_levels=optimized_count,
        source_layer_candidate_batch_levels=source_count,
        causal_lower_bound=causal_lower,
        conflict_clique_lower_bound=clique_lower,
        low_rate_singleton_count=len(fallback_ids),
        finite_capability_missing_field_count=len(capability_missing),
        finite_backend_missing_field_count=len(backend_missing),
        finite_backend_incompatible_field_count=len(backend_incompatible),
        finite_schedule_rejected=True,
        all_passed=True,
    )


def direct_ccz_ppm_batching_replay_to_data(
    summary: DirectCczPpmBatchingReplaySummary,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible independent replay counts."""

    return {
        "all_passed": summary.all_passed,
        "anticommuting_pair_count": summary.anticommuting_pair_count,
        "axis_conflict_pair_count": summary.axis_conflict_pair_count,
        "causal_lower_bound": summary.causal_lower_bound,
        "causal_pair_count": summary.causal_pair_count,
        "compatible_overlap_pair_count": summary.compatible_overlap_pair_count,
        "conflict_clique_lower_bound": summary.conflict_clique_lower_bound,
        "evidence_status": summary.evidence_status.value,
        "finite_backend_incompatible_field_count": (
            summary.finite_backend_incompatible_field_count
        ),
        "finite_backend_missing_field_count": summary.finite_backend_missing_field_count,
        "finite_capability_missing_field_count": (
            summary.finite_capability_missing_field_count
        ),
        "finite_schedule_rejected": summary.finite_schedule_rejected,
        "low_rate_singleton_count": summary.low_rate_singleton_count,
        "observable_profile_count": summary.observable_profile_count,
        "optimized_candidate_batch_levels": (
            summary.optimized_candidate_batch_levels
        ),
        "pair_relation_count": summary.pair_relation_count,
        "possible_y_ppm_count": summary.possible_y_ppm_count,
        "ppm_count": summary.ppm_count,
        "reaction_pair_count": summary.reaction_pair_count,
        "source_layer_candidate_batch_levels": (
            summary.source_layer_candidate_batch_levels
        ),
        "symbolic_axis_checks": summary.symbolic_axis_checks,
        "symbolic_commutation_checks": summary.symbolic_commutation_checks,
        "trace_id": summary.trace_id,
    }
