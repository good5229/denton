#!/usr/bin/env python3
"""Phase51 building-register real-estate source fill.

Downloads were performed from BuildingHUB large-file service outside this
script.  This script consumes the current building-register title ZIP and
extracts only Goyang/Pohang rows, then builds free-source real-estate stock
features from total floor area and main-use categories.

Important guardrail: the building register is legal-dong/address based, not
administrative-dong-coordinate based.  We therefore expose reliable
city/gu/legal-dong features and only mark administrative-dong matching when the
current administrative-dong name is directly present in the address.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase51_building_realestate_sources"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
ZIP_PATH = RAW / "building_register_current_ttlldr_202606.zip"

TARGET_SIGUNGU = {
    "41281": ("고양시", "덕양구"),
    "41285": ("고양시", "일산동구"),
    "41287": ("고양시", "일산서구"),
    "47111": ("포항시", "남구"),
    "47113": ("포항시", "북구"),
}

FIELD_INDEX = {
    "mgm_bldrgst_pk": 0,
    "regstr_kind_nm": 4,
    "plat_plc": 5,
    "new_plat_plc": 6,
    "sigungu_cd": 8,
    "bjdong_cd": 9,
    "bun": 11,
    "ji": 12,
    "dong_nm": 22,
    "main_atch_gb_nm": 24,
    "plat_area": 25,
    "arch_area": 26,
    "bc_rat": 27,
    "tot_area": 28,
    "vl_rat_estm_tot_area": 29,
    "main_purps_cd": 34,
    "main_purps_cd_nm": 35,
    "etc_purps": 36,
    "hhld_cnt": 40,
    "fmly_cnt": 41,
    "grnd_flr_cnt": 43,
    "ugrnd_flr_cnt": 44,
    "atch_bld_cnt": 47,
    "atch_bld_area": 48,
    "tot_dong_tot_area": 49,
    "pms_day": 58,
    "stcns_day": 59,
    "use_apr_day": 60,
    "ho_cnt": 66,
    "crtn_day": 74,
}


def parse_float(value: str) -> float:
    try:
        return float(value) if value not in ("", None) else 0.0
    except ValueError:
        return 0.0


def parse_int(value: str) -> int:
    try:
        return int(float(value)) if value not in ("", None) else 0
    except ValueError:
        return 0


def normalize_day(value: str) -> str:
    value = str(value or "").strip()
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return ""


def use_group(code: str, name: str) -> str:
    code = str(code or "")
    name = str(name or "")
    if code.startswith(("01", "02")) or "주택" in name:
        return "주거"
    if code.startswith(("03", "04", "05")) or any(k in name for k in ["근린", "판매", "업무"]):
        return "상업·업무"
    if code.startswith(("17", "18", "19")) or any(k in name for k in ["공장", "창고", "위험물"]):
        return "산업·창고"
    if code.startswith(("10", "11", "12", "13", "14")) or any(k in name for k in ["교육", "의료", "복지", "수련"]):
        return "공공·사회서비스"
    if code.startswith(("06", "07", "15", "16")) or any(k in name for k in ["운수", "숙박", "위락", "관광"]):
        return "숙박·운수·여가"
    return "기타"


def load_admin_names() -> dict[str, list[str]]:
    names: dict[str, list[str]] = {"고양시": [], "포항시": []}
    goyang_boundary = ROOT / "data" / "raw" / "phase37_goyang_emd" / "goyang_top_adstrd.geojson"
    if goyang_boundary.exists():
        g = gpd.read_file(goyang_boundary)
        names["고양시"] = sorted((g["nm"].astype(str) + "동").unique(), key=len, reverse=True)
    pohang_boundary = ROOT / "data" / "raw" / "phase42_pohang" / "administrative_dong_20260401.geojson"
    if pohang_boundary.exists():
        p = gpd.read_file(pohang_boundary)
        p = p[p["sggnm"].isin(["포항시남구", "포항시북구"])]
        names["포항시"] = sorted(p["adm_nm"].astype(str).str.split().str[-1].unique(), key=len, reverse=True)
    return names


def match_admin_name(city: str, address: str, admin_names: dict[str, list[str]]) -> str:
    compact = str(address or "").replace(" ", "")
    for name in admin_names.get(city, []):
        if str(name).replace(" ", "") in compact:
            return name
    return ""


def extract_rows() -> pd.DataFrame:
    if not ZIP_PATH.exists():
        raise SystemExit(f"missing building register ZIP: {ZIP_PATH}")
    rows = []
    admin_names = load_admin_names()
    with ZipFile(ZIP_PATH) as zf:
        names = zf.namelist()
        if len(names) != 1:
            raise SystemExit(f"unexpected ZIP member count: {names[:5]}")
        with zf.open(names[0]) as handle:
            for raw_line in handle:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                parts = line.split("|")
                if len(parts) < 61:
                    continue
                sigungu = parts[FIELD_INDEX["sigungu_cd"]]
                if sigungu not in TARGET_SIGUNGU:
                    continue
                city, gu = TARGET_SIGUNGU[sigungu]
                address = parts[FIELD_INDEX["plat_plc"]]
                main_code = parts[FIELD_INDEX["main_purps_cd"]]
                main_name = parts[FIELD_INDEX["main_purps_cd_nm"]]
                rows.append(
                    {
                        "city": city,
                        "general_gu": gu,
                        "sigungu_cd": sigungu,
                        "bjdong_cd": parts[FIELD_INDEX["bjdong_cd"]],
                        "legal_dong_key": f"{sigungu}{parts[FIELD_INDEX['bjdong_cd']]}",
                        "admin_emd_name_direct": match_admin_name(city, address, admin_names),
                        "mgm_bldrgst_pk": parts[FIELD_INDEX["mgm_bldrgst_pk"]],
                        "plat_plc": address,
                        "new_plat_plc": parts[FIELD_INDEX["new_plat_plc"]],
                        "main_purps_cd": main_code,
                        "main_purps_cd_nm": main_name,
                        "use_group": use_group(main_code, main_name),
                        "tot_area": parse_float(parts[FIELD_INDEX["tot_area"]]),
                        "vl_rat_estm_tot_area": parse_float(parts[FIELD_INDEX["vl_rat_estm_tot_area"]]),
                        "plat_area": parse_float(parts[FIELD_INDEX["plat_area"]]),
                        "hhld_cnt": parse_int(parts[FIELD_INDEX["hhld_cnt"]]),
                        "fmly_cnt": parse_int(parts[FIELD_INDEX["fmly_cnt"]]),
                        "ho_cnt": parse_int(parts[FIELD_INDEX["ho_cnt"]]),
                        "use_approval_day": normalize_day(parts[FIELD_INDEX["use_apr_day"]]),
                        "created_day": normalize_day(parts[FIELD_INDEX["crtn_day"]]),
                    }
                )
    out = pd.DataFrame(rows)
    filtered_path = PROCESSED / "partial_stats_phase51_building_register_goyang_pohang_rows.csv"
    out.to_csv(filtered_path, index=False, encoding="utf-8-sig")
    return out


def aggregate_features(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_cols = ["city", "general_gu", "sigungu_cd", "bjdong_cd", "legal_dong_key", "use_group"]
    legal = (
        rows.groupby(group_cols, as_index=False)
        .agg(
            building_count=("mgm_bldrgst_pk", "count"),
            total_floor_area=("tot_area", "sum"),
            vl_floor_area=("vl_rat_estm_tot_area", "sum"),
            parcel_area=("plat_area", "sum"),
            household_count=("hhld_cnt", "sum"),
            family_count=("fmly_cnt", "sum"),
            unit_count=("ho_cnt", "sum"),
        )
        .sort_values(["city", "general_gu", "legal_dong_key", "use_group"])
    )
    gu = (
        legal.groupby(["city", "general_gu", "sigungu_cd", "use_group"], as_index=False)
        .agg(
            building_count=("building_count", "sum"),
            total_floor_area=("total_floor_area", "sum"),
            vl_floor_area=("vl_floor_area", "sum"),
            parcel_area=("parcel_area", "sum"),
            household_count=("household_count", "sum"),
            family_count=("family_count", "sum"),
            unit_count=("unit_count", "sum"),
        )
        .sort_values(["city", "general_gu", "use_group"])
    )
    admin = rows[rows["admin_emd_name_direct"].ne("")].copy()
    admin_agg = (
        admin.groupby(["city", "general_gu", "admin_emd_name_direct", "use_group"], as_index=False)
        .agg(
            building_count=("mgm_bldrgst_pk", "count"),
            total_floor_area=("tot_area", "sum"),
            vl_floor_area=("vl_rat_estm_tot_area", "sum"),
            household_count=("hhld_cnt", "sum"),
            unit_count=("ho_cnt", "sum"),
        )
        .sort_values(["city", "general_gu", "admin_emd_name_direct", "use_group"])
    )
    legal.to_csv(PROCESSED / "partial_stats_phase51_realestate_legal_dong_use_features.csv", index=False, encoding="utf-8-sig")
    gu.to_csv(PROCESSED / "partial_stats_phase51_realestate_gu_use_features.csv", index=False, encoding="utf-8-sig")
    admin_agg.to_csv(PROCESSED / "partial_stats_phase51_realestate_admin_name_direct_features.csv", index=False, encoding="utf-8-sig")
    return legal, gu, admin_agg


def write_report(rows: pd.DataFrame, legal: pd.DataFrame, gu: pd.DataFrame, admin: pd.DataFrame) -> dict:
    report_path = REPORTS / "partial_statistics_estimation_phase51_building_register_realestate.md"
    city_summary = (
        rows.groupby("city", as_index=False)
        .agg(
            building_rows=("mgm_bldrgst_pk", "count"),
            total_floor_area=("tot_area", "sum"),
            direct_admin_matched_rows=("admin_emd_name_direct", lambda s: int(s.ne("").sum())),
        )
    )
    city_summary["direct_admin_match_rate"] = city_summary["direct_admin_matched_rows"] / city_summary["building_rows"]
    gu_top = gu.sort_values("total_floor_area", ascending=False).head(12).copy()
    for col in ["vl_floor_area", "parcel_area"]:
        if col in city_summary:
            city_summary[col] = city_summary[col].map(lambda x: f"{x:,.0f}")
        if col in gu_top:
            gu_top[col] = gu_top[col].map(lambda x: f"{x:,.0f}")
    city_summary["total_floor_area"] = city_summary["total_floor_area"].map(lambda x: f"{x:,.0f}")
    gu_top["total_floor_area"] = gu_top["total_floor_area"].map(lambda x: f"{x:,.0f}")
    city_summary["direct_admin_match_rate"] = city_summary["direct_admin_match_rate"].map(lambda x: f"{x:.1%}")
    lines = [
        "# Phase51 건축물대장 기반 부동산업 보강자료",
        "",
        "## 결론",
        "",
        "- 건축HUB 대용량 서비스에서 현행 건축물대장 표제부 2026년 06월 ZIP을 다운로드했고, 고양시·포항시 행만 추출했다.",
        "- 부동산업 보강에는 건축물 수보다 용도별 연면적이 더 적합하므로, 주용도 기준으로 주거·상업업무·산업창고·공공사회서비스·숙박운수여가·기타 면적 피처를 만들었다.",
        "- 다만 원자료는 법정동/주소 기반이다. 좌표가 없으므로 행정동 직접 매칭은 주소에 현재 행정동명이 포함되는 경우로 제한했고, 나머지는 법정동·구 단위에서만 확정 사용한다.",
        "",
        "## 도시별 추출 규모",
        "",
        "| 도시 | 건축물 행 | 총 연면적 | 행정동 직접매칭 행 | 직접매칭률 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for _, r in city_summary.iterrows():
        lines.append(
            f"| {r['city']} | {r['building_rows']} | {r['total_floor_area']} | {r['direct_admin_matched_rows']} | {r['direct_admin_match_rate']} |"
        )
    lines += [
        "",
        "## 구×용도 상위 연면적",
        "",
        "| 도시 | 구 | 용도그룹 | 건축물 | 총 연면적 | 용적률산정연면적 |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for _, r in gu_top.iterrows():
        lines.append(
            f"| {r['city']} | {r['general_gu']} | {r['use_group']} | {int(r['building_count'])} | {r['total_floor_area']} | {r['vl_floor_area']} |"
        )
    lines += [
        "",
        "## 산출 파일",
        "",
        "- `data/processed/partial_stats_phase51_building_register_goyang_pohang_rows.csv`",
        "- `data/processed/partial_stats_phase51_realestate_legal_dong_use_features.csv`",
        "- `data/processed/partial_stats_phase51_realestate_gu_use_features.csv`",
        "- `data/processed/partial_stats_phase51_realestate_admin_name_direct_features.csv`",
        "- `data/processed/partial_stats_phase51_status.json`",
        "",
        "## 활용 판정",
        "",
        "- 시·구·법정동 부동산업 배분: 사용 가능.",
        "- 행정동 부동산업 배분: 직접명칭 매칭분은 보조 사용 가능, 전체 행정동 배분에는 법정동→행정동 공식 매핑 또는 좌표/공간결합 자료가 추가 필요. 현 단계에서 법정동 값을 행정동으로 강제 배분하지 않는다.",
        "- 월 변화: 표제부 stock은 월별 전체 snapshot이므로 월간 신규/변동은 건축인허가·실거래가와 결합해야 한다.",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    status = {
        "run_id": "partial_statistics_estimation_phase51_building_register_realestate",
        "source": {
            "hub_page": "https://www.hub.go.kr/portal/opn/lps/idx-lgcpt-pvsn-srvc-list.do",
            "public_data_page": "https://www.data.go.kr/data/15044720/fileData.do",
            "download_id": "OPN202607201251380890",
            "service": "건축물대장 표제부 (2026년 06월)",
            "purpose_code_used": "4 연구(논문 등)",
        },
        "city_summary": city_summary.to_dict(orient="records"),
        "outputs": [
            "data/processed/partial_stats_phase51_building_register_goyang_pohang_rows.csv",
            "data/processed/partial_stats_phase51_realestate_legal_dong_use_features.csv",
            "data/processed/partial_stats_phase51_realestate_gu_use_features.csv",
            "data/processed/partial_stats_phase51_realestate_admin_name_direct_features.csv",
            "reports/partial_statistics_estimation_phase51_building_register_realestate.md",
        ],
        "guardrail": "legal-dong features are reliable; administrative-dong features are direct-name-match only",
    }
    (PROCESSED / "partial_stats_phase51_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    rows = extract_rows()
    legal, gu, admin = aggregate_features(rows)
    status = write_report(rows, legal, gu, admin)
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
