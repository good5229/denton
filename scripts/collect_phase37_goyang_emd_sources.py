from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "phase37_goyang_emd"
OUT_DIR = ROOT / "data" / "processed"
ORG_CODE = "3940000"
POPULATION_URL = (
    "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
    "atchFileId=FILE_000000003635868&fileDetailSn=1&insertDataPrcus=N"
)


@dataclass(frozen=True)
class LocalDataSource:
    slug: str
    label: str
    sector_code: str
    sector_name: str


SOURCES = (
    LocalDataSource("general_restaurants", "일반음식점", "I00", "숙박·음식점"),
    LocalDataSource("rest_cafes", "휴게음식점", "I00", "숙박·음식점"),
    LocalDataSource("lodgings", "숙박업", "I00", "숙박·음식점"),
    LocalDataSource("tourist_accommodations", "관광숙박업", "I00", "숙박·음식점"),
    LocalDataSource("hospitals", "병원", "Q00", "보건·사회복지"),
    LocalDataSource("clinics", "의원", "Q00", "보건·사회복지"),
    LocalDataSource("pharmacies", "약국", "Q00", "보건·사회복지"),
    LocalDataSource("beauty_salons", "미용업", "S00", "개인서비스"),
    LocalDataSource("barber_shops", "이용업", "S00", "개인서비스"),
    LocalDataSource("laundries", "세탁업", "S00", "개인서비스"),
    LocalDataSource("public_baths", "목욕장업", "S00", "개인서비스"),
    LocalDataSource("fitness_centers", "체력단련장업", "R00", "예술·스포츠·여가"),
    LocalDataSource("golf_practice_ranges", "골프연습장업", "R00", "예술·스포츠·여가"),
    LocalDataSource("billiard_halls", "당구장업", "R00", "예술·스포츠·여가"),
    LocalDataSource("martial_arts_dojo", "체육도장업", "R00", "예술·스포츠·여가"),
    LocalDataSource("pc_bangs", "인터넷컴퓨터게임시설제공업", "R00", "예술·스포츠·여가"),
    LocalDataSource("performance_halls", "공연장", "R00", "예술·스포츠·여가"),
    LocalDataSource("museums_and_art_galleries", "박물관·미술관", "R00", "예술·스포츠·여가"),
    LocalDataSource("large_scale_retail_stores", "대규모점포", "G00", "도소매"),
)
GOYANG_LAYERS = {
    "LYR0031": "체육시설현황",
    "LYR0044": "병의원현황",
    "LYR0061": "교습소",
    "LYR0062": "학원",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, path: Path, referrer: str, post_data: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        return
    command = ["curl", "-sS", "-L", "-A", "Mozilla/5.0", "-e", referrer]
    if post_data is not None:
        command.extend(["-X", "POST", "-d", post_data])
    command.extend([url, "-o", str(path)])
    subprocess.run(command, check=True)


def collect_raw() -> None:
    download(
        "https://www.goyang.go.kr/bigdata/lvlhmap/getFeature.json",
        RAW_DIR / "goyang_top_adstrd.geojson",
        "https://www.goyang.go.kr/bigdata/lvlhmap/map.do",
        "layerId=goyang_top_adstrd&lyrId=goyang_top_adstrd",
    )
    download(
        "https://www.goyang.go.kr/bigdata/lvlhmap/selectLayerList.json",
        RAW_DIR / "goyang_life_map_layer_catalog.json",
        "https://www.goyang.go.kr/bigdata/lvlhmap/map.do",
        "",
    )
    for layer_id, title in GOYANG_LAYERS.items():
        download(
            "https://www.goyang.go.kr/bigdata/lvlhmap/getFeatureFile.do",
            RAW_DIR / f"goyang_layer_{layer_id}.csv",
            "https://www.goyang.go.kr/bigdata/lvlhmap/map.do",
            f"lyrId={layer_id}&lyrTit={title}",
        )
    download(
        POPULATION_URL,
        RAW_DIR / "goyang_resident_population_2024.csv",
        "https://www.data.go.kr/data/3070908/fileData.do",
    )
    for source in SOURCES:
        download(
            f"https://file.localdata.go.kr/file/download/{source.slug}/info?orgCode={ORG_CODE}",
            RAW_DIR / f"localdata_{source.slug}_goyang.csv",
            f"https://file.localdata.go.kr/file/{source.slug}/info",
        )


def load_boundaries() -> gpd.GeoDataFrame:
    # The service returns EPSG:5179 coordinates, but its non-standard GeoJSON
    # CRS object is interpreted as EPSG:4326 by GDAL. Override from the
    # service metadata before transforming to LOCALDATA's documented 5174.
    boundaries = (
        gpd.read_file(RAW_DIR / "goyang_top_adstrd.geojson")
        .set_crs("EPSG:5179", allow_override=True)
        .to_crs("EPSG:5174")
    )
    boundaries = boundaries.rename(columns={"cd": "emd_code", "nm": "emd_name"})
    boundaries["emd_name"] = boundaries["emd_name"].astype(str) + "동"
    boundaries["general_gu"] = boundaries["emd_code"].astype(str).str[:5].map(
        {"41281": "덕양구", "41285": "일산동구", "41287": "일산서구"}
    )
    return boundaries[["emd_code", "emd_name", "general_gu", "geometry"]]


def attach_population(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    population = pd.read_csv(RAW_DIR / "goyang_resident_population_2024.csv", encoding="utf-8-sig")
    population.columns = [str(column).replace(" ", "") for column in population.columns]
    population["emd_name"] = population["구분"].astype(str).str.replace(" ", "", regex=False)
    population["population_2024"] = pd.to_numeric(population["남자"], errors="coerce") + pd.to_numeric(
        population["여자"], errors="coerce"
    )
    population["households_2024"] = pd.to_numeric(population["세대수"], errors="coerce")
    output = boundaries.drop(columns="geometry").merge(
        population[["emd_name", "population_2024", "households_2024"]], on="emd_name", how="left", validate="one_to_one"
    )
    if output["population_2024"].isna().any():
        missing = output.loc[output["population_2024"].isna(), "emd_name"].tolist()
        raise RuntimeError(f"population did not match current administrative dongs: {missing}")
    return output


def education_snapshot(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    records = []
    audits = []
    specs = (
        ("LYR0061", "학습소명", "학습소주소", "tutoring_center_count"),
        ("LYR0062", "학원명", "주소", "academy_count"),
    )
    for layer_id, name_col, address_col, metric in specs:
        frame = pd.read_csv(RAW_DIR / f"goyang_layer_{layer_id}.csv", encoding="cp949", low_memory=False, dtype=str)
        frame["emd_code"] = frame["행정동코드"].str.strip().where(frame["행정동코드"].str.fullmatch(r"\d{8,10}"))
        frame["has_emd_code"] = frame["emd_code"].notna()
        deduped = frame.sort_values("has_emd_code", ascending=False).drop_duplicates([name_col, address_col])
        counts = deduped[deduped["emd_code"].notna()].groupby("emd_code").size()
        audits.append(
            {
                "layer_id": layer_id,
                "metric": metric,
                "reference_period": str(frame["기준년월"].dropna().iloc[0]),
                "raw_course_rows": len(frame),
                "deduplicated_facilities": len(deduped),
                "facilities_with_emd_code": int(deduped["emd_code"].notna().sum()),
                "emd_code_coverage_rate": float(deduped["emd_code"].notna().mean()),
                "raw_sha256": sha256(RAW_DIR / f"goyang_layer_{layer_id}.csv"),
            }
        )
        for code, value in counts.items():
            records.append({"emd_code": code, "metric": metric, "value": int(value)})
    wide = pd.DataFrame(records).pivot_table(index="emd_code", columns="metric", values="value", aggfunc="sum", fill_value=0).reset_index()
    output = boundaries.drop(columns="geometry").merge(wide, on="emd_code", how="left")
    for metric in ("tutoring_center_count", "academy_count"):
        output[metric] = output[metric].fillna(0).astype(int)
    output["education_facility_count"] = output["tutoring_center_count"] + output["academy_count"]
    output["reference_period"] = "2026-06"
    output["caveat"] = "강좌 행을 기관명·주소로 중복 제거; 행정동코드가 있는 기관만 집계"
    pd.DataFrame(audits).to_csv(OUT_DIR / "partial_stats_phase37_goyang_education_audit.csv", index=False)
    return output


def find_column(frame: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    normalized = {str(col).strip(): col for col in frame.columns}
    for name in names:
        if name in normalized:
            return normalized[name]
    return None


def load_and_geocode(source: LocalDataSource, boundaries: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    path = RAW_DIR / f"localdata_{source.slug}_goyang.csv"
    frame = pd.read_csv(path, encoding="cp949", low_memory=False)
    x_col = find_column(frame, ("좌표정보(X)", "좌표정보x", "좌표정보(X좌표)"))
    y_col = find_column(frame, ("좌표정보(Y)", "좌표정보y", "좌표정보(Y좌표)"))
    permit_col = find_column(frame, ("인허가일자", "개설일자", "신고일자"))
    close_col = find_column(frame, ("폐업일자", "휴업종료일자"))
    status_col = find_column(frame, ("영업상태명", "상세영업상태명"))
    if not x_col or not y_col or not permit_col:
        raise ValueError(f"{source.slug}: required coordinate/date columns are absent")

    work = pd.DataFrame(
        {
            "license_id": frame[find_column(frame, ("관리번호",))].astype(str),
            "permit_date": pd.to_datetime(frame[permit_col], errors="coerce"),
            "close_date": pd.to_datetime(frame[close_col], errors="coerce") if close_col else pd.NaT,
            "status": frame[status_col].astype(str) if status_col else "",
            "x": pd.to_numeric(frame[x_col], errors="coerce"),
            "y": pd.to_numeric(frame[y_col], errors="coerce"),
        }
    )
    work["source_slug"] = source.slug
    work["source_label"] = source.label
    work["sector_code"] = source.sector_code
    work["sector_name"] = source.sector_name
    valid_xy = work["x"].notna() & work["y"].notna() & work["x"].between(100_000, 300_000) & work["y"].between(300_000, 700_000)
    points = gpd.GeoDataFrame(
        work.loc[valid_xy].copy(),
        geometry=gpd.points_from_xy(work.loc[valid_xy, "x"], work.loc[valid_xy, "y"]),
        crs="EPSG:5174",
    )
    joined = gpd.sjoin(points, boundaries, how="left", predicate="within").drop(columns=["geometry", "index_right"])
    audit = {
        "source_slug": source.slug,
        "source_label": source.label,
        "sector_code": source.sector_code,
        "raw_rows": len(frame),
        "valid_permit_date_rows": int(work["permit_date"].notna().sum()),
        "valid_coordinate_rows": int(valid_xy.sum()),
        "matched_emd_rows": int(joined["emd_code"].notna().sum()),
        "coordinate_match_rate": float(joined["emd_code"].notna().sum() / len(frame)) if len(frame) else 0.0,
        "min_permit_date": work["permit_date"].min(),
        "max_permit_date": work["permit_date"].max(),
        "max_close_date": work["close_date"].max(),
        "raw_sha256": sha256(path),
    }
    return joined[joined["emd_code"].notna()].copy(), audit


def build_monthly(events: pd.DataFrame, boundaries: gpd.GeoDataFrame, start: str, end: str) -> pd.DataFrame:
    months = pd.period_range(start, end, freq="M")
    sectors = pd.DataFrame(
        sorted({(s.sector_code, s.sector_name) for s in SOURCES}), columns=["sector_code", "sector_name"]
    )
    grid = (
        boundaries.drop(columns="geometry")
        .merge(sectors, how="cross")
        .merge(pd.DataFrame({"period": months}), how="cross")
    )
    rows: list[dict[str, object]] = []
    grouped = events.groupby(["emd_code", "sector_code"], observed=True)
    for (emd_code, sector_code), group in grouped:
        permits = group["permit_date"].dropna().dt.to_period("M")
        closes = group["close_date"].dropna().dt.to_period("M")
        for period in months:
            month_end = period.to_timestamp(how="end")
            active = (group["permit_date"].notna() & (group["permit_date"] <= month_end)) & (
                group["close_date"].isna() | (group["close_date"] > month_end)
            )
            rows.append(
                {
                    "emd_code": emd_code,
                    "sector_code": sector_code,
                    "period": period,
                    "active_license_stock": int(active.sum()),
                    "license_openings": int((permits == period).sum()),
                    "license_closures": int((closes == period).sum()),
                }
            )
    metrics = pd.DataFrame(rows)
    panel = grid.merge(metrics, on=["emd_code", "sector_code", "period"], how="left")
    for col in ("active_license_stock", "license_openings", "license_closures"):
        panel[col] = panel[col].fillna(0).astype(int)
    panel["net_license_change"] = panel["license_openings"] - panel["license_closures"]
    panel["period"] = panel["period"].astype(str)
    panel["proxy_scope"] = "LOCALDATA 인허가 19종; 전체 사업체가 아님"
    return panel.sort_values(["emd_code", "sector_code", "period"])


def write_manifest(paths: list[Path]) -> None:
    rows = []
    for path in paths:
        rows.append(
            {
                "file": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "partial_stats_phase37_goyang_source_manifest.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--start", default="2021-01")
    parser.add_argument("--end", default="2026-06")
    args = parser.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.skip_download:
        collect_raw()

    boundaries = load_boundaries()
    current_emd = attach_population(boundaries)
    education = education_snapshot(boundaries)
    all_events: list[pd.DataFrame] = []
    audits: list[dict[str, object]] = []
    for source in SOURCES:
        events, audit = load_and_geocode(source, boundaries)
        all_events.append(events)
        audits.append(audit)
    combined = pd.concat(all_events, ignore_index=True)
    panel = build_monthly(combined, boundaries, args.start, args.end)

    current_emd.sort_values("emd_code").to_csv(
        OUT_DIR / "partial_stats_phase37_goyang_emd_current.csv", index=False
    )
    education.sort_values("emd_code").to_csv(
        OUT_DIR / "partial_stats_phase37_goyang_emd_education_snapshot.csv", index=False
    )
    pd.DataFrame(audits).to_csv(OUT_DIR / "partial_stats_phase37_goyang_source_audit.csv", index=False)
    panel.to_csv(OUT_DIR / "partial_stats_phase37_goyang_emd_industry_monthly_proxy.csv", index=False)
    raw_paths = [RAW_DIR / "goyang_top_adstrd.geojson", RAW_DIR / "goyang_resident_population_2024.csv"] + [
        RAW_DIR / f"localdata_{source.slug}_goyang.csv" for source in SOURCES
    ] + [RAW_DIR / "goyang_life_map_layer_catalog.json"] + [
        RAW_DIR / f"goyang_layer_{layer_id}.csv" for layer_id in GOYANG_LAYERS
    ]
    raw_paths.extend(
        path for path in (RAW_DIR / "kosis_620_catalog.json", RAW_DIR / "kosis_DT_1D00006_2021_2023.json") if path.exists()
    )
    write_manifest(raw_paths)
    print(f"current administrative dongs: {len(boundaries)}")
    print(f"geocoded license records: {len(combined)}")
    print(f"monthly panel rows: {len(panel)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
