"""Scalable PPM support envelopes for reviewed direct-CCZ QCLA traces.

The compatibility certificate proves that every phase-one observable remains
Z type.  This module refines that result with exact Boolean-ANF support for OOP
traces and small IP anchors, plus sound may-support upper envelopes and
concrete branch witnesses for large IP traces.  It deliberately reports
logical support hypergraphs, not native placement, surgery rounds, or runtime.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from ecdlp_ftqc.circuits import OopQclaTrace, QclaGateKind, QclaTrace
from ecdlp_ftqc.compiler import (
    BooleanPolynomial,
    DirectCczEventTrace,
    SymbolicDirectCczPpmTrace,
)
from ecdlp_ftqc.metadata import EvidenceStatus
from ecdlp_ftqc.scheduler.direct_ccz_ppm_compatibility_certificate import (
    QclaVariant,
    certify_qcla_direct_ccz_ppm_compatibility,
)

DIRECT_CCZ_PPM_SUPPORT_CERTIFICATE_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-scalable-support-certificate"
)
DIRECT_CCZ_PPM_SUPPORT_CERTIFICATE_SCHEMA_VERSION = 1
DIRECT_CCZ_PPM_SUPPORT_EXACT_EQUIVALENCE_SCHEMA = (
    "ecdlp-ftqc/direct-ccz-qcla-exact-support-equivalence"
)
SUPPORT_COORDINATE = "logical_support_hypergraph_not_native_geometry"
SUPPORT_MODEL = "exact-boolean-anf-z-support-components-v1"

Axis = Literal["X", "Z"]
ActivityCertificateKind = Literal[
    "exact_anf_zdd",
    "saturated_may_envelope",
    "unwitnessed_may_envelope",
]


class DirectCczPpmSupportCertificateError(ValueError):
    """Raised when support-certificate inputs are inconsistent."""


@dataclass(frozen=True, slots=True)
class SupportValidationCounterexample:
    """The first deterministic witness to an invalid support-model premise."""

    obligation: str
    source_algorithmic_layer: int | None
    source_gate_id: str | None
    event_id: str | None
    detail: str


@dataclass(frozen=True, slots=True)
class SupportActivity:
    """Exact or sound-bounded activity for one Pauli support component."""

    logical_value: str
    certificate_kind: ActivityCertificateKind
    anf_zdd_sha256: str | None
    anf_zdd_node_count: int | None
    anf_monomial_count: int | None
    variables: tuple[str, ...]
    constant_term: bool | None
    is_always_active: bool
    is_branch_dependent: bool
    anf_monomials: tuple[tuple[str, ...], ...] | None
    sample_evaluation_sha256: str | None
    one_witness_sample: int | None
    zero_witness_sample: int | None

    def __post_init__(self) -> None:
        if self.certificate_kind == "exact_anf_zdd":
            if (
                self.anf_monomial_count is None
                or self.anf_monomial_count < 1
                or self.anf_zdd_node_count is None
                or self.anf_zdd_node_count < 1
                or self.anf_zdd_sha256 is None
            ):
                raise DirectCczPpmSupportCertificateError(
                    "exact support activity must encode a nonzero Boolean function"
                )
        elif self.sample_evaluation_sha256 is None:
            raise DirectCczPpmSupportCertificateError(
                "sampled support activity must bind its branch evaluations"
            )
        if self.is_always_active and self.is_branch_dependent:
            raise DirectCczPpmSupportCertificateError(
                "support activity cannot be both constant and branch dependent"
            )


@dataclass(frozen=True, slots=True)
class PpmSupportProfile:
    """Exact component activities and support envelope for one PPM."""

    operation_id: str
    source_gate_id: str
    injection_event_id: str
    source_algorithmic_layer: int
    injection_layer: int
    axis: Axis
    activities: tuple[SupportActivity, ...]
    possible_logical_support: tuple[str, ...]
    witnessed_logical_support: tuple[str, ...]
    unwitnessed_may_logical_support: tuple[str, ...]
    guaranteed_logical_support: tuple[str, ...]
    branch_dependent_logical_support: tuple[str, ...]
    branch_variable_count: int
    minimum_weight_lower_bound: int
    maximum_weight_upper_bound: int
    weight_bounds_exact: bool
    outcome_independent_support: bool
    possible_support_exact: bool
    possible_support_sha256: str
    activity_anf_sha256: str
    evidence_status: EvidenceStatus


@dataclass(frozen=True, slots=True)
class PpmSupportBatch:
    """One source-aligned candidate batch represented as a support hypergraph."""

    batch_level: int
    source_algorithmic_layer: int
    injection_layer: int
    ppm_count: int
    operation_ids: tuple[str, ...]
    operation_id_sha256: str
    possible_support_union: tuple[str, ...]
    possible_support_union_sha256: str
    witnessed_support_union: tuple[str, ...]
    guaranteed_support_union: tuple[str, ...]
    branch_dependent_profile_count: int
    maximum_ppm_weight_upper_bound: int
    maximum_witnessed_support_union_size: int
    total_possible_support_incidence: int
    total_witnessed_support_incidence: int
    maximum_possible_contact_count: int
    maximum_possible_contact_logical_values: tuple[str, ...]
    possible_contact_counts: tuple[tuple[str, int], ...]
    maximum_witnessed_contact_count: int
    exact_hyperedge_count: int
    pair_records_materialized: bool
    coordinate: str
    evidence_status: EvidenceStatus


@dataclass(frozen=True, slots=True)
class SupportBranchDependenceWitness:
    """A concrete two-branch witness that PPM support is outcome dependent."""

    operation_id: str
    source_gate_id: str
    source_algorithmic_layer: int
    logical_value: str
    certificate_kind: Literal["exact_anf", "sampled_branches"]
    anf_monomials: tuple[tuple[str, ...], ...] | None
    zero_assignment: tuple[tuple[str, int], ...] | None
    one_assignment: tuple[tuple[str, int], ...] | None
    zero_sample_index: int | None
    one_sample_index: int | None
    sample_seed: str | None
    evidence_status: EvidenceStatus


@dataclass(frozen=True, slots=True)
class QclaPpmSupportCertificate:
    """Exact logical-support certificate for one QCLA width and variant."""

    variant: QclaVariant
    width: int
    source_trace_id: str
    event_trace_id: str
    support_model: str
    profiles: tuple[PpmSupportProfile, ...]
    batches: tuple[PpmSupportBatch, ...]
    source_logical_value_count: int
    direct_ccz_event_count: int
    ppm_count: int
    nonclifford_source_layer_count: int
    candidate_batch_level_count: int | None
    exact_activity_monomial_count: int | None
    branch_dependent_profile_count: int
    maximum_ppm_weight_upper_bound: int | None
    maximum_witnessed_support_union_size: int | None
    maximum_sampled_branch_weight: int | None
    maximum_batch_possible_contact_count: int | None
    maximum_batch_witnessed_contact_count: int | None
    all_possible_supports_exact: bool
    support_envelope_evidence_status: EvidenceStatus
    outcome_independent_support_evidence_status: EvidenceStatus
    branch_dependence_witness: SupportBranchDependenceWitness | None
    validation_counterexample: SupportValidationCounterexample | None
    deterministic_branch_sample_count: int
    deterministic_branch_sample_seed: str | None
    records_checked: int
    asymptotic_certificate_size: str
    complete_native_schedule: bool = False
    surgery_rounds: None = None
    runtime_seconds: None = None
    physical_qubits: None = None
    failure_probability: None = None
    schema: str = DIRECT_CCZ_PPM_SUPPORT_CERTIFICATE_SCHEMA
    schema_version: int = DIRECT_CCZ_PPM_SUPPORT_CERTIFICATE_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class ExactSupportEquivalence:
    """Comparison with a fully materialized symbolic PPM trace."""

    variant: QclaVariant
    width: int
    ppm_count: int
    component_activity_match: bool
    possible_support_match: bool
    guaranteed_support_match: bool
    branch_dependence_match: bool
    first_witness_match: bool
    all_checks_passed: bool
    evidence_status: EvidenceStatus
    schema: str = DIRECT_CCZ_PPM_SUPPORT_EXACT_EQUIVALENCE_SCHEMA
    schema_version: int = 1


PolynomialColumn = dict[str, int]
SupportMatrix = dict[str, PolynomialColumn]


class _AnfZddArena:
    """Canonical zero-suppressed decision diagrams for exact ANF term sets.

    New outcome variables arrive in chronological order and are assigned a
    successively earlier diagram rank.  Multiplication by a fresh variable is
    therefore one canonical node rather than an expansion of every monomial.
    """

    ZERO = 0
    ONE = 1

    def __init__(self) -> None:
        self._nodes: dict[int, tuple[str, int, int]] = {}
        self._unique: dict[tuple[str, int, int], int] = {}
        self._ranks: dict[str, int] = {}
        self._next_rank = 0
        self._xor_cache: dict[tuple[int, int], int] = {}
        self._digest_cache: dict[int, str] = {}
        self._variable_cache: dict[int, frozenset[str]] = {}
        self._monomial_count_cache: dict[int, int] = {}
        self._node_count_cache: dict[int, int] = {}

    def _register_fresh(self, variable: str) -> None:
        if variable in self._ranks:
            raise DirectCczPpmSupportCertificateError(
                f"support-changing outcome variable is reused: {variable}"
            )
        self._next_rank -= 1
        self._ranks[variable] = self._next_rank

    def _mk(self, variable: str, low: int, high: int) -> int:
        if high == self.ZERO:
            return low
        key = (variable, low, high)
        existing = self._unique.get(key)
        if existing is not None:
            return existing
        node = len(self._nodes) + 2
        self._nodes[node] = key
        self._unique[key] = node
        return node

    def _top(self, root: int) -> str | None:
        return None if root in {self.ZERO, self.ONE} else self._nodes[root][0]

    def xor(self, left: int, right: int) -> int:
        if left == right:
            return self.ZERO
        if left == self.ZERO:
            return right
        if right == self.ZERO:
            return left
        key = (left, right) if left < right else (right, left)
        cached = self._xor_cache.get(key)
        if cached is not None:
            return cached
        left_top = self._top(left)
        right_top = self._top(right)
        if left_top is None:
            assert right_top is not None
            right_low, right_high = self._nodes[right][1:]
            result = self._mk(
                right_top,
                self.xor(left, right_low),
                right_high,
            )
        elif right_top is None:
            left_low, left_high = self._nodes[left][1:]
            result = self._mk(
                left_top,
                self.xor(left_low, right),
                left_high,
            )
        else:
            left_rank = self._ranks[left_top]
            right_rank = self._ranks[right_top]
            if left_rank == right_rank:
                left_low, left_high = self._nodes[left][1:]
                right_low, right_high = self._nodes[right][1:]
                result = self._mk(
                    left_top,
                    self.xor(left_low, right_low),
                    self.xor(left_high, right_high),
                )
            elif left_rank < right_rank:
                left_low, left_high = self._nodes[left][1:]
                result = self._mk(
                    left_top,
                    self.xor(left_low, right),
                    left_high,
                )
            else:
                right_low, right_high = self._nodes[right][1:]
                result = self._mk(
                    right_top,
                    self.xor(left, right_low),
                    right_high,
                )
        self._xor_cache[key] = result
        return result

    def multiply_by_fresh_variable(self, root: int, variable: str) -> int:
        self._register_fresh(variable)
        return self._mk(variable, self.ZERO, root)

    def variables(self, root: int) -> tuple[str, ...]:
        cached = self._variable_cache.get(root)
        if cached is None:
            if root in {self.ZERO, self.ONE}:
                cached = frozenset()
            else:
                variable, low, high = self._nodes[root]
                cached = frozenset(
                    {variable, *self.variables(low), *self.variables(high)}
                )
            self._variable_cache[root] = cached
        return tuple(sorted(cached))

    def monomial_count(self, root: int) -> int:
        cached = self._monomial_count_cache.get(root)
        if cached is not None:
            return cached
        if root == self.ZERO:
            result = 0
        elif root == self.ONE:
            result = 1
        else:
            _, low, high = self._nodes[root]
            result = self.monomial_count(low) + self.monomial_count(high)
        self._monomial_count_cache[root] = result
        return result

    def node_count(self, root: int) -> int:
        cached = self._node_count_cache.get(root)
        if cached is not None:
            return cached
        visited: set[int] = set()

        def visit(node: int) -> None:
            if node in visited:
                return
            visited.add(node)
            if node not in {self.ZERO, self.ONE}:
                _, low, high = self._nodes[node]
                visit(low)
                visit(high)

        visit(root)
        result = len(visited)
        self._node_count_cache[root] = result
        return result

    def has_constant_term(self, root: int) -> bool:
        current = root
        while current not in {self.ZERO, self.ONE}:
            current = self._nodes[current][1]
        return current == self.ONE

    def digest(self, root: int) -> str:
        cached = self._digest_cache.get(root)
        if cached is not None:
            return cached
        if root == self.ZERO:
            payload: object = ["ZERO"]
        elif root == self.ONE:
            payload = ["ONE"]
        else:
            variable, low, high = self._nodes[root]
            payload = [variable, self.digest(low), self.digest(high)]
        result = _digest(payload)
        self._digest_cache[root] = result
        return result

    def materialize(
        self,
        root: int,
        *,
        limit: int = 4096,
    ) -> tuple[tuple[str, ...], ...] | None:
        if self.monomial_count(root) > limit:
            return None

        def build(node: int) -> tuple[tuple[str, ...], ...]:
            if node == self.ZERO:
                return ()
            if node == self.ONE:
                return ((),)
            variable, low, high = self._nodes[node]
            without = build(low)
            with_variable = tuple(
                tuple(sorted((*monomial, variable))) for monomial in build(high)
            )
            return tuple(
                sorted(
                    (*without, *with_variable),
                    key=lambda item: (len(item), item),
                )
            )

        return build(root)

    def find_assignment(self, root: int, target: int) -> tuple[tuple[str, int], ...]:
        all_variables = self.variables(root)

        def search(node: int) -> dict[str, int] | None:
            if node == self.ZERO:
                return {} if target == 0 else None
            if node == self.ONE:
                return {} if target == 1 else None
            variable, low, high = self._nodes[node]
            zero_result = search(low)
            if zero_result is not None:
                return {variable: 0, **zero_result}
            one_result = search(self.xor(low, high))
            if one_result is not None:
                return {variable: 1, **one_result}
            return None

        result = search(root)
        if result is None:
            raise DirectCczPpmSupportCertificateError(
                f"support activity cannot attain value {target}"
            )
        for variable in all_variables:
            result.setdefault(variable, 0)
        return tuple(sorted(result.items()))


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest().upper()


def _activity_rows(
    activities: tuple[SupportActivity, ...],
) -> list[dict[str, object]]:
    return [
        {
            "activity_sha256": (
                item.anf_zdd_sha256 or item.sample_evaluation_sha256
            ),
            "certificate_kind": item.certificate_kind,
            "logical_value": item.logical_value,
        }
        for item in activities
    ]


def _column_xor(
    arena: _AnfZddArena,
    columns: SupportMatrix,
    target: str,
    source: str,
    *,
    condition_variable: str | None = None,
) -> None:
    """Apply a right-side CNOT column operation, optionally conditionally."""

    target_column = columns[target]
    source_column = columns[source]
    if condition_variable is not None:
        arena._register_fresh(condition_variable)
    for logical, source_root in tuple(source_column.items()):
        contribution = (
            source_root
            if condition_variable is None
            else arena._mk(condition_variable, arena.ZERO, source_root)
        )
        updated = arena.xor(target_column.get(logical, arena.ZERO), contribution)
        if updated == arena.ZERO:
            target_column.pop(logical, None)
        else:
            target_column[logical] = updated


def _left_cnot(
    arena: _AnfZddArena,
    columns: SupportMatrix,
    control: str,
    target: str,
) -> None:
    """Apply the output-side row operation for CNOT conjugation."""

    for column in columns.values():
        target_root = column.get(target)
        if target_root is None:
            continue
        updated = arena.xor(column.get(control, arena.ZERO), target_root)
        if updated == arena.ZERO:
            column.pop(control, None)
        else:
            column[control] = updated


def _source_cnot_conjugate(
    arena: _AnfZddArena,
    columns: SupportMatrix,
    control: str,
    target: str,
) -> None:
    """Update ``M`` to ``G M G`` for a source passthrough CNOT ``G``."""

    _column_xor(arena, columns, target, control)
    _left_cnot(arena, columns, control, target)


def _expected_corrections(event: Any) -> tuple[str, ...]:
    c1, c2, target = event.data
    outcomes = tuple(ppm.outcome_token for ppm in event.ppms)
    a, b, c, x0, x1, x2 = outcomes
    return (
        f"CZ({c2},{target})^{a}",
        f"CZ({c1},{target})^{b}",
        f"CZ({c1},{c2})^{c}",
        f"Z({c1})^({x0} XOR ({b} AND {c}))",
        f"Z({c2})^({x1} XOR ({a} AND {c}))",
        f"X({target})^({x2} XOR ({a} AND {b}))",
    )


def _activities_from_column(
    arena: _AnfZddArena,
    column: PolynomialColumn,
    *,
    extra_constant: str | None = None,
) -> tuple[SupportActivity, ...]:
    rows = {
        logical: _activity_from_root(arena, logical, root)
        for logical, root in column.items()
        if root != arena.ZERO
    }
    if extra_constant is not None:
        if extra_constant in rows:
            raise DirectCczPpmSupportCertificateError(
                "fresh resource unexpectedly aliases source support"
            )
        rows[extra_constant] = _activity_from_root(
            arena,
            extra_constant,
            arena.ONE,
        )
    return tuple(rows[logical] for logical in sorted(rows))


def _activity_from_root(
    arena: _AnfZddArena,
    logical_value: str,
    root: int,
) -> SupportActivity:
    if root == arena.ZERO:
        raise DirectCczPpmSupportCertificateError(
            "zero activity must not be serialized as possible support"
        )
    return SupportActivity(
        logical_value=logical_value,
        certificate_kind="exact_anf_zdd",
        anf_zdd_sha256=arena.digest(root),
        anf_zdd_node_count=arena.node_count(root),
        anf_monomial_count=arena.monomial_count(root),
        variables=arena.variables(root),
        constant_term=arena.has_constant_term(root),
        is_always_active=root == arena.ONE,
        is_branch_dependent=root not in {arena.ZERO, arena.ONE},
        anf_monomials=arena.materialize(root),
        sample_evaluation_sha256=None,
        one_witness_sample=None,
        zero_witness_sample=None,
    )


def _profile(
    *,
    operation_id: str,
    source_gate_id: str,
    injection_event_id: str,
    source_algorithmic_layer: int,
    injection_layer: int,
    axis: Axis,
    activities: tuple[SupportActivity, ...],
    possible_support_exact: bool = True,
) -> PpmSupportProfile:
    possible = tuple(item.logical_value for item in activities)
    witnessed = tuple(
        item.logical_value
        for item in activities
        if item.certificate_kind == "exact_anf_zdd"
        or item.one_witness_sample is not None
    )
    unwitnessed = tuple(
        logical for logical in possible if logical not in set(witnessed)
    )
    guaranteed = tuple(
        item.logical_value for item in activities if item.is_always_active
    )
    branch_dependent = tuple(
        item.logical_value for item in activities if item.is_branch_dependent
    )
    variables = {
        variable for item in activities for variable in item.variables
    }
    exact_function = all(
        item.certificate_kind == "exact_anf_zdd" for item in activities
    )
    return PpmSupportProfile(
        operation_id=operation_id,
        source_gate_id=source_gate_id,
        injection_event_id=injection_event_id,
        source_algorithmic_layer=source_algorithmic_layer,
        injection_layer=injection_layer,
        axis=axis,
        activities=activities,
        possible_logical_support=possible,
        witnessed_logical_support=witnessed,
        unwitnessed_may_logical_support=unwitnessed,
        guaranteed_logical_support=guaranteed,
        branch_dependent_logical_support=branch_dependent,
        branch_variable_count=len(variables),
        minimum_weight_lower_bound=len(guaranteed),
        maximum_weight_upper_bound=len(possible),
        weight_bounds_exact=exact_function and not branch_dependent,
        outcome_independent_support=exact_function and not branch_dependent,
        possible_support_exact=possible_support_exact,
        possible_support_sha256=_digest(possible),
        activity_anf_sha256=_digest(_activity_rows(activities)),
        evidence_status=EvidenceStatus.PROVED,
    )


def _batch(
    profiles: tuple[PpmSupportProfile, ...],
    *,
    batch_level: int,
) -> PpmSupportBatch:
    if not profiles:
        raise DirectCczPpmSupportCertificateError("support batch cannot be empty")
    contact_counts = Counter(
        logical
        for profile in profiles
        for logical in profile.possible_logical_support
    )
    witnessed_contact_counts = Counter(
        logical
        for profile in profiles
        for logical in profile.witnessed_logical_support
    )
    maximum_contact = max(contact_counts.values())
    maximum_contact_values = tuple(
        logical
        for logical, count in sorted(contact_counts.items())
        if count == maximum_contact
    )
    operation_ids = tuple(profile.operation_id for profile in profiles)
    possible_union = tuple(sorted(contact_counts))
    witnessed_union = tuple(sorted(witnessed_contact_counts))
    guaranteed_union = tuple(
        sorted(
            {
                logical
                for profile in profiles
                for logical in profile.guaranteed_logical_support
            }
        )
    )
    return PpmSupportBatch(
        batch_level=batch_level,
        source_algorithmic_layer=profiles[0].source_algorithmic_layer,
        injection_layer=profiles[0].injection_layer,
        ppm_count=len(profiles),
        operation_ids=operation_ids,
        operation_id_sha256=_digest(operation_ids),
        possible_support_union=possible_union,
        possible_support_union_sha256=_digest(possible_union),
        witnessed_support_union=witnessed_union,
        guaranteed_support_union=guaranteed_union,
        branch_dependent_profile_count=sum(
            bool(profile.branch_dependent_logical_support) for profile in profiles
        ),
        maximum_ppm_weight_upper_bound=max(
            profile.maximum_weight_upper_bound for profile in profiles
        ),
        maximum_witnessed_support_union_size=max(
            len(profile.witnessed_logical_support) for profile in profiles
        ),
        total_possible_support_incidence=sum(
            profile.maximum_weight_upper_bound for profile in profiles
        ),
        total_witnessed_support_incidence=sum(
            len(profile.witnessed_logical_support) for profile in profiles
        ),
        maximum_possible_contact_count=maximum_contact,
        maximum_possible_contact_logical_values=maximum_contact_values,
        possible_contact_counts=tuple(sorted(contact_counts.items())),
        maximum_witnessed_contact_count=max(witnessed_contact_counts.values()),
        exact_hyperedge_count=len(profiles),
        pair_records_materialized=False,
        coordinate=SUPPORT_COORDINATE,
        evidence_status=(
            EvidenceStatus.PROVED
            if all(profile.possible_support_exact for profile in profiles)
            else EvidenceStatus.CHECK
        ),
    )


def _restrict_polynomial(
    monomials: tuple[tuple[str, ...], ...],
    variable: str,
    bit: int,
) -> tuple[tuple[str, ...], ...]:
    retained: list[tuple[str, ...]] = []
    for monomial in monomials:
        if variable not in monomial:
            retained.append(monomial)
        elif bit == 1:
            retained.append(tuple(item for item in monomial if item != variable))
    return BooleanPolynomial.from_monomials(retained).monomials


def _find_value_assignment(
    monomials: tuple[tuple[str, ...], ...],
    target: int,
) -> tuple[tuple[str, int], ...]:
    variables = tuple(
        sorted({variable for monomial in monomials for variable in monomial})
    )

    def search(
        current: tuple[tuple[str, ...], ...],
        remaining: tuple[str, ...],
    ) -> dict[str, int] | None:
        if not remaining:
            value = 1 if current == ((),) else 0
            return {} if value == target else None
        variable = remaining[0]
        rest = remaining[1:]
        for bit in (0, 1):
            restricted = _restrict_polynomial(current, variable, bit)
            result = search(restricted, rest)
            if result is not None:
                return {variable: bit, **result}
        return None

    result = search(monomials, variables)
    if result is None:
        raise DirectCczPpmSupportCertificateError(
            f"Boolean support component cannot attain requested value {target}"
        )
    return tuple(sorted(result.items()))


def _first_branch_witness(
    profiles: tuple[PpmSupportProfile, ...],
) -> SupportBranchDependenceWitness | None:
    for profile in profiles:
        for activity in profile.activities:
            if not activity.is_branch_dependent:
                continue
            if activity.anf_monomials is None:
                raise DirectCczPpmSupportCertificateError(
                    "first branch-dependence witness exceeds materialization limit"
                )
            return SupportBranchDependenceWitness(
                operation_id=profile.operation_id,
                source_gate_id=profile.source_gate_id,
                source_algorithmic_layer=profile.source_algorithmic_layer,
                logical_value=activity.logical_value,
                certificate_kind="exact_anf",
                anf_monomials=activity.anf_monomials,
                zero_assignment=_find_value_assignment(activity.anf_monomials, 0),
                one_assignment=_find_value_assignment(activity.anf_monomials, 1),
                zero_sample_index=None,
                one_sample_index=None,
                sample_seed=None,
                evidence_status=EvidenceStatus.FALSIFIED,
            )
    return None


def _invalid_certificate(
    trace: QclaTrace | OopQclaTrace,
    event_trace: DirectCczEventTrace,
    *,
    variant: QclaVariant,
    counterexample: SupportValidationCounterexample,
) -> QclaPpmSupportCertificate:
    return QclaPpmSupportCertificate(
        variant=variant,
        width=trace.width,
        source_trace_id=trace.trace_id,
        event_trace_id=event_trace.trace_id,
        support_model=SUPPORT_MODEL,
        profiles=(),
        batches=(),
        source_logical_value_count=len(
            {
                logical
                for gate in trace.gates
                for logical in gate.logical_support
            }
        ),
        direct_ccz_event_count=len(event_trace.injection_events),
        ppm_count=sum(len(event.ppms) for event in event_trace.injection_events),
        nonclifford_source_layer_count=len(
            {
                gate.algorithmic_layer
                for gate in trace.gates
                if gate.kind is QclaGateKind.TOFFOLI
            }
        ),
        candidate_batch_level_count=None,
        exact_activity_monomial_count=0,
        branch_dependent_profile_count=0,
        maximum_ppm_weight_upper_bound=None,
        maximum_witnessed_support_union_size=None,
        maximum_sampled_branch_weight=None,
        maximum_batch_possible_contact_count=None,
        maximum_batch_witnessed_contact_count=None,
        all_possible_supports_exact=False,
        support_envelope_evidence_status=EvidenceStatus.FALSIFIED,
        outcome_independent_support_evidence_status=EvidenceStatus.OPEN,
        branch_dependence_witness=None,
        validation_counterexample=counterexample,
        deterministic_branch_sample_count=0,
        deterministic_branch_sample_seed=None,
        records_checked=0,
        asymptotic_certificate_size=(
            "output-sensitive sparse Boolean matrix plus emitted support incidences; "
            "no global PPM-pair table"
        ),
    )


_BRANCH_SAMPLE_COUNT = 512
_BRANCH_SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"


def _sample_mask(variable: str, *, count: int, seed: str) -> int:
    byte_count = (count + 7) // 8
    raw = int.from_bytes(
        hashlib.shake_256(f"{seed}|{variable}".encode()).digest(byte_count),
        "little",
    )
    all_mask = (1 << count) - 1
    raw &= all_mask
    raw &= ~1
    raw |= 1 << 1
    return raw


def _sample_digest(mask: int, *, count: int) -> str:
    return hashlib.sha256(mask.to_bytes((count + 7) // 8, "little")).hexdigest().upper()


def _least_set_bit(mask: int) -> int | None:
    return None if mask == 0 else (mask & -mask).bit_length() - 1


def _maximum_parallel_mask_weight(masks: tuple[int, ...], *, count: int) -> int:
    """Return the largest simultaneous support weight across packed samples."""

    planes: list[int] = []
    for mask in masks:
        carry = mask
        plane = 0
        while carry:
            if plane == len(planes):
                planes.append(0)
            next_carry = planes[plane] & carry
            planes[plane] ^= carry
            carry = next_carry
            plane += 1
    maximum = 0
    for sample in range(count):
        weight = sum(
            ((plane >> sample) & 1) << index
            for index, plane in enumerate(planes)
        )
        maximum = max(maximum, weight)
    return maximum


def _constant_activity(logical_value: str) -> SupportActivity:
    return SupportActivity(
        logical_value=logical_value,
        certificate_kind="exact_anf_zdd",
        anf_zdd_sha256=_digest(["ONE"]),
        anf_zdd_node_count=1,
        anf_monomial_count=1,
        variables=(),
        constant_term=True,
        is_always_active=True,
        is_branch_dependent=False,
        anf_monomials=((),),
        sample_evaluation_sha256=None,
        one_witness_sample=None,
        zero_witness_sample=None,
    )


def _sampled_activity(
    logical_value: str,
    mask: int,
    *,
    all_mask: int,
    possible_witnessed: bool,
    count: int,
) -> SupportActivity:
    one_sample = _least_set_bit(mask)
    zero_sample = _least_set_bit(all_mask ^ mask)
    return SupportActivity(
        logical_value=logical_value,
        certificate_kind=(
            "saturated_may_envelope"
            if possible_witnessed
            else "unwitnessed_may_envelope"
        ),
        anf_zdd_sha256=None,
        anf_zdd_node_count=None,
        anf_monomial_count=None,
        variables=(),
        constant_term=None,
        is_always_active=False,
        is_branch_dependent=one_sample is not None and zero_sample is not None,
        anf_monomials=None,
        sample_evaluation_sha256=_sample_digest(mask, count=count),
        one_witness_sample=one_sample,
        zero_witness_sample=zero_sample,
    )


def _sampled_source_cnot_conjugate(
    sampled: dict[str, dict[str, int]],
    may: dict[str, set[str]],
    control: str,
    target: str,
) -> None:
    target_sampled = sampled[target]
    for logical, mask in tuple(sampled[control].items()):
        updated = target_sampled.get(logical, 0) ^ mask
        if updated == 0:
            target_sampled.pop(logical, None)
        else:
            target_sampled[logical] = updated
    may[target].update(may[control])

    for sampled_column in sampled.values():
        target_mask = sampled_column.get(target, 0)
        updated = sampled_column.get(control, 0) ^ target_mask
        if updated == 0:
            sampled_column.pop(control, None)
        else:
            sampled_column[control] = updated
    for may_column in may.values():
        if target in may_column:
            may_column.add(control)


def _sampled_conditional_column_xor(
    sampled: dict[str, dict[str, int]],
    may: dict[str, set[str]],
    target: str,
    source: str,
    condition_mask: int,
) -> None:
    target_column = sampled[target]
    for logical, source_mask in tuple(sampled[source].items()):
        updated = target_column.get(logical, 0) ^ (source_mask & condition_mask)
        if updated == 0:
            target_column.pop(logical, None)
        else:
            target_column[logical] = updated
    may[target].update(may[source])


def _first_sampled_branch_witness(
    profiles: tuple[PpmSupportProfile, ...],
) -> SupportBranchDependenceWitness | None:
    for profile in profiles:
        for activity in profile.activities:
            if not activity.is_branch_dependent:
                continue
            return SupportBranchDependenceWitness(
                operation_id=profile.operation_id,
                source_gate_id=profile.source_gate_id,
                source_algorithmic_layer=profile.source_algorithmic_layer,
                logical_value=activity.logical_value,
                certificate_kind="sampled_branches",
                anf_monomials=None,
                zero_assignment=None,
                one_assignment=None,
                zero_sample_index=activity.zero_witness_sample,
                one_sample_index=activity.one_witness_sample,
                sample_seed=_BRANCH_SAMPLE_SEED,
                evidence_status=EvidenceStatus.FALSIFIED,
            )
    return None


def _certify_sampled_support_envelope(
    trace: QclaTrace | OopQclaTrace,
    event_trace: DirectCczEventTrace,
    *,
    variant: QclaVariant,
) -> QclaPpmSupportCertificate:
    compatibility = certify_qcla_direct_ccz_ppm_compatibility(
        trace,
        event_trace,
        variant=variant,
    )
    if not compatibility.compatibility_proved:
        compatibility_witness = compatibility.counterexample
        if compatibility_witness is None:  # pragma: no cover - compatibility invariant
            raise DirectCczPpmSupportCertificateError(
                "falsified compatibility certificate has no witness"
            )
        return _invalid_certificate(
            trace,
            event_trace,
            variant=variant,
            counterexample=SupportValidationCounterexample(
                obligation=compatibility_witness.obligation,
                source_algorithmic_layer=compatibility_witness.source_algorithmic_layer,
                source_gate_id=compatibility_witness.source_gate_id,
                event_id=compatibility_witness.event_id,
                detail=compatibility_witness.detail,
            ),
        )

    sample_count = _BRANCH_SAMPLE_COUNT
    all_mask = (1 << sample_count) - 1
    logical_values = tuple(
        sorted(
            {
                logical
                for gate in trace.gates
                for logical in gate.logical_support
            }
        )
    )
    sampled = {logical: {logical: all_mask} for logical in logical_values}
    may = {logical: {logical} for logical in logical_values}
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    profiles: list[PpmSupportProfile] = []
    maximum_sampled_branch_weight = 1

    for gate in trace.gates:
        if gate.kind is QclaGateKind.X:
            continue
        if gate.kind is QclaGateKind.CNOT:
            _sampled_source_cnot_conjugate(
                sampled,
                may,
                gate.controls[0],
                gate.target,
            )
            continue
        if gate.kind is not QclaGateKind.TOFFOLI:
            return _invalid_certificate(
                trace,
                event_trace,
                variant=variant,
                counterexample=SupportValidationCounterexample(
                    obligation="support_preserving_source_gate_set",
                    source_algorithmic_layer=gate.algorithmic_layer,
                    source_gate_id=gate.gate_id,
                    event_id=None,
                    detail="support propagation only admits source X/CNOT/Toffoli",
                ),
            )

        event = event_by_source[gate.gate_id]
        if event.correction_frame != _expected_corrections(event):
            return _invalid_certificate(
                trace,
                event_trace,
                variant=variant,
                counterexample=SupportValidationCounterexample(
                    obligation="canonical_support_changing_correction_map",
                    source_algorithmic_layer=gate.algorithmic_layer,
                    source_gate_id=gate.gate_id,
                    event_id=event.event_id,
                    detail=(
                        "correction map does not equal the reviewed two conditional-"
                        "CNOT support updates plus support-preserving corrections"
                    ),
                ),
            )

        for index, ppm in enumerate(event.ppms):
            if ppm.layer == 1:
                data_logical = event.data[index]
                possible_upper = tuple(
                    sorted({event.resource[index], *may[data_logical]})
                )
                masks = dict(sampled[data_logical])
                masks[event.resource[index]] = all_mask
                witnessed_size = sum(mask != 0 for mask in masks.values())
                if witnessed_size > maximum_sampled_branch_weight:
                    maximum_sampled_branch_weight = max(
                        maximum_sampled_branch_weight,
                        _maximum_parallel_mask_weight(
                            tuple(mask for mask in masks.values() if mask),
                            count=sample_count,
                        ),
                    )
                possible_exact = all(masks.get(logical, 0) != 0 for logical in possible_upper)
                activities = tuple(
                    _constant_activity(logical)
                    if logical == event.resource[index]
                    else _sampled_activity(
                        logical,
                        masks.get(logical, 0),
                        all_mask=all_mask,
                        possible_witnessed=masks.get(logical, 0) != 0,
                        count=sample_count,
                    )
                    for logical in possible_upper
                )
                axis: Axis = "Z"
            else:
                resource_index = index - 3
                activities = (_constant_activity(event.resource[resource_index]),)
                possible_exact = True
                axis = "X"
            profiles.append(
                _profile(
                    operation_id=ppm.event_id,
                    source_gate_id=gate.gate_id,
                    injection_event_id=event.event_id,
                    source_algorithmic_layer=gate.algorithmic_layer,
                    injection_layer=ppm.layer,
                    axis=axis,
                    activities=activities,
                    possible_support_exact=possible_exact,
                )
            )

        _sampled_conditional_column_xor(
            sampled,
            may,
            event.data[2],
            event.data[1],
            _sample_mask(
                event.ppms[0].outcome_token,
                count=sample_count,
                seed=_BRANCH_SAMPLE_SEED,
            ),
        )
        _sampled_conditional_column_xor(
            sampled,
            may,
            event.data[2],
            event.data[0],
            _sample_mask(
                event.ppms[1].outcome_token,
                count=sample_count,
                seed=_BRANCH_SAMPLE_SEED,
            ),
        )

    grouped: dict[tuple[int, int], list[PpmSupportProfile]] = {}
    for profile in profiles:
        grouped.setdefault(
            (profile.source_algorithmic_layer, profile.injection_layer), []
        ).append(profile)
    batches = tuple(
        _batch(tuple(items), batch_level=index)
        for index, (_, items) in enumerate(sorted(grouped.items()), start=1)
    )
    profile_tuple = tuple(profiles)
    branch_witness = _first_sampled_branch_witness(profile_tuple)
    all_exact = all(profile.possible_support_exact for profile in profile_tuple)
    branch_dependent_count = sum(
        bool(profile.branch_dependent_logical_support) for profile in profile_tuple
    )
    return QclaPpmSupportCertificate(
        variant=variant,
        width=trace.width,
        source_trace_id=trace.trace_id,
        event_trace_id=event_trace.trace_id,
        support_model="sound-may-envelope-with-concrete-branch-witnesses-v1",
        profiles=profile_tuple,
        batches=batches,
        source_logical_value_count=len(logical_values),
        direct_ccz_event_count=len(event_trace.injection_events),
        ppm_count=len(profile_tuple),
        nonclifford_source_layer_count=len(batches) // 2,
        candidate_batch_level_count=len(batches),
        exact_activity_monomial_count=None,
        branch_dependent_profile_count=branch_dependent_count,
        maximum_ppm_weight_upper_bound=max(
            profile.maximum_weight_upper_bound for profile in profile_tuple
        ),
        maximum_witnessed_support_union_size=max(
            len(profile.witnessed_logical_support) for profile in profile_tuple
        ),
        maximum_sampled_branch_weight=maximum_sampled_branch_weight,
        maximum_batch_possible_contact_count=max(
            batch.maximum_possible_contact_count for batch in batches
        ),
        maximum_batch_witnessed_contact_count=max(
            batch.maximum_witnessed_contact_count for batch in batches
        ),
        all_possible_supports_exact=all_exact,
        support_envelope_evidence_status=(
            EvidenceStatus.PROVED if all_exact else EvidenceStatus.CHECK
        ),
        outcome_independent_support_evidence_status=(
            EvidenceStatus.FALSIFIED
            if branch_witness is not None
            else EvidenceStatus.INCONCLUSIVE
        ),
        branch_dependence_witness=branch_witness,
        validation_counterexample=None,
        deterministic_branch_sample_count=sample_count,
        deterministic_branch_sample_seed=_BRANCH_SAMPLE_SEED,
        records_checked=(
            len(trace.gates)
            + len(trace.dependencies)
            + len(event_trace.injection_events)
            + len(profile_tuple)
            + sum(len(profile.activities) for profile in profile_tuple)
        ),
        asymptotic_certificate_size=(
            "output-sensitive may-support matrix plus 512 parallel concrete branch "
            "witnesses and emitted support incidences; no global PPM-pair table"
        ),
    )


def certify_qcla_direct_ccz_ppm_support(
    trace: QclaTrace | OopQclaTrace,
    event_trace: DirectCczEventTrace,
    *,
    variant: QclaVariant,
) -> QclaPpmSupportCertificate:
    """Return exact or sound-bounded logical-support hypergraphs."""

    if variant == "ip" and trace.width > 8:
        return _certify_sampled_support_envelope(
            trace,
            event_trace,
            variant=variant,
        )

    compatibility = certify_qcla_direct_ccz_ppm_compatibility(
        trace,
        event_trace,
        variant=variant,
    )
    if not compatibility.compatibility_proved:
        compatibility_witness = compatibility.counterexample
        if compatibility_witness is None:  # pragma: no cover - compatibility invariant
            raise DirectCczPpmSupportCertificateError(
                "falsified compatibility certificate has no witness"
            )
        return _invalid_certificate(
            trace,
            event_trace,
            variant=variant,
            counterexample=SupportValidationCounterexample(
                obligation=compatibility_witness.obligation,
                source_algorithmic_layer=compatibility_witness.source_algorithmic_layer,
                source_gate_id=compatibility_witness.source_gate_id,
                event_id=compatibility_witness.event_id,
                detail=compatibility_witness.detail,
            ),
        )

    logical_values = tuple(
        sorted(
            {
                logical
                for gate in trace.gates
                for logical in gate.logical_support
            }
        )
    )
    arena = _AnfZddArena()
    columns: SupportMatrix = {
        logical: {logical: arena.ONE} for logical in logical_values
    }
    event_by_source = {
        event.source_gate_id: event for event in event_trace.injection_events
    }
    profiles: list[PpmSupportProfile] = []

    for gate in trace.gates:
        if gate.kind is QclaGateKind.X:
            continue
        if gate.kind is QclaGateKind.CNOT:
            _source_cnot_conjugate(
                arena,
                columns,
                gate.controls[0],
                gate.target,
            )
            continue
        if gate.kind is not QclaGateKind.TOFFOLI:
            return _invalid_certificate(
                trace,
                event_trace,
                variant=variant,
                counterexample=SupportValidationCounterexample(
                    obligation="support_preserving_source_gate_set",
                    source_algorithmic_layer=gate.algorithmic_layer,
                    source_gate_id=gate.gate_id,
                    event_id=None,
                    detail="support propagation only admits source X/CNOT/Toffoli",
                ),
            )

        event = event_by_source[gate.gate_id]
        expected_corrections = _expected_corrections(event)
        if event.correction_frame != expected_corrections:
            return _invalid_certificate(
                trace,
                event_trace,
                variant=variant,
                counterexample=SupportValidationCounterexample(
                    obligation="canonical_support_changing_correction_map",
                    source_algorithmic_layer=gate.algorithmic_layer,
                    source_gate_id=gate.gate_id,
                    event_id=event.event_id,
                    detail=(
                        "correction map does not equal the reviewed two conditional-"
                        "CNOT support updates plus support-preserving corrections"
                    ),
                ),
            )

        for index, ppm in enumerate(event.ppms):
            if ppm.layer == 1:
                data_logical = event.data[index]
                activities = _activities_from_column(
                    arena,
                    columns[data_logical],
                    extra_constant=event.resource[index],
                )
                axis: Axis = "Z"
            else:
                resource_index = index - 3
                activities = (
                    _activity_from_root(
                        arena,
                        event.resource[resource_index],
                        arena.ONE,
                    ),
                )
                axis = "X"
            profiles.append(
                _profile(
                    operation_id=ppm.event_id,
                    source_gate_id=gate.gate_id,
                    injection_event_id=event.event_id,
                    source_algorithmic_layer=gate.algorithmic_layer,
                    injection_layer=ppm.layer,
                    axis=axis,
                    activities=activities,
                )
            )

        c1, c2, target = event.data
        _column_xor(
            arena,
            columns,
            target,
            c2,
            condition_variable=event.ppms[0].outcome_token,
        )
        _column_xor(
            arena,
            columns,
            target,
            c1,
            condition_variable=event.ppms[1].outcome_token,
        )

    grouped: dict[tuple[int, int], list[PpmSupportProfile]] = {}
    for profile in profiles:
        grouped.setdefault(
            (profile.source_algorithmic_layer, profile.injection_layer), []
        ).append(profile)
    batches = tuple(
        _batch(tuple(items), batch_level=index)
        for index, (_, items) in enumerate(sorted(grouped.items()), start=1)
    )
    profile_tuple = tuple(profiles)
    branch_witness = _first_branch_witness(profile_tuple)
    branch_dependent_count = sum(
        bool(profile.branch_dependent_logical_support) for profile in profile_tuple
    )
    return QclaPpmSupportCertificate(
        variant=variant,
        width=trace.width,
        source_trace_id=trace.trace_id,
        event_trace_id=event_trace.trace_id,
        support_model=SUPPORT_MODEL,
        profiles=profile_tuple,
        batches=batches,
        source_logical_value_count=len(logical_values),
        direct_ccz_event_count=len(event_trace.injection_events),
        ppm_count=len(profile_tuple),
        nonclifford_source_layer_count=len(batches) // 2,
        candidate_batch_level_count=len(batches),
        exact_activity_monomial_count=sum(
            activity.anf_monomial_count or 0
            for profile in profile_tuple
            for activity in profile.activities
        ),
        branch_dependent_profile_count=branch_dependent_count,
        maximum_ppm_weight_upper_bound=max(
            profile.maximum_weight_upper_bound for profile in profile_tuple
        ),
        maximum_witnessed_support_union_size=max(
            len(profile.witnessed_logical_support) for profile in profile_tuple
        ),
        maximum_sampled_branch_weight=None,
        maximum_batch_possible_contact_count=max(
            batch.maximum_possible_contact_count for batch in batches
        ),
        maximum_batch_witnessed_contact_count=max(
            batch.maximum_witnessed_contact_count for batch in batches
        ),
        all_possible_supports_exact=True,
        support_envelope_evidence_status=EvidenceStatus.PROVED,
        outcome_independent_support_evidence_status=(
            EvidenceStatus.PROVED
            if branch_witness is None
            else EvidenceStatus.FALSIFIED
        ),
        branch_dependence_witness=branch_witness,
        validation_counterexample=None,
        deterministic_branch_sample_count=0,
        deterministic_branch_sample_seed=None,
        records_checked=(
            len(trace.gates)
            + len(trace.dependencies)
            + len(event_trace.injection_events)
            + len(profile_tuple)
            + sum(len(profile.activities) for profile in profile_tuple)
        ),
        asymptotic_certificate_size=(
            "output-sensitive sparse Boolean matrix plus emitted support incidences; "
            "no global PPM-pair table"
        ),
    )


def compare_support_certificate_to_symbolic_trace(
    certificate: QclaPpmSupportCertificate,
    symbolic_trace: SymbolicDirectCczPpmTrace,
) -> ExactSupportEquivalence:
    """Compare compact propagation with a fully materialized symbolic trace."""

    if certificate.support_envelope_evidence_status is not EvidenceStatus.PROVED:
        raise DirectCczPpmSupportCertificateError(
            "only a proved support certificate can be compared"
        )
    symbolic_by_id = {ppm.operation_id: ppm for ppm in symbolic_trace.ppms}
    component_match = True
    possible_match = True
    guaranteed_match = True
    branch_match = True
    for profile in certificate.profiles:
        symbolic = symbolic_by_id.get(profile.operation_id)
        if symbolic is None:
            component_match = False
            possible_match = False
            guaranteed_match = False
            branch_match = False
            continue
        raw_components = (
            symbolic.presented_observable.z_components
            if profile.axis == "Z"
            else symbolic.presented_observable.x_components
        )
        expected_rows = tuple(
            (logical, polynomial.monomials)
            for logical, polynomial in raw_components
        )
        actual_rows = tuple(
            (activity.logical_value, activity.anf_monomials)
            for activity in profile.activities
        )
        component_match &= actual_rows == expected_rows
        possible_match &= profile.possible_logical_support == tuple(
            logical for logical, _ in expected_rows
        )
        guaranteed_match &= profile.guaranteed_logical_support == tuple(
            logical
            for logical, monomials in expected_rows
            if monomials == ((),)
        )
        branch_match &= profile.branch_dependent_logical_support == tuple(
            logical
            for logical, monomials in expected_rows
            if monomials != ((),)
        )

    expected_witness: SupportBranchDependenceWitness | None = None
    for ppm in symbolic_trace.ppms:
        components = (
            ppm.presented_observable.z_components
            if ppm.injection_layer == 1
            else ppm.presented_observable.x_components
        )
        branch_component = next(
            (
                (logical, polynomial)
                for logical, polynomial in components
                if polynomial.monomials != ((),)
            ),
            None,
        )
        if branch_component is None:
            continue
        logical, polynomial = branch_component
        expected_witness = SupportBranchDependenceWitness(
            operation_id=ppm.operation_id,
            source_gate_id=ppm.source_gate_id,
            source_algorithmic_layer=ppm.source_algorithmic_layer,
            logical_value=logical,
            certificate_kind="exact_anf",
            anf_monomials=polynomial.monomials,
            zero_assignment=_find_value_assignment(polynomial.monomials, 0),
            one_assignment=_find_value_assignment(polynomial.monomials, 1),
            zero_sample_index=None,
            one_sample_index=None,
            sample_seed=None,
            evidence_status=EvidenceStatus.FALSIFIED,
        )
        break
    witness_match = certificate.branch_dependence_witness == expected_witness
    all_passed = all(
        (
            len(certificate.profiles) == len(symbolic_trace.ppms),
            component_match,
            possible_match,
            guaranteed_match,
            branch_match,
            witness_match,
        )
    )
    return ExactSupportEquivalence(
        variant=certificate.variant,
        width=certificate.width,
        ppm_count=len(certificate.profiles),
        component_activity_match=component_match,
        possible_support_match=possible_match,
        guaranteed_support_match=guaranteed_match,
        branch_dependence_match=branch_match,
        first_witness_match=witness_match,
        all_checks_passed=all_passed,
        evidence_status=(
            EvidenceStatus.NUMERICAL if all_passed else EvidenceStatus.FALSIFIED
        ),
    )


def support_activity_to_data(activity: SupportActivity) -> dict[str, Any]:
    """Serialize one support activity."""

    return {
        "anf_monomial_count": activity.anf_monomial_count,
        "anf_monomials": (
            None
            if activity.anf_monomials is None
            else [list(item) for item in activity.anf_monomials]
        ),
        "anf_zdd_node_count": activity.anf_zdd_node_count,
        "anf_zdd_sha256": activity.anf_zdd_sha256,
        "certificate_kind": activity.certificate_kind,
        "constant_term": activity.constant_term,
        "is_always_active": activity.is_always_active,
        "is_branch_dependent": activity.is_branch_dependent,
        "logical_value": activity.logical_value,
        "one_witness_sample": activity.one_witness_sample,
        "sample_evaluation_sha256": activity.sample_evaluation_sha256,
        "variables": list(activity.variables),
        "zero_witness_sample": activity.zero_witness_sample,
    }


def ppm_support_profile_to_data(profile: PpmSupportProfile) -> dict[str, Any]:
    """Serialize one PPM support profile."""

    return {
        "activities": [support_activity_to_data(item) for item in profile.activities],
        "activity_anf_sha256": profile.activity_anf_sha256,
        "axis": profile.axis,
        "branch_dependent_logical_support": list(
            profile.branch_dependent_logical_support
        ),
        "branch_variable_count": profile.branch_variable_count,
        "evidence_status": profile.evidence_status.value,
        "guaranteed_logical_support": list(profile.guaranteed_logical_support),
        "injection_event_id": profile.injection_event_id,
        "injection_layer": profile.injection_layer,
        "maximum_weight_upper_bound": profile.maximum_weight_upper_bound,
        "minimum_weight_lower_bound": profile.minimum_weight_lower_bound,
        "operation_id": profile.operation_id,
        "outcome_independent_support": profile.outcome_independent_support,
        "possible_support_exact": profile.possible_support_exact,
        "possible_logical_support": list(profile.possible_logical_support),
        "possible_support_sha256": profile.possible_support_sha256,
        "source_algorithmic_layer": profile.source_algorithmic_layer,
        "source_gate_id": profile.source_gate_id,
        "weight_bounds_exact": profile.weight_bounds_exact,
        "witnessed_logical_support": list(profile.witnessed_logical_support),
        "unwitnessed_may_logical_support": list(
            profile.unwitnessed_may_logical_support
        ),
    }


def ppm_support_batch_to_data(batch: PpmSupportBatch) -> dict[str, Any]:
    """Serialize one support-hypergraph batch."""

    return {
        "batch_level": batch.batch_level,
        "branch_dependent_profile_count": batch.branch_dependent_profile_count,
        "coordinate": batch.coordinate,
        "evidence_status": batch.evidence_status.value,
        "exact_hyperedge_count": batch.exact_hyperedge_count,
        "guaranteed_support_union": list(batch.guaranteed_support_union),
        "injection_layer": batch.injection_layer,
        "maximum_possible_contact_count": batch.maximum_possible_contact_count,
        "maximum_possible_contact_logical_values": list(
            batch.maximum_possible_contact_logical_values
        ),
        "maximum_ppm_weight_upper_bound": batch.maximum_ppm_weight_upper_bound,
        "maximum_witnessed_contact_count": batch.maximum_witnessed_contact_count,
        "maximum_witnessed_support_union_size": (
            batch.maximum_witnessed_support_union_size
        ),
        "operation_id_sha256": batch.operation_id_sha256,
        "operation_ids": list(batch.operation_ids),
        "pair_records_materialized": batch.pair_records_materialized,
        "possible_contact_counts": [
            {"contact_count": count, "logical_value": logical}
            for logical, count in batch.possible_contact_counts
        ],
        "possible_support_union": list(batch.possible_support_union),
        "possible_support_union_sha256": batch.possible_support_union_sha256,
        "ppm_count": batch.ppm_count,
        "source_algorithmic_layer": batch.source_algorithmic_layer,
        "total_possible_support_incidence": batch.total_possible_support_incidence,
        "total_witnessed_support_incidence": (
            batch.total_witnessed_support_incidence
        ),
        "witnessed_support_union": list(batch.witnessed_support_union),
    }


def _branch_witness_to_data(
    witness: SupportBranchDependenceWitness | None,
) -> dict[str, Any] | None:
    if witness is None:
        return None
    return {
        "anf_monomials": (
            None
            if witness.anf_monomials is None
            else [list(item) for item in witness.anf_monomials]
        ),
        "certificate_kind": witness.certificate_kind,
        "evidence_status": witness.evidence_status.value,
        "logical_value": witness.logical_value,
        "one_assignment": (
            None
            if witness.one_assignment is None
            else dict(witness.one_assignment)
        ),
        "one_sample_index": witness.one_sample_index,
        "operation_id": witness.operation_id,
        "sample_seed": witness.sample_seed,
        "source_algorithmic_layer": witness.source_algorithmic_layer,
        "source_gate_id": witness.source_gate_id,
        "zero_assignment": (
            None
            if witness.zero_assignment is None
            else dict(witness.zero_assignment)
        ),
        "zero_sample_index": witness.zero_sample_index,
    }


def qcla_ppm_support_certificate_to_data(
    certificate: QclaPpmSupportCertificate,
) -> dict[str, Any]:
    """Serialize one scalable support certificate."""

    counterexample = certificate.validation_counterexample
    return {
        "all_possible_supports_exact": certificate.all_possible_supports_exact,
        "asymptotic_certificate_size": certificate.asymptotic_certificate_size,
        "batches": [ppm_support_batch_to_data(item) for item in certificate.batches],
        "branch_dependence_witness": _branch_witness_to_data(
            certificate.branch_dependence_witness
        ),
        "branch_dependent_profile_count": certificate.branch_dependent_profile_count,
        "candidate_batch_level_count": certificate.candidate_batch_level_count,
        "complete_native_schedule": certificate.complete_native_schedule,
        "direct_ccz_event_count": certificate.direct_ccz_event_count,
        "deterministic_branch_sample_count": (
            certificate.deterministic_branch_sample_count
        ),
        "deterministic_branch_sample_seed": (
            certificate.deterministic_branch_sample_seed
        ),
        "event_trace_id": certificate.event_trace_id,
        "exact_activity_monomial_count": certificate.exact_activity_monomial_count,
        "failure_probability": certificate.failure_probability,
        "maximum_batch_possible_contact_count": (
            certificate.maximum_batch_possible_contact_count
        ),
        "maximum_batch_witnessed_contact_count": (
            certificate.maximum_batch_witnessed_contact_count
        ),
        "maximum_ppm_weight_upper_bound": (
            certificate.maximum_ppm_weight_upper_bound
        ),
        "maximum_sampled_branch_weight": (
            certificate.maximum_sampled_branch_weight
        ),
        "maximum_witnessed_support_union_size": (
            certificate.maximum_witnessed_support_union_size
        ),
        "nonclifford_source_layer_count": (
            certificate.nonclifford_source_layer_count
        ),
        "outcome_independent_support_evidence_status": (
            certificate.outcome_independent_support_evidence_status.value
        ),
        "physical_qubits": certificate.physical_qubits,
        "ppm_count": certificate.ppm_count,
        "profiles": [ppm_support_profile_to_data(item) for item in certificate.profiles],
        "records_checked": certificate.records_checked,
        "runtime_seconds": certificate.runtime_seconds,
        "schema": certificate.schema,
        "schema_version": certificate.schema_version,
        "source_logical_value_count": certificate.source_logical_value_count,
        "source_trace_id": certificate.source_trace_id,
        "support_envelope_evidence_status": (
            certificate.support_envelope_evidence_status.value
        ),
        "support_model": certificate.support_model,
        "surgery_rounds": certificate.surgery_rounds,
        "validation_counterexample": (
            None
            if counterexample is None
            else {
                "detail": counterexample.detail,
                "event_id": counterexample.event_id,
                "obligation": counterexample.obligation,
                "source_algorithmic_layer": (
                    counterexample.source_algorithmic_layer
                ),
                "source_gate_id": counterexample.source_gate_id,
            }
        ),
        "variant": certificate.variant,
        "width": certificate.width,
    }


def qcla_ppm_support_certificate_summary_to_data(
    certificate: QclaPpmSupportCertificate,
) -> dict[str, Any]:
    """Serialize the replayable support hypergraph without bulky ANF payloads."""

    data = qcla_ppm_support_certificate_aggregate_to_data(certificate)
    data["batches"] = [
        ppm_support_batch_to_data(item) for item in certificate.batches
    ]
    data["profiles"] = [
        {
            "axis": profile.axis,
            "branch_dependent_logical_support": list(
                profile.branch_dependent_logical_support
            ),
            "evidence_status": profile.evidence_status.value,
            "guaranteed_logical_support": list(
                profile.guaranteed_logical_support
            ),
            "injection_layer": profile.injection_layer,
            "maximum_weight_upper_bound": profile.maximum_weight_upper_bound,
            "minimum_weight_lower_bound": profile.minimum_weight_lower_bound,
            "operation_id": profile.operation_id,
            "possible_logical_support": list(
                profile.possible_logical_support
            ),
            "possible_support_exact": profile.possible_support_exact,
            "possible_support_sha256": profile.possible_support_sha256,
            "source_algorithmic_layer": profile.source_algorithmic_layer,
            "source_gate_id": profile.source_gate_id,
            "unwitnessed_may_logical_support": list(
                profile.unwitnessed_may_logical_support
            ),
            "witnessed_logical_support": list(
                profile.witnessed_logical_support
            ),
        }
        for profile in certificate.profiles
    ]
    return data


def qcla_ppm_support_certificate_aggregate_to_data(
    certificate: QclaPpmSupportCertificate,
) -> dict[str, Any]:
    """Serialize sweep-level aggregate claims without support hyperedges."""

    counterexample = certificate.validation_counterexample
    return {
        "all_possible_supports_exact": certificate.all_possible_supports_exact,
        "asymptotic_certificate_size": certificate.asymptotic_certificate_size,
        "branch_dependence_witness": _branch_witness_to_data(
            certificate.branch_dependence_witness
        ),
        "branch_dependent_profile_count": (
            certificate.branch_dependent_profile_count
        ),
        "candidate_batch_level_count": certificate.candidate_batch_level_count,
        "complete_native_schedule": certificate.complete_native_schedule,
        "direct_ccz_event_count": certificate.direct_ccz_event_count,
        "deterministic_branch_sample_count": (
            certificate.deterministic_branch_sample_count
        ),
        "deterministic_branch_sample_seed": (
            certificate.deterministic_branch_sample_seed
        ),
        "event_trace_id": certificate.event_trace_id,
        "exact_activity_monomial_count": certificate.exact_activity_monomial_count,
        "failure_probability": certificate.failure_probability,
        "maximum_batch_possible_contact_count": (
            certificate.maximum_batch_possible_contact_count
        ),
        "maximum_batch_witnessed_contact_count": (
            certificate.maximum_batch_witnessed_contact_count
        ),
        "maximum_ppm_weight_upper_bound": (
            certificate.maximum_ppm_weight_upper_bound
        ),
        "maximum_sampled_branch_weight": (
            certificate.maximum_sampled_branch_weight
        ),
        "maximum_witnessed_support_union_size": (
            certificate.maximum_witnessed_support_union_size
        ),
        "nonclifford_source_layer_count": (
            certificate.nonclifford_source_layer_count
        ),
        "outcome_independent_support_evidence_status": (
            certificate.outcome_independent_support_evidence_status.value
        ),
        "physical_qubits": certificate.physical_qubits,
        "ppm_count": certificate.ppm_count,
        "records_checked": certificate.records_checked,
        "runtime_seconds": certificate.runtime_seconds,
        "schema": certificate.schema,
        "schema_version": certificate.schema_version,
        "source_logical_value_count": certificate.source_logical_value_count,
        "source_trace_id": certificate.source_trace_id,
        "support_envelope_evidence_status": (
            certificate.support_envelope_evidence_status.value
        ),
        "support_model": certificate.support_model,
        "surgery_rounds": certificate.surgery_rounds,
        "validation_counterexample": (
            None
            if counterexample is None
            else {
                "detail": counterexample.detail,
                "event_id": counterexample.event_id,
                "obligation": counterexample.obligation,
                "source_algorithmic_layer": (
                    counterexample.source_algorithmic_layer
                ),
                "source_gate_id": counterexample.source_gate_id,
            }
        ),
        "variant": certificate.variant,
        "width": certificate.width,
    }


def exact_support_equivalence_to_data(
    equivalence: ExactSupportEquivalence,
) -> dict[str, Any]:
    """Serialize one exact-anchor comparison."""

    return {
        "all_checks_passed": equivalence.all_checks_passed,
        "branch_dependence_match": equivalence.branch_dependence_match,
        "component_activity_match": equivalence.component_activity_match,
        "evidence_status": equivalence.evidence_status.value,
        "first_witness_match": equivalence.first_witness_match,
        "guaranteed_support_match": equivalence.guaranteed_support_match,
        "possible_support_match": equivalence.possible_support_match,
        "ppm_count": equivalence.ppm_count,
        "schema": equivalence.schema,
        "schema_version": equivalence.schema_version,
        "variant": equivalence.variant,
        "width": equivalence.width,
    }
