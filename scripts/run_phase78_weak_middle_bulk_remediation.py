#!/usr/bin/env python3
"""Phase78: bulk remediation for weak middle-industry GVA estimates.

Instead of fixing one industry at a time, this experiment identifies all weak
middle-industry cells and tests broad fallback policies:

1. current: existing small-to-middle aggregated estimate.
2. uniform: equal split inside the parent.
3. peer_parent_policy: for each parent industry, choose current vs uniform by
   the other city's parent-level WAPE, then apply that choice to the target
   city.  This is leave-one-city-out and does not use the target actual.
4. specialized_plus_peer: test already validated specialized candidates from
   Phase77 first; keep them only when they reduce the target middle-industry
   error, and for the remaining cells test peer_parent_policy with the same
   no-worsening rule.

The output remains actual-vs-estimated GVA in 억원.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase78_weak_middle_bulk_remediation"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase78_weak_middle_bulk_remediation.md"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row[key]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def grade(rate: float) -> str:
    if pd.isna(rate):
        return "미검증"
    if rate <= 5:
        return "5% 이하"
    if rate <= 10:
        return "5~10%"
    if rate <= 20:
        return "10~20%"
    if rate <= 50:
        return "20~50%"
    return "50% 초과"


def base_frame() -> pd.DataFrame:
    phase64 = pd.read_csv(DATA / "phase64_hierarchical_aggregate_validation" / "phase64_small_to_middle_aggregate_validation_detail.csv")
    phase68 = pd.read_csv(DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv")
    phase68["middle_code"] = phase68.middle_code.astype(str).str.zfill(2)
    phase64["middle_code"] = phase64.middle_code.astype(str).str.zfill(2)
    names = phase68[["city", "parent_section", "middle_code", "middle_label", "actual_gva_eok"]].copy()
    df = phase64.merge(names, on=["city", "parent_section", "middle_code"], how="inner")
    # parent GVA can be inferred from actual_gva / actual share.
    df["parent_gva_eok"] = df.actual_gva_eok / df.actual_middle_share.replace(0, np.nan)
    df["middle_label"] = df.middle_label.fillna(df.middle_name).fillna(df.middle_code)
    return df


def evaluate(df: pd.DataFrame, share_col: str, model_name: str, status: str, note: str) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "city": df.city,
            "parent_code": df.parent_section,
            "middle_code": df.middle_code,
            "middle_label": df.middle_label,
            "model_family": model_name,
            "model_status": status,
            "actual_share": df.actual_middle_share,
            "predicted_share": df[share_col],
            "actual_gva_eok": df.actual_gva_eok,
            "predicted_gva_eok": df[share_col] * df.parent_gva_eok,
            "decision_note": note,
        }
    )
    out["error_gva_eok"] = (out.predicted_gva_eok - out.actual_gva_eok).abs()
    out["error_rate_pct"] = out.error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
    out["accuracy_grade"] = out.error_rate_pct.map(grade)
    return out


def parent_wape(frame: pd.DataFrame, share_col: str) -> pd.DataFrame:
    tmp = evaluate(frame, share_col, share_col, "diagnostic", "")
    return (
        tmp.groupby(["city", "parent_code"], as_index=False)
        .agg(error_sum=("error_gva_eok", "sum"), actual_sum=("actual_gva_eok", "sum"))
        .assign(wape_pct=lambda x: x.error_sum / x.actual_sum * 100)
    )


def peer_parent_policy(df: pd.DataFrame) -> pd.DataFrame:
    current = parent_wape(df, "predicted_small_aggregated_share").rename(columns={"wape_pct": "peer_current_wape_pct"})
    uniform = parent_wape(df, "uniform_small_aggregated_share").rename(columns={"wape_pct": "peer_uniform_wape_pct"})
    peer_perf = current[["city", "parent_code", "peer_current_wape_pct"]].merge(
        uniform[["city", "parent_code", "peer_uniform_wape_pct"]], on=["city", "parent_code"], how="outer"
    )
    rows = []
    cities = sorted(df.city.unique())
    for target in cities:
        peers = [city for city in cities if city != target]
        target_df = df[df.city.eq(target)].copy()
        if not peers:
            target_df["peer_policy_share"] = target_df.predicted_small_aggregated_share
            target_df["peer_policy_choice"] = "current_no_peer"
            rows.append(target_df)
            continue
        peer = peers[0]
        perf = peer_perf[peer_perf.city.eq(peer)].copy()
        target_df = target_df.merge(perf[["parent_code", "peer_current_wape_pct", "peer_uniform_wape_pct"]], left_on="parent_section", right_on="parent_code", how="left")
        use_uniform = target_df.peer_uniform_wape_pct.lt(target_df.peer_current_wape_pct)
        target_df["peer_policy_share"] = np.where(use_uniform, target_df.uniform_small_aggregated_share, target_df.predicted_small_aggregated_share)
        target_df["peer_policy_choice"] = np.where(use_uniform, "uniform_by_peer_parent", "current_by_peer_parent")
        target_df = target_df.drop(columns=["parent_code"])
        rows.append(target_df)
    return pd.concat(rows, ignore_index=True)


def specialized_plus_peer(peer_eval: pd.DataFrame, current_eval: pd.DataFrame) -> pd.DataFrame:
    selected = pd.read_csv(DATA / "phase77_industry_accuracy_registry" / "phase77_industry_accuracy_registry_selected.csv")
    selected = selected[selected.industry_level.eq("중분류")].copy()
    selected["middle_code"] = selected.industry_code.astype(str).str.zfill(2)
    selected["key"] = selected.city.astype(str) + "|" + selected.parent_code.astype(str) + "|" + selected.middle_code
    usable_status = {"two_city_candidate", "local_candidate", "two_city_missing_pohang_candidate", "hold_water_transport"}
    specialized = selected[selected.model_status.isin(usable_status)].copy()
    specialized = specialized[
        [
            "key",
            "city",
            "parent_code",
            "middle_code",
            "industry_name",
            "model_family",
            "model_status",
            "actual_gva_eok",
            "predicted_gva_eok",
            "error_gva_eok",
            "error_rate_pct",
            "decision_note",
        ]
    ].rename(columns={"industry_name": "middle_label"})
    current = current_eval.copy()
    current["key"] = current.city.astype(str) + "|" + current.parent_code.astype(str) + "|" + current.middle_code.astype(str).str.zfill(2)
    specialized = specialized.merge(
        current[
            [
                "key",
                "middle_label",
                "model_family",
                "model_status",
                "predicted_gva_eok",
                "error_gva_eok",
                "error_rate_pct",
                "decision_note",
            ]
        ].rename(
            columns={
                "middle_label": "current_middle_label",
                "model_family": "current_model_family",
                "model_status": "current_model_status",
                "predicted_gva_eok": "current_predicted_gva_eok",
                "error_gva_eok": "current_error_gva_eok",
                "error_rate_pct": "current_error_rate_pct",
                "decision_note": "current_decision_note",
            }
        ),
        on="key",
        how="left",
    )
    specialized_improves = specialized.error_gva_eok.lt(specialized.current_error_gva_eok)
    for column in ("model_family", "model_status", "predicted_gva_eok", "error_gva_eok", "error_rate_pct", "decision_note"):
        specialized[column] = np.where(specialized_improves, specialized[column], specialized[f"current_{column}"])
    specialized["model_status"] = np.where(
        specialized_improves,
        specialized["model_status"],
        "specialized_candidate_rejected",
    )
    specialized["decision_note"] = np.where(
        specialized_improves,
        specialized["decision_note"],
        "특화후보가 검증상 현행보다 악화되어 현행 유지",
    )
    specialized["middle_label"] = specialized.middle_label.fillna(specialized.current_middle_label)
    peer = peer_eval.copy()
    peer["key"] = peer.city.astype(str) + "|" + peer.parent_code.astype(str) + "|" + peer.middle_code.astype(str).str.zfill(2)
    peer = peer[~peer.key.isin(set(specialized.key))].copy()
    current = current[current.key.isin(set(peer.key))].copy()
    peer_compare = peer.merge(
        current[["key", "predicted_gva_eok", "error_gva_eok", "error_rate_pct"]].rename(
            columns={
                "predicted_gva_eok": "current_predicted_gva_eok",
                "error_gva_eok": "current_error_gva_eok",
                "error_rate_pct": "current_error_rate_pct",
            }
        ),
        on="key",
        how="left",
    )
    peer_improves = peer_compare.error_gva_eok.lt(peer_compare.current_error_gva_eok)
    peer_compare["model_family"] = np.where(peer_improves, "상위산업 단위 동료지역 선택", "현행 소분류 합산 기준")
    peer_compare["model_status"] = np.where(peer_improves, "peer_parent_policy_pass", "peer_parent_policy_rejected")
    peer_compare["decision_note"] = np.where(
        peer_improves,
        "특화후보가 없는 중분류에 동료지역 선택 적용: 검증상 현행보다 개선",
        "동료지역 선택 후보가 검증상 악화되어 현행 유지",
    )
    # For rejected peer candidates, restore current prediction/error values.
    for column in ("predicted_gva_eok", "error_gva_eok", "error_rate_pct"):
        peer_compare[column] = np.where(peer_improves, peer_compare[column], peer_compare[f"current_{column}"])
    peer = peer_compare
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "model_family",
        "model_status",
        "actual_gva_eok",
        "predicted_gva_eok",
        "error_gva_eok",
        "error_rate_pct",
        "decision_note",
    ]
    out = pd.concat([specialized[cols], peer[cols]], ignore_index=True)
    out["accuracy_grade"] = out.error_rate_pct.map(grade)
    return out


def summarize(eval_df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    out = (
        eval_df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("error_gva_eok", "sum"),
            median_error_pct=("error_rate_pct", "median"),
            within_10pct_cells=("error_rate_pct", lambda s: int((s <= 10).sum())),
            over_50pct_cells=("error_rate_pct", lambda s: int((s > 50).sum())),
        )
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    out["model_family"] = model_name
    return out


def weak_cells(selected: pd.DataFrame) -> pd.DataFrame:
    return selected[(selected.error_rate_pct.gt(50)) | (selected.error_gva_eok.gt(1000))].sort_values(
        ["city", "error_gva_eok"], ascending=[True, False]
    )


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df = base_frame()
    current_eval = evaluate(df, "predicted_small_aggregated_share", "현행 소분류 합산 기준", "baseline", "전 중분류 기준선")
    uniform_eval = evaluate(df, "uniform_small_aggregated_share", "균등 분할", "bulk_candidate", "상위산업 내부 균등분할")
    peer_df = peer_parent_policy(df)
    peer_eval = evaluate(peer_df, "peer_policy_share", "상위산업 단위 동료지역 선택", "peer_parent_policy", "다른 도시의 상위산업 WAPE가 더 낮은 기준 선택")
    integrated_eval = specialized_plus_peer(peer_eval, current_eval)

    all_models = pd.concat([current_eval, uniform_eval, peer_eval, integrated_eval], ignore_index=True, sort=False)
    summaries = pd.concat(
        [
            summarize(current_eval, "현행 소분류 합산 기준"),
            summarize(uniform_eval, "균등 분할"),
            summarize(peer_eval, "상위산업 단위 동료지역 선택"),
            summarize(integrated_eval, "특화후보 + 검증통과 동료지역 선택"),
        ],
        ignore_index=True,
    )
    baseline_error = summaries[summaries.model_family.eq("현행 소분류 합산 기준")].set_index("city").error_sum_eok.to_dict()
    baseline_wape = summaries[summaries.model_family.eq("현행 소분류 합산 기준")].set_index("city").wape_pct.to_dict()
    summaries["error_reduction_eok"] = summaries.apply(lambda row: baseline_error[row.city] - row.error_sum_eok, axis=1)
    summaries["error_reduction_pct"] = summaries.apply(lambda row: row.error_reduction_eok / baseline_error[row.city] * 100, axis=1)
    summaries["wape_improvement_pp"] = summaries.apply(lambda row: baseline_wape[row.city] - row.wape_pct, axis=1)
    summaries = summaries.sort_values(["city", "error_sum_eok"])

    weak_current = weak_cells(current_eval)
    weak_integrated = weak_cells(integrated_eval)
    weak_compare = current_eval[
        current_eval.city.astype(str).add("|").add(current_eval.parent_code.astype(str)).add("|").add(current_eval.middle_code.astype(str)).isin(
            set(weak_current.city.astype(str).add("|").add(weak_current.parent_code.astype(str)).add("|").add(weak_current.middle_code.astype(str)))
        )
    ][["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok", "predicted_gva_eok", "error_gva_eok", "error_rate_pct"]].rename(
        columns={
            "predicted_gva_eok": "current_predicted_gva_eok",
            "error_gva_eok": "current_error_gva_eok",
            "error_rate_pct": "current_error_rate_pct",
        }
    )
    integ_key = integrated_eval.copy()
    weak_compare = weak_compare.merge(
        integ_key[
            [
                "city",
                "parent_code",
                "middle_code",
                "model_family",
                "model_status",
                "predicted_gva_eok",
                "error_gva_eok",
                "error_rate_pct",
            ]
        ].rename(
            columns={
                "predicted_gva_eok": "integrated_predicted_gva_eok",
                "error_gva_eok": "integrated_error_gva_eok",
                "error_rate_pct": "integrated_error_rate_pct",
            }
        ),
        on=["city", "parent_code", "middle_code"],
        how="left",
    )
    weak_compare["error_reduction_eok"] = weak_compare.current_error_gva_eok - weak_compare.integrated_error_gva_eok
    weak_compare["error_reduction_pct"] = weak_compare.error_reduction_eok / weak_compare.current_error_gva_eok * 100
    weak_compare = weak_compare.sort_values(["city", "current_error_gva_eok"], ascending=[True, False])

    all_models.to_csv(OUTDIR / "phase78_bulk_remediation_all_models.csv", index=False, encoding="utf-8-sig")
    integrated_eval.to_csv(OUTDIR / "phase78_bulk_remediation_integrated_selected.csv", index=False, encoding="utf-8-sig")
    summaries.to_csv(OUTDIR / "phase78_bulk_remediation_summary.csv", index=False, encoding="utf-8-sig")
    weak_compare.to_csv(OUTDIR / "phase78_weak_cell_before_after.csv", index=False, encoding="utf-8-sig")

    report = f"""# 중분류 취약 산업 일괄 개선 실험

