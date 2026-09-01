from __future__ import annotations

import copy
import inspect
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from ecdlp_ftqc.architectures import (
    load_direct_ccz_backend_audit,
    load_direct_ccz_capability,
)
from ecdlp_ftqc.circuits import build_oop_qcla_trace
from ecdlp_ftqc.compiler import (
    lower_oop_qcla_to_symbolic_direct_ccz_ppm,
    symbolic_direct_ccz_ppm_trace_to_data,
)
from ecdlp_ftqc.scheduler import (
    analyze_direct_ccz_ppm_batches,
    finite_instance_admission_to_data,
    general_high_rate_candidate_to_data,
)
from ecdlp_ftqc.verification import (
    DirectCczPpmAtlasReplayError,
    replay_direct_ccz_ppm_atlas,
)
from ecdlp_ftqc.verification import direct_ccz_ppm_atlas_replay as replay_module
from ecdlp_ftqc.visualization import (
    DirectCczPpmAtlasError,
    build_direct_ccz_ppm_atlas,
    dumps_direct_ccz_ppm_atlas,
    render_direct_ccz_ppm_atlas_svgs,
)

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = ROOT / "configs" / "architectures" / "direct_ccz_single_event_capability_v1.yaml"
AUDIT_PATH = ROOT / "configs" / "architectures" / "direct_ccz_finite_backend_audit_v1.yaml"


@pytest.fixture(scope="module")
def atlas_cycle() -> dict[str, Any]:
    capability = load_direct_ccz_capability(CAPABILITY_PATH)
    audit = load_direct_ccz_backend_audit(AUDIT_PATH)
    trace = lower_oop_qcla_to_symbolic_direct_ccz_ppm(
        build_oop_qcla_trace(5),
        capability,
    )
    analysis = analyze_direct_ccz_ppm_batches(trace, capability, audit)
    trace_data = symbolic_direct_ccz_ppm_trace_to_data(trace)
    general_data = general_high_rate_candidate_to_data(analysis.general)
    finite_data = finite_instance_admission_to_data(analysis.finite)
    atlas_data = build_direct_ccz_ppm_atlas(trace_data, general_data, finite_data)
    svg_documents = render_direct_ccz_ppm_atlas_svgs(atlas_data)
    replay = replay_direct_ccz_ppm_atlas(
        trace_data,
        general_data,
        finite_data,
        atlas_data,
        svg_documents,
    )
    return {
        "atlas_data": atlas_data,
        "finite_data": finite_data,
        "general_data": general_data,
        "replay": replay,
        "svg_documents": svg_documents,
        "trace_data": trace_data,
    }


def test_atlas_overview_preserves_reviewed_counts(atlas_cycle: dict[str, Any]) -> None:
    overview = atlas_cycle["atlas_data"]["overview"]

    assert overview == {
        "batch_sizes": [12, 12, 6, 6, 3, 3, 3, 3, 3, 3, 3, 3],
        "candidate_batch_level_count": 12,
        "correction_update_count": 60,
        "injection_count": 10,
        "macro_layer_count": 9,
        "maximum_ppm_weight": 7,
        "peak_live_logical_requirement": 26,
        "peak_resource_state_count": 4,
        "ppm_count": 60,
        "source_kind_counts": {"cnot": 13, "toffoli": 10},
        "source_operation_count": 23,
    }


def test_all_nine_macro_layers_are_rendered_without_hiding_empty_ppm_layers(
    atlas_cycle: dict[str, Any],
) -> None:
    panels = atlas_cycle["atlas_data"]["panels"]

    assert [panel["source_algorithmic_layer"] for panel in panels] == list(range(1, 10))
    assert [len(panel["source_operations"]) for panel in panels] == [4, 3, 1, 2, 1, 1, 1, 5, 5]
    assert [len(panel["ppm_operation_ids"]) for panel in panels] == [24, 0, 6, 12, 6, 6, 6, 0, 0]
    assert [panel["frame_in_term_count"] for panel in panels] == [0, 24, 24, 30, 42, 48, 54, 60, 60]
    assert [panel["frame_out_term_count"] for panel in panels] == [
        24,
        24,
        30,
        42,
        48,
        54,
        60,
        60,
        60,
    ]


