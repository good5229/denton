#!/usr/bin/env python3
"""Phase147 amount-weighted error priority diagnostics.

The user pointed out that high percentage errors in small industries should not
drive the improvement queue as much as modest percentage errors in very large
industries.  This phase turns the Phase145 operational prediction table into a
priority diagnosis based on:

* actual GVA amount share,
* absolute error amount share,
* WAPE by city × vintage × KSIC middle industry.
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
IN = DATA / "phase145_operational_route_decision_registry" / "phase145_selected_operational_predictions.csv"
OUT = DATA / "phase147_amount_weighted_error_priority"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase147_amount_weighted_error_priority.md"


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


def priority_label(r: pd.Series) -> str:
    if r["available_quarters"] == 4:
        return "회계정산"
    if r["error_share_pct"] >= 5 or (r["actual_share_pct"] >= 5 and r["wape_pct"] >= 3):
        return "핵심개선"
    if r["actual_share_pct"] >= 2 or r["error_share_pct"] >= 2:
        return "관리관찰"
    if r["wape_pct"] >= 10 and r["actual_share_pct"] < 1 and r["error_share_pct"] < 1.5:
        return "소액고오차"
    return "저우선순위"


def priority_reason(r: pd.Series) -> str:
    if r["priority_class"] == "핵심개선":
        return "오차금액 기여가 크거나 실제 GVA 비중이 큰 업종"
    if r["priority_class"] == "관리관찰":
        return "금액 또는 오차기여가 중간 이상인 업종"
    if r["priority_class"] == "소액고오차":
        return "%오차는 크지만 실제 금액·오차금액 기여가 작음"
    if r["priority_class"] == "회계정산":
        return "Q4는 연간 회계 회수 단계"
    return "금액·오차기여 모두 낮아 후순위"


def classify_with_params(
    data: pd.DataFrame,
    error_core: float,
    actual_core: float,
    wape_core: float,
    observe_share: float,
    observe_error: float,
    high_wape: float,
    small_share: float,
    small_error: float,
) -> pd.Series:
    """Classify rows under alternative triage thresholds."""

    out = []
    for _, r in data.iterrows():
        if r["error_share_pct"] >= error_core or (
            r["actual_share_pct"] >= actual_core and r["wape_pct"] >= wape_core
        ):
            out.append("핵심개선")
        elif r["actual_share_pct"] >= observe_share or r["error_share_pct"] >= observe_error:
            out.append("관리관찰")
        elif (
            r["wape_pct"] >= high_wape
            and r["actual_share_pct"] < small_share
            and r["error_share_pct"] < small_error
        ):
            out.append("소액고오차")
        else:
            out.append("저우선순위")
    return pd.Series(out, index=data.index)


def main() -> None:
    if not IN.exists():
        raise FileNotFoundError(IN)
    OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN, dtype={"middle_code": str})
    eval_df = df[df["year"].between(2022, 2023) & df["available_quarters"].isin([1, 2, 3])].copy()

    by_middle = (
        eval_df.groupby(
            [
                "city",
                "available_quarters",
                "vintage_label",
                "parent_code",
                "middle_code",
                "middle_label",
                "selected_operational_route",
            ],
            as_index=False,
        )
        .agg(
            actual_sum_eok=("actual_annual_gva_eok", "sum"),
            prediction_sum_eok=("annual_prediction_eok", "sum"),
            error_sum_eok=("annual_error_eok", "sum"),
            years=("year", lambda s: "-".join(map(str, sorted(s.unique())))),
        )
    )
    by_middle["wape_pct"] = np.where(
        by_middle["actual_sum_eok"].gt(0),
        by_middle["error_sum_eok"] / by_middle["actual_sum_eok"] * 100,
        np.nan,
    )
    by_middle["actual_share_pct"] = by_middle.groupby(["city", "available_quarters"])[
        "actual_sum_eok"
    ].transform(lambda s: s / s.sum() * 100)
    by_middle["error_share_pct"] = by_middle.groupby(["city", "available_quarters"])[
        "error_sum_eok"
    ].transform(lambda s: s / s.sum() * 100 if s.sum() else 0)
    by_middle["priority_score"] = (
        by_middle["error_share_pct"] * 0.65
        + by_middle["actual_share_pct"] * 0.30
        + by_middle["wape_pct"].clip(upper=20) * 0.05
    )
    by_middle["priority_class"] = by_middle.apply(priority_label, axis=1)
    by_middle["priority_reason"] = by_middle.apply(priority_reason, axis=1)
    by_middle = by_middle.sort_values(
        ["city", "available_quarters", "priority_score"], ascending=[True, True, False]
    )
    by_middle = by_middle.rename(columns={"annual_error_eok": "annual_abs_error_eok"})

    # Priority queue: top amount-weighted candidates for each city/vintage.
    queue = (
        by_middle[by_middle["priority_class"].isin(["핵심개선", "관리관찰"])]
        .sort_values(["city", "available_quarters", "priority_score"], ascending=[True, True, False])
        .groupby(["city", "available_quarters"], as_index=False)
        .head(10)
        .copy()
    )

    # High percentage errors that should not dominate decisions because their
    # amount share and error contribution are small.
    low_importance_high_pct = by_middle[
        (by_middle["wape_pct"] >= 10)
        & (by_middle["actual_share_pct"] < 1.0)
        & (by_middle["error_share_pct"] < 1.5)
    ].copy()

    # Detect repeated parent-level rates that are more a sign of shared parent
    # seasonal allocation than middle-specific precision.
    repeated = (
        by_middle.assign(wape_round=by_middle["wape_pct"].round(2))
        .groupby(["city", "available_quarters", "parent_code", "wape_round"], as_index=False)
        .agg(
            middle_count=("middle_code", "nunique"),
            actual_sum_eok=("actual_sum_eok", "sum"),
            error_sum_eok=("error_sum_eok", "sum"),
            examples=("middle_label", lambda s: ", ".join(list(s)[:4])),
        )
    )
    repeated = repeated[repeated["middle_count"].ge(5)].sort_values(
        ["city", "available_quarters", "middle_count"], ascending=[True, True, False]
    )

    sensitivity_specs = [
        {
            "scenario": "기준",
            "error_core": 5.0,
            "actual_core": 5.0,
            "wape_core": 3.0,
            "observe_share": 2.0,
            "observe_error": 2.0,
            "high_wape": 10.0,
            "small_share": 1.0,
            "small_error": 1.5,
            "weight_error": 0.65,
            "weight_actual": 0.30,
            "weight_wape": 0.05,
        },
        {
            "scenario": "오차금액 중시",
            "error_core": 4.0,
            "actual_core": 5.0,
            "wape_core": 3.0,
            "observe_share": 2.0,
            "observe_error": 1.5,
            "high_wape": 10.0,
            "small_share": 1.0,
            "small_error": 1.0,
            "weight_error": 0.75,
            "weight_actual": 0.20,
            "weight_wape": 0.05,
        },
        {
            "scenario": "금액규모 중시",
            "error_core": 6.0,
            "actual_core": 4.0,
            "wape_core": 3.0,
            "observe_share": 1.5,
            "observe_error": 2.5,
            "high_wape": 12.0,
            "small_share": 0.8,
            "small_error": 1.5,
            "weight_error": 0.55,
            "weight_actual": 0.40,
            "weight_wape": 0.05,
        },
        {
            "scenario": "고율오차 경계",
            "error_core": 5.0,
            "actual_core": 5.0,
            "wape_core": 2.5,
            "observe_share": 2.0,
            "observe_error": 2.0,
            "high_wape": 8.0,
            "small_share": 1.0,
            "small_error": 1.5,
            "weight_error": 0.60,
            "weight_actual": 0.25,
            "weight_wape": 0.15,
        },
    ]
    sens_rows = []
    for spec in sensitivity_specs:
        tmp = by_middle.copy()
        tmp["scenario_priority_score"] = (
            tmp["error_share_pct"] * spec["weight_error"]
            + tmp["actual_share_pct"] * spec["weight_actual"]
            + tmp["wape_pct"].clip(upper=20) * spec["weight_wape"]
        )
        tmp["scenario_class"] = classify_with_params(
            tmp,
            spec["error_core"],
            spec["actual_core"],
            spec["wape_core"],
            spec["observe_share"],
            spec["observe_error"],
            spec["high_wape"],
            spec["small_share"],
            spec["small_error"],
        )
        for keys, gg in tmp.groupby(["city", "available_quarters", "vintage_label"], sort=False):
            top = gg.sort_values("scenario_priority_score", ascending=False).head(10)
            sens_rows.append(
                {
                    "scenario": spec["scenario"],
                    "city": keys[0],
                    "available_quarters": keys[1],
                    "vintage_label": keys[2],
                    "top10_codes": ", ".join(top["middle_code"].astype(str)),
                    "top10_labels": ", ".join(top["middle_label"].astype(str)),
                    "core_count": int((gg["scenario_class"] == "핵심개선").sum()),
                    "observe_count": int((gg["scenario_class"] == "관리관찰").sum()),
                    "small_high_pct_count": int((gg["scenario_class"] == "소액고오차").sum()),
                }
            )
    sensitivity = pd.DataFrame(sens_rows)

    base_top = sensitivity[sensitivity["scenario"].eq("기준")][
        ["city", "available_quarters", "top10_codes"]
    ].rename(columns={"top10_codes": "base_top10_codes"})
    sensitivity = sensitivity.merge(base_top, on=["city", "available_quarters"], how="left")

    def overlap_ratio(row: pd.Series) -> float:
        a = set(str(row["top10_codes"]).split(", "))
        b = set(str(row["base_top10_codes"]).split(", "))
        return len(a & b) / 10 * 100 if a and b else np.nan

    sensitivity["top10_overlap_with_base_pct"] = sensitivity.apply(overlap_ratio, axis=1)

    summary = (
        by_middle.groupby(["city", "available_quarters", "vintage_label", "priority_class"], as_index=False)
        .agg(
            middle_count=("middle_code", "nunique"),
            actual_sum_eok=("actual_sum_eok", "sum"),
            error_sum_eok=("error_sum_eok", "sum"),
        )
    )
    total_actual = summary.groupby(["city", "available_quarters"])["actual_sum_eok"].transform("sum")
    total_error = summary.groupby(["city", "available_quarters"])["error_sum_eok"].transform("sum")
    summary["actual_share_pct"] = summary["actual_sum_eok"] / total_actual * 100
    summary["error_share_pct"] = np.where(total_error.gt(0), summary["error_sum_eok"] / total_error * 100, 0)
    summary["class_wape_pct"] = np.where(
        summary["actual_sum_eok"].gt(0), summary["error_sum_eok"] / summary["actual_sum_eok"] * 100, np.nan
    )

    # Export machine-readable evidence.
    by_middle.to_csv(OUT / "phase147_middle_priority_all.csv", index=False)
    queue.to_csv(OUT / "phase147_improvement_priority_queue.csv", index=False)
    low_importance_high_pct.to_csv(OUT / "phase147_low_importance_high_pct.csv", index=False)
    repeated.to_csv(OUT / "phase147_repeated_parent_rate_audit.csv", index=False)
    summary.to_csv(OUT / "phase147_priority_class_summary.csv", index=False)
    sensitivity.to_csv(OUT / "phase147_priority_sensitivity.csv", index=False)
    manifest = {
        "phase": "phase147_amount_weighted_error_priority",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "inputs": [
            {
                "path": str(IN.relative_to(ROOT)),
                "bytes": IN.stat().st_size,
                "sha256": file_sha256(IN),
                "row_count": int(len(df)),
                "columns": list(df.columns),
            }
        ],
        "outputs": [
            "phase147_middle_priority_all.csv",
            "phase147_improvement_priority_queue.csv",
            "phase147_low_importance_high_pct.csv",
            "phase147_repeated_parent_rate_audit.csv",
            "phase147_priority_class_summary.csv",
            "phase147_priority_sensitivity.csv",
        ],
        "notes": [
            "2022-2023 retrospective backtest using Phase145 selected operational predictions.",
            "Q4 accounting recovery excluded from priority ranking.",
            "Thresholds are policy triage rules, not statistically optimized cutoffs.",
        ],
    }
    (OUT / "execution_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    def view(df: pd.DataFrame, city: str, q: int, n: int = 8) -> pd.DataFrame:
        cols = [
            "middle_code",
            "middle_label",
            "actual_sum_eok",
            "prediction_sum_eok",
            "error_sum_eok",
            "wape_pct",
            "actual_share_pct",
            "error_share_pct",
            "priority_class",
        ]
        return df[(df.city == city) & (df.available_quarters == q)][cols].head(n)

    goyang_q1 = view(queue, "고양시", 1, 10)
    goyang_q2 = view(queue, "고양시", 2, 8)
    goyang_q3 = view(queue, "고양시", 3, 8)
    pohang_q1 = view(queue, "포항시", 1, 8)
    pohang_q2 = view(queue, "포항시", 2, 8)
    pohang_q3 = view(queue, "포항시", 3, 8)

    low_goyang = low_importance_high_pct[low_importance_high_pct.city.eq("고양시")][
        [
            "vintage_label",
            "middle_code",
            "middle_label",
            "actual_sum_eok",
            "error_sum_eok",
            "wape_pct",
            "actual_share_pct",
            "error_share_pct",
        ]
    ].head(12)

    repeated_view = repeated[
        ["city", "available_quarters", "parent_code", "wape_round", "middle_count", "actual_sum_eok", "error_sum_eok", "examples"]
    ].head(12)

    sensitivity_view = sensitivity[
        sensitivity["available_quarters"].eq(1)
        & sensitivity["city"].isin(["고양시", "포항시"])
        & ~sensitivity["scenario"].eq("기준")
    ][
        [
            "scenario",
            "city",
            "vintage_label",
            "top10_overlap_with_base_pct",
            "core_count",
            "observe_count",
            "small_high_pct_count",
            "top10_labels",
        ]
    ]

    class_summary_view = summary[
        summary["priority_class"].isin(["핵심개선", "관리관찰", "소액고오차"])
    ][
        [
            "city",
            "vintage_label",
            "priority_class",
            "middle_count",
            "actual_sum_eok",
            "error_sum_eok",
            "actual_share_pct",
            "error_share_pct",
            "class_wape_pct",
        ]
    ].sort_values(["city", "vintage_label", "priority_class"])

    report = f"""# Phase147 금액가중 중분류 오차 우선순위 진단

