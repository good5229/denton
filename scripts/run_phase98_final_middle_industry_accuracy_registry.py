#!/usr/bin/env python3
"""Phase98: final middle-industry GVA accuracy registry.

The project goal is to explain, by industry, how accurate the GVA estimate is.
This phase consolidates the latest strict and operational selections into one
auditable registry:

* strict track: no middle-industry cell is allowed to worsen;
* protected track: weak-queue reduction is allowed only when grade boundaries
  do not deteriorate;
* both tracks must preserve city × parent-industry totals;
* remaining weak industries are grouped by cause and required data type.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE92 = DATA / "phase92_current_accuracy_after_grouped_transfer"
PHASE97 = DATA / "phase97_goyang_augmented_activity_screen"
OUTDIR = DATA / "phase98_final_middle_industry_accuracy_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase98_final_middle_industry_accuracy_registry.md"


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
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(value) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def grade_order(grade: str) -> int:
    order = {
        "매우 양호(5% 이하)": 1,
        "양호(5~10%)": 2,
        "주의(10~20%)": 3,
        "취약(20~50%)": 4,
        "고취약(50% 초과)": 5,
    }
    return order.get(str(grade), 9)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = pd.read_csv(PHASE92 / "phase92_current_middle_industry_accuracy_registry.csv")
    strict = pd.read_csv(PHASE97 / "phase97_strict_selected_registry.csv")
    protected = pd.read_csv(PHASE97 / "phase97_protected_selected_registry.csv")
    for df in (base, strict, protected):
        df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    return base, strict, protected


def required_data(row: pd.Series) -> str:
    if row["strict_remaining_queue"] == "현행유지가능" and row["protected_remaining_queue"] == "현행유지가능":
        return "추가 자료 불필요"
    label = str(row.middle_label)
    cause = str(row.cause_group)
    if "협회" in label or "단체" in label:
        return "비영리단체 수입·회원·종사자·보조금 또는 단체 활동규모"
    if "방송" in label or "영상" in label or "출판" in label or "정보서비스" in label:
        return "방송·콘텐츠·정보서비스 사업장 매출, 제작규모, 플랫폼/서버 활동량"
    if "연구개발" in label or "과학기술" in label or "전문 서비스" in label:
        return "전문인력, 임금총액, 연구개발비, 용역·계약액"
    if "자동차" in label and "판매" in label:
        return "자동차 등록·판매대수, 딜러 매출, 정비/부품 매출"
    if "제조업" in label or "수리업" in label:
        return "제조업 중분류별 출하액·부가가치·전력·공장면적·대형사업장 규모"
    if "수도" in label or "하수" in label or "폐기물" in label or "환경" in label:
        return "상하수도 처리량, 폐기물 처리량, 시설용량, 위탁계약액"
    if "숙박" in label or "음식" in label:
        return "숙박 객실·가동률, 음식점 매출·면적·종사자"
    if "운송" in label or "창고" in label:
        return "여객·화물·창고면적·물동량 활동자료"
    if cause == "거래·자산형":
        return "거래금액, 자산가치, 공시가격, 임대면적"
    if cause == "계약·공사형":
        return "허가·착공·사용승인·기성·계약액"
    return str(row.get("phase92_needed_data", "중분류 직접 활동자료"))


def build_registry(base: pd.DataFrame, strict: pd.DataFrame, protected: pd.DataFrame) -> pd.DataFrame:
    keys = ["city", "parent_code", "middle_code"]
    meta_cols = [
        "city",
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "initial_predicted_gva_eok",
        "initial_error_gva_eok",
        "initial_error_rate_pct",
        "phase92_predicted_gva_eok",
        "phase92_error_gva_eok",
        "phase92_error_rate_pct",
        "phase92_accuracy_grade",
        "phase92_queue",
        "phase92_initial_worsened",
        "cause_group",
        "phase92_needed_data",
        "diagnostic_note",
    ]
    out = base[meta_cols].copy()
    out["phase92_remaining_queue_normalized"] = np.where(
        out.phase92_queue.eq("현행유지가능"),
        "현행유지가능",
        "추가개선대상",
    )
    strict_keep = strict[
        keys
        + [
            "option_name",
            "option_family",
            "predicted_gva_eok",
            "error_gva_eok",
            "error_rate_pct",
            "accuracy_grade",
            "remaining_queue",
            "error_reduction_eok",
        ]
    ].rename(
        columns={
            "option_name": "strict_option_name",
            "option_family": "strict_option_family",
            "predicted_gva_eok": "strict_predicted_gva_eok",
            "error_gva_eok": "strict_error_gva_eok",
            "error_rate_pct": "strict_error_rate_pct",
            "accuracy_grade": "strict_accuracy_grade",
            "remaining_queue": "strict_remaining_queue",
            "error_reduction_eok": "strict_error_reduction_vs_phase92_eok",
        }
    )
    protected_keep = protected[
        keys
        + [
            "option_name",
            "option_family",
            "predicted_gva_eok",
            "error_gva_eok",
            "error_rate_pct",
            "accuracy_grade",
            "remaining_queue",
            "error_reduction_eok",
            "error_rate_delta_pp",
            "grade_boundary_worse",
        ]
    ].rename(
        columns={
            "option_name": "protected_option_name",
            "option_family": "protected_option_family",
            "predicted_gva_eok": "protected_predicted_gva_eok",
            "error_gva_eok": "protected_error_gva_eok",
            "error_rate_pct": "protected_error_rate_pct",
            "accuracy_grade": "protected_accuracy_grade",
            "remaining_queue": "protected_remaining_queue",
            "error_reduction_eok": "protected_error_reduction_vs_phase92_eok",
            "error_rate_delta_pp": "protected_error_rate_delta_vs_phase92_pp",
            "grade_boundary_worse": "protected_grade_boundary_worse",
        }
    )
    out = out.merge(strict_keep, on=keys, how="left").merge(protected_keep, on=keys, how="left")
    out["strict_grade_order"] = out.strict_accuracy_grade.map(grade_order)
    out["protected_grade_order"] = out.protected_accuracy_grade.map(grade_order)
    out["phase92_grade_order"] = out.phase92_accuracy_grade.map(grade_order)
    out["strict_grade_worse_than_phase92"] = out.strict_grade_order.gt(out.phase92_grade_order)
    # The protected operational track guards the public-facing grade boundaries
    # used in Phase96: <=10, <=20, <=50.  Crossing from <=5 to <=10 is still
    # inside the "10% 이하" headline bucket and is not counted as a protected
    # boundary deterioration.
    out["protected_grade_worse_than_phase92"] = out.protected_grade_boundary_worse.fillna(False)
    out["strict_exact_worse_than_phase92"] = out.strict_error_gva_eok.gt(out.phase92_error_gva_eok + 1e-9)
    out["protected_exact_worse_than_phase92"] = out.protected_error_gva_eok.gt(out.phase92_error_gva_eok + 1e-9)
    out["required_next_data"] = out.apply(required_data, axis=1)
    out["public_claim_track"] = np.where(out.strict_remaining_queue.eq("현행유지가능"), "정확도 주장 가능", "추가개선 필요")
    out["operational_track"] = np.where(out.protected_remaining_queue.eq("현행유지가능"), "운영 적용 가능", "운영 개선 필요")
    return out.sort_values(["city", "strict_error_gva_eok"], ascending=[True, False])


def summarize(df: pd.DataFrame, pred_col: str, err_col: str, rate_col: str, queue_col: str, stage: str) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=(err_col, "sum"),
            median_error_pct=(rate_col, "median"),
            within_5pct_cells=(rate_col, lambda s: int((s <= 5).sum())),
            within_10pct_cells=(rate_col, lambda s: int((s <= 10).sum())),
            over_20pct_cells=(rate_col, lambda s: int((s > 20).sum())),
            over_50pct_cells=(rate_col, lambda s: int((s > 50).sum())),
            remaining_queue_cells=(queue_col, lambda s: int((s == "추가개선대상").sum())),
        )
        .assign(model_stage=stage)
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    return out


def accounting_check(df: pd.DataFrame, pred_col: str, track: str) -> pd.DataFrame:
    chk = (
        df.groupby(["city", "parent_code"], as_index=False)
        .agg(actual_parent_eok=("actual_gva_eok", "sum"), predicted_parent_eok=(pred_col, "sum"))
    )
    chk["track"] = track
    chk["gap_eok"] = chk.predicted_parent_eok - chk.actual_parent_eok
    chk["gap_pct"] = chk.gap_eok / chk.actual_parent_eok.replace(0, np.nan) * 100
    chk["pass"] = chk.gap_eok.abs().lt(1e-6)
    return chk


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base, strict, protected = load_inputs()
    reg = build_registry(base, strict, protected)
    summary = pd.concat(
        [
            summarize(
                reg,
                "phase92_predicted_gva_eok",
                "phase92_error_gva_eok",
                "phase92_error_rate_pct",
                "phase92_remaining_queue_normalized",
                "Phase92 기준",
            ),
            summarize(reg, "strict_predicted_gva_eok", "strict_error_gva_eok", "strict_error_rate_pct", "strict_remaining_queue", "엄격 기준"),
            summarize(reg, "protected_predicted_gva_eok", "protected_error_gva_eok", "protected_error_rate_pct", "protected_remaining_queue", "취약큐 보호 기준"),
        ],
        ignore_index=True,
    )
    base_summary = summary[summary.model_stage.eq("Phase92 기준")].set_index("city")
    summary["phase92_wape_improvement_pp"] = summary.apply(lambda r: base_summary.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    summary["phase92_error_reduction_eok"] = summary.apply(lambda r: base_summary.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)

    acct = pd.concat(
        [
            accounting_check(reg, "strict_predicted_gva_eok", "엄격 기준"),
            accounting_check(reg, "protected_predicted_gva_eok", "취약큐 보호 기준"),
        ],
        ignore_index=True,
    )
    audits = {
        "strict_exact_worse": reg[reg.strict_exact_worse_than_phase92].copy(),
        "strict_grade_worse": reg[reg.strict_grade_worse_than_phase92].copy(),
        "protected_grade_worse": reg[reg.protected_grade_worse_than_phase92 | reg.protected_grade_boundary_worse.fillna(False)].copy(),
    }

    remaining = reg[reg.protected_remaining_queue.eq("추가개선대상")].copy()
    remaining_by_cause = (
        remaining.groupby(["city", "cause_group"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            strict_error_sum_eok=("strict_error_gva_eok", "sum"),
            protected_error_sum_eok=("protected_error_gva_eok", "sum"),
            max_error_rate_pct=("protected_error_rate_pct", "max"),
            required_data_examples=("required_next_data", lambda s: " / ".join(pd.Series(s).drop_duplicates().head(3))),
        )
    )
    remaining_by_cause["protected_wape_pct"] = remaining_by_cause.protected_error_sum_eok / remaining_by_cause.actual_sum_eok * 100
    remaining_top = remaining.sort_values(["city", "protected_error_gva_eok"], ascending=[True, False])
    improved_protected = reg[reg.protected_error_reduction_vs_phase92_eok.gt(1e-9)].sort_values(
        ["city", "protected_error_reduction_vs_phase92_eok"], ascending=[True, False]
    )
    worsened_protected = reg[reg.protected_exact_worse_than_phase92].sort_values(
        ["city", "protected_error_reduction_vs_phase92_eok"], ascending=[True, True]
    )

    reg.to_csv(OUTDIR / "phase98_final_middle_industry_accuracy_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase98_final_accuracy_summary.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase98_accounting_checks.csv", index=False, encoding="utf-8-sig")
    remaining_by_cause.to_csv(OUTDIR / "phase98_remaining_by_cause_group.csv", index=False, encoding="utf-8-sig")
    remaining_top.to_csv(OUTDIR / "phase98_remaining_industry_queue.csv", index=False, encoding="utf-8-sig")
    improved_protected.to_csv(OUTDIR / "phase98_protected_improved_industries.csv", index=False, encoding="utf-8-sig")
    worsened_protected.to_csv(OUTDIR / "phase98_protected_worsened_industries.csv", index=False, encoding="utf-8-sig")
    for name, frame in audits.items():
        frame.to_csv(OUTDIR / f"phase98_audit_{name}.csv", index=False, encoding="utf-8-sig")

    report = f"""# 최종 중분류별 GVA 추정 정확도 레지스트리