def test_every_ppm_outcome_and_frame_update_is_present_once(
    atlas_cycle: dict[str, Any],
) -> None:
    panels = atlas_cycle["atlas_data"]["panels"]
    ppm_rows = [
        ppm
        for panel in panels
        for operation in panel["source_operations"]
        for ppm in operation["ppm_measurements"]
    ]
    update_rows = [
        update
        for panel in panels
        for operation in panel["source_operations"]
        for update in operation["correction_updates"]
    ]

    assert len(ppm_rows) == len({ppm["operation_id"] for ppm in ppm_rows}) == 60
    assert len({ppm["outcome_token"] for ppm in ppm_rows}) == 60
    assert len(update_rows) == len({update["update_id"] for update in update_rows}) == 60
    assert all(update["outcome_dependencies"] for update in update_rows)


def test_split_certificates_preserve_all_pairwise_reasons(
    atlas_cycle: dict[str, Any],
) -> None:
    reason_counts: Counter[str] = Counter()
    certificate_count = 0
    for panel in atlas_cycle["atlas_data"]["panels"]:
        reason_counts.update(panel["separation_reason_counts"])
        for operation in panel["source_operations"]:
            for ppm in operation["ppm_measurements"]:
                certificate_count += len(ppm["separation_certificates_from_earlier_levels"])

    assert certificate_count == 1584
    assert reason_counts == Counter(
        {
            "causal_dependency": 1206,
            "reaction_dependency": 1116,
            "deterministic_frontier_partition": 378,
            "logical_axis_conflict": 30,
            "resource_reuse": 30,
            "symplectic_noncommutation": 30,
        }
    )


def test_general_and_finite_statuses_are_separate_and_fail_closed(
    atlas_cycle: dict[str, Any],
) -> None:
    status = atlas_cycle["atlas_data"]["backend_status"]

    assert status["general_high_rate_candidate"] is True
    assert status["finite_backend_admitted"] is False
    assert status["native_schedule_emitted"] is False
    assert status["null_finite_outputs"] == {
        "failure_probability": None,
        "physical_qubits": None,
        "runtime_seconds": None,
        "schedule": None,
    }
    assert len(status["capability_missing_fields"]) == 13
    assert len(status["backend_missing_fields"]) == 13
    assert len(status["backend_incompatible_fields"]) == 3
    assert len(status["native_mapper_missing_fields"]) == 4


def test_svg_set_is_static_valid_and_machine_addressable(
    atlas_cycle: dict[str, Any],
) -> None:
    documents = atlas_cycle["svg_documents"]

    assert sorted(documents) == [
        *(f"macro-layer-{layer:02d}.svg" for layer in range(1, 10)),
        "overview.svg",
    ]
    for document in documents.values():
        root = ET.fromstring(document)
        assert root.attrib["data-batch-unit"] == "candidate_batch_level_not_time"
        assert root.attrib["role"] == "img"
        assert "candidate batch levels are not time, surgery rounds" in "".join(root.itertext())
        assert "<script" not in document
        assert "href=" not in document


def test_svg_batch_palette_and_conditions_survive_portable_rendering(
    atlas_cycle: dict[str, Any],
) -> None:
    atlas = atlas_cycle["atlas_data"]
    documents = atlas_cycle["svg_documents"]
    overview = documents["overview.svg"]

    for legend in atlas["batch_legend"]:
        assert f'style="fill:{legend["color"]}"' in overview
    assert " xor " in documents["macro-layer-01.svg"]
    assert "⊕" not in documents["macro-layer-01.svg"]


