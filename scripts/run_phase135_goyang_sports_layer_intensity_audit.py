#!/usr/bin/env python3
"""Phase135: audit Goyang sports/movie layers as high-gap activity indicators.

This phase does not overwrite GVA predictions.  It asks a narrower question:
do the newly collected free Goyang portal layers contain stronger activity
intensity variables than a plain establishment count for the remaining
high-amount-gap industries?

The answer is relevant because Phase133 rejected weak retrospective packages.
If the new layers only provide current-snapshot facilities, they can support
precision/spatial allocation, but not strict 2023 Q+1M flash estimation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "phase37_goyang_emd"
OUT = DATA / "phase135_goyang_sports_layer_intensity_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase135_goyang_sports_layer_intensity_audit.md"

PHASE133 = DATA / "phase133_goyang_amount_weighted_refinement" / "phase133_guarded_amount_route_registry.csv"
PHASE134_COMWEL = DATA / "phase134_goyang_high_gap_source_roadmap" / "phase134_comwel_direct_coverage.csv"

LAYERS = {
    "LYR0084": ("J00", "59", "영화상영관"),
    "LYR0099": ("ERS", "91", "골프연습장업"),
    "LYR0100": ("ERS", "91", "골프장"),
    "LYR0101": ("ERS", "91", "당구장업"),
    "LYR0102": ("ERS", "91", "빙상장업"),
    "LYR0103": ("ERS", "91", "수영장업"),
    "LYR0104": ("ERS", "91", "승마장업"),
    "LYR0105": ("ERS", "91", "썰매장업"),
    "LYR0106": ("ERS", "91", "체육도장업"),
    "LYR0107": ("ERS", "91", "체력단련장업"),
}


def read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("-", "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)


def layer_summary() -> pd.DataFrame:
    rows = []
    for layer_id, (parent, middle, label) in LAYERS.items():
        path = RAW / f"goyang_layer_{layer_id}.csv"
        if not path.exists() or not path.stat().st_size:
            rows.append({
                "layer_id": layer_id,
                "parent_code": parent,
                "middle_code": middle,
                "layer_name": label,
                "status": "missing",
                "reference_period": "",
                "row_count": 0,
                "leader_count": 0.0,
                "building_count": 0.0,
                "building_area_sqm": 0.0,
                "member_capacity": 0.0,
                "intensity_score": 0.0,
                "strict_flash_2023": "N",
                "use_track": "unavailable",
            })
            continue
        try:
            df = read_csv_any(path)
            ref = str(df["기준년월"].dropna().iloc[0]) if "기준년월" in df.columns and df["기준년월"].notna().any() else ""
            leader = float(num(df["지도자수"]).sum()) if "지도자수" in df.columns else 0.0
            bcnt = float(num(df["건축물동수"]).sum()) if "건축물동수" in df.columns else 0.0
            area = float(num(df["건축물연면적"]).sum()) if "건축물연면적" in df.columns else 0.0
            members = float(num(df["회원모집총인원"]).sum()) if "회원모집총인원" in df.columns else 0.0
            # A scale-free diagnostic index, not a GVA predictor.
            intensity = np.log1p(len(df)) + np.log1p(leader) + np.log1p(area) + np.log1p(members)
            strict = "Y" if ref and ref <= "202304" else "N"
            rows.append({
                "layer_id": layer_id,
                "parent_code": parent,
                "middle_code": middle,
                "layer_name": label,
                "status": "collected",
                "reference_period": ref,
                "row_count": int(len(df)),
                "leader_count": leader,
                "building_count": bcnt,
                "building_area_sqm": area,
                "member_capacity": members,
                "intensity_score": float(intensity),
                "strict_flash_2023": strict,
                "use_track": "precision_spatial_structure" if strict == "N" else "strict_flash_candidate",
            })
        except Exception as exc:  # noqa: BLE001
            rows.append({
                "layer_id": layer_id,
                "parent_code": parent,
                "middle_code": middle,
                "layer_name": label,
                "status": f"parse_failed:{type(exc).__name__}",
                "reference_period": "",
                "row_count": 0,
                "leader_count": 0.0,
                "building_count": 0.0,
                "building_area_sqm": 0.0,
                "member_capacity": 0.0,
                "intensity_score": 0.0,
                "strict_flash_2023": "N",
                "use_track": "parse_fix_needed",
            })
    return pd.DataFrame(rows).sort_values(["parent_code", "middle_code", "intensity_score"], ascending=[True, True, False])


def group_summary(layers: pd.DataFrame) -> pd.DataFrame:
    g = (
        layers.groupby(["parent_code", "middle_code"], as_index=False)
        .agg(
            collected_layers=("status", lambda s: int((s == "collected").sum())),
            row_count=("row_count", "sum"),
            leader_count=("leader_count", "sum"),
            building_count=("building_count", "sum"),
            building_area_sqm=("building_area_sqm", "sum"),
            member_capacity=("member_capacity", "sum"),
            intensity_score=("intensity_score", "sum"),
            strict_flash_2023_layers=("strict_flash_2023", lambda s: int((s == "Y").sum())),
        )
    )
    return g


def attach_gva_context(group: pd.DataFrame) -> pd.DataFrame:
    gva = pd.read_csv(PHASE133, dtype={"middle_code": str})
    gva["middle_code"] = gva["middle_code"].astype(str).str.zfill(2)
    keep = gva[[
        "parent_code",
        "middle_code",
        "middle_label",
        "actual_gva_eok",
        "phase133_prediction_eok",
        "phase133_error_eok",
        "phase133_error_rate_pct",
    ]]
    out = group.merge(keep, on=["parent_code", "middle_code"], how="left")
    out["facility_gva_scale_eok_per_row"] = np.where(out["row_count"] > 0, out["actual_gva_eok"] / out["row_count"], np.nan)
    out["error_eok_per_row"] = np.where(out["row_count"] > 0, out["phase133_error_eok"] / out["row_count"], np.nan)
    out["diagnosis"] = np.where(
        out["strict_flash_2023_layers"].gt(0),
        "속보 후보 가능",
        "현재 snapshot 구조축: 2023 속보에는 부적격",
    )
    return out.sort_values("phase133_error_eok", ascending=False)


def compare_comwel(group_context: pd.DataFrame) -> pd.DataFrame:
    if not PHASE134_COMWEL.exists():
        return pd.DataFrame()
    c = pd.read_csv(PHASE134_COMWEL, dtype={"middle_code": str})
    c["middle_code"] = c["middle_code"].astype(str).str.zfill(2)
    sports = group_context[group_context["parent_code"].eq("ERS") & group_context["middle_code"].eq("91")]
    movie = group_context[group_context["parent_code"].eq("J00") & group_context["middle_code"].eq("59")]
    rows = []
    for _, r in pd.concat([sports, movie], ignore_index=True).iterrows():
        cw = c[c["parent_code"].eq(r["parent_code"]) & c["middle_code"].eq(r["middle_code"])]
        rows.append({
            "parent_code": r["parent_code"],
            "middle_code": r["middle_code"],
            "middle_label": r.get("middle_label", ""),
            "portal_layer_rows": int(r["row_count"]),
            "portal_member_capacity": float(r["member_capacity"]),
            "portal_building_area_sqm": float(r["building_area_sqm"]),
            "comwel_active_rows": int(cw["active_rows"].iloc[0]) if len(cw) else 0,
            "comwel_active_workers": float(cw["active_workers"].iloc[0]) if len(cw) else 0.0,
            "actual_gva_eok": float(r["actual_gva_eok"]),
            "remaining_error_eok": float(r["phase133_error_eok"]),
            "interpretation": "시설 강도+고용보험을 함께 써야 함" if r["row_count"] > 0 and len(cw) else "관객·매출 외부 API 필요",
        })
    return pd.DataFrame(rows)


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_eok", " 억원").replace("_pct", " %").replace("_sqm", " ㎡").replace("_", " ") for c in d.columns]

    def fmt(v: object) -> str:
        if pd.isna(v):
            return ""
        if isinstance(v, (float, np.floating)):
            return f"{float(v):,.2f}"
        if isinstance(v, (int, np.integer)):
            return f"{int(v):,}"
        return str(v).replace("|", "\\|")

    body = ["| " + " | ".join(fmt(x) for x in row) + " |" for row in d.to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(layers: pd.DataFrame, context: pd.DataFrame, compare: pd.DataFrame) -> None:
    sports = context[context["parent_code"].eq("ERS") & context["middle_code"].eq("91")]
    if len(sports):
        s = sports.iloc[0]
        sports_sentence = (
            f"ERS91 스포츠·오락은 고양시 포털 레이어에서 {int(s['row_count']):,}개 시설 행, "
            f"{float(s['leader_count']):,.0f}명 지도자수, {float(s['building_area_sqm']):,.0f}㎡ 건축물연면적, "
            f"{float(s['member_capacity']):,.0f}명 회원모집총인원을 확인했다. 따라서 정밀화·행정동 공간배분 구조축으로는 기존 단순 시설 수보다 낫다."
        )
    else:
        sports_sentence = "ERS91 스포츠·오락 레이어 집계가 없어 추가 수집 또는 파싱 보완이 필요하다."
    REPORT.write_text("\n".join([
        "# Phase135 고양시 스포츠·영화 레이어 활동강도 감사",
        "",
        "## 목적",
        "",
        "Phase134에서 추가 수집한 고양시 무료 포털 레이어가 단순 시설 수를 넘어 GVA 배분에 쓸 만한 강도 변수를 갖는지 확인했다. 이 단계는 예측값을 바꾸지 않고, 정밀화·공간배분 후보성과 strict flash 부적격성을 분리한다.",
        "",
        "## 레이어별 활동강도 변수",
        "",
        md_table(layers, ["layer_id", "layer_name", "reference_period", "row_count", "leader_count", "building_area_sqm", "member_capacity", "intensity_score", "strict_flash_2023", "use_track"]),
        "",
        "## GVA 잔여오차와 시설강도 비교",
        "",
        md_table(context, ["parent_code", "middle_code", "middle_label", "actual_gva_eok", "phase133_error_eok", "phase133_error_rate_pct", "row_count", "member_capacity", "building_area_sqm", "facility_gva_scale_eok_per_row", "error_eok_per_row", "diagnosis"]),
        "",
        "## 포털 레이어와 고용보험 세부업종 결합 가능성",
        "",
        md_table(compare, compare.columns.tolist()),
        "",
        "## 판정",
        "",
        f"1. {sports_sentence}",
        "2. 하지만 기준년월이 202607이므로 2023년 Q+1개월 strict flash에는 사용할 수 없다. Phase132 기준상 과거 as-of archive나 변동분 공표달력이 없으면 속보 성능으로 주장하면 안 된다.",
        "3. J59 영상·오디오 쪽 영화상영관 레이어는 0행으로 내려와, 이 경로만으로는 금액격차 220억원을 설명하기 어렵다. KOBIS 지역 관객·매출 또는 고양시 영상산업 기업/제작지원 자료가 필요하다.",
        "4. 다음 모델 개선은 `ERS91 공간배분/정밀화 구조축`에는 포털 레이어를 붙이고, `연·분기·월 GVA 금액 예측`에는 KOPIS/KOBIS 관객·매출 API를 붙이는 2트랙으로 가야 한다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    layers = layer_summary()
    group = group_summary(layers)
    context = attach_gva_context(group)
    compare = compare_comwel(context)
    layers.to_csv(OUT / "phase135_goyang_layer_intensity_summary.csv", index=False)
    group.to_csv(OUT / "phase135_goyang_layer_group_summary.csv", index=False)
    context.to_csv(OUT / "phase135_goyang_layer_gva_context.csv", index=False)
    compare.to_csv(OUT / "phase135_portal_comwel_comparison.csv", index=False)
    write_report(layers, context, compare)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
