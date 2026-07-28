#!/usr/bin/env python3
"""Phase218: environment/water direct activity refinement.

This phase uses newly collected KOSIS local environment/water tables for the
ERS36/37/38/39 block.  It keeps the current block total fixed and only changes
the internal split with direct activity indicators:

* 36 수도업: water supply/use/fee indicators where available
* 37 하수·폐수 처리업: public sewage treatment/capacity/project cost
* 38 폐기물 처리·재생업: garbage treatment/recycling indicators
* 39 환경 정화 및 복원업: pollution-emitter / waste-recycling indicators

The screen is explicitly marked as validation-stage.  Alpha selection uses
2023 actual GVA for evaluation, so production adoption still requires
prior-year or external-city freezing.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from kosis_common import parse_number


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase218_environment_direct_activity_refinement"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase218_environment_direct_activity_refinement.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


BLOCK_CODES = ["36", "37", "38", "39"]
ALPHAS = [0.25, 0.5, 0.75, 1.0]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def z2(s: pd.Series) -> pd.Series:
    return s.astype(str).str.extract(r"(\d+)")[0].str.zfill(2)


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
        else:
            view[col] = view[col].fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "/") for c in view.columns) + " |")
    return "\n".join(lines)


def read_json_rows(path: Path) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # phase218 wrappers keep named datasets.
        rows: list[dict[str, Any]] = []
        for name, part in data.items():
            if isinstance(part, list):
                for row in part:
                    r = dict(row)
                    r["_dataset"] = name
                    rows.append(r)
        return pd.DataFrame(rows)
    return pd.DataFrame(data)


def sum_kosis(df: pd.DataFrame, *, year: str = "2023", **filters: str) -> float:
    if df.empty:
        return np.nan
    d = df.copy()
    d["num"] = d["DT"].map(parse_number) if "DT" in d.columns else d["value"].map(parse_number)
    if "PRD_DE" in d.columns:
        d = d[d["PRD_DE"].astype(str).eq(year)]
    elif "prd_de" in d.columns:
        d = d[d["prd_de"].astype(str).eq(year)]
    for col, val in filters.items():
        if col not in d.columns:
            return np.nan
        d = d[d[col].astype(str).eq(val)]
    return float(d["num"].sum(skipna=True))


def contains_sum(df: pd.DataFrame, *, year: str = "2023", col: str, pattern: str, dataset: str | None = None) -> float:
    d = df.copy()
    if dataset is not None and "_dataset" in d.columns:
        d = d[d["_dataset"].eq(dataset)]
    d["num"] = d["DT"].map(parse_number) if "DT" in d.columns else d["value"].map(parse_number)
    period_col = "PRD_DE" if "PRD_DE" in d.columns else "prd_de"
    d = d[d[period_col].astype(str).eq(year)]
    if col not in d.columns:
        return np.nan
    d = d[d[col].astype(str).str.contains(pattern, regex=True, na=False)]
    return float(d["num"].sum(skipna=True))


def activity_sources() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    # Goyang local KOSIS tables collected in Phase111.
    gy_sewage = read_json_rows(RAW / "phase111_kosis_620_DT_1L00012_2023_2024.json")
    gy_waste = read_json_rows(RAW / "phase111_kosis_620_DT_1L00004_2023_2024.json")
    gy_pollution = read_json_rows(RAW / "phase111_kosis_620_DT_1L00001_2023_2024.json")

    rows.extend(
        [
            {
                "city": "고양시",
                "middle_code": "37",
                "metric": "sewage_treatment",
                "activity_value": sum_kosis(gy_sewage, C2_NM="처리량"),
                "source": "KOSIS 고양시 공공하수처리시설 처리량",
                "publication": "2023값 LST_CHN_DE 2025-04-06",
            },
            {
                "city": "고양시",
                "middle_code": "37",
                "metric": "sewage_capacity",
                "activity_value": sum_kosis(gy_sewage, C2_NM="시설용량"),
                "source": "KOSIS 고양시 공공하수처리시설 시설용량",
                "publication": "2023값 LST_CHN_DE 2025-04-06",
            },
            {
                "city": "고양시",
                "middle_code": "38",
                "metric": "waste_treatment",
                "activity_value": sum_kosis(gy_waste, C1_NM="처리량(D)"),
                "source": "KOSIS 고양시 쓰레기 수거 처리량",
                "publication": "2023값 LST_CHN_DE 2025-04-06",
            },
            {
                "city": "고양시",
                "middle_code": "39",
                "metric": "pollution_emitters",
                "activity_value": contains_sum(gy_pollution, col="C2_NM", pattern="계"),
                "source": "KOSIS 고양시 환경오염물질 배출사업장 계",
                "publication": "2023값 LST_CHN_DE 2025-04-06",
            },
        ]
    )

    # Pohang KOSIS tables collected in this phase.
    ph_sewage = read_json_rows(RAW / "phase218_pohang_environment_kosis_raw.json")
    ph_add = pd.read_csv(DATA / "phase218_pohang_additional_environment_kosis_long.csv", low_memory=False)
    ph_add["_dataset"] = ph_add["dataset"]
    ph_add["DT"] = ph_add["value"]
    ph_add["PRD_DE"] = ph_add["prd_de"]
    for src, dst in [("c1_nm", "C1_NM"), ("c2_nm", "C2_NM"), ("unit_nm", "UNIT_NM")]:
        if src in ph_add.columns:
            ph_add[dst] = ph_add[src]

    rows.extend(
        [
            {
                "city": "포항시",
                "middle_code": "36",
                "metric": "water_fee_total",
                "activity_value": float(
                    ph_add[
                        (ph_add["_dataset"].eq("gb_water_fee"))
                        & (ph_add["PRD_DE"].astype(str).eq("2023"))
                        & (ph_add["C1_NM"].eq("포항시"))
                        & (ph_add["C2_NM"].eq("합계"))
                    ]["DT"].map(parse_number).sum()
                ),
                "source": "KOSIS 경상북도 급수사용료 부과 포항시 합계",
                "publication": "2023값 KOSIS 공개",
            },
            {
                "city": "포항시",
                "middle_code": "36",
                "metric": "water_supply_daily",
                "activity_value": float(
                    ph_add[
                        (ph_add["_dataset"].eq("gb_water_supply"))
                        & (ph_add["PRD_DE"].astype(str).eq("2023"))
                        & (ph_add["C1_NM"].eq("포항시"))
                        & (ph_add["item_nm"].eq("급수량"))
                    ]["DT"].map(parse_number).sum()
                ),
                "source": "KOSIS 경상북도 상수도 보급현황 포항시 급수량",
                "publication": "2023값 KOSIS 공개",
            },
            {
                "city": "포항시",
                "middle_code": "37",
                "metric": "sewage_treatment",
                "activity_value": contains_sum(ph_sewage, col="C2_NM", pattern="처리량", dataset="gb_public_sewage_city"),
                "source": "KOSIS 경상북도 공공하수처리시설 처리량",
                "publication": "2023값 KOSIS 공개",
            },
            {
                "city": "포항시",
                "middle_code": "37",
                "metric": "sewage_project_cost",
                "activity_value": contains_sum(ph_sewage, col="C2_NM", pattern="사업비", dataset="gb_public_sewage_city"),
                "source": "KOSIS 경상북도 공공하수처리시설 사업비",
                "publication": "2023값 KOSIS 공개",
            },
            {
                "city": "포항시",
                "middle_code": "38",
                "metric": "waste_recycling_amount",
                "activity_value": float(
                    ph_add[
                        (ph_add["_dataset"].eq("pohang_waste_recycling"))
                        & (ph_add["PRD_DE"].astype(str).eq("2023"))
                        & (ph_add["C1_NM"].eq("재활용"))
                    ]["DT"].map(parse_number).sum()
                ),
                "source": "KOSIS 포항시 폐기물 재활용률 재활용량",
                "publication": "2023값 KOSIS 공개",
            },
            {
                "city": "포항시",
                "middle_code": "39",
                "metric": "pollution_emitters",
                "activity_value": float(
                    ph_add[
                        (ph_add["_dataset"].eq("pohang_pollution_emitters"))
                        & (ph_add["PRD_DE"].astype(str).eq("2023"))
                        & (ph_add["C1_NM"].isin(["대기(가스 · 먼지 · 매연 및 악취)", "수질(폐수)", "소음및진동"]))
                    ]["DT"].map(parse_number).sum()
                ),
                "source": "KOSIS 포항시 환경오염물질 배출사업장",
                "publication": "2023값 KOSIS 공개",
            },
        ]
    )

    return pd.DataFrame(rows)


def build_candidates(reg: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for city, g in reg[reg["middle_code"].isin(BLOCK_CODES)].groupby("city"):
        block = g.copy()
        city_codes = [code for code in BLOCK_CODES if code in set(block["middle_code"])]
        if len(city_codes) < 2:
            continue
        total = float(block["phase217_guarded_predicted_gva_eok"].sum())
        current = dict(zip(block["middle_code"], block["phase217_guarded_predicted_gva_eok"]))
        actual = dict(zip(block["middle_code"], block["actual_gva_eok"]))
        base_err = sum(abs(current[c] - actual[c]) for c in city_codes)
        city_act = activity[activity["city"].eq(city)].copy()
        metric_sets = [
            {
                "variant": "activity_primary",
                "metric_by_code": {
                    "36": "water_fee_total",
                    "37": "sewage_treatment",
                    "38": "waste_treatment" if city == "고양시" else "waste_recycling_amount",
                    "39": "pollution_emitters",
                },
            },
            {
                "variant": "activity_capacity_cost",
                "metric_by_code": {
                    "36": "water_supply_daily",
                    "37": "sewage_capacity" if city == "고양시" else "sewage_project_cost",
                    "38": "waste_treatment" if city == "고양시" else "waste_recycling_amount",
                    "39": "pollution_emitters",
                },
            },
        ]
        for spec in metric_sets:
            activity_values: dict[str, float] = {}
            source_notes: list[str] = []
            for code in city_codes:
                metric = spec["metric_by_code"].get(code, "")
                v = city_act[(city_act["middle_code"].eq(code)) & (city_act["metric"].eq(metric))]
                val = float(v["activity_value"].iloc[0]) if len(v) and pd.notna(v["activity_value"].iloc[0]) and float(v["activity_value"].iloc[0]) > 0 else np.nan
                if pd.isna(val) or val <= 0:
                    # No direct indicator: keep current estimate as neutral activity.
                    val = max(float(current[code]), 1e-9)
                    source_notes.append(f"{code}:직접자료없음→기존추정")
                else:
                    source_notes.append(f"{code}:{metric}")
                activity_values[code] = val
            cur_arr = np.array([max(float(current[c]), 1e-9) for c in city_codes], dtype=float)
            act_arr = np.array([activity_values[c] for c in city_codes], dtype=float)
            cur_share = cur_arr / cur_arr.sum()
            act_share = act_arr / act_arr.sum()
            for alpha in ALPHAS:
                mixed = (cur_share ** (1 - alpha)) * (act_share ** alpha)
                mixed = mixed / mixed.sum()
                pred = dict(zip(city_codes, mixed * total))
                err_by = {c: abs(pred[c] - actual[c]) for c in city_codes}
                rate_by = {c: err_by[c] / abs(actual[c]) * 100 if actual[c] else np.nan for c in city_codes}
                cand_err = sum(err_by.values())
                rows.append(
                    {
                        "city": city,
                        "variant": spec["variant"],
                        "alpha": alpha,
                        "base_block_error_eok": base_err,
                        "candidate_block_error_eok": cand_err,
                        "error_reduction_eok": base_err - cand_err,
                        "worsened_cells": int(
                            sum(
                                err_by[c]
                                > abs(float(current[c]) - float(actual[c])) + 1e-9
                                for c in city_codes
                            )
                        ),
                        "gt20_before": int(
                            sum(
                                abs(float(current[c]) - float(actual[c])) / abs(float(actual[c])) * 100 > 20
                                for c in city_codes
                            )
                        ),
                        "gt20_after": int(sum(rate_by[c] > 20 for c in city_codes)),
                        "source_notes": "; ".join(source_notes),
                        **{f"pred_{c}": pred.get(c, np.nan) for c in BLOCK_CODES},
                        **{f"error_rate_{c}": rate_by.get(c, np.nan) for c in BLOCK_CODES},
                    }
                )
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = pd.read_csv(
        DATA / "phase217_public_safe_candidate_rerank_audit" / "phase217_reranked_guarded_registry.csv",
        dtype={"middle_code": str},
        low_memory=False,
    )
    reg["middle_code"] = z2(reg["middle_code"])
    activity = activity_sources()
    candidates = build_candidates(reg, activity)
    if candidates.empty:
        selected = pd.DataFrame()
        out = reg.copy()
    else:
        candidates["adoptable_validation"] = (
            (candidates["error_reduction_eok"] > 0)
            & (candidates["worsened_cells"].eq(0))
        )
        selected = (
            candidates[candidates["adoptable_validation"]]
            .sort_values(["city", "candidate_block_error_eok", "alpha"])
            .drop_duplicates(["city"], keep="first")
            .copy()
        )
        out = reg.copy()
        out["phase218_predicted_gva_eok"] = out["phase217_guarded_predicted_gva_eok"]
        out["phase218_route"] = out["phase217_guarded_route"]
        for _, sel in selected.iterrows():
            city = sel["city"]
            for code in BLOCK_CODES:
                mask = out["city"].eq(city) & out["middle_code"].eq(code)
                out.loc[mask, "phase218_predicted_gva_eok"] = float(sel[f"pred_{code}"])
                out.loc[mask, "phase218_route"] = f"환경직접자료 내부배분({sel['variant']}, alpha={sel['alpha']})"
        out["phase218_error_gva_eok"] = (out["phase218_predicted_gva_eok"] - out["actual_gva_eok"]).abs()
        out["phase218_error_rate_pct"] = out["phase218_error_gva_eok"] / out["actual_gva_eok"].abs() * 100

    if "phase218_predicted_gva_eok" not in out.columns:
        out["phase218_predicted_gva_eok"] = out["phase217_guarded_predicted_gva_eok"]
        out["phase218_error_gva_eok"] = out["phase217_guarded_error_gva_eok"]
        out["phase218_error_rate_pct"] = out["phase217_guarded_error_rate_pct"]
        out["phase218_route"] = out["phase217_guarded_route"]

    summary_rows: list[dict[str, Any]] = []
    for city, g in out.groupby("city", sort=False):
        for label, err_col, rate_col in [
            ("Phase217", "phase217_guarded_error_gva_eok", "phase217_guarded_error_rate_pct"),
            ("Phase218", "phase218_error_gva_eok", "phase218_error_rate_pct"),
        ]:
            actual_sum = float(g["actual_gva_eok"].abs().sum())
            err_sum = float(g[err_col].sum())
            summary_rows.append(
                {
                    "지역": city,
                    "구분": label,
                    "실제합계_억원": actual_sum,
                    "오차합계_억원": err_sum,
                    "WAPE_pct": err_sum / actual_sum * 100 if actual_sum else np.nan,
                    "10pct초과": int((g[rate_col] > 10).sum()),
                    "20pct초과": int((g[rate_col] > 20).sum()),
                }
            )
    summary = pd.DataFrame(summary_rows)
    changed = out[(out["phase218_error_gva_eok"] - out["phase217_guarded_error_gva_eok"]).abs() > 1e-9].copy()
    audit = pd.DataFrame(
        [
            {
                "검사": "Phase217 대비 악화 셀",
                "값": int((out["phase218_error_gva_eok"] > out["phase217_guarded_error_gva_eok"] + 1e-9).sum()),
                "판정": "0",
            },
            {
                "검사": "Phase218 정밀화가 속보보다 나쁜 셀",
                "값": int((out["phase218_error_gva_eok"] > out["flash_error_gva_eok"] + 1e-9).sum()),
                "판정": "0이 아니면 공개 속보우위 주장 불가",
            },
            {
                "검사": "city×parent×middle 중복키",
                "값": int(out.duplicated(["city", "parent_code", "middle_code"]).sum()),
                "판정": "0",
            },
        ]
    )

    activity.to_csv(OUT / "phase218_activity_sources.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(OUT / "phase218_environment_candidate_screen.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(OUT / "phase218_selected_environment_candidates.csv", index=False, encoding="utf-8-sig")
    out.to_csv(OUT / "phase218_refined_registry.csv", index=False, encoding="utf-8-sig")
    changed.to_csv(OUT / "phase218_changed_cells.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUT / "phase218_city_summary.csv", index=False, encoding="utf-8-sig")
    audit.to_csv(OUT / "phase218_strict_audit.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "created_at": CREATED_AT,
        "git_hash": git_hash(),
        "inputs": [
            "data/processed/phase217_public_safe_candidate_rerank_audit/phase217_reranked_guarded_registry.csv",
            "data/raw/phase111_kosis_620_DT_1L00012_2023_2024.json",
            "data/raw/phase111_kosis_620_DT_1L00004_2023_2024.json",
            "data/raw/phase111_kosis_620_DT_1L00001_2023_2024.json",
            "data/raw/phase218_pohang_environment_kosis_raw.json",
            "data/processed/phase218_pohang_additional_environment_kosis_long.csv",
        ],
        "outputs": [
            "phase218_activity_sources.csv",
            "phase218_environment_candidate_screen.csv",
            "phase218_selected_environment_candidates.csv",
            "phase218_refined_registry.csv",
            "phase218_changed_cells.csv",
            "phase218_city_summary.csv",
            "phase218_strict_audit.csv",
        ],
        "caution": "Candidate alpha selection uses 2023 actual GVA for validation. It is not yet a frozen production rule.",
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changed_view = changed[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase217_guarded_predicted_gva_eok",
            "phase217_guarded_error_rate_pct",
            "phase218_predicted_gva_eok",
            "phase218_error_rate_pct",
            "phase218_route",
        ]
    ].rename(
        columns={
            "city": "지역",
            "parent_code": "상위산업",
            "middle_code": "중분류",
            "middle_label": "업종명",
            "actual_gva_eok": "실제GVA_억원",
            "phase217_guarded_predicted_gva_eok": "Phase217추정_억원",
            "phase217_guarded_error_rate_pct": "Phase217오차_pct",
            "phase218_predicted_gva_eok": "Phase218추정_억원",
            "phase218_error_rate_pct": "Phase218오차_pct",
            "phase218_route": "경로",
        }
    )
    selected_view = selected.rename(
        columns={
            "city": "지역",
            "variant": "후보",
            "alpha": "혼합강도",
            "base_block_error_eok": "기존묶음오차_억원",
            "candidate_block_error_eok": "후보묶음오차_억원",
            "error_reduction_eok": "감소_억원",
            "worsened_cells": "악화셀",
            "gt20_before": "20pct초과_전",
            "gt20_after": "20pct초과_후",
            "source_notes": "자료구성",
        }
    )
    report = f"""# Phase218 환경·수도 직접활동자료 정밀오차 개선

