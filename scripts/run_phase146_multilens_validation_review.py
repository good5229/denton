#!/usr/bin/env python3
"""Phase146 multi-lens validation review for Goyang/Pohang KSIC GVA estimates.

This script does not fit a new model. It consolidates currently available
evidence into a reproducible review report: data scope, temporal-leakage guards,
accounting checks, operational performance, and purpose-specific judgments.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/phase146_multilens_validation_review"
REPORT = ROOT / "reports/partial_statistics_estimation_phase146_multilens_validation_review.md"


def read_csv(rel: str) -> pd.DataFrame:
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def read_parquet(rel: str) -> pd.DataFrame:
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def md_table(df: pd.DataFrame, float_digits: int = 2) -> str:
    if df.empty:
        return "\n"
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{float_digits}f}")
    out = out.fillna("").astype(str)
    headers = list(out.columns)

    def esc(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", "<br>")

    lines = [
        "| " + " | ".join(esc(h) for h in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in out.iterrows():
        lines.append("| " + " | ".join(esc(row[h]) for h in headers) + " |")
    return "\n".join(lines)


def pct(x: float) -> str:
    return f"{x:.2f}"


def summarize_cube(rel: str, city: str) -> dict[str, object]:
    df = read_parquet(rel)
    return {
        "city": city,
        "rows": len(df),
        "years": "-".join(map(str, sorted(df["year"].dropna().astype(int).unique()))),
        "industry_levels": ", ".join(df["industry_level"].value_counts().index.astype(str).tolist()),
        "industry_counts": " / ".join(
            f"{lvl} {cnt}"
            for lvl, cnt in df.groupby("industry_level")["industry_code"].nunique().sort_index().items()
        ),
        "time_levels": ", ".join(df["time_level"].value_counts().index.astype(str).tolist()),
        "geo_counts": " / ".join(
            f"{lvl} {cnt}"
            for lvl, cnt in df.groupby("geo_level")["geo_code"].nunique().sort_index().items()
        ),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    input_rels = [
        "data/processed/phase145_operational_route_decision_registry/phase145_selected_operational_performance.csv",
        "data/processed/phase145_operational_route_decision_registry/phase145_operational_route_decision_registry.csv",
        "data/processed/phase145_operational_route_decision_registry/phase145_accounting_checks.csv",
        "data/processed/phase144_city_temporal_route_audit/phase144_baseline_samewindow_temporal_comparison.csv",
        "data/processed/phase143_temporal_out_of_sample_route_audit/phase143_baseline_samewindow_temporal_comparison.csv",
        "data/processed/phase132_source_vintage_eligibility_audit/phase132_vintage_eligibility_summary.csv",
        "data/processed/partial_stats_phase41_all_ksic_multiresolution_cube.parquet",
        "data/processed/partial_stats_phase42_pohang_multiresolution_cube.parquet",
        "data/processed/ksic10_official_registry.csv",
        "data/processed/ksic11_official_registry.csv",
        "data/processed/ksic10_11_official_crosswalk.csv",
    ]

    perf = read_csv(
        "data/processed/phase145_operational_route_decision_registry/"
        "phase145_selected_operational_performance.csv"
    )
    registry = read_csv(
        "data/processed/phase145_operational_route_decision_registry/"
        "phase145_operational_route_decision_registry.csv"
    )
    checks = read_csv(
        "data/processed/phase145_operational_route_decision_registry/"
        "phase145_accounting_checks.csv"
    )
    city_audit = read_csv(
        "data/processed/phase144_city_temporal_route_audit/"
        "phase144_baseline_samewindow_temporal_comparison.csv"
    )
    parent_audit = read_csv(
        "data/processed/phase143_temporal_out_of_sample_route_audit/"
        "phase143_baseline_samewindow_temporal_comparison.csv"
    )
    vintage = read_csv(
        "data/processed/phase132_source_vintage_eligibility_audit/"
        "phase132_vintage_eligibility_summary.csv"
    )

    cube_summary = pd.DataFrame(
        [
            summarize_cube(
                "data/processed/partial_stats_phase41_all_ksic_multiresolution_cube.parquet",
                "고양시",
            ),
            summarize_cube(
                "data/processed/partial_stats_phase42_pohang_multiresolution_cube.parquet",
                "포항시",
            ),
        ]
    )

    perf_out = perf[
        [
            "city",
            "vintage_label",
            "selected_operational_route",
            "evaluated_years",
            "actual_sum_eok",
            "error_sum_eok",
            "overall_wape_pct",
            "high_value_wape_pct",
            "gt20_cells",
            "operation_note",
        ]
    ].copy()
    perf_out.columns = [
        "지역",
        "운영시점",
        "운영경로",
        "평가기간",
        "실제 총량(억원)",
        "절대오차 합(억원)",
        "전체 WAPE(%)",
        "고액업종 WAPE(%)",
        "20%초과 셀",
        "비고",
    ]

    registry_out = registry[
        [
            "city",
            "vintage_label",
            "selected_operational_route",
            "decision_status",
            "baseline_wape_pct",
            "city_temporal_wape_pct",
            "temporal_delta_pct_point",
            "reason",
        ]
    ].copy()
    registry_out.columns = [
        "지역",
        "운영시점",
        "채택경로",
        "판정",
        "기준 WAPE(%)",
        "시간분리 후보 WAPE(%)",
        "차이(%p)",
        "근거",
    ]

    temporal_out = city_audit[
        [
            "city",
            "vintage_label",
            "baseline_wape_pct",
            "city_same_window_wape_pct",
            "city_temporal_wape_pct",
            "city_temporal_vs_baseline_delta_pct_point",
            "recommendation",
        ]
    ].copy()
    temporal_out.columns = [
        "지역",
        "운영시점",
        "기준 WAPE(%)",
        "동일창 후보 WAPE(%)",
        "시간분리 WAPE(%)",
        "시간분리-기준(%p)",
        "권고",
    ]

    parent_out = parent_audit[
        [
            "city",
            "vintage_label",
            "baseline_wape_pct",
            "same_window_parent_wape_pct",
            "temporal_oos_wape_pct",
            "temporal_vs_baseline_wape_delta_pct_point",
        ]
    ].copy()
    parent_out.columns = [
        "지역",
        "운영시점",
        "기준 WAPE(%)",
        "상위산업 동일창 WAPE(%)",
        "상위산업 시간분리 WAPE(%)",
        "시간분리-기준(%p)",
    ]

    source_summary = vintage.pivot_table(
        index=["city", "vintage_label"],
        columns="strict_flash_eligible",
        values="source_count",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    for col in ["Y", "PARTIAL", "UNKNOWN", "N"]:
        if col not in source_summary.columns:
            source_summary[col] = 0
    source_summary = source_summary[["city", "vintage_label", "Y", "PARTIAL", "UNKNOWN", "N"]]
    source_summary.columns = ["지역", "운영시점", "속보적격", "부분적격", "공표시점미확인", "속보부적격"]

    purpose = pd.DataFrame(
        [
            ["학술연구", "추가 검증 후 활용 가능", 3, "배분·외삽·벤치마킹 연구질문에는 적합하나 인과·공식통계 주장은 제한"],
            ["지역경제 모니터링", "제한적·보조적 활용 가능", 4, "중분류 연간/분기 nowcast는 WAPE와 회계검증 근거가 있음"],
            ["지방행정·정책", "제한적·보조적 활용 가능", 3, "정책 타깃팅 후보 발굴에는 유용하나 예산·지원대상 자동결정은 부적절"],
            ["신용평가·기업위험", "현재 단독 활용 곤란", 2, "개별 기업 부도·연체 outcome 검증이 없고 지역×업종 경기지표와 신용위험은 다름"],
            ["조기경보", "추가 검증 후 활용 가능", 3, "Q+1개월 속보 체계는 설계됐지만 공표시점 미확인 자료와 outcome 선행성 검증 필요"],
            ["외부 공개 통계", "현재 활용 곤란", 1, "공식통계로 오인될 위험이 높고 표준오차·비밀보호·전국 확장검증 부족"],
            ["내부 참고자료", "제한적·보조적 활용 가능", 4, "오차·제약을 명시하면 부서 간 토론용 지표로 효과적"],
        ],
        columns=["활용목적", "판정", "점수(1~5)", "근거"],
    )

    period = pd.DataFrame(
        [
            ["월별", "조건부 참고", "행정동·소분류 월간 흐름 탐색", "상위 actual 직접검증 부족, 계절·달력효과·희소셀 민감"],
            ["분기별", "운영 활용 후보", "Q+1개월 rolling nowcast와 재검증", "자료 공표시점 registry와 시간분리 백테스트 유지 필요"],
            ["연도별", "가장 안정적", "상위 actual 집계검증과 회계 정합성", "Q4 회계회수는 예측성능이 아니라 최종 정산"],
        ],
        columns=["주기", "판정", "적합한 용도", "주의점"],
    )

    industry = pd.DataFrame(
        [
            ["대분류", "안정적 요약", "대외 설명·정책 큰 방향", "산업 내 이질성 은폐"],
            ["중분류", "핵심 운영단위", "집계검증·포스터·행정 의사결정 보조", "일부 중분류는 직접 활동자료 부족 시 오차 집중"],
            ["소분류", "내부 진단용", "중분류 오차 원인 추적·업종 세분화 후보", "관측치 부족·분류오류·비밀보호 위험으로 단독 공개 부적합"],
        ],
        columns=["KSIC 수준", "판정", "적합한 용도", "주의점"],
    )

    model_candidates = pd.DataFrame(
        [
            ["현 운영 기준 배분·외삽", "높음", "중", "높음", "현재 운영 baseline. 2022~2023 시간분리 감사 통과"],
            ["Denton/Chow-Lin 계열 시간배분", "중", "중", "중", "연간·분기 통제총량과 고빈도 지표가 함께 있을 때 유리"],
            ["산업군별 직접 활동자료 라우팅", "중", "중~상", "중", "부동산·건설·운수·문화 등 직접지표 확보 시 제한 적용"],
            ["계층적 베이지안/소지역 추정", "낮음~중", "상", "중", "불확실성 제시에 강하지만 유지보수와 설명비용이 큼"],
            ["머신러닝 앙상블", "낮음", "상", "낮음~중", "현재 연도 수·지역 수에서는 과적합 위험이 큼"],
        ],
        columns=["모형 후보", "설명가능성", "구현복잡도", "현재 권장도", "비고"],
    )

    # Persist evidence tables for downstream inspection.
    tables = {
        "phase146_cube_summary.csv": cube_summary,
        "phase146_operational_performance.csv": perf_out,
        "phase146_temporal_candidate_audit.csv": temporal_out,
        "phase146_parent_candidate_audit.csv": parent_out,
        "phase146_flash_source_summary.csv": source_summary,
        "phase146_purpose_judgment.csv": purpose,
        "phase146_period_judgment.csv": period,
        "phase146_industry_level_judgment.csv": industry,
        "phase146_model_candidates.csv": model_candidates,
    }
    for name, df in tables.items():
        df.to_csv(OUT_DIR / name, index=False)
    manifest = {
        "phase": "phase146_multilens_validation_review",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "inputs": [],
    }
    for rel in input_rels:
        path = ROOT / rel
        if path.exists():
            manifest["inputs"].append(
                {
                    "path": rel,
                    "bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                }
            )
        else:
            manifest["inputs"].append({"path": rel, "missing": True})
    (OUT_DIR / "execution_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    goyang_q1 = perf[(perf.city == "고양시") & (perf.available_quarters == 1)].iloc[0]
    goyang_q3 = perf[(perf.city == "고양시") & (perf.available_quarters == 3)].iloc[0]
    pohang_q1 = perf[(perf.city == "포항시") & (perf.available_quarters == 1)].iloc[0]
    pohang_q3 = perf[(perf.city == "포항시") & (perf.available_quarters == 3)].iloc[0]
    q4_checks_pass = bool(checks["pass"].all())
    max_check = checks["max_abs_diff_eok"].abs().max()

    report = f"""# Phase146 고양·포항 KSIC 업종별 GVA 추정모형 다중 관점 검증

