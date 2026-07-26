#!/usr/bin/env python3
"""Phase148 strict-flash bridge audit for amount-weighted GVA priorities.

Phase145 is the current rolling operational benchmark.  Phase147 identifies
amount-weighted middle-industry priorities.  This phase checks whether those
priority industries already have strict-flash candidate evidence from Phase120
and clearly separates:

* rolling benchmark performance (2022-2023, Phase145/147), and
* 2023 cross-sectional strict-flash candidate evidence (Phase120).

The two are intentionally not merged into a single performance claim.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase148_strict_flash_priority_bridge"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase148_strict_flash_priority_bridge.md"

PRIORITY = DATA / "phase147_amount_weighted_error_priority" / "phase147_middle_priority_all.csv"
PHASE120_CITY = DATA / "phase120_finance_procurement_source_integration" / "phase120_strict_flash_city_summary.csv"
PHASE120_REG = DATA / "phase120_finance_procurement_source_integration" / "phase120_strict_flash_registry.csv"
PHASE120_OPTIONS = DATA / "phase120_finance_procurement_source_integration" / "phase120_strict_flash_selected_options.csv"
PHASE132_REQ = DATA / "phase132_source_vintage_eligibility_audit" / "phase132_publication_date_requests.csv"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def md_table(df: pd.DataFrame, digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_"
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
    out = out.fillna("").astype(str)
    cols = list(out.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, r in out.iterrows():
        lines.append("| " + " | ".join(r[c].replace("|", "\\|") for c in cols) + " |")
    return "\n".join(lines)


def candidate_track(row: pd.Series) -> str:
    option = str(row.get("phase120_strict_flash_option_id", ""))
    if option == "" or option == "nan":
        return "후보없음"
    if option == "baseline":
        return "baseline"
    status = str(row.get("public_claim_status", ""))
    if "보류" in status:
        return "조건부보류"
    if "2021 이하" in status or "지연자료" in status:
        return "지연구조자료"
    if "검증 통과" in status:
        return "속보후보검증통과"
    return "status미확인"


def bridge_status(row: pd.Series) -> str:
    track = str(row.get("candidate_track", ""))
    if track == "후보없음":
        return "직접 as-of 후보 없음"
    if track == "baseline":
        return "baseline 유지"
    rate = row.get("phase120_strict_flash_error_rate_pct", np.nan)
    if track == "조건부보류":
        return "2023 단면 저오차이나 보류" if pd.notna(rate) and float(rate) <= 10 else "2023 단면 보류"
    if track == "지연구조자료":
        return "지연 구조자료 후보"
    if str(row.get("operational_track", "")).find("운영 개선 필요") >= 0:
        return "2023 단면 저오차이나 운영개선필요" if pd.notna(rate) and float(rate) <= 10 else "운영개선필요 후보"
    rate = row.get("phase120_strict_flash_error_rate_pct", np.nan)
    if pd.notna(rate) and float(rate) <= 10:
        return "2023 단면 저오차·검증통과"
    if pd.notna(rate) and float(rate) <= 20:
        return "2023 단면 주의"
    return "2023 단면 취약"


def next_action(row: pd.Series) -> str:
    label = str(row["middle_label"])
    city = str(row["city"])
    status = str(row["strict_bridge_status"])
    if status == "직접 as-of 후보 없음":
        if "부동산" in label:
            return "국토부 실거래·공시가격·건축물 공표시점 확인 후 strict 후보 생성"
        if "항공" in label:
            return "한국공항공사 GW 스케줄/공항통계 대체자료 검토"
        if "교육" in label:
            return "교육기관·학생수·학원/학교 인허가의 월별 공표시점 확인"
        if "공공행정" in label:
            return "예산집행·조달·공공고용 월별 지표 검토"
        if "전기" in label or "가스" in label:
            return "전력·가스 판매량/사용량 시군구 월별 공표시점 확인"
        return "직접 활동자료 후보 탐색"
    if "취약" in status:
        return "후보를 바로 승격하지 말고 rolling holdout에서 재검증"
    if "주의" in status:
        return "보조지표로 유지, 금액가중 악화 방지 gate 필요"
    if "보류" in status:
        return "2셀 고적합/공표시점 위험을 해소한 뒤 rolling holdout"
    if "지연 구조자료" in status:
        return "속보 활동지표가 아니라 구조축으로만 사용"
    if "운영개선필요" in status:
        return "저오차라도 운영트랙 미통과: rolling holdout과 악화셀 gate 필요"
    if "baseline 유지" in status:
        return "직접지표 추가 수집 전까지 baseline 유지"
    return "rolling nowcast 후보로만 검토, Phase145와 직접 비교 금지"


def main() -> None:
    for p in [PRIORITY, PHASE120_CITY, PHASE120_REG, PHASE120_OPTIONS]:
        if not p.exists():
            raise FileNotFoundError(p)
    OUT.mkdir(parents=True, exist_ok=True)

    prio = pd.read_csv(PRIORITY, dtype={"middle_code": str})
    city = pd.read_csv(PHASE120_CITY)
    reg = pd.read_csv(PHASE120_REG, dtype={"middle_code": str})
    options = pd.read_csv(PHASE120_OPTIONS)

    q1 = prio[
        prio["available_quarters"].eq(1)
        & prio["priority_class"].isin(["핵심개선", "관리관찰"])
    ].copy()
    q1 = q1.sort_values(["city", "priority_score"], ascending=[True, False])

    reg_cols = [
        "city",
        "parent_code",
        "middle_code",
        "actual_gva_eok",
        "flash_baseline_error_gva_eok",
        "flash_baseline_error_rate_pct",
        "phase120_strict_flash_predicted_gva_eok",
        "phase120_strict_flash_error_gva_eok",
        "phase120_strict_flash_error_rate_pct",
        "phase120_strict_flash_option_id",
        "phase120_strict_flash_error_reduction_eok",
        "public_claim_track",
        "operational_track",
    ]
    reg_bridge = reg[reg_cols].rename(columns={"parent_code": "parent_code_phase120"})
    bridge = q1.merge(
        reg_bridge,
        on=["city", "middle_code"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    option_status = options.rename(
        columns={
            "parent_code": "parent_code_phase120",
            "option_id": "phase120_strict_flash_option_id",
        }
    )[
        [
            "city",
            "parent_code_phase120",
            "phase120_strict_flash_option_id",
            "public_claim_status",
            "adoptable",
            "worsened_cells",
            "max_worsen_eok",
            "max_worsen_pp",
        ]
    ]
    bridge = bridge.merge(
        option_status,
        on=["city", "parent_code_phase120", "phase120_strict_flash_option_id"],
        how="left",
        validate="many_to_one",
    )
    bridge["parent_group_match"] = np.where(
        bridge["parent_code_phase120"].notna(),
        bridge["parent_code"].astype(str).eq(bridge["parent_code_phase120"].astype(str)),
        np.nan,
    )
    bridge["candidate_track"] = bridge.apply(candidate_track, axis=1)
    bridge["strict_bridge_status"] = bridge.apply(bridge_status, axis=1)
    bridge["next_action"] = bridge.apply(next_action, axis=1)
    bridge["bridge_scope"] = "Phase147 2022~2023 rolling 우선순위 ↔ Phase120 2023 strict/as-of 단면 후보"

    status_summary = (
        bridge.groupby(["city", "strict_bridge_status"], as_index=False)
        .agg(
            middle_count=("middle_code", "nunique"),
            rolling_actual_sum_eok=("actual_sum_eok", "sum"),
            rolling_error_sum_eok=("error_sum_eok", "sum"),
        )
    )
    city_totals = (
        prio[prio["available_quarters"].eq(1)]
        .groupby("city", as_index=False)
        .agg(
            city_q1_actual_sum_eok=("actual_sum_eok", "sum"),
            city_q1_error_sum_eok=("error_sum_eok", "sum"),
        )
    )
    status_summary = status_summary.merge(city_totals, on="city", how="left")
    status_summary["rolling_actual_share_pct"] = (
        status_summary["rolling_actual_sum_eok"] / status_summary["city_q1_actual_sum_eok"] * 100
    )
    status_summary["rolling_error_share_pct"] = np.where(
        status_summary["city_q1_error_sum_eok"].gt(0),
        status_summary["rolling_error_sum_eok"] / status_summary["city_q1_error_sum_eok"] * 100,
        0,
    )

    missing = bridge[bridge["strict_bridge_status"].eq("직접 as-of 후보 없음")].copy()
    weak = bridge[
        bridge["strict_bridge_status"].isin(
            [
                "2023 단면 취약",
                "2023 단면 주의",
                "2023 단면 보류",
                "2023 단면 저오차이나 보류",
                "운영개선필요 후보",
                "2023 단면 저오차이나 운영개선필요",
            ]
        )
    ].copy()

    # Candidate API/data requests are free-access candidates.  URLs are kept as
    # application links for the user to request/confirm API keys when needed.
    api_candidates = pd.DataFrame(
        [
            {
                "priority": "상",
                "target_industry": "부동산업",
                "data_name": "국토교통부_아파트매매 실거래 상세 자료",
                "url": "https://www.data.go.kr/data/15126469/openapi.do",
                "use": "부동산 GVA의 거래활동·가격·회전율 활동지표",
                "key_needed": "기존 공공데이터포털 키로 가능 여부 확인",
                "coverage_limit": "아파트 거래 중심. 부동산업 전체 GVA를 직접 대표하지 않음",
                "release_lag_claim": "공표시차 원문 확인 필요",
                "verification_date": "2026-07-26",
                "as_of_eligible": "미확정",
            },
            {
                "priority": "상",
                "target_industry": "항공 운송업",
                "data_name": "한국공항공사_항공기 운항 스케줄 정보_GW",
                "url": "https://www.data.go.kr/data/15158949/openapi.do",
                "use": "김포공항/인접 공항 운항·노선 빈도 활동지표",
                "key_needed": "공공데이터포털 활용신청 필요 가능",
                "coverage_limit": "스케줄 자료이며 실제 여객·화물 실적과 다를 수 있음",
                "release_lag_claim": "실시간으로 표기되나 과거 as-of 재현 가능성 확인 필요",
                "verification_date": "2026-07-26",
                "as_of_eligible": "미확정",
            },
            {
                "priority": "중",
                "target_industry": "관광·숙박·문화",
                "data_name": "한국관광공사_국문 관광정보 서비스_GW",
                "url": "https://www.data.go.kr/data/15101578/openapi.do",
                "use": "관광·숙박 시설 구조지표 및 지역 관광활동 보조",
                "key_needed": "공공데이터포털 활용신청 필요 가능",
                "coverage_limit": "관광 콘텐츠/시설 중심. 숙박·문화 GVA 직접 활동량은 아님",
                "release_lag_claim": "실시간으로 표기되나 GVA 예측용 공표시차 별도 확인 필요",
                "verification_date": "2026-07-26",
                "as_of_eligible": "미확정",
            },
            {
                "priority": "중",
                "target_industry": "항공 운송업",
                "data_name": "한국공항공사_항공사별 운항실적 파일데이터",
                "url": "https://www.data.go.kr/data/15002628/fileData.do",
                "use": "연간 운항실적 구조자료. 속보성은 약하지만 정밀화 보조 가능",
                "key_needed": "파일데이터라 별도 API 키 불필요 가능",
                "coverage_limit": "연간 파일자료. Q+1개월 속보에는 부적합할 가능성 큼",
                "release_lag_claim": "연간 업데이트",
                "verification_date": "2026-07-26",
                "as_of_eligible": "정밀화 보조",
            },
        ]
    )

    if PHASE132_REQ.exists():
        req = pd.read_csv(PHASE132_REQ)
        req_view = req.head(30)
    else:
        req_view = pd.DataFrame()

    bridge.to_csv(OUT / "phase148_priority_strict_flash_bridge.csv", index=False)
    status_summary.to_csv(OUT / "phase148_bridge_status_summary.csv", index=False)
    missing.to_csv(OUT / "phase148_missing_strict_flash_priority.csv", index=False)
    weak.to_csv(OUT / "phase148_weak_strict_flash_priority.csv", index=False)
    api_candidates.to_csv(OUT / "phase148_free_api_candidates.csv", index=False)

    unmatched_count = int((bridge["_merge"] != "both").sum())
    parent_mismatch_count = int((bridge["parent_group_match"] == False).sum())
    option_status_counts = bridge["candidate_track"].value_counts(dropna=False).to_dict()
    manifest = {
        "phase": "phase148_strict_flash_priority_bridge",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "inputs": [],
        "script": {
            "path": "scripts/run_phase148_strict_flash_priority_bridge.py",
            "sha256": sha256(ROOT / "scripts/run_phase148_strict_flash_priority_bridge.py"),
        },
        "outputs": [
            "phase148_priority_strict_flash_bridge.csv",
            "phase148_bridge_status_summary.csv",
            "phase148_missing_strict_flash_priority.csv",
            "phase148_weak_strict_flash_priority.csv",
            "phase148_free_api_candidates.csv",
            "reports/partial_statistics_estimation_phase148_strict_flash_priority_bridge.md",
        ],
        "unmatched_priority_middle_count": unmatched_count,
        "parent_group_mismatch_count": parent_mismatch_count,
        "candidate_track_counts": option_status_counts,
        "scope_warning": "Phase120 strict flash evidence is 2023 cross-sectional; it is not directly comparable to Phase145 rolling WAPE.",
    }
    for p in [PRIORITY, PHASE120_CITY, PHASE120_REG, PHASE120_OPTIONS]:
        manifest["inputs"].append(
            {
                "path": str(p.relative_to(ROOT)),
                "bytes": p.stat().st_size,
                "sha256": sha256(p),
                "rows": int(pd.read_csv(p).shape[0]),
                "columns": list(pd.read_csv(p, nrows=0).columns),
            }
        )
    (OUT / "execution_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    display_cols = [
        "city",
        "middle_code",
        "middle_label",
        "priority_class",
        "actual_sum_eok",
        "error_sum_eok",
        "wape_pct",
        "error_share_pct",
        "phase120_strict_flash_option_id",
        "phase120_strict_flash_error_rate_pct",
        "phase120_strict_flash_error_gva_eok",
        "candidate_track",
        "public_claim_status",
        "parent_group_match",
        "strict_bridge_status",
        "next_action",
    ]
    goyang_view = bridge[bridge["city"].eq("고양시")][display_cols].head(15)
    pohang_view = bridge[bridge["city"].eq("포항시")][display_cols].head(15)
    missing_view = missing[
        [
            "city",
            "middle_code",
            "middle_label",
            "priority_class",
            "actual_sum_eok",
            "error_sum_eok",
            "error_share_pct",
            "next_action",
        ]
    ].head(20)
    weak_view = weak[
        [
            "city",
            "middle_code",
            "middle_label",
            "priority_class",
            "phase120_strict_flash_option_id",
            "phase120_strict_flash_error_rate_pct",
            "phase120_strict_flash_error_gva_eok",
            "next_action",
        ]
    ].head(20)
    status_summary_view = status_summary[
        [
            "city",
            "strict_bridge_status",
            "middle_count",
            "rolling_actual_sum_eok",
            "rolling_error_sum_eok",
            "rolling_actual_share_pct",
            "rolling_error_share_pct",
        ]
    ].copy()

    report = f"""# Phase148 strict flash 전용 우선순위 브릿지 감사

