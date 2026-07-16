from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime
from statistics import mean, median
from typing import Any

import numpy as np

from kosis_common import PROCESSED_DIR, ROOT, read_csv, write_csv
from run_electricity_vintage_dry_run import num


REPORT_PATH = ROOT / "reports" / "electricity_only_policy_closure_and_next_workstreams.md"
CLOSURE_MANIFEST_PATH = PROCESSED_DIR / "electricity_policy_closure_manifest.json"
CONFIRMATORY_MANIFEST_PATH = PROCESSED_DIR / "electricity_confirmatory_challenger_manifest.json"


FEATURE_COLUMNS = [
    "electricity_total_kwh",
    "electricity_industrial_kwh",
    "electricity_commercial_kwh",
    "industrial_share",
    "commercial_share",
    "log_total_kwh",
    "log_industrial_kwh",
    "log_commercial_kwh",
]


def file_hash(path: Any) -> str:
    p = ROOT / path if isinstance(path, str) else path
    if not p.exists():
        return ""
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def variance(values: list[float]) -> float:
    return float(np.var(np.asarray(values, dtype=float), ddof=0)) if values else 0.0


def month_add(period: str, months: int) -> str:
    year = int(period[:4])
    month = int(period[4:6]) + months
    while month > 12:
        year += 1
        month -= 12
    while month < 1:
        year -= 1
        month += 12
    return f"{year}{month:02d}"


def load_monthly_panel() -> list[dict[str, Any]]:
    rows = read_csv(PROCESSED_DIR / "municipality_electricity_asof_long.csv")
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        period = str(row.get("observation_period", ""))
        if not ("202001" <= period <= "202312"):
            continue
        key = (row["sigungu_feature_key"], period)
        old = selected.get(key)
        candidate_key = (row.get("selected_publication_date", ""), row.get("selected_source_vintage", ""))
        old_key = (old.get("selected_publication_date", ""), old.get("selected_source_vintage", "")) if old else ("", "")
        if old is None or candidate_key > old_key:
            selected[key] = row
    out = []
    for (feature_key, period), row in sorted(selected.items()):
        total = max(num(row.get("electricity_total_kwh")), 0.0)
        industrial = max(num(row.get("electricity_industrial_kwh")), 0.0)
        commercial = max(num(row.get("electricity_commercial_kwh")), 0.0)
        out.append(
            {
                "sigungu_feature_key": feature_key,
                "observation_period": period,
                "electricity_total_kwh": total,
                "electricity_industrial_kwh": industrial,
                "electricity_commercial_kwh": commercial,
                "industrial_share": industrial / total if total else 0.0,
                "commercial_share": commercial / total if total else 0.0,
                "log_total_kwh": math.log1p(total),
                "log_industrial_kwh": math.log1p(industrial),
                "log_commercial_kwh": math.log1p(commercial),
            }
        )
    return out


