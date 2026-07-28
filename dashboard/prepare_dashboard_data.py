#!/usr/bin/env python3
"""Build compact JSON data for the nationwide GRDP/GVA dashboard."""

from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DASH = Path(__file__).resolve().parent
DATA = DASH / "data"
NATION = ROOT / "nationwide" / "outputs"
ADMIN_CENTER_RAW = ROOT / "data" / "raw" / "admin_center_coordinates"
SIGUNGU_SHP = ROOT / (
    "data/interim/extracted/3f517984bfdf4bbe43ee2a8849cff010d70ac5a826f880e6976b9a1f2b30611b/"
    "2. 경계/2. 2025년 2분기 기준 시군구 경계/bnd_sigungu_00_2025_2Q.shp"
)

TRACK = "recursive_no_target_actual"

SGIS_PREFIX_TO_REGION = {
    "11": ("서울", "서울특별시"),
    "21": ("부산", "부산광역시"),
    "22": ("대구", "대구광역시"),
    "23": ("인천", "인천광역시"),
    "24": ("광주", "광주광역시"),
    "25": ("대전", "대전광역시"),
    "26": ("울산", "울산광역시"),
    "29": ("세종", "세종특별자치시"),
    "31": ("경기도", "경기도"),
    "32": ("강원", "강원특별자치도"),
    "33": ("충북", "충청북도"),
    "34": ("충남", "충청남도"),
    "35": ("전북", "전북특별자치도"),
    "36": ("전남", "전라남도"),
    "37": ("경북", "경상북도"),
    "38": ("경남", "경상남도"),
    "39": ("제주", "제주특별자치도"),
}

DISPLAY_REGION = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기도": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}

FULL_REGION_TO_QUARTER = {v: k for k, v in DISPLAY_REGION.items()}
FULL_REGION_TO_QUARTER.update({"경기도": "경기도"})
REGION_ADDRESS_ALIASES = {
    "강원 ": "강원",
    "강원도 ": "강원",
    "충북 ": "충북",
    "충청북도 ": "충북",
    "충남 ": "충남",
    "충청남도 ": "충남",
    "전북 ": "전북",
    "전라북도 ": "전북",
    "전남 ": "전남",
    "전라남도 ": "전남",
    "경북 ": "경북",
    "경상북도 ": "경북",
    "경남 ": "경남",
    "경상남도 ": "경남",
}


def clean_number(value, digits: int = 1):
    if value is None or pd.isna(value):
        return None
    v = float(value)
    if not math.isfinite(v):
        return None
    return round(v, digits)


def round_records(df: pd.DataFrame, cols: list[str], digits: int = 1) -> list[dict]:
    out = []
    for rec in df.to_dict("records"):
        clean = {}
        for k, v in rec.items():
            if k in cols:
                clean[k] = clean_number(v, digits)
            elif isinstance(v, float):
                clean[k] = clean_number(v, 3)
            else:
                clean[k] = None if pd.isna(v) else v
        out.append(clean)
    return out


def load_centroids() -> tuple[pd.DataFrame, pd.DataFrame]:
    g = gpd.read_file(SIGUNGU_SHP)[["SIGUNGU_CD", "SIGUNGU_NM", "geometry"]].copy()
    g["prefix"] = g["SIGUNGU_CD"].astype(str).str[:2]
    g["quarter_region"] = g["prefix"].map(lambda x: SGIS_PREFIX_TO_REGION.get(x, (None, None))[0])
    g["province_full"] = g["prefix"].map(lambda x: SGIS_PREFIX_TO_REGION.get(x, (None, None))[1])
    g = g.dropna(subset=["quarter_region"]).to_crs(4326)
    g["lon"] = g.geometry.representative_point().x
    g["lat"] = g.geometry.representative_point().y
    province = g.dissolve("quarter_region", as_index=False)
    province["lon"] = province.geometry.representative_point().x
    province["lat"] = province.geometry.representative_point().y
    province["province_full"] = province["quarter_region"].map(DISPLAY_REGION)
    sig = g[["quarter_region", "province_full", "SIGUNGU_CD", "SIGUNGU_NM", "lat", "lon", "geometry"]].copy()
    return (
        province[["quarter_region", "province_full", "lat", "lon"]],
        sig[["quarter_region", "province_full", "SIGUNGU_CD", "SIGUNGU_NM", "lat", "lon", "geometry"]],
    )