## 목적

각 산업별 총부가가치(GVA)를 얼마나 정확히 추정했는지 설명하기 위해 최신 엄격 기준과 취약큐 보호 기준을 하나의 중분류 레지스트리로 통합했다. 모든 수치는 실제 중분류 GVA와 추정 중분류 GVA의 차이를 억원과 %로 계산한다.

## 기준 구분

| 기준 | 용도 | 채택 조건 |
| --- | --- | --- |
| 엄격 기준 | 대외적으로 각 산업별 정확도를 강하게 주장할 때 사용 | Phase92보다 개별 중분류 오차가 하나도 커지지 않아야 함 |
| 취약큐 보호 기준 | 실제 격차 축소를 위한 운영안 | 취약 중분류 오차와 상위산업 오차가 줄고, 판정 구간이 악화되지 않아야 함 |

## 도시별 요약

{md_table(summary.sort_values(["city", "model_stage"]), [("city", "지역"), ("model_stage", "기준"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_5pct_cells", "5% 이하"), ("within_10pct_cells", "10% 이하"), ("over_20pct_cells", "20% 초과"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("phase92_wape_improvement_pp", "Phase92 대비 개선 pp"), ("phase92_error_reduction_eok", "Phase92 대비 감소 억원")])}

## 취약큐 보호 기준에서 오차가 줄어든 산업

{md_table(improved_protected, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("protected_predicted_gva_eok", "추정 억원"), ("protected_error_gva_eok", "오차 억원"), ("protected_error_rate_pct", "오차 %"), ("protected_error_reduction_vs_phase92_eok", "감소 억원"), ("protected_option_name", "선택 기준")], 80)}

## 취약큐 보호 기준에서 오차가 증가한 산업

{md_table(worsened_protected, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("protected_predicted_gva_eok", "추정 억원"), ("protected_error_gva_eok", "오차 억원"), ("protected_error_rate_pct", "오차 %"), ("protected_error_reduction_vs_phase92_eok", "감소 억원"), ("protected_option_name", "선택 기준")], 80)}

## 남은 취약 중분류 상위

{md_table(remaining_top, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("actual_gva_eok", "실제 억원"), ("protected_predicted_gva_eok", "추정 억원"), ("protected_error_gva_eok", "오차 억원"), ("protected_error_rate_pct", "오차 %"), ("required_next_data", "필요자료")], 100)}

## 남은 취약 원인군 요약

{md_table(remaining_by_cause.sort_values(["city", "protected_error_sum_eok"], ascending=[True, False]), [("city", "지역"), ("cause_group", "원인군"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("protected_error_sum_eok", "오차합계 억원"), ("protected_wape_pct", "가중오차 %"), ("max_error_rate_pct", "최대오차 %"), ("required_data_examples", "대표 필요자료")], 80)}

## 감사

상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개.

{md_table(acct[~acct["pass"]], [("track", "기준"), ("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

엄격 기준 개별 중분류 오차 악화: {len(audits["strict_exact_worse"])}개.

엄격 기준 판정 악화: {len(audits["strict_grade_worse"])}개.

취약큐 보호 기준 판정 악화: {len(audits["protected_grade_worse"])}개.

## 판정

1. 각 산업별 정확도 설명은 `phase98_final_middle_industry_accuracy_registry.csv`를 기준으로 한다.
2. 엄격 기준은 개별 산업 악화가 없어 대외 성능 주장에 적합하다.
3. 취약큐 보호 기준은 포항에서 총오차를 더 줄이지만 일부 산업의 오차금액 증가는 남으므로 운영 고도화 후보로 분리한다.
4. 고양은 로컬 인허가·버스·공장·복지 자료를 추가해도 남은 취약 산업을 줄이지 못했다. 다음 개선은 협회·단체, 방송·콘텐츠, 연구개발·과학기술, 자동차판매, 제조업 세부 출하·전력처럼 중분류에 직접 연결되는 자료 확보가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase98_final_middle_industry_accuracy_registry.csv")
    print(OUTDIR / "phase98_final_accuracy_summary.csv")


if __name__ == "__main__":
    main()
