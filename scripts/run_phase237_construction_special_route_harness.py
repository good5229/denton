"""Phase237 construction special-route harness.

This script does not claim a new WAPE improvement.  It turns the current
construction bottleneck into an auditable staged experiment:

1. keep BOK-style construction order dispersion as a *time-path* candidate;
2. keep BuildingHUB/redevelopment/PPS/SOC as *spatial-allocation* candidates;
3. define collection stages and no-leakage guardrails before any new actual
   year can be used for route selection.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/phase237_construction_special_route_harness"
REPORT = ROOT / "reports/partial_statistics_estimation_phase237_construction_special_route_harness.md"
NATIONWIDE_NOTE = ROOT / "nationwide/construction_special_route_harness.md"


def fmt_num(x: object, digits: int = 3) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (int, float)):
        return f"{x:,.{digits}f}"
    return str(x)


def md_table(df: pd.DataFrame, columns: list[tuple[str, str]], max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    headers = [label for _, label in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        vals: list[str] = []
        for key, _ in columns:
            val = row.get(key, "")
            if isinstance(val, float):
                vals.append(fmt_num(val))
            else:
                vals.append(str(val))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def load_csv(path: str) -> pd.DataFrame:
    p = ROOT / path
    if not p.exists():
        raise FileNotFoundError(p)
    return pd.read_csv(p)


def classify_city(row: pd.Series) -> str:
    province = str(row["province_full"])
    city = str(row["city"])
    if province == "서울특별시" and city in {"강남구", "서초구", "송파구", "용산구", "강동구", "성동구"}:
        return "정비·대형민간건축형"
    if city in {"평택시", "여수시", "서산시", "포항시", "구미시", "울산 남구", "남구"} or province in {"울산광역시"}:
        return "산업·항만·토목혼합형"
    if province == "서울특별시":
        return "도심·상업건축혼합형"
    if province in {"경기도", "인천광역시"}:
        return "수도권 민간건축확장형"
    return "일반혼합형"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    remaining = load_csv("nationwide/outputs/active_goal_sigungu_remaining_activity_frontier.csv")
    city = load_csv("nationwide/outputs/construction_city_error_reduction_contribution.csv")
    strict_time = load_csv(
        "data/processed/phase235_construction_bok_regional_gate/"
        "phase235_construction_bok_regional_gate_strict_policy_summary.csv"
    )
    oracle = load_csv("nationwide/outputs/construction_wape_reduction_frontier.csv")

    construction = remaining[remaining["activity"] == "건설업"].iloc[0].to_dict()
    current_wape = float(construction["wape_pct"])
    current_abs = float(construction["abs_error_sum_eok"])
    actual_sum = float(construction["actual_sum_eok"])
    target_abs = actual_sum * 0.10
    required_reduction = current_abs - target_abs
    required_reduction_pct = required_reduction / current_abs * 100

    stages = []
    for n in [1, 5, 10, 28, 40, 52, 70]:
        sub = city.head(n)
        stages.append(
            {
                "stage": f"top{n}",
                "cities": n,
                "legal_dong_requests": int(sub["active_legal_dong_requests"].sum()),
                "captured_error_eok": float(sub["abs_error_sum_eok"].sum()),
                "captured_error_share_pct": float(sub["abs_error_sum_eok"].sum() / current_abs * 100),
                "oracle_wape_75pct_reduction": float(
                    (current_abs - 0.75 * sub["abs_error_sum_eok"].sum()) / actual_sum * 100
                ),
                "decision": "pipeline_probe"
                if n <= 5
                else ("primary_validation" if n == 28 else "expansion_validation"),
            }
        )
    stage_df = pd.DataFrame(stages)

    priority = city.head(52).copy()
    priority["route_type"] = priority.apply(classify_city, axis=1)
    priority["required_blocks"] = priority["route_type"].map(
        {
            "정비·대형민간건축형": "건축HUB+정비사업+기존share",
            "산업·항만·토목혼합형": "건축HUB+PPS/SOC+기존share",
            "도심·상업건축혼합형": "건축HUB+상업/업무용도+기존share",
            "수도권 민간건축확장형": "건축HUB+착공/사용승인+기존share",
            "일반혼합형": "건축HUB+PPS보조+기존share",
        }
    )

    route_blocks = pd.DataFrame(
        [
            {
                "block": "기준 배분값",
                "role": "fallback anchor",
                "data": "직전 공표연도 시군구 건설업 GVA share",
                "use_for": "새 자료가 약하거나 guardrail 실패 시 유지",
                "status": "adopted fallback",
            },
            {
                "block": "BOK식 건설수주 분산",
                "role": "time-path",
                "data": "시도별 건축/토목 건설수주액, 건축 12분기·토목 24분기 분산",
                "use_for": "광역시도×건설업 Q1/Q2 분기 시간경로",
                "status": "limited candidate",
            },
            {
                "block": "건축HUB 허가·착공·사용승인",
                "role": "private building spatial signal",
                "data": "법정동×월×용도별 면적/건수 event",
                "use_for": "민간 건축 중심 시군구 share 이동",
                "status": "collection required",
            },
            {
                "block": "재건축·재개발 단계",
                "role": "large redevelopment event signal",
                "data": "정비구역, 조합설립, 사업시행인가, 관리처분, 착공, 준공",
                "use_for": "대형 주거정비사업 지역의 급등락 보정",
                "status": "collection required",
            },
            {
                "block": "PPS 공공공사",
                "role": "public works signal",
                "data": "조달청 공사공고 소재지·금액·공종",
                "use_for": "공공·토목형 시군구 보조 share",
                "status": "candidate only",
            },
            {
                "block": "SOC/항만/도로 사업",
                "role": "civil engineering event signal",
                "data": "항만·도로·철도·산단 등 사업위치·예산·착공/준공",
                "use_for": "건축물 자료로 잡히지 않는 토목공사",
                "status": "collection required",
            },
        ]
    )

    guardrails = pd.DataFrame(
        [
            {"rule": "target-year actual 금지", "detail": "목표연도 시군구 건설업 actual로 feature, threshold, 혼합비를 고르지 않는다."},
            {"rule": "rolling prior 선택", "detail": "t-1, t-2 또는 expanding prior 성과만으로 route 적용 여부를 정한다."},
            {"rule": "속보·정밀화 분리", "detail": "속보형은 운영시점까지 공표된 허가·착공·PPS만, 정밀화는 사용승인·준공·확정 단계까지 허용한다."},
            {"rule": "동시 guardrail", "detail": "WAPE, 10% 초과 셀, 20% 초과 셀, 최대 APE가 모두 기준보다 악화되지 않아야 한다."},
            {"rule": "부문별 제한혼합", "detail": "건축HUB·PPS·정비사업을 단일 대체하지 않고 기존 share 대비 이동상한을 둔다."},
            {"rule": "부분 증거 표현", "detail": "Q1/Q2 시간경로 개선을 시군구 공간배분 개선으로 표현하지 않는다."},
        ]
    )

    experiment_steps = pd.DataFrame(
        [
            {
                "step": 1,
                "name": "top1 pipeline proof",
                "scope": "평택시",
                "purpose": "수집·정제·시점필터·feature 생성 전체 파이프라인 점검",
                "success": "방향성 설명 가능. 성능 주장은 하지 않음",
            },
            {
                "step": 2,
                "name": "top5 type gate probe",
                "scope": "평택·강남·영등포·강서·여수",
                "purpose": "민간건축형/정비형/공공토목형 gate 필요성 검증",
                "success": "단일지표 대체 금지 여부와 유형별 후보 확인",
            },
            {
                "step": 3,
                "name": "top28 primary validation",
                "scope": "오차기여 약 50% 시군구",
                "purpose": "rolling out-of-year로 제한혼합 채택 가능성 검증",
                "success": "기준보다 악화 없음, 10% 초과 셀 감소",
            },
            {
                "step": 4,
                "name": "top52 expansion validation",
                "scope": "오차기여 약 70% 시군구",
                "purpose": "건설업 시군구 WAPE 10% 근접 가능성 검증",
                "success": "현실적 감축률에서 WAPE 10% 전후 가능성 확인",
            },
        ]
    )

    data_sources = pd.DataFrame(
        [
            {
                "source": "BOK reference / KOSIS 건설수주",
                "local_state": "시도별 건설수주·건축/토목 계열 보유",
                "release_cycle": "월/분기 계열. 속보 적용 전 빈티지 공표시점 확인 필요",
                "model_role": "시간경로",
            },
            {
                "source": "건축HUB 건축 인허가·착공·사용승인",
                "local_state": "고양·포항 및 일부 샘플 보유, 전국 top 도시 수집 필요",
                "release_cycle": "event/월 단위 API. 운영시점 기준 등록일 필터 필요",
                "model_role": "민간건축 공간배분",
            },
            {
                "source": "조달청 나라장터 공사공고",
                "local_state": "2021 일부월·2023 일부기간 raw 변환 보유",
                "release_cycle": "공고 event 단위. 공고일 기준 속보 사용 가능성 높음",
                "model_role": "공공공사 보조",
            },
            {
                "source": "재건축·재개발 정비사업",
                "local_state": "전국 통합 feature 미구축",
                "release_cycle": "지자체/공공포털 수시 또는 월·분기 갱신 가능성. 원천별 확인 필요",
                "model_role": "대형 정비사업 공간충격",
            },
            {
                "source": "SOC/항만/도로/철도 사업",
                "local_state": "일부 부문 후보만 보유",
                "release_cycle": "사업공고·예산·착공/준공 event별 상이",
                "model_role": "토목공사 보정",
            },
        ]
    )

    stage_df.to_csv(OUT / "phase237_collection_stage_frontier.csv", index=False)
    priority.to_csv(OUT / "phase237_priority_city_route_blocks.csv", index=False)
    route_blocks.to_csv(OUT / "phase237_route_blocks.csv", index=False)
    guardrails.to_csv(OUT / "phase237_no_leakage_guardrails.csv", index=False)
    experiment_steps.to_csv(OUT / "phase237_experiment_steps.csv", index=False)
    data_sources.to_csv(OUT / "phase237_construction_data_sources.csv", index=False)

    strict_view = strict_time[
        [
            "available_quarters",
            "adopted_cells",
            "baseline_wape_pct",
            "selected_wape_pct",
            "delta_pp",
            "baseline_over10",
            "selected_over10",
            "policy_pass",
        ]
    ].copy()
    strict_view.rename(columns={"available_quarters": "operating_quarter"}, inplace=True)

    top_priority_view = priority.head(12).copy()

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    report = "\n\n".join(
        [
            "# Phase237 건설업 특화 route 하네스",
            f"생성시각: {now}",
            "## 결론",
            (
                f"- 현재 시군구×건설업 최선 WAPE는 **{current_wape:.3f}%**로 목표 10%를 넘는다.\n"
                f"- 10%에 도달하려면 절대오차를 **{required_reduction:,.1f}억원** 줄여야 하며, 이는 현재 건설업 절대오차의 **{required_reduction_pct:.1f}%**다.\n"
                "- BOK reference식 건축 12분기·토목 24분기 분산은 **시간경로** 개선 후보이고, 시군구 공간배분 개선으로 해석하지 않는다.\n"
                "- 건축HUB·재건축/재개발·PPS·SOC 자료는 **공간배분** 개선 후보이며, staged collection과 rolling 검증 전에는 채택 route로 주장하지 않는다.\n"
                "- 따라서 현재 실험의 안전한 다음 단계는 `top1→top5→top28→top52` 건설업 특화 공간배분 검증이다."
            ),
            "## 1. 현재 성능 병목",
            md_table(
                pd.DataFrame([construction]),
                [
                    ("activity", "업종"),
                    ("rows", "셀"),
                    ("actual_sum_eok", "실제합_억원"),
                    ("abs_error_sum_eok", "절대오차_억원"),
                    ("wape_pct", "WAPE_%"),
                    ("over10_cells", "10%초과"),
                    ("over20_cells", "20%초과"),
                    ("scenario", "현재 최선 시나리오"),
                ],
            ),
            "## 2. Reference 방식의 제한 채택 범위",
            "BOK식 건축/토목 수주 분산은 광역시도 건설업의 분기 시간경로에만 쓴다.",
            md_table(
                strict_view,
                [
                    ("operating_quarter", "운영분기"),
                    ("adopted_cells", "BOK적용셀"),
                    ("baseline_wape_pct", "기준WAPE_%"),
                    ("selected_wape_pct", "선택WAPE_%"),
                    ("delta_pp", "변화_pp"),
                    ("baseline_over10", "기준10%초과"),
                    ("selected_over10", "선택10%초과"),
                    ("policy_pass", "통과"),
                ],
            ),
            "## 3. 수집 단계 frontier",
            md_table(
                stage_df,
                [
                    ("stage", "단계"),
                    ("cities", "시군구"),
                    ("legal_dong_requests", "법정동요청"),
                    ("captured_error_eok", "포착오차_억원"),
                    ("captured_error_share_pct", "포착오차_%"),
                    ("oracle_wape_75pct_reduction", "75%감축가정_WAPE_%"),
                    ("decision", "용도"),
                ],
            ),
            "## 4. 오차 상위 시군구와 필요한 자료 블록",
            md_table(
                top_priority_view,
                [
                    ("priority_rank", "순위"),
                    ("province_full", "시도"),
                    ("city", "시군구"),
                    ("actual_sum_eok", "실제합_억원"),
                    ("abs_error_sum_eok", "절대오차_억원"),
                    ("wape_pct", "WAPE_%"),
                    ("active_legal_dong_requests", "법정동요청"),
                    ("route_type", "지역유형"),
                    ("required_blocks", "우선자료"),
                ],
            ),
            "## 5. route 블록",
            md_table(
                route_blocks,
                [
                    ("block", "블록"),
                    ("role", "역할"),
                    ("data", "자료"),
                    ("use_for", "사용처"),
                    ("status", "상태"),
                ],
            ),
            "## 6. 누수 방지 및 채택 guardrail",
            md_table(guardrails, [("rule", "규칙"), ("detail", "내용")]),
            "## 7. 실험 순서",
            md_table(
                experiment_steps,
                [
                    ("step", "순서"),
                    ("name", "실험"),
                    ("scope", "범위"),
                    ("purpose", "목적"),
                    ("success", "성공 기준"),
                ],
            ),
            "## 8. 자료 출처·공표주기 기록",
            md_table(
                data_sources,
                [
                    ("source", "자료"),
                    ("local_state", "현재 로컬 상태"),
                    ("release_cycle", "공표주기/시점 처리"),
                    ("model_role", "모형 역할"),
                ],
            ),
            "## 9. 과학자·평가관 검증 반영",
            (
                "- 과학자 검토: 건설업은 특화 route 분리가 정합적이며, top1→top5→top28→top52 단계검증이 필요하다.\n"
                "- 평가관 검토: BOK 시간경로 개선과 시군구 공간배분 개선을 분리해야 하며, 현재 증거로는 건설업 WAPE 10% 달성을 주장하면 안 된다.\n"
                "- 반영: 본 산출물은 route 채택 보고서가 아니라, 다음 성능개선 실험을 실행하기 위한 하네스와 guardrail이다."
            ),
            "## 산출 파일",
            (
                f"- `{OUT.relative_to(ROOT)}/phase237_collection_stage_frontier.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase237_priority_city_route_blocks.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase237_route_blocks.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase237_no_leakage_guardrails.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase237_experiment_steps.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase237_construction_data_sources.csv`"
            ),
        ]
    )

    REPORT.write_text(report + "\n", encoding="utf-8")
    NATIONWIDE_NOTE.write_text(report + "\n", encoding="utf-8")
    print(REPORT)
    print(NATIONWIDE_NOTE)


if __name__ == "__main__":
    main()
