from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, encoding=CSV_ENCODING, dtype=str, keep_default_na=False, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def test_phase21_official_source_and_track_separation() -> None:
    final = json.loads((PROCESSED_DIR / "partial_stats_phase21_gva_final_status.json").read_text(encoding="utf-8"))
    assert final["target"] == "GVA"
    assert final["target_unchanged"] is True
    assert final["official_quarterly_source_materialized"] is False
    assert final["first_release_target_count"] == 0
    assert final["latest_revision_target_count"] == 0
    assert final["official_proxy_tracks_separated"] is True
    assert final["official_statistics_claim"] is False
    assert final["production_use"] is False

    source = read_csv("partial_stats_phase21_gva_official_source_registry.csv")
    official = source[source["source_id"].eq("KOSIS_EXPERIMENTAL_QUARTERLY_GRDP")].iloc[0]
    assert official["direct_source_gate"] == "fail"
    proxy = source[source["source_id"].eq("PROJECT_SIDO_QUARTERLY_GVA_BENCHMARK")].iloc[0]
    assert proxy["direct_source_gate"] == "fail_proxy_not_official"

    official_cube = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_official_target_cube.parquet")
    assert len(official_cube) == 0


def test_phase21_warmup_leakage_origin_and_selection() -> None:
    warmup = read_csv("partial_stats_phase21_gva_warmup_audit.csv")
    assert warmup["evaluation_role"].eq("warmup_seed").all()
    assert warmup["scored"].eq("N").all()

    zero = read_csv("partial_stats_phase21_gva_zero_error_audit.csv")
    assert zero["zero_error_reason"].isin(["warmup_target_copy", "rounding_or_constraint_identity"]).all()

    leakage = read_csv("partial_stats_phase21_gva_leakage_audit.csv")
    assert leakage[leakage["check_id"].eq("same_period_actual_used")]["status"].iloc[0] == "pass"

    origin = read_csv("partial_stats_phase21_gva_origin_identity_audit.csv")
    assert origin["origin_status"].eq("independent_origin").sum() == 1
    assert origin["origin_status"].eq("collapsed_origin").sum() == 6

    selection = read_csv("partial_stats_phase21_gva_parent_policy_selection.csv")
    assert selection[selection["metric_best"].eq("Y")]["parent_policy_id"].iloc[0] == "QP1_national_bridge"
    assert selection[selection["gate_selected_policy"].eq("Y")]["parent_policy_id"].iloc[0] == "QP0_seasonal"


def test_phase21_parent_child_and_archive_outputs() -> None:
    growth = read_csv("partial_stats_phase21_gva_growth_accuracy.csv")
    assert growth["growth_unit"].eq("percentage_point").all()
    assert num(growth["yoy_growth_mae_pp"]).notna().all()

    unreconciled = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_child_unreconciled.parquet")
    reconciled = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase21_gva_child_reconciled.parquet")
    assert len(unreconciled) == len(reconciled)
    assert len(unreconciled) > 0

    child = read_csv("partial_stats_phase21_gva_child_validation.csv")
    assert child["direct_sigungu_quarterly_actual"].eq("N").all()
    assert child["accuracy_claim"].eq("indirect_development_only").all()

    archive = read_csv("partial_stats_phase21_gva_forecast_archive.csv")
    assert archive["archive_status"].eq("frozen_waiting_release").all()
    assert archive["one_shot_consumed"].eq("false").all()


def test_phase21_current_outputs_report_and_topic_index() -> None:
    nowcast = read_csv("partial_stats_phase21_gva_quarterly_nowcast_2026.csv")
    assert nowcast["actual_used"].eq("N").all()
    annual = read_csv("partial_stats_phase21_gva_annual_from_quarters_2026.csv")
    assert annual["actual_used"].eq("N").all()

    report = (ROOT / "reports" / "partial_statistics_estimation_phase21_gva.md").read_text(encoding="utf-8")
    sections = [int(match.group(1)) for match in re.finditer(r"^## (\d+)\.", report, flags=re.MULTILINE)]
    assert sections == list(range(1, 46))
    assert "Official·Proxy Track 분리" in report
    assert "Prospective Forecast Archive" in report

    topic_index = (ROOT / "reports" / "topics" / "ml.md").read_text(encoding="utf-8")
    assert "partial_statistics_estimation_phase21_gva.md" in topic_index
    assert "Official quarterly GRDP materialization" in topic_index