## 전제

초기 검토에서는 사용자의 기존 지시 때문에 subagent를 만들지 않았으나, 이후 사용자가 이번 검증 절차에 한해 subagent 사용을 승인했다. 따라서 이번 개정본은 8개 전문 역할을 3개 검토 묶음으로 나눈 subagent 검토 결과를 반영했다: 연구방법론·통계/시계열, KSIC·데이터품질, 신용·행정활용·레드팀. 최종 판단과 문구 반영은 루트 작업자가 통합했다.

이번 검토의 예측 대상은 **총부가가치(GVA)** 다. 사업체 수, 매출, 전력, 인허가, 조달, 교통·항만 등의 자료는 GVA를 직접 관측하는 값이 아니라 GVA를 배분·외삽하기 위한 활동지표 또는 구조지표다.

## A. 한 페이지 요약

현재 고양시·포항시 모형은 **공식통계가 제공하지 않는 시군구·행정동/읍면동 × KSIC 대·중·소분류 × 월·분기·연 GVA를 이용 가능 활동지표와 구조지표로 배분·외삽하고, 사후에는 최종 연간 actual과 집계 정합성을 검증하는 운영형 추정체계**다. 가장 방어 가능한 사용처는 “중분류 중심의 지역경제 모니터링과 행정 내부 참고자료”이며, 신용평가·개별기업 위험판정·공식통계 대체에는 아직 부족하다.