## 목적

이번 단계는 고양시·포항시 GVA 예측에서 **오차율(%)만 보고 개선대상을 고르는 문제**를 줄이기 위한 진단이다. 실제 GVA 금액이 작은 업종은 % 오차가 크게 보일 수 있지만 정책·경제적 중요도는 낮을 수 있다. 반대로 GVA 금액이 큰 업종은 % 오차가 작아도 오차금액이 커져 전체 추정 신뢰도를 크게 흔든다.

따라서 Phase145 운영 예측표를 기준으로 2022~2023 기간의 중분류별 `실제 GVA`, `예측 GVA`, `절대오차`, `WAPE`, `실제금액 비중`, `오차금액 기여도`를 함께 계산했다. Q4는 회계 정산이므로 개선 우선순위 산정에서 제외했다.

## 진단 기준

| 구분 | 기준 | 해석 |
| --- | --- | --- |
| 핵심개선 | 오차금액 기여도 5% 이상 또는 실제 GVA 비중 5% 이상이면서 WAPE 3% 이상 | 성능 개선의 최우선 대상 |
| 관리관찰 | 실제 GVA 비중 2% 이상 또는 오차금액 기여도 2% 이상 | 포스터·보고서에서 계속 추적 |
| 소액고오차 | WAPE 10% 이상이지만 실제 GVA 비중 1% 미만·오차기여 1.5% 미만 | % 오차는 크지만 중요도는 낮음 |
| 저우선순위 | 위 조건 외 | 현재 운영에서는 후순위 |