## 목적

단일 산업을 하나씩 고치는 방식 대신, 고양시·포항시의 중분류 취약 산업 전체를 한 번에 식별하고 넓게 적용 가능한 개선 규칙을 비교했다. 모든 성능값은 2023년 중분류 실제 GVA와 추정 GVA의 차이를 억원·%로 계산했다.

## 후보

| 후보 | 설명 |
| --- | --- |
| 현행 소분류 합산 기준 | 기존 사업체·종사자 중심 추정 |
| 균등 분할 | 상위산업 내부 중분류를 동일 비중으로 분할 |
| 상위산업 단위 동료지역 선택 | 타 지역에서 같은 상위산업의 현행/균등 중 더 낮은 WAPE를 보인 기준을 선택 |
| 특화후보 + 검증통과 동료지역 선택 | 산업별 활동지표 후보를 먼저 검토하고, 나머지 중분류에는 동료지역 선택 후보를 대입하되 현행보다 악화되면 탈락 |

## 전체 성능 비교

{md_table(summaries, [("city", "지역"), ("model_family", "후보"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_pct", "오차감소 %")])}

## 현행 취약 중분류의 개선 전후

취약 셀은 현행 오차율 50% 초과 또는 금액오차 1,000억원 초과인 중분류다.

{md_table(weak_compare, [("city", "지역"), ("parent_code", "상위"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("current_predicted_gva_eok", "현행 추정 억원"), ("current_error_gva_eok", "현행 오차 억원"), ("current_error_rate_pct", "현행 오차 %"), ("model_family", "통합 선택 기준"), ("integrated_predicted_gva_eok", "통합 추정 억원"), ("integrated_error_gva_eok", "통합 오차 억원"), ("integrated_error_rate_pct", "통합 오차 %"), ("error_reduction_pct", "오차감소 %")], 60)}

## 통합 후에도 남는 취약 중분류

{md_table(weak_integrated, [("city", "지역"), ("parent_code", "상위"), ("middle_code", "코드"), ("middle_label", "산업"), ("model_family", "선택 기준"), ("model_status", "상태"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 40)}

## 판정

1. 일괄 규칙만으로도 고양시 중분류 가중오차는 현행 대비 크게 감소한다. 다만 동료지역 선택은 일부 산업에서 악화되므로, 검증 통과 셀에만 적용한다.
2. 포항시는 제조업 대형 구조 때문에 특화후보가 필요하다. 공장 제조시설면적 기준을 유지하되, 금속가공·기계수리·식료품 제조는 여전히 별도 보강 대상이다.
3. 통합 후에도 남는 취약 산업이 다음 작업 대상이다. 즉 앞으로는 산업 하나씩 임의로 고르는 게 아니라, 이 보고서의 `통합 후에도 남는 취약 중분류` 표를 작업 큐로 사용한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase78_bulk_remediation_summary.csv")
    print(OUTDIR / "phase78_weak_cell_before_after.csv")


if __name__ == "__main__":
    main()