## 목적

Phase147은 금액가중 관점에서 중분류 개선 우선순위를 정했다. 이번 Phase148은 그 우선순위 업종들에 대해 **strict/as-of 적격 후보(속보 활동지표 또는 lagged 구조자료)가 이미 있는지**를 점검한다.

중요한 전제는 다음과 같다.

- Phase145/147의 rolling 성능은 2022~2023 기간의 분기별 nowcast 운영 벤치마크다.
- Phase120 strict/as-of 후보는 2023 단면에서 속보성 또는 지연 구조자료 후보를 붙인 cross-sectional 감사다. 일부 후보는 `보류`, `2021 이하 지연자료`, `공표일자 확인 필요` 상태이므로 strict 확정 자료로 읽으면 안 된다.
- 따라서 Phase120 수치를 Phase145 WAPE와 직접 비교해 “성능이 개선됐다”고 주장하지 않는다. 이번 결과는 **strict flash 보강 가능성 지도**로만 사용한다.

## Phase120 2023 단면 후보 적합도(운영 개선 아님)

{md_table(city.rename(columns={
    'city': '지역',
    'actual_sum_eok': '2023 실제합계(억원)',
    'baseline_error_eok': '기준오차(억원)',
    'baseline_wape_pct': '기준 WAPE(%)',
    'phase120_error_eok': '후보오차(억원)',
    'phase120_wape_pct': '후보 WAPE(%)',
    'error_reduction_eok': '2023 단면 기준오차 대비 차이(억원)',
    'wape_reduction_pp': '2023 단면 WAPE 차이(%p)',
    'baseline_gt20_cells': '기준 20%초과',
    'phase120_gt20_cells': 'strict 20%초과',
    'baseline_gt10_cells': '기준 10%초과',
    'phase120_gt10_cells': 'strict 10%초과',
    'worsened_cells': '악화셀'
}))}