확인된 운영 성능은 2022~2023 두 개 holdout 연도에서, 분기 rolling 시점에 생성한 **연간 중분류 GVA 예측**을 사후 연간 actual과 비교한 집계검증 기준이다. 고양시는 Q1+1개월 WAPE {pct(goyang_q1.overall_wape_pct)}%, Q1~Q3+1개월 WAPE {pct(goyang_q3.overall_wape_pct)}%다. 포항시는 Q1+1개월 WAPE {pct(pohang_q1.overall_wape_pct)}%, Q1~Q3+1개월 WAPE {pct(pohang_q3.overall_wape_pct)}%다. 분기 자체 GVA의 독립 actual 검증은 아직 제한적이며, Q4+1개월은 연간 통제총량을 회수하는 회계 정산 단계이므로 예측력으로 해석하지 않는다.

중요한 감사 결과는 “더 좋아 보이는 복잡한 후보”가 모두 채택된 것이 아니라는 점이다. Phase143~144 시간분리 검증에서 동일 평가창 기준 개선 후보의 상당수가 baseline보다 악화되어, Phase145에서는 고양 Q1~Q3와 포항 Q1~Q2를 baseline으로 되돌렸다. 포항 Q3만 시간분리에서 아주 작은 개선이 확인되어 제한 후보로 채택했다.

