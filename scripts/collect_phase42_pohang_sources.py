from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd

from kosis_common import PROCESSED_DIR, RAW_DIR as KOSIS_RAW_DIR, get_kosis_key, kosis_data, normalize_kosis_rows, write_csv, write_json


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "phase42_pohang"
OUT_DIR = ROOT / "data" / "processed"
KOSIS_TABLE = "DT_1KI1510_10"
KOSIS_REGION = "37010"
LOCALDATA_ORG = "5020000"
BOUNDARY_URL = "https://raw.githubusercontent.com/vuski/admdongkor/master/ver20260401/HangJeongDong_ver20260401.geojson"
FACTORY_URL = (
    "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
    "atchFileId=FILE_000000003225099&fileDetailSn=1&insertDataPrcus=N"
)
POPULATION_URL = (
    "https://www.data.go.kr/cmm/cmm/fileDownload.do?"
    "atchFileId=FILE_000000003615178&fileDetailSn=1&insertDataPrcus=N"
)


@dataclass(frozen=True)
class LocalDataSource:
    slug: str
    label: str
    sector_code: str


SOURCES = (
    LocalDataSource("general_restaurants", "일반음식점", "I00"),
    LocalDataSource("rest_cafes", "휴게음식점", "I00"),
    LocalDataSource("lodgings", "숙박업", "I00"),
    LocalDataSource("tourist_accommodations", "관광숙박업", "I00"),
    LocalDataSource("hospitals", "병원", "Q00"),
    LocalDataSource("clinics", "의원", "Q00"),
    LocalDataSource("pharmacies", "약국", "Q00"),
    LocalDataSource("beauty_salons", "미용업", "S00"),
    LocalDataSource("barber_shops", "이용업", "S00"),
    LocalDataSource("laundries", "세탁업", "S00"),
    LocalDataSource("public_baths", "목욕장업", "S00"),
    LocalDataSource("fitness_centers", "체력단련장업", "R00"),
    LocalDataSource("golf_practice_ranges", "골프연습장업", "R00"),
    LocalDataSource("billiard_halls", "당구장업", "R00"),
    LocalDataSource("martial_arts_dojo", "체육도장업", "R00"),
    LocalDataSource("pc_bangs", "인터넷컴퓨터게임시설제공업", "R00"),
    LocalDataSource("performance_halls", "공연장", "R00"),
    LocalDataSource("museums_and_art_galleries", "박물관·미술관", "R00"),
    LocalDataSource("large_scale_retail_stores", "대규모점포", "G00"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, path: Path, referrer: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        return
    command = ["curl", "-sS", "-L", "-A", "Mozilla/5.0"]
    if referrer:
        command.extend(["-e", referrer])
    command.extend([url, "-o", str(path)])
    subprocess.run(command, check=True)


def collect_downloads() -> None:
    download(BOUNDARY_URL, RAW_DIR / "administrative_dong_20260401.geojson")
    download(FACTORY_URL, RAW_DIR / "pohang_factory_20250813.csv", "https://www.data.go.kr/data/15100100/fileData.do")
    download(POPULATION_URL, RAW_DIR / "pohang_population_20260323.csv", "https://www.data.go.kr/data/15048474/fileData.do")
    for source in SOURCES:
        download(
            f"https://file.localdata.go.kr/file/download/{source.slug}/info?orgCode={LOCALDATA_ORG}",
            RAW_DIR / f"localdata_{source.slug}_pohang.csv",
            f"https://file.localdata.go.kr/file/{source.slug}/info",
        )


def collect_kosis() -> None:
    rows_out: list[dict[str, object]] = []
    raw: dict[str, object] = {}
    for item_id, metric in (("T10", "establishments"), ("T20", "employees"), ("T30", "sales")):
        rows = kosis_data(
            api_key=get_kosis_key(), org_id="101", tbl_id=KOSIS_TABLE, item_id=item_id,
            period="F", start="2015", end="2015", obj={1: "ALL", 2: KOSIS_REGION},
        )
        raw[item_id] = rows
        for row in normalize_kosis_rows(rows, "phase42_pohang_2015_all_ksic"):
            row["metric"] = metric
            rows_out.append(row)
    write_json(KOSIS_RAW_DIR / "phase42_pohang_2015_all_ksic.json", raw)
    write_csv(PROCESSED_DIR / "partial_stats_phase42_pohang_2015_all_ksic.csv", rows_out)


def boundaries() -> gpd.GeoDataFrame:
    frame = gpd.read_file(RAW_DIR / "administrative_dong_20260401.geojson")
    frame = frame[frame["sggnm"].isin(["포항시남구", "포항시북구"])].copy()
    frame["emd_code"] = frame["adm_cd"].astype(str)
    frame["emd_code10"] = frame["adm_cd2"].astype(str)
    frame["emd_name"] = frame["adm_nm"].str.split().str[-1]
    frame["general_gu"] = frame["sggnm"].map({"포항시남구": "남구", "포항시북구": "북구"})
    if len(frame) != 29 or frame.emd_code.nunique() != 29:
        raise RuntimeError(f"expected 29 current Pohang administrative eup/myeon/dong, found {len(frame)}")
    return frame[["emd_code", "emd_code10", "emd_name", "general_gu", "geometry"]]


def population_snapshot(boundary: gpd.GeoDataFrame) -> pd.DataFrame:
    raw = pd.read_csv(RAW_DIR / "pohang_population_20260323.csv", encoding="cp949")
    raw.columns = [str(c).strip() for c in raw.columns]
    name_col = next(c for c in raw if "읍면동" in c or c in {"구분", "지역", "행정기관"})
    raw["emd_name"] = raw[name_col].astype(str).str.replace(" ", "", regex=False)
    numeric = {}
    for label, needles in {"population": ("인구수", "총인구", "계"), "households": ("세대수",)}.items():
        choices = [c for c in raw if any(n in c for n in needles)]
        if choices:
            numeric[label] = pd.to_numeric(raw[choices[0]].astype(str).str.replace(",", "", regex=False), errors="coerce")
    for key, values in numeric.items():
        raw[key] = values
    keep = ["emd_name"] + list(numeric)
    out = boundary.drop(columns="geometry").merge(raw[keep], on="emd_name", how="left")
    out["reference_date"] = "2026-03-23"
    return out


def factory_snapshot(boundary: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    frame = pd.read_csv(RAW_DIR / "pohang_factory_20250813.csv", encoding="cp949")
    lookup = sorted(boundary.emd_name.unique(), key=len, reverse=True)
    frame["emd_name"] = frame["공장소재지주소"].fillna("").map(lambda x: next((name for name in lookup if name in x), None))
    # Addresses in urban legal dongs do not always equal administrative-dong names; retain them as unmatched, never force allocation.
    out = frame.merge(boundary.drop(columns="geometry"), on="emd_name", how="left")
    audit = {
        "source": "포항시 공장등록현황",
        "raw_rows": len(frame),
        "matched_emd_rows": int(out.emd_code.notna().sum()),
        "match_rate": float(out.emd_code.notna().mean()),
        "rule": "address contains current administrative eup/myeon/dong name; unmatched legal-dong addresses are not forced",
    }
    return out, audit


def find_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    normalized = {str(c).strip(): c for c in frame.columns}
    return next((normalized[c] for c in candidates if c in normalized), None)


def localdata_events(source: LocalDataSource, boundary: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    path = RAW_DIR / f"localdata_{source.slug}_pohang.csv"
    frame = pd.read_csv(path, encoding="cp949", low_memory=False)
    x_col = find_column(frame, ("좌표정보(X)", "좌표정보x")); y_col = find_column(frame, ("좌표정보(Y)", "좌표정보y"))
    permit_col = find_column(frame, ("인허가일자", "개설일자", "신고일자")); close_col = find_column(frame, ("폐업일자", "휴업종료일자"))
    if not x_col or not y_col or not permit_col:
        raise RuntimeError(f"{source.slug}: coordinate/date columns absent")
    work = pd.DataFrame({
        "license_id": frame[find_column(frame, ("관리번호",))].astype(str),
        "permit_date": pd.to_datetime(frame[permit_col], errors="coerce"),
        "close_date": pd.to_datetime(frame[close_col], errors="coerce") if close_col else pd.NaT,
        "x": pd.to_numeric(frame[x_col], errors="coerce"), "y": pd.to_numeric(frame[y_col], errors="coerce"),
    })
    valid = work.x.between(100_000, 600_000) & work.y.between(100_000, 700_000)
    points = gpd.GeoDataFrame(work[valid].copy(), geometry=gpd.points_from_xy(work.loc[valid, "x"], work.loc[valid, "y"]), crs="EPSG:5174")
    joined = gpd.sjoin(points, boundary.to_crs("EPSG:5174"), how="left", predicate="within").drop(columns=["geometry", "index_right"])
    joined["source_slug"] = source.slug; joined["source_label"] = source.label; joined["sector_code"] = source.sector_code
    audit = {"source": source.label, "raw_rows": len(frame), "valid_coordinate_rows": int(valid.sum()), "matched_emd_rows": int(joined.emd_code.notna().sum()), "match_rate": float(joined.emd_code.notna().sum()/len(frame)) if len(frame) else 0.0}
    return joined[joined.emd_code.notna()].copy(), audit


def monthly_panel(events: pd.DataFrame, boundary: gpd.GeoDataFrame, start: str, end: str) -> pd.DataFrame:
    months = pd.period_range(start, end, freq="M")
    sectors = pd.DataFrame({"sector_code": sorted({s.sector_code for s in SOURCES})})
    grid = boundary.drop(columns="geometry").merge(sectors, how="cross").merge(pd.DataFrame({"period": months}), how="cross")
    rows = []
    for (emd_code, sector), group in events.groupby(["emd_code", "sector_code"]):
        permits = group.permit_date.dt.to_period("M"); closes = group.close_date.dt.to_period("M")
        for period in months:
            end_at = period.to_timestamp(how="end")
            active = (group.permit_date <= end_at) & (group.close_date.isna() | (group.close_date > end_at))
            rows.append({"emd_code": emd_code, "sector_code": sector, "period": period, "active_license_stock": int(active.sum()), "openings": int((permits == period).sum()), "closures": int((closes == period).sum())})
    measures = pd.DataFrame(rows)
    out = grid.merge(measures, on=["emd_code", "sector_code", "period"], how="left")
    for col in ("active_license_stock", "openings", "closures"):
        out[col] = out[col].fillna(0).astype(int)
    out["period"] = out.period.astype(str)
    out["net_change"] = out.openings - out.closures
    out["scope_caveat"] = "LOCALDATA 19 selected license categories, not all establishments"
    return out


def write_manifest(paths: list[Path]) -> None:
    pd.DataFrame([{"file": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in paths]).to_csv(OUT_DIR / "partial_stats_phase42_pohang_source_manifest.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--start", default="2021-01"); parser.add_argument("--end", default="2026-06")
    args = parser.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True); OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.skip_download:
        collect_downloads(); collect_kosis()
    boundary = boundaries(); population = population_snapshot(boundary); factory, factory_audit = factory_snapshot(boundary)
    events, audits = [], [factory_audit]
    for source in SOURCES:
        found, audit = localdata_events(source, boundary); events.append(found); audits.append(audit)
    combined = pd.concat(events, ignore_index=True)
    boundary.drop(columns="geometry").to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_registry.csv", index=False)
    population.to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_population.csv", index=False)
    factory.to_csv(OUT_DIR / "partial_stats_phase42_pohang_factory_snapshot.csv", index=False)
    pd.DataFrame(audits).to_csv(OUT_DIR / "partial_stats_phase42_pohang_source_audit.csv", index=False)
    monthly_panel(combined, boundary, args.start, args.end).to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_monthly_proxy.csv", index=False)
    paths = [RAW_DIR / "administrative_dong_20260401.geojson", RAW_DIR / "pohang_factory_20250813.csv", RAW_DIR / "pohang_population_20260323.csv"] + [RAW_DIR / f"localdata_{s.slug}_pohang.csv" for s in SOURCES]
    write_manifest(paths)
    print(f"emd=29 localdata_geocoded={len(combined)} factory_match={factory_audit['match_rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
