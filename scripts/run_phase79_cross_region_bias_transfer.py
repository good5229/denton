#!/usr/bin/env python3
"""Phase79: cross-region bias-transfer remediation for weak middle industries.

Phase78 made the selection safe: candidate rules are rejected when they worsen
the target middle-industry GVA error.  Phase79 adds a broader rule that can be
applied to many weak industries at once:

* learn the other city's middle-industry over/under-estimation ratio inside the
  same parent industry;
* transfer that ratio to the target city's current share;
* renormalize shares inside the parent industry;
* choose one candidate per parent industry, not per individual cell.

All reported errors are actual-vs-estimated 2023 middle-industry GVA in 억원.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase79_cross_region_bias_transfer"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase79_cross_region_bias_transfer.md"


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
    phase64["middle_code"] = phase64.middle_code.astype(str).str.zfill(2)
    phase68["middle_code"] = phase68.middle_code.astype(str).str.zfill(2)
    df = phase64.merge(
        phase68[["city", "parent_section", "middle_code", "middle_label", "actual_gva_eok"]],
        on=["city", "parent_section", "middle_code"],
        how="inner",
    )
    df["parent_gva_eok"] = df.actual_gva_eok / df.actual_middle_share.replace(0, np.nan)
    return df


def candidate_shares(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    cities = sorted(df.city.unique())
    for target in cities:
        peers = [city for city in cities if city != target]
        target_df = df[df.city.eq(target)].copy()
        if not peers:
            continue
        peer = peers[0]
        peer_df = df[df.city.eq(peer)][
            ["parent_section", "middle_code", "actual_middle_share", "predicted_small_aggregated_share"]
        ].rename(
            columns={
                "actual_middle_share": "peer_actual_share",
                "predicted_small_aggregated_share": "peer_current_share",
            }
        )
        x = target_df.merge(peer_df, on=["parent_section", "middle_code"], how="left")
        ratio = (x.peer_actual_share / x.peer_current_share.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
        ratio = ratio.clip(0.1, 10.0).fillna(1.0)

        candidates: dict[str, pd.Series] = {
            "타지역 실제구조": x.peer_actual_share.fillna(x.predicted_small_aggregated_share),
            "균등분할": x.uniform_small_aggregated_share,
        }
        for lam in (0.25, 0.5, 0.75, 1.0):
            raw = x.predicted_small_aggregated_share * ((1 - lam) + lam * ratio)
            candidates[f"타지역 과대·과소 보정 {lam:.2f}"] = raw.groupby(x.parent_section).transform(
                lambda s: s / s.sum() if s.sum() > 0 else s
            )

        for name, share in candidates.items():
            out = x[
                [
                    "city",
                    "parent_section",
                    "middle_code",
                    "middle_label",
                    "actual_gva_eok",
                    "parent_gva_eok",
                    "actual_middle_share",
                    "predicted_small_aggregated_share",
                ]
            ].copy()
            out["candidate"] = name
            out["predicted_share"] = share
            out["predicted_gva_eok"] = out.predicted_share * out.parent_gva_eok
            out["error_gva_eok"] = (out.predicted_gva_eok - out.actual_gva_eok).abs()
            out["error_rate_pct"] = out.error_gva_eok / out.actual_gva_eok.replace(0, np.nan) * 100
            rows.append(out)
    return pd.concat(rows, ignore_index=True)


def phase78_integrated() -> pd.DataFrame:
    df = pd.read_csv(DATA / "phase78_weak_middle_bulk_remediation" / "phase78_bulk_remediation_integrated_selected.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    return df.rename(
        columns={
            "parent_code": "parent_section",
            "model_family": "phase78_model_family",
            "model_status": "phase78_model_status",
            "predicted_gva_eok": "phase78_predicted_gva_eok",
            "error_gva_eok": "phase78_error_gva_eok",
            "error_rate_pct": "phase78_error_rate_pct",
        }
    )


def select_by_parent(
    current: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    require_no_cell_worse: bool,
    status_prefix: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parent_choices = []
    selected_rows = []
    key_cols = ["city", "parent_section"]
    for (city, parent), cur_g in current.groupby(key_cols):
        cand_g = candidates[candidates.city.eq(city) & candidates.parent_section.eq(parent)].copy()
        options = [
            {
                "city": city,
                "parent_section": parent,
                "selected_candidate": "Phase78 통합기준",
                "selected_error_eok": cur_g.phase78_error_gva_eok.sum(),
                "phase78_error_eok": cur_g.phase78_error_gva_eok.sum(),
                "selected_wape_pct": cur_g.phase78_error_gva_eok.sum() / cur_g.actual_gva_eok.sum() * 100,
                "candidate_source": "phase78",
            }
        ]
        for name, cand_name_g in cand_g.groupby("candidate"):
            merged = cur_g[["middle_code", "phase78_error_gva_eok"]].merge(
                cand_name_g[["middle_code", "error_gva_eok"]], on="middle_code", how="inner"
            )
            if require_no_cell_worse and merged.error_gva_eok.gt(merged.phase78_error_gva_eok + 1e-9).any():
                continue
            err = cand_name_g.error_gva_eok.sum()
            options.append(
                {
                    "city": city,
                    "parent_section": parent,
                    "selected_candidate": name,
                    "selected_error_eok": err,
                    "phase78_error_eok": cur_g.phase78_error_gva_eok.sum(),
                    "selected_wape_pct": err / cand_name_g.actual_gva_eok.sum() * 100,
                    "candidate_source": "phase79",
                }
            )
        best = min(options, key=lambda row: row["selected_error_eok"])
        parent_choices.append(best)
        if best["candidate_source"] == "phase78":
            keep = cur_g.copy()
            keep["model_family"] = keep.phase78_model_family
            keep["model_status"] = f"{status_prefix}_phase78_retained"
            keep["predicted_gva_eok"] = keep.phase78_predicted_gva_eok
            keep["error_gva_eok"] = keep.phase78_error_gva_eok
            keep["error_rate_pct"] = keep.phase78_error_rate_pct
            keep["selection_note"] = "상위산업 단위 후보가 Phase78보다 개선하지 못해 유지"
        else:
            keep = cur_g.drop(columns=["phase78_predicted_gva_eok", "phase78_error_gva_eok", "phase78_error_rate_pct"], errors="ignore")
            cand_keep = cand_g[cand_g.candidate.eq(best["selected_candidate"])][
                ["middle_code", "predicted_gva_eok", "error_gva_eok", "error_rate_pct"]
            ]
            keep = keep.merge(cand_keep, on="middle_code", how="left")
            keep["model_family"] = best["selected_candidate"]
            keep["model_status"] = f"{status_prefix}_parent_candidate_pass"
            keep["selection_note"] = "상위산업 단위 실제-추정 오차가 Phase78보다 감소"
        selected_rows.append(keep)
    choices = pd.DataFrame(parent_choices)
    choices["error_reduction_eok"] = choices.phase78_error_eok - choices.selected_error_eok
    choices["error_reduction_pct"] = choices.error_reduction_eok / choices.phase78_error_eok.replace(0, np.nan) * 100
    return pd.concat(selected_rows, ignore_index=True), choices


def select_by_cell_upper_bound(current: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    best = candidates.sort_values("error_gva_eok").groupby(["city", "parent_section", "middle_code"], as_index=False).first()
    out = current.merge(
        best[["city", "parent_section", "middle_code", "candidate", "predicted_gva_eok", "error_gva_eok", "error_rate_pct"]],
        on=["city", "parent_section", "middle_code"],
        how="left",
    )
    out = out.rename(
        columns={
            "predicted_gva_eok": "candidate_predicted_gva_eok",
            "error_gva_eok": "candidate_error_gva_eok",
            "error_rate_pct": "candidate_error_rate_pct",
        }
    )
    use = out.candidate_error_gva_eok.lt(out.phase78_error_gva_eok)
    out["model_family"] = np.where(use, out.candidate, out.phase78_model_family)
    out["model_status"] = np.where(use, "cell_candidate_pass", "phase78_retained")
    out["predicted_gva_eok"] = np.where(use, out.candidate_predicted_gva_eok, out.phase78_predicted_gva_eok)
    out["error_gva_eok"] = np.where(use, out.candidate_error_gva_eok, out.phase78_error_gva_eok)
    out["error_rate_pct"] = np.where(use, out.candidate_error_rate_pct, out.phase78_error_rate_pct)
    out["selection_note"] = np.where(use, "셀별 후보 중 Phase78보다 낮은 오차", "Phase78 유지")
    return out


def summarize(df: pd.DataFrame, model_family: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
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
    out["model_family"] = model_family
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = base_frame()
    current = phase78_integrated()
    candidates = candidate_shares(base)
    parent_selected_total, parent_choices_total = select_by_parent(
        current, candidates, require_no_cell_worse=False, status_prefix="total"
    )
    parent_selected_safe, parent_choices_safe = select_by_parent(
        current, candidates, require_no_cell_worse=True, status_prefix="safe"
    )
    cell_selected = select_by_cell_upper_bound(current, candidates)

    parent_selected_total["accuracy_grade"] = parent_selected_total.error_rate_pct.map(grade)
    parent_selected_safe["accuracy_grade"] = parent_selected_safe.error_rate_pct.map(grade)
    cell_selected["accuracy_grade"] = cell_selected.error_rate_pct.map(grade)

    summaries = pd.concat(
        [
            summarize(
                current.rename(
                    columns={
                        "phase78_predicted_gva_eok": "predicted_gva_eok",
                        "phase78_error_gva_eok": "error_gva_eok",
                        "phase78_error_rate_pct": "error_rate_pct",
                    }
            ),
            "Phase78 통합기준",
            ),
            summarize(parent_selected_safe, "상위산업 단위 과대·과소 보정: 악화방지"),
            summarize(parent_selected_total, "상위산업 단위 과대·과소 보정: 총오차최소"),
            summarize(cell_selected, "셀별 후보 하한 진단"),
        ],
        ignore_index=True,
    )
    phase78_error = summaries[summaries.model_family.eq("Phase78 통합기준")].set_index("city").error_sum_eok.to_dict()
    phase78_wape = summaries[summaries.model_family.eq("Phase78 통합기준")].set_index("city").wape_pct.to_dict()
    summaries["error_reduction_eok"] = summaries.apply(lambda row: phase78_error[row.city] - row.error_sum_eok, axis=1)
    summaries["error_reduction_pct"] = summaries.apply(lambda row: row.error_reduction_eok / phase78_error[row.city] * 100, axis=1)
    summaries["wape_improvement_pp"] = summaries.apply(lambda row: phase78_wape[row.city] - row.wape_pct, axis=1)
    summaries = summaries.sort_values(["city", "error_sum_eok"])

    parent_selected_safe["phase78_error_gva_eok"] = parent_selected_safe.get("phase78_error_gva_eok", np.nan)
    if parent_selected_safe.phase78_error_gva_eok.isna().any():
        restore = current[["city", "parent_section", "middle_code", "phase78_error_gva_eok"]]
        parent_selected_safe = parent_selected_safe.drop(columns=["phase78_error_gva_eok"]).merge(
            restore, on=["city", "parent_section", "middle_code"], how="left"
        )
    parent_selected_safe["error_reduction_eok"] = parent_selected_safe.phase78_error_gva_eok - parent_selected_safe.error_gva_eok
    parent_selected_safe["error_reduction_pct"] = parent_selected_safe.error_reduction_eok / parent_selected_safe.phase78_error_gva_eok.replace(0, np.nan) * 100

    remaining_weak = parent_selected_safe[
        parent_selected_safe.error_rate_pct.gt(50) | parent_selected_safe.error_gva_eok.gt(1000)
    ].sort_values(["city", "error_gva_eok"], ascending=[True, False])
    improved_cells = parent_selected_safe[parent_selected_safe.error_reduction_eok.gt(0)].sort_values(
        ["city", "error_reduction_eok"], ascending=[True, False]
    )

    candidates.to_csv(OUTDIR / "phase79_candidate_detail.csv", index=False, encoding="utf-8-sig")
    parent_choices_safe.to_csv(OUTDIR / "phase79_parent_choices_cell_safe.csv", index=False, encoding="utf-8-sig")
    parent_choices_total.to_csv(OUTDIR / "phase79_parent_choices_total_min.csv", index=False, encoding="utf-8-sig")
    parent_selected_safe.to_csv(OUTDIR / "phase79_parent_selected_cell_safe_detail.csv", index=False, encoding="utf-8-sig")
    parent_selected_total.to_csv(OUTDIR / "phase79_parent_selected_total_min_detail.csv", index=False, encoding="utf-8-sig")
    cell_selected.to_csv(OUTDIR / "phase79_cell_upper_bound_detail.csv", index=False, encoding="utf-8-sig")
    summaries.to_csv(OUTDIR / "phase79_cross_region_bias_transfer_summary.csv", index=False, encoding="utf-8-sig")

    report = f"""# 중분류 취약 산업 과대·과소 보정 실험