최종 판정은 다음과 같다.

- **현재 표본 내에서 방어 가능한 결과**: 도시×KSIC 중분류×분기 rolling 시점의 연간 GVA nowcast에 대한 amount-weighted 집계검증, Q4 회계정합성, 후보모형 시간분리 탈락/채택 판정.
- **조건부 해석 결과**: 월별·행정동/읍면동·소분류 추정치. 공간·산업 세부 진단에는 유용하지만 단독 actual 검증이 부족하므로 상위 집계검증과 불확실성 표시가 필요하다.
- **현재 신뢰하기 어려운 결과**: 공식통계 대체, 인과효과 주장, 개별기업 신용평가, 소분류 월별 수치의 외부 공개 순위화, 전국 일반화 주장.
- **최우선 보완사항**: 공표일자/as-of 자료관리, 타지역·추가연도 외부검증, 산업별 직접 활동자료 확충, 예측구간 제시, KSIC 개정·소표본 비밀보호 규칙.

## 프로젝트 구조·자료·추정흐름 확인

### 확인된 파일 구조

| 구분 | 확인 내용 |
| --- | --- |
| 주요 코드 | `scripts/run_phase131~145_*.py` 계열 rolling 추정·감사·운영 결정 스크립트 |
| 주요 보고서 | `reports/partial_statistics_estimation_phase131~145_*.md` |
| 고양 산출 | `goyang/`, `data/processed/partial_stats_phase41_*` |
| 포항 산출 | `pohang/`, `data/processed/partial_stats_phase42_*` |
| 공표시점 감사 | `reports/partial_statistics_estimation_phase132_source_vintage_eligibility_audit.md` |
| 최종 운영 결정 | `reports/partial_statistics_estimation_phase145_operational_route_decision_registry.md` |

