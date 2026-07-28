#!/usr/bin/env python3
"""Phase157 external 10-sigungu real-estate feature bundle.

Phase156 proved that residential rent-flow rows can be collected for the
external 10-sigungu sample.  This phase adds two stock-side sources:

* nationwide 2025 public housing price parquet (already converted locally);
* nationwide 2026-06 BuildingHUB building-register title ZIP.

It does not claim 681/682 error rates because external 681/682 actuals are not
available.  The output is a reproducible feature bundle and a source-scope
audit showing which inputs are nationwide originals and which are extracted
subsets for the 10-region pilot.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

import run_partial_statistics_phase51_building_register_realestate as p51


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase157_external_10_realestate_feature_bundle"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase157_external_10_realestate_feature_bundle.md"

PHASE156 = DATA / "phase156_rtms_rent_external_10"
CROSSWALK = PHASE156 / "phase156_external_10_lawd_crosswalk.csv"
RENT_MONTHLY = PHASE156 / "phase156_rtms_rent_sigungu_monthly.csv"
L00_ACTUAL = PHASE156 / "phase156_l00_actual_crosswalk.csv"
HOUSING = DATA / "phase56_housing_price" / "molit_public_housing_price_2025.parquet"
BUILDING_ZIP = RAW / "phase51_building_realestate_sources" / "building_register_current_ttlldr_202606.zip"


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{float(x):,.{digits}f}")
        elif pd.api.types.is_integer_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{int(x):,}")
    view = view.fillna("").astype(str)
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(row[col].replace("|", "\\|") for col in view.columns) + " |")
    return "\n".join(lines)


def targets() -> pd.DataFrame:
    xw = pd.read_csv(
        CROSSWALK,
        dtype={"area_code": str, "lawd_cd": str, "rtms_lawd_cd": str},
    )
    xw["stock_lawd_cd"] = xw["lawd_cd"]
    xw["stock_lawd_name"] = xw["name"]
    return xw[
        [
            "source_region",
            "c1_nm",
            "area_code",
            "stock_lawd_cd",
            "stock_lawd_name",
            "lawd_cd",
            "name",
            "폐지여부",
            "rtms_lawd_cd",
            "rtms_lawd_name",
            "rtms_code_policy",
        ]
    ].copy()


def housing_features(t: pd.DataFrame) -> pd.DataFrame:
    hp = pd.read_parquet(
        HOUSING,
        columns=["법정동코드", "시도", "시군구", "전용면적", "공시가격", "건축물대장PK"],
    )
    hp["stock_lawd_cd"] = hp["법정동코드"].astype(str).str.slice(0, 5)
    sub = hp[hp["stock_lawd_cd"].isin(set(t["stock_lawd_cd"].astype(str)))].copy()
    sub["전용면적"] = pd.to_numeric(sub["전용면적"], errors="coerce").fillna(0.0)
    sub["공시가격"] = pd.to_numeric(sub["공시가격"], errors="coerce").fillna(0.0)
    out = (
        sub.groupby("stock_lawd_cd", as_index=False)
        .agg(
            public_housing_unit_count=("건축물대장PK", "count"),
            public_housing_area_sqm=("전용면적", "sum"),
            public_housing_value_eok=("공시가격", lambda s: s.sum() / 1e8),
            public_housing_median_price_eok=("공시가격", lambda s: s.replace(0, np.nan).median() / 1e8),
        )
        .sort_values("stock_lawd_cd")
    )
    sub.to_parquet(OUT / "phase157_external_10_public_housing_price_rows.parquet", index=False)
    return t.merge(out, on="stock_lawd_cd", how="left")


def extract_building_rows(t: pd.DataFrame, refresh: bool) -> pd.DataFrame:
    out_path = OUT / "phase157_external_10_building_register_rows.csv"
    if out_path.exists() and not refresh:
        return pd.read_csv(
            out_path,
            dtype={"sigungu_cd": str, "bjdong_cd": str, "stock_lawd_cd": str, "rtms_lawd_cd": str},
        )
    target_codes = set(t["stock_lawd_cd"].astype(str))
    name_by_code = t.set_index("stock_lawd_cd")[["source_region", "c1_nm", "area_code", "rtms_lawd_cd"]].to_dict("index")
    rows: list[dict[str, object]] = []
    with ZipFile(BUILDING_ZIP) as zf:
        names = zf.namelist()
        if len(names) != 1:
            raise SystemExit(f"unexpected ZIP member count: {names[:5]}")
        with zf.open(names[0]) as handle:
            for raw_line in handle:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                parts = line.split("|")
                if len(parts) < 61:
                    continue
                sigungu = parts[p51.FIELD_INDEX["sigungu_cd"]]
                if sigungu not in target_codes:
                    continue
                meta = name_by_code[sigungu]
                main_code = parts[p51.FIELD_INDEX["main_purps_cd"]]
                main_name = parts[p51.FIELD_INDEX["main_purps_cd_nm"]]
                rows.append(
                    {
                        "source_region": meta["source_region"],
                        "sigungu_name": meta["c1_nm"],
                        "kosis_area_code": meta["area_code"],
                        "stock_lawd_cd": sigungu,
                        "rtms_lawd_cd": meta["rtms_lawd_cd"],
                        "bjdong_cd": parts[p51.FIELD_INDEX["bjdong_cd"]],
                        "legal_dong_key": f"{sigungu}{parts[p51.FIELD_INDEX['bjdong_cd']]}",
                        "mgm_bldrgst_pk": parts[p51.FIELD_INDEX["mgm_bldrgst_pk"]],
                        "plat_plc": parts[p51.FIELD_INDEX["plat_plc"]],
                        "main_purps_cd": main_code,
                        "main_purps_cd_nm": main_name,
                        "use_group": p51.use_group(main_code, main_name),
                        "tot_area": p51.parse_float(parts[p51.FIELD_INDEX["tot_area"]]),
                        "vl_rat_estm_tot_area": p51.parse_float(parts[p51.FIELD_INDEX["vl_rat_estm_tot_area"]]),
                        "plat_area": p51.parse_float(parts[p51.FIELD_INDEX["plat_area"]]),
                        "hhld_cnt": p51.parse_int(parts[p51.FIELD_INDEX["hhld_cnt"]]),
                        "fmly_cnt": p51.parse_int(parts[p51.FIELD_INDEX["fmly_cnt"]]),
                        "ho_cnt": p51.parse_int(parts[p51.FIELD_INDEX["ho_cnt"]]),
                        "use_approval_day": p51.normalize_day(parts[p51.FIELD_INDEX["use_apr_day"]]),
                        "created_day": p51.normalize_day(parts[p51.FIELD_INDEX["crtn_day"]]),
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out


def building_features(t: pd.DataFrame, refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = extract_building_rows(t, refresh=refresh)
    if rows.empty:
        return rows, pd.DataFrame()
    use = (
        rows.groupby(["stock_lawd_cd", "use_group"], as_index=False)
        .agg(
            building_count=("mgm_bldrgst_pk", "count"),
            total_floor_area=("tot_area", "sum"),
            vl_floor_area=("vl_rat_estm_tot_area", "sum"),
            parcel_area=("plat_area", "sum"),
            household_count=("hhld_cnt", "sum"),
            family_count=("fmly_cnt", "sum"),
            unit_count=("ho_cnt", "sum"),
        )
        .sort_values(["stock_lawd_cd", "use_group"])
    )
    use.to_csv(OUT / "phase157_external_10_building_use_features.csv", index=False, encoding="utf-8-sig")
    wide = use.pivot_table(
        index="stock_lawd_cd",
        columns="use_group",
        values=["building_count", "total_floor_area"],
        aggfunc="sum",
        fill_value=0,
    )
    wide.columns = [f"{metric}_{group}" for metric, group in wide.columns]
    wide = wide.reset_index()
    total = rows.groupby("stock_lawd_cd", as_index=False).agg(
        building_rows=("mgm_bldrgst_pk", "count"),
        building_total_floor_area=("tot_area", "sum"),
        building_vl_floor_area=("vl_rat_estm_tot_area", "sum"),
        building_households=("hhld_cnt", "sum"),
        building_units=("ho_cnt", "sum"),
    )
    return rows, total.merge(wide, on="stock_lawd_cd", how="left")


def rent_features() -> pd.DataFrame:
    rent = pd.read_csv(RENT_MONTHLY, encoding="utf-8-sig", dtype={"kosis_area_code": str, "lawd_cd": str})
    rent["year"] = rent["period"].astype(str).str.slice(0, 4)
    r2023 = rent[rent["year"].eq("2023")].copy()
    for col in ["rent_contract_count", "deposit_10k_krw", "monthly_rent_10k_krw", "area_sqm"]:
        r2023[col] = pd.to_numeric(r2023[col], errors="coerce").fillna(0.0)
    out = (
        r2023.groupby("lawd_cd", as_index=False)
        .agg(
            rent_contract_count=("rent_contract_count", "sum"),
            rent_deposit_eok=("deposit_10k_krw", lambda s: s.sum() / 10000),
            rent_monthly_eok=("monthly_rent_10k_krw", lambda s: s.sum() / 10000),
            rent_area_sqm=("area_sqm", "sum"),
            rent_asset_types=("asset_type", "nunique"),
        )
        .rename(columns={"lawd_cd": "rtms_lawd_cd"})
    )
    out["rent_deposit_per_contract_eok"] = out["rent_deposit_eok"] / out["rent_contract_count"].replace(0, np.nan)
    out["rent_deposit_per_area_10k_per_sqm"] = out["rent_deposit_eok"] * 10000 / out["rent_area_sqm"].replace(0, np.nan)
    return out


def l00_actual() -> pd.DataFrame:
    return pd.read_csv(L00_ACTUAL, encoding="utf-8-sig", dtype={"area_code": str, "rtms_lawd_cd": str})


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-building", action="store_true")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    t = targets()
    h = housing_features(t)
    b_rows, b = building_features(t, refresh=args.refresh_building)
    r = rent_features()
    l00 = l00_actual()[["area_code", "l00_realestate_gva_eok"]]

    features = (
        h.merge(b, on="stock_lawd_cd", how="left")
        .merge(r, on="rtms_lawd_cd", how="left")
        .merge(l00, on="area_code", how="left")
    )
    for col in [
        "public_housing_value_eok",
        "public_housing_area_sqm",
        "building_total_floor_area",
        "rent_deposit_eok",
        "rent_contract_count",
        "l00_realestate_gva_eok",
    ]:
        if col in features:
            features[col] = pd.to_numeric(features[col], errors="coerce")
    features["housing_value_to_l00_pct"] = features["public_housing_value_eok"] / features[
        "l00_realestate_gva_eok"
    ].replace(0, np.nan) * 100
    features["rent_deposit_to_l00_pct"] = features["rent_deposit_eok"] / features[
        "l00_realestate_gva_eok"
    ].replace(0, np.nan) * 100
    features["rent_deposit_to_housing_value_pct"] = features["rent_deposit_eok"] / features[
        "public_housing_value_eok"
    ].replace(0, np.nan) * 100
    features["housing_value_per_unit_eok"] = features["public_housing_value_eok"] / features[
        "public_housing_unit_count"
    ].replace(0, np.nan)
    features["building_residential_area_share_pct"] = features.get("total_floor_area_주거", 0) / features[
        "building_total_floor_area"
    ].replace(0, np.nan) * 100
    features["building_commercial_area_share_pct"] = features.get("total_floor_area_상업·업무", 0) / features[
        "building_total_floor_area"
    ].replace(0, np.nan) * 100

    source_scope = pd.DataFrame(
        [
            {
                "source": "국토교통부 공동주택 공시가격 2025",
                "local_original": str(HOUSING.relative_to(ROOT)),
                "original_scope": "전국 원본 parquet",
                "phase157_use": "외부 10개 시군구 stock_lawd_cd prefix 추출",
                "rows_or_calls": int(pd.read_parquet(HOUSING, columns=["법정동코드"]).shape[0]),
                "source_limit": "2025 현재 stock 자료: 속보성 과거시점 예측에는 직접 사용 금지, 정밀화/구조 검증용",
            },
            {
                "source": "건축HUB 건축물대장 표제부 2026-06",
                "local_original": str(BUILDING_ZIP.relative_to(ROOT)),
                "original_scope": "전국 원본 ZIP",
                "phase157_use": "외부 10개 시군구 stock_lawd_cd 스트리밍 추출",
                "rows_or_calls": int(len(b_rows)),
                "source_limit": "2026 현재 stock 자료: 속보성 과거시점 예측에는 직접 사용 금지, 정밀화/구조 검증용",
            },
            {
                "source": "국토교통부 RTMS 전월세 3종",
                "local_original": str(PHASE156.relative_to(ROOT)),
                "original_scope": "전국 API이나 Phase156 로컬 raw는 외부 10개 표본만 저장",
                "phase157_use": "2023 전월세 계약·보증금·면적 집계",
                "rows_or_calls": int(features["rent_contract_count"].sum()),
                "source_limit": "행별 공표일자 없음: strict Q+1개월 속보 성능 주장은 보수적 lag 감사 필요",
            },
            {
                "source": "공인중개사무소 자료",
                "local_original": "data/raw/phase53_free_candidate_sources/*broker*",
                "original_scope": "현재 로컬은 고양·포항 개별 파일만 확인",
                "phase157_use": "외부 10개 지역에는 미적용",
                "rows_or_calls": 0,
                "source_limit": "외부 10개 지역 일반화를 위해 전국 또는 지역별 중개업소 파일/API 추가 필요",
            },
        ]
    )
    features.to_csv(OUT / "phase157_external_10_realestate_feature_bundle.csv", index=False, encoding="utf-8-sig")
    source_scope.to_csv(OUT / "phase157_source_scope_audit.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "phase": "phase157_external_10_realestate_feature_bundle",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": [
            str(CROSSWALK.relative_to(ROOT)),
            str(RENT_MONTHLY.relative_to(ROOT)),
            str(L00_ACTUAL.relative_to(ROOT)),
            str(HOUSING.relative_to(ROOT)),
            str(BUILDING_ZIP.relative_to(ROOT)),
        ],
        "outputs": [
            "phase157_external_10_realestate_feature_bundle.csv",
            "phase157_external_10_building_register_rows.csv",
            "phase157_external_10_building_use_features.csv",
            "phase157_external_10_public_housing_price_rows.parquet",
            "phase157_source_scope_audit.csv",
            str(REPORT.relative_to(ROOT)),
        ],
        "validation_boundary": "External 681/682 actuals unavailable; this is a feature coverage and L00-scale audit, not an error-rate validation.",
    }
    (OUT / "phase157_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    view_cols = [
        "source_region",
        "c1_nm",
        "l00_realestate_gva_eok",
        "public_housing_unit_count",
        "public_housing_value_eok",
        "building_rows",
        "building_total_floor_area",
        "rent_contract_count",
        "rent_deposit_eok",
        "housing_value_to_l00_pct",
        "rent_deposit_to_l00_pct",
        "rent_deposit_to_housing_value_pct",
        "building_residential_area_share_pct",
        "building_commercial_area_share_pct",
    ]
    display = features[view_cols].sort_values("rent_deposit_to_l00_pct", ascending=False)
    report = f"""# Phase157 외부 10개 시군구 부동산 재고·임대흐름 결합 감사

