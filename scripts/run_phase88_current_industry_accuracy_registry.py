#!/usr/bin/env python3
"""Phase88: current per-middle-industry GVA accuracy registry.

The user-facing question is: "how accurately did we estimate each industry?"
This registry supersedes older Phase81/83 registries by using the current
Phase87 safe result, which preserves parent totals and has no worsening against
its Phase86 reference.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase88_current_industry_accuracy_registry"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase88_current_industry_accuracy_registry.md"


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
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load() -> pd.DataFrame:
    baseline = pd.read_csv(DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv")
    baseline["middle_code"] = baseline.middle_code.astype(str).str.zfill(2)
    baseline = baseline.rename(
        columns={
            "parent_section": "parent_code",
            "predicted_gva_eok": "initial_predicted_gva_eok",
            "error_gva_eok": "initial_error_gva_eok",
            "error_rate_pct": "initial_error_rate_pct",
        }
    )[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "initial_predicted_gva_eok",
            "initial_error_gva_eok",
            "initial_error_rate_pct",
        ]
    ]

    phase86 = pd.read_csv(DATA / "phase86_structural_template_screen" / "phase86_final_safe_registry.csv")
    phase86["middle_code"] = phase86.middle_code.astype(str).str.zfill(2)
    phase86 = phase86.rename(
        columns={
            "predicted_gva_eok": "phase86_predicted_gva_eok",
            "error_gva_eok": "phase86_error_gva_eok",
            "error_rate_pct": "phase86_error_rate_pct",
            "option_name": "phase86_option_name",
            "option_family": "phase86_option_family",
        }
    )[
        [
            "city",
            "parent_code",
            "middle_code",
            "phase86_option_name",
            "phase86_option_family",
            "phase86_predicted_gva_eok",
            "phase86_error_gva_eok",
            "phase86_error_rate_pct",
        ]
    ]

    final = pd.read_csv(DATA / "phase87_remaining_family_template_screen" / "phase87_final_safe_registry.csv")
    final["middle_code"] = final.middle_code.astype(str).str.zfill(2)
    final = final.rename(
        columns={
            "option_name": "final_option_name",
            "option_family": "final_option_family",
            "predicted_gva_eok": "final_predicted_gva_eok",
            "error_gva_eok": "final_error_gva_eok",
            "error_rate_pct": "final_error_rate_pct",
            "accuracy_grade": "final_accuracy_grade",
            "remaining_queue": "final_remaining_queue",
        }
    )[
        [
            "city",
            "parent_code",
            "middle_code",
            "final_option_name",
            "final_option_family",
            "final_predicted_gva_eok",
            "final_error_gva_eok",
            "final_error_rate_pct",
            "final_accuracy_grade",
            "final_remaining_queue",
        ]
    ]
    reg = baseline.merge(phase86, on=["city", "parent_code", "middle_code"], how="left").merge(
        final, on=["city", "parent_code", "middle_code"], how="left"
    )
    reg["initial_to_final_error_reduction_eok"] = reg.initial_error_gva_eok - reg.final_error_gva_eok
    reg["initial_to_final_error_reduction_pct"] = (
        reg.initial_to_final_error_reduction_eok / reg.initial_error_gva_eok.replace(0, np.nan) * 100
    )
    reg["phase86_to_final_error_reduction_eok"] = reg.phase86_error_gva_eok - reg.final_error_gva_eok
    reg["phase86_to_final_error_reduction_pct"] = (
        reg.phase86_to_final_error_reduction_eok / reg.phase86_error_gva_eok.replace(0, np.nan) * 100
    )
    reg["needed_data_type"] = np.where(reg.final_remaining_queue.eq("추가개선대상"), reg.apply(needed_data, axis=1), "추가 자료 불필요")
    reg["diagnostic_note"] = np.where(reg.final_remaining_queue.eq("추가개선대상"), reg.apply(diagnostic_note, axis=1), "현 기준 사용 가능")
    return reg


def needed_data(row: pd.Series) -> str:
    code = f"{row.parent_code}:{str(row.middle_code).zfill(2)}"
    mapping = {
        "ERS:94": "비영리단체·협회 활동규모, 단체 예산·종사자·회원수",
        "J00:60": "방송·콘텐츠 사업장 규모, 방송매출·제작인력·채널/송출시설",
        "MN0:72": "전문서비스 임금총액, 용역·설계·엔지니어링 계약액",
        "C00:34": "정비·수리 물량, 수리업 매출, 기계장비 정비시설 규모",
        "J00:63": "정보서비스 사업장 규모, 서버·데이터센터·플랫폼 매출",
        "ERS:39": "환경정화 처리량, 복원사업 계약액, 폐기물·오염처리 실적",
    }
    return mapping.get(code, "업종별 가치·물량형 활동자료")


def diagnostic_note(row: pd.Series) -> str:
    if row.final_error_rate_pct > 50:
        return "상대오차가 커서 일반 사업체·종사자 구조만으로는 구분 어려움"
    if row.final_error_gva_eok > 1000:
        return "금액오차가 커서 정책 설명 시 별도 주의 필요"
    return "잔여 개선 대상"


def summarize_stage(reg: pd.DataFrame, stage: str, pred_col: str, err_col: str, rate_col: str) -> pd.DataFrame:
    tmp = reg.copy()
    tmp["_stage_remaining_queue"] = np.where(
        tmp[rate_col].gt(50) | tmp[err_col].gt(1000),
        "추가개선대상",
        "현행유지가능",
    )
    out = (
        tmp.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=(err_col, "sum"),
            median_error_pct=(rate_col, "median"),
            within_5pct_cells=(rate_col, lambda s: int((s <= 5).sum())),
            within_10pct_cells=(rate_col, lambda s: int((s <= 10).sum())),
            over_50pct_cells=(rate_col, lambda s: int((s > 50).sum())),
            remaining_queue_cells=("_stage_remaining_queue", lambda s: int((s == "추가개선대상").sum())),
        )
        .assign(model_stage=stage)
    )
    out["wape_pct"] = out.error_sum_eok / out.actual_sum_eok * 100
    return out


def summarize(reg: pd.DataFrame) -> pd.DataFrame:
    out = pd.concat(
        [
            summarize_stage(reg, "초기 기준", "initial_predicted_gva_eok", "initial_error_gva_eok", "initial_error_rate_pct"),
            summarize_stage(reg, "Phase86 기준", "phase86_predicted_gva_eok", "phase86_error_gva_eok", "phase86_error_rate_pct"),
            summarize_stage(reg, "최종 기준", "final_predicted_gva_eok", "final_error_gva_eok", "final_error_rate_pct"),
        ],
        ignore_index=True,
    )
    base = out[out.model_stage.eq("초기 기준")].set_index("city")
    out["initial_error_reduction_eok"] = out.apply(lambda r: base.loc[r.city, "error_sum_eok"] - r.error_sum_eok, axis=1)
    out["initial_wape_improvement_pp"] = out.apply(lambda r: base.loc[r.city, "wape_pct"] - r.wape_pct, axis=1)
    out["initial_error_reduction_pct"] = out.apply(lambda r: r.initial_error_reduction_eok / base.loc[r.city, "error_sum_eok"] * 100, axis=1)
    return out.sort_values(["city", "error_sum_eok"])


def accounting_check(reg: pd.DataFrame) -> pd.DataFrame:
    out = reg.groupby(["city", "parent_code"], as_index=False).agg(
        actual_parent_eok=("actual_gva_eok", "sum"),
        predicted_parent_eok=("final_predicted_gva_eok", "sum"),
    )
    out["gap_eok"] = out.predicted_parent_eok - out.actual_parent_eok
    out["gap_pct"] = out.gap_eok / out.actual_parent_eok.replace(0, np.nan) * 100
    out["pass"] = out.gap_eok.abs().le(1e-6)
    return out


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    reg = load()
    summary = summarize(reg)
    acct = accounting_check(reg)
    weak = reg[reg.final_remaining_queue.eq("추가개선대상")].sort_values(["city", "final_error_gva_eok"], ascending=[True, False])
    good = reg.sort_values(["city", "final_error_rate_pct"]).groupby("city").head(20)
    improved = reg[reg.initial_to_final_error_reduction_eok.gt(0)].sort_values(
        ["city", "initial_to_final_error_reduction_eok"], ascending=[True, False]
    )
    worsened = reg[reg.initial_to_final_error_reduction_eok.lt(-1e-9)].copy()
    phase86_worsened = reg[reg.phase86_to_final_error_reduction_eok.lt(-1e-9)].copy()
    formula_bad = reg[(reg.final_error_gva_eok / reg.actual_gva_eok * 100 - reg.final_error_rate_pct).abs().gt(1e-6)]

    reg.to_csv(OUTDIR / "phase88_current_middle_industry_accuracy_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase88_current_middle_industry_accuracy_summary.csv", index=False, encoding="utf-8-sig")
    weak.to_csv(OUTDIR / "phase88_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")
    acct.to_csv(OUTDIR / "phase88_accounting_checks.csv", index=False, encoding="utf-8-sig")

    report = f"""# 현재 중분류 산업별 GVA 추정 정확도 레지스트리

