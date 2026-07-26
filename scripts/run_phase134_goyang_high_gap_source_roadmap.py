#!/usr/bin/env python3
"""Phase134: Goyang high-amount-gap source roadmap.

Phase133 showed that the current candidate packages should not be adopted just
because they slightly reduce retrospective error.  This phase turns that result
into a concrete data roadmap for Goyang's largest remaining absolute GVA gaps:

* quantify the high-gap middle industries in KRW 100M and error contribution;
* measure already-collected direct activity coverage from COMWEL and LOCALDATA;
* separate sources usable for precision refinement from sources requiring API
  keys or publication-calendar confirmation for strict flash use.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
OUT = DATA / "phase134_goyang_high_gap_source_roadmap"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase134_goyang_high_gap_source_roadmap.md"

PHASE133 = DATA / "phase133_goyang_amount_weighted_refinement" / "phase133_guarded_amount_route_registry.csv"
COMWEL = DATA / "phase121_direct_activity_sources" / "phase121_comwel_workplaces_goyang_pohang_filtered.csv"
CATALOG = DATA / "phase112_goyang_openapi_probe" / "goyang_dataset_catalog.csv"
LOCALDATA_RAW = RAW / "phase37_goyang_emd"

TARGET_CODES = {
    ("ERS", "91"): {
        "focus": "스포츠·오락 서비스업",
        "direct_need": "이용객·매출·회원권·시설가동률",
        "comwel_prefixes": ["911", "912"],
        "localdata_slugs": [
            "fitness_centers",
            "golf_practice_ranges",
            "billiard_halls",
            "martial_arts_dojo",
            "pc_bangs",
        ],
        "candidate_sources": [
            "고양시 체육시설현황/LOCALDATA 체육시설업",
            "KOPIS 지역별 공연 관객·매출",
            "생활체육/공공체육시설 이용실적",
        ],
        "api_key_needed": "KOPIS_API_KEY(공연 관객·매출 사용 시)",
    },
    ("J00", "60"): {
        "focus": "방송업",
        "direct_need": "방송사업자 매출·종사자·사업장, 지역 방송·제작 활동",
        "comwel_prefixes": ["601", "602"],
        "localdata_slugs": [],
        "candidate_sources": [
            "고용보험 사업장 세부업종 601/602",
            "방송통신위원회/과기정통부 방송산업 실태조사",
            "고양시 영상·미디어 기업 지원사업/입주기업 자료",
        ],
        "api_key_needed": "없음 또는 원자료 수동수집 확인",
    },
    ("J00", "59"): {
        "focus": "영상·오디오 제작업",
        "direct_need": "영화·비디오 제작 사업장, 촬영·제작지원, 영화관 관객·매출",
        "comwel_prefixes": ["591", "592"],
        "localdata_slugs": ["performance_halls"],
        "candidate_sources": [
            "고용보험 사업장 세부업종 591/592",
            "KOBIS 영화관입장권 지역별 관객·매출",
            "고양시 영화상영관/공연장 인허가",
        ],
        "api_key_needed": "KOBIS_API_KEY(영화 관객·매출 사용 시)",
    },
    ("C00", "14"): {
        "focus": "의복·모피 제조업",
        "direct_need": "제조업 중분류 사업체·종사자·부가가치, 공장 규모",
        "comwel_prefixes": ["141", "142", "143", "144"],
        "localdata_slugs": [],
        "candidate_sources": [
            "고용보험 제조 세부업종",
            "KOSIS 광업제조업조사 시군구×중분류",
            "공장등록/건축물 용도 제조시설",
        ],
        "api_key_needed": "기존 KOSIS_API_KEY로 확인 가능",
    },
    ("C00", "10"): {
        "focus": "식료품 제조업",
        "direct_need": "제조업 중분류 사업체·종사자·부가가치, 공장 규모",
        "comwel_prefixes": ["101", "102", "103", "104", "105", "106", "107", "108"],
        "localdata_slugs": [],
        "candidate_sources": [
            "고용보험 제조 세부업종",
            "KOSIS 광업제조업조사 시군구×중분류",
            "식품제조가공업 인허가/공장등록",
        ],
        "api_key_needed": "기존 KOSIS_API_KEY로 확인 가능",
    },
}

LOCALDATA_LABEL = {
    "fitness_centers": "체력단련장업",
    "golf_practice_ranges": "골프연습장업",
    "billiard_halls": "당구장업",
    "martial_arts_dojo": "체육도장업",
    "pc_bangs": "인터넷컴퓨터게임시설제공업",
    "performance_halls": "공연장",
}

GOYANG_LAYER_LABEL = {
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
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0.0)


def has_env_name(name: str) -> bool:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return False
    text = env_path.read_text(encoding="utf-8", errors="ignore")
    return bool(re.search(rf"^\s*{re.escape(name)}\s*=", text, flags=re.MULTILINE))


def high_gap_table() -> pd.DataFrame:
    df = pd.read_csv(PHASE133, dtype={"middle_code": str})
    df["middle_code"] = df["middle_code"].astype(str).str.zfill(2)
    df["error_contribution_pct"] = df["phase133_error_eok"] / df["phase133_error_eok"].sum() * 100
    rows = []
    for (parent, middle), meta in TARGET_CODES.items():
        g = df[df["parent_code"].eq(parent) & df["middle_code"].eq(middle)]
        if g.empty:
            continue
        r = g.iloc[0]
        rows.append({
            "parent_code": parent,
            "middle_code": middle,
            "middle_label": r["middle_label"],
            "actual_gva_eok": float(r["actual_gva_eok"]),
            "prediction_eok": float(r["phase133_prediction_eok"]),
            "error_eok": float(r["phase133_error_eok"]),
            "error_rate_pct": float(r["phase133_error_rate_pct"]),
            "error_contribution_pct": float(r["error_contribution_pct"]),
            "focus": meta["focus"],
            "direct_need": meta["direct_need"],
        })
    return pd.DataFrame(rows).sort_values("error_eok", ascending=False).reset_index(drop=True)


def comwel_coverage() -> pd.DataFrame:
    if not COMWEL.exists():
        return pd.DataFrame()
    df = pd.read_csv(COMWEL, dtype=str)
    df = df[df["city"].eq("고양시")].copy()
    code = df["고용보험 업종코드(제11차)"].fillna(df["고용보험 업종코드"]).astype(str).str.extract(r"(\d+)")[0]
    df["ksic5"] = code.fillna("")
    df["workers"] = num(df.get("고용보험 상시근로자수", pd.Series(index=df.index, dtype=str)))
    df["active_flag"] = df.get("고용보험 사업구분", pd.Series("", index=df.index)).astype(str).str.contains("계속", na=False)
    rows = []
    for (parent, middle), meta in TARGET_CODES.items():
        prefixes = tuple(meta["comwel_prefixes"])
        if not prefixes:
            continue
        g = df[df["ksic5"].str.startswith(prefixes, na=False)].copy()
        active = g[g["active_flag"]]
        top_names = (
            active.groupby("고용보험 업종명(제11차)", dropna=False)
            .size()
            .sort_values(ascending=False)
            .head(4)
        )
        rows.append({
            "parent_code": parent,
            "middle_code": middle,
            "source_name": "고용보험 사업장 세부업종",
            "source_status": "collected_local_precision_candidate",
            "matched_ksic_prefixes": ",".join(prefixes),
            "raw_rows": int(len(g)),
            "active_rows": int(len(active)),
            "active_workers": float(active["workers"].sum()),
            "top_activity_labels": "; ".join(f"{idx}:{val}" for idx, val in top_names.items()),
            "flash_gate": "공표시차/as-of archive 확인 전 strict flash 금지",
        })
    return pd.DataFrame(rows)


def active_localdata(path: Path) -> tuple[int, float, str]:
    if not path.exists():
        return 0, 0.0, "missing"
    df = read_csv_any(path)
    status = df.get("영업상태명", pd.Series("", index=df.index)).astype(str)
    detail = df.get("상세영업상태명", pd.Series("", index=df.index)).astype(str)
    active = df[status.str.contains("영업|정상", na=False) | detail.str.contains("영업|정상", na=False)]
    area_cols = [c for c in active.columns if "소재지면적" in str(c) or str(c).strip() in {"소재지면적", "영업장면적"}]
    area = float(num(active[area_cols[0]]).sum()) if area_cols else 0.0
    return int(len(active)), area, "collected"


def localdata_coverage() -> pd.DataFrame:
    rows = []
    for (parent, middle), meta in TARGET_CODES.items():
        for slug in meta["localdata_slugs"]:
            count, area, status = active_localdata(LOCALDATA_RAW / f"localdata_{slug}_goyang.csv")
            rows.append({
                "parent_code": parent,
                "middle_code": middle,
                "source_name": f"LOCALDATA {LOCALDATA_LABEL.get(slug, slug)}",
                "source_status": status,
                "active_rows": count,
                "active_area_sqm": area,
                "raw_path": str(LOCALDATA_RAW / f"localdata_{slug}_goyang.csv"),
                "flash_gate": "변동분/공표시차 확인 전 strict flash 금지, 정밀화·공간배분 후보",
            })
    return pd.DataFrame(rows)


def goyang_catalog_matches() -> pd.DataFrame:
    if not CATALOG.exists():
        return pd.DataFrame()
    df = pd.read_csv(CATALOG)
    keywords = ["체육", "영화", "상영", "공연", "골프", "당구", "수영", "빙상", "승마", "썰매", "도장", "체력"]
    mask = df.astype(str).apply(lambda c: c.str.contains("|".join(keywords), na=False)).any(axis=1)
    out = df.loc[mask, ["apiKeyword", "layerId", "layerName", "tagNm", "provdInstt", "csvAt", "jsonAt", "updtDt"]].copy()
    out["use_for"] = np.where(out["layerName"].astype(str).str.contains("영화|상영", na=False), "J59/J60 보조", "ERS91 스포츠·오락")
    return out.sort_values(["use_for", "layerName"]).reset_index(drop=True)


def goyang_layer_coverage() -> pd.DataFrame:
    rows = []
    for layer_id, (parent, middle, label) in GOYANG_LAYER_LABEL.items():
        path = LOCALDATA_RAW / f"goyang_layer_{layer_id}.csv"
        if path.exists() and path.stat().st_size:
            try:
                df = read_csv_any(path)
                row_count = int(len(df))
                columns = ",".join(map(str, df.columns[:8]))
                status = "collected"
            except Exception as exc:  # noqa: BLE001 - diagnostic artifact should record parse failure.
                row_count = 0
                columns = ""
                status = f"parse_failed:{type(exc).__name__}"
        else:
            row_count = 0
            columns = ""
            status = "missing"
        rows.append({
            "parent_code": parent,
            "middle_code": middle,
            "layer_id": layer_id,
            "layer_name": label,
            "source_status": status,
            "row_count": row_count,
            "raw_size_bytes": int(path.stat().st_size) if path.exists() else 0,
            "first_columns": columns,
            "raw_path": str(path),
        })
    return pd.DataFrame(rows)


def external_requests() -> pd.DataFrame:
    rows = [
        {
            "needed_key": "KOPIS_API_KEY",
            "status_in_env": "present" if has_env_name("KOPIS_API_KEY") else "missing",
            "target": "스포츠·오락/공연장: 공연 건수·관객수·매출",
            "public_link": "https://www.kopis.or.kr/por/cs/openapi/openApiInfo.do",
            "why_needed": "시설 수보다 관객·매출이 GVA에 더 직접적",
        },
        {
            "needed_key": "KOBIS_API_KEY",
            "status_in_env": "present" if has_env_name("KOBIS_API_KEY") else "missing",
            "target": "영상·오디오 제작업/영화상영: 지역별 관객수·매출",
            "public_link": "https://www.kobis.or.kr/kobisopenapi/homepg/main/main.do",
            "why_needed": "영화상영관 인허가보다 매출·관객이 GVA에 더 직접적",
        },
        {
            "needed_key": "none",
            "status_in_env": "not_required",
            "target": "고양시 체육시설현황·영화상영관·LOCALDATA 체육/공연 인허가",
            "public_link": "https://www.goyang.go.kr/bigdata/lvlhmap/map.do",
            "why_needed": "행정동 공간배분과 정밀화 구조축 보강",
        },
    ]
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


def write_report(high_gap: pd.DataFrame, comwel: pd.DataFrame, localdata: pd.DataFrame, layers: pd.DataFrame, catalog: pd.DataFrame, requests: pd.DataFrame) -> None:
    REPORT.write_text("\n".join([
        "# Phase134 고양시 금액격차 상위 업종 직접자료 로드맵",
        "",
        "## 목적",
        "",
        "Phase133에서 즉시 채택 가능한 금액가중 개선 패키지가 없었으므로, 이번 단계는 잔여 금액격차 상위 중분류에 필요한 직접 활동자료를 분리한다. 핵심은 `오차율 큰 업종`이 아니라 `억원 격차와 전체 오차 기여도가 큰 업종`을 우선 개선하는 것이다.",
        "",
        "## 금액격차 우선순위",
        "",
        md_table(high_gap, ["parent_code", "middle_code", "middle_label", "actual_gva_eok", "prediction_eok", "error_eok", "error_rate_pct", "error_contribution_pct", "direct_need"]),
        "",
        "## 이미 수집된 고용보험 세부업종 커버리지",
        "",
        md_table(comwel, ["parent_code", "middle_code", "source_name", "matched_ksic_prefixes", "active_rows", "active_workers", "top_activity_labels", "flash_gate"]),
        "",
        "## 이미 수집된 LOCALDATA 체육·공연 인허가 커버리지",
        "",
        md_table(localdata, ["parent_code", "middle_code", "source_name", "source_status", "active_rows", "active_area_sqm", "flash_gate"]),
        "",
        "## 추가 수집한 고양시 포털 레이어",
        "",
        md_table(layers, ["parent_code", "middle_code", "layer_id", "layer_name", "source_status", "row_count", "raw_size_bytes", "first_columns"]),
        "",
        "## 고양시 빅데이터 포털 후보 레이어",
        "",
        md_table(catalog, ["use_for", "layerId", "layerName", "apiKeyword", "tagNm", "provdInstt", "jsonAt", "updtDt"], n=30),
        "",
        "## 추가 API/자료 요청",
        "",
        md_table(requests, ["needed_key", "status_in_env", "target", "public_link", "why_needed"]),
        "",
        "## 판정",
        "",
        "1. 스포츠·오락 서비스업은 고양시 포털/LOCALDATA 시설 수가 풍부하지만, 시설 수만으로는 4,366억원 규모 GVA의 이용강도·매출 변동을 설명하기 어렵다. KOPIS 공연 관객·매출 또는 공공체육시설 이용실적 같은 활동량이 필요하다.",
        "2. 방송업과 영상·오디오 제작업은 고용보험 세부업종 자료가 이미 있으나, 종사자·사업장 수만으로 2023년 금액격차를 충분히 줄이지 못했다. 고양시 영상산업 특성상 기업 입주·제작지원·촬영/상영 매출 자료가 필요하다.",
        "3. 제조업 세부 중분류는 KOSIS 광업제조업조사와 고용보험 세부업종이 이미 가장 직접적인 축이다. 여기서는 신규 API보다 과거연도 holdout과 공표시차 확인을 우선해야 한다.",
        "4. 다음 실행 우선순위는 KOPIS/KOBIS 키 확보 후 관객·매출을 지역·월 단위로 붙이는 것이다. 키가 없으면 기존 후보를 더 고르는 것보다, 포스터/보고서에는 금액가중 진단과 자료 한계를 정직하게 제시하는 편이 낫다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    high_gap = high_gap_table()
    comwel = comwel_coverage()
    localdata = localdata_coverage()
    layers = goyang_layer_coverage()
    catalog = goyang_catalog_matches()
    requests = external_requests()

    high_gap.to_csv(OUT / "phase134_high_gap_priority.csv", index=False)
    comwel.to_csv(OUT / "phase134_comwel_direct_coverage.csv", index=False)
    localdata.to_csv(OUT / "phase134_localdata_direct_coverage.csv", index=False)
    layers.to_csv(OUT / "phase134_goyang_downloaded_layer_coverage.csv", index=False)
    catalog.to_csv(OUT / "phase134_goyang_catalog_candidate_layers.csv", index=False)
    requests.to_csv(OUT / "phase134_external_api_requests.csv", index=False)
    write_report(high_gap, comwel, localdata, layers, catalog, requests)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