def test_every_layer_frame_out_bar_stays_inside_its_svg_viewport(
    atlas_cycle: dict[str, Any],
) -> None:
    namespace = "{http://www.w3.org/2000/svg}"
    for name, document in atlas_cycle["svg_documents"].items():
        if name == "overview.svg":
            continue
        root = ET.fromstring(document)
        frame_out = next(
            element for element in root.iter() if element.attrib.get("data-frame-role") == "out"
        )
        frame_rect = frame_out.find(f"{namespace}rect")
        assert frame_rect is not None
        frame_bottom = int(frame_rect.attrib["y"]) + int(frame_rect.attrib["height"])
        assert frame_bottom <= int(root.attrib["height"])


def test_independent_replay_checks_data_and_svg_coverage(
    atlas_cycle: dict[str, Any],
) -> None:
    replay = atlas_cycle["replay"]

    assert replay.all_passed
    assert replay.atlas_panel_count == 9
    assert replay.source_operation_checks == 23
    assert replay.ppm_checks == replay.batch_membership_checks == 60
    assert replay.correction_update_checks == 60
    assert replay.source_dependency_checks == 36
    assert replay.separation_certificate_checks == 1584
    assert replay.svg_document_checks == replay.non_temporal_document_checks == 10
    assert replay.svg_source_operation_id_checks == 23
    assert replay.svg_ppm_id_checks == 60
    assert replay.svg_update_id_checks == 60
    assert replay.finite_backend_rejected


def test_independent_replay_does_not_import_renderer_compiler_or_scheduler() -> None:
    source = inspect.getsource(replay_module)

    assert "from ecdlp_ftqc.visualization" not in source
    assert "from ecdlp_ftqc.compiler" not in source
    assert "from ecdlp_ftqc.scheduler" not in source


def test_replay_rejects_tampered_batch_membership(atlas_cycle: dict[str, Any]) -> None:
    atlas = copy.deepcopy(atlas_cycle["atlas_data"])
    atlas["panels"][0]["source_operations"][0]["ppm_measurements"][0]["batch_level"] = 12
    svgs = render_direct_ccz_ppm_atlas_svgs(atlas)

    with pytest.raises(DirectCczPpmAtlasReplayError, match="batch mismatch"):
        replay_direct_ccz_ppm_atlas(
            atlas_cycle["trace_data"],
            atlas_cycle["general_data"],
            atlas_cycle["finite_data"],
            atlas,
            svgs,
        )


def test_replay_rejects_svg_with_missing_ppm(atlas_cycle: dict[str, Any]) -> None:
    documents = dict(atlas_cycle["svg_documents"])
    documents["macro-layer-01.svg"] = documents["macro-layer-01.svg"].replace(
        'data-ppm-id="direct-ccz:000000:ppm:zz_0"',
        'data-removed-ppm-id="direct-ccz:000000:ppm:zz_0"',
        1,
    )

    with pytest.raises(DirectCczPpmAtlasReplayError, match="SVG PPM coverage"):
        replay_direct_ccz_ppm_atlas(
            atlas_cycle["trace_data"],
            atlas_cycle["general_data"],
            atlas_cycle["finite_data"],
            atlas_cycle["atlas_data"],
            documents,
        )


def test_builder_rejects_forged_finite_output(atlas_cycle: dict[str, Any]) -> None:
    finite = copy.deepcopy(atlas_cycle["finite_data"])
    finite["runtime_seconds"] = 1.0

    with pytest.raises(DirectCczPpmAtlasError, match="null outputs"):
        build_direct_ccz_ppm_atlas(
            atlas_cycle["trace_data"],
            atlas_cycle["general_data"],
            finite,
        )


def test_atlas_json_and_svg_rendering_are_deterministic(
    atlas_cycle: dict[str, Any],
) -> None:
    atlas = atlas_cycle["atlas_data"]

    assert dumps_direct_ccz_ppm_atlas(atlas) == dumps_direct_ccz_ppm_atlas(copy.deepcopy(atlas))
    assert render_direct_ccz_ppm_atlas_svgs(atlas) == render_direct_ccz_ppm_atlas_svgs(
        copy.deepcopy(atlas)
    )