우선순위 점수는 `오차금액 기여도 65% + 실제금액 비중 30% + capped WAPE 5%`로 계산했다. 즉 사용자가 지적한 것처럼 **금액 규모와 오차금액을 % 오차보다 훨씬 크게 반영**했다.

이 기준은 통계적으로 최적화된 절단값이 아니라 현재 운영을 위한 **정책적 triage rule**이다. 따라서 특정 업종을 “좋다/나쁘다”로 확정하는 기준이 아니라, 다음 데이터 보강과 검증을 어디부터 해야 하는지 정하는 우선순위표로 해석해야 한다. 또한 소액고오차는 관리관찰 조건보다 후순위로 판정한다. 즉 % 오차가 높더라도 실제금액 또는 오차기여가 관리관찰 기준을 넘으면 소액고오차가 아니라 관리관찰로 분류한다.

## 우선순위 분포

{md_table(class_summary_view)}

## 고양시 개선 우선순위

### 1분기 자료만 있을 때

{md_table(goyang_q1)}

### 1~2분기 자료가 있을 때

{md_table(goyang_q2)}

### 1~3분기 자료가 있을 때

{md_table(goyang_q3)}

고양시는 Q1 단계에서 **부동산업**이 실제 GVA 비중과 오차기여 모두 가장 크다. 소매업, 전문직별 공사업, 교육 서비스업, 보건업은 % 오차가 아주 크지는 않더라도 금액 규모가 커서 관리대상이다. 음식점 및 주점업, 항공 운송업, 보험 및 연금업은 금액과 % 오차가 동시에 무시하기 어렵다.