def annual_sigungu_centers(sig_geom: pd.DataFrame, annual_city_keys: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, key in annual_city_keys.drop_duplicates().iterrows():
        qr = key["quarter_region"]
        city = key["city"]
        candidates = sig_geom[sig_geom["quarter_region"].eq(qr)].copy()
        exact = candidates[candidates["SIGUNGU_NM"].eq(city)]
        if not exact.empty:
            geom = exact.geometry.union_all()
            cd = ",".join(exact["SIGUNGU_CD"].astype(str).tolist())
        else:
            # Annual GRVA tables often use integrated cities, e.g. 고양시,
            # while the map boundary has 고양시 덕양구/일산동구/일산서구.
            prefix = candidates[candidates["SIGUNGU_NM"].str.startswith(city + " ", na=False)]
            if prefix.empty and city.endswith("시"):
                prefix = candidates[candidates["SIGUNGU_NM"].str.startswith(city, na=False)]
            if prefix.empty:
                prefix = candidates[candidates["SIGUNGU_NM"].str.contains(city, regex=False, na=False)]
            if prefix.empty:
                # Historical GRVA can follow the period's jurisdiction while
                # the 2025 boundary follows a later transfer, e.g. 군위군.
                prefix = sig_geom[sig_geom["SIGUNGU_NM"].eq(city)].copy()
            if prefix.empty:
                continue
            geom = prefix.geometry.union_all()
            cd = ",".join(prefix["SIGUNGU_CD"].astype(str).tolist())
        p = gpd.GeoSeries([geom], crs=4326).representative_point().iloc[0]
        rows.append(
            {
                "quarter_region": qr,
                "province_full": DISPLAY_REGION.get(qr, key.get("province_full")),
                "city": city,
                "sigungu_cd": cd,
                "lat": float(p.y),
                "lon": float(p.x),
            }
        )
    return pd.DataFrame(rows)


def build_regions() -> list[dict]:
    province_centers, sig_geom = load_centroids()
    annual = pd.read_csv(NATION / "annual_sigungu_gva_normalized.csv")
    annual_keys = annual[["quarter_region", "province_full", "city"]].drop_duplicates()
    city_centers = annual_sigungu_centers(sig_geom, annual_keys)
    admin_centers = load_admin_center_overrides()

    regions = []
    for _, r in province_centers.iterrows():
        region_id = f"sido:{r['quarter_region']}"
        override = admin_centers.get(region_id, {})
        regions.append(
            {
                "id": region_id,
                "type": "sido",
                "name": r["province_full"],
                "shortName": r["quarter_region"],
                "quarterRegion": r["quarter_region"],
                "city": None,
                "lat": clean_number(override.get("lat", r["lat"]), 6),
                "lon": clean_number(override.get("lon", r["lon"]), 6),
                "coordinateBasis": override.get("coordinateBasis", "행정구역 도형 대표점"),
                "coordinateStatus": override.get("coordinateStatus", "admin_office_coordinate_not_yet_sourced"),
                "coordinateSource": override.get("coordinateSource"),
            }
        )
    for _, r in city_centers.iterrows():
        region_id = f"sigungu:{r['quarter_region']}:{r['city']}"
        override = admin_centers.get(region_id, {})
        regions.append(
            {
                "id": region_id,
                "type": "sigungu",
                "name": f"{r['province_full']} {r['city']}",
                "shortName": r["city"],
                "quarterRegion": r["quarter_region"],
                "city": r["city"],
                "sigunguCd": r["sigungu_cd"],
                "lat": clean_number(override.get("lat", r["lat"]), 6),
                "lon": clean_number(override.get("lon", r["lon"]), 6),
                "coordinateBasis": override.get("coordinateBasis", "행정구역 도형 대표점"),
                "coordinateStatus": override.get("coordinateStatus", "admin_office_coordinate_not_yet_sourced"),
                "coordinateSource": override.get("coordinateSource"),
            }
        )
    return regions


def load_admin_center_overrides() -> dict[str, dict]:
    """Load free public office coordinates where a stable source is available.

    The dashboard still falls back to geometry representative points for
    municipalities without sourced office coordinates.
    """

    overrides: dict[str, dict] = {}
    overrides.update(load_esri_local_government_office_overrides())
    incheon = ADMIN_CENTER_RAW / "incheon_facility_info_15076595.csv"
    if incheon.exists():
        df = pd.read_csv(incheon, encoding="cp949")
        df = df[df["분야"].eq("행정기관")].copy()
        src = "공공데이터포털 인천광역시_시설 정보 현황_20210107"
        for _, r in df[df["유형"].eq("시청")].iterrows():
            if r.get("시설명") == "인천광역시청":
                overrides["sido:인천"] = {
                    "lat": r["위도"],
                    "lon": r["경도"],
                    "coordinateBasis": "행정청사 좌표",
                    "coordinateStatus": "admin_office_coordinate_sourced",
                    "coordinateSource": src,
                }
        for _, r in df[df["유형"].eq("군구청")].iterrows():
            facility = str(r["시설명"]).strip()
            city = facility.split()[0].replace("청", "").replace("민원실", "").strip()
            if not city:
                city = str(r["시군구"]).strip()
            overrides[f"sigungu:인천:{city}"] = {
                "lat": r["위도"],
                "lon": r["경도"],
                "coordinateBasis": "행정청사 좌표",
                "coordinateStatus": "admin_office_coordinate_sourced",
                "coordinateSource": src,
            }
    overrides.update(load_gyeonggi_admin_center_overrides())
    return overrides


def read_korean_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def pick_col(df: pd.DataFrame, candidates: list[str], contains: list[str] | None = None) -> str | None:
    cols = [str(c).strip() for c in df.columns]
    rename = {old: new for old, new in zip(df.columns, cols)}
    if rename:
        df.rename(columns=rename, inplace=True)
    for c in candidates:
        if c in df.columns:
            return c
    if contains:
        for c in df.columns:
            s = str(c)
            if all(token in s for token in contains):
                return s
    return None


def load_gyeonggi_admin_center_overrides() -> dict[str, dict]:
    """Load Gyeonggi office coordinates when the manual/API CSV is available.

    The official Gyeonggi Data Dream endpoint has been identified, but direct
    non-browser CSV download can return a security-policy HTML page. If the CSV
    is later downloaded manually or through a working API route to the expected
    path, this loader applies it automatically.
    """

    path = ADMIN_CENTER_RAW / "gyeonggi_office_branch_15057551.csv"
    if not path.exists():
        return {}
    df = read_korean_csv(path)
    if df.empty:
        return {}

    sigun_col = pick_col(df, ["시군명", "SIGUN_NM", "SIGUN_NM".lower()], ["시군"])
    type_col = pick_col(df, ["구분명", "기관구분", "분류", "시설구분"], ["구분"])
    name_col = pick_col(df, ["기관명", "명칭", "청사명", "시설명"], ["명"])
    lat_col = pick_col(df, ["위도", "WGS84위도", "WGS84_LAT", "REFINE_WGS84_LAT"], ["위도"])
    lon_col = pick_col(df, ["경도", "WGS84경도", "WGS84_LOGT", "REFINE_WGS84_LOGT"], ["경도"])
    if not lat_col or not lon_col:
        return {}

    src = "공공데이터포털/경기데이터드림 경기도 청사및출장소 현황"
    overrides: dict[str, dict] = {}
    for _, r in df.iterrows():
        lat = pd.to_numeric(r.get(lat_col), errors="coerce")
        lon = pd.to_numeric(r.get(lon_col), errors="coerce")
        if pd.isna(lat) or pd.isna(lon):
            continue
        row_type = str(r.get(type_col, "")).strip() if type_col else ""
        row_name = str(r.get(name_col, "")).strip() if name_col else ""
        sigun = str(r.get(sigun_col, "")).strip() if sigun_col else ""
        descriptor = f"{row_type} {row_name}"

        # Province offices: prefer the main 도청 row. Exclude 출장소/북부청사
        # because the dashboard's province-level search should move to the
        # primary provincial office unless the user explicitly searches branch.
        if "도청" in descriptor and "출장" not in descriptor and "북부" not in descriptor:
            overrides["sido:경기도"] = {
                "lat": lat,
                "lon": lon,
                "coordinateBasis": "행정청사 좌표",
                "coordinateStatus": "admin_office_coordinate_sourced",
                "coordinateSource": src,
            }
            continue

        if not sigun:
            # If a row lacks 시군명, try to infer from an office name such as
            # 고양시청/가평군청. Keep this conservative to avoid 읍면동 rows.
            tokens = row_name.replace("청", "청 ").split()
            sigun = tokens[0].replace("청", "").strip() if tokens else ""
        if not sigun:
            continue
        if any(word in descriptor for word in ("시청", "군청")):
            city = sigun if sigun.endswith(("시", "군")) else row_name.replace("청", "").strip()
            if city:
                overrides[f"sigungu:경기도:{city}"] = {
                    "lat": lat,
                    "lon": lon,
                    "coordinateBasis": "행정청사 좌표",
                    "coordinateStatus": "admin_office_coordinate_sourced",
                    "coordinateSource": src,
                }
    return overrides


def strip_office_name(name: str) -> str:
    out = str(name or "").strip()
    if "(" in out:
        out = out.split("(", 1)[0].strip()
    for suffix in ("시청", "군청", "구청", "도청", "청"):
        if out.endswith(suffix):
            out = out[: -len("청")].strip()
            break
    return out


def region_from_address(address: str) -> str | None:
    addr = str(address or "").strip()
    for full, region in sorted(FULL_REGION_TO_QUARTER.items(), key=lambda x: len(x[0]), reverse=True):
        if addr.startswith(full):
            return region
    for prefix, region in REGION_ADDRESS_ALIASES.items():
        if addr.startswith(prefix):
            return region
    if addr.startswith("세종 "):
        return "세종"
    return None


def load_esri_local_government_office_overrides() -> dict[str, dict]:
    path = ROOT / "data" / "processed" / "admin_center_coordinates" / "esri_local_government_offices_2025.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    src = "ESRI Korea 관공서(지방자치단체) / 행정안전부 주소 기반 지오코딩"
    overrides: dict[str, dict] = {}
    for _, r in df.iterrows():
        lat = pd.to_numeric(r.get("lat"), errors="coerce")
        lon = pd.to_numeric(r.get("lon"), errors="coerce")
        if pd.isna(lat) or pd.isna(lon):
            continue
        name = str(r.get("name", "")).strip()
        office_type = str(r.get("office_type", "")).strip()
        address = str(r.get("address", "")).strip()

        # Keep main offices only for default map movement.
        if any(token in name for token in ("북부청사", "2청사", "조치원청사")):
            continue

        q_region = region_from_address(address)
        clean_name = strip_office_name(name)
        record = {
            "lat": lat,
            "lon": lon,
            "coordinateBasis": "행정청사 좌표",
            "coordinateStatus": "admin_office_coordinate_sourced",
            "coordinateSource": src,
        }

        if office_type == "도청":
            # 도 단위만 들어 있다. 특별·광역시는 시청 레이어에서 처리.
            q = clean_name
            if q in FULL_REGION_TO_QUARTER:
                q = FULL_REGION_TO_QUARTER[q]
            elif q == "경기도":
                q = "경기도"
            if q in DISPLAY_REGION or q == "경기도":
                overrides[f"sido:{q}"] = record
            continue

        if office_type == "시청":
            if clean_name in FULL_REGION_TO_QUARTER:
                q = FULL_REGION_TO_QUARTER[clean_name]
                overrides[f"sido:{q}"] = record
                if q == "세종":
                    overrides["sigungu:세종:세종시"] = record
                continue
            if clean_name == "경기도":
                overrides["sido:경기도"] = record
                continue
            # Sejong is a single-tier metropolitan city and also has a
            # synthetic lower unit in the nationwide validation.
            if clean_name == "세종특별자치시":
                overrides["sido:세종"] = record
                overrides["sigungu:세종:세종시"] = record
                continue
            if q_region:
                overrides[f"sigungu:{q_region}:{clean_name}"] = record
            continue

        if office_type in {"구청", "군청"} and q_region and clean_name:
            overrides[f"sigungu:{q_region}:{clean_name}"] = record
            # The historical GRVA panel still contains 경북:군위군 for earlier
            # years, while the current office address is 대구광역시 군위군.
            if clean_name == "군위군":
                overrides["sigungu:경북:군위군"] = record
    return overrides


def build_province_geojson() -> dict:
    g = gpd.read_file(SIGUNGU_SHP)[["SIGUNGU_CD", "geometry"]].copy()
    g["prefix"] = g["SIGUNGU_CD"].astype(str).str[:2]
    g["quarter_region"] = g["prefix"].map(lambda x: SGIS_PREFIX_TO_REGION.get(x, (None, None))[0])
    g = g.dropna(subset=["quarter_region"]).to_crs(4326)
    province = g.dissolve("quarter_region", as_index=False)
    province["geometry"] = province.geometry.simplify(0.015, preserve_topology=True)
    province["name"] = province["quarter_region"].map(DISPLAY_REGION)
    return json.loads(province[["quarter_region", "name", "geometry"]].to_json())


def build_sigungu_geojson() -> dict:
    """Build dashboard municipality boundaries aligned to validation keys.

    The official 2025 boundary file has district-level geometries such as
    고양시 덕양구/일산동구/일산서구, while the annual GRVA panel can use an
    integrated city key such as 고양시.  For map selection, dissolve boundary
    pieces to the same `sigungu:{시도}:{시군구}` keys used in the dashboard
    metrics.
    """

    g = gpd.read_file(SIGUNGU_SHP)[["SIGUNGU_CD", "SIGUNGU_NM", "geometry"]].copy()
    g["prefix"] = g["SIGUNGU_CD"].astype(str).str[:2]
    g["quarter_region"] = g["prefix"].map(lambda x: SGIS_PREFIX_TO_REGION.get(x, (None, None))[0])
    g = g.dropna(subset=["quarter_region"]).to_crs(4326)
    annual = pd.read_csv(NATION / "annual_sigungu_gva_normalized.csv")
    keys = annual[["quarter_region", "province_full", "city"]].drop_duplicates()
    features = []
    for _, key in keys.iterrows():
        qr = key["quarter_region"]
        city = key["city"]
        candidates = g[g["quarter_region"].eq(qr)].copy()
        matched = candidates[candidates["SIGUNGU_NM"].eq(city)]
        if matched.empty:
            matched = candidates[candidates["SIGUNGU_NM"].str.startswith(city + " ", na=False)]
        if matched.empty and str(city).endswith("시"):
            matched = candidates[candidates["SIGUNGU_NM"].str.startswith(str(city), na=False)]
        if matched.empty:
            matched = candidates[candidates["SIGUNGU_NM"].str.contains(str(city), regex=False, na=False)]
        if matched.empty:
            matched = g[g["SIGUNGU_NM"].eq(city)].copy()
        if matched.empty:
            continue
        geom = matched.geometry.union_all()
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": f"sigungu:{qr}:{city}",
                    "quarter_region": qr,
                    "name": f"{DISPLAY_REGION.get(qr, qr)} {city}",
                    "shortName": city,
                    "sigungu_cd": ",".join(matched["SIGUNGU_CD"].astype(str).tolist()),
                },
                "geometry": json.loads(
                    gpd.GeoSeries([geom], crs=4326).simplify(0.006, preserve_topology=True).to_json()
                )["features"][0]["geometry"],
            }
        )
    return {"type": "FeatureCollection", "features": features}