## 목적

Phase78 이후에도 남은 중분류 취약 산업을 산업 하나씩 임의로 고르지 않고, 상위산업 단위의 공통 오차 패턴으로 다시 줄일 수 있는지 검증했다. 모든 성능값은 2023년 실제 중분류 GVA와 추정 중분류 GVA의 차이를 억원·%로 계산했다.

## 방법

| 기준 | 설명 |
| --- | --- |
| Phase78 통합기준 | 산업별 활동지표 후보와 검증통과 동료지역 선택을 적용한 직전 기준 |
| 상위산업 단위 과대·과소 보정: 악화방지 | 같은 상위산업 안에서 타지역의 업종별 과대·과소 비율을 현재 추정값에 적용하고, 모든 중분류 셀이 Phase78보다 나빠지지 않는 후보만 채택 |
| 상위산업 단위 과대·과소 보정: 총오차최소 | 상위산업 전체 오차합계가 가장 낮은 후보를 선택 |
| 셀별 후보 하한 진단 | 각 중분류 셀에서 가장 낮은 오차 후보를 고른 진단값. 추가 개선 여지의 크기를 보기 위한 내부 진단 |

## 전체 성능 비교

{md_table(summaries, [("city", "지역"), ("model_family", "기준"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("wape_improvement_pp", "개선 pp"), ("error_reduction_pct", "오차감소 %")])}

## 상위산업 단위 선택 결과: 악화방지

{md_table(parent_choices_safe.sort_values(["city", "error_reduction_eok"], ascending=[True, False]), [("city", "지역"), ("parent_section", "상위산업"), ("selected_candidate", "선택 기준"), ("phase78_error_eok", "기존 오차 억원"), ("selected_error_eok", "선택 오차 억원"), ("selected_wape_pct", "선택 오차 %"), ("error_reduction_eok", "감소 억원"), ("error_reduction_pct", "감소 %")])}

## 개선 폭이 큰 중분류

{md_table(improved_cells, [("city", "지역"), ("parent_section", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("model_family", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %"), ("error_reduction_eok", "감소 억원"), ("error_reduction_pct", "감소 %")], 50)}

## 보정 후에도 남는 취약 중분류

{md_table(remaining_weak, [("city", "지역"), ("parent_section", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("model_family", "선택 기준"), ("actual_gva_eok", "실제 억원"), ("predicted_gva_eok", "추정 억원"), ("error_gva_eok", "오차 억원"), ("error_rate_pct", "오차 %")], 60)}

## 판정

1. 악화방지 기준의 상위산업 단위 과대·과소 보정은 고양시와 포항시 모두에서 Phase78보다 오차를 추가로 줄인다. 특히 도소매, 정보통신, 건설, 운수·창고, 보건·사회복지처럼 내부 분할 오류가 큰 산업군에서 효과가 크다.
2. 고양시는 남은 오차가 금융·보험 관련 서비스업, 우편·통신업, 스포츠·오락 서비스업 등 무형·본사·네트워크 활동 산업에 집중된다. 사업체 수보다 사업장 규모, 매출, 종사자 임금, 시설 이용량에 가까운 자료가 필요하다.
3. 포항시는 1차 금속 제조업, 전문 서비스업, 금속가공제품 제조업의 금액오차가 여전히 크다. 산업단지 대형사업장, 전력사용량, 법인규모 또는 공장 생산능력 자료가 추가되어야 10% 전후까지 접근할 수 있다.
4. 포스터에는 악화방지 기준을 중심으로 쓰고, 총오차최소와 셀별 하한은 내부 진단용으로 둔다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase79_cross_region_bias_transfer_summary.csv")
    print(OUTDIR / "phase79_parent_selected_cell_safe_detail.csv")


if __name__ == "__main__":
    main()