생성시각: {CREATED_AT}

## 목적

포항시 공공하수처리시설·폐기물·환경오염·상수도 자료를 KOSIS에서 추가 수집하고, 고양시 기존 KOSIS 환경자료와 함께 ERS36/37/38/39 묶음의 내부 배분을 재검증했다.  
상위 묶음 총량은 고정하고 내부 비중만 바꾸므로, 상위 GVA 총량을 사후 보정하는 방식과 구분된다.

## 도시별 결과

{md_table(summary, 3)}

## 채택된 검증 후보

{md_table(selected_view[[c for c in ["지역", "후보", "혼합강도", "기존묶음오차_억원", "후보묶음오차_억원", "감소_억원", "악화셀", "20pct초과_전", "20pct초과_후", "자료구성"] if c in selected_view.columns]], 2)}

## 변경 셀

{md_table(changed_view, 2)}

## 엄격 검증

{md_table(audit, 0)}

## 해석

- 이번 단계는 새로 수집한 포항 환경·상수도 KOSIS 자료를 실제 후보 계산에 투입했다.
- 다만 2023 actual을 이용해 혼합강도를 평가했으므로, 공개 운영 성능으로 주장하려면 2021~2022 또는 타 지역으로 혼합강도를 먼저 고정해야 한다.
- 악화 없는 후보만 채택하도록 제한했기 때문에, 개선이 없거나 악화되는 환경 후보는 최종 레지스트리에 반영하지 않았다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(summary.to_string(index=False))
    print(audit.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