def source_records_for_sido() -> list[dict]:
    return [
        {
            "title": "통계청·지역통계 실험적 통계: 실질 지역내총생산(잠정)",
            "role": "시도 분기 GRDP/GVA actual 및 전국 GDP 경계 검증",
            "period": "2015Q1~2026Q1 로컬 XLSX 파생, 대시보드 검증은 2021~2025",
        },
        {
            "title": "KOSIS 지역소득: 시도별 경제활동별 지역내총부가가치 및 요소소득",
            "role": "시도 업종별 연간 actual 보조·검증",
            "period": "연간",
        },
    ]


def source_records_for_sigungu(actual_rows: pd.DataFrame) -> list[dict]:
    sources = (
        actual_rows[["table_id", "table_name", "latest_change_date"]]
        .drop_duplicates()
        .sort_values(["table_name", "table_id"])
    )
    out = []
    for _, r in sources.iterrows():
        title = str(r["table_name"])
        table_id = str(r["table_id"])
        if table_id.startswith("pseudo_"):
            title = "세종 단층 하위단위 연간 벤치마크: 통계청 실험적 분기 GRDP/GVA 연간합"
        out.append(
            {
                "title": title,
                "role": "시군구 연간 GVA actual 집계검증",
                "tableId": table_id,
                "latestChangeDate": None if pd.isna(r["latest_change_date"]) else str(r["latest_change_date"]),
            }
        )
    return out


