#!/usr/bin/env python3
"""Phase123: test PPS procurement notices as flash GVA activity indicators.

Phase122 collected PPS/Nara bid notices.  This script converts those notices
into city×KSIC-middle public-demand indicators and evaluates whether they
improve Goyang/Pohang middle-industry GVA allocation under the existing
Phase120 flash-safe framework.

Important: PPS notices are not GVA actuals.  They are only activity indicators.
Middle GVA actuals are used only by the inherited evaluator for candidate
screening/validation, not as allocation inputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import run_phase115_flash_gt20_source_improvement as p115
import run_phase116_expanded_flash_gt20_improvement as p116
import run_phase120_finance_procurement_source_integration as p120


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase123_pps_procurement_gva_improvement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase123_pps_procurement_gva_improvement.md"
PPS = DATA / "phase122_pps_bid_notices" / "phase122_pps_goyang_pohang_combined_notices.csv"
P120_STRICT = DATA / "phase120_finance_procurement_source_integration" / "phase120_strict_flash_registry.csv"


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0.0)


def text(row: pd.Series) -> str:
    fields = [
        "bidNtceNm",
        "ntceInsttNm",
        "dminsttNm",
        "srvceDivNm",
        "pubPrcrmntLrgClsfcNm",
        "pubPrcrmntMidClsfcNm",
        "pubPrcrmntClsfcNm",
        "rgnLmtBidLocplcJdgmBssNm",
    ]
    return " ".join(str(row.get(c, "") or "") for c in fields)


def classify_notice(row: pd.Series) -> tuple[str | None, str | None, str]:
    t = text(row)
    op = str(row.get("op", ""))

    if "cnstwk" in op:
        if any(k in t for k in ["전기", "소방", "통신", "기계", "설비", "보수", "유지", "개선", "철거", "조경", "실내", "인테리어", "전문"]):
            return "F00", "42", "공사-전문직별 공사업"
        return "F00", "41", "공사-종합 건설업"

    if "servc" in op:
        if any(k in t for k in ["연구개발", "R&D", "알앤디"]):
            return "MN0", "70", "용역-연구개발업"
        if any(k in t for k in ["건축", "엔지니어링", "설계", "감리", "측량", "기술진단", "안전진단", "과학기술"]):
            return "MN0", "72", "용역-건축기술·엔지니어링"
        if any(k in t for k in ["학술", "연구", "조사", "분석", "평가", "컨설팅", "자문"]):
            return "MN0", "73", "용역-전문과학기술서비스"
        if any(k in t for k in ["청소", "경비", "시설관리", "방역", "소독", "위생", "건물관리", "조경관리", "유지관리"]):
            return "MN0", "74", "용역-사업시설관리"
        if any(k in t for k in ["콜센터", "인력", "파견", "운영대행", "행사", "대행", "사무지원", "교육운영"]):
            return "MN0", "75", "용역-사업지원서비스"
        if any(k in t for k in ["소프트웨어", "정보시스템", "시스템", "전산", "프로그램", "플랫폼", "DB", "데이터베이스"]):
            return "J00", "62", "용역-컴퓨터프로그래밍·시스템통합"
        if any(k in t for k in ["통신", "네트워크", "인터넷"]):
            return "J00", "61", "용역-통신"
        if any(k in t for k in ["폐기물", "재활용", "수집운반", "처리"]):
            return "ERS", "38", "용역-폐기물처리"
        if any(k in t for k in ["하수", "폐수", "분뇨"]):
            return "ERS", "37", "용역-하수폐수처리"
        if any(k in t for k in ["운송", "버스", "택시", "차량임차", "전세버스"]):
            return "H00", "49", "용역-육상운송"
        if any(k in t for k in ["문화", "공연", "예술", "전시", "축제"]):
            return "ERS", "90", "용역-창작예술"
        return "MN0", "75", "용역-기타 사업지원 후보"

    if "thng" in op:
        if any(k in t for k in ["컴퓨터", "서버", "소프트웨어", "정보", "전산"]):
            return "J00", "62", "물품-정보시스템 장비"
        if any(k in t for k in ["의료", "병원", "보건"]):
            return "Q00", "86", "물품-보건"
        # 물품은 GVA 중분류 활동과의 연결이 약하므로 기본적으로 제외한다.
        return None, None, "물품-분류보류"

    return None, None, "분류보류"


def pps_indicators() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not PPS.exists():
        return pd.DataFrame(), pd.DataFrame()
    df = pd.read_csv(PPS, dtype={"middle_code": str}, low_memory=False)
    df["bidNtceDt_ts"] = pd.to_datetime(df.get("bidNtceDt"), errors="coerce")
    df = df[df["bidNtceDt_ts"].notna() & df["bidNtceDt_ts"].le(pd.Timestamp("2023-09-30 23:59:59"))].copy()
    df["amount"] = num(df.get("presmptPrce", pd.Series(0, index=df.index)))
    alt = num(df.get("asignBdgtAmt", pd.Series(0, index=df.index)))
    df.loc[df["amount"].le(0), "amount"] = alt[df["amount"].le(0)]

    classified = []
    for _, r in df.iterrows():
        parent, middle, label = classify_notice(r)
        item = r.to_dict()
        item.update({"parent_code": parent, "middle_code": middle, "pps_class_label": label})
        classified.append(item)
    cdf = pd.DataFrame(classified)
    audit = (
        cdf.groupby(["city", "op", "pps_class_label"], dropna=False, as_index=False)
        .agg(notices=("bidNtceNo", "count"), amount_eok=("amount", lambda s: float(s.sum()) / 1e8))
        .sort_values(["city", "op", "amount_eok"], ascending=[True, True, False])
    )
    use = cdf[cdf["parent_code"].notna() & cdf["middle_code"].notna() & cdf["amount"].gt(0)].copy()
    if use.empty:
        return pd.DataFrame(), audit

    agg = (
        use.groupby(["city", "parent_code", "middle_code", "pps_class_label"], as_index=False)
        .agg(notices=("bidNtceNo", "count"), amount=("amount", "sum"))
    )
    rows: list[dict[str, Any]] = []
    for _, r in agg.iterrows():
        for metric, value, unit, source_suffix, label_suffix in [
            ("amount", float(r.amount), "원", "amount", "추정가격·배정예산 합계"),
            ("notices", float(r.notices), "건", "notices", "공고 건수"),
        ]:
            if value <= 0:
                continue
            rows.append(
                {
                    "city": r.city,
                    "parent_code": r.parent_code,
                    "middle_code": str(r.middle_code).zfill(2),
                    "source_id": f"flash_pps_procurement_{source_suffix}",
                    "source_label": f"조달청 공공발주 {label_suffix}",
                    "indicator_raw_value": value,
                    "indicator_value": float(np.log1p(value)),
                    "allocation_value": value,
                    "unit": unit,
                    "timing_track": "속보성",
                    "timing_note": "조달청 나라장터 입찰공고; bidNtceDt<=2023-09-30만 사용, 실제 GVA가 아닌 공공발주 활동지표",
                }
            )
            rows.append(
                {
                    "city": r.city,
                    "parent_code": r.parent_code,
                    "middle_code": str(r.middle_code).zfill(2),
                    "source_id": f"flash_pps_procurement_{source_suffix}_{r.parent_code}",
                    "source_label": f"조달청 공공발주 {label_suffix}({r.parent_code})",
                    "indicator_raw_value": value,
                    "indicator_value": float(np.log1p(value)),
                    "allocation_value": value,
                    "unit": unit,
                    "timing_track": "속보성",
                    "timing_note": "상위산업별 조달청 공공발주 활동지표",
                }
            )

    out = pd.DataFrame(rows)
    out = (
        out.groupby(["city", "parent_code", "middle_code", "source_id", "source_label", "unit", "timing_track", "timing_note"], as_index=False)
        .agg(indicator_raw_value=("indicator_raw_value", "sum"), indicator_value=("indicator_value", "sum"), allocation_value=("allocation_value", "sum"))
    )
    return out, audit


def select(screen: pd.DataFrame) -> pd.DataFrame:
    if screen.empty:
        return screen
    selected = p120.select(screen)
    if selected.empty:
        return selected
    selected = selected.copy()
    selected.loc[selected["option_id"].astype(str).str.contains("pps_procurement", na=False), "public_claim_status"] = "속보 후보: 조달청 공공발주"
    return selected


def apply_named(base: pd.DataFrame, selected: pd.DataFrame, detail: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = p115.apply(base, selected, detail)
    return out.rename(
        columns={
            "phase115_flash_predicted_gva_eok": f"{prefix}_predicted_gva_eok",
            "phase115_flash_error_gva_eok": f"{prefix}_error_gva_eok",
            "phase115_flash_error_rate_pct": f"{prefix}_error_rate_pct",
            "phase115_option_id": f"{prefix}_option_id",
            "phase115_flash_error_reduction_eok": f"{prefix}_error_reduction_eok",
        }
    )


def summarize(reg: pd.DataFrame, prefix: str) -> pd.DataFrame:
    rows = []
    for city, g in reg.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        old = float(g["flash_baseline_error_gva_eok"].sum())
        new = float(g[f"{prefix}_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "actual_sum_eok": actual,
                "baseline_error_eok": old,
                "baseline_wape_pct": old / actual * 100,
                "phase123_error_eok": new,
                "phase123_wape_pct": new / actual * 100,
                "error_reduction_vs_initial_eok": old - new,
                "wape_reduction_vs_initial_pp": (old - new) / actual * 100,
                "baseline_gt20_cells": int((g["flash_baseline_error_rate_pct"] > 20).sum()),
                "phase123_gt20_cells": int((g[f"{prefix}_error_rate_pct"] > 20).sum()),
                "baseline_gt10_cells": int((g["flash_baseline_error_rate_pct"] > 10).sum()),
                "phase123_gt10_cells": int((g[f"{prefix}_error_rate_pct"] > 10).sum()),
                "worsened_vs_initial_cells": int((g[f"{prefix}_error_gva_eok"] > g["flash_baseline_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def incremental_vs_phase120(reg: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not P120_STRICT.exists():
        return pd.DataFrame(), pd.DataFrame()
    p120reg = pd.read_csv(P120_STRICT, dtype={"middle_code": str})
    p120reg["middle_code"] = p120reg["middle_code"].astype(str).str.zfill(2)
    cols = [
        "city",
        "parent_code",
        "middle_code",
        "phase120_strict_flash_predicted_gva_eok",
        "phase120_strict_flash_error_gva_eok",
        "phase120_strict_flash_error_rate_pct",
        "phase120_strict_flash_option_id",
    ]
    m = reg.merge(p120reg[cols], on=["city", "parent_code", "middle_code"], how="left")
    m["phase123_incremental_error_reduction_eok"] = m["phase120_strict_flash_error_gva_eok"] - m["phase123_flash_error_gva_eok"]
    m["phase123_incremental_error_rate_change_pp"] = m["phase123_flash_error_rate_pct"] - m["phase120_strict_flash_error_rate_pct"]
    rows = []
    for city, g in m.groupby("city", sort=False):
        p120err = float(g["phase120_strict_flash_error_gva_eok"].sum())
        p123err = float(g["phase123_flash_error_gva_eok"].sum())
        actual = float(g["actual_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "phase120_error_eok": p120err,
                "phase120_wape_pct": p120err / actual * 100,
                "phase123_error_eok": p123err,
                "phase123_wape_pct": p123err / actual * 100,
                "incremental_reduction_eok": p120err - p123err,
                "incremental_reduction_pp": (p120err - p123err) / actual * 100,
                "phase120_gt20_cells": int((g["phase120_strict_flash_error_rate_pct"] > 20).sum()),
                "phase123_gt20_cells": int((g["phase123_flash_error_rate_pct"] > 20).sum()),
                "phase120_gt10_cells": int((g["phase120_strict_flash_error_rate_pct"] > 10).sum()),
                "phase123_gt10_cells": int((g["phase123_flash_error_rate_pct"] > 10).sum()),
                "worsened_vs_phase120_cells": int((g["phase123_flash_error_gva_eok"] > g["phase120_strict_flash_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return m, pd.DataFrame(rows)


def conservative_no_worse_vs_phase120(reg: pd.DataFrame, inc_detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep Phase120 values except PPS-updated parent blocks with no cell worsening."""
    if inc_detail.empty:
        return pd.DataFrame(), pd.DataFrame()
    out = inc_detail.copy()
    out["phase123_conservative_predicted_gva_eok"] = out["phase120_strict_flash_predicted_gva_eok"]
    out["phase123_conservative_error_gva_eok"] = out["phase120_strict_flash_error_gva_eok"]
    out["phase123_conservative_error_rate_pct"] = out["phase120_strict_flash_error_rate_pct"]
    out["phase123_conservative_option_id"] = out["phase120_strict_flash_option_id"]

    adopted_blocks: list[dict[str, Any]] = []
    pps_blocks = reg[reg["phase123_flash_option_id"].astype(str).str.contains("pps_procurement", na=False)][["city", "parent_code"]].drop_duplicates()
    for _, b in pps_blocks.iterrows():
        mask = inc_detail["city"].eq(b.city) & inc_detail["parent_code"].eq(b.parent_code)
        block = inc_detail[mask]
        if block.empty:
            continue
        worsened = int((block["phase123_flash_error_gva_eok"] > block["phase120_strict_flash_error_gva_eok"] + 1e-9).sum())
        p120_err = float(block["phase120_strict_flash_error_gva_eok"].sum())
        p123_err = float(block["phase123_flash_error_gva_eok"].sum())
        if worsened == 0 and p123_err < p120_err:
            out.loc[mask, "phase123_conservative_predicted_gva_eok"] = out.loc[mask, "phase123_flash_predicted_gva_eok"]
            out.loc[mask, "phase123_conservative_error_gva_eok"] = out.loc[mask, "phase123_flash_error_gva_eok"]
            out.loc[mask, "phase123_conservative_error_rate_pct"] = out.loc[mask, "phase123_flash_error_rate_pct"]
            out.loc[mask, "phase123_conservative_option_id"] = out.loc[mask, "phase123_flash_option_id"]
            adopted_blocks.append(
                {
                    "city": b.city,
                    "parent_code": b.parent_code,
                    "phase120_error_eok": p120_err,
                    "conservative_error_eok": p123_err,
                    "incremental_reduction_eok": p120_err - p123_err,
                    "worsened_cells": worsened,
                    "option_id": str(block["phase123_flash_option_id"].iloc[0]),
                    "decision": "채택: Phase120 대비 셀 악화 없음",
                }
            )
        else:
            adopted_blocks.append(
                {
                    "city": b.city,
                    "parent_code": b.parent_code,
                    "phase120_error_eok": p120_err,
                    "conservative_error_eok": p120_err,
                    "incremental_reduction_eok": 0.0,
                    "worsened_cells": worsened,
                    "option_id": str(block["phase123_flash_option_id"].iloc[0]),
                    "decision": "보류: 총오차는 줄지만 일부 중분류 악화",
                }
            )

    rows = []
    for city, g in out.groupby("city", sort=False):
        actual = float(g["actual_gva_eok"].sum())
        p120err = float(g["phase120_strict_flash_error_gva_eok"].sum())
        cerr = float(g["phase123_conservative_error_gva_eok"].sum())
        rows.append(
            {
                "city": city,
                "phase120_error_eok": p120err,
                "phase120_wape_pct": p120err / actual * 100,
                "conservative_error_eok": cerr,
                "conservative_wape_pct": cerr / actual * 100,
                "incremental_reduction_eok": p120err - cerr,
                "incremental_reduction_pp": (p120err - cerr) / actual * 100,
                "phase120_gt20_cells": int((g["phase120_strict_flash_error_rate_pct"] > 20).sum()),
                "conservative_gt20_cells": int((g["phase123_conservative_error_rate_pct"] > 20).sum()),
                "phase120_gt10_cells": int((g["phase120_strict_flash_error_rate_pct"] > 10).sum()),
                "conservative_gt10_cells": int((g["phase123_conservative_error_rate_pct"] > 10).sum()),
                "worsened_vs_phase120_cells": int((g["phase123_conservative_error_gva_eok"] > g["phase120_strict_flash_error_gva_eok"] + 1e-9).sum()),
            }
        )
    return out, pd.DataFrame(adopted_blocks), pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = p115.load_base()

    base_indicators, personal_audit = p120.build_indicators(include_refinement_candidates=False)
    pps, pps_audit = pps_indicators()
    indicators = pd.concat([base_indicators, pps], ignore_index=True) if not pps.empty else base_indicators.copy()

    screen, detail = p116.evaluate(base, indicators)
    selected = select(screen)
    registry = apply_named(base, selected, detail, "phase123_flash")
    summary = summarize(registry, "phase123_flash")
    inc_detail, inc_summary = incremental_vs_phase120(registry)
    conservative_detail, conservative_blocks, conservative_summary = conservative_no_worse_vs_phase120(registry, inc_detail)

    pps_selected = selected[selected["option_id"].astype(str).str.contains("pps_procurement", na=False)].copy() if not selected.empty else pd.DataFrame()
    pps_screen = screen[screen["option_id"].astype(str).str.contains("pps_procurement", na=False)].copy() if not screen.empty else pd.DataFrame()
    improved = registry[registry["phase123_flash_error_reduction_eok"].gt(1e-9)].sort_values(["city", "phase123_flash_error_reduction_eok"], ascending=[True, False])
    remaining_gt20 = registry[registry["phase123_flash_error_rate_pct"].gt(20)].sort_values(["city", "phase123_flash_error_gva_eok"], ascending=[True, False])

    indicators.to_csv(OUT / "phase123_all_flash_indicators.csv", index=False, encoding="utf-8-sig")
    pps.to_csv(OUT / "phase123_pps_indicators.csv", index=False, encoding="utf-8-sig")
    pps_audit.to_csv(OUT / "phase123_pps_classification_audit.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUT / "phase123_candidate_screen.csv", index=False, encoding="utf-8-sig")
    pps_screen.to_csv(OUT / "phase123_pps_candidate_screen.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase123_selected_options.csv", index=False, encoding="utf-8-sig")
    pps_selected.to_csv(OUT / "phase123_pps_selected_options.csv", index=False, encoding="utf-8-sig")
    registry.to_csv(OUT / "phase123_flash_registry.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase123_city_summary.csv", index=False, encoding="utf-8-sig")
    inc_detail.to_csv(OUT / "phase123_incremental_vs_phase120_detail.csv", index=False, encoding="utf-8-sig")
    inc_summary.to_csv(OUT / "phase123_incremental_vs_phase120_summary.csv", index=False, encoding="utf-8-sig")
    conservative_detail.to_csv(OUT / "phase123_conservative_no_worse_detail.csv", index=False, encoding="utf-8-sig")
    conservative_blocks.to_csv(OUT / "phase123_conservative_no_worse_blocks.csv", index=False, encoding="utf-8-sig")
    conservative_summary.to_csv(OUT / "phase123_conservative_no_worse_summary.csv", index=False, encoding="utf-8-sig")
    improved.to_csv(OUT / "phase123_improved_cells.csv", index=False, encoding="utf-8-sig")
    remaining_gt20.to_csv(OUT / "phase123_remaining_gt20.csv", index=False, encoding="utf-8-sig")

    report = f"""# Phase123 조달청 공공발주 기반 GVA 속보성 개선 실험

## 목적

Phase122에서 수집한 조달청 나라장터 입찰공고를 고양시·포항시 중분류 총부가가치(GVA) 속보 추정의 활동지표로 변환해 성능 개선 여부를 검증했다. 조달청 자료는 실제 GVA가 아니며, 2023년 9월 30일 이전 공고만 사용했다.

## 조달청 지표 변환

공사 공고는 공고명 키워드로 `종합 건설업(41)`과 `전문직별 공사업(42)`으로 나눴다. 용역 공고는 연구개발, 건축기술·엔지니어링, 전문과학기술서비스, 사업시설관리, 사업지원서비스, 정보서비스, 폐기물처리 등으로 매핑했다. 물품 공고는 GVA 중분류와의 직접 연결이 약해 정보시스템·보건 등 일부만 사용하고 나머지는 보류했다.

### 조달청 분류 감사

{p115.md_table(pps_audit, [("city", "지역"), ("op", "업무"), ("pps_class_label", "분류"), ("notices", "공고 수"), ("amount_eok", "금액 억원")], 80)}

## 도시별 결과: 초기 속보 기준 대비

{p115.md_table(summary, [("city", "지역"), ("actual_sum_eok", "실제합계 억원"), ("baseline_error_eok", "초기오차 억원"), ("baseline_wape_pct", "초기오차 %"), ("phase123_error_eok", "Phase123 오차 억원"), ("phase123_wape_pct", "Phase123 오차 %"), ("error_reduction_vs_initial_eok", "초기 대비 감소 억원"), ("wape_reduction_vs_initial_pp", "초기 대비 감소 pp"), ("baseline_gt20_cells", "초기 20%초과"), ("phase123_gt20_cells", "Phase123 20%초과"), ("baseline_gt10_cells", "초기 10%초과"), ("phase123_gt10_cells", "Phase123 10%초과"), ("worsened_vs_initial_cells", "초기 대비 악화 셀")])}

## Phase120 대비 증분 성능

{p115.md_table(inc_summary, [("city", "지역"), ("phase120_error_eok", "Phase120 오차 억원"), ("phase120_wape_pct", "Phase120 오차 %"), ("phase123_error_eok", "Phase123 오차 억원"), ("phase123_wape_pct", "Phase123 오차 %"), ("incremental_reduction_eok", "추가 감소 억원"), ("incremental_reduction_pp", "추가 감소 pp"), ("phase120_gt20_cells", "Phase120 20%초과"), ("phase123_gt20_cells", "Phase123 20%초과"), ("phase120_gt10_cells", "Phase120 10%초과"), ("phase123_gt10_cells", "Phase123 10%초과"), ("worsened_vs_phase120_cells", "Phase120 대비 악화 셀")])}

## 권장안: Phase120 대비 무악화 보수 채택

총오차 최소 기준으로는 포항시 건설업(F00)과 ERS에서 조달청 지표가 선택된다. 그러나 ERS는 총오차를 줄이면서도 일부 중분류를 악화시킨다. 따라서 운영 산출물에는 **Phase120 대비 중분류별 오차가 하나도 악화되지 않는 보수안**을 별도로 둔다.

{p115.md_table(conservative_summary, [("city", "지역"), ("phase120_error_eok", "Phase120 오차 억원"), ("phase120_wape_pct", "Phase120 오차 %"), ("conservative_error_eok", "보수안 오차 억원"), ("conservative_wape_pct", "보수안 오차 %"), ("incremental_reduction_eok", "추가 감소 억원"), ("incremental_reduction_pp", "추가 감소 pp"), ("phase120_gt20_cells", "Phase120 20%초과"), ("conservative_gt20_cells", "보수안 20%초과"), ("phase120_gt10_cells", "Phase120 10%초과"), ("conservative_gt10_cells", "보수안 10%초과"), ("worsened_vs_phase120_cells", "Phase120 대비 악화 셀")])}

### 보수 채택/보류 블록

{p115.md_table(conservative_blocks, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "조달청 후보"), ("phase120_error_eok", "Phase120 오차 억원"), ("conservative_error_eok", "보수안 오차 억원"), ("incremental_reduction_eok", "추가 감소 억원"), ("worsened_cells", "악화 셀"), ("decision", "판정")])}

## 선택된 조달청 후보

{p115.md_table(pps_selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("worsen_sum_eok", "악화합계 억원"), ("max_worsen_pp", "최대악화 pp"), ("public_claim_status", "판정")], 80)}

## 선택된 전체 후보

{p115.md_table(selected, [("city", "지역"), ("parent_code", "상위산업"), ("option_id", "선택 지표"), ("alpha", "혼합비"), ("baseline_floor", "기존구조 보존비"), ("baseline_error_eok", "기준오차 억원"), ("candidate_error_eok", "후보오차 억원"), ("error_reduction_eok", "감소 억원"), ("baseline_gt20_cells", "기준 20%초과"), ("candidate_gt20_cells", "후보 20%초과"), ("public_claim_status", "판정")], 80)}

## 개선된 중분류

{p115.md_table(improved, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("flash_baseline_error_gva_eok", "초기오차 억원"), ("phase123_flash_error_gva_eok", "Phase123 오차 억원"), ("phase123_flash_error_rate_pct", "Phase123 오차 %"), ("phase123_flash_error_reduction_eok", "초기 대비 감소 억원"), ("phase123_flash_option_id", "적용 지표")], 100)}

## 남은 20% 초과 중분류

{p115.md_table(remaining_gt20, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("phase123_flash_predicted_gva_eok", "추정 억원"), ("phase123_flash_error_gva_eok", "오차 억원"), ("phase123_flash_error_rate_pct", "오차 %"), ("phase123_flash_option_id", "적용 지표")], 120)}

## 판정

조달청 공공발주 자료는 수집 가능하고 시점상 속보성 후보로 쓸 수 있다. 다만 성능 개선 여부는 산업별로 다르게 나타난다. 특히 수요기관 기준 공고는 실제 사업 수행지와 다를 수 있으므로, 공공발주 지표가 선택된 경우에도 금액 상위 공고의 사업지 검증을 붙여야 한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
