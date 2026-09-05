"""Generate scalable logical-support certificates for direct-CCZ QCLA PPMs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from ecdlp_ftqc.architectures import load_direct_ccz_capability
from ecdlp_ftqc.circuits import (
    QCLA_SOURCE_PDF_SHA256,
    build_oop_qcla_trace,
    build_qcla_trace,
)
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_direct_ccz_events,
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    lower_qcla_to_direct_ccz_events,
    lower_qcla_to_symbolic_direct_ccz_ppm,
)
from ecdlp_ftqc.scheduler import (
    certify_qcla_direct_ccz_ppm_support,
    compare_support_certificate_to_symbolic_trace,
    exact_support_equivalence_to_data,
    qcla_ppm_support_certificate_aggregate_to_data,
    qcla_ppm_support_certificate_summary_to_data,
)
from ecdlp_ftqc.verification import (
    direct_ccz_ppm_support_replay_to_data,
    replay_direct_ccz_ppm_support,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "T-20260903-002"
EXPERIMENT_ID = "E-20260903-002"
WIDTHS = (
    5,
    7,
    8,
    9,
    15,
    16,
    17,
    31,
    32,
    33,
    63,
    64,
    65,
    127,
    128,
    129,
    255,
    256,
    257,
)
EXACT_WIDTHS = (5, 8)
VARIANTS: tuple[Literal["oop", "ip"], ...] = ("oop", "ip")
SAMPLE_SEED = "T-20260903-002-support-witnesses-v1"
CAPABILITY_PATH = (
    PROJECT_ROOT
    / "configs"
    / "architectures"
    / "direct_ccz_single_event_capability_v1.yaml"
)
DRAPER_PDF = PROJECT_ROOT / "literature" / "papers" / "quant-ph-0406142v1.pdf"
OUTPUT_ROOT = PROJECT_ROOT / "experiments" / "runs" / TASK_ID
SOURCE_BINDINGS = (
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "circuits" / "qcla_oop.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz.py",
    PROJECT_ROOT / "src" / "ecdlp_ftqc" / "compiler" / "direct_ccz_ppm.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "scheduler"
    / "direct_ccz_ppm_support_certificate.py",
    PROJECT_ROOT
    / "src"
    / "ecdlp_ftqc"
    / "verification"
    / "direct_ccz_ppm_support_replay.py",
    PROJECT_ROOT / "docs" / "DIRECT_CCZ_QCLA_SCALABLE_SUPPORT_CONTRACT.md",
    PROJECT_ROOT / "experiments" / "manifests" / "E-20260903-002.yaml",
    CAPABILITY_PATH,
    Path(__file__),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest().upper()


def _git(*args: str) -> str:
    completed = subprocess.run(
        ("git", *args),
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _filtered_worktree_status() -> str:
    lines = _git("status", "--porcelain").splitlines()
    return "\n".join(
        line
        for line in lines
        if not line.startswith("?? .claude/")
        and f"experiments/runs/{TASK_ID}/" not in line.replace("\\", "/")
        and not line.startswith("?? tmp/")
    )


def _verify_source_hashes() -> dict[str, str]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    paths = {DRAPER_PDF}
    paths.update(PROJECT_ROOT / source.local_pdf for source in capability.sources)
    hashes = {
        str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
        for path in sorted(paths)
    }
    draper_key = str(DRAPER_PDF.relative_to(PROJECT_ROOT)).replace("\\", "/")
    if hashes[draper_key] != QCLA_SOURCE_PDF_SHA256:
        raise RuntimeError("Draper source PDF hash mismatch")
    for source in capability.sources:
        if hashes[source.local_pdf] != source.pdf_sha256.upper():
            raise RuntimeError(f"source PDF hash mismatch: {source.local_pdf}")
    return hashes


def main() -> None:
    source_pdf_hashes = _verify_source_hashes()
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    aggregates: list[dict[str, Any]] = []
    exact_objects: dict[tuple[str, int], Any] = {}
    width_256_objects: dict[str, Any] = {}

    for width in WIDTHS:
        for variant in VARIANTS:
            if variant == "oop":
                oop_trace = build_oop_qcla_trace(width)
                oop_events = lower_oop_qcla_to_direct_ccz_events(
                    oop_trace, capability
                )
                certificate = certify_qcla_direct_ccz_ppm_support(
                    oop_trace,
                    oop_events,
                    variant=variant,
                )
            else:
                ip_trace = build_qcla_trace(width)
                ip_events = lower_qcla_to_direct_ccz_events(ip_trace, capability)
                certificate = certify_qcla_direct_ccz_ppm_support(
                    ip_trace,
                    ip_events,
                    variant=variant,
                )
            if certificate.validation_counterexample is not None:
                raise RuntimeError(
                    f"support certificate failed for {variant} width {width}"
                )
            aggregates.append(
                qcla_ppm_support_certificate_aggregate_to_data(certificate)
            )
            if width in EXACT_WIDTHS:
                exact_objects[(variant, width)] = certificate
            if width == 256:
                width_256_objects[variant] = certificate

    equivalences: list[dict[str, Any]] = []
    for width in EXACT_WIDTHS:
        for variant in VARIANTS:
            if variant == "oop":
                oop_trace = build_oop_qcla_trace(width)
                symbolic = lower_oop_qcla_to_symbolic_direct_ccz_ppm(
                    oop_trace, capability
                )
            else:
                ip_trace = build_qcla_trace(width)
                symbolic = lower_qcla_to_symbolic_direct_ccz_ppm(
                    ip_trace, capability
                )
            equivalence = compare_support_certificate_to_symbolic_trace(
                exact_objects[(variant, width)],
                symbolic,
            )
            if not equivalence.all_checks_passed:
                raise RuntimeError(
                    f"exact support anchor failed for {variant} width {width}"
                )
            equivalences.append(exact_support_equivalence_to_data(equivalence))

    width_256_hypergraphs = [
        qcla_ppm_support_certificate_summary_to_data(
            width_256_objects[variant]
        )
        for variant in VARIANTS
    ]
    replay = replay_direct_ccz_ppm_support(
        aggregates,
        width_256_hypergraphs,
        expected_widths=WIDTHS,
    )
    if not replay.all_passed:
        raise RuntimeError("independent support replay failed")
    replay_data = direct_ccz_ppm_support_replay_to_data(replay)

    width_256 = {
        variant: qcla_ppm_support_certificate_aggregate_to_data(
            width_256_objects[variant]
        )
        for variant in VARIANTS
    }
    summary = {
        "certificate_method": {
            "exact": (
                "canonical Boolean ANF support propagation for every OOP width "
                "and OOP/IP widths 5 and 8"
            ),
            "ip_large": (
                "sound may-support upper envelope plus 512 deterministic concrete "
                "branch lower witnesses"
            ),
            "coordinate": "logical support hypergraph, not native geometry or time",
        },
        "evidence_qualification": {
            "outcome_independent_support": (
                "FALSIFIED by an exact width-5 branch witness"
            ),
            "oop_possible_support": "PROVED exact at every selected width",
            "ip_large_possible_support": (
                "CHECK where deterministic witnesses do not saturate the sound "
                "may-support upper envelope"
            ),
            "exact_anchor_bridge": (
                "NUMERICAL full-ANF agreement at OOP/IP widths 5 and 8"
            ),
            "native_backend": (
                "OPEN; surgery rounds, runtime, physical qubits, and failure "
                "probability remain null"
            ),
        },
        "exact_anchor_equivalences": equivalences,
        "experiment_id": EXPERIMENT_ID,
        "input_configuration": str(
            CAPABILITY_PATH.relative_to(PROJECT_ROOT)
        ).replace("\\", "/"),
        "sample_seed": SAMPLE_SEED,
        "source_pdf_hashes": source_pdf_hashes,
        "task_id": TASK_ID,
        "validation_status": (
            "passed_exact_anchors_support_brackets_and_independent_replay"
        ),
        "width_256": {
            variant: {
                "all_possible_supports_exact": width_256[variant][
                    "all_possible_supports_exact"
                ],
                "branch_dependent_profile_count": width_256[variant][
                    "branch_dependent_profile_count"
                ],
                "candidate_batch_level_count": width_256[variant][
                    "candidate_batch_level_count"
                ],
                "maximum_batch_possible_contact_count": width_256[variant][
                    "maximum_batch_possible_contact_count"
                ],
                "maximum_batch_witnessed_contact_count": width_256[variant][
                    "maximum_batch_witnessed_contact_count"
                ],
                "maximum_ppm_weight_upper_bound": width_256[variant][
                    "maximum_ppm_weight_upper_bound"
                ],
                "maximum_sampled_branch_weight": width_256[variant][
                    "maximum_sampled_branch_weight"
                ],
                "maximum_witnessed_support_union_size": width_256[variant][
                    "maximum_witnessed_support_union_size"
                ],
                "ppm_count": width_256[variant]["ppm_count"],
                "support_envelope_evidence_status": width_256[variant][
                    "support_envelope_evidence_status"
                ],
            }
            for variant in VARIANTS
        },
    }

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    primary_outputs = {
        "exact_anchor_equivalence.json": equivalences,
        "independent_replay.json": replay_data,
        "summary.json": summary,
        "support_aggregates.json": aggregates,
        "width_256_support_hypergraphs.json": width_256_hypergraphs,
    }
    for name, value in primary_outputs.items():
        _write_json(OUTPUT_ROOT / name, value)

    filtered_status = _filtered_worktree_status()
    reproducibility = {
        "configuration_sha256": {
            str(CAPABILITY_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"): (
                _sha256(CAPABILITY_PATH)
            )
        },
        "exact_widths": list(EXACT_WIDTHS),
        "experiment_id": EXPERIMENT_ID,
        "git_branch": _git("branch", "--show-current"),
        "git_head": _git("rev-parse", "HEAD"),
        "input_trace": "deterministically generated OOP/IP QCLA source traces",
        "output_path": str(OUTPUT_ROOT.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        ),
        "output_sha256": {
            name: _sha256(OUTPUT_ROOT / name) for name in sorted(primary_outputs)
        },
        "package_versions": {
            name: importlib.metadata.version(name)
            for name in ("mypy", "networkx", "pytest", "pyyaml", "ruff")
        },
        "platform": platform.platform(),
        "python": sys.version,
        "sample_seed": SAMPLE_SEED,
        "source_binding_sha256": {
            str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"): _sha256(path)
            for path in SOURCE_BINDINGS
        },
        "source_pdf_hashes": source_pdf_hashes,
        "task_id": TASK_ID,
        "validation_status": summary["validation_status"],
        "widths": list(WIDTHS),
        "working_tree_state": "dirty:" + _text_sha256(filtered_status),
        "working_tree_status": filtered_status,
    }
    _write_json(OUTPUT_ROOT / "reproducibility.json", reproducibility)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