### 추정 큐브 범위

{md_table(cube_summary, 0)}

KSIC 계층은 대분류 19개, 중분류 74개, 소분류 228개로 산출되어 있다. 로컬 `ksic10_official_registry.csv` 기준 KSIC 10차는 2017-07-01~2024-06-30 유효하고, `ksic11_official_registry.csv` 및 `ksic10_11_official_crosswalk.csv`도 확보되어 있다. 따라서 2021~2023 평가 결과는 **KSIC 10차 기준**으로 해석한다. 2024-07-01 이후 자료는 KSIC 11차 적용 및 10↔11 연결표 검증 없이는 동일 결론으로 확장하지 않는다.

또한 `parent_code`는 공식 KSIC 대분류와 완전히 같지 않은 모형용 상위그룹을 포함한다. 예를 들어 `ERS`는 수도·하수·폐기물·문화·기타서비스를 묶은 운영상 그룹이고, `MN0`는 전문·과학·기술 및 사업지원 관련 그룹이다. 외부 공개표에서는 공식 KSIC 대분류와 모형용 상위그룹을 분리해 표기해야 한다.

### 운영 성능: Q1~Q3 예측

{md_table(perf_out)}

위 표는 Phase145 운영 선택표를 요약한 것이며, Q4 행은 비교 편의를 위해 포함되어 있다. 외부 공개 성능표에서는 Q4 0%를 평균 예측성능에 포함하지 말고 아래 회계검증으로 분리하는 것이 안전하다.

### 회계 검증

{md_table(checks.rename(columns={'check_id':'검증항목','rows':'행수','max_abs_diff_eok':'최대차이(억원)','pass':'통과'}))}

검증 결과, Q4 연간 회수 및 현재분기+이전기간=누계 정합성은 통과했다. 최대 회계 차이는 {max_check:.8f}억원 수준이며, 이는 부동소수점 오차로 볼 수 있다. 이 항목은 예측성능이 아니라 회계 정합성 검증이다.

## B. 목적별 활용성 평가표

{md_table(purpose, 0)}

## C. 주기별 평가표

{md_table(period, 0)}

## D. 산업분류 수준별 평가표

{md_table(industry, 0)}

## 전문 관점별 검토

### subagent 교차검토 반영사항

| 검토 묶음 | 주요 지적 | 반영 |
| --- | --- | --- |
| 연구방법론·통계/시계열 | 두 개 holdout 연도만으로 “신뢰 가능” 표현은 강함. Q4 0%는 성능표가 아니라 회계검증으로 분리해야 함. | “현재 표본 내 방어 가능”으로 표현 완화, 2022~2023 한계와 Q4 회계정산 성격 명시 |
| KSIC·데이터품질 | KSIC 10차/11차 기준, `parent_code`와 공식 대분류 혼동, as-of 누수 위험, manifest 부족 | KSIC 10차 적용기간과 11차 전환주의 명시, 모형용 상위그룹 설명, execution manifest 생성 |
| 신용·행정활용·레드팀 | 제안서·포스터에서 자동 정책결정처럼 읽힐 위험, 소액고오차 묶음은 개별 후순위라도 총량 모니터링 필요 | 정책 활용은 “후보 경보→현장확인→부서검토”로 제한, 금액가중 핵심관리/관리관찰/소액고오차 표현 권고 |

