#!/usr/bin/env python3
"""Phase180: residual source retriage after Phase179.

This phase does not change GVA estimates.  It audits remaining >20% middle
industry errors after Phase179, invalidates stale "no further data needed"
metadata when the current audited error contradicts it, and maps each residual
block to the next free/public activity-data candidates.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = DATA / "phase180_residual_source_retriage"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase180_residual_source_retriage.md"

RESIDUAL = DATA / "phase179_metadata_guarded_middle_gate/phase179_residual_gt20.csv"
SUMMARY = DATA / "phase179_metadata_guarded_middle_gate/phase179_summary.csv"


SOURCE_MAP = {
    "MN0": {
        "block": "전문·사업지원",
        "priority": 1,
        "candidate_data": "조달청 계약정보/입찰공고, 조달업체 기본·업종·공급물품, 개인사업자 매출·재무, 법인/사업장 규모",
        "free_sources": [
            "조달청_나라장터 공공데이터개방표준서비스: https://www.data.go.kr/data/15058815/openapi.do",
            "조달청_나라장터 사용자정보 서비스: https://www.data.go.kr/data/15129466/openapi.do?recommendDataYn=Y",
            "조달청_나라장터 업종 및 근거법규서비스: https://www.data.go.kr/data/15129467/openapi.do",
            "금융위원회 개인사업자 기본/재무/매출 정보: 기존 수집·활용",
        ],
        "key_need": "공공데이터포털 키. 조달청 사용자정보/업종법규는 현재 403이므로 승인-키 연결 재확인 필요.",
        "model_use": "MN0 전체가 아니라 70/71/72/73/74/75/76 중분류별 계약액·사업장규모 축으로 분리",
    },
    "ERS": {
        "block": "환경·수도·개인서비스",
        "priority": 2,
        "candidate_data": "폐기물 처리량/처리업체/시설용량, 하수처리량·수질, 단체/개인서비스 사업장 활동",
        "free_sources": [
            "한국환경공단_하수처리수재이용현황: https://www.data.go.kr/data/15118460/fileData.do",
            "한국수자원공사_하수처리장 일일 수질: https://www.data.go.kr/data/15099046/openapi.do",
            "환경공단 폐기물 처리업체/폐기물처분부담금 후보: 현재 403, 재시도 필요",
            "LOCALDATA 인허가/영업상태: 기존 보유·수집 가능",
        ],
        "key_need": "공공데이터포털 키. 일부 환경공단 API는 현재 403이므로 서비스별 승인 확인 필요.",
        "model_use": "E36/E37/E38/E39와 ERS94/96을 분리; 시설 수가 아니라 처리량·가동량·영업상태를 우선",
    },
    "C00": {
        "block": "제조업",
        "priority": 3,
        "candidate_data": "공장등록 업종·생산품·종업원·면적, 제조업 중분류별 광업제조업 통계, 전력/물동량",
        "free_sources": [
            "한국산업단지공단_공장등록생산정보조회서비스: https://www.data.go.kr/data/15087611/openapi.do",
            "FactoryOn OpenAPI 목록: https://www.factoryon.go.kr/openapi/list.do",
            "한국산업단지공단_공장등록필지정보조회서비스: https://www.data.go.kr/data/15087615/openapi.do",
            "포항항 품목별 물동량: 기존 MOF 수집자료",
        ],
        "key_need": "공공데이터포털 키. 공장등록생산정보는 개발계정 자동승인 후보.",
        "model_use": "C00 전체 보정 금지; 식료품/비금속/기계수리/전자/의복 등 잔여 중분류별 직접지표 후보 선별",
    },
    "J00": {
        "block": "정보통신·콘텐츠",
        "priority": 4,
        "candidate_data": "통신회선·가입자, 방송사업자/콘텐츠 제작·배급 활동, KOBIS 영화시장 시간지표",
        "free_sources": [
            "과학기술정보통신부_유선통신서비스 통계: https://www.data.go.kr/data/15070091/fileData.do",
            "KOBIS OpenAPI: 기존 KOBIS_API_KEY 사용 가능",
            "방송·콘텐츠 지역매출 직접자료는 공개 API 탐색 계속 필요",
        ],
        "key_need": "KOBIS는 사용 가능. KOPIS는 사용 불가. 통신/방송 직접 지역자료는 추가 탐색 필요.",
        "model_use": "J58/J59/J60/J61/J62/J63 분리; KOBIS는 J59 시간축 보조만, J61은 통신회선/가입자 자료 필요",
    },
    "K00": {
        "block": "금융·보험",
        "priority": 5,
        "candidate_data": "금융회사 주소·종업원, 지역 여수신/보험료/계약건수, 개인사업자 금융·매출",
        "free_sources": [
            "금융위원회_금융회사기본정보: https://www.data.go.kr/data/15043232/openapi.do?recommendDataYn=Y",
            "금융공공데이터 안내: https://www.fsc.go.kr/in060000",
            "금융위원회 개인사업자 기본/재무/매출 정보: 기존 수집·활용",
        ],
        "key_need": "공공데이터포털 키. 금융회사기본정보는 자동승인 후보이나 지역 취급액 직접자료는 별도 탐색 필요.",
        "model_use": "K64/K65/K66을 분리; 금융회사 수보다 취급액·계약액·보험료 성격 자료 필요",
    },
    "H00": {
        "block": "운수·창고",
        "priority": 6,
        "candidate_data": "항만 품목별 물동량, 물류주선업체, 교통량/화물차 통행",
        "free_sources": [
            "해양수산통계 DT_MLTM_1310: 기존 포항항 월별 품목 물동량 수집",
            "행안부 기타 국제물류주선업 조회서비스: https://www.data.go.kr/en/data/15155056/openapi.do",
            "한국도로공사_AVC원시자료: https://www.data.go.kr/data/15066742/openapi.do",
        ],
        "key_need": "MOF_API_KEY 사용 가능. 행안부/도로공사 API는 공공데이터포털 신청 필요 가능.",
        "model_use": "H50은 항만물동량 조건부 유지; 고양 H50처럼 항만활동 없는 소규모 셀은 별도 보정 금지",
    },
}


def md_table(df: pd.DataFrame, digits: int = 2, max_rows: int | None = None) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    if max_rows is not None and len(view) > max_rows:
        view = view.head(max_rows).copy()
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
        lines.append("| " + " | ".join(row[c].replace("|", "\\|") for c in view.columns) + " |")
    if max_rows is not None and len(df) > max_rows:
        lines.append(f"\n_상위 {max_rows}개 표시, 전체 {len(df):,}개는 CSV 참조_")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    residual = pd.read_csv(RESIDUAL)
    summary = pd.read_csv(SUMMARY)

    residual["stale_meta_flag"] = (
        residual["phase179_error_rate_pct"].gt(20)
        & (
            residual["phase92_queue"].eq("현행유지가능")
            | residual["public_claim_track"].eq("정확도 주장 가능")
            | residual["operational_track"].eq("운영 적용 가능")
            | residual["required_next_data"].eq("추가 자료 불필요")
        )
    )
    residual["updated_queue"] = residual["phase92_queue"]
    residual.loc[residual["phase179_error_rate_pct"].gt(50), "updated_queue"] = "고취약"
    residual.loc[
        residual["phase179_error_rate_pct"].between(20, 50, inclusive="right"),
        "updated_queue",
    ] = "취약"
    residual["updated_public_claim_track"] = residual["public_claim_track"]
    residual.loc[residual["phase179_error_rate_pct"].gt(20), "updated_public_claim_track"] = "추가개선 필요"
    residual["updated_operational_track"] = residual["operational_track"]
    residual.loc[residual["phase179_error_rate_pct"].gt(20), "updated_operational_track"] = "운영 개선 필요"

    source_rows = []
    for parent, g in residual.groupby("parent_code", sort=False):
        cfg = SOURCE_MAP.get(parent, {})
        actual = float(g["actual_gva_eok"].sum())
        err = float(g["phase179_error_gva_eok"].sum())
        source_rows.append(
            {
                "parent_code": parent,
                "block": cfg.get("block", parent),
                "priority": cfg.get("priority", 99),
                "residual_cells": int(len(g)),
                "actual_sum_eok": actual,
                "error_sum_eok": err,
                "wape_pct": err / actual * 100 if actual else pd.NA,
                "max_error_cell": g.iloc[0]["middle_label"],
                "stale_meta_cells": int(g["stale_meta_flag"].sum()),
                "candidate_data": cfg.get("candidate_data", "추가 조사 필요"),
                "free_sources": " / ".join(cfg.get("free_sources", [])),
                "key_need": cfg.get("key_need", "추가 조사 필요"),
                "model_use": cfg.get("model_use", "중분류별 별도 검증 필요"),
            }
        )
    source_priority = pd.DataFrame(source_rows).sort_values(["priority", "error_sum_eok"], ascending=[True, False])

    top_cells = residual[
        [
            "city",
            "parent_code",
            "middle_code",
            "middle_label",
            "actual_gva_eok",
            "phase179_predicted_gva_eok",
            "phase179_error_gva_eok",
            "phase179_error_rate_pct",
            "phase92_queue",
            "updated_queue",
            "stale_meta_flag",
            "updated_public_claim_track",
            "updated_operational_track",
            "required_next_data",
            "phase179_route",
        ]
    ].copy()

    stale = top_cells[top_cells["stale_meta_flag"]].copy()
    source_priority.to_csv(OUT / "phase180_source_priority_by_block.csv", index=False, encoding="utf-8-sig")
    top_cells.to_csv(OUT / "phase180_residual_cells_retriaged.csv", index=False, encoding="utf-8-sig")
    stale.to_csv(OUT / "phase180_stale_metadata_cells.csv", index=False, encoding="utf-8-sig")
    (OUT / "execution_manifest.json").write_text(
        json.dumps(
            {
                "phase": "phase180_residual_source_retriage",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "input": str(RESIDUAL.relative_to(ROOT)),
                "does_not_change_estimates": True,
                "purpose": "retriage residual >20% middle-industry errors and map free/public activity data candidates",
                "outputs": {
                    "residual_cells": int(len(top_cells)),
                    "stale_metadata_cells": int(len(stale)),
                    "source_blocks": int(len(source_priority)),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summ_show = summary[summary["candidate"].eq("Phase179 메타게이트")][
        ["candidate", "city", "actual_sum_eok", "error_sum_eok", "wape_pct", "gt20_cells", "gt50_cells"]
    ]
    REPORT.write_text(
        f"""# Phase180 Phase179 잔여오차 재분류와 직접 활동자료 우선순위