## 목적

Phase156에서 확보한 외부 10개 시군구 전월세 흐름자료에 공시가격과 건축물대장 stock 자료를 결합했다. 목표는 고양·포항에서 쓰던 부동산업 소분류 배분 논리가 외부지역으로 확장 가능한 자료구조를 갖는지 확인하는 것이다.

## 핵심 결과

- 공시가격: 전국 parquet에서 외부 10개 지역 추출 가능
- 건축물대장: 전국 ZIP에서 외부 10개 지역 스트리밍 추출 가능
- 전월세: Phase156에서 10개 지역 151,965행 확보
- 공인중개사무소: 현재 로컬 원본은 고양·포항 개별 파일뿐이라 외부 10개 일반화에는 아직 미적용
- 검증 경계: 외부 10개 지역의 681/682 actual이 없으므로 소분류 오차율은 주장하지 않음

## 자료 원본 범위 감사

{md_table(source_scope.rename(columns={'source':'자료','local_original':'로컬 원본','original_scope':'원본 범위','phase157_use':'Phase157 사용','rows_or_calls':'행수/호출','source_limit':'사용 제한'}), 0)}

## 2023 부동산업 총량 대비 결합 지표

{md_table(display.rename(columns={'source_region':'광역','c1_nm':'시군구','l00_realestate_gva_eok':'2023 부동산업 GVA(억원)','public_housing_unit_count':'공시가격 주택수','public_housing_value_eok':'공시가격 총액(억원)','building_rows':'건축물대장 행수','building_total_floor_area':'건축물 연면적㎡','rent_contract_count':'전월세 계약건수','rent_deposit_eok':'전월세 보증금(억원)','housing_value_to_l00_pct':'공시가격/GVA(%)','rent_deposit_to_l00_pct':'보증금/GVA(%)','rent_deposit_to_housing_value_pct':'보증금/공시가격(%)','building_residential_area_share_pct':'주거연면적 비중(%)','building_commercial_area_share_pct':'상업업무연면적 비중(%)'}), 2)}