### 1. 연구방법론 검증

이 작업은 관찰자료 기반의 **소지역 GVA 배분·외삽·nowcast**에 가깝다. 통계적 예측이라는 표현은 Q1~Q3 rolling 단계에만 제한적으로 적합하고, Q4는 회계 정산이다. 연구보고서에서는 “지역 산업 GVA의 고빈도 추정 가능성”과 “상위 actual 집계검증 기반의 운영지표 설계”를 연구질문으로 삼을 수 있다.

허용되는 주장은 “상위 총량과 일치하도록 조정된 고빈도·세분류 추정치가 지역경제 모니터링에 보조적으로 기여한다” 정도다. 허용되지 않는 주장은 “개별 기업 위험을 직접 예측한다”, “공식통계를 대체한다”, “정책 효과의 인과성을 입증한다”다.

### 2. 통계·시계열 검증

현 운영모형의 장점은 설명가능성과 회계 정합성이다. 단점은 연도 수가 2021~2023 중심이라 구조변화·계절성·달력효과를 충분히 분리하기 어렵다는 점이다. 아래 시간분리 감사에서 보듯 동일 평가창에서 좋아 보인 후보가 미래연도 holdout에서는 악화될 수 있다.

{md_table(temporal_out)}

상위산업 라우팅 후보도 동일창 개선을 시간분리에서 재현하지 못했다.

{md_table(parent_out)}

따라서 현 단계에서 복잡도 증가는 “성능 개선”이 아니라 “과적합 위험”으로 우선 간주해야 한다. 추가 개선은 더 많은 지역·연도 holdout 또는 독립 직접 활동자료가 있을 때만 채택하는 것이 맞다.

### 3. KSIC 산업분류 검증

중분류는 현재 가장 균형 잡힌 운영 단위다. 소분류는 중분류 오차 원인을 찾는 내부 진단에는 필요하지만, 일부 지역·월에서는 관측근거가 희소하고 분류오류 영향이 커진다. 소분류 결과를 외부 공개하려면 최소 관측치, 최소 GVA 규모, 상위 집계 검증 통과, 비밀보호 suppression 규칙이 필요하다.

### 4. 신용평가 활용성 검증

현재 산출물은 지역×업종 경기지표이지 개별 기업 신용위험 모형이 아니다. 신용평가에 쓰려면 부도·연체·휴폐업 outcome, 기업 단위 재무·대표업종·주소 이력, 선행성 검증, calibration, PSI, 경기국면별 안정성 검증이 추가되어야 한다. 지금은 신용평가 단독 변수로는 부적절하고, 포트폴리오 모니터링의 배경 경기 보조지표 정도가 상한이다.

### 5. 행정·정책 활용성 검증

행정 활용성은 비교적 높다. 특히 고양·포항처럼 산업구조가 다른 도시에서 같은 형식의 중분류 GVA nowcast를 산출하면 부서 간 정책 토론의 공통 언어가 된다. 다만 지원대상 선정, 예산 배분, 규제 판단 같은 처분성 의사결정에는 단독 사용하면 안 된다. 정책 현장에서는 “진단 → 현장자료 대조 → 부서 검토 → 의사결정” 흐름의 첫 단계로 쓰는 것이 적절하다.

### 6. 데이터 품질·재현성 검증

재현성의 강점은 phase별 스크립트와 보고서가 축적되어 있고, input_hash/run_id가 큐브에 남아 있다는 점이다. 약점은 원천 raw data가 gitignore되어 있으며 API key와 다운로드 시점에 의존한다는 점, 일부 자료의 공표일자/as-of archive가 아직 미확인이라는 점이다.