## 목적

Phase179는 합계 WAPE를 16.44%까지 낮췄고 기준선 대비 악화 셀을 만들지 않았다. 하지만 20% 초과 잔여오차가 56개 남아 있으며, 이 중 일부는 과거 메타데이터에서 `현행유지가능` 또는 `정확도 주장 가능`으로 남아 있다. 이번 단계는 추정값을 바꾸지 않고, 남은 오차를 기준으로 메타판정과 다음 수집자료 우선순위를 갱신한다.

## Phase179 현황

{md_table(summ_show, 2)}

## 잔여오차 업종군 우선순위

{md_table(source_priority[["priority","parent_code","block","residual_cells","actual_sum_eok","error_sum_eok","wape_pct","stale_meta_cells","candidate_data","key_need"]].rename(columns={
    "priority":"우선순위",
    "parent_code":"상위산업",
    "block":"업종군",
    "residual_cells":"20%초과 셀",
    "actual_sum_eok":"실제 GVA(억원)",
    "error_sum_eok":"잔여오차(억원)",
    "wape_pct":"잔여 WAPE(%)",
    "stale_meta_cells":"메타판정 갱신필요 셀",
    "candidate_data":"필요 활동자료",
    "key_need":"키/수집 상태",
}), 2)}

## 메타판정 갱신 필요 셀

