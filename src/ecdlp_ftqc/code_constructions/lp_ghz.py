"""Exact GF(2) audit of the completed-LP GHZ measurement interface.

Binary supports are column vectors packed into Python integers. A circulant
monomial x**t has row c, column c-t. X checks are d1 and Z checks are d2.T.
No fault-tolerant preparation or native runtime is admitted by this module.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

EXPONENTS = ((0, 71, 73, 68, 33, 50, 47), (38, 39, 60, 26, 18, 1, 23), (73, 6, 5, 42, 20, 22, 73))
INFORMATION = (2, 3, 5, 6)
G = (0b0001, 0b0011, 0b0101, 0b1111)
W = (0b0100, 0b0101, 0b1100, 0b1010)


def bits(value: int) -> Iterable[int]:
    """Yield set-bit indices; reject negative supports."""
    if value < 0:
        raise ValueError("A binary support must be nonnegative")
    while value:
        low = value & -value
        yield low.bit_length() - 1
        value ^= low


def parity(value: int) -> int:
    return value.bit_count() & 1


def apply_rows(rows: tuple[int, ...], vector: int) -> int:
    return sum(parity(row & vector) << i for i, row in enumerate(rows))


def echelon(rows: Iterable[int]) -> dict[int, int]:
    basis: dict[int, int] = {}
    for original in rows:
        if original < 0:
            raise ValueError("Negative binary row")
        row = original
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = row
                break
            row ^= basis[pivot]
    return basis


def remainder(vector: int, basis: dict[int, int]) -> int:
    if vector < 0:
        raise ValueError("Negative binary vector")
    residual = 0
    while vector:
        pivot = vector.bit_length() - 1
        row = basis.get(pivot)
        if row is None:
            free = 1 << pivot
            residual ^= free
            vector ^= free
        else:
            vector ^= row
    return residual


def kernel(rows: tuple[int, ...], width: int) -> tuple[int, ...]:
    if width < 0 or any(row < 0 or row.bit_length() > width for row in rows):
        raise ValueError("Invalid binary matrix shape")
    basis = echelon(rows)
    pivots = sorted(basis)
    result = []
    for free in range(width):
        if free in basis:
            continue
        vector = 1 << free
        for pivot in pivots:
            if parity(vector & basis[pivot]):
                vector ^= 1 << pivot
        result.append(vector)
    return tuple(result)


def transpose(rows: tuple[int, ...], width: int) -> tuple[int, ...]:
    columns = [0] * width
    for i, row in enumerate(rows):
        if row < 0 or row.bit_length() > width:
            raise ValueError("Invalid binary matrix shape")
        for j in bits(row):
            columns[j] |= 1 << i
    return tuple(columns)


def rotate_cells(vector: int, shift: int, lift: int, cells: int) -> int:
    mask = (1 << lift) - 1
    shift %= lift
    result = 0
    for cell in range(cells):
        part = vector >> (cell * lift) & mask
        part = ((part << shift) | (part >> ((lift - shift) % lift))) & mask
        result |= part << (cell * lift)
    return result


@dataclass(frozen=True)
class RingMatrix:
    """Cells are cyclic polynomial bitmasks, including zero."""

    lift: int
    rows: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if self.lift <= 0 or not self.rows or not self.rows[0]:
            raise ValueError("Nonempty matrix and positive lift required")
        width = len(self.rows[0])
        if any(len(row) != width for row in self.rows):
            raise ValueError("Ragged ring matrix")
        if any(x < 0 or x.bit_length() > self.lift for row in self.rows for x in row):
            raise ValueError("Polynomial outside the cyclic ring")

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.rows), len(self.rows[0])

    def binary(self) -> tuple[int, ...]:
        result = []
        for row in self.rows:
            for c in range(self.lift):
                value = 0
                for j, polynomial in enumerate(row):
                    for exponent in bits(polynomial):
                        value ^= 1 << (j * self.lift + (c - exponent) % self.lift)
                result.append(value)
        return tuple(result)

    def adjoint(self) -> RingMatrix:
        m, n = self.shape
        return RingMatrix(
            self.lift,
            tuple(
                tuple(sum(1 << ((-a) % self.lift) for a in bits(self.rows[i][j])) for i in range(m))
                for j in range(n)
            ),
        )


def base_seed(lift: int = 75) -> RingMatrix:
    """Other odd lifts are structural test instances, not published codes."""
    if lift <= 0 or lift % 2 == 0:
        raise ValueError("An odd positive lift is required")
    return RingMatrix(lift, tuple(tuple(1 << (a % lift) for a in row) for row in EXPONENTS))


def completed_seed(lift: int = 75) -> RingMatrix:
    base = base_seed(lift)
    rows = [row + (0,) * 7 for row in base.rows]
    rows += [(0,) * 7 + row for row in base.rows]
    for w in W:
        wg = 0
        for i in bits(w):
            wg ^= G[i]
        row = [0] * 14
        for i in bits(wg):
            row[INFORMATION[i]] = 1
        for i in bits(w):
            row[7 + INFORMATION[i]] = 1
        rows.append(tuple(row))
    return RingMatrix(lift, tuple(rows))


@dataclass(frozen=True)
class CSSCode:
    n: int
    hx: tuple[int, ...]
    hz: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.n <= 0 or any(row < 0 or row.bit_length() > self.n for row in self.hx + self.hz):
            raise ValueError("Invalid CSS matrix dimensions")


def lifted_product(first: RingMatrix, second: RingMatrix) -> CSSCode:
    if first.lift != second.lift:
        raise ValueError("LP factors have different lifts")
    ell = first.lift
    ma, na = first.shape
    mb, nb = second.shape
    count = na * mb + ma * nb
    x_rows = []
    for i in range(ma):
        for k in range(mb):
            row = [0] * count
            for p in range(na):
                row[p * mb + k] = first.rows[i][p]
            for q in range(nb):
                row[na * mb + i * nb + q] = second.rows[k][q]
            x_rows.append(tuple(row))
    astar, bstar = first.adjoint(), second.adjoint()
    z_rows = []
    for p in range(na):
        for q in range(nb):
            row = [0] * count
            for k in range(mb):
                row[p * mb + k] = bstar.rows[q][k]
            for i in range(ma):
                row[na * mb + i * nb + q] = astar.rows[p][i]
            z_rows.append(tuple(row))
    return CSSCode(
        count * ell,
        RingMatrix(ell, tuple(x_rows)).binary(),
        RingMatrix(ell, tuple(z_rows)).binary(),
    )


def auxiliary(lift: int = 75, *, strict: bool = False) -> CSSCode:
    rows = base_seed(lift).binary()
    if strict:
        all_fibre = (1 << lift) - 1
        rows += (all_fibre << lift, all_fibre << (4 * lift))
    return CSSCode(7 * lift, (), rows)


def info_projection(vector: int, lift: int) -> int:
    mask = (1 << lift) - 1
    return sum(((vector >> (p * lift)) & mask) << (i * lift) for i, p in enumerate(INFORMATION))


@lru_cache(maxsize=4)
def canonical_seed_words(lift: int = 75) -> tuple[int, ...]:
    """Fix the two trivial-component ambiguities by column-2/5 parity=0."""
    strict = auxiliary(lift, strict=True)
    words = kernel(strict.hz, strict.n)
    basis: dict[int, tuple[int, int]] = {}
    for original in words:
        image, word = info_projection(original, lift), original
        while image:
            pivot = image.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = image, word
                break
            image ^= basis[pivot][0]
            word ^= basis[pivot][1]
        if not image:
            raise ValueError("Selected canonical section is not injective")
    if len(basis) != 4 * lift:
        raise ValueError("Selected canonical section is not surjective")
    result = []
    for i in range(4):
        image, word = 1 << (i * lift), 0
        while image:
            pivot = image.bit_length() - 1
            image ^= basis[pivot][0]
            word ^= basis[pivot][1]
        result.append(word)
    return tuple(result)


def embedded_aux(vector: int, row: int, lift: int = 75) -> int:
    if row not in range(4) or vector < 0 or vector.bit_length() > 7 * lift:
        raise ValueError("Invalid auxiliary embedding")
    return vector << (INFORMATION[row] * 7 * lift)


def canonical_logicals(lift: int = 75) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return paired (X,Z), order ((i*4+j)*lift+a).

    Construct actual binary normalizers, not the attachment's ambiguous
    polynomial representative formula. This fixes all shift conventions.
    """
    seed = canonical_seed_words(lift)
    xs, zs = [], []
    for i in range(4):
        second = 0
        for k, row in enumerate(G):
            if row >> i & 1:
                second ^= seed[k]
        graph_word = seed[i] | (second << (7 * lift))
        for j in range(4):
            for a in range(lift):
                xs.append(embedded_aux(rotate_cells(seed[j], a, lift, 7), i, lift))
                z = 0
                shifted = rotate_cells(graph_word, a, lift, 14)
                for position in bits(shifted):
                    p, c = divmod(position, lift)
                    z |= 1 << ((p * 7 + INFORMATION[j]) * lift + c)
                zs.append(z)
    return tuple(xs), tuple(zs)


