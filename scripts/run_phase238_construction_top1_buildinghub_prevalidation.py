"""Phase238 top1 BuildingHUB prevalidation for construction.

This is a prevalidation step, not a nationwide model adoption.  It audits the
newly collected Pyeongtaek BuildingHUB events and tests whether simple,
pre-registered activity-ratio adjustments can explain the remaining
sigungu-level construction error.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/phase238_construction_top1_buildinghub_prevalidation"
REPORT = ROOT / "reports/partial_statistics_estimation_phase238_construction_top1_buildinghub_prevalidation.md"
EVENTS = ROOT / "data/processed/buildinghub_priority_events_phase238_top1_pyeongtaek.csv"
MANIFEST = ROOT / "data/processed/buildinghub_priority_events_manifest_phase238_top1_pyeongtaek.csv"
AUDIT = ROOT / "nationwide/outputs/annual_sigungu_activity_error_audit.csv"


def fmt(x: object, digits: int = 3) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (float, np.floating)):
        return f"{x:,.{digits}f}"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}"
    return str(x)


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    lines = [
        "| " + " | ".join(label for _, label in cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            vals.append(fmt(row.get(key, "")))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def event_features(events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    event_specs = [
        ("permit", "permit_date"),
        ("start", "start_date"),
        ("approval", "approval_date"),
    ]
    use_groups = ["전체", "산업·창고", "상업·업무", "주거"]
    for event_name, col in event_specs:
        d = events.dropna(subset=[col]).copy()
        d["year"] = d[col].dt.year
        d = d[(d["year"] >= 2019) & (d["year"] <= 2023)]
        for year, gy in d.groupby("year"):
            for group in use_groups:
                g = gy if group == "전체" else gy[gy["use_group"].eq(group)]
                rows.append(
                    {
                        "feature": f"{event_name}_{group}_area",
                        "event": event_name,
                        "use_group": group,
                        "year": int(year),
                        "rows": int(len(g)),
                        "area": float(g["total_floor_area"].sum()),
                        "site_area": float(g["site_area"].sum()),
                    }
                )
                rows.append(
                    {
                        "feature": f"{event_name}_{group}_count",
                        "event": event_name,
                        "use_group": group,
                        "year": int(year),
                        "rows": int(len(g)),
                        "area": float(len(g)),
                        "site_area": float(g["site_area"].sum()),
                    }
                )
    return pd.DataFrame(rows)


def build_candidates(base: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    wide = features.pivot_table(index="year", columns="feature", values="area", aggfunc="sum").sort_index()
    years = [2021, 2022, 2023]
    candidate_rows: list[dict[str, object]] = []
    alphas = [0.1, 0.2, 0.3, 0.4, 0.5]
    caps = [0.2, 0.3, 0.5]
    selected_features = [
        "permit_전체_area",
        "permit_산업·창고_area",
        "start_전체_area",
        "start_산업·창고_area",
        "approval_전체_area",
        "approval_산업·창고_area",
    ]
    for _, b in base.iterrows():
        y = int(b["year"])
        pred0 = float(b["predicted_eok"])
        actual = float(b["actual_eok"])
        candidate_rows.append(
            {
                "candidate": "baseline",
                "feature": "",
                "alpha": 0.0,
                "cap": 0.0,
                "year": y,
                "predicted_eok": pred0,
                "actual_eok": actual,
                "abs_error_eok": abs(pred0 - actual),
                "ape_pct": abs(pred0 - actual) / actual * 100,
                "adjustment_ratio": 1.0,
                "feature_ratio": np.nan,
            }
        )
        prior_y = y - 1
        if y not in wide.index or prior_y not in wide.index:
            continue
        for feature in selected_features:
            if feature not in wide.columns:
                continue
            cur = float(wide.loc[y, feature] or 0.0)
            prev = float(wide.loc[prior_y, feature] or 0.0)
            if cur <= 0 or prev <= 0:
                continue
            raw_ratio = cur / prev
            change = raw_ratio - 1.0
            for cap in caps:
                clipped = float(np.clip(change, -cap, cap))
                for alpha in alphas:
                    adjustment = max(0.05, 1.0 + alpha * clipped)
                    pred = pred0 * adjustment
                    candidate_rows.append(
                        {
                            "candidate": f"{feature}_alpha{alpha:.1f}_cap{cap:.1f}",
                            "feature": feature,
                            "alpha": alpha,
                            "cap": cap,
                            "year": y,
                            "predicted_eok": pred,
                            "actual_eok": actual,
                            "abs_error_eok": abs(pred - actual),
                            "ape_pct": abs(pred - actual) / actual * 100,
                            "adjustment_ratio": adjustment,
                            "feature_ratio": raw_ratio,
                        }
                    )
    return pd.DataFrame(candidate_rows)


def choose_rolling(candidates: pd.DataFrame, base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Prior-selected diagnostic: choose a route for year y using all prior
    # years.  This can still fail out-of-sample, so adoption requires a
    # separate evaluation guardrail after the fact.
    choices: list[dict[str, object]] = []
    preds: list[pd.Series] = []
    for y in [2021, 2022, 2023]:
        baseline = candidates[(candidates["year"].eq(y)) & (candidates["candidate"].eq("baseline"))].iloc[0]
        if y == 2021:
            chosen = baseline.copy()
            reason = "first_year_fallback"
        else:
            prior_years = [yy for yy in [2021, 2022, 2023] if yy < y]
            prior = candidates[candidates["year"].isin(prior_years)].copy()
            piv = prior.pivot_table(index="candidate", values="abs_error_eok", aggfunc="sum")
            base_err = float(piv.loc["baseline", "abs_error_eok"])
            # Require no worse than baseline on every available prior year and
            # lower total prior error; ties go to the smaller alpha/cap.
            ok = []
            for cand, g in prior.groupby("candidate"):
                if cand == "baseline" or len(g) < len(prior_years):
                    continue
                merged = g[["year", "abs_error_eok"]].merge(
                    prior[prior["candidate"].eq("baseline")][["year", "abs_error_eok"]],
                    on="year",
                    suffixes=("_candidate", "_baseline"),
                )
                no_worse_each = bool((merged["abs_error_eok_candidate"] <= merged["abs_error_eok_baseline"]).all())
                total = float(g["abs_error_eok"].sum())
                if no_worse_each and total < base_err:
                    meta = g.iloc[0]
                    ok.append((total, float(meta["alpha"]), float(meta["cap"]), cand))
            if ok:
                ok.sort()
                chosen_name = ok[0][3]
                chosen = candidates[(candidates["year"].eq(y)) & (candidates["candidate"].eq(chosen_name))].iloc[0].copy()
                reason = "strict_prior_no_worse"
            else:
                chosen = baseline.copy()
                reason = "no_prior_candidate_passed"
        choices.append({"year": y, "chosen_candidate": chosen["candidate"], "reason": reason})
        preds.append(chosen)
    return pd.DataFrame(choices), pd.DataFrame(preds)


def choose_diagnostic_2023(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Diagnostic only: choose the smallest-alpha candidate that brings 2022 APE
    # below 10%, then evaluate 2023.  This is intentionally not an adopted
    # route because it uses a single prior problem year.
    prior = candidates[candidates["year"].eq(2022)].copy()
    viable = prior[(prior["candidate"].ne("baseline")) & (prior["ape_pct"] <= 10.0)].copy()
    if viable.empty:
        chosen_name = "baseline"
        reason = "no_candidate_brings_2022_under10"
    else:
        viable = viable.sort_values(["alpha", "cap", "ape_pct", "candidate"])
        chosen_name = str(viable.iloc[0]["candidate"])
        reason = "smallest_alpha_candidate_with_2022_ape_under10"
    pred_rows = []
    for y in [2021, 2022, 2023]:
        if y < 2023:
            row = candidates[(candidates["year"].eq(y)) & (candidates["candidate"].eq("baseline"))].iloc[0]
        else:
            row = candidates[(candidates["year"].eq(y)) & (candidates["candidate"].eq(chosen_name))].iloc[0]
        pred_rows.append(row)
    pred = pd.DataFrame(pred_rows)
    choice = pd.DataFrame([{"evaluation_year": 2023, "chosen_candidate": chosen_name, "selection_basis": reason}])
    return choice, pred


def metrics(preds: pd.DataFrame, label: str) -> dict[str, object]:
    actual_sum = float(preds["actual_eok"].sum())
    abs_sum = float(preds["abs_error_eok"].sum())
    return {
        "policy": label,
        "years": int(preds["year"].nunique()),
        "actual_sum_eok": actual_sum,
        "abs_error_sum_eok": abs_sum,
        "wape_pct": abs_sum / actual_sum * 100,
        "over10_years": int((preds["ape_pct"] > 10).sum()),
        "max_ape_pct": float(preds["ape_pct"].max()),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(EVENTS, parse_dates=["permit_date", "start_date", "approval_date", "created_at"])
    manifest = pd.read_csv(MANIFEST)
    audit = pd.read_csv(AUDIT)
    base = audit[(audit["city"].eq("평택시")) & (audit["activity"].eq("건설업")) & (audit["year"].between(2021, 2023))].copy()

    features = event_features(events)
    candidates = build_candidates(base, features)
    prior_choices, prior_preds = choose_rolling(candidates, base)
    diag_choice, diag_preds = choose_diagnostic_2023(candidates)

    baseline_preds = candidates[candidates["candidate"].eq("baseline") & candidates["year"].between(2021, 2023)].copy()
    prior_summary = metrics(prior_preds, "prior_selected_diagnostic")
    baseline_summary = metrics(baseline_preds, "baseline")
    prior_pass = (
        prior_summary["wape_pct"] <= baseline_summary["wape_pct"]
        and prior_summary["over10_years"] <= baseline_summary["over10_years"]
        and prior_summary["max_ape_pct"] <= baseline_summary["max_ape_pct"]
    )
    guarded_preds = prior_preds.copy() if prior_pass else baseline_preds.copy()
    summary = pd.DataFrame(
        [
            baseline_summary,
            prior_summary,
            metrics(guarded_preds, "guarded_operational_fallback" if not prior_pass else "guarded_operational_candidate"),
            metrics(diag_preds, "diagnostic_2023_single_prior"),
        ]
    )

    feature_view = (
        features[features["feature"].isin(["permit_전체_area", "start_전체_area", "approval_전체_area", "permit_산업·창고_area"])]
        .pivot_table(index="year", columns="feature", values="area", aggfunc="sum")
        .reset_index()
        .sort_values("year")
    )
    detail = pd.concat(
        [
            baseline_preds.assign(policy="baseline"),
            prior_preds.assign(policy="prior_selected_diagnostic"),
            guarded_preds.assign(policy="guarded_operational_fallback" if not prior_pass else "guarded_operational_candidate"),
            diag_preds.assign(policy="diagnostic_2023_single_prior"),
        ],
        ignore_index=True,
    )

    features.to_csv(OUT / "phase238_pyeongtaek_buildinghub_annual_features.csv", index=False)
    candidates.to_csv(OUT / "phase238_pyeongtaek_candidate_detail.csv", index=False)
    prior_choices.to_csv(OUT / "phase238_pyeongtaek_prior_choices.csv", index=False)
    diag_choice.to_csv(OUT / "phase238_pyeongtaek_diagnostic_choice.csv", index=False)
    detail.to_csv(OUT / "phase238_pyeongtaek_policy_detail.csv", index=False)
    summary.to_csv(OUT / "phase238_pyeongtaek_policy_summary.csv", index=False)

    manifest_summary = pd.DataFrame(
        [
            {
                "legal_dongs": int(len(manifest)),
                "api_requests": int(manifest["requested_pages"].sum()),
                "received_rows_manifest": int(manifest["received_rows"].sum()),
                "event_rows": int(len(events)),
                "legal_dongs_with_error": int(manifest["error"].notna().sum()),
                "legal_dongs_with_rows": int((manifest["received_rows"] > 0).sum()),
                "prior_selected_passes_full_guardrail": bool(prior_pass),
            }
        ]
    )
    manifest_summary.to_csv(OUT / "phase238_collection_quality.csv", index=False)

    top_candidates_2022 = (
        candidates[candidates["year"].eq(2022)]
        .sort_values("ape_pct")
        .head(8)
        .copy()
    )
    top_candidates_2023 = (
        candidates[candidates["year"].eq(2023)]
        .sort_values("ape_pct")
        .head(8)
        .copy()
    )

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    report = "\n\n".join(
        [
            "# Phase238 평택시 건설업 BuildingHUB top1 사전검증",
            f"생성시각: {now}",
            "## 결론",
            (
                "- 평택시 200개 법정동 BuildingHUB 건축 인허가 event를 수집했다.\n"
                "- 수집 품질은 부분 양호하다. 200개 법정동, 236 API page, 16,655 event row가 확보됐고 HTTP 500 에러 법정동은 13개다.\n"
                "- 허가 총연면적은 2022년 급등, 2023년 하락을 보여 평택시 건설업의 2022 과소·2023 과대 오차 방향을 설명할 후보 신호다.\n"
                "- prior-selected 후보는 WAPE를 낮추지만 2022년 최대 APE를 악화시켜 전체 guardrail을 통과하지 못했다. 운영 route는 fallback 유지다.\n"
                "- 2022년 한 해를 prior로 삼은 진단 후보는 2023년 APE를 15.512%에서 7%대까지 낮출 수 있으나, 이는 단일 prior 진단이므로 운영 채택이 아니다."
            ),
            "## 1. 수집 품질",
            md_table(
                manifest_summary,
                [
                    ("legal_dongs", "법정동"),
                    ("api_requests", "API page"),
                    ("received_rows_manifest", "manifest 행"),
                    ("event_rows", "event 행"),
                    ("legal_dongs_with_error", "에러 법정동"),
                    ("legal_dongs_with_rows", "행 보유 법정동"),
                    ("prior_selected_passes_full_guardrail", "prior후보 전체통과"),
                ],
            ),
            "## 2. 평택시 건설업 기준 오차",
            md_table(
                base,
                [
                    ("year", "연도"),
                    ("predicted_eok", "현재추정_억원"),
                    ("actual_eok", "실제_억원"),
                    ("abs_error_eok", "절대오차_억원"),
                    ("ape_pct", "APE_%"),
                ],
            ),
            "## 3. 연도별 건축 event 신호",
            md_table(
                feature_view,
                [
                    ("year", "연도"),
                    ("permit_전체_area", "허가총연면적"),
                    ("start_전체_area", "착공총연면적"),
                    ("approval_전체_area", "사용승인총연면적"),
                    ("permit_산업·창고_area", "허가산업창고면적"),
                ],
            ),
            "해석: 허가 총연면적은 2021년 953,969㎡ → 2022년 1,787,876㎡ → 2023년 684,757㎡로 움직인다. 이는 현재 추정이 2022년에 과소, 2023년에 과대였던 방향과 맞는다.",
            "## 4. 정책별 사전검증",
            md_table(
                summary,
                [
                    ("policy", "정책"),
                    ("years", "연도수"),
                    ("actual_sum_eok", "실제합_억원"),
                    ("abs_error_sum_eok", "절대오차합_억원"),
                    ("wape_pct", "WAPE_%"),
                    ("over10_years", "10%초과연도"),
                    ("max_ape_pct", "최대APE_%"),
                ],
            ),
            "## 5. prior-selected rolling 진단",
            md_table(prior_choices, [("year", "연도"), ("chosen_candidate", "선택후보"), ("reason", "이유")]),
            "prior-selected 후보는 과거 정보만으로 선택됐지만, 평가기간 전체에서 최대 APE를 악화시켜 채택하지 않는다. 운영 정책은 guarded fallback이다.",
            "## 6. 2023 단일 prior 진단",
            md_table(diag_choice, [("evaluation_year", "평가연도"), ("chosen_candidate", "진단후보"), ("selection_basis", "선택근거")]),
            md_table(
                detail[detail["policy"].eq("diagnostic_2023_single_prior")],
                [
                    ("year", "연도"),
                    ("candidate", "후보"),
                    ("predicted_eok", "추정_억원"),
                    ("actual_eok", "실제_억원"),
                    ("abs_error_eok", "절대오차_억원"),
                    ("ape_pct", "APE_%"),
                ],
            ),
            "## 7. 후보별 best-case 참고",
            "### 2022",
            md_table(
                top_candidates_2022,
                [
                    ("candidate", "후보"),
                    ("predicted_eok", "추정_억원"),
                    ("actual_eok", "실제_억원"),
                    ("abs_error_eok", "절대오차_억원"),
                    ("ape_pct", "APE_%"),
                    ("feature_ratio", "feature ratio"),
                    ("adjustment_ratio", "조정배율"),
                ],
            ),
            "### 2023",
            md_table(
                top_candidates_2023,
                [
                    ("candidate", "후보"),
                    ("predicted_eok", "추정_억원"),
                    ("actual_eok", "실제_억원"),
                    ("abs_error_eok", "절대오차_억원"),
                    ("ape_pct", "APE_%"),
                    ("feature_ratio", "feature ratio"),
                    ("adjustment_ratio", "조정배율"),
                ],
            ),
            "## 8. 판정",
            (
                "- BuildingHUB 허가 신호는 평택시의 오차 방향을 설명하는 강한 후보지만, top1 단독으로 운영 route를 채택하지 않는다.\n"
                "- prior-selected 후보는 WAPE를 16.666%에서 14.456%로 낮추지만 최대 APE가 24.643%에서 30.671%로 악화되어 guarded fallback 유지가 맞다.\n"
                "- 다음 단계는 top5로 확장해 평택형 신호가 다른 오차 상위 시군구에서도 반복되는지 확인하는 것이다.\n"
                "- 특히 서울 강남·영등포·강서처럼 정비·상업건축형 지역은 허가총연면적 단일 신호가 아니라 정비사업/상업용도 블록과 분리해야 한다."
            ),
            "## 9. 과학자·평가관 검토 반영",
            (
                "- 과학자 검토: 평택 top1은 건축HUB 신호 존재를 보여주지만 alpha/cap이 공격적이면 tail risk가 커진다. 다음 실험은 top5 확장과 더 작은 alpha/cap grid가 필요하다.\n"
                "- 평가관 검토: WAPE 개선이 있어도 최대 APE가 악화되면 정책 산출용 route로 채택하지 않는다. 전국 시군구 건설업 성능 주장은 다지역·다연도 rolling holdout 이후에만 가능하다.\n"
                "- 반영: Phase238은 `운영 route 채택`이 아니라 `top1 후보 신호 사전검증`으로 고정한다."
            ),
            "## 10. 다음 실험 요구사항",
            (
                "1. top5 수집: 평택·강남·영등포·강서·여수.\n"
                "2. 보수 grid: alpha 0.02/0.05/0.10/0.15, cap 0.02/0.05/0.10.\n"
                "3. feature 분리: 허가·착공·사용승인, 면적·건수, 산업/상업/주거 용도, 정비사업 블록.\n"
                "4. 채택 기준: WAPE, 10% 초과연도, 20% 초과연도, 최대 APE, 최근 2년 악화 없음.\n"
                "5. 단일 prior 결과는 관찰로만 보존하고 채택 근거로 쓰지 않는다."
            ),
            "## 산출 파일",
            (
                f"- `{OUT.relative_to(ROOT)}/phase238_pyeongtaek_buildinghub_annual_features.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase238_pyeongtaek_candidate_detail.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase238_pyeongtaek_policy_summary.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase238_pyeongtaek_policy_detail.csv`\n"
                f"- `{OUT.relative_to(ROOT)}/phase238_collection_quality.csv`"
            ),
        ]
    )
    REPORT.write_text(report + "\n", encoding="utf-8")
    print(REPORT)


if __name__ == "__main__":
    main()
