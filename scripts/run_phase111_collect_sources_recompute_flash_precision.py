#!/usr/bin/env python3
"""Phase111: collect free weak-industry sources and recompute flash/refined errors.

This phase is deliberately conservative.  Newly collected sources are split into
two tracks:

* flash candidates: indicators that could plausibly exist before annual GRDP is
  published, but only if a historical release vintage is available;
* refined candidates: annual post-publication indicators that can improve an
  after-the-fact estimate, but must not be represented as flash evidence.

For the public performance registry we adopt only candidate rules that improve a
whole city×parent-industry block without increasing >10% cells and without
making any individual middle-industry cell worse.  If no candidate passes that
guardrail, Phase105 flash/refined values remain the official recalculation.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUTDIR = DATA / "phase111_collect_sources_recompute_flash_precision"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase111_collect_sources_recompute_flash_precision.md"

BASE_REGISTRY = DATA / "phase105_no_worse_refinement_guardrail" / "phase105_no_worse_refinement_registry.csv"
SAUPM78_RAW = RAW / "phase111_saupm78_2024_all_total_size.json"
MONA49_RAW = RAW / "phase111_mona49_goyang_pohang_halfyear_employment.json"
GOYANG_CATALOG = DATA / "partial_stats_phase37_goyang_kosis_catalog.csv"
KOSIS_META_DIMS = DATA / "kosis_candidate_metadata_dimensions.csv"
KOSIS_META_CODES = DATA / "kosis_candidate_metadata_codes.csv"
ACTUAL_COLLECTION = OUTDIR / "phase111_actual_collection_summary.csv"


MFG_MIDDLE_LABELS = {
    "10": "식료품 제조업",
    "11": "음료 제조업",
    "12": "담배 제조업",
    "13": "섬유제품 제조업",
    "14": "의복·모피 제조업",
    "15": "가죽·가방·신발 제조업",
    "16": "목재·나무제품 제조업",
    "17": "펄프·종이 제조업",
    "18": "인쇄·기록매체 복제업",
    "19": "코크스·석유정제품 제조업",
    "20": "화학물질·화학제품 제조업",
    "21": "의약품 제조업",
    "22": "고무·플라스틱 제조업",
    "23": "비금속 광물제품 제조업",
    "24": "1차 금속 제조업",
    "25": "금속가공제품 제조업",
    "26": "전자부품·컴퓨터 제조업",
    "27": "의료·정밀기기 제조업",
    "28": "전기장비 제조업",
    "29": "기계·장비 제조업",
    "30": "자동차·트레일러 제조업",
    "31": "기타 운송장비 제조업",
    "32": "가구 제조업",
    "33": "기타 제품 제조업",
    "34": "산업용 기계 수리업",
}


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(x in label for x in ("억원", "%", "개", "pp", "행")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals: list[str] = []
        for key, _ in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}" if abs(float(value)) < 100 else f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_base() -> pd.DataFrame:
    df = pd.read_csv(BASE_REGISTRY)
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    return df


def baseline_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby("city", as_index=False)
        .agg(
            cells=("middle_code", "count"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            flash_error_eok=("initial_error_gva_eok", "sum"),
            refined_error_eok=("no_worse_refined_error_gva_eok", "sum"),
            flash_gt10_cells=("initial_error_rate_pct", lambda s: int((s > 10).sum())),
            refined_gt10_cells=("no_worse_refined_error_rate_pct", lambda s: int((s > 10).sum())),
            flash_median_pct=("initial_error_rate_pct", "median"),
            refined_median_pct=("no_worse_refined_error_rate_pct", "median"),
        )
    )
    out["flash_wape_pct"] = out["flash_error_eok"] / out["actual_sum_eok"] * 100
    out["refined_wape_pct"] = out["refined_error_eok"] / out["actual_sum_eok"] * 100
    return out


def source_inventory() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if GOYANG_CATALOG.exists():
        cat = read_csv_any(GOYANG_CATALOG)
        keep = cat[
            cat["table_id"].isin(
                [
                    "DT_1F00334",
                    "DT_1F00101",
                    "DT_1F00009",
                    "DT_1L00012",
                    "DT_1L00004",
                    "DT_1L00001",
                    "DT_1M00037",
                    "DT_1J00015",
                    "DT_1C00012",
                    "DT_1I00022",
                ]
            )
        ].copy()
        for _, r in keep.iterrows():
            rows.append(
                {
                    "source": f"KOSIS 고양시 {r.table_name}",
                    "org_tbl": f"{r.org_id}/{r.table_id}",
                    "target": "고양 취약업종 후보",
                    "period_range": f"{r.start_period}~{r.end_period}",
                    "timing_track": "정밀화 후보",
                    "status": "목록/메타데이터 확인",
                    "note": str(r.link_url),
                }
            )
    if KOSIS_META_DIMS.exists():
        dims = read_csv_any(KOSIS_META_DIMS)
        for org_tbl, target, timing, status in [
            ("118/DT_118N_MONA49", "고양·포항 산업묶음 반기 고용", "속보 후보(빈티지 미보장)", "수집"),
            ("118/DT_118N_SAUPM78", "고양·포항 제조업 중분류 사업체·종사자", "정밀화 후보", "수집"),
            ("106/DT_106N_06_0100043", "상수도 활동지표", "정밀화 후보", "메타데이터 확인"),
            ("106/DT_106N_03_0200079", "환경배출/정화 활동지표", "정밀화 후보", "메타데이터 확인"),
            ("133/DT_133001_3234", "시군구 소득종류별 금액", "정밀화 후보", "메타데이터 확인"),
            ("133/DT_133N_A3212", "시군구 종합소득 주요항목", "정밀화 후보", "메타데이터 확인"),
        ]:
            org_id, tbl_id = org_tbl.split("/")
            d = dims[dims["org_id"].astype(str).eq(org_id) & dims["tbl_id"].eq(tbl_id)]
            pr = "; ".join(sorted(set(str(x) for x in d.get("period_range", pd.Series(dtype=str)).dropna())))
            rows.append(
                {
                    "source": str(d["tbl_nm"].dropna().iloc[0]) if not d.empty else org_tbl,
                    "org_tbl": org_tbl,
                    "target": target,
                    "period_range": pr,
                    "timing_track": timing,
                    "status": status,
                    "note": "API key 추가 불필요: 기존 KOSIS key 사용" if org_id != "133" else "공개 KOSIS; 세부 산업 없음",
                }
            )
    return pd.DataFrame(rows).drop_duplicates(subset=["org_tbl", "target"], keep="first")


def saupm78_indicators() -> pd.DataFrame:
    if not SAUPM78_RAW.exists():
        return pd.DataFrame()
    rows = json.loads(SAUPM78_RAW.read_text(encoding="utf-8"))
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d["value"] = pd.to_numeric(d["DT"], errors="coerce")
    d = d[
        d["C1_NM"].isin(["고양시", "포항시"])
        & d["C2"].astype(str).str.match(r"INDUSTRY_11SC\d\d")
        & d["ITM_ID"].isin(["16118ED_1", "16118ED_9A"])
    ].copy()
    d["city"] = d["C1_NM"]
    d["middle_code"] = d["C2"].astype(str).str.extract(r"SC(\d\d)")
    d["metric"] = d["ITM_ID"].map({"16118ED_1": "establishments", "16118ED_9A": "employees"})
    out = (
        d.pivot_table(index=["city", "middle_code", "C2_NM"], columns="metric", values="value", aggfunc="sum")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    out["source"] = "고용노동부 사업체노동실태현황 2024"
    out["lst_chn_de"] = d.groupby(["city", "middle_code"])["LST_CHN_DE"].transform("max").max()
    return out


def screen_manufacturing(base: pd.DataFrame, indicators: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    details: list[pd.DataFrame] = []
    if indicators.empty:
        return pd.DataFrame(), pd.DataFrame()
    alphas = [0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30, 0.50, 0.75, 1.00]
    for city, g in base[base["parent_code"].eq("C00")].groupby("city", sort=False):
        ind_city = indicators[indicators["city"].eq(city)].drop(columns=["city"], errors="ignore")
        x = g.merge(ind_city, on="middle_code", how="left")
        parent_actual = float(x["actual_gva_eok"].sum())
        baseline_pred = x["no_worse_refined_predicted_gva_eok"].to_numpy(float)
        actual = x["actual_gva_eok"].to_numpy(float)
        old_err = x["no_worse_refined_error_gva_eok"].to_numpy(float)
        old_rate = x["no_worse_refined_error_rate_pct"].to_numpy(float)
        for metric in ["establishments", "employees"]:
            indicator = pd.to_numeric(x[metric], errors="coerce").fillna(0).to_numpy(float)
            if indicator.sum() <= 0:
                continue
            indicator_pred = indicator / indicator.sum() * parent_actual
            for alpha in alphas:
                pred = (1 - alpha) * baseline_pred + alpha * indicator_pred
                err = np.abs(pred - actual)
                rate = np.where(actual > 0, err / actual * 100, np.nan)
                row = {
                    "city": city,
                    "parent_code": "C00",
                    "source": "고용노동부 사업체노동실태현황 2024",
                    "metric": metric,
                    "alpha": alpha,
                    "baseline_error_eok": float(old_err.sum()),
                    "candidate_error_eok": float(err.sum()),
                    "error_reduction_eok": float(old_err.sum() - err.sum()),
                    "baseline_gt10_cells": int((old_rate > 10).sum()),
                    "candidate_gt10_cells": int((rate > 10).sum()),
                    "worsened_cells": int((err > old_err + 1e-9).sum()),
                    "max_worsen_eok": float(np.max(err - old_err)),
                }
                row["strict_adopt"] = (
                    row["error_reduction_eok"] > 0
                    and row["candidate_gt10_cells"] <= row["baseline_gt10_cells"]
                    and row["worsened_cells"] == 0
                )
                rows.append(row)
                detail = x[["city", "parent_code", "middle_code", "middle_label", "actual_gva_eok"]].copy()
                detail["metric"] = metric
                detail["alpha"] = alpha
                detail["baseline_predicted_gva_eok"] = baseline_pred
                detail["candidate_predicted_gva_eok"] = pred
                detail["baseline_error_gva_eok"] = old_err
                detail["candidate_error_gva_eok"] = err
                detail["baseline_error_rate_pct"] = old_rate
                detail["candidate_error_rate_pct"] = rate
                detail["candidate_worse"] = err > old_err + 1e-9
                details.append(detail)
    screen = pd.DataFrame(rows).sort_values(["strict_adopt", "error_reduction_eok"], ascending=[False, False])
    detail_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    return screen, detail_df


def collect_timing_audit() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if SAUPM78_RAW.exists():
        d = pd.DataFrame(json.loads(SAUPM78_RAW.read_text(encoding="utf-8")))
        rows.append(
            {
                "source": "고용노동부 사업체노동실태현황 2024",
                "reference_period": "2024",
                "latest_change_date": str(d.get("LST_CHN_DE", pd.Series(dtype=str)).dropna().max()),
                "usable_for_flash": "아니오",
                "usable_for_refined": "예",
                "reason": "2024년 연간자료이며 2026-03-31 갱신 스냅샷",
            }
        )
    if MONA49_RAW.exists():
        d = pd.DataFrame(json.loads(MONA49_RAW.read_text(encoding="utf-8")))
        rows.append(
            {
                "source": "고용노동부 행정구역/산업별 고용",
                "reference_period": f"{d.get('PRD_DE', pd.Series(dtype=str)).min()}~{d.get('PRD_DE', pd.Series(dtype=str)).max()}",
                "latest_change_date": str(d.get("LST_CHN_DE", pd.Series(dtype=str)).dropna().max()),
                "usable_for_flash": "보류",
                "usable_for_refined": "예",
                "reason": "반기 지표이나 API 응답은 현재 스냅샷이라 과거 예측시점 빈티지 미확인",
            }
        )
    return pd.DataFrame(rows)


def actual_collection_summary() -> pd.DataFrame:
    if ACTUAL_COLLECTION.exists():
        return pd.read_csv(ACTUAL_COLLECTION)
    return pd.DataFrame(columns=["org_id", "tbl_id", "start", "end", "rows", "latest_change_date", "raw_path"])


def recompute_registry(base: pd.DataFrame, screen: pd.DataFrame, detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return recalculated registry and adoption table under strict guardrail."""
    registry = base.copy()
    adoption_rows = []
    if not screen.empty:
        accepted = screen[screen["strict_adopt"]].copy()
        for _, a in accepted.iterrows():
            mask = (
                detail["city"].eq(a.city)
                & detail["parent_code"].eq(a.parent_code)
                & detail["metric"].eq(a.metric)
                & np.isclose(detail["alpha"].astype(float), float(a.alpha))
            )
            d = detail[mask]
            if d.empty:
                continue
            key = ["city", "parent_code", "middle_code"]
            registry = registry.merge(
                d[key + ["candidate_predicted_gva_eok", "candidate_error_gva_eok", "candidate_error_rate_pct"]],
                on=key,
                how="left",
                suffixes=("", "_phase111"),
            )
            m = registry["candidate_predicted_gva_eok"].notna()
            registry.loc[m, "no_worse_refined_predicted_gva_eok"] = registry.loc[m, "candidate_predicted_gva_eok"]
            registry.loc[m, "no_worse_refined_error_gva_eok"] = registry.loc[m, "candidate_error_gva_eok"]
            registry.loc[m, "no_worse_refined_error_rate_pct"] = registry.loc[m, "candidate_error_rate_pct"]
            registry = registry.drop(columns=["candidate_predicted_gva_eok", "candidate_error_gva_eok", "candidate_error_rate_pct"])
            adoption_rows.append(a.to_dict())
    return registry, pd.DataFrame(adoption_rows)