이 표는 2023 단면의 후보 성능이다. Phase145의 2022~2023 rolling WAPE와 같은 평가가 아니므로, 포스터/보고서에서 운영 성능으로 승격하면 안 된다.

## 금액가중 우선순위와 strict/as-of 후보 연결 요약

조인 감사: Phase147 Q1 우선순위 중분류 {len(bridge)}개 중 Phase120 후보 미매칭은 {unmatched_count}개, 상위그룹 불일치는 {parent_mismatch_count}개다. 미매칭 업종은 **직접 as-of 후보 없음**으로 분류했다.

{md_table(status_summary_view.rename(columns={
    'city': '지역',
    'strict_bridge_status': '후보상태',
    'middle_count': '중분류 수',
    'rolling_actual_sum_eok': 'rolling 실제합계(억원)',
    'rolling_error_sum_eok': 'rolling 오차합(억원)',
    'rolling_actual_share_pct': '전체 Q1 rolling 실제비중(%)',
    'rolling_error_share_pct': '전체 Q1 rolling 오차기여(%)',
}))}

## 고양시 Q1 우선순위 브릿지(상위 15개 표시, 전체는 CSV 참조)

{md_table(goyang_view.rename(columns={
    'city': '지역',
    'middle_code': '중분류',
    'middle_label': '업종명',
    'priority_class': '금액가중 등급',
    'actual_sum_eok': 'rolling 실제(억원)',
    'error_sum_eok': 'rolling 오차(억원)',
    'wape_pct': 'rolling WAPE(%)',
    'error_share_pct': 'rolling 오차기여(%)',
    'phase120_strict_flash_option_id': '2023 후보',
    'phase120_strict_flash_error_rate_pct': '2023 후보 오차율(%)',
    'phase120_strict_flash_error_gva_eok': '2023 후보 오차(억원)',
    'candidate_track': '후보트랙',
    'public_claim_status': 'Phase120 공개판정',
    'parent_group_match': '상위그룹 일치',
    'strict_bridge_status': '판정',
    'next_action': '다음 조치',
}))}

