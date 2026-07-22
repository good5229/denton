#!/usr/bin/env python3
"""Phase50 free-source fill for vulnerable sectors.

This step consumes newly collected no-key LOCALDATA logistics warehouse
downloads for Goyang and Pohang.  It builds administrative-dong/month features
for the warehouse component of KSIC H00, while keeping real-estate and broader
transport claims blocked unless suitable free/API-keyed sources are supplied.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase50_free_vulnerable_sources"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


@dataclass(frozen=True)
class CitySpec:
    city: str
    raw_file: Path
    boundary_file: Path
    boundary_kind: str


SPECS = [
    CitySpec(
        "고양시",
        RAW / "localdata_logistics_warehouses_goyang.csv",
        ROOT / "data" / "raw" / "phase37_goyang_emd" / "goyang_top_adstrd.geojson",
        "goyang_life_map",
    ),
    CitySpec(
        "포항시",
        RAW / "localdata_logistics_warehouses_pohang.csv",
        ROOT / "data" / "raw" / "phase42_pohang" / "administrative_dong_20260401.geojson",
        "admdongkor",
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_boundary(spec: CitySpec) -> gpd.GeoDataFrame:
    if spec.boundary_kind == "goyang_life_map":
        gdf = gpd.read_file(spec.boundary_file).set_crs("EPSG:5179", allow_override=True).to_crs("EPSG:5174")
        gdf = gdf.rename(columns={"cd": "emd_code", "nm": "emd_name"})
        gdf["emd_name"] = gdf["emd_name"].astype(str) + "동"
        gdf["general_gu"] = gdf["emd_code"].astype(str).str[:5].map(
            {"41281": "덕양구", "41285": "일산동구", "41287": "일산서구"}
        )
        return gdf[["emd_code", "emd_name", "general_gu", "geometry"]]
    if spec.boundary_kind == "admdongkor":
        gdf = gpd.read_file(spec.boundary_file).to_crs("EPSG:5174")
        gdf = gdf[gdf["sggnm"].isin(["포항시남구", "포항시북구"])].copy()
        gdf["emd_code"] = gdf["adm_cd"].astype(str)
        gdf["emd_name"] = gdf["adm_nm"].astype(str).str.split().str[-1]
        gdf["general_gu"] = gdf["sggnm"].map({"포항시남구": "남구", "포항시북구": "북구"})
        return gdf[["emd_code", "emd_name", "general_gu", "geometry"]]
    raise ValueError(spec.boundary_kind)


def read_logistics(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="cp949", low_memory=False)
    frame["permit_date"] = pd.to_datetime(frame["인허가일자"], errors="coerce")
    frame["close_date"] = pd.to_datetime(frame["폐업일자"], errors="coerce")
    frame["x"] = pd.to_numeric(frame["좌표정보(X)"], errors="coerce")
    frame["y"] = pd.to_numeric(frame["좌표정보(Y)"], errors="coerce")
    for col in ["보관장소면적", "일반창고면적", "냉동냉장창고면적", "직원수", "일반창고동수", "냉동냉장창고동수"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
    frame["warehouse_area"] = frame[["보관장소면적", "일반창고면적", "냉동냉장창고면적"]].max(axis=1)
    frame["warehouse_building_count"] = frame[["일반창고동수", "냉동냉장창고동수"]].sum(axis=1)
    frame["is_open_latest"] = frame["영업상태명"].astype(str).str.contains("영업", na=False)
    return frame


def spatial_join(frame: pd.DataFrame, boundary: gpd.GeoDataFrame) -> pd.DataFrame:
    valid = frame["x"].notna() & frame["y"].notna() & frame["x"].between(100_000, 500_000) & frame["y"].between(200_000, 700_000)
    points = gpd.GeoDataFrame(
        frame.loc[valid].copy(),
        geometry=gpd.points_from_xy(frame.loc[valid, "x"], frame.loc[valid, "y"]),
        crs="EPSG:5174",
    )
    joined = gpd.sjoin(points, boundary, how="left", predicate="within").drop(columns=["geometry", "index_right"])
    return pd.DataFrame(joined)


def monthly_features(city: str, joined: pd.DataFrame) -> pd.DataFrame:
    months = pd.period_range("2021-01", "2026-06", freq="M")
    emds = joined[["emd_code", "emd_name", "general_gu"]].dropna().drop_duplicates()
    if emds.empty:
        return pd.DataFrame()
    grid = emds.merge(pd.DataFrame({"period": months}), how="cross")
    rows = []
    grouped = joined.dropna(subset=["emd_code"]).groupby(["emd_code", "emd_name", "general_gu"], observed=True)
    for (emd_code, emd_name, gu), group in grouped:
        for period in months:
            month_end = period.to_timestamp(how="end")
            active = (group["permit_date"].notna() & (group["permit_date"] <= month_end)) & (
                group["close_date"].isna() | (group["close_date"] > month_end)
            )
            opened = group["permit_date"].dt.to_period("M").eq(period)
            closed = group["close_date"].dt.to_period("M").eq(period)
            active_group = group.loc[active]
            rows.append(
                {
                    "city": city,
                    "emd_code": emd_code,
                    "emd_name": emd_name,
                    "general_gu": gu,
                    "period": str(period),
                    "ksic_parent": "H00",
                    "ksic_small": "521",
                    "industry_name": "보관 및 창고업",
                    "active_warehouse_count": int(active.sum()),
                    "active_warehouse_area": float(active_group["warehouse_area"].sum()),
                    "active_warehouse_employees": float(active_group["직원수"].sum()),
                    "new_warehouse_permits": int(opened.sum()),
                    "warehouse_closures": int(closed.sum()),
                }
            )
    out = pd.DataFrame(rows)
    totals = out.groupby(["city", "period"], as_index=False)["active_warehouse_area"].sum().rename(
        columns={"active_warehouse_area": "city_period_warehouse_area"}
    )
    out = out.merge(totals, on=["city", "period"], how="left")
    out["warehouse_area_share_in_city"] = out["active_warehouse_area"] / out["city_period_warehouse_area"].replace(0, pd.NA)
    return out.sort_values(["city", "period", "emd_code"])


def run() -> dict:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    all_monthly = []
    audit_rows = []
    for spec in SPECS:
        if not spec.raw_file.exists():
            raise SystemExit(f"missing raw download: {spec.raw_file}")
        boundary = load_boundary(spec)
        raw = read_logistics(spec.raw_file)
        joined = spatial_join(raw, boundary)
        matched = joined["emd_code"].notna()
        all_monthly.append(monthly_features(spec.city, joined))
        audit_rows.append(
            {
                "city": spec.city,
                "source_name": "LOCALDATA 기타_물류_물류창고업",
                "raw_rows": int(len(raw)),
                "valid_coordinate_rows": int(joined.shape[0]),
                "matched_emd_rows": int(matched.sum()),
                "matched_emd_rate": float(matched.mean()) if len(joined) else 0.0,
                "open_latest_rows": int(raw["is_open_latest"].sum()),
                "total_warehouse_area": float(raw["warehouse_area"].sum()),
                "open_latest_warehouse_area": float(raw.loc[raw["is_open_latest"], "warehouse_area"].sum()),
                "min_permit_date": str(raw["permit_date"].min().date()) if raw["permit_date"].notna().any() else "",
                "max_permit_date": str(raw["permit_date"].max().date()) if raw["permit_date"].notna().any() else "",
                "raw_sha256": sha256(spec.raw_file),
                "free_source_status": "downloaded_without_api_key",
                "use_scope": "KSIC 521 보관 및 창고업의 행정동별 공간비중과 월별 stock/flow 보강",
                "limitation": "운수 및 창고업 전체가 아니라 창고업 하위항목만 직접 보강",
            }
        )

    monthly = pd.concat([x for x in all_monthly if len(x)], ignore_index=True)
    audit = pd.DataFrame(audit_rows)
    monthly_path = PROCESSED / "partial_stats_phase50_logistics_warehouse_emd_monthly.csv"
    audit_path = PROCESSED / "partial_stats_phase50_logistics_warehouse_source_audit.csv"
    readiness_path = PROCESSED / "partial_stats_phase50_free_source_readiness.csv"
    status_path = PROCESSED / "partial_stats_phase50_status.json"
    report_path = REPORTS / "partial_statistics_estimation_phase50_free_source_fill.md"

    monthly.to_csv(monthly_path, index=False, encoding="utf-8-sig")
    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")

    readiness = pd.DataFrame(
        [
            {
                "sector": "운수 및 창고업",
                "subsector": "보관 및 창고업",
                "city": row["city"],
                "usable_now": True,
                "available_resolution": "행정동×월",
                "feature": "물류창고 영업 stock, 창고면적, 신규 인허가, 폐업",
                "validation_status": "공간·월 보강 가능 / 전체 H00 성능검증은 보류",
                "reason": "LOCALDATA 물류창고업 무키 다운로드와 좌표가 확보됨",
            }
            for _, row in audit.iterrows()
        ]
        + [
            {
                "sector": "부동산업",
                "subsector": "부동산 임대·공급 / 관련 서비스",
                "city": city,
                "usable_now": False,
                "available_resolution": "미확보",
                "feature": "건축물대장 표제부·공동주택가격·실거래가 필요",
                "validation_status": "API 키 또는 대용량 파일 수동 다운로드 필요",
                "reason": "건축물대장 표제부는 무료 파일이나 건축HUB 대용량 UI/API 경로 확인 및 키 필요 가능",
            }
            for city in ["고양시", "포항시"]
        ]
    )
    readiness.to_csv(readiness_path, index=False, encoding="utf-8-sig")

    status = {
        "run_id": "partial_statistics_estimation_phase50_free_source_fill",
        "created_at": pd.Timestamp.now(tz="Asia/Seoul").isoformat(),
        "downloaded_without_api_key": ["LOCALDATA logistics_warehouses for Goyang and Pohang"],
        "needs_api_key_or_manual_download": [
            "국토교통부 건축물대장 표제부/전유부/공동주택가격",
            "국토교통부 실거래가 정보",
            "공공데이터포털 물류창고업 API 변동분",
            "버스·철도 승하차 또는 재차인원 API",
        ],
        "audit": audit.to_dict(orient="records"),
        "outputs": {
            "monthly": str(monthly_path.relative_to(ROOT)),
            "audit": str(audit_path.relative_to(ROOT)),
            "readiness": str(readiness_path.relative_to(ROOT)),
        },
    }
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        "# Phase50 무료자료 수집 및 취약 산업 보강",
        "",
        "## 결론",
        "",
        "- 무키로 즉시 수집 가능한 자료는 LOCALDATA 물류창고업이었다. 고양시 37행, 포항시 32행을 내려받아 행정동×월 보강 피처로 변환했다.",
        "- 이 자료는 KSIC H00 전체가 아니라 `521 보관 및 창고업`에 직접 대응한다. 따라서 운수·창고업 전체 성능 개선이 아니라 창고업 하위항목의 공간·월 변화 보강으로 해석해야 한다.",
        "- 부동산업은 건축물대장 표제부·공동주택가격·실거래가가 맞는 자료지만, 현 PC에는 공공데이터포털 키가 없고 건축HUB 대용량 다운로드도 자동 URL이 확정되지 않아 즉시 채우지 못했다.",
        "",
        "## 물류창고 자료 수집 결과",
        "",
        "| 도시 | 원천행 | 행정동 매칭행 | 매칭률 | 최신 영업행 | 총 창고면적 | 최신 영업 창고면적 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in audit.iterrows():
        report_lines.append(
            f"| {row['city']} | {row['raw_rows']} | {row['matched_emd_rows']} | {row['matched_emd_rate']:.1%} | "
            f"{row['open_latest_rows']} | {row['total_warehouse_area']:.1f} | {row['open_latest_warehouse_area']:.1f} |"
        )
    report_lines += [
        "",
        "## 산출 파일",
        "",
        f"- `{monthly_path.relative_to(ROOT)}`",
        f"- `{audit_path.relative_to(ROOT)}`",
        f"- `{readiness_path.relative_to(ROOT)}`",
        f"- `{status_path.relative_to(ROOT)}`",
        "",
        "## 확인한 무료 원천",
        "",
        "- LOCALDATA 기존 다운로드 경로: `https://file.localdata.go.kr/file/download/logistics_warehouses/info?orgCode=...` 는 현재 무키 다운로드가 가능했다. 단, 공식 LOCALDATA 포털은 2026-04-16 폐쇄되어 공공데이터포털 이용 안내로 이관되어 있다.",
        "- 공공데이터포털 물류창고업 API: 무료·일 100,000건 한도·개발/운영 자동승인이지만 `serviceKey`가 필수다. 이 API는 변동분/자동 갱신용으로 쓰고, 이번에는 무키 파일 다운로드를 우선 사용했다.",
        "- 건축물대장 표제부: 공공데이터포털 기준 무료 XLSX 파일이며 연면적·주용도·사용승인일 등 부동산업 보강에 필요한 필드가 있다. 다만 실제 파일은 건축HUB 대용량 UI 경로라 자동 수집 URL 또는 공공데이터포털/건축HUB 키가 필요하다.",
        "",
        "## 추가로 필요한 무료자료",
        "",
        "- 부동산업: 건축물대장 표제부/전유부, 공동주택가격, 실거래가·전월세 집계. 공공데이터포털 인증키 또는 건축HUB 대용량 파일 수동 다운로드가 필요하다.",
        "- 운수 및 창고업: 물류창고 외에 버스·철도 승하차, 화물자동차 등록, 항만 물동량, 택배·소화물 물량이 필요하다.",
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))

    return status


if __name__ == "__main__":
    run()