def build_sido_metrics() -> dict:
    q = pd.read_csv(NATION / "sido_quarterly_grdp_validation.csv")
    q = q[q["track"].eq(TRACK)].copy()
    annual = (
        q.groupby(["quarter_region", "year"], as_index=False)
        .agg(
            estimated_grdp_eok=("predicted_grdp_eok", "sum"),
            actual_grdp_eok=("official_grdp_eok", "sum"),
        )
    )
    annual["abs_error_eok"] = (annual["estimated_grdp_eok"] - annual["actual_grdp_eok"]).abs()
    annual["ape_pct"] = annual["abs_error_eok"] / annual["actual_grdp_eok"].abs() * 100

    act = pd.read_csv(NATION / "sido_activity_quarterly_validation.csv")
    act = act[act["track"].eq(TRACK)].copy()
    industries = (
        act.groupby(["quarter_region", "activity", "year"], as_index=False)
        .agg(estimated_gva_eok=("predicted_value_eok", "sum"), actual_gva_eok=("official_value_eok", "sum"))
    )
    industries["abs_error_eok"] = (industries["estimated_gva_eok"] - industries["actual_gva_eok"]).abs()
    industries["ape_pct"] = industries["abs_error_eok"] / industries["actual_gva_eok"].abs() * 100

    operating = pd.read_csv(NATION / "operating_point_sido_grdp_validation.csv")
    operating = operating[operating["track"].eq(TRACK)].copy()
    routed_path = NATION / "hard_region_indicator_route_rolling_gate_grdp_detail.csv"
    if routed_path.exists():
        routed = pd.read_csv(routed_path)
        routed = routed[routed["track"].eq(TRACK)].copy()
        operating = operating.merge(
            routed[
                [
                    "quarter_region",
                    "year",
                    "available_quarters",
                    "rolling_routed_annualized_predicted_grdp_eok",
                    "rolling_routed_ape_pct",
                ]
            ],
            on=["quarter_region", "year", "available_quarters"],
            how="left",
        )
    metrics = {}
    for region, g in annual.groupby("quarter_region"):
        region_id = f"sido:{region}"
        ind = industries[industries["quarter_region"].eq(region)].copy()
        op = operating[operating["quarter_region"].eq(region)].copy()
        metrics[region_id] = {
            "valueType": "sido_grdp",
            "actualSources": source_records_for_sido(),
            "total": round_records(
                g.sort_values("year")[
                    ["year", "estimated_grdp_eok", "actual_grdp_eok", "abs_error_eok", "ape_pct"]
                ],
                ["estimated_grdp_eok", "actual_grdp_eok", "abs_error_eok", "ape_pct"],
            ),
            "industries": round_records(
                ind.sort_values(["activity", "year"])[
                    ["activity", "year", "estimated_gva_eok", "actual_gva_eok", "abs_error_eok", "ape_pct"]
                ],
                ["estimated_gva_eok", "actual_gva_eok", "abs_error_eok", "ape_pct"],
            ),
            "operating": round_records(
                op.sort_values(["year", "available_quarters"])[
                    [
                        "year",
                        "available_quarters",
                        "operating_label",
                        "annualized_predicted_grdp_eok",
                        "official_annual_grdp_eok",
                        "annualized_ape_pct",
                        "rolling_routed_annualized_predicted_grdp_eok",
                        "rolling_routed_ape_pct",
                    ]
                ],
                [
                    "annualized_predicted_grdp_eok",
                    "official_annual_grdp_eok",
                    "annualized_ape_pct",
                    "rolling_routed_annualized_predicted_grdp_eok",
                    "rolling_routed_ape_pct",
                ],
            ),
        }
    return metrics