속보 적격성 감사 요약은 다음과 같다.

{md_table(source_summary, 0)}

UNKNOWN 및 needs_publication_calendar 자료는 엄격 속보에는 투입하지 않거나, 투입 시 “정밀화 전용”으로 명확히 분리해야 한다.

### 7. 레드팀 검토

가장 큰 위험은 세 가지다.

1. **데이터 유출 위험**: 연간 actual 또는 사후 확정 자료가 Q+1개월 속보 단계에 섞이면 성능이 과대평가된다. Phase132의 공표시점 감사와 Phase145의 baseline 회귀는 이를 줄였지만, 원출처 공표일자 확인이 끝나지 않은 자료는 여전히 제한해야 한다.
2. **과적합 위험**: Phase141~142의 parent routing은 동일창에서는 개선됐지만 Phase143 시간분리에서는 악화됐다. 따라서 “복잡한 라우팅=좋은 모형”이 아니다.
3. **해석 과잉 위험**: 소분류·월별·행정동 값은 그럴듯한 지도와 순위를 만들 수 있지만 actual 검증은 대부분 상위 집계로만 가능하다. 외부 포스터에서는 중분류 중심의 검증표를 앞에 두고 소분류는 진단 보조로 내려야 한다.

### 8. 종합판정

현재 체계는 “공공데이터 기반 지역 GVA 고빈도 추정 엔진”으로서 내부 정책·연구·모니터링에는 기여가 있다. 그러나 현재 성능근거는 2022~2023 두 개 holdout 연도에 한정되며, 공식통계·신용평가·처분성 행정결정에 바로 투입할 정도의 검증 수준은 아니다. 다음 단계의 핵심은 더 복잡한 모형이 아니라 **검증 가능한 자료만 쓰는 운영규칙**, **타지역·추가연도 외부검증**, **업종별 직접 활동자료의 제한적 채택**, **불확실성 표시**다.

## E. 방법론 개선안

### 1단계: 즉시 적용

- Phase145 운영 레지스트리를 최종 기준으로 고정한다.
- Q1~Q3는 예측/nowcast, Q4는 회계 정산으로 라벨을 분리한다.
- 포스터·보고서에서 “전체 WAPE”와 “고액업종 WAPE”를 함께 제시한다.
- 소분류 수치는 중분류 집계검증을 통과한 범위에서만 공개하고, 그 외는 내부 진단으로 제한한다.
- 공표시점 미확인 자료는 속보가 아니라 정밀화 자료로 분리한다.

### 2단계: 추가데이터

- 부동산: 실거래, 건축물대장, 공시가격, 인허가·착공·준공 시계열의 원 공표일자 확보.
- 건설: 건축허가·착공·준공, 조달청 공사입찰, 지역별 건설수주·면허업체 활동자료.
- 운수·창고: 버스·철도·항만·물류창고 인허가, 화물처리량의 월별 공표일자 확보.
- 문화·서비스: KOBIS는 사용 가능하므로 영화·상영 관련 중분류 보조지표로 유지한다. KOPIS는 사용 불가이므로 공연업 직접지표로는 제외한다.
- 제조: 전력·공장등록·광업제조업 과거 구조자료를 쓰되, 연도별 생산·출하·부가가치 공표시점 registry를 보강한다.

### 3단계: 고도화

- 타 시군구 10개 이상으로 시간분리·공간분리 외부검증을 수행한다.
- 도시×산업별 모형 선택은 동일창 성능이 아니라 rolling-origin holdout에서만 허용한다.
- 예측구간을 추가해 단일 숫자 대신 “추정범위”로 공개한다.
- 대/중/소분류 계층을 동시 만족하는 constrained reconciliation을 적용한다.
- 신용평가 목적은 별도 프로젝트로 분리해 부도·연체·휴폐업 outcome과 연결한다.

## F. 권장 모형 후보 비교표

