from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import io
import zipfile
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
BUSINESS_SURVEY_URLS = {
    2023: "https://bis.pohang.go.kr/common/file/download.do?atchFileId=4663FF60AFA3E9E9803E337E874FCA84DB013F1E906B46BF35FD3F9E6F7A5EC3&fileSn=125EB0AE64ED2AE7001CFD6CFA9E31E8",
    2024: "https://bis.pohang.go.kr/common/file/download.do?atchFileId=6818B1CDC6C9C961A2FB89E6903398DF5CBCB79047C851DF6EB74DB5B4FD7864&fileSn=125EB0AE64ED2AE7001CFD6CFA9E31E8",
}


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
    for year, url in BUSINESS_SURVEY_URLS.items():
        download(url, RAW_DIR / f"pohang_business_survey_{year}.zip", "https://bis.pohang.go.kr/portal/board/post/list.do?bcIdx=581&mid=0403010000")
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


def business_survey_actuals() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for year in (2024,):
        with zipfile.ZipFile(RAW_DIR / f"pohang_business_survey_{year}.zip") as archive:
            targets = [name for name in archive.namelist() if "/10-" in name and ("남구" in name or "북구" in name)]
            if len(targets) != 2:
                raise RuntimeError(f"{year}: expected South/North gu table 10 files, found {targets}")
            for name in targets:
                gu = "남구" if "남구" in name else "북구"
                frame = pd.read_excel(io.BytesIO(archive.read(name)), header=None)
                for raw in frame.iloc[4:].itertuples(index=False, name=None):
                    section = str(raw[1]).strip() if pd.notna(raw[1]) else ""
                    division = str(raw[2]).strip() if pd.notna(raw[2]) else ""
                    if not (len(section) == 1 and section.isalpha() and len(division) == 2 and division.isdigit()):
                        continue
                    values = [pd.to_numeric(str(raw[i]).replace(",", ""), errors="coerce") for i in (8, 10, 12)]
                    rows.append({
                        "year": year, "general_gu": gu, "section_code": section,
                        "division_code": division, "division_name": str(raw[6]).strip(),
                        "establishments": values[0], "employees": values[1], "sales": values[2],
                        "source": f"포항시 {year}년 기준 사업체조사 통계표 10-{2 if gu == '남구' else 3}",
                    })
    out = pd.DataFrame(rows)
    if out.duplicated(["year", "general_gu", "division_code"]).any():
        raise RuntimeError("duplicate gu×division actual cells")
    return out


def decoded_zip_name(name: str) -> str:
    try:
        return name.encode("cp437").decode("cp949")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name


def business_survey_emd_actuals() -> pd.DataFrame:
    """Parse repeated print-page blocks in the 2023 gu workbooks into EMD×KSIC-middle actuals."""
    records: list[dict[str, object]] = []
    with zipfile.ZipFile(RAW_DIR / "pohang_business_survey_2023.zip") as archive:
        targets = [(name, decoded_zip_name(name)) for name in archive.namelist()]
        targets = [(raw, decoded) for raw, decoded in targets if decoded.startswith("2.")]
        if len(targets) != 2:
            raise RuntimeError(f"2023: expected two EMD×industry table-2 files, found {[x[1] for x in targets]}")
        for raw_name, decoded in targets:
            gu = "남구" if "남구" in decoded else "북구"
            frame = pd.read_excel(io.BytesIO(archive.read(raw_name)), header=None)
            header_rows = [i for i in frame.index if str(frame.iat[i, 0]).startswith("산업분류")]
            for block_index, header_row in enumerate(header_rows):
                metric_row = header_row + 1
                end_row = header_rows[block_index + 1] if block_index + 1 < len(header_rows) else len(frame)
                names: list[tuple[int, str]] = []
                for col in range(4, frame.shape[1]):
                    value = frame.iat[header_row, col]
                    if pd.notna(value) and str(value).strip():
                        names.append((col, str(value).strip()))
                for col in range(4, frame.shape[1]):
                    metric_value = frame.iat[metric_row, col]
                    metric_text = str(metric_value) if pd.notna(metric_value) else ""
                    metric = "establishments" if "사업체수" in metric_text else ("employees" if "종사자수" in metric_text else None)
                    if metric is None:
                        continue
                    prior_names = [(position, name) for position, name in names if position <= col]
                    if not prior_names:
                        continue
                    emd_name = prior_names[-1][1]
                    if emd_name in {"남구", "북구"}:
                        continue
                    for row_index in range(metric_row + 1, end_row):
                        division_raw = frame.iat[row_index, 1]
                        division = str(division_raw).strip().replace(".0", "") if pd.notna(division_raw) else ""
                        if not (len(division) == 2 and division.isdigit()):
                            continue
                        raw_value = frame.iat[row_index, col]
                        value = pd.to_numeric(str(raw_value).replace(",", ""), errors="coerce")
                        if pd.notna(value):
                            records.append({"year": 2023, "general_gu": gu, "emd_name": emd_name, "division_code": division, "metric": metric, "value": value})
    long = pd.DataFrame(records)
    # Page boundaries may repeat the last EMD metric; exact duplicates are benign, conflicting duplicates are not.
    conflict = long.groupby(["year", "general_gu", "emd_name", "division_code", "metric"]).value.nunique()
    if (conflict > 1).any():
        raise RuntimeError(f"conflicting repeated EMD actual cells: {conflict[conflict > 1].head().to_dict()}")
    long = long.drop_duplicates(["year", "general_gu", "emd_name", "division_code", "metric"])
    out = long.pivot(index=["year", "general_gu", "emd_name", "division_code"], columns="metric", values="value").reset_index()
    return out


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
    business_actuals = business_survey_actuals(); emd_actuals = business_survey_emd_actuals()
    events, audits = [], [factory_audit]
    for source in SOURCES:
        found, audit = localdata_events(source, boundary); events.append(found); audits.append(audit)
    combined = pd.concat(events, ignore_index=True)
    boundary.drop(columns="geometry").to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_registry.csv", index=False)
    population.to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_population.csv", index=False)
    factory.to_csv(OUT_DIR / "partial_stats_phase42_pohang_factory_snapshot.csv", index=False)
    business_actuals.to_csv(OUT_DIR / "partial_stats_phase42_pohang_gu_industry_actual.csv", index=False)
    emd_actuals.to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_industry_actual.csv", index=False)
    pd.DataFrame(audits).to_csv(OUT_DIR / "partial_stats_phase42_pohang_source_audit.csv", index=False)
    monthly_panel(combined, boundary, args.start, args.end).to_csv(OUT_DIR / "partial_stats_phase42_pohang_emd_monthly_proxy.csv", index=False)
    paths = [RAW_DIR / "administrative_dong_20260401.geojson", RAW_DIR / "pohang_factory_20250813.csv", RAW_DIR / "pohang_population_20260323.csv"] + [RAW_DIR / f"pohang_business_survey_{year}.zip" for year in BUSINESS_SURVEY_URLS] + [RAW_DIR / f"localdata_{s.slug}_pohang.csv" for s in SOURCES]
    write_manifest(paths)
    print(f"emd=29 localdata_geocoded={len(combined)} factory_match={factory_audit['match_rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