## 포항시 Q1 우선순위 브릿지(상위 15개 표시, 전체는 CSV 참조)

{md_table(pohang_view.rename(columns={
    'city': '지역',
    'middle_code': '중분류',
    'middle_label': '업종명',
    'priority_class': '금액가중 등급',
    'actual_sum_eok': 'rolling 실제(억원)',
    'error_sum_eok': 'rolling 오차(억원)',
    'wape_pct': 'rolling WAPE(%)',
    'error_share_pct': 'rolling 오차기여(%)',
    'phase120_strict_flash_option_id': '2023 후보',
    'phase120_strict_flash_error_rate_pct': '2023 후보 오차율(%)',
    'phase120_strict_flash_error_gva_eok': '2023 후보 오차(억원)',
    'candidate_track': '후보트랙',
    'public_claim_status': 'Phase120 공개판정',
    'parent_group_match': '상위그룹 일치',
    'strict_bridge_status': '판정',
    'next_action': '다음 조치',
}))}

## 직접 as-of 후보가 비어 있는 금액가중 우선순위 업종

{md_table(missing_view.rename(columns={
    'city': '지역',
    'middle_code': '중분류',
    'middle_label': '업종명',
    'priority_class': '금액가중 등급',
    'actual_sum_eok': 'rolling 실제(억원)',
    'error_sum_eok': 'rolling 오차(억원)',
    'error_share_pct': 'rolling 오차기여(%)',
    'next_action': '필요 조치',
}))}