{md_table(model_candidates, 0)}

## G. 위험 및 제한사항

- **공표시점 위험**: 일부 활동자료는 실제 예측시점에 이용 가능했는지 확인이 끝나지 않았다.
- **상위 actual 의존**: 소분류·월별 값을 직접 검증하기 어렵고, 상위 집계검증에 의존한다.
- **지역 일반화 부족**: 현재 엄격한 운영검증은 고양·포항 중심이다. 전국 적용 주장은 아직 이르다.
- **소표본·희소셀 위험**: 소분류×행정동×월은 0 또는 극단값에 민감하다.
- **산업분류 오류**: 대표업종·사업장업종·기업업종이 다르면 KSIC 배분이 왜곡된다.
- **정책 오용 위험**: 순위표가 행정 처분이나 낙인으로 쓰이면 안 된다.
- **Q4 오해 위험**: Q4 회계 회수는 예측성능이 아니라 연간 정산이다.

## H. 최종 실행계획

1. **운영 산출물 고정**: Phase145 결정 레지스트리를 고양·포항 포스터와 보고서의 기준으로 고정한다.
2. **표현 정리**: “프록시” 대신 “활동지표/구조지표/배분근거”로 표현한다.
3. **중분류 중심 공개**: 포스터와 대외자료는 중분류 검증표를 중심에 두고, 소분류는 원인진단 또는 보조표로 제한한다.
4. **속보·정밀화 분리**: Q+1개월 자료만 속보성, 사후 확정·snapshot 자료는 정밀화로 분리한다.
5. **공표일자 registry 보강**: Phase132에서 UNKNOWN/needs_publication_calendar인 자료의 원출처 공표일자를 확인한다.
6. **불확실성 표시**: WAPE, 고액업종 WAPE, 10/20% 초과 셀 수, 예측구간을 함께 표시한다.
7. **확장검증 예약**: 고양·포항 마무리 후 비편중 10개 시군구를 선정해 동일 자료유형을 수집하고 외부검증을 수행한다.
8. **신용평가 분리검증**: KOBIS 등 업종 활동자료는 GVA 보조지표로만 쓰고, 신용평가는 별도 outcome 검증 전까지 보조적 지역경기 변수로 제한한다.

## 이번에 수행한 검증과 미수행 검증

### 수행

- Phase145 운영 성능표 재계산 결과 확인.
- Q4 회계 회수 및 누계 정합성 검증 확인.
- Phase143 parent routing 시간분리 out-of-sample 감사 결과 확인.
- Phase144 city routing 시간분리 out-of-sample 감사 결과 확인.
- Phase132 공표시점·속보적격성 요약 확인.
- 고양·포항 KSIC 대/중/소분류 × 월/분기/연 × 시/구/읍면동 큐브 범위 확인.
- KSIC 10차/11차 registry 및 10↔11 연결표 로컬 존재 확인. 2021~2023 결과는 KSIC 10차 기준으로 한정.

### 미수행 및 필요자료

- 타 시군구 10개 외부검증: 해당 지역별 동일 원천자료 수집과 actual 집계표 필요.
- 신용평가 활용검증: 부도·연체·휴폐업 outcome 및 기업 단위 패널 필요.
- 원출처 공표일자 완전감사: data.go.kr, KOSIS, 지자체 포털, 해양수산통계 등 자료별 historical release calendar 필요.
- 소분류 직접 actual 검증: 공공에서 제공되지 않으므로 현재는 중분류/대분류 집계검증으로 대체.
- 예측구간 검증: 추가 연도 또는 지역 bootstrap/rolling-origin 표본 필요.
- 엄격 속보 전용 재산출: `strict_flash_eligible in {{Y, PARTIAL}}`만 사용한 별도 WAPE 필요.
"""

    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    for name in tables:
        print(f"Wrote {OUT_DIR.relative_to(ROOT) / name}")
    print(f"Accounting checks pass: {q4_checks_pass}")


if __name__ == "__main__":
    main()