def automorphism_permutation(lift: int = 75) -> tuple[int, ...]:
    """Old coordinate -> new coordinate for Eq.(74) of the attachment."""
    checks = (3, 4, 5, 0, 1, 2, 7, 6, 9, 8)
    result = []
    for p in range(14):
        for k in range(7):
            for a in range(lift):
                result.append((((p + 7) % 14) * 7 + k) * lift + a)
    for i in range(10):
        for q in range(3):
            for a in range(lift):
                result.append((98 + checks[i] * 3 + q) * lift + a)
    return tuple(result)


def permute(vector: int, permutation: tuple[int, ...]) -> int:
    return sum(1 << permutation[i] for i in bits(vector))


def homomorphic_css_failures(
    data: CSSCode, ancilla: CSSCode, targets: tuple[int, ...]
) -> tuple[int, int]:
    """Check code-preserving ancilla-control CNOT inclusion conditions.

    targets[a] identifies the single data target of auxiliary qubit a. The
    result counts failed X-ancilla and Z-data stabilizer inclusions.
    """
    if (
        len(targets) != ancilla.n
        or len(set(targets)) != len(targets)
        or any(t < 0 or t >= data.n for t in targets)
    ):
        raise ValueError("A valid injective physical matching is required")
    data_x, anc_z = echelon(data.hx), echelon(ancilla.hz)
    x_fail = sum(bool(remainder(permute(x, targets), data_x)) for x in ancilla.hx)
    reverse = {t: i for i, t in enumerate(targets)}
    z_fail = 0
    for z in data.hz:
        restricted = sum(1 << reverse[t] for t in bits(z) if t in reverse)
        z_fail += bool(remainder(restricted, anc_z))
    return x_fail, z_fail


