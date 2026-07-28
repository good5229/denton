#!/usr/bin/env python3
"""Phase184: local activity-source availability matrix.

The goal is to avoid waiting on network/API calls when useful free/public
activity data are already cached locally.  This script catalogs local candidate
tables against Phase182 residual blocks and classifies whether each source is
usable for flash, precision, both, or audit only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "phase184_local_activity_source_availability"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase184_local_activity_source_availability.md"

PHASE182_SOURCE = ROOT / "data" / "processed" / "phase182_residual_improvement_routebook" / "phase182_source_pack_priority.csv"


@dataclass(frozen=True)
class Candidate:
    source_id: str
    path: str
    blocks: str
    expected_resolution: str
    intended_use: str
    original_scope_note: str
    source_status: str
    caveat: str


def candidates() -> list[Candidate]:
    return [
        Candidate(
            "factory_feature_table",
            "data/processed/factory_feature_table.csv",
            "C00",
            "시군구/공장 또는 집계, 산업: 제조업 KSIC 후보, 시점: snapshot/연",
            "제조업 중분류·소분류 공간 배분 정밀화",
            "원천은 공장등록 계열 전국 자료에서 지역 필터링 가능한 구조로 추정; phase184에서 컬럼으로 재확인",
            "local_cached",
            "생산금액 actual이 아니면 공장면적·종업원·생산품 구조지표로만 사용",
        ),
        Candidate(
            "factory_aggregate_feature_table",
            "data/processed/factory_aggregate_feature_table.csv",
            "C00",
            "시군구/연 또는 snapshot 집계, 산업: 제조업",
            "C00 중분류별 배분근거 후보",
            "전국 집계 가능 후보",
            "local_cached",
            "중분류별 실제 생산액이 없으면 단독 채택 금지",
        ),
        Candidate(
            "factory_ksic_fine_mapping",
            "data/processed/factory_ksic_fine_mapping.csv",
            "C00",
            "KSIC 세분류 매핑",
            "공장등록 생산품/업종을 KSIC 중·소분류로 연결",
            "전국 공장등록 매핑 보조표",
            "local_cached",
            "수작업/자동 매핑 품질 감사를 같이 사용",
        ),
        Candidate(
            "municipality_electricity_monthly",
            "data/processed/municipality_electricity_monthly.csv",
            "C00, ERS 일부, 전산업 보조",
            "시군구/월, 산업: 계약종별 또는 용도",
            "제조업·전력 민감 업종 시간축 보조",
            "전국 시군구 전력 자료로 보이며 다른 지역 재사용 가능",
            "local_cached",
            "2021~2023 actual 검증기간과 겹치는지, 공표시점 lag를 반드시 적용",
        ),
        Candidate(
            "electricity_feature_registry",
            "data/processed/electricity_feature_registry.csv",
            "C00, ERS 일부, 전산업 보조",
            "자료계약서/공표시점",
            "전력자료 속보성 사용 가능성 판정",
            "전국 시군구 전력자료의 메타데이터",
            "local_cached",
            "공표 lag 기준을 위반하면 속보 트랙 제외",
        ),
        Candidate(
            "pps_bid_monthly_summary",
            "data/processed/phase122_pps_bid_notices/phase122_pps_goyang_pohang_monthly_summary.csv",
            "MN0, F00, 사업지원, 전문서비스",
            "고양·포항/월, 조달 공고/입찰",
            "조달 수요 시간축 보조 및 MN0/F00 일부 개선 후보",
            "원천 조달청 API는 전국 자료이나 현재 파일은 고양·포항 필터 산출물",
            "local_cached_subset",
            "입찰공고는 계약금액 actual이 아니므로 낙찰/계약정보가 열리면 우선 교체",
        ),
        Candidate(
            "pps_procurement_indicators",
            "data/processed/phase123_pps_procurement_gva_improvement/phase123_pps_indicators.csv",
            "MN0, F00, 사업지원, 전문서비스",
            "고양·포항/업종 후보",
            "기존 조달 기반 GVA 개선 후보 재사용 여부 판단",
            "원천은 전국 가능성이 있으나 산출물은 고양·포항 중심",
            "local_cached_subset",
            "target actual 기준 채택 여부가 섞이지 않았는지 Phase183 규칙 적용 필요",
        ),
        Candidate(
            "personal_business_indicators",
            "data/processed/phase120_finance_procurement_source_integration/phase120_personal_business_indicators.csv",
            "MN0, K00, G00, 서비스 일부",
            "시군구/업종 후보",
            "개인사업자 구조·매출 보조",
            "금융공공데이터 원천은 전국 자료일 가능성이 높고 고양·포항 필터 여부 확인 필요",
            "local_cached",
            "공표시점·익명화 수준에 따라 정밀화 전용일 수 있음",
        ),
        Candidate(
            "pohang_port_product_year",
            "data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_pohang_port_product_year.csv",
            "C00, H00",
            "포항항/연/품목",
            "포항 C24·H50/H52 보조, 항만 게이트",
            "원천 MOF 자료는 항만 전체 수집 가능하나 현재 산출물은 포항항 중심",
            "local_cached_subset",
            "항만 없는 지역에는 적용 금지; 포항 외 일반화 시 각 항만 수집 필요",
        ),
        Candidate(
            "pohang_port_annual_summary",
            "data/processed/phase170_pohang_port_cargo_split_diagnostic/phase170_pohang_port_annual_summary.csv",
            "C00, H00",
            "포항항/연",
            "포항항 품목 구조 요약",
            "원천 MOF 전국항만 가능, 현재는 포항항 중심",
            "local_cached_subset",
            "철강/광물 내부비중 진단은 외부검증 전 전체 C00 채택 금지",
        ),
        Candidate(
            "kobis_monthly_summary",
            "data/processed/phase136_kobis_boxoffice_temporal_proxy/phase136_kobis_monthly_summary.csv",
            "J59, ERS90/91 일부 시간축",
            "전국/월",
            "영화시장 시간축 보조",
            "KOBIS 전국 박스오피스 top-list",
            "local_cached",
            "고양·포항 공간 actual이 아니며 Phase136에서 J59 자동채택 기각",
        ),
        Candidate(
            "goyang_sports_layer_intensity",
            "data/processed/phase135_goyang_sports_layer_intensity_audit/phase135_goyang_layer_intensity_summary.csv",
            "ERS91",
            "고양시/시설 layer/snapshot",
            "고양 스포츠·오락 정밀 공간구조 보조",
            "고양시 포털/공공시설 계열 지역특화 자료",
            "local_cached_subset",
            "2023 속보에는 부적격으로 기존 진단됨; 정밀화/공간구조 전용",
        ),
        Candidate(
            "building_register_features",
            "data/processed/partial_stats_phase51_building_register_goyang_pohang_rows.csv",
            "MN0, L00, F00, ERS 일부",
            "고양·포항/건축물/용도",
            "사업장·시설 규모 보조",
            "원천 건축물대장/건축데이터는 전국 자료로 확장 가능, 현재 산출물은 고양·포항",
            "local_cached_subset",
            "공표/등록일 기준으로 as-of 구분 필요",
        ),
        Candidate(
            "building_permit_events",
            "data/processed/partial_stats_phase52_building_permit_events_goyang_pohang.csv",
            "F00, L00, MN0 일부",
            "고양·포항/월/인허가 이벤트",
            "건설·부동산·시설투자 시간축 보조",
            "원천 건축 인허가 전국 확장 가능, 현재 산출물은 고양·포항",
            "local_cached_subset",
            "인허가가 부가가치 발생시점과 다를 수 있어 lag 검증 필요",
        ),
        Candidate(
            "realestate_broker_features",
            "data/processed/partial_stats_phase53_realestate_broker_goyang_pohang.csv",
            "L00, MN0 일부",
            "고양·포항/중개업/영업상태",
            "부동산·중개업 공간구조 보조",
            "LOCALDATA 원천은 전국 인허가 가능, 현재 산출물은 고양·포항",
            "local_cached_subset",
            "GVA target actual이 아니므로 거래/임대료 자료와 결합 필요",
        ),
    ]


def try_read(path: Path) -> tuple[pd.DataFrame, str]:
    if not path.exists():
        return pd.DataFrame(), "missing"
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc), enc
        except Exception:
            continue
    return pd.DataFrame(), "read_error"


def classify_use(c: Candidate, df: pd.DataFrame) -> tuple[str, str, str]:
    text = " ".join(df.columns.astype(str)).lower() if not df.empty else ""
    has_year = any(x in text for x in ["year", "년도", "연도", "yyyy"])
    has_month = any(x in text for x in ["month", "월", "ym", "yyyymm", "date"])
    has_city = any(x in text for x in ["city", "sigungu", "시군구", "sgg", "region"])
    has_emd = any(x in text for x in ["emd", "행정동", "법정동", "dong", "읍면동"])
    has_ksic = any(x in text for x in ["ksic", "industry", "산업", "업종", "middle_code", "middle"])
    has_release = any(x in text for x in ["publication", "release", "eligible", "공표", "등록일", "rgst", "asof"])
    spatial = []
    if has_city:
        spatial.append("시군구")
    if has_emd:
        spatial.append("읍면동/동")
    if not spatial:
        spatial.append("불명/전국 또는 특수지역")
    temporal = []
    if has_year:
        temporal.append("연")
    if has_month:
        temporal.append("월")
    if not temporal:
        temporal.append("snapshot/불명")
    industry = "KSIC/업종 연결 후보" if has_ksic else "산업 연결 약함"

    if "속보에는 부적격" in c.caveat or "정밀화" in c.caveat:
        track = "정밀화 우선"
    elif has_release or "registry" in c.source_id or "publication" in c.path:
        track = "속보/정밀 판정 가능"
    elif has_month and c.source_status != "missing":
        track = "속보 후보: 공표시점 추가확인"
    else:
        track = "정밀화/구조 후보"
    return ", ".join(spatial), ", ".join(temporal), f"{industry}; {track}"


def md_table(rows: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
    out = ["| " + " | ".join(h for _, h in cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        vals = []
        for key, _ in cols:
            val = str(row.get(key, ""))
            vals.append(val.replace("|", "/").replace("\n", " ")[:240])
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def matches_block(blocks: str, block: str) -> bool:
    text = str(blocks)
    if block in text:
        return True
    if block == "J00" and any(code in text for code in ["J58", "J59", "J60", "J61", "J62", "J63"]):
        return True
    if block == "H00" and any(code in text for code in ["H49", "H50", "H51", "H52"]):
        return True
    if block == "ERS" and any(code in text for code in ["ERS90", "ERS91", "ERS94", "ERS96", "E36", "E37", "E38", "E39"]):
        return True
    return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for c in candidates():
        p = ROOT / c.path
        df, enc = try_read(p)
        exists = p.exists() and enc != "read_error"
        spatial, temporal, industry_track = classify_use(c, df)
        sample_cols = ", ".join(list(df.columns.astype(str))[:24]) if not df.empty else ""
        rows.append(
            {
                "source_id": c.source_id,
                "path": c.path,
                "exists": bool(exists),
                "read_encoding": enc,
                "rows": int(len(df)) if exists else 0,
                "columns": int(len(df.columns)) if exists else 0,
                "blocks": c.blocks,
                "detected_spatial": spatial,
                "detected_temporal": temporal,
                "industry_track": industry_track,
                "expected_resolution": c.expected_resolution,
                "intended_use": c.intended_use,
                "original_scope_note": c.original_scope_note,
                "source_status": c.source_status,
                "caveat": c.caveat,
                "sample_columns": sample_cols,
            }
        )

    df_out = pd.DataFrame(rows)
    matrix_path = OUT / "phase184_local_source_availability_matrix.csv"
    df_out.to_csv(matrix_path, index=False, encoding="utf-8-sig")

    block_rows = []
    for block in ["MN0", "ERS", "C00", "J00", "K00", "H00"]:
        sub = df_out[df_out["blocks"].map(lambda x: matches_block(x, block))]
        block_rows.append(
            {
                "block": block,
                "candidate_sources": int(len(sub)),
                "available_sources": int(sub["exists"].sum()),
                "flash_or_asof_candidates": int(sub["industry_track"].str.contains("속보").sum()),
                "precision_or_structure_candidates": int(sub["industry_track"].str.contains("정밀화|구조").sum()),
                "top_sources": ", ".join(sub[sub["exists"]]["source_id"].head(5).tolist()),
            }
        )
    block_df = pd.DataFrame(block_rows)
    block_path = OUT / "phase184_block_source_coverage.csv"
    block_df.to_csv(block_path, index=False, encoding="utf-8-sig")

    p182 = pd.read_csv(PHASE182_SOURCE) if PHASE182_SOURCE.exists() else pd.DataFrame()
    p182_text = ""
    if not p182.empty:
        p182_display = p182[["block", "cells", "error_sum_eok", "source_pack", "api_dependency", "model_action"]].copy()
        p182_display["error_sum_eok"] = p182_display["error_sum_eok"].round(2)
        p182_text = md_table(p182_display.to_dict("records"), [
            ("block", "업종군"),
            ("cells", "셀"),
            ("error_sum_eok", "잔여오차(억원)"),
            ("source_pack", "필요 자료묶음"),
            ("api_dependency", "API/자료"),
        ])

    missing = df_out[~df_out["exists"]].to_dict("records")
    available = df_out[df_out["exists"]].to_dict("records")

    report = f"""# Phase184 로컬 공개 활동자료 가용성 매트릭스

