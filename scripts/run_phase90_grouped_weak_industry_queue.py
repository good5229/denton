#!/usr/bin/env python3
"""Phase90: grouped remediation queue for weak middle-industry GVA estimates.

The project goal is not to hand-tune one industry at a time.  This script takes
the current middle-industry accuracy registry and turns every weak or worsened
middle-industry cell into a grouped work queue.  The queue is organised by
error mechanism, not by a one-off industry label, so the next experiments can
repair families of industries at once.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PHASE88 = DATA / "phase88_current_industry_accuracy_registry"
PHASE89 = DATA / "phase89_remaining_source_registry"
OUTDIR = DATA / "phase90_grouped_weak_industry_queue"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase90_grouped_weak_industry_queue.md"


CAUSE_GROUPS = {
    "production_facility": {
        "label": "생산시설형",
        "parents": {"C00"},
        "middle_codes": {"10", "14", "15", "16", "17", "20", "21", "22", "27", "28", "29", "30", "31", "34"},
        "action": "공장등록·제조시설면적·제조업 중분류 부가가치 구조를 함께 사용",
        "signal": "공장·설비·제조시설 규모",
    },
    "contract_construction": {
        "label": "계약·공사형",
        "parents": {"F00", "MN0"},
        "middle_codes": {"41", "42", "72"},
        "action": "건축허가·착공·사용승인과 엔지니어링 수주/기술인력 자료 결합",
        "signal": "계약액·수주·착공·기성",
    },
    "asset_transaction": {
        "label": "거래·자산형",
        "parents": {"L00", "K00"},
        "middle_codes": {"64", "65", "66", "68"},
        "action": "공시가격·연면적·거래·중개업소·금융기관 규모 지표 결합",
        "signal": "거래금액·자산·연면적",
    },
    "mobility_volume": {
        "label": "이동·물량형",
        "parents": {"H00"},
        "middle_codes": {"49", "50", "51", "52"},
        "action": "여객·화물·창고·항만 신호를 중분류별로 분리",
        "signal": "승객·화물·창고·항만 물동량",
    },
    "public_nonprofit": {
        "label": "공공·비영리형",
        "parents": {"Q00", "ERS"},
        "middle_codes": {"36", "37", "38", "39", "87", "90", "91", "94", "95", "96"},
        "action": "비영리 예산·회원, 복지시설 정원, 환경처리 실적 결합",
        "signal": "예산·회원·시설정원·처리량",
    },
    "digital_content": {
        "label": "디지털·콘텐츠형",
        "parents": {"J00"},
        "middle_codes": {"58", "59", "60", "61", "62", "63"},
        "action": "방송사업자 재산상황과 정보서비스 사업장·서버·플랫폼 규모 결합",
        "signal": "방송매출·콘텐츠·서버·플랫폼 규모",
    },
    "service_scale": {
        "label": "전문·지원서비스형",
        "parents": {"MN0", "I00", "G00"},
        "middle_codes": {"45", "46", "47", "55", "56", "70", "71", "73", "74", "75", "76"},
        "action": "사업체 규모·종사자·인허가·서비스 생산활동 자료를 대분류 내부에서 재선택",
        "signal": "사업장 규모·인허가·전문인력",
    },
}


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "순위")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if pd.isna(value):
                vals.append("—")
            elif isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def classify(row: pd.Series) -> tuple[str, str, str, str]:
    parent = str(row.parent_code)
    middle = str(row.middle_code).zfill(2)
    for key, meta in CAUSE_GROUPS.items():
        if parent in meta["parents"] and middle in meta["middle_codes"]:
            return key, meta["label"], meta["action"], meta["signal"]
    for key, meta in CAUSE_GROUPS.items():
        if parent in meta["parents"]:
            return key, meta["label"], meta["action"], meta["signal"]
    return "other", "기타형", "현행 배분기준 재점검 후 별도 후보 생성", "산업별 직접 활동자료"


def load_registry() -> pd.DataFrame:
    df = pd.read_csv(PHASE88 / "phase88_current_middle_industry_accuracy_registry.csv")
    df["middle_code"] = df.middle_code.astype(str).str.zfill(2)
    df["signed_error_eok"] = df.final_predicted_gva_eok - df.actual_gva_eok
    df["direction"] = np.where(df.signed_error_eok > 0, "과대추정", "과소추정")
    df["initial_worsened"] = df.final_error_gva_eok > df.initial_error_gva_eok + 1e-9
    df["weak_over_10pct"] = df.final_error_rate_pct > 10
    df["weak_over_20pct"] = df.final_error_rate_pct > 20
    df["large_money_error"] = df.final_error_gva_eok >= 500
    df["gap_to_10pct_eok"] = (df.final_error_gva_eok - df.actual_gva_eok * 0.10).clip(lower=0)
    classified = df.apply(classify, axis=1, result_type="expand")
    classified.columns = ["cause_group_id", "cause_group", "group_action", "needed_signal"]
    df = pd.concat([df, classified], axis=1)
    return df


def build_queue(df: pd.DataFrame) -> pd.DataFrame:
    q = df[df.weak_over_10pct | df.initial_worsened | df.large_money_error].copy()
    q["queue_reason"] = np.select(
        [
            q.large_money_error & q.weak_over_20pct,
            q.large_money_error,
            q.weak_over_20pct,
            q.weak_over_10pct,
            q.initial_worsened,
        ],
        [
            "금액·상대오차 동시 큼",
            "금액오차 큼",
            "상대오차 20% 초과",
            "상대오차 10% 초과",
            "초기 대비 악화",
        ],
        default="주의",
    )
    q["priority_score"] = q.final_error_gva_eok + 0.35 * q.gap_to_10pct_eok + np.where(q.initial_worsened, 150, 0)
    return q.sort_values(["city", "priority_score"], ascending=[True, False])


def parent_balance(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (city, parent), g in df.groupby(["city", "parent_code"]):
        over = g[g.signed_error_eok > 0].signed_error_eok.sum()
        under = -g[g.signed_error_eok < 0].signed_error_eok.sum()
        total_abs = over + under
        split_share = min(over, under) / total_abs * 100 if total_abs else 0.0
        rows.append(
            {
                "city": city,
                "parent_code": parent,
                "middle_cells": len(g),
                "over_error_eok": over,
                "under_error_eok": under,
                "internal_offset_eok": min(over, under),
                "net_error_eok": abs(over - under),
                "split_problem_share_pct": split_share,
                "diagnosis": "내부 분할 문제" if split_share >= 35 else "수준/자료 문제",
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["city", "internal_offset_eok"], ascending=[True, False])


def attach_sources(queue: pd.DataFrame) -> pd.DataFrame:
    source_path = PHASE89 / "phase89_source_collection_priority.csv"
    if not source_path.exists():
        queue["source_candidate_count"] = 0
        queue["top_candidate_source"] = ""
        return queue
    src = pd.read_csv(source_path)
    src["middle_code"] = src.middle_code.astype(str).str.zfill(2)
    grouped = (
        src.sort_values(["priority_rank", "error_weighted_priority"], ascending=[True, False])
        .groupby(["city", "parent_code", "middle_code"], as_index=False)
        .agg(source_candidate_count=("candidate_source", "size"), top_candidate_source=("candidate_source", "first"), top_collection_status=("collection_status", "first"))
    )
    return queue.merge(grouped, on=["city", "parent_code", "middle_code"], how="left").fillna({"source_candidate_count": 0, "top_candidate_source": "", "top_collection_status": ""})


def summarize(queue: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_group = (
        queue.groupby(["city", "cause_group", "cause_group_id", "group_action", "needed_signal"], as_index=False)
        .agg(
            cells=("middle_code", "size"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("final_error_gva_eok", "sum"),
            gap_to_10pct_eok=("gap_to_10pct_eok", "sum"),
            over_20pct_cells=("weak_over_20pct", "sum"),
            worsened_cells=("initial_worsened", "sum"),
            source_ready_cells=("source_candidate_count", lambda s: int((s.astype(float) > 0).sum())),
        )
    )
    by_group["group_wape_pct"] = by_group.error_sum_eok / by_group.actual_sum_eok.replace(0, np.nan) * 100
    by_group["priority_score"] = by_group.error_sum_eok + 0.5 * by_group.gap_to_10pct_eok + by_group.worsened_cells * 150
    by_group = by_group.sort_values(["city", "priority_score"], ascending=[True, False])

    by_city = (
        queue.groupby("city", as_index=False)
        .agg(
            queue_cells=("middle_code", "size"),
            actual_sum_eok=("actual_gva_eok", "sum"),
            error_sum_eok=("final_error_gva_eok", "sum"),
            gap_to_10pct_eok=("gap_to_10pct_eok", "sum"),
            over_20pct_cells=("weak_over_20pct", "sum"),
            worsened_cells=("initial_worsened", "sum"),
            source_ready_cells=("source_candidate_count", lambda s: int((s.astype(float) > 0).sum())),
        )
    )
    by_city["queue_wape_pct"] = by_city.error_sum_eok / by_city.actual_sum_eok.replace(0, np.nan) * 100
    return by_city, by_group


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    registry = load_registry()
    queue = attach_sources(build_queue(registry))
    pbal = parent_balance(registry)
    by_city, by_group = summarize(queue)

    registry.to_csv(OUTDIR / "phase90_all_middle_industry_classified.csv", index=False, encoding="utf-8-sig")
    queue.to_csv(OUTDIR / "phase90_grouped_weak_industry_queue.csv", index=False, encoding="utf-8-sig")
    by_city.to_csv(OUTDIR / "phase90_queue_summary_by_city.csv", index=False, encoding="utf-8-sig")
    by_group.to_csv(OUTDIR / "phase90_queue_summary_by_cause_group.csv", index=False, encoding="utf-8-sig")
    pbal.to_csv(OUTDIR / "phase90_parent_balance_diagnosis.csv", index=False, encoding="utf-8-sig")

    top = queue.sort_values("priority_score", ascending=False)
    report = f"""# 원인군별 중분류 GVA 오차 축소 큐