def build_sigungu_metrics() -> dict:
    pred = pd.read_csv(NATION / "sigungu_industry_quarterly_predictions.csv")
    pred = pred[pred["track"].eq(TRACK)].copy()
    annual_pred = (
        pred.groupby(["quarter_region", "province_full", "city", "activity_group", "year"], as_index=False)
        .agg(estimated_gva_eok=("predicted_gva_eok", "sum"))
    )
    total_gva = (
        annual_pred.groupby(["quarter_region", "province_full", "city", "year"], as_index=False)["estimated_gva_eok"]
        .sum()
        .rename(columns={"estimated_gva_eok": "estimated_gva_total_eok"})
    )
    npt = pd.read_csv(NATION / "sido_other_npt_quarterly_predictions.csv")
    npt = (
        npt[npt["track"].eq(TRACK)]
        .groupby(["quarter_region", "year"], as_index=False)["predicted_other_npt_eok"]
        .sum()
        .rename(columns={"predicted_other_npt_eok": "province_other_npt_eok"})
    )
    province_gva = (
        total_gva.groupby(["quarter_region", "year"], as_index=False)["estimated_gva_total_eok"]
        .sum()
        .rename(columns={"estimated_gva_total_eok": "province_estimated_gva_eok"})
    )
    total = total_gva.merge(province_gva, on=["quarter_region", "year"], how="left").merge(
        npt, on=["quarter_region", "year"], how="left"
    )
    total["allocated_other_npt_eok"] = (
        total["province_other_npt_eok"] * total["estimated_gva_total_eok"] / total["province_estimated_gva_eok"]
    )
    total["estimated_grdp_like_eok"] = total["estimated_gva_total_eok"] + total["allocated_other_npt_eok"].fillna(0)

    actual = pd.read_csv(NATION / "annual_sigungu_gva_normalized.csv")
    actual_total = (
        actual.groupby(["quarter_region", "city", "year"], as_index=False)["annual_gva_eok"]
        .sum()
        .rename(columns={"annual_gva_eok": "actual_gva_total_eok"})
    )
    total = total.merge(actual_total, on=["quarter_region", "city", "year"], how="left")
    total["gva_abs_error_eok"] = (total["estimated_gva_total_eok"] - total["actual_gva_total_eok"]).abs()
    total["gva_ape_pct"] = total["gva_abs_error_eok"] / total["actual_gva_total_eok"].abs() * 100

    actual_ind = actual.rename(columns={"activity_group": "activity", "annual_gva_eok": "actual_gva_eok"})
    annual_pred = annual_pred.rename(columns={"activity_group": "activity"})
    ind = annual_pred.merge(
        actual_ind[["quarter_region", "city", "activity", "year", "actual_gva_eok"]],
        on=["quarter_region", "city", "activity", "year"],
        how="left",
    )
    ind["abs_error_eok"] = (ind["estimated_gva_eok"] - ind["actual_gva_eok"]).abs()
    ind["ape_pct"] = ind["abs_error_eok"] / ind["actual_gva_eok"].abs() * 100

    metrics = {}
    for (region, city), g in total.groupby(["quarter_region", "city"]):
        region_id = f"sigungu:{region}:{city}"
        ig = ind[ind["quarter_region"].eq(region) & ind["city"].eq(city)].copy()
        actual_sources = source_records_for_sigungu(
            actual[(actual["quarter_region"].eq(region)) & (actual["city"].eq(city))]
        )
        metrics[region_id] = {
            "valueType": "sigungu_estimated_grdp_like_with_actual_gva",
            "actualSources": actual_sources,
            "total": round_records(
                g.sort_values("year")[
                    [
                        "year",
                        "estimated_grdp_like_eok",
                        "estimated_gva_total_eok",
                        "allocated_other_npt_eok",
                        "actual_gva_total_eok",
                        "gva_abs_error_eok",
                        "gva_ape_pct",
                    ]
                ],
                [
                    "estimated_grdp_like_eok",
                    "estimated_gva_total_eok",
                    "allocated_other_npt_eok",
                    "actual_gva_total_eok",
                    "gva_abs_error_eok",
                    "gva_ape_pct",
                ],
            ),
            "industries": round_records(
                ig.sort_values(["activity", "year"])[
                    ["activity", "year", "estimated_gva_eok", "actual_gva_eok", "abs_error_eok", "ape_pct"]
                ],
                ["estimated_gva_eok", "actual_gva_eok", "abs_error_eok", "ape_pct"],
            ),
        }
    return metrics