## 포항시 비교 우선순위

### 1분기 자료만 있을 때

{md_table(pohang_q1)}

### 1~2분기 자료가 있을 때

{md_table(pohang_q2)}

### 1~3분기 자료가 있을 때

{md_table(pohang_q3)}

포항시는 부동산업, 전기·가스·증기 및 공기조절 공급업, 1차 금속 제조업, 전문직별 공사업이 금액가중 관점에서 중요하다. 특히 1차 금속 제조업은 % 오차가 낮아 보여도 실제 GVA 비중이 커서 반드시 별도 관리해야 한다.

## % 오차는 크지만 우선순위가 낮은 고양 업종

{md_table(low_goyang)}

위 표의 업종들은 % 오차가 눈에 띄지만 실제 GVA 비중과 전체 오차기여가 작다. 따라서 포스터나 의사결정 자료에서 “예측 취약”으로 과도하게 부각하면 전체 프로젝트 성능이 실제보다 나빠 보일 수 있다.

다만 개별 업종이 후순위라는 뜻이지, 소액고오차 묶음 전체를 무시해도 된다는 뜻은 아니다. 고양 Q1에서는 소액고오차 묶음의 실제금액 비중이 3.73%, 오차기여가 9.65%이므로 **개별 업종은 후순위, 묶음 총량은 별도 모니터링**이 적절하다.

