#!/usr/bin/env python3
"""Phase110: actionable plan for >10% refined middle-industry GVA errors.

The user asked to defer the 10-sigungu generalization pilot and focus on
Goyang/Pohang industries whose post-publication refined error still exceeds
10%.  This phase does three things:

1. freeze the current >10% queue from the Phase105 no-worse registry;
2. screen newly collected/available free sources without claiming unsafe gains;
3. write a concrete data/action plan for the remaining industries.

This script intentionally does not fit cell-by-cell corrections using the
middle-industry actual values.  Candidate source adoption is accepted only when
it improves a whole city×parent-industry block under a predeclared guardrail.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUTDIR = DATA / "phase110_goyang_pohang_gt10_action_plan"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase110_goyang_pohang_gt10_action_plan.md"

BASE_REGISTRY = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"
PHASE109_DIR = DATA / "phase109_goyang_pohang_gt10_precision_improvement"
POHANG_BUSINESS_2024 = DATA / "partial_stats_phase43_pohang_gu_sales_cv_detail.csv"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "pp", "비")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals: list[str] = []
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


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE_REGISTRY)
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["gt10_refined"] = df.no_worse_refined_error_rate_pct.gt(10)
    return df


def summarise_gt10(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    weak = base[base.gt10_refined].copy()
    weak_summary = (
        weak.groupby(["city", "cause_group"], as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("no_worse_refined_error_gva_eok", "sum"),
            median_error_pct=("no_worse_refined_error_rate_pct", "median"),
            max_error_pct=("no_worse_refined_error_rate_pct", "max"),
            top_industries=("middle_label", lambda s: ", ".join(s.head(4))),
        )
        .sort_values(["city", "error_sum_eok"], ascending=[True, False])
    )
    weak_detail = weak.sort_values(["city", "no_worse_refined_error_gva_eok"], ascending=[True, False])
    return weak_summary, weak_detail


def goyang_source_audit() -> pd.DataFrame:
    rows = [
        {
            "city": "고양시",
            "source": "고양시 사전정보공표 지역산업 통계: 사업체 총괄",
            "local_path": "data/raw/phase109_goyang_business_summary_2023.xlsx",
            "grain": "산업대분류×고양시",
            "usable_for_gt10": "부분사용",
            "decision": "중분류 10% 초과 개선에는 미채택",
            "reason": "대분류 사업체수·종사자만 있어 방송업·협회단체·중분류 제조업 등 내부 배분을 직접 바꾸지 못함",
        },
        {
            "city": "고양시",
            "source": "고양시 사전정보공표 지역산업 통계: 산업별 사업체수 및 종사자수",
            "local_path": "data/raw/phase109_goyang_industry_est_emp_2023.xlsx",
            "grain": "구×산업대분류",
            "usable_for_gt10": "부분사용",
            "decision": "중분류 10% 초과 개선에는 미채택",
            "reason": "구 단위 공간배분에는 쓸 수 있으나 중분류별 GVA 격차 축소에는 정보량 부족",
        },
        {
            "city": "고양시",
            "source": "고양시 사전정보공표 지역산업 통계: 종사자규모별 사업체수 및 종사자수",
            "local_path": "data/raw/phase109_goyang_size_est_emp_2023.xlsx",
            "grain": "구×종사자규모",
            "usable_for_gt10": "부분사용",
            "decision": "중분류 10% 초과 개선에는 미채택",
            "reason": "중분류 식별자가 없어 취약 중분류별 배분식에 직접 투입 불가",
        },
    ]
    return pd.DataFrame(rows)


def manufacturing_audit() -> pd.DataFrame:
    rec_path = PHASE109_DIR / "phase109_manufacturing_blend_recommendation.csv"
    if not rec_path.exists():
        return pd.DataFrame()
    rec = pd.read_csv(rec_path)
    out = rec.copy()
    out["source"] = "KOSIS 광업제조업조사 시군구×제조업 중분류"
    out["decision"] = np.where(
        out.recommendation.eq("reject_no_safe_improvement"),
        "미채택",
        "운영 후보·대외 성능값 미채택",
    )
    out["reason"] = np.where(
        out.city.eq("고양시"),
        "소량 혼합도 제조업 총오차와 악화 셀을 늘림",
        "제조업 총오차는 줄지만 10% 초과 셀이 늘고 악화 셀이 남음",
    )
    return out


def screen_pohang_business_2024(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Screen Pohang 2024 middle-industry sales/employees/establishments blends.

    Acceptable block rule:
    - only city×parent blocks with at least one >10% refined cell are considered;
    - block absolute error must decline;
    - >10% cell count must not increase;
    - no individual cell in the block may worsen.
    """
    src = pd.read_csv(POHANG_BUSINESS_2024)
    src["middle_code"] = src.division_code.astype(int).astype(str).str.zfill(2)
    src = src.groupby("middle_code", as_index=False)[["sales", "employees", "establishments"]].sum()
    ph = base[base.city.eq("포항시")].copy()
    rows: list[dict] = []
    detail_frames: list[pd.DataFrame] = []
    alphas = [0.05, 0.10, 0.20, 0.33, 0.50, 0.75, 1.00]
    for parent, g in ph.groupby("parent_code", sort=False):
        if not g.gt10_refined.any():
            continue
        x = g.merge(src, on="middle_code", how="left")
        old_err = x.no_worse_refined_error_gva_eok.to_numpy(float)
        old_rate = x.no_worse_refined_error_rate_pct.to_numpy(float)
        old_gt10 = int((old_rate > 10).sum())
        parent_actual = float(x.actual_gva_eok.sum())
        for metric in ["sales", "employees", "establishments"]:
            indicator = pd.to_numeric(x[metric], errors="coerce").fillna(0.0).to_numpy(float)
            if indicator.sum() <= 0:
                continue
            indicator_pred = indicator / indicator.sum() * parent_actual
            for alpha in alphas:
                pred = (1 - alpha) * x.no_worse_refined_predicted_gva_eok.to_numpy(float) + alpha * indicator_pred
                err = np.abs(pred - x.actual_gva_eok.to_numpy(float))
                rate = err / x.actual_gva_eok.replace(0, np.nan).to_numpy(float) * 100
                row = {
                    "city": "포항시",
                    "parent_code": parent,
                    "metric": metric,
                    "alpha": alpha,
                    "baseline_error_eok": float(old_err.sum()),
                    "candidate_error_eok": float(err.sum()),
                    "error_reduction_eok": float(old_err.sum() - err.sum()),
                    "baseline_gt10_cells": old_gt10,
                    "candidate_gt10_cells": int((rate > 10).sum()),
                    "worsened_cells": int((err > old_err + 1e-9).sum()),
                    "max_worsen_eok": float(np.max(err - old_err)),
                }
                row["accepted"] = (
                    row["error_reduction_eok"] > 1e-9
                    and row["candidate_gt10_cells"] <= row["baseline_gt10_cells"]
                    and row["worsened_cells"] == 0
                )
                rows.append(row)
                d = x[
                    [
                        "city",
                        "parent_code",
                        "middle_code",
                        "middle_label",
                        "actual_gva_eok",
                        "no_worse_refined_predicted_gva_eok",
                        "no_worse_refined_error_gva_eok",
                        "no_worse_refined_error_rate_pct",
                    ]
                ].copy()
                d["metric"] = metric
                d["alpha"] = alpha
                d["candidate_predicted_gva_eok"] = pred
                d["candidate_error_gva_eok"] = err
                d["candidate_error_rate_pct"] = rate
                d["candidate_error_delta_eok"] = err - old_err
                detail_frames.append(d)
    screen = pd.DataFrame(rows)
    if not screen.empty:
        screen = screen.sort_values(["accepted", "error_reduction_eok"], ascending=[False, False])
    detail = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame()
    return screen, detail