def build_hard_region_diagnostics() -> dict[str, list[dict]]:
    path = NATION / "hard_region_activity_diagnostics.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[(df["track"].eq(TRACK)) & (df["available_quarters"].eq(1))].copy()
    if df.empty:
        return {}
    cols = [
        "quarter_region",
        "activity",
        "annualized_official_sum_eok",
        "annualized_abs_error_sum_eok",
        "annualized_wape_pct",
        "max_annualized_ape_pct",
        "years_over_10pct",
        "cause_class",
        "needed_direct_data",
        "candidate_action",
    ]
    df = df[cols].sort_values(["quarter_region", "annualized_wape_pct"], ascending=[True, False])
    out: dict[str, list[dict]] = {}
    for region, g in df.groupby("quarter_region"):
        out[region] = round_records(
            g.head(5),
            [
                "annualized_official_sum_eok",
                "annualized_abs_error_sum_eok",
                "annualized_wape_pct",
                "max_annualized_ape_pct",
            ],
            digits=2,
        )
    return out


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    regions = build_regions()
    metrics = build_sido_metrics()
    metrics.update(build_sigungu_metrics())

    industries = sorted(
        {
            item["activity"]
            for metric in metrics.values()
            for item in metric.get("industries", [])
            if item.get("activity") and item.get("activity") != "기타산업 및 순생산물세"
        }
    )
    payload = {
        "generatedAt": "2026-07-28",
        "unit": "억원, 실질 기준",
        "track": TRACK,
        "notes": [
            "시도 total은 분기 GRDP 추정과 공식 시도 GRDP actual 비교다.",
            "시군구 total은 추정 GVA에 시도 순생산물세·기타항목을 GVA 비중으로 배분한 GRDP형 추정값이다.",
            "시군구 actual은 공개 가능한 연간 GVA actual이며, 엄밀한 GRDP actual은 아니다.",
            "활동지표 보조 추정은 어려운 5개 시도 Q1·Q1~Q2 조기점검 참고값으로만 제공한다.",
            "지도 이동 좌표는 확보된 행정청사 좌표를 우선 사용하며, 미확보 지역은 행정구역 도형 대표점으로 이동한다.",
            "청사 좌표는 인천 11개 지역은 공공데이터포털 인천 원천, 그 외 지역은 ESRI/MOIS 공개 조회 레이어를 사용한다. ESRI/MOIS 좌표의 재배포·상업적 이용 가능 범위는 원천 사용조건 확인이 필요하며, 원자료 기준일은 2016.12, 서비스 갱신 표기는 2025.02다.",
        ],
        "regions": regions,
        "industries": ["전체"] + industries,
        "metrics": metrics,
        "hardRegionDiagnostics": build_hard_region_diagnostics(),
    }
    (DATA / "dashboard_data.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DATA / "dashboard_data.js").write_text(
        "window.DASHBOARD_DATA=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    province_geojson = build_province_geojson()
    (DATA / "province_features.js").write_text(
        "window.PROVINCE_FEATURES=" + json.dumps(province_geojson, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    sigungu_geojson = build_sigungu_geojson()
    (DATA / "sigungu_features.js").write_text(
        "window.SIGUNGU_FEATURES=" + json.dumps(sigungu_geojson, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    manifest = {
        "regions": len(regions),
        "metrics": len(metrics),
        "industries": len(industries),
        "sigungu_features": len(sigungu_geojson["features"]),
        "source_outputs": [
            "nationwide/outputs/sido_quarterly_grdp_validation.csv",
            "nationwide/outputs/operating_point_sido_grdp_validation.csv",
            "nationwide/outputs/sido_activity_quarterly_validation.csv",
            "nationwide/outputs/sigungu_industry_quarterly_predictions.csv",
            "nationwide/outputs/annual_sigungu_gva_normalized.csv",
            "nationwide/outputs/sido_other_npt_quarterly_predictions.csv",
            "nationwide/outputs/hard_region_indicator_route_rolling_gate_grdp_detail.csv",
            "data/processed/admin_center_coordinates/esri_local_government_offices_2025.csv",
            "data/raw/admin_center_coordinates/incheon_facility_info_15076595.csv",
        ],
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