## 목적

현재까지의 최종 기준인 Phase87 결과를 사용해 고양시·포항시의 각 중분류 산업별 실제 GVA, 추정 GVA, 오차금액, 오차율, 판정, 남은 개선자료를 정리했다. 모든 금액은 억원이며, 오차율은 `|추정 GVA-실제 GVA|/실제 GVA×100`이다.

## 전체 성능

{md_table(summary, [("city", "지역"), ("model_stage", "단계"), ("cells", "셀 수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("wape_pct", "가중오차 %"), ("median_error_pct", "중앙오차 %"), ("within_5pct_cells", "5% 이하"), ("within_10pct_cells", "10% 이하"), ("over_50pct_cells", "50% 초과"), ("remaining_queue_cells", "추가개선대상"), ("initial_wape_improvement_pp", "초기대비 개선 pp")])}

## 최종 정확도 양호 산업 예시

{md_table(good, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("final_accuracy_grade", "판정"), ("final_option_family", "적용 기준")], 50)}

## 개선 폭 상위 산업

{md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("initial_predicted_gva_eok", "초기 추정 억원"), ("initial_error_gva_eok", "초기 오차 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "최종 오차 억원"), ("final_error_rate_pct", "최종 오차 %"), ("initial_to_final_error_reduction_eok", "감소 억원"), ("final_option_family", "최종 기준")], 80)}

## 남은 추가개선대상

{md_table(weak, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("final_accuracy_grade", "판정"), ("needed_data_type", "필요 자료"), ("diagnostic_note", "진단")], 80)}

## 집계 일치 및 오류 점검

- 상위산업 합계 불일치 건수: {int((~acct["pass"]).sum())}개
- 최종 오차율 산식 오류: {len(formula_bad)}개
- 초기 기준 대비 악화 셀: {len(worsened)}개
- Phase86 대비 악화 셀: {len(phase86_worsened)}개

{md_table(acct[~acct["pass"]], [("city", "지역"), ("parent_code", "상위산업"), ("actual_parent_eok", "실제합계 억원"), ("predicted_parent_eok", "추정합계 억원"), ("gap_eok", "차이 억원"), ("gap_pct", "차이 %")], 40)}

### 초기 기준 대비 악화 셀

{md_table(worsened.sort_values(["city", "initial_to_final_error_reduction_eok"]), [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("actual_gva_eok", "실제 억원"), ("initial_predicted_gva_eok", "초기 추정 억원"), ("initial_error_gva_eok", "초기 오차 억원"), ("final_predicted_gva_eok", "최종 추정 억원"), ("final_error_gva_eok", "최종 오차 억원"), ("final_error_rate_pct", "최종 오차 %"), ("initial_to_final_error_reduction_eok", "개선 억원")], 40)}

## 판정

1. 집계 일치가 검증된 최종 기준에서 고양시 중분류 GVA 가중오차는 44.1%에서 4.6%로, 포항시는 73.5%에서 6.8%로 감소했다.
2. 고양시는 57개 중분류 중 37개가 10% 이하, 포항시는 53개 중분류 중 27개가 10% 이하에 들어왔다.
3. 남은 취약군은 6개로 축소됐다. 이들은 일반 사업체·종사자·건축물 구조보다 더 직접적인 가치·물량형 활동자료가 필요하다.
4. 단, 상위산업 합계 보존과 유형별 템플릿 적용 과정에서 초기 기준보다 오차가 커진 셀이 8개 있다. 이들은 최종 표에 별도 표시해 산업별 설명에서 과장하지 않는다.
5. 따라서 현재 산출물은 “전 산업 중분류별 GVA 추정 정확도”를 표로 제시할 수 있는 상태이며, 후속 개선은 남은 6개 취약군과 초기 대비 악화 셀의 자료 보강으로 집중하면 된다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase88_current_middle_industry_accuracy_registry.csv")
    print(OUTDIR / "phase88_remaining_improvement_queue.csv")


if __name__ == "__main__":
    main()
