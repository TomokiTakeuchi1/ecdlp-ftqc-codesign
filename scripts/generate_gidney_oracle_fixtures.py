"""Generate deterministic small-width Gidney oracle fixtures from a pinned checkout."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecdlp_ftqc.circuits.gidney_adapter import PINNED_GIDNEY_SOURCE_COMMIT

RELEVANT_SOURCE_PATHS = (
    "src/runtime_metadata_benchmark/gidney",
    "src/runtime_metadata_benchmark/ir",
    "src/runtime_metadata_benchmark/ppm",
    "src/runtime_metadata_benchmark/scheduling",
)


def _git(source_repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={source_repo.as_posix()}",
            "-C",
            str(source_repo),
            *arguments,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _verify_source(source_repo: Path) -> None:
    observed_commit = _git(source_repo, "rev-parse", "HEAD")
    if observed_commit != PINNED_GIDNEY_SOURCE_COMMIT:
        raise RuntimeError(
            "Gidney source commit mismatch: "
            f"expected {PINNED_GIDNEY_SOURCE_COMMIT}, observed {observed_commit}"
        )
    status = _git(source_repo, "status", "--porcelain", "--", *RELEVANT_SOURCE_PATHS)
    if status:
        raise RuntimeError(
            "Gidney fixture inputs contain uncommitted changes:\n" + status
        )


def _generate(source_repo: Path, output_dir: Path, widths: tuple[int, ...]) -> None:
    _verify_source(source_repo)
    sys.path.insert(0, str(source_repo / "src"))
    from runtime_metadata_benchmark.gidney import (
        generate_gidney_adder,
        to_oracle_document,
    )
    from runtime_metadata_benchmark.ir import dumps_oracle

    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for width in widths:
        if width < 2:
            raise ValueError("fixture widths must be at least two")
        text = dumps_oracle(to_oracle_document(generate_gidney_adder(width)))
        name = f"gidney_width{width}_oracle_v3.json"
        output = output_dir / name
        output.write_text(text, encoding="utf-8", newline="\n")
        encoded = text.encode("utf-8")
        files.append(
            {
                "bytes": len(encoded),
                "name": name,
                "sha256": sha256(encoded).hexdigest(),
                "width": width,
            }
        )

    manifest = {
        "files": files,
        "generator": "runtime_metadata_benchmark.gidney",
        "oracle_schema": "runtime-metadata-benchmark/oracle",
        "oracle_schema_version": 3,
        "source_commit": PINNED_GIDNEY_SOURCE_COMMIT,
        "source_repository": "runtime-metadata-benchmark",
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (output_dir / "manifest.json").write_text(
        manifest_text,
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--widths", type=int, nargs="+", default=(2, 3, 4))
    arguments = parser.parse_args()
    _generate(
        arguments.source_repo.resolve(),
        arguments.output_dir.resolve(),
        tuple(arguments.widths),
    )


if __name__ == "__main__":
    main()
