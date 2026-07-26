#!/usr/bin/env python3
"""Phase132: source vintage eligibility audit for rolling GVA nowcasts.

Phase131 defined the rolling quarterly update protocol.  This phase audits the
local source manifests to decide which inputs can be used in a strict
quarter+one-month flash nowcast, which inputs are precision-only, and which
inputs need primary-source publication-date confirmation.

The audit is intentionally conservative: if a historical publication date or an
as-of archive is absent, a source is not allowed into the strict flash track.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase132_source_vintage_eligibility_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase132_source_vintage_eligibility_audit.md"

TARGET_YEAR = 2023
VINTAGES = [
    (1, "Q1_plus_1m", "1분기+1개월", pd.Timestamp(f"{TARGET_YEAR}-04-30"), ["2023-01", "2023-02", "2023-03"]),
    (2, "Q2_plus_1m", "1~2분기+1개월", pd.Timestamp(f"{TARGET_YEAR}-07-31"), ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06"]),
    (3, "Q3_plus_1m", "1~3분기+1개월", pd.Timestamp(f"{TARGET_YEAR}-10-31"), ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06", "2023-07", "2023-08", "2023-09"]),
    (4, "Q4_plus_1m", "1~4분기+1개월", pd.Timestamp(f"{TARGET_YEAR + 1}-01-31"), [f"2023-{m:02d}" for m in range(1, 13)]),
]


def norm_period(value: object) -> str:
    s = str(value)
    m = re.search(r"(20\d{2})[-_]?([01]\d)", s)
    if not m:
        return ""
    month = int(m.group(2))
    if not 1 <= month <= 12:
        return ""
    return f"{m.group(1)}-{month:02d}"


def add_record(records: list[dict[str, object]], **kwargs: object) -> None:
    base = {
        "source_id": "",
        "source_label": "",
        "city": "공통",
        "source_family": "",
        "native_period_min": "",
        "native_period_max": "",
        "release_date": "",
        "release_rule": "",
        "timing_track_local": "",
        "strict_flash_class": "needs_confirmation",
        "precision_class": "usable_after_publication",
        "reason": "",
        "evidence_file": "",
    }
    base.update(kwargs)
    records.append(base)


def load_source_records() -> pd.DataFrame:
    records: list[dict[str, object]] = []

    # Source inventory with explicit release dates.
    inv_path = DATA / "partial_stats_phase35_source_inventory.csv"
    if inv_path.exists():
        inv = pd.read_csv(inv_path)
        for _, r in inv.iterrows():
            release_date = str(r.get("release_date", ""))
            period_min = str(r.get("reference_period_min", ""))
            period_max = str(r.get("reference_period_max", ""))
            if re.match(r"\d{4}-\d{2}-\d{2}", release_date):
                strict = "strict_flash_only_after_release"
                reason = "명시 release_date가 있으므로 cutoff와 직접 비교"
            elif "monthly" in release_date:
                strict = "needs_publication_calendar"
                reason = "월별 vintage라 적혀 있으나 월별 실제 공표일자가 없음"
            else:
                strict = "needs_confirmation"
                reason = "공표일자 불명"
            add_record(
                records,
                source_id=r.get("source_id", ""),
                source_label=r.get("source_family", ""),
                source_family=r.get("classification", ""),
                native_period_min=period_min,
                native_period_max=period_max,
                release_date=release_date,
                release_rule=release_date,
                timing_track_local=r.get("role", ""),
                strict_flash_class=strict,
                reason=reason,
                evidence_file=str(inv_path),
            )

    # Flash indicator sources previously marked as flash candidates.
    for path in [
        DATA / "phase117_max_source_flash_push" / "phase117_flash_indicators.csv",
        DATA / "phase120_finance_procurement_source_integration" / "phase120_all_candidate_indicators.csv",
    ]:
        if path.exists():
            df = pd.read_csv(path, dtype={"middle_code": str})
            for (city, parent, source_id), g in df.groupby(["city", "parent_code", "source_id"], dropna=False):
                note = str(g["timing_note"].dropna().iloc[0]) if g["timing_note"].notna().any() else ""
                track = str(g["timing_track"].dropna().iloc[0]) if g["timing_track"].notna().any() else ""
                label = str(g["source_label"].dropna().iloc[0]) if g["source_label"].notna().any() else str(source_id)
                if track == "속보성" and ("2021" in note or "2015" in note or "이전 이용 가능" in note or "first_eligible" in note):
                    strict = "strict_flash_static_structure"
                    reason = "과거 구조자료로 2023년 Q+1개월 이전 이용 가능하다고 로컬 timing_note에 명시"
                elif track == "속보성":
                    strict = "needs_publication_calendar"
                    reason = "속보성 후보지만 원 공표일자/시차 확인 필요"
                else:
                    strict = "not_flash_precision_or_unknown"
                    reason = "속보성으로 표시되지 않음"
                add_record(
                    records,
                    source_id=source_id,
                    source_label=label,
                    city=city,
                    source_family=str(parent),
                    timing_track_local=track,
                    strict_flash_class=strict,
                    reason=reason,
                    evidence_file=str(path),
                )

    # Precision-only Goyang OpenAPI/current-snapshot indicators.
    p114 = DATA / "phase114_block_routed_refinement_audit" / "phase114_activity_indicators.csv"
    if p114.exists():
        df = pd.read_csv(p114, dtype={"middle_code": str})
        for (city, parent, source_id), g in df.groupby(["city", "parent_code", "source_id"], dropna=False):
            label = str(g["source_label"].dropna().iloc[0]) if g["source_label"].notna().any() else str(source_id)
            add_record(
                records,
                source_id=source_id,
                source_label=label,
                city=city,
                source_family=str(parent),
                timing_track_local=str(g["timing_track"].dropna().iloc[0]) if g["timing_track"].notna().any() else "정밀화",
                strict_flash_class="not_strict_flash_current_snapshot",
                precision_class="precision_only_current_snapshot",
                reason="현재 snapshot/공표 후 활동자료로 관리되어 Q+1개월 strict flash에는 사용 금지",
                evidence_file=str(p114),
            )

    # Localdata Goyang source audit is a current snapshot with event dates.
    p37 = DATA / "partial_stats_phase37_goyang_source_audit.csv"
    if p37.exists():
        df = pd.read_csv(p37)
        for _, r in df.iterrows():
            add_record(
                records,
                source_id=f"goyang_localdata_{r.get('source_slug','')}",
                source_label=r.get("source_label", ""),
                city="고양시",
                source_family=r.get("sector_code", ""),
                native_period_min=r.get("min_permit_date", ""),
                native_period_max=r.get("max_permit_date", ""),
                release_date="current_snapshot_with_event_dates",
                release_rule="historical as-of archive absent",
                timing_track_local="정밀화/운영경보 후보",
                strict_flash_class="not_strict_flash_without_asof_archive",
                precision_class="precision_or_monitoring_after_collection",
                reason="인허가/폐업 날짜는 있으나 과거 특정 시점 snapshot 재현근거가 없음",
                evidence_file=str(p37),
            )

    # Procurement notices: announcement dates are themselves public events.
    pps = DATA / "phase122_pps_bid_notices" / "phase122_pps_goyang_pohang_monthly_summary.csv"
    if pps.exists():
        df = pd.read_csv(pps)
        for (city, op), g in df.groupby(["city", "op"], dropna=False):
            periods = sorted(norm_period(x) for x in g["period"].dropna().astype(str).unique())
            periods = [p for p in periods if p]
            add_record(
                records,
                source_id=f"pps_bid_notice_{op}",
                source_label=f"조달청 입찰공고 {op}",
                city=city,
                source_family="procurement",
                native_period_min=min(periods) if periods else "",
                native_period_max=max(periods) if periods else "",
                release_date="event_date_public_notice",
                release_rule="announcement-month public event",
                timing_track_local="속보성 후보",
                strict_flash_class="strict_flash_event_source",
                reason="입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 사용 가능",
                evidence_file=str(pps),
            )

    # RTMS apt trade manifest: API query result, but exact statutory release lag is not encoded locally.
    rtms = DATA / "partial_stats_phase55_rtms_apt_trade_call_manifest.csv"
    if rtms.exists():
        df = pd.read_csv(rtms)
        for (city, general_gu), g in df.groupby(["city", "general_gu"], dropna=False):
            periods = sorted(norm_period(x) for x in g["period"].dropna().astype(str).unique())
            add_record(
                records,
                source_id="molit_apt_trade_15126469",
                source_label="국토부 아파트 실거래가",
                city=city,
                source_family="real_estate",
                native_period_min=min(periods) if periods else "",
                native_period_max=max(periods) if periods else "",
                release_date="api_current_query",
                release_rule="local manifest lacks first-publication date",
                timing_track_local="부동산 활동 후보",
                strict_flash_class="needs_publication_calendar",
                reason="월별 조회 가능하지만 각 거래월의 최초 공개일자가 로컬 manifest에 없음",
                evidence_file=str(rtms),
            )

    # MOF Pohang cargo raw exists, but local collection does not encode monthly publication lag.
    mof_raw = ROOT / "data" / "raw" / "phase118_public_sources"
    if mof_raw.exists() and any(mof_raw.glob("mof_DT_MLTM_1310_pohang*.json")):
        add_record(
            records,
            source_id="mof_DT_MLTM_1310_pohang_port_cargo",
            source_label="해양수산통계 포항항 품목별 화물 입출항현황",
            city="포항시",
            source_family="port_logistics",
            release_date="api_current_query",
            release_rule="local raw files lack monthly publication lag",
            timing_track_local="수상운송/철강 물동량 후보",
            strict_flash_class="needs_publication_calendar",
            reason="포항항 월별 물동량 자료는 확보했지만 Q+1개월 적격성을 판단할 공표일자 메타데이터가 없음",
            evidence_file=str(mof_raw),
        )

    out = pd.DataFrame(records).drop_duplicates()
    return out.sort_values(["city", "strict_flash_class", "source_id"]).reset_index(drop=True)


def evaluate_vintage_matrix(sources: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, src in sources.iterrows():
        release_date = pd.to_datetime(src["release_date"], errors="coerce")
        period_min = norm_period(src["native_period_min"])
        period_max = norm_period(src["native_period_max"])
        for k, vid, label, cutoff, required_months in VINTAGES:
            klass = str(src["strict_flash_class"])
            if klass in {"strict_flash_static_structure", "strict_flash_event_source"}:
                eligible = "Y"
                reason = src["reason"]
            elif klass == "strict_flash_only_after_release" and pd.notna(release_date):
                eligible = "Y" if release_date <= cutoff else "N"
                reason = f"release_date={release_date.date()} cutoff={cutoff.date()}"
            elif klass.startswith("not_strict_flash"):
                eligible = "N"
                reason = src["reason"]
            else:
                eligible = "UNKNOWN"
                reason = src["reason"]
            if period_min and period_max:
                required_end = required_months[-1]
                if period_max < required_end and eligible == "Y":
                    eligible = "PARTIAL"
                    reason = f"{reason}; coverage ends {period_max}, required through {required_end}"
            rows.append({
                "source_id": src["source_id"],
                "source_label": src["source_label"],
                "city": src["city"],
                "source_family": src["source_family"],
                "vintage_id": vid,
                "vintage_label": label,
                "cutoff_date": cutoff.date().isoformat(),
                "strict_flash_eligible": eligible,
                "eligibility_reason": reason,
                "strict_flash_class": klass,
            })
    return pd.DataFrame(rows)


def summarize(sources: pd.DataFrame, matrix: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    class_summary = (
        sources.groupby(["city", "strict_flash_class"], as_index=False)
        .agg(source_count=("source_id", "nunique"))
        .sort_values(["city", "strict_flash_class"])
    )
    vintage_summary = (
        matrix.groupby(["city", "vintage_label", "strict_flash_eligible"], as_index=False)
        .agg(source_count=("source_id", "nunique"))
        .sort_values(["city", "vintage_label", "strict_flash_eligible"])
    )
    needs = sources[sources["strict_flash_class"].isin(["needs_publication_calendar", "needs_confirmation"])].copy()
    needs["request_to_user"] = np.where(
        needs["source_id"].str.contains("mof", case=False, na=False),
        "해양수산통계 DT_MLTM_1310의 월별 공표일/갱신주기 확인 필요",
        np.where(
            needs["source_id"].str.contains("molit|apt", case=False, na=False),
            "국토부 실거래가 API의 거래월별 최초 공개 가능일/갱신주기 확인 필요",
            "원 출처의 과거 공표일자 또는 as-of archive 확인 필요",
        ),
    )
    return class_summary, vintage_summary, needs


def compact_for_report(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicated evidence rows into one readable source-level row."""
    if df.empty:
        return df.copy()
    cols = [
        "city",
        "source_id",
        "source_label",
        "strict_flash_class",
        "precision_class",
        "reason",
        "request_to_user",
    ]
    present = [c for c in cols if c in df.columns]
    compact = (
        df.groupby(present, dropna=False, as_index=False)
        .agg(
            source_family=("source_family", lambda s: ", ".join(sorted({str(x) for x in s if str(x)}))[:120]),
            evidence_files=("evidence_file", lambda s: ", ".join(sorted({Path(str(x)).name for x in s if str(x)}))),
            evidence_file_count=("evidence_file", lambda s: len({str(x) for x in s if str(x)})),
        )
        .sort_values(["city", "strict_flash_class", "source_id"])
    )
    return compact