## 목적

Phase182에서 남은 고오차 업종군은 MN0, ERS, C00, J00, K00, H00 순으로 정리됐다. Phase184는 외부 API 호출이 막혀 있는 동안에도, 이미 로컬에 캐시된 무료·공개 활동자료가 어떤 업종군에 바로 연결 가능한지 점검한다.

이 단계는 예측값을 바꾸지 않는다. 다음 Phase에서 사용할 수 있는 입력 후보와 사용 제한을 정리하는 사전 준비다.

## Phase182 필요 자료묶음

{p182_text if p182_text else "- Phase182 source priority 파일을 찾지 못했다."}

## 업종군별 로컬 자료 커버리지

{md_table(block_df.to_dict("records"), [
    ("block", "업종군"),
    ("candidate_sources", "후보수"),
    ("available_sources", "로컬가용"),
    ("flash_or_asof_candidates", "속보/as-of 후보"),
    ("precision_or_structure_candidates", "정밀/구조 후보"),
    ("top_sources", "대표 자료"),
])}

## 사용 가능한 로컬 후보

{md_table(available, [
    ("source_id", "자료ID"),
    ("blocks", "대상"),
    ("rows", "행"),
    ("detected_spatial", "공간"),
    ("detected_temporal", "시간"),
    ("industry_track", "산업/트랙"),
    ("intended_use", "사용 목적"),
    ("caveat", "제한"),
])}