def remaining_gt10(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[df["no_worse_refined_error_rate_pct"].gt(10)]
        .sort_values(["city", "no_worse_refined_error_gva_eok"], ascending=[True, False])
        [[
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "no_worse_refined_predicted_gva_eok",
            "no_worse_refined_error_gva_eok",
            "no_worse_refined_error_rate_pct",
            "required_next_data",
        ]]
    )


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = load_base()
    inventory = source_inventory()
    saupm = saupm78_indicators()
    timing = collect_timing_audit()
    actual_collection = actual_collection_summary()
    screen, detail = screen_manufacturing(base, saupm)
    recalculated, adopted = recompute_registry(base, screen, detail)
    before_summary = baseline_summary(base)
    after_summary = baseline_summary(recalculated)
    after_summary["changed_by_phase111"] = after_summary["refined_error_eok"] - before_summary["refined_error_eok"]
    remain = remaining_gt10(recalculated)

    inventory.to_csv(OUTDIR / "phase111_collected_source_inventory.csv", index=False, encoding="utf-8-sig")
    saupm.to_csv(OUTDIR / "phase111_saupm78_mfg_indicators.csv", index=False, encoding="utf-8-sig")
    timing.to_csv(OUTDIR / "phase111_publication_timing_audit.csv", index=False, encoding="utf-8-sig")
    actual_collection.to_csv(OUTDIR / "phase111_actual_collection_summary.csv", index=False, encoding="utf-8-sig")
    screen.to_csv(OUTDIR / "phase111_mfg_candidate_screen.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase111_mfg_candidate_detail.csv", index=False, encoding="utf-8-sig")
    adopted.to_csv(OUTDIR / "phase111_strict_adopted_candidates.csv", index=False, encoding="utf-8-sig")
    recalculated.to_csv(OUTDIR / "phase111_flash_refined_recomputed_registry.csv", index=False, encoding="utf-8-sig")
    before_summary.to_csv(OUTDIR / "phase111_before_summary.csv", index=False, encoding="utf-8-sig")
    after_summary.to_csv(OUTDIR / "phase111_after_summary.csv", index=False, encoding="utf-8-sig")
    remain.to_csv(OUTDIR / "phase111_remaining_gt10_after_recompute.csv", index=False, encoding="utf-8-sig")

    best_mfg = screen.sort_values(["city", "candidate_error_eok"]).groupby("city", as_index=False).head(4) if not screen.empty else pd.DataFrame()
    strict_count = int(screen["strict_adopt"].sum()) if not screen.empty else 0
    report = f"""# Phase111 무료자료 수집 및 속보/정밀오차 재계산

## 목적

정밀오차 10% 초과 업종을 줄이기 위해 무료 공개자료를 추가 수집했다. 단, 중분류 실제값을 보고 개별 업종을 맞추는 방식은 제외하고, 새 지표가 상위산업 묶음의 집계검증에서 안전하게 작동하는 경우만 채택했다.

## 수집·확인 자료

{md_table(inventory, [("source", "자료"), ("org_tbl", "기관/표"), ("target", "대상"), ("period_range", "기간"), ("timing_track", "시점 구분"), ("status", "상태"), ("note", "비고")], 40)}

## 공표시점 판정

{md_table(timing, [("source", "자료"), ("reference_period", "대상기간"), ("latest_change_date", "API 갱신일"), ("usable_for_flash", "속보 사용"), ("usable_for_refined", "정밀화 사용"), ("reason", "판정 사유")])}

## 원자료 수집 현황

{md_table(actual_collection, [("org_id", "기관"), ("tbl_id", "표ID"), ("start", "시작"), ("end", "끝"), ("rows", "행수"), ("latest_change_date", "최신 API 갱신일"), ("raw_path", "저장 경로")], 40)}

## 신규 제조업 후보 스크린

고용노동부 `사업체노동실태현황 2024`는 고양·포항 제조업 10~34 중분류별 사업체수와 종사자수를 제공한다. 하지만 갱신일이 2026-03-31인 사후 스냅샷이므로 정밀화 후보로만 보았다.

{md_table(best_mfg, [("city", "지역"), ("metric", "지표"), ("alpha", "혼합비"), ("baseline_error_eok", "기준 제조업오차 억원"), ("candidate_error_eok", "후보 제조업오차 억원"), ("error_reduction_eok", "오차감소 억원"), ("baseline_gt10_cells", "기준 10%초과"), ("candidate_gt10_cells", "후보 10%초과"), ("worsened_cells", "악화 중분류"), ("strict_adopt", "엄격채택")], 20)}

엄격채택 후보 수: **{strict_count}개**.

## 속보오차·정밀오차 재계산

엄격채택 후보가 없으므로, 공개 성능 레지스트리는 Phase105의 속보/정밀화 값을 유지한다. 이번에 수집한 자료는 정밀화 후보 또는 향후 빈티지 검증 후보로 남긴다.

{md_table(after_summary, [("city", "지역"), ("cells", "중분류 수"), ("actual_sum_eok", "실제합계 억원"), ("flash_error_eok", "속보오차 억원"), ("flash_wape_pct", "속보오차 %"), ("flash_gt10_cells", "속보 10%초과"), ("refined_error_eok", "정밀오차 억원"), ("refined_wape_pct", "정밀오차 %"), ("refined_gt10_cells", "정밀 10%초과"), ("changed_by_phase111", "이번 변경 억원")])}

## 남은 10% 초과 업종

{md_table(remain, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "중분류"), ("actual_gva_eok", "실제 억원"), ("no_worse_refined_predicted_gva_eok", "정밀추정 억원"), ("no_worse_refined_error_gva_eok", "정밀오차 억원"), ("no_worse_refined_error_rate_pct", "정밀오차 %"), ("required_next_data", "다음 필요자료")], 60)}

## 결론

1. 추가 API key는 현재 필요하지 않았다. KOSIS, 고용노동부 KOSIS, 환경부 KOSIS, 국세 KOSIS 후보는 기존 KOSIS key로 접근 가능했다.
2. 실제로 새로 수집한 고용노동부 2024 제조업 중분류 자료는 포항 제조업 총오차를 일부 줄일 수 있지만, 악화되는 중분류가 많아 엄격채택하지 않았다.
3. 반기 고용자료는 속보 후보처럼 보이지만, 과거 예측시점별 원자료 빈티지가 아니라 현재 스냅샷으로 확인되어 속보오차 개선값에는 넣지 않았다.
4. 따라서 이번 재계산의 최종 공개 성능값은 기존과 동일하다. 다만 다음 개선은 자료 부재가 아니라 더 구체적이다. 고양은 비영리·방송/콘텐츠·스포츠 이용실적, 포항은 금융취급액·환경처리량·전문서비스 계약액처럼 중분류 내부를 직접 가르는 무료자료가 필요하다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