def md_table(df: pd.DataFrame, cols: list[str], n: int | None = None) -> str:
    if df.empty:
        return "_없음_"
    d = df[cols].copy()
    if n:
        d = d.head(n)
    labels = [c.replace("_", " ") for c in d.columns]
    body = ["| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |" for row in d.fillna("").to_numpy()]
    return "\n".join(["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |", *body])


def write_report(sources: pd.DataFrame, class_summary: pd.DataFrame, vintage_summary: pd.DataFrame, needs: pd.DataFrame) -> None:
    strict = compact_for_report(sources[sources["strict_flash_class"].str.startswith("strict_flash")].copy())
    precision = compact_for_report(
        sources[
            sources["precision_class"].str.contains("precision", case=False, na=False)
            & ~sources["strict_flash_class"].str.startswith("strict_flash")
        ].copy()
    )
    needs = compact_for_report(needs)
    REPORT.write_text("\n".join([
        "# Phase132 고양·포항 자료 공표시차 및 속보 적격성 감사",
        "",
        "## 목적",
        "",
        "Phase131의 분기별 rolling GVA 갱신을 실제 속보 체계로 승격하기 위해, 로컬에 남아 있는 source/audit/manifest 파일을 기준으로 자료별 Q+1개월 사용 가능성을 분리했다. 원 공표일자나 as-of archive가 없으면 엄격 속보에는 넣지 않는 보수 기준을 적용했다.",
        "",
        "## 소스 등급 요약",
        "",
        md_table(class_summary, class_summary.columns.tolist()),
        "",
        "## 빈티지별 적격성 요약",
        "",
        md_table(vintage_summary, vintage_summary.columns.tolist(), n=80),
        "",
        "## 엄격 속보에 넣을 수 있는 자료",
        "",
        md_table(strict, ["city", "source_id", "source_label", "source_family", "strict_flash_class", "reason", "evidence_files"], n=60),
        "",
        "## 정밀화 전용 또는 monitoring 전용 자료",
        "",
        md_table(precision, ["city", "source_id", "source_label", "source_family", "strict_flash_class", "precision_class", "reason"], n=60),
        "",
        "## 공표일자 확인 필요 자료",
        "",
        md_table(needs, ["city", "source_id", "source_label", "source_family", "strict_flash_class", "reason", "request_to_user", "evidence_files"], n=80),
        "",
        "## 판정",
        "",
        "1. KEPCO처럼 release_date가 명시된 자료는 Q+1개월 cutoff와 직접 비교해야 한다. 로컬 inventory 기준 2023년 1~3월 전력자료는 2023-08-16 공개라 2023-04-30 Q1+1개월 strict flash에는 부적격이다.",
        "2. KOSIS 2021/2015 구조자료처럼 과거 구조로 명시된 자료는 2023년 strict flash 구조축에 사용할 수 있다.",
        "3. 고양 LOCALDATA/OpenAPI 현재 snapshot, COMWEL 사업장 구조, 고양시 통계시설 자료는 정밀화/운영경보에는 유용하지만 과거 as-of archive가 없으면 strict flash에는 넣지 않는다.",
        "4. 조달청 입찰공고는 공고월 자체가 공개 이벤트이므로 cutoff 이전 공고만 쓰는 조건에서 strict flash 후보가 될 수 있다.",
        "5. 해양수산통계 포항항 물동량과 국토부 실거래가는 자료는 확보했지만, 월별 최초 공표일/갱신주기 메타데이터가 로컬에 없어 strict flash 투입 전 원 출처 확인이 필요하다.",
    ]) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sources = load_source_records()
    matrix = evaluate_vintage_matrix(sources)
    class_summary, vintage_summary, needs = summarize(sources, matrix)
    sources.to_csv(OUT / "phase132_source_eligibility_registry.csv", index=False)
    matrix.to_csv(OUT / "phase132_vintage_source_matrix.csv", index=False)
    class_summary.to_csv(OUT / "phase132_source_class_summary.csv", index=False)
    vintage_summary.to_csv(OUT / "phase132_vintage_eligibility_summary.csv", index=False)
    needs.to_csv(OUT / "phase132_publication_date_requests.csv", index=False)
    write_report(sources, class_summary, vintage_summary, needs)
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
