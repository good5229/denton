#!/usr/bin/env python3
"""Phase228: BuildingHUB sample spatial holdout for construction.

Use the already-collected BuildingHUB vintage sample (Seoul Gangnam/Jongno and
Busan Haeundae) to test whether building activity helps construction GVA
spatial allocation outside the Goyang/Pohang middle-industry proof.

Only Seoul Gangnam/Jongno form a comparable multi-city parent group in the
local sample, so this is a tiny diagnostic holdout rather than an adopted
route.  It allocates the Gangnam+Jongno construction actual total by candidate
shares and compares against the two district actuals.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUTDIR = DATA / "phase228_construction_buildinghub_sample_spatial_holdout"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase228_construction_buildinghub_sample_spatial_holdout.md"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")

FEATURES = DATA / "buildinghub_feature_table.csv"
ERROR_AUDIT = ROOT / "nationwide" / "outputs" / "annual_sigungu_activity_error_audit.csv"


def read_csv_any(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949", low_memory=False)


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], digits: int = 2) -> str:
    if df.empty:
        return "_해당 없음_\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "개", "WAPE", "면적")) else "---" for _, label in cols) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            v = row.get(key, "")
            if isinstance(v, (float, np.floating)):
                vals.append(f"{float(v):,.{digits}f}")
            elif isinstance(v, (int, np.integer)):
                vals.append(f"{int(v):,}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def normalize_features(features: pd.DataFrame) -> pd.DataFrame:
    f = features.copy()
    key_map = {
        "서울특별시 강남구": "강남구",
        "서울특별시 종로구": "종로구",
        "부산광역시 해운대구": "해운대구",
    }
    f["city"] = f["sigungu_feature_key"].map(key_map).fillna(f["sigungu_feature_key"])
    f["year"] = pd.to_numeric(f["observation_period"], errors="coerce").floordiv(100).astype("Int64")
    f["feature_value"] = pd.to_numeric(f["feature_value"], errors="coerce").fillna(0.0)
    return f


def annual_feature_matrix(features: pd.DataFrame) -> pd.DataFrame:
    wanted = [
        "permit_floor_area",
        "start_floor_area",
        "approval_floor_area",
        "residential_permit_area",
        "commercial_permit_area",
        "office_permit_area",
        "other_permit_area",
        "permit_count",
        "start_count",
        "approval_count",
    ]
    f = features[features["feature_name"].isin(wanted)].copy()
    g = f.groupby(["city", "year", "feature_name"], as_index=False)["feature_value"].sum()
    wide = g.pivot_table(index=["city", "year"], columns="feature_name", values="feature_value", fill_value=0).reset_index()
    for c in wanted:
        if c not in wide.columns:
            wide[c] = 0.0
    wide["permit_nonres_area"] = (
        wide["permit_floor_area"] - wide["residential_permit_area"]
    ).clip(lower=0)
    wide["permit_commercial_office_area"] = wide["commercial_permit_area"] + wide["office_permit_area"]
    wide["permit_area_per_count"] = wide["permit_floor_area"] / wide["permit_count"].replace(0, np.nan)
    return wide


def safe_share(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce").fillna(0.0).clip(lower=0)
    total = float(values.sum())
    if total <= 0:
        return pd.Series(1.0 / len(values), index=values.index)
    return values / total


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    features = normalize_features(read_csv_any(FEATURES))
    annual_features = annual_feature_matrix(features)

    audit = pd.read_csv(ERROR_AUDIT)
    cons = audit[(audit["activity"].eq("건설업")) & (audit["city"].isin(["강남구", "종로구"]))].copy()
    cons = cons[cons["year"].between(2021, 2023)].copy()
    cons["actual_eok"] = pd.to_numeric(cons["actual_eok"], errors="coerce")
    cons["predicted_eok"] = pd.to_numeric(cons["predicted_eok"], errors="coerce")

    candidates = [
        ("baseline_current_share", "현행 추정비중", "predicted_eok"),
        ("permit_floor_area_share", "건축허가 연면적", "permit_floor_area"),
        ("start_floor_area_share", "착공 연면적", "start_floor_area"),
        ("approval_floor_area_share", "사용승인 연면적", "approval_floor_area"),
        ("permit_nonres_area_share", "비주거 허가면적", "permit_nonres_area"),
        ("permit_commercial_office_share", "상업·업무 허가면적", "permit_commercial_office_area"),
        ("permit_count_share", "허가 건수", "permit_count"),
    ]

    detail_rows = []
    summary_rows = []
    for year, g in cons.groupby("year"):
        pair = g[["city", "actual_eok", "predicted_eok"]].merge(
            annual_features[annual_features["year"].eq(year)].drop(columns=["year"]),
            on="city",
            how="left",
        )
        if set(pair["city"]) != {"강남구", "종로구"}:
            continue
        pair = pair.fillna(0.0)
        total_actual = float(pair["actual_eok"].sum())
        for candidate_id, label, source_col in candidates:
            shares = safe_share(pair[source_col])
            pred = total_actual * shares
            err = (pred - pair["actual_eok"]).abs()
            wape = float(err.sum() / total_actual * 100) if total_actual else np.nan
            summary_rows.append(
                {
                    "year": int(year),
                    "candidate_id": candidate_id,
                    "candidate_label": label,
                    "actual_sum_eok": total_actual,
                    "error_sum_eok": float(err.sum()),
                    "wape_pct": wape,
                    "max_ape_pct": float((err / pair["actual_eok"].replace(0, np.nan) * 100).max()),
                }
            )
            for i, row in pair.iterrows():
                detail_rows.append(
                    {
                        "year": int(year),
                        "city": row["city"],
                        "candidate_id": candidate_id,
                        "candidate_label": label,
                        "source_value": float(row[source_col]),
                        "actual_eok": float(row["actual_eok"]),
                        "predicted_eok": float(pred.loc[i]),
                        "error_eok": float(err.loc[i]),
                        "ape_pct": float(err.loc[i] / row["actual_eok"] * 100) if row["actual_eok"] else np.nan,
                        "share_pct": float(shares.loc[i] * 100),
                    }
                )

    detail = pd.DataFrame(detail_rows)
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        overall = (
            summary.groupby(["candidate_id", "candidate_label"], as_index=False)
            .agg(actual_sum_eok=("actual_sum_eok", "sum"), error_sum_eok=("error_sum_eok", "sum"), mean_wape_pct=("wape_pct", "mean"), max_wape_pct=("wape_pct", "max"))
        )
        overall["pooled_wape_pct"] = overall["error_sum_eok"] / overall["actual_sum_eok"] * 100
        overall = overall.sort_values(["pooled_wape_pct", "max_wape_pct"])
    else:
        overall = pd.DataFrame()

    summary = summary.sort_values(["year", "wape_pct"]) if not summary.empty else summary
    detail = detail.sort_values(["year", "candidate_id", "city"]) if not detail.empty else detail

    annual_features.to_csv(OUTDIR / "phase228_buildinghub_sample_annual_features.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTDIR / "phase228_seoul_pair_candidate_summary.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase228_seoul_pair_candidate_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase228_seoul_pair_candidate_overall.csv", index=False, encoding="utf-8-sig")

    best_by_year = summary.groupby("year", as_index=False).head(3) if not summary.empty else pd.DataFrame()
    baseline = summary[summary["candidate_id"].eq("baseline_current_share")] if not summary.empty else pd.DataFrame()

    report = f"""# 건설업 BuildingHUB 샘플 공간배분 holdout