def matrix_digest(rows: tuple[int, ...], width: int) -> str:
    digest = hashlib.sha256()
    digest.update(f"gf2-rows-le:{len(rows)}:{width}\n".encode())
    byte_width = (width + 7) // 8
    for row in rows:
        digest.update(row.to_bytes(byte_width, "little"))
    return digest.hexdigest()


def _commutation_failures(hx: tuple[int, ...], hz: tuple[int, ...], n: int) -> int:
    columns = transpose(hz, n)
    failures = 0
    for row in hx:
        syndrome = 0
        for i in bits(row):
            syndrome ^= columns[i]
        failures += syndrome.bit_count()
    return failures


def audit_instance() -> dict[str, Any]:
    """Reconstruct and exhaustively audit the fixed ell=75 binary instance."""
    lift = 75
    seed = base_seed(lift)
    completed = completed_seed(lift)
    data = lifted_product(completed, seed.adjoint())
    bx, bz = echelon(data.hx), echelon(data.hz)
    xs, zs = canonical_logicals(lift)
    permutation = automorphism_permutation(lift)
    hx_set, hz_set = set(data.hx), set(data.hz)
    failures: dict[str, int] = {
        "css_commutator_nonzeros": _commutation_failures(data.hx, data.hz, data.n),
        "canonical_x_syndromes": sum(bool(apply_rows(data.hz, x)) for x in xs),
        "canonical_z_syndromes": sum(bool(apply_rows(data.hx, z)) for z in zs),
        "canonical_pairing_rows": sum(apply_rows(zs, x) != 1 << i for i, x in enumerate(xs)),
        "permuted_x_checks": sum(permute(x, permutation) not in hx_set for x in data.hx),
        "permuted_z_checks": sum(permute(z, permutation) not in hz_set for z in data.hz),
        "canonical_x_auto_action": 0,
        "canonical_z_auto_action": 0,
    }
    wrong_x = 0
    for index, (x, z) in enumerate(zip(xs, zs, strict=True)):
        i, rest = divmod(index, 4 * lift)
        expected_x, expected_z, transposed_wrong_x = 0, 0, 0
        for k in range(4):
            if G[i] >> k & 1:
                expected_x ^= xs[k * 4 * lift + rest]
            if G[k] >> i & 1:
                expected_z ^= zs[k * 4 * lift + rest]
                transposed_wrong_x ^= xs[k * 4 * lift + rest]
        actual_x, actual_z = permute(x, permutation), permute(z, permutation)
        failures["canonical_x_auto_action"] += bool(remainder(actual_x ^ expected_x, bx))
        failures["canonical_z_auto_action"] += bool(remainder(actual_z ^ expected_z, bz))
        wrong_x += bool(remainder(actual_x ^ transposed_wrong_x, bx))

    # Explicit residual generators of ker A killed by the information projection.
    omega = (1 << lift) - 1
    residuals = (omega | (omega << lift), omega | (omega << (4 * lift)))
    seed_words = canonical_seed_words(lift)
    selected_words = tuple(
        rotate_cells(word, a, lift, 7) for word in seed_words for a in range(lift)
    )
    canonical_x_basis = echelon(data.hx + xs)
    all_canonical_rank = len(canonical_x_basis)
    selected_row = 3  # one-based logical i=4, after the convention audit
    targets = tuple(
        range(INFORMATION[selected_row] * 7 * lift, (INFORMATION[selected_row] + 1) * 7 * lift)
    )
    residual_images = tuple(embedded_aux(r, selected_row, lift) for r in residuals)
    residual_pairing = sum(bool(apply_rows(zs, r)) for r in residual_images)
    residual_extra_rank = len(echelon(data.hx + xs + residual_images)) - all_canonical_rank
    failures["residual_canonical_pairing"] = residual_pairing
    aux_reports = []
    for strict in (False, True):
        aux = auxiliary(lift, strict=strict)
        generators = kernel(aux.hz, aux.n)
        intended = selected_words if strict else selected_words + residuals
        expected_space = echelon(intended)
        space_errors = sum(bool(remainder(v, expected_space)) for v in generators)
        if len(expected_space) != len(generators):
            space_errors += 1
        inclusions = homomorphic_css_failures(data, aux, targets)
        images = tuple(embedded_aux(v, selected_row, lift) for v in generators)
        image_rank = len(echelon(data.hx + images)) - len(bx)
        z_basis = echelon(aux.hz)
        single_z_logicals = [
            i for i in range(aux.n) if not apply_rows(aux.hx, 1 << i) and remainder(1 << i, z_basis)
        ]
        fault_counts = [sum(bool(v >> p & 1) for v in selected_words) for p in range(aux.n)]
        bad = inclusions[0] + inclusions[1] + space_errors
        failures[f"{'strict' if strict else 'raw'}_interface"] = bad
        aux_reports.append(
            {
                "name": "strict_300" if strict else "raw_302",
                "evidence": "NUMERICAL",
                "data_qubits": aux.n,
                "hx_generators": len(aux.hx),
                "hz_generators": len(aux.hz),
                "hz_rank": len(z_basis),
                "hz_weight_max": max(row.bit_count() for row in aux.hz),
                "hz_edges": sum(row.bit_count() for row in aux.hz),
                "logical_qubits": len(generators),
                "independent_measured_data_x": image_rank,
                "canonical_x_measurements": 300,
                "additional_residual_x_measurements": 0 if strict else 2,
                "preserves_unmeasured_residual_subsystem_ideally": strict,
                "homomorphic_inclusion_failures": list(inclusions),
                "measured_space_failures": space_errors,
                "interface_cnots": aux.n,
                "interface_matching_layers": 1,
                "algebraic_batch_ghz4_count": 300,
                "z_distance": 1,
                "single_z_logical_count": len(single_z_logicals),
                "readout_fault_canonical_outcomes_flipped_min": min(fault_counts),
                "readout_fault_canonical_outcomes_flipped_max": max(fault_counts),
                "single_fault_witness": {
                    "auxiliary_physical_qubit_zero_based": INFORMATION[0] * lift,
                    "fault": "Z immediately before destructive X readout",
                    "auxiliary_syndrome": [],
                    "data_error_propagated": False,
                    "canonical_outcomes_flipped": fault_counts[INFORMATION[0] * lift],
                    "incorrect_canonical_sign": "GHZ quartet j=1,a=0",
                },
                "ft_single_shot_admitted": False,
                "data_plus_helper_qubits_excluding_qec": data.n + aux.n,
                "qec_ancillas_one_per_supplied_check_not_ft_schedule": len(data.hx)
                + len(data.hz)
                + len(aux.hz),
                "initialization_rounds": None,
                "logical_failure_probability": None,
                "native_runtime_seconds": None,
                "ft_admitted_parallel_measurements": None,
                "hz_sha256": matrix_digest(aux.hz, aux.n),
                "kernel_sha256": matrix_digest(generators, aux.n),
            }
        )
    if residual_extra_rank != 2:
        failures["residual_extra_rank"] = 1
    if any(failures.values()):
        raise ValueError(f"Finite certificate failed: {failures}")
    return {
        "schema": "lp-ghz-certificate-v1",
        "task_id": "T-20261001-001",
        "code": {
            "name": "Q_one=LP(tilde_A,A*)",
            "lift": lift,
            "data_qubits": data.n,
            "hx_rows": len(data.hx),
            "hx_rank": len(bx),
            "hz_rows": len(data.hz),
            "hz_rank": len(bz),
            "logical_qubits": data.n - len(bx) - len(bz),
            "canonical_logical_qubits": len(xs),
            "residual_logical_qubits": 40,
            "hx_max_weight": max(row.bit_count() for row in data.hx),
            "hz_max_weight": max(row.bit_count() for row in data.hz),
            "hx_edges": sum(row.bit_count() for row in data.hx),
            "hz_edges": sum(row.bit_count() for row in data.hz),
            "hx_sha256": matrix_digest(data.hx, data.n),
            "hz_sha256": matrix_digest(data.hz, data.n),
            "canonical_x_sha256": matrix_digest(xs, data.n),
            "canonical_z_sha256": matrix_digest(zs, data.n),
            "base_rank": len(echelon(seed.binary())),
            "completed_seed_rank": len(echelon(completed.binary())),
        },
        "convention": {
            "support": "binary column vector; circulant row c, column c-t",
            "canonical_order": "((i*4+j)*75+a), all indices zero-based",
            "canonical_section": "pi_J E=I; parity of base columns 2 and 5 is zero",
            "canonical_seed_words_hex": [hex(word) for word in seed_words],
            "g_z_rows_little_endian": list(G),
            "computational_gate": "transpose(g_z)",
            "correct_ghz_input": "000+",
            "correct_selected_logical_row_one_based": 4,
            "source_ghz_input_negative_control": "+000",
            "wrong_x_action_failures_of_1200": wrong_x,
        },
        "checks": failures,
        "residual_image": {
            "basis_hex": [hex(r) for r in residuals],
            "additional_rank_beyond_all_canonical_x": residual_extra_rank,
            "canonical_symplectic_pairing_failures": residual_pairing,
            "canonical_symplectic_space_invariant": True,
        },
        "auxiliaries": aux_reports,
        "admission": {
            "ideal_algebra": True,
            "fault_tolerant_factory": False,
            "runtime_seconds": None,
            "failure_probability": None,
            "distance_of_data_code_certified_this_cycle": None,
            "review_status": "PENDING",
        },
    }