## 해석

1. 전월세 보증금/GVA는 영동·강진처럼 저거래 지역과 인천 동구·광주 북구 같은 고밀도 지역을 강하게 구분한다.
2. 공시가격/GVA와 전월세 보증금/공시가격을 함께 보면 “재고가 큰데 임대흐름이 약한 지역”과 “재고 대비 임대흐름이 강한 지역”을 분리할 수 있다.
3. 건축물대장 연면적은 주거/상업업무 비중을 제공하므로 681 임대·공급축과 682 관련서비스축을 분리할 구조 변수로 쓸 수 있다.
4. 다만 중개업소 외부 10개 지역 자료가 빠져 있어 682 서비스축의 핵심 활동자료가 아직 불완전하다.
5. 따라서 현 단계 포스터/보고서에는 `외부지역 자료확장성`, `부동산업 총량 대비 지표 일관성`, `현행 코드-공표 코드 분리 감사`를 contribution으로 쓰고, 외부 681/682 오차율은 쓰지 않는다.

## 다음 필요자료

- 외부 10개 지역 공인중개사무소 전국/지역별 무료 자료
- 가능하면 외부지역 681/682 소분류 actual 또는 독립 검증자료
- 행별 공표일자를 대체할 RTMS 보수 공표시차 정책
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