아래 셀들은 현재 감사오차가 20%를 넘는데 과거 판정이 `현행유지가능`, `정확도 주장 가능`, `운영 적용 가능`, 또는 `추가 자료 불필요`로 남아 있다. 이후 포스터/보고서에서는 이 판정을 사용하면 안 된다.

{md_table(stale[["city","parent_code","middle_code","middle_label","actual_gva_eok","phase179_error_gva_eok","phase179_error_rate_pct","phase92_queue","updated_queue","updated_public_claim_track","updated_operational_track"]].rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase179_error_gva_eok":"오차(억원)",
    "phase179_error_rate_pct":"오차율(%)",
    "phase92_queue":"기존 판정",
    "updated_queue":"갱신 판정",
    "updated_public_claim_track":"갱신 공개트랙",
    "updated_operational_track":"갱신 운영트랙",
}), 2, 40)}

## 상위 30개 잔여 셀

{md_table(top_cells[["city","parent_code","middle_code","middle_label","actual_gva_eok","phase179_predicted_gva_eok","phase179_error_gva_eok","phase179_error_rate_pct","updated_queue","required_next_data"]].head(30).rename(columns={
    "city":"도시",
    "parent_code":"상위산업",
    "middle_code":"중분류",
    "middle_label":"업종명",
    "actual_gva_eok":"실제 GVA(억원)",
    "phase179_predicted_gva_eok":"추정 GVA(억원)",
    "phase179_error_gva_eok":"오차(억원)",
    "phase179_error_rate_pct":"오차율(%)",
    "updated_queue":"갱신 판정",
    "required_next_data":"필요자료",
}), 2, 30)}

## 무료 공개자료/API 후보

{md_table(source_priority[["priority","block","free_sources","model_use"]].rename(columns={
    "priority":"우선순위",
    "block":"업종군",
    "free_sources":"무료 공개자료/API 후보",
    "model_use":"모형 반영 방식",
}), 2)}

## 판정

1. Phase179 결과를 기준으로 과거 `현행유지가능/정확도 주장 가능` 메타판정은 일부 폐기해야 한다. 현재 감사오차가 20%를 넘는 셀은 모두 `추가개선 필요 / 운영 개선 필요`로 재분류한다.
2. 다음 실제 성능 개선 우선순위는 `MN0 전문·사업지원`, `ERS 환경·개인서비스`, `C00 제조업`, `J00 정보통신·콘텐츠`, `K00 금융·보험` 순이다.
3. 현재 추가 API가 막혀 있으므로 즉시 모델 반영 가능한 새 자료는 제한적이다. 다만 공장등록생산정보, 조달청 계약정보, 금융회사기본정보, 하수/폐기물 관련 파일·API는 모두 개인이 무료로 접근 가능한 후보로 확인됐다.
4. 다음 실험은 새 자료가 열리는 즉시 상위산업 일괄 보정이 아니라 `도시 × 중분류` 단위의 block routing으로만 적용해야 한다.
""",
        encoding="utf-8",
    )
    print(REPORT)
    print(OUT)


if __name__ == "__main__":
    main()