def between_within(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_region = defaultdict(list)
    for row in rows:
        by_region[row["sigungu_feature_key"]].append(row)
    scale_by_region = {
        region: mean([float(r["electricity_total_kwh"]) for r in items])
        for region, items in by_region.items()
    }
    between_rows = []
    autocorr_rows = []
    diagnostics = []
    for feature in FEATURE_COLUMNS:
        all_values = [float(r[feature]) for r in rows]
        total_var = variance(all_values)
        region_means = {region: mean([float(r[feature]) for r in items]) for region, items in by_region.items()}
        region_vars = {region: variance([float(r[feature]) for r in items]) for region, items in by_region.items()}
        overall_mean = mean(all_values) if all_values else 0.0
        total_n = len(all_values)
        between_var = (
            sum(len(by_region[region]) * (region_means[region] - overall_mean) ** 2 for region in region_means) / total_n
            if total_n
            else 0.0
        )
        within_var = (
            sum(len(by_region[region]) * region_vars[region] for region in region_vars) / total_n
            if total_n
            else 0.0
        )
        ratio = between_var / total_var if total_var else 0.0
        scale_corr = corr(list(region_means.values()), [scale_by_region[r] for r in region_means])
        yoy_values = []
        lag1_corrs = []
        lag12_corrs = []
        for region, items in by_region.items():
            item_by_period = {r["observation_period"]: r for r in items}
            periods = sorted(item_by_period)
            lag1_x, lag1_y, lag12_x, lag12_y = [], [], [], []
            for period in periods:
                value = float(item_by_period[period][feature])
                p1 = month_add(period, -1)
                p12 = month_add(period, -12)
                if p1 in item_by_period:
                    lag1_x.append(float(item_by_period[p1][feature]))
                    lag1_y.append(value)
                if p12 in item_by_period:
                    prev = float(item_by_period[p12][feature])
                    lag12_x.append(prev)
                    lag12_y.append(value)
                    if abs(prev) > 1e-9:
                        yoy_values.append(value / prev - 1.0)
            c1 = corr(lag1_x, lag1_y)
            c12 = corr(lag12_x, lag12_y)
            if c1 is not None:
                lag1_corrs.append(c1)
            if c12 is not None:
                lag12_corrs.append(c12)
        yoy_var = variance(yoy_values)
        autocorr_rows.append(
            {
                "feature": feature,
                "region_count": len(by_region),
                "mean_autocorrelation_lag1": round(mean(lag1_corrs), 6) if lag1_corrs else "",
                "median_autocorrelation_lag1": round(median(lag1_corrs), 6) if lag1_corrs else "",
                "mean_autocorrelation_lag12": round(mean(lag12_corrs), 6) if lag12_corrs else "",
                "median_autocorrelation_lag12": round(median(lag12_corrs), 6) if lag12_corrs else "",
                "year_over_year_variance": round(yoy_var, 10),
            }
        )
        between_rows.append(
            {
                "feature": feature,
                "observation_count": len(all_values),
                "region_count": len(by_region),
                "total_variance": round(total_var, 10),
                "between_region_variance": round(between_var, 10),
                "within_region_variance": round(within_var, 10),
                "between_to_total_ratio": round(ratio, 6),
                "mean_region_scale_correlation": round(scale_corr, 6) if scale_corr is not None else "",
            }
        )
        diagnostics.append(
            {
                "feature": feature,
                "between_to_total_ratio": round(ratio, 6),
                "within_to_total_ratio": round(within_var / total_var, 6) if total_var else 0.0,
                "mean_autocorrelation_lag1": autocorr_rows[-1]["mean_autocorrelation_lag1"],
                "mean_autocorrelation_lag12": autocorr_rows[-1]["mean_autocorrelation_lag12"],
                "year_over_year_variance": round(yoy_var, 10),
                "interpretation": "mostly_cross_sectional_scale_or_structure" if ratio >= 0.70 else "contains_material_within_region_temporal_signal",
            }
        )
    return between_rows, autocorr_rows, diagnostics


def source_status_rows() -> list[dict[str, Any]]:
    return [
        {
            "workstream": "factory_registration",
            "priority": 1,
            "target_sectors": "C00",
            "status": "not_yet_ml_ready",
            "required_fields": "sigungu_code, industry_code, factory_status, registration_date, closure_date, employee_count, site_area, building_area",
            "publication_lag_status": "unknown_requires_source_audit",
            "next_action": "FactoryOn and local-government file routes; verify historical reconstruction",
        },
        {
            "workstream": "industrial_complex_activity",
            "priority": 2,
            "target_sectors": "C00",
            "status": "not_yet_ml_ready",
            "required_fields": "operating_company_count, employment, production, exports, utilization_rate, industrial_facility_area",
            "publication_lag_status": "unknown_requires_source_audit",
            "next_action": "Collect quarterly complex files, standardize complex codes, build sigungu allocation rule",
        },
        {
            "workstream": "building_permits_and_starts",
            "priority": 3,
            "target_sectors": "F00,L00",
            "status": "not_yet_ml_ready",
            "required_fields": "permit/start/approval event date, sigungu, use code, floor area",
            "publication_lag_status": "unknown_requires_source_audit",
            "next_action": "Confirm BuildingHub bulk/API access and event classification",
        },
        {
            "workstream": "electricity_pipeline",
            "priority": 0,
            "target_sectors": "research_context",
            "status": "active_data_pipeline_inactive_ml_correction",
            "required_fields": "source manifest, hash, publication date, vintage, crosswalk, schema fingerprint",
            "publication_lag_status": "implemented_for_current_historical_source",
            "next_action": "Continue monthly collection and schema/quality audits",
        },
    ]


def load_key_results() -> dict[str, Any]:
    comparison = read_csv(PROCESSED_DIR / "electricity_r2_r3b_comparison.csv")
    metrics = [r for r in comparison if r.get("wmape") and r.get("policy") in {"R2_all_only_trainalpha_B6_rel5", "R3b_all_only_conservative_B4_rel5"} and r.get("count")]
    gates = []
    manifest_path = PROCESSED_DIR / "electricity_confirmatory_challenger_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        gates = manifest.get("gate_results", [])
    placebo = read_csv(PROCESSED_DIR / "electricity_r2_r3b_placebo.csv")
    selection = read_csv(PROCESSED_DIR / "electricity_r2_r3b_selection_aware_bootstrap.csv")
    return {"metrics": metrics, "gates": gates, "placebo": placebo, "selection": selection}


def write_manifests(diagnostics: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> None:
    key = load_key_results()
    closure = {
        "experiment_status": "closed_no_confirmatory_challenger",
        "decision": "retain_global",
        "champion": "global",
        "challenger": None,
        "challenger_status": "none_selected",
        "selection_reason": "no_candidate_passed_all_preconfirmatory_gates",
        "electricity_only_result": "insufficient_preconfirmatory_evidence",
        "production_replacement": False,
        "same_actual_retuning_allowed": False,
        "development_actual_period": "2022-2023",
        "confirmatory_test_status": "not_applicable_without_frozen_challenger",
        "electricity_feature_pipeline": "retained_active",
        "electricity_prediction_correction": "disabled",
        "electricity_research_status": "available_for_future_combined_model",
        "frozen_code_commit_hash": git_hash(),
        "recommended_tag": "electricity-only-preconfirmatory-closed-v1",
        "random_seed": 20260716,
        "input_hashes": {
            "municipality_electricity_asof_long.csv": file_hash(PROCESSED_DIR / "municipality_electricity_asof_long.csv"),
            "municipality_electricity_asof_features.csv": file_hash(PROCESSED_DIR / "municipality_electricity_asof_features.csv"),
            "electricity_r2_r3b_comparison.csv": file_hash(PROCESSED_DIR / "electricity_r2_r3b_comparison.csv"),
            "electricity_r2_r3b_placebo.csv": file_hash(PROCESSED_DIR / "electricity_r2_r3b_placebo.csv"),
            "electricity_r2_r3b_selection_aware_bootstrap.csv": file_hash(PROCESSED_DIR / "electricity_r2_r3b_selection_aware_bootstrap.csv"),
        },
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    CLOSURE_MANIFEST_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")

    confirmatory = {}
    if CONFIRMATORY_MANIFEST_PATH.exists():
        confirmatory = json.loads(CONFIRMATORY_MANIFEST_PATH.read_text(encoding="utf-8"))
    confirmatory.update(
        {
            "champion": "global",
            "challenger": None,
            "confirmatory_challenger": "none",
            "challenger_status": "none_selected",
            "selection_reason": "no_candidate_passed_all_preconfirmatory_gates",
            "production_replacement": False,
            "same_actual_retuning_allowed": False,
            "development_actual_period": "2022-2023",
            "confirmatory_test_status": "not_applicable_without_frozen_challenger",
            "electricity_only_policy_status": "research_candidate_only",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    CONFIRMATORY_MANIFEST_PATH.write_text(json.dumps(confirmatory, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(diagnostics: list[dict[str, Any]], between_rows: list[dict[str, Any]], autocorr_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> None:
    key = load_key_results()
    selection_prob = next((r.get("probability_of_improvement") for r in key["selection"] if r.get("probability_of_improvement")), "")
    lines = [
        "# 전력 단독 정책 종료 및 다음 Workstream",
        "",
        "## 최종 종료 결정",
        "",
        "- experiment_status: `closed_no_confirmatory_challenger`",
        "- champion: `global`",
        "- confirmatory_challenger: `none`",
        "- electricity_only_policy_status: `research_candidate_only`",
        "- production_replacement: `prohibited`",
        "- same_actual_retuning_allowed: `false`",
        "",
        "R2와 R3b는 pooled WMAPE, tail stability, LOSO, large-observation removal에서 일부 긍정적 신호를 보였지만, 사전 Gate 전체를 통과하지 못했다. 따라서 전력 단독 residual correction 정책은 종료하고, 전력 데이터는 향후 구조 Feature 결합용으로만 보존한다.",
        "",
        "## R2 및 R3b Gate 실패 사유",
        "",
        "| policy | gate | pass | note |",
        "| --- | --- | --- | --- |",
    ]
    for row in key["gates"]:
        lines.append(f"| {row.get('policy')} | {row.get('gate')} | {row.get('pass')} | {row.get('note')} |")
    lines.extend(["", "## 전력 Feature 결과 해석", "", "| policy | WMAPE | global WMAPE | delta +good | relative % | material | +5pp | +10pp |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for row in key["metrics"]:
        lines.append(f"| {row.get('policy')} | {row.get('wmape')} | {row.get('global_wmape_same_rows')} | {row.get('delta_positive_good')} | {row.get('relative_improvement_pct')} | {row.get('material_degradation_count')} | {row.get('ape_plus_5pp_count')} | {row.get('ape_plus_10pp_count')} |")
    lines.extend(["", "## 추가 튜닝 금지", "", "2022-2023 actual을 이용해 alpha, clipping, feature bundle, residual target, 지역별 적용 규칙, R2/R3b 혼합 정책을 추가 탐색하지 않는다. 이는 사후 과적합으로 간주한다.", "", "## Temporal Signal 진단", "", f"- selection-aware P(improve): `{selection_prob}`", "- temporal placebo 실패는 모델 재튜닝 사유가 아니라 feature 성격 진단 대상으로 처리한다.", "", "| feature | between/total | within/total | lag1 autocorr | lag12 autocorr | yoy variance | interpretation |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"])
    for row in diagnostics:
        lines.append(f"| {row['feature']} | {row['between_to_total_ratio']} | {row['within_to_total_ratio']} | {row['mean_autocorrelation_lag1']} | {row['mean_autocorrelation_lag12']} | {row['year_over_year_variance']} | {row['interpretation']} |")
    lines.extend(["", "## Between/Within Variance", "", "| feature | total variance | between variance | within variance | between/total | scale corr |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for row in between_rows:
        lines.append(f"| {row['feature']} | {row['total_variance']} | {row['between_region_variance']} | {row['within_region_variance']} | {row['between_to_total_ratio']} | {row['mean_region_scale_correlation']} |")
    lines.extend(["", "## Autocorrelation Audit", "", "| feature | lag1 mean | lag12 mean | yoy variance |", "| --- | ---: | ---: | ---: |"])
    for row in autocorr_rows:
        lines.append(f"| {row['feature']} | {row['mean_autocorrelation_lag1']} | {row['mean_autocorrelation_lag12']} | {row['year_over_year_variance']} |")
    lines.extend(
        [
            "",
            "## 전력 Pipeline 유지계획",
            "",
            "- data pipeline: `active`",
            "- ML correction policy: `inactive`",
            "- monthly source manifest, file hash, publication date, source vintage, region crosswalk, schema fingerprint, duplicate key, negative value, publication lag drift를 계속 점검한다.",
            "",
            "## 다음 Feature Source Workstreams",
            "",
            "| workstream | priority | status | target sectors | next action |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for row in source_rows:
        lines.append(f"| {row['workstream']} | {row['priority']} | {row['status']} | {row['target_sectors']} | {row['next_action']} |")
    lines.extend(
        [
            "",
            "## 차기 ML 재개 Gate",
            "",
            "- C00: factory registration 또는 industrial complex activity가 ML-ready이고 시군구 coverage가 90% 이상이며 first eligible period가 구현된 뒤 재개한다.",
            "- all: building activity, business openings/closures, employment, card sales, foot traffic 중 하나 이상의 신규 source가 ML-ready일 때 재개한다.",
            "- D00: 별도 직접 Feature가 확보될 때까지 global fallback을 유지한다.",
            "",
            "## 미사용 Actual 관리원칙",
            "",
            "confirmatory challenger가 없으므로 2024 이후 official actual로 R2/R3b를 자동 평가하지 않는다. 향후 actual은 결합 정책이 actual 공개 전에 완전히 동결된 경우에만 confirmatory로 사용하고, 그렇지 않으면 development_extension으로 명시해 confirmatory 자격을 포기한다.",
            "",
            "## 산출물",
            "",
            "- `data/processed/electricity_policy_closure_manifest.json`",
            "- `data/processed/electricity_temporal_signal_diagnostics.csv`",
            "- `data/processed/electricity_between_within_variance.csv`",
            "- `data/processed/electricity_autocorrelation_audit.csv`",
            "- `data/processed/next_feature_source_status.csv`",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    monthly = load_monthly_panel()
    between_rows, autocorr_rows, diagnostics = between_within(monthly)
    source_rows = source_status_rows()
    write_csv(PROCESSED_DIR / "electricity_between_within_variance.csv", between_rows)
    write_csv(PROCESSED_DIR / "electricity_autocorrelation_audit.csv", autocorr_rows)
    write_csv(PROCESSED_DIR / "electricity_temporal_signal_diagnostics.csv", diagnostics)
    write_csv(PROCESSED_DIR / "next_feature_source_status.csv", source_rows)
    write_manifests(diagnostics, source_rows)
    write_report(diagnostics, between_rows, autocorr_rows, source_rows)
    print(f"monthly rows: {len(monthly)}")
    print(f"features diagnosed: {len(diagnostics)}")
    print(f"report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