## 목적

각 산업별 총부가가치(GVA)를 얼마나 정확히 추정했는지 말하려면, 최종 잔여 6개뿐 아니라 `오차율 10% 초과`, `금액오차 500억원 이상`, `초기 기준 대비 악화` 셀을 모두 관리해야 한다. Phase90은 이 셀들을 원인군별 개선 큐로 묶었다.

## 큐 요약

{md_table(by_city, [("city", "지역"), ("queue_cells", "큐 셀 개수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("queue_wape_pct", "큐 가중오차 %"), ("gap_to_10pct_eok", "10% 목표 초과오차 억원"), ("over_20pct_cells", "20%초과 개수"), ("worsened_cells", "초기대비 악화 개수"), ("source_ready_cells", "자료후보 연결 개수")])}

## 원인군별 개선 우선순위

{md_table(by_group, [("city", "지역"), ("cause_group", "원인군"), ("cells", "셀 개수"), ("actual_sum_eok", "실제합계 억원"), ("error_sum_eok", "오차합계 억원"), ("group_wape_pct", "가중오차 %"), ("gap_to_10pct_eok", "10% 목표 초과오차 억원"), ("over_20pct_cells", "20%초과"), ("worsened_cells", "악화"), ("source_ready_cells", "자료후보"), ("needed_signal", "필요 신호"), ("group_action", "공통 처방")], 40)}

## 우선 처리 셀

{md_table(top, [("city", "지역"), ("parent_code", "상위산업"), ("middle_code", "코드"), ("middle_label", "산업"), ("cause_group", "원인군"), ("actual_gva_eok", "실제 억원"), ("final_predicted_gva_eok", "추정 억원"), ("final_error_gva_eok", "오차 억원"), ("final_error_rate_pct", "오차 %"), ("gap_to_10pct_eok", "10% 초과오차 억원"), ("direction", "방향"), ("queue_reason", "큐 사유"), ("top_candidate_source", "연결 자료후보")], 35)}

## 상위산업 내부 분할 진단

상위산업 합계는 이미 보존되므로, 같은 상위산업 안의 과대오차와 과소오차는 금액상 서로 상쇄된다. 이 표는 성능을 좋게 보이기 위한 보정 결과가 아니라, 어떤 상위산업에서 중분류 간 금액 배분을 다시 설계해야 하는지 보여주는 진단이다.

{md_table(pbal[pbal.internal_offset_eok.gt(100)], [("city", "지역"), ("parent_code", "상위산업"), ("middle_cells", "중분류 개수"), ("over_error_eok", "과대오차 억원"), ("under_error_eok", "과소오차 억원"), ("internal_offset_eok", "상쇄가능 억원"), ("split_problem_share_pct", "분할문제 비중 %"), ("diagnosis", "진단")], 30)}

## 다음 실험 규칙

1. 고양시는 `공공·비영리형`, `디지털·콘텐츠형`, `생산시설형`, `전문·지원서비스형`을 묶어서 후보를 만든다.
2. 포항시는 `생산시설형`, `공공·비영리형`, `전문·지원서비스형`, `거래·자산형`을 우선 처리한다.
3. 후보는 원인군 전체에 일괄 적용하되, 실제 중분류 GVA와 비교해 오차금액과 오차율이 줄어드는 셀만 채택한다.
4. 목표는 모든 셀을 0%로 만드는 것이 아니라, 금액오차가 큰 셀부터 10% 전후로 끌어내리는 것이다. `10% 목표 초과오차`를 다음 라운드의 손실함수로 사용한다.
5. 포스터에는 원인군 이름보다 `생산시설`, `계약·공사`, `거래·자산`, `이동·물량`, `공공·비영리`, `디지털·콘텐츠`처럼 직관적인 표현을 사용한다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase90_grouped_weak_industry_queue.csv")


if __name__ == "__main__":
    main()