def improvement_queue(weak_detail: pd.DataFrame) -> pd.DataFrame:
    priority = []
    for _, row in weak_detail.iterrows():
        label = str(row.middle_label)
        city = str(row.city)
        cause = str(row.cause_group)
        if city == "고양시" and ("협회" in label or "단체" in label):
            source = "고양시 지방보조금·비영리민간단체 등록/결산 또는 공익법인 결산자료"
            method = "협회·단체 총량을 사업체수 대신 보조금·수입·회원규모로 재배분"
        elif city == "고양시" and ("방송" in label or "영상" in label or "컴퓨터" in label):
            source = "방송통신위원회 방송사업자, 문체부 콘텐츠산업 지역자료, 고양산업진흥원 콘텐츠/ICT 기업자료"
            method = "정보통신 내부를 사업체수보다 매출·제작/송출/ICT기업 규모로 재배분"
        elif city == "고양시" and ("스포츠" in label or "오락" in label):
            source = "고양시 공공체육시설·공연장·관광/문화시설 이용실적, LOCALDATA 체육·오락 인허가"
            method = "시설 수가 아니라 이용량·좌석/면적·운영예산을 결합"
        elif city == "고양시" and ("제조업" in label or "수리업" in label):
            source = "전력사용량 또는 공장등록 면적/종업원수의 중분류 매핑 보강"
            method = "KOSIS 제조업 부가가치 단독 대체는 금지, 공장규모+전력+기준추정의 보수 혼합만 허용"
        elif city == "포항시" and row.parent_code == "K00":
            source = "금융기관 점포별 예수금·대출금 또는 금융점포 규모 자료"
            method = "금융·보험 내부를 단순 사업체수 대신 금융취급액 또는 점포규모로 재배분"
        elif city == "포항시" and ("건축기술" in label or "엔지니어링" in label):
            source = "건축허가·착공·사용승인 면적, 조달/계약정보의 설계·감리·엔지니어링 계약액"
            method = "전문서비스 내부를 건설활동 파생 계약액으로 재배분"
        elif city == "포항시" and ("사업시설" in label or "임대업" in label):
            source = "사업시설관리·임대업 계약액, 건축물 용도별 연면적, 조달 위탁계약"
            method = "사업체수 대신 관리대상 면적·계약액으로 재배분"
        elif city == "포항시" and ("제조업" in label or "수리업" in label):
            source = "대형사업장 전력·생산능력·공장면적, 광업제조업조사 출하/부가가치의 제한 혼합"
            method = "대기업 집중 제조업은 매출·부가가치 대체지표를 5~10% 이내로만 혼합하고 악화방지 적용"
        elif "수도" in label or "하수" in label or "환경" in label:
            source = "상하수도 처리량·폐기물 처리량·환경정화 계약액"
            method = "환경·공공서비스 내부를 처리량과 위탁계약액으로 재배분"
        else:
            source = str(row.required_next_data)
            method = f"{cause} 전용 활동지표 수집 후 city×상위산업 합계 보존 검증"
        priority.append(
            {
                "city": row.city,
                "parent_code": row.parent_code,
                "middle_code": row.middle_code,
                "middle_label": row.middle_label,
                "actual_gva_eok": row.actual_gva_eok,
                "current_error_eok": row.no_worse_refined_error_gva_eok,
                "current_error_pct": row.no_worse_refined_error_rate_pct,
                "priority_source": source,
                "improvement_method": method,
            }
        )
    return pd.DataFrame(priority)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_base()
    weak_summary, weak_detail = summarise_gt10(base)
    goyang_audit = goyang_source_audit()
    mfg_audit = manufacturing_audit()
    pohang_screen, pohang_detail = screen_pohang_business_2024(base)
    queue = improvement_queue(weak_detail)

    candidate_status = []
    if not pohang_screen.empty:
        target = pohang_screen[pohang_screen.parent_code.isin(["C00", "ERS", "J00", "K00", "MN0"])]
        safe = target[target.accepted]
        candidate_status.append(
            {
                "candidate": "포항 2024 사업체조사 매출·종사자·사업체수 혼합",
                "target": "포항 잔여 10% 초과 부모산업",
                "screened_options": len(target),
                "accepted_options": len(safe),
                "decision": "안전 채택 없음",
                "reason": "일부 총오차 감소 후보도 10% 초과 셀 증가 또는 개별 셀 악화를 동반",
            }
        )
    candidate_status.append(
        {
            "candidate": "고양 2023 사업체 대분류/규모 공개자료",
            "target": "고양 잔여 10% 초과 중분류",
            "screened_options": 3,
            "accepted_options": 0,
            "decision": "미채택",
            "reason": "중분류 식별자가 없어 취약 중분류 내부 배분을 바꾸는 검증 불가",
        }
    )
    candidate_status.append(
        {
            "candidate": "KOSIS 광업제조업조사 중분류 부가가치/사업체/종사자",
            "target": "고양·포항 제조업 잔여 10% 초과 중분류",
            "screened_options": int(len(mfg_audit)) if not mfg_audit.empty else 0,
            "accepted_options": 0,
            "decision": "대외 채택 없음",
            "reason": "고양은 악화, 포항은 일부 개선하나 악화 셀과 10% 초과 셀 증가가 남음",
        }
    )
    status = pd.DataFrame(candidate_status)

    weak_summary.to_csv(OUTDIR / "phase110_gt10_summary_by_cause.csv", index=False, encoding="utf-8-sig")
    weak_detail.to_csv(OUTDIR / "phase110_gt10_current_detail.csv", index=False, encoding="utf-8-sig")
    goyang_audit.to_csv(OUTDIR / "phase110_goyang_new_source_audit.csv", index=False, encoding="utf-8-sig")
    if not mfg_audit.empty:
        mfg_audit.to_csv(OUTDIR / "phase110_manufacturing_source_audit.csv", index=False, encoding="utf-8-sig")
    pohang_screen.to_csv(OUTDIR / "phase110_pohang_2024_business_screen.csv", index=False, encoding="utf-8-sig")
    pohang_detail.to_csv(OUTDIR / "phase110_pohang_2024_business_detail.csv", index=False, encoding="utf-8-sig")
    queue.to_csv(OUTDIR / "phase110_remaining_improvement_queue.csv", index=False, encoding="utf-8-sig")
    status.to_csv(OUTDIR / "phase110_candidate_status.csv", index=False, encoding="utf-8-sig")

    report = f"""# 고양·포항 정밀오차 10% 초과 업종 개선 방안

## 범위

- 10개 시군구 일반화 검증은 고양시·포항시 산출물 마무리 후 재개한다.
- 이번 단계는 고양·포항의 `중분류 총부가가치(GVA)` 정밀오차 10% 초과 업종에 한정한다.
- 실제값을 보고 셀별로 맞추는 보정은 성능 개선으로 보지 않는다. 후보자료는 city×상위산업 묶음 단위로 총오차, 10% 초과 셀, 개별 악화 여부를 동시에 본다.

## 현재 10% 초과 잔여군

{md_table(weak_summary, [("city", "지역"), ("cause_group", "원인군"), ("cells", "중분류 개"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "현재오차 억원"), ("median_error_pct", "중앙오차 %"), ("max_error_pct", "최대오차 %"), ("top_industries", "대표 중분류")], 80)}

## 새로 확인한 자료의 채택 판정

{md_table(status, [("candidate", "후보자료"), ("target", "대상"), ("screened_options", "검토조합"), ("accepted_options", "채택조합"), ("decision", "판정"), ("reason", "사유")])}

## 고양시 신규 공개자료 감사

{md_table(goyang_audit, [("source", "자료"), ("grain", "해상도"), ("usable_for_gt10", "사용가능성"), ("decision", "판정"), ("reason", "사유")])}

## 제조업 보조자료 감사

{md_table(mfg_audit, [("city", "지역"), ("source", "자료"), ("year", "자료연도"), ("metric", "지표"), ("alpha", "혼합비"), ("baseline_error_eok", "기준 제조업오차 억원"), ("candidate_error_eok", "후보 제조업오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("worse_cells", "악화 셀"), ("gt10_before", "기준 10%초과"), ("gt10_after", "후보 10%초과"), ("decision", "판정"), ("reason", "사유")])}

## 포항 2024 사업체조사 후보 스크린

상위산업 총오차가 줄어도 개별 취약 셀을 더 만들면 채택하지 않았다. 특히 남은 취약 부모산업(C00·ERS·J00·K00·MN0)에서는 안전 채택 조합이 없었다.

{md_table(pohang_screen[pohang_screen.parent_code.isin(["C00", "ERS", "J00", "K00", "MN0"])].head(30), [("parent_code", "상위산업"), ("metric", "지표"), ("alpha", "혼합비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt10_cells", "기준 10%초과"), ("candidate_gt10_cells", "후보 10%초과"), ("worsened_cells", "악화 셀"), ("accepted", "채택")], 30)}

## 남은 업종별 개선 실행안

{md_table(queue, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("current_error_eok", "현재오차 억원"), ("current_error_pct", "현재오차 %"), ("priority_source", "필요 무료자료"), ("improvement_method", "개선 방식")], 80)}

## 결론

1. 지금 수집된 무료자료만으로는 고양·포항 잔여 10% 초과 업종을 안전하게 더 낮추는 채택 후보가 없다.
2. 고양은 중분류 매출·임금·활동규모 자료 부재가 병목이다. 새로 받은 고양 공개파일은 대분류/구 단위라 포스터의 공간 설명에는 도움되지만, 중분류 정밀오차 개선에는 부족하다.
3. 포항은 2024 사업체조사 매출표가 강하지만, 남은 취약 업종에서는 개별 악화가 동반되어 최종값에 넣으면 안 된다.
4. 다음 실질 개선은 자료수집 방향이 명확하다. 고양은 협회·단체/방송·콘텐츠/스포츠·오락/전문서비스의 매출·예산·이용량 자료, 포항은 금융취급액/건축·엔지니어링 계약액/시설관리 면적·계약액/환경처리량 자료가 필요하다.
5. 고양·포항 작업이 마무리되면 10개 시군구 일반화 검증을 다시 진행해야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