## 아직 로컬 파일이 없거나 읽기 실패한 후보

{md_table(missing, [
    ("source_id", "자료ID"),
    ("path", "경로"),
    ("blocks", "대상"),
    ("source_status", "상태"),
    ("caveat", "제한"),
]) if missing else "후보 파일은 모두 로컬에서 확인됐다."}

## 판정

1. **C00 제조업**은 공장등록·전력·포항항 물동량이 이미 로컬에 있어 다음 개선 실험의 1차 대상이 될 수 있다. 다만 C00 전체 일괄 보정은 금지하고, 식료품/비금속/기계수리/전자 등 중분류별로 따로 선택해야 한다.
2. **MN0 전문·사업지원**은 조달 입찰공고와 개인사업자 지표가 있으나, 입찰공고는 계약/낙찰 금액보다 약하다. 새로 승인된 조달청 계약/낙찰 API가 열리면 우선 교체해야 한다.
3. **ERS 환경·개인서비스**는 고양 스포츠시설·LOCALDATA·건축물 계열은 있으나, 폐기물/하수 처리량 같은 직접 물량형 지표가 부족하다. 한국수자원공사/환경공단 자료가 열리면 E36/E37/E38/E39를 별도 개선한다.
4. **J00 정보통신·콘텐츠**는 KOBIS가 있으나 Phase136에서 고양 J59 자동채택은 기각됐다. 콘텐츠·방송·출판은 별도 매출/사업체 활동자료가 없으면 보수적으로 유지한다.
5. **K00 금융·보험**은 개인사업자/금융회사 구조자료만으로는 금액형 지역 활동량이 약하다. 예수금·대출·보험료 같은 금액형 공개 API가 필요하다.
6. 고양·포항 subset 파일은 원천이 전국 자료인 경우가 많다. 다른 지역 일반화 실험 때 원천 전체 자료를 다시 사용해야 하며, 현재 subset만으로 전국 일반화 성능을 주장하면 안 된다.

## 다음 실험 제안

Phase185는 네트워크 없이 가능한 범위에서 **C00 제조업 로컬 재실험**이 가장 현실적이다. 입력은 공장등록 + 전력 + 포항항 물동량이며, 선택 조건은 Phase183 guardrail을 따른다. MN0/ERS는 계약/처리량 API가 열릴 때까지 기존 자료만으로는 큰 폭 개선을 기대하기 어렵다.

## 산출물

- 가용성 매트릭스: `{matrix_path.relative_to(ROOT)}`
- 업종군별 커버리지: `{block_path.relative_to(ROOT)}`
"""
    REPORT.write_text(report, encoding="utf-8")

    manifest = {
        "phase": 184,
        "candidate_sources": int(len(df_out)),
        "available_sources": int(df_out["exists"].sum()),
        "outputs": [str(matrix_path.relative_to(ROOT)), str(block_path.relative_to(ROOT)), str(REPORT.relative_to(ROOT))],
    }
    (OUT / "execution_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
