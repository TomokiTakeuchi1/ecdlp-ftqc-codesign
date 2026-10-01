"""Generate the deterministic T-20261001-001 finite-instance certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from ecdlp_ftqc.code_constructions.lp_ghz import EXPONENTS, INFORMATION, G, W, audit_instance
from ecdlp_ftqc.verification.lp_ghz import dense_logical_audit, validate_emitted_certificate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/manifests/E-20261001-001.json"


def load_manifest(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": "lp-ghz-input-v1",
        "task_id": "T-20261001-001",
        "lift": 75,
        "seed_exponents": [list(row) for row in EXPONENTS],
        "information_columns_zero_based": list(INFORMATION),
        "g_z_rows_little_endian": list(G),
        "w_rows_little_endian": list(W),
        "selected_logical_row_one_based": 4,
        "initial_proposal_row_one_based_negative_control": 1,
        "canonical_section_zero_parity_columns_one_based": [2, 5],
        "auxiliary_variants": ["raw_302", "strict_300"],
        "random_seed": None,
        "native_timing": None,
        "ft_admission": False,
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"Manifest mismatch: {key}")
    for source in config["sources"]:
        if "path" in source:
            digest = hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest()
            if digest != source["sha256"]:
                raise ValueError(f"Source hash mismatch: {source['name']}")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "experiments/runs/T-20261001-001")
    args = parser.parse_args()
    config = load_manifest(MANIFEST)
    result = audit_instance()
    result["independent_dense_logical_audit"] = dense_logical_audit()
    result["manifest_sha256"] = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    result["sources"] = config["sources"]
    validate_emitted_certificate(result)
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    summary = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (output / "summary.json").write_text(summary, encoding="utf-8", newline="\n")
    tracked_sources = [
        "src/ecdlp_ftqc/code_constructions/lp_ghz.py",
        "src/ecdlp_ftqc/verification/lp_ghz.py",
        "scripts/run_lp_ghz_cycle.py",
        "experiments/manifests/E-20261001-001.json",
    ]
    repro = {
        "task_id": "T-20261001-001",
        "python": sys.version,
        "platform": platform.platform(),
        "random_seed": None,
        "working_tree_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_status": subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True
        ).splitlines(),
        "input_files_sha256": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked_sources
        },
        "summary_sha256": hashlib.sha256(summary.encode()).hexdigest(),
        "output_path": str(output.resolve()),
        "validation": "exact GF(2) certificate plus independent dense logical checks",
        "cross_review": "PENDING",
    }
    (output / "reproducibility.json").write_text(
        json.dumps(repro, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "code": result["code"],
                "convention": result["convention"],
                "auxiliaries": result["auxiliaries"],
                "summary_sha256": repro["summary_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