## as-of 후보가 있으나 아직 약한 업종

{md_table(weak_view.rename(columns={
    'city': '지역',
    'middle_code': '중분류',
    'middle_label': '업종명',
    'priority_class': '금액가중 등급',
    'phase120_strict_flash_option_id': '2023 후보',
    'phase120_strict_flash_error_rate_pct': '2023 후보 오차율(%)',
    'phase120_strict_flash_error_gva_eok': '2023 후보 오차(억원)',
    'next_action': '필요 조치',
}))}

## 무료 API·파일 후보

{md_table(api_candidates.rename(columns={
    'priority': '우선순위',
    'target_industry': '대상 업종',
    'data_name': '자료명',
    'url': '링크',
    'use': '활용 목적',
    'key_needed': '키/신청',
    'coverage_limit': '포괄 한계',
    'release_lag_claim': '공표시차 상태',
    'verification_date': '확인일',
    'as_of_eligible': 'as-of 적격성',
}), 0)}

확인한 공개 후보는 모두 무료 공개자료 계열이다. 다만 공공데이터포털 API는 활용신청 또는 기존 key 적용 가능 여부 확인이 필요하다.

## 판정

1. 현재 운영 성능 주장은 Phase145 기준으로 유지한다. Phase120 strict/as-of 후보는 아직 rolling 운영 성능으로 승격하지 않는다.
2. 고양시는 부동산업·항공 운송업·교육 서비스업처럼 금액가중 우선순위가 높지만 직접 as-of 후보가 없는 업종이 남아 있다.
3. 포항시는 부동산업·전기/가스/공기조절 공급업·항공 운송업·교육 서비스업·공공행정이 직접 as-of 후보 공백이다.
4. as-of 후보가 있는 업종도 2023 단면에서만 좋게 보이면 안 된다. 다음 단계는 Phase145 rolling 구조에 후보를 넣고 2022~2023 또는 추가연도 holdout에서만 채택하는 것이다.
5. 부동산업은 두 도시 모두 금액가중 중요도가 크고 직접 후보가 비어 있으므로, 다음 개선 실험의 1순위다.

## 다음 실험

1. 고양·포항 부동산업에 대해 국토부 실거래 API와 기존 로컬 실거래 manifest의 공표시점/as-of 적격성을 다시 감사한다.
2. 실거래 자료가 Q+1개월 strict로 인정되는 범위만 사용해 부동산업 annual nowcast 후보를 만든다.
3. 후보는 Phase145 baseline과 같은 rolling-origin 방식으로만 비교한다.
4. 항공 운송업은 한국공항공사 GW 스케줄 API 또는 항공통계 파일을 수집할 수 있는지 확인한 뒤 동일 절차를 적용한다.
"""
    if not req_view.empty:
        report += "\n## Phase132 공표일자 확인 요청 일부\n\n"
        report += md_table(req_view.head(20), 0)
        report += "\n"

    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    for name in [
        "phase148_priority_strict_flash_bridge.csv",
        "phase148_bridge_status_summary.csv",
        "phase148_missing_strict_flash_priority.csv",
        "phase148_weak_strict_flash_priority.csv",
        "phase148_free_api_candidates.csv",
        "execution_manifest.json",
    ]:
        print(f"Wrote {(OUT / name).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