생성시각: {CREATED_AT}

## 목적

고양·포항 41/42 중분류 실험 외에, 로컬에 이미 있는 BuildingHUB vintage 샘플이 건설업 시군구 공간배분을 설명하는지 추가로 확인한다. 현재 샘플에서 같은 시도 내 복수 시군구 검증이 가능한 조합은 서울 강남구·종로구뿐이다. 따라서 이 결과는 전국 채택 검증이 아니라 작은 holdout 진단이다.

## 결론

- 서울 강남구·종로구 pair 기준으로는 건축활동 단일지표가 모든 연도에서 안정적으로 현행 추정비중을 이기지는 못했다.
- 특히 2022년처럼 실제 건설업 GVA가 급변하는 경우, 허가·착공·사용승인 연면적만으로는 공간배분을 설명하기 어렵다.
- 따라서 Phase227의 고양·포항 41/42 개선은 강한 local proof지만, 시군구 건설업 전체 공간배분에는 재건축·재개발 단계, 대형 민간개발, 공공·토목 공사금액을 함께 넣어야 한다.

## 후보별 2021~2023 pooled 결과

{md_table(overall, [("candidate_label", "후보"), ("actual_sum_eok", "실제합 억원"), ("error_sum_eok", "오차합 억원"), ("pooled_wape_pct", "pooled WAPE %"), ("mean_wape_pct", "평균 WAPE %"), ("max_wape_pct", "최대 WAPE %")])}

## 연도별 상위 후보

{md_table(best_by_year, [("year", "연도"), ("candidate_label", "후보"), ("actual_sum_eok", "실제합 억원"), ("error_sum_eok", "오차합 억원"), ("wape_pct", "WAPE %"), ("max_ape_pct", "최대 APE %")])}

## 현행 추정비중 기준

{md_table(baseline, [("year", "연도"), ("candidate_label", "후보"), ("actual_sum_eok", "실제합 억원"), ("error_sum_eok", "오차합 억원"), ("wape_pct", "WAPE %"), ("max_ape_pct", "최대 APE %")])}

## 판정

- 건축허가/착공/사용승인 자료는 건설업 내부 41/42 분할에는 매우 유망하지만, 시군구 전체 건설업 GVA 공간배분에서는 단일지표로 부족하다.
- 서울 pair holdout은 건설업 route가 `건축물 자료만`으로 끝나면 안 된다는 반증에 가깝다.
- 다음 실험은 top1/top5 수집 지역에서 다음 묶음을 분리해 비교해야 한다.
  - 민간건축: 허가·착공·사용승인 면적
  - 정비사업: 재개발·재건축 단계·면적·세대수
  - 공공/토목: PPS 공사공고·계약 금액
  - fallback: 기존 share
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase228_seoul_pair_candidate_overall.csv")


if __name__ == "__main__":
    main()
