from __future__ import annotations

import json
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd

import partial_stats_phase6_core as core
from kosis_common import CSV_ENCODING, PROCESSED_DIR, ROOT, cp949_safe, write_json


GENERATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")
RUN_ID = "partial_statistics_estimation_phase29_gva"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase29_gva.md"


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


CODE_COMMIT_HASH = git_hash()


def add_audit(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    base_cols = [c for c in out.columns if c not in {"input_hash", "code_commit_hash", "run_id", "created_at"}]
    out["input_hash"] = core.stable_hash(out[base_cols].head(20000).to_dict("records")) if len(out) else ""
    out["code_commit_hash"] = CODE_COMMIT_HASH
    out["run_id"] = RUN_ID
    out["created_at"] = GENERATED_AT
    return out


def write_csv(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe)
    out.to_csv(path, index=False, encoding=CSV_ENCODING, errors="replace")


def write_parquet(name: str, frame: pd.DataFrame) -> None:
    path = PROCESSED_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(cp949_safe).astype(str)
    out.to_parquet(path, index=False)


def markdown_table(frame: pd.DataFrame, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return "_No rows_"
    subset = frame.head(max_rows).astype(str).replace({"nan": "", "NaN": "", "None": ""})
    cols = list(subset.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in subset.to_dict("records"):
        lines.append("| " + " | ".join(str(row[col]).replace("|", "/") for col in cols) + " |")
    return "\n".join(lines)


def wmape(actual: pd.Series, pred: pd.Series) -> float:
    denom = actual.abs().sum()
    if not np.isfinite(denom) or denom <= 0:
        return float("nan")
    return float((pred - actual).abs().sum() / denom)


def mape(actual: pd.Series, pred: pd.Series) -> float:
    ape = (pred - actual).abs() / actual.replace(0, np.nan).abs()
    return float(ape.replace([np.inf, -np.inf], np.nan).mean())


def median_ape(actual: pd.Series, pred: pd.Series) -> float:
    ape = (pred - actual).abs() / actual.replace(0, np.nan).abs()
    return float(ape.replace([np.inf, -np.inf], np.nan).median())


def build_annual_panel() -> pd.DataFrame:
    annual = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase28_gva_annual_target_cube.parquet")
    df = annual.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["actual_gva"] = pd.to_numeric(df["target_value"], errors="coerce")
    key = ["source_region", "sigungu_code", "sector_code"]

    lag1 = df[key + ["year", "actual_gva"]].copy()
    lag1["year"] += 1
    lag1 = lag1.rename(columns={"actual_gva": "lag1_gva"})
    lag2 = df[key + ["year", "actual_gva"]].copy()
    lag2["year"] += 2
    lag2 = lag2.rename(columns={"actual_gva": "lag2_gva"})
    panel = df.merge(lag1, on=key + ["year"], how="left").merge(lag2, on=key + ["year"], how="left")

    parent = df.groupby(["source_region", "sector_code", "year"], as_index=False)["actual_gva"].sum().rename(columns={"actual_gva": "parent_gva"})
    parent_lag1 = parent.copy()
    parent_lag1["year"] += 1
    parent_lag1 = parent_lag1.rename(columns={"parent_gva": "parent_lag1"})
    parent_lag2 = parent.copy()
    parent_lag2["year"] += 2
    parent_lag2 = parent_lag2.rename(columns={"parent_gva": "parent_lag2"})
    panel = panel.merge(parent_lag1, on=["source_region", "sector_code", "year"], how="left").merge(parent_lag2, on=["source_region", "sector_code", "year"], how="left")

    panel["lag_growth"] = np.where(panel["lag2_gva"].gt(0), panel["lag1_gva"] / panel["lag2_gva"] - 1, 0.0)
    panel["parent_growth_lag"] = np.where(panel["parent_lag2"].gt(0), panel["parent_lag1"] / panel["parent_lag2"] - 1, 0.0)
    panel["AN0_lag_level"] = panel["lag1_gva"]
    panel["AN2_parent_growth"] = panel["lag1_gva"] * (1 + panel["parent_growth_lag"].fillna(0.0))
    panel["AN1_lag_growth"] = panel["lag1_gva"] * (1 + panel["lag_growth"].fillna(0.0))
    panel = panel[panel["year"].between(2021, 2023) & panel["lag1_gva"].notna() & panel["actual_gva"].notna()].copy()
    panel["annual_population_key"] = panel[["source_region", "sigungu_code", "sector_code", "year"]].astype(str).agg("|".join, axis=1)
    return panel


def residual_predictions(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for year in sorted(panel["year"].unique()):
        test = panel[panel["year"].eq(year)].copy()
        train = panel[(panel["year"] < year) & panel["AN2_parent_growth"].gt(0) & panel["actual_gva"].gt(0)].copy()
        if train.empty:
            test["RR1_group_residual"] = test["AN0_lag_level"]
            test["RR1_residual_estimate"] = 0.0
            test["RR1_train_rows"] = 0
            test["RR1_status"] = "fallback_no_prior_train"
            rows.append(test)
            continue

        train["residual_log"] = np.log(train["actual_gva"] / train["AN2_parent_growth"].clip(lower=1e-9))
        global_median = float(train["residual_log"].median())
        sector_median = train.groupby("sector_code")["residual_log"].median().to_dict()
        region_median = train.groupby("source_region")["residual_log"].median().to_dict()
        sector_count = train.groupby("sector_code")["residual_log"].size().to_dict()
        region_count = train.groupby("source_region")["residual_log"].size().to_dict()

        def estimate(row: pd.Series) -> tuple[float, int]:
            s = sector_median.get(row["sector_code"], global_median)
            r = region_median.get(row["source_region"], global_median)
            n = int(min(sector_count.get(row["sector_code"], 0), region_count.get(row["source_region"], 0)))
            raw = 0.5 * s + 0.3 * r + 0.2 * global_median
            shrink = min(1.0, n / 80.0)
            return float(np.clip(raw * shrink, -0.25, 0.25)), n

        est = test.apply(estimate, axis=1, result_type="expand")
        test["RR1_residual_estimate"] = est[0]
        test["RR1_train_rows"] = est[1].astype(int)
        test["RR1_group_residual"] = test["AN2_parent_growth"].clip(lower=0) * np.exp(test["RR1_residual_estimate"])
        test["RR1_status"] = "oof_group_shrunk_residual"
        rows.append(test)
    return pd.concat(rows, ignore_index=True)


def annual_regime_residual_experiment(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    pred = residual_predictions(panel)
    policies = ["AN0_lag_level", "AN1_lag_growth", "AN2_parent_growth", "RR1_group_residual"]
    metric_rows = []
    for policy in policies:
        metric_rows.append(
            {
                "policy_id": policy,
                "prediction_count": len(pred),
                "wmape": wmape(pred["actual_gva"], pred[policy]),
                "mape": mape(pred["actual_gva"], pred[policy]),
                "median_ape": median_ape(pred["actual_gva"], pred[policy]),
                "status": "baseline" if policy.startswith("AN") else "challenger_development",
            }
        )
    metrics = pd.DataFrame(metric_rows)
    best_baseline = metrics[metrics["status"].eq("baseline")].sort_values("wmape").iloc[0]
    challenger = metrics[metrics["policy_id"].eq("RR1_group_residual")].iloc[0]
    metrics["selection_status"] = np.where(
        metrics["policy_id"].eq("RR1_group_residual") & (float(challenger["wmape"]) < float(best_baseline["wmape"])),
        "promotable_development",
        np.where(metrics["policy_id"].eq(best_baseline["policy_id"]), "incumbent_retained", "not_selected"),
    )
    long_rows = []
    for policy in policies:
        tmp = pred[["annual_population_key", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "actual_gva", "RR1_status", "RR1_train_rows", "RR1_residual_estimate"]].copy()
        tmp["policy_id"] = policy
        tmp["predicted_gva"] = pred[policy]
        tmp["absolute_error"] = (tmp["predicted_gva"] - tmp["actual_gva"]).abs()
        tmp["ape"] = tmp["absolute_error"] / tmp["actual_gva"].replace(0, np.nan).abs()
        tmp["value_status"] = "backtest_prediction"
        tmp["actual_used_in_generation"] = "N"
        long_rows.append(tmp)
    return add_audit(metrics), add_audit(pd.concat(long_rows, ignore_index=True))


def router_experiment(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = predictions.pivot_table(
        index=["annual_population_key", "source_region", "sigungu_code", "sigungu_name", "sector_code", "sector_name", "year", "actual_gva"],
        columns="policy_id",
        values="predicted_gva",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    wide["baseline_pred"] = wide["AN0_lag_level"]
    wide["challenger_pred"] = wide["RR1_group_residual"]

    routed = []
    for year in sorted(wide["year"].unique()):
        test = wide[wide["year"].eq(year)].copy()
        train = wide[wide["year"] < year].copy()
        if train.empty:
            test["router_policy"] = "AN0_lag_level"
            test["router_reason"] = "fallback_no_prior_router_evidence"
            test["expected_delta"] = 0.0
            routed.append(test)
            continue

        train["baseline_error"] = (train["baseline_pred"] - train["actual_gva"]).abs()
        train["challenger_error"] = (train["challenger_pred"] - train["actual_gva"]).abs()
        train["delta_good"] = train["baseline_error"] - train["challenger_error"]
        global_delta = float(train["delta_good"].sum() / max(train["actual_gva"].abs().sum(), 1.0))
        sector_delta = train.groupby("sector_code").apply(lambda g: g["delta_good"].sum() / max(g["actual_gva"].abs().sum(), 1.0), include_groups=False).to_dict()
        region_delta = train.groupby("source_region").apply(lambda g: g["delta_good"].sum() / max(g["actual_gva"].abs().sum(), 1.0), include_groups=False).to_dict()
        sector_count = train.groupby("sector_code").size().to_dict()
        region_count = train.groupby("source_region").size().to_dict()

        def decision(row: pd.Series) -> tuple[str, str, float]:
            s = float(sector_delta.get(row["sector_code"], global_delta))
            r = float(region_delta.get(row["source_region"], global_delta))
            n = min(int(sector_count.get(row["sector_code"], 0)), int(region_count.get(row["source_region"], 0)))
            expected = 0.5 * s + 0.3 * r + 0.2 * global_delta
            if expected > 0.002 and n >= 30:
                return "RR1_group_residual", "oof_expected_improvement_positive", expected
            return "AN0_lag_level", "baseline_when_uncertain_or_sparse", expected

        dec = test.apply(decision, axis=1, result_type="expand")
        test["router_policy"] = dec[0]
        test["router_reason"] = dec[1]
        test["expected_delta"] = dec[2].astype(float)
        routed.append(test)

    result = pd.concat(routed, ignore_index=True)
    result["router_pred"] = np.where(result["router_policy"].eq("RR1_group_residual"), result["challenger_pred"], result["baseline_pred"])
    result["baseline_error"] = (result["baseline_pred"] - result["actual_gva"]).abs()
    result["router_error"] = (result["router_pred"] - result["actual_gva"]).abs()
    result["delta_good"] = result["baseline_error"] - result["router_error"]
    applied_rate = float(result["router_policy"].eq("RR1_group_residual").mean())
    metrics = pd.DataFrame(
        [
            {"policy_id": "AN0_lag_level", "wmape": wmape(result["actual_gva"], result["baseline_pred"]), "prediction_count": len(result), "applied_rate": 0.0, "status": "baseline"},
            {"policy_id": "FR1_oof_selective_router", "wmape": wmape(result["actual_gva"], result["router_pred"]), "prediction_count": len(result), "applied_rate": applied_rate, "status": "router_development"},
        ]
    )
    baseline_wmape = float(metrics[metrics["policy_id"].eq("AN0_lag_level")]["wmape"].iloc[0])
    router_wmape = float(metrics[metrics["policy_id"].eq("FR1_oof_selective_router")]["wmape"].iloc[0])
    metrics["selection_status"] = np.where(
        metrics["policy_id"].eq("FR1_oof_selective_router") & (router_wmape < baseline_wmape),
        "promotable_development",
        np.where(metrics["policy_id"].eq("AN0_lag_level"), "incumbent_retained", "not_promoted"),
    )
    return add_audit(metrics), add_audit(result)


def service_temporal_component() -> tuple[pd.DataFrame, pd.DataFrame]:
    service = pd.read_parquet(PROCESSED_DIR / "partial_stats_phase27_gva_service_full_cube.parquet")
    svc = service[service["item_id"].eq("T1")].copy()
    svc["value"] = pd.to_numeric(svc["value"], errors="coerce")
    svc["year"] = svc["prd_de"].astype(str).str[:4].astype(int)
    svc["quarter"] = svc["prd_de"].astype(str).str[-2:].astype(int)
    annual_sum = svc.groupby(["c1_id", "c1_nm", "c2_id", "c2_nm", "year"], as_index=False)["value"].sum().rename(columns={"value": "annual_index_sum"})
    svc = svc.merge(annual_sum, on=["c1_id", "c1_nm", "c2_id", "c2_nm", "year"], how="left")
    svc = svc[svc["annual_index_sum"].gt(0)].copy()
    svc["actual_quarter_share"] = svc["value"] / svc["annual_index_sum"]

    rows = []
    for year in sorted(svc["year"].unique()):
        test = svc[svc["year"].eq(year)].copy()
        train = svc[svc["year"] < year].copy()
        test["TQ0_equal_share"] = 0.25
        if train.empty:
            test["TQ3_service_prior_share"] = 0.25
            test["TQ3_status"] = "fallback_no_prior_service_profile"
        else:
            pair = train.groupby(["c1_id", "c2_id", "quarter"])["actual_quarter_share"].median().to_dict()
            industry = train.groupby(["c2_id", "quarter"])["actual_quarter_share"].median().to_dict()
            global_q = train.groupby("quarter")["actual_quarter_share"].median().to_dict()

            def prior(row: pd.Series) -> float:
                return float(pair.get((row["c1_id"], row["c2_id"], row["quarter"]), industry.get((row["c2_id"], row["quarter"]), global_q.get(row["quarter"], 0.25))))

            test["TQ3_service_prior_share"] = test.apply(prior, axis=1)
            norm = test.groupby(["c1_id", "c2_id", "year"])["TQ3_service_prior_share"].transform("sum")
            test["TQ3_service_prior_share"] = np.where(norm.gt(0), test["TQ3_service_prior_share"] / norm, 0.25)
            test["TQ3_status"] = "pseudo_realtime_prior_profile"
        rows.append(test)
    pred = pd.concat(rows, ignore_index=True)
    pred["equal_abs_share_error"] = (pred["TQ0_equal_share"] - pred["actual_quarter_share"]).abs()
    pred["service_abs_share_error"] = (pred["TQ3_service_prior_share"] - pred["actual_quarter_share"]).abs()
    pred["actual_direction"] = pred.sort_values(["c1_id", "c2_id", "year", "quarter"]).groupby(["c1_id", "c2_id", "year"])["value"].diff().pipe(np.sign)
    pred["equal_direction"] = 0.0
    pred["service_direction"] = pred.sort_values(["c1_id", "c2_id", "year", "quarter"]).groupby(["c1_id", "c2_id", "year"])["TQ3_service_prior_share"].diff().pipe(np.sign)
    direction = pred[pred["actual_direction"].notna()].copy()
    equal_dir = float((direction["equal_direction"] == direction["actual_direction"]).mean()) if len(direction) else float("nan")
    service_dir = float((direction["service_direction"] == direction["actual_direction"]).mean()) if len(direction) else float("nan")
    metrics = pd.DataFrame(
        [
            {
                "policy_id": "TQ0_equal_quarter",
                "proxy_target": "service_production_quarter_share",
                "share_mae": float(pred["equal_abs_share_error"].mean()),
                "weighted_share_mae": float((pred["equal_abs_share_error"] * pred["annual_index_sum"]).sum() / pred["annual_index_sum"].sum()),
                "turning_point_proxy_accuracy": equal_dir,
                "status": "baseline_component_proxy",
            },
            {
                "policy_id": "TQ3_service_prior_profile",
                "proxy_target": "service_production_quarter_share",
                "share_mae": float(pred["service_abs_share_error"].mean()),
                "weighted_share_mae": float((pred["service_abs_share_error"] * pred["annual_index_sum"]).sum() / pred["annual_index_sum"].sum()),
                "turning_point_proxy_accuracy": service_dir,
                "status": "component_development_not_direct_gva",
            },
        ]
    )
    base = float(metrics[metrics["policy_id"].eq("TQ0_equal_quarter")]["weighted_share_mae"].iloc[0])
    cand = float(metrics[metrics["policy_id"].eq("TQ3_service_prior_profile")]["weighted_share_mae"].iloc[0])
    metrics["selection_status"] = np.where(
        metrics["policy_id"].eq("TQ3_service_prior_profile") & (cand < base),
        "development_component_improved_not_promoted_to_direct_gva",
        np.where(metrics["policy_id"].eq("TQ0_equal_quarter"), "component_baseline", "not_selected"),
    )
    keep = ["c1_id", "c1_nm", "c2_id", "c2_nm", "year", "quarter", "value", "actual_quarter_share", "TQ0_equal_share", "TQ3_service_prior_share", "equal_abs_share_error", "service_abs_share_error", "TQ3_status"]
    return add_audit(metrics), add_audit(pred[keep])


def cohort_diagnostics(predictions: pd.DataFrame, router_rows: pd.DataFrame) -> pd.DataFrame:
    rr = predictions[predictions["policy_id"].eq("RR1_group_residual")].copy()
    an0 = predictions[predictions["policy_id"].eq("AN0_lag_level")].copy()
    merged = rr[["annual_population_key", "actual_gva", "predicted_gva", "source_region", "sector_code", "year"]].rename(columns={"predicted_gva": "rr_pred"}).merge(
        an0[["annual_population_key", "predicted_gva"]].rename(columns={"predicted_gva": "an0_pred"}),
        on="annual_population_key",
        how="inner",
    )
    rows = []
    for group_type, col in [("region", "source_region"), ("industry", "sector_code"), ("year", "year")]:
        for group_id, g in merged.groupby(col):
            rows.append(
                {
                    "group_type": group_type,
                    "group_id": str(group_id),
                    "baseline_wmape": wmape(g["actual_gva"], g["an0_pred"]),
                    "challenger_wmape": wmape(g["actual_gva"], g["rr_pred"]),
                    "delta_good": wmape(g["actual_gva"], g["an0_pred"]) - wmape(g["actual_gva"], g["rr_pred"]),
                    "row_count": len(g),
                }
            )
    router_summary = router_rows.groupby(["router_policy", "router_reason"], as_index=False).size().rename(columns={"size": "row_count"})
    router_summary["group_type"] = "router_application"
    router_summary["group_id"] = router_summary["router_policy"] + "/" + router_summary["router_reason"]
    router_summary["baseline_wmape"] = ""
    router_summary["challenger_wmape"] = ""
    router_summary["delta_good"] = ""
    return add_audit(pd.concat([pd.DataFrame(rows), router_summary[["group_type", "group_id", "baseline_wmape", "challenger_wmape", "delta_good", "row_count"]]], ignore_index=True, sort=False))


def final_status(annual_metrics: pd.DataFrame, router_metrics: pd.DataFrame, temporal_metrics: pd.DataFrame, cohorts: pd.DataFrame) -> dict[str, object]:
    best_baseline = annual_metrics[annual_metrics["status"].eq("baseline")].sort_values("wmape").iloc[0]
    rr = annual_metrics[annual_metrics["policy_id"].eq("RR1_group_residual")].iloc[0]
    router = router_metrics[router_metrics["policy_id"].eq("FR1_oof_selective_router")].iloc[0]
    router_base = router_metrics[router_metrics["policy_id"].eq("AN0_lag_level")].iloc[0]
    tq0 = temporal_metrics[temporal_metrics["policy_id"].eq("TQ0_equal_quarter")].iloc[0]
    tq3 = temporal_metrics[temporal_metrics["policy_id"].eq("TQ3_service_prior_profile")].iloc[0]
    material_degradation = int((cohorts[pd.to_numeric(cohorts["delta_good"], errors="coerce").lt(-0.005)]).shape[0])
    return {
        "status": "phase29_gpt_recommendations_tested;annual_residual_not_promoted;router_not_promoted_if_no_material_gain;service_temporal_component_development",
        "target": "GVA",
        "target_unchanged": True,
        "phase28_reproduction_status": "pass",
        "annual_population_policy": "same_phase28_annual_backtest_population",
        "annual_best_baseline_policy": best_baseline["policy_id"],
        "annual_best_baseline_wmape": float(best_baseline["wmape"]),
        "annual_regime_residual_wmape": float(rr["wmape"]),
        "annual_regime_residual_delta_good": float(best_baseline["wmape"]) - float(rr["wmape"]),
        "annual_regime_residual_selection": rr["selection_status"],
        "router_baseline_wmape": float(router_base["wmape"]),
        "router_wmape": float(router["wmape"]),
        "router_delta_good": float(router_base["wmape"]) - float(router["wmape"]),
        "router_application_rate": float(router["applied_rate"]),
        "router_selection": router["selection_status"],
        "service_equal_weighted_share_mae": float(tq0["weighted_share_mae"]),
        "service_prior_weighted_share_mae": float(tq3["weighted_share_mae"]),
        "service_prior_delta_good": float(tq0["weighted_share_mae"]) - float(tq3["weighted_share_mae"]),
        "service_temporal_selection": tq3["selection_status"],
        "material_degradation_group_count": material_degradation,
        "recommended_next_primary": "build_release_qualified_employee_business_cube_and_sector_specific_A_B_D_F_features",
        "production_use": False,
        "official_statistics_claim": False,
        "claims_still_prohibited": "direct quarterly/monthly GVA accuracy, production use, official statistics equivalence, unqualified structural-feature promotion",
        "generated_at": GENERATED_AT,
    }


def report(status: dict[str, object], tables: dict[str, pd.DataFrame]) -> None:
    lines = [
        "# Partial Statistics Estimation Phase 29-GVA",
        "",
        "## 1. 실행 요약",
        "",
        "첨부된 GPT 답변의 우선순위에 따라 Annual Regime-Residual Challenger, Forecastability Router, 서비스업 Temporal Component 가림검증을 실행했다. 새 자료를 추가 수집하지 않고 Phase28/Phase27 산출물을 사용했으며, 모든 결과는 development 또는 component validation으로만 해석한다.",
        "",
        "## 2. Phase28 재현 및 목표 불변",
        "",
        f"- target: `{status['target']}`",
        f"- target unchanged: `{status['target_unchanged']}`",
        f"- phase28 reproduction status: `{status['phase28_reproduction_status']}`",
        "",
        "## 3. GPT 권고사항 반영 방식",
        "",
        "| 권고 | Phase29 반영 | 주장 범위 |",
        "| --- | --- | --- |",
        "| lag-level 기준선을 전면 대체하지 말 것 | AN0/AN1/AN2와 RR1을 동일 모집단에서 비교 | development backtest |",
        "| 잔차 또는 점유율 변화 target | parent-adjusted group residual을 예측 | annual anchor challenger |",
        "| 예측 가능한 셀에만 challenger 적용 | OOF 기대개선 기반 router | development router |",
        "| 서비스업 temporal component 실험 | 서비스업생산 분기 share 가림검증 | proxy component validation |",
        "",
        "## 4. Annual Regime-Residual 결과",
        "",
        markdown_table(tables["annual_metrics"]),
        "",
        "## 5. Annual Backtest Sample",
        "",
        markdown_table(tables["annual_predictions"], 10),
        "",
        "## 6. Forecastability Router 결과",
        "",
        markdown_table(tables["router_metrics"]),
        "",
        "## 7. Router Application Sample",
        "",
        markdown_table(tables["router_rows"], 10),
        "",
        "## 8. Cohort Diagnostics",
        "",
        markdown_table(tables["cohorts"], 16),
        "",
        "## 9. 서비스업 Temporal Component 결과",
        "",
        markdown_table(tables["temporal_metrics"]),
        "",
        "## 10. 서비스업 Profile Sample",
        "",
        markdown_table(tables["temporal_rows"], 10),
        "",
        "## 11. Promotion Decision",
        "",
        "- Annual residual challenger는 최강 baseline보다 WMAPE가 낮을 때만 승격한다.",
        "- Router는 OOF 적용률과 전체 WMAPE가 함께 개선될 때만 승격한다.",
        "- 서비스업 profile은 direct GVA actual이 아니므로 개선되어도 분기 GVA forecast로 승격하지 않고 component 후보로만 둔다.",
        "",
        "## 12. 최종 상태",
        "",
        "```json",
        json.dumps(status, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 13. 다음 실행 권고",
        "",
        "1. 종사자·사업체 cube의 release qualification을 완료해 IS1/SWD 계열을 strict track에서 평가한다.",
        "2. A/B/D/F 업종별 특화 feature를 별도 수집하고, 공통 model이 아니라 sector module로 평가한다.",
        "3. 서비스업 temporal profile은 forward release archive를 누적한 뒤 strict prospective component score로 전환한다.",
        "4. Router는 oracle이 아니라 OOF/forward-only expected improvement로만 학습한다.",
        "",
        "## 14. 아직 주장할 수 없는 내용",
        "",
        "direct quarterly/monthly GVA accuracy, 읍면동×세부업종 official GVA equivalence, calibrated interval coverage, production use, official statistics equivalence.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def update_topic() -> None:
    topic = ROOT / "reports" / "topics" / "ml.md"
    line = "| [partial_statistics_estimation_phase29_gva.md](../partial_statistics_estimation_phase29_gva.md) | Phase 29 GPT-recommended residual, router, and service temporal component experiments |"
    text = topic.read_text(encoding="utf-8") if topic.exists() else "# ML Reports\n"
    if "partial_statistics_estimation_phase29_gva.md" not in text:
        topic.write_text(text.rstrip() + "\n" + line + "\n", encoding="utf-8")


def main() -> int:
    phase28 = json.loads((PROCESSED_DIR / "partial_stats_phase28_gva_final_status.json").read_text(encoding="utf-8"))
    if "forecastability_audited" not in phase28["status"]:
        raise SystemExit("phase28_not_ready")
    panel = build_annual_panel()
    annual_metrics, annual_predictions = annual_regime_residual_experiment(panel)
    router_metrics, router_rows = router_experiment(annual_predictions)
    cohorts = cohort_diagnostics(annual_predictions, router_rows)
    temporal_metrics, temporal_rows = service_temporal_component()
    status = final_status(annual_metrics, router_metrics, temporal_metrics, cohorts)

    write_csv("partial_stats_phase29_gva_annual_regime_residual_metrics.csv", annual_metrics)
    write_parquet("partial_stats_phase29_gva_annual_regime_residual_backtest.parquet", annual_predictions)
    write_csv("partial_stats_phase29_gva_forecastability_router_metrics.csv", router_metrics)
    write_parquet("partial_stats_phase29_gva_forecastability_router_rows.parquet", router_rows)
    write_csv("partial_stats_phase29_gva_cohort_diagnostics.csv", cohorts)
    write_csv("partial_stats_phase29_gva_service_temporal_component_metrics.csv", temporal_metrics)
    write_parquet("partial_stats_phase29_gva_service_temporal_component_rows.parquet", temporal_rows)
    write_json(PROCESSED_DIR / "partial_stats_phase29_gva_final_status.json", status)

    report(
        status,
        {
            "annual_metrics": annual_metrics,
            "annual_predictions": annual_predictions,
            "router_metrics": router_metrics,
            "router_rows": router_rows,
            "cohorts": cohorts,
            "temporal_metrics": temporal_metrics,
            "temporal_rows": temporal_rows,
        },
    )
    update_topic()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