## 기준 민감도

{md_table(sensitivity_view)}

기준을 약간 바꿔도 Q1 상위 10개 업종은 상당 부분 겹친다. 그러나 핵심개선/관리관찰/소액고오차의 개수는 변할 수 있으므로, 이 분류는 고정된 통계적 진단명이 아니라 운영상 우선순위 라벨로만 써야 한다.

## 반복 오차율 감사

{md_table(repeated_view)}

동일한 parent 내 여러 중분류가 같은 WAPE를 보이는 경우가 있다. 이는 중분류별 정보가 충분히 독립적으로 들어간 결과라기보다 **상위산업 단위의 계절/배분율이 여러 중분류에 공통 적용된 흔적**일 가능성이 크다. 이 경우 해당 중분류의 % 오차를 “중분류별로 정밀하게 맞춘 성능”이라고 주장하면 안 된다.

## 판정

1. 고양시 개선의 첫 번째 대상은 “오차율이 가장 큰 업종”이 아니라 **오차금액 기여가 큰 대형 업종**이어야 한다.
2. 고양시는 부동산업, 소매업, 전문직별 공사업, 음식점 및 주점업, 항공 운송업, 보험 및 연금업이 우선 개선 후보로 남는다.
3. 일부 제조 중분류는 같은 오차율이 반복되므로 중분류 독립 예측이라기보다 parent-level 배분의 결과로 해석해야 한다.
4. 포스터에서는 “양호/취약”처럼 단순 이분법을 쓰기보다 **금액가중 핵심관리 / 관리관찰 / 소액고오차**로 표현하는 편이 더 정확하다.
5. 다음 개선은 부동산·건설·소매·음식·운수처럼 금액 또는 오차기여가 큰 업종에 직접 활동지표를 붙여 시간분리 holdout에서만 채택해야 한다.
6. Phase145 기준 성능은 2022~2023 두 개 holdout 연도에 대한 제한적 평가다. 전국 일반화나 공식통계 대체 주장은 아직 금지한다.

## 다음 작업 제안

1. 고양시 부동산업에 대해 실거래·건축물·공시가격 계열 자료의 공표시점 적격성을 다시 분리한다.
2. 소매업·음식점업은 LOCALDATA/생활업종/카드 대체 공개자료 중 속보 사용 가능한 자료만 추려 후보를 만든다.
3. 항공 운송업처럼 지역 실제 활동과 행정동 배분근거가 약한 업종은 공항 접근성·교통량·사업체 구조자료의 설명력을 별도 검증한다.
4. 반복 오차율이 나타나는 제조 중분류는 중분류별 독립 활동자료가 없으면 포스터에서 “제조업 공통 배분군”으로 묶어 표현한다.
5. Phase132에서 `UNKNOWN` 또는 공표시점 확인 필요로 분류된 자료를 제외한 strict flash 전용 성능표를 별도 산출한다.
"""

    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    for name in [
        "phase147_middle_priority_all.csv",
        "phase147_improvement_priority_queue.csv",
        "phase147_low_importance_high_pct.csv",
        "phase147_repeated_parent_rate_audit.csv",
        "phase147_priority_class_summary.csv",
        "phase147_priority_sensitivity.csv",
    ]:
        print(f"Wrote {(OUT / name).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
