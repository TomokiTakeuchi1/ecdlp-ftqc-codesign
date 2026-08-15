from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HUB = ROOT / "Research Hub"
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def _resolve_wiki_link(source: Path, raw_target: str) -> Path:
    target = raw_target.split("|", maxsplit=1)[0].split("#", maxsplit=1)[0]
    candidate = Path(target)
    if not candidate.suffix:
        candidate = candidate.with_suffix(".md")
    rooted = ROOT / candidate
    if rooted.exists():
        return rooted
    return source.parent / candidate


def test_required_research_hub_files_exist() -> None:
    required = {
        "Home.md",
        "Roadmap.md",
        "Progress Log.md",
        "Decisions and Blockers.md",
        "Glossary.md",
        "How to Update.md",
        "Architecture Map.canvas",
    }

    assert required <= {path.name for path in HUB.iterdir()}
    assert (ROOT / ".obsidian" / "snippets" / "research-dashboard.css").is_file()


def test_hub_wiki_links_resolve() -> None:
    missing: list[str] = []
    for source in HUB.glob("*.md"):
        for raw_target in WIKI_LINK_RE.findall(source.read_text(encoding="utf-8")):
            resolved = _resolve_wiki_link(source, raw_target)
            if not resolved.exists():
                missing.append(f"{source.relative_to(ROOT)} -> {raw_target}")

    assert missing == []


def test_architecture_canvas_is_well_formed_and_links_existing_files() -> None:
    canvas_path = HUB / "Architecture Map.canvas"
    canvas = json.loads(canvas_path.read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in canvas["nodes"]}

    assert len(node_ids) == len(canvas["nodes"])
    assert {"algorithm", "memory", "bridge", "processor", "operation", "factory"} <= node_ids

    for node in canvas["nodes"]:
        if node["type"] == "file":
            assert (ROOT / node["file"]).is_file()

    for edge in canvas["edges"]:
        assert edge["fromNode"] in node_ids
        assert edge["toNode"] in node_ids


def test_dashboard_preserves_evidence_qualifiers() -> None:
    home = (HUB / "Home.md").read_text(encoding="utf-8")

    assert "T-BOOT-001" in home
    assert "RV-20260815-004" in home
    assert "15,270 syndrome rounds" in home
    assert "CHECK" in home
    assert "not" in home.lower() and "runtime" in home.lower()


def test_dashboard_css_snippet_is_enabled() -> None:
    appearance = json.loads(
        (ROOT / ".obsidian" / "appearance.json").read_text(encoding="utf-8")
    )

    assert "research-dashboard" in appearance["enabledCssSnippets"]
