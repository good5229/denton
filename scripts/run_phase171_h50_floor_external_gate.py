#!/usr/bin/env python3
"""Phase171: external diagnostic for an H50 water-transport floor rule.

Rule under test:
    If a city/sigungu already has an H50 row in the H00 middle-industry
    estimation universe, set predicted H50 share to at least 7% and rescale
    the remaining H49/H52 shares proportionally.  If no H50 row exists, do not
    create one.

This keeps the rule from hallucinating water transport in inland/non-H50
regions.  The 7% threshold remains a diagnostic candidate until validated on a
broader set of port cities with independent port cargo/GVA mapping.
"""

from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data" / "processed" / "phase171_h50_floor_external_gate"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase171_h50_floor_external_gate.md"
EXTERNAL = ROOT / "data" / "processed" / "phase108_collected_10_sigungu_generalization" / "phase108_collected_10_sigungu_middle_accuracy_detail.csv"
POHANG = ROOT / "data" / "processed" / "phase124_pps_subblock_no_worse" / "phase124_registry.csv"


def md_table(df: pd.DataFrame, cols: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    if df.empty:
        return "해당 없음\n"
    lines = ["| " + " | ".join(label for _, label in cols) + " |"]
    lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in cols:
            value = row.get(key, "")
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.2f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def load_external() -> pd.DataFrame:
    df = pd.read_csv(EXTERNAL)
    df["code"] = df["division_code"].astype(str).str.zfill(2)
    df = df[df["parent_code"].eq("H00") & df["code"].isin(["49", "50", "52"])].copy()
    return pd.DataFrame(
        {
            "sample_group": "external10",
            "region": df["source_region"],
            "sigungu": df["sigungu_name"],
            "code": df["code"],
            "label": df["division_name"],
            "actual_gva_eok": pd.to_numeric(df["actual_gva_eok"], errors="coerce"),
            "baseline_predicted_gva_eok": pd.to_numeric(df["predicted_gva_eok"], errors="coerce"),
        }
    )


def load_pohang() -> pd.DataFrame:
    df = pd.read_csv(POHANG)
    df["code"] = df["middle_code"].astype(str).str.zfill(2)
    df = df[df["city"].eq("포항시") & df["parent_code"].eq("H00") & df["code"].isin(["49", "50", "52"])].copy()
    return pd.DataFrame(
        {
            "sample_group": "target_pohang",
            "region": "경상북도",
            "sigungu": df["city"],
            "code": df["code"],
            "label": df["middle_label"],
            "actual_gva_eok": pd.to_numeric(df["actual_gva_eok"], errors="coerce"),
            "baseline_predicted_gva_eok": pd.to_numeric(df["phase124_predicted_gva_eok"], errors="coerce"),
        }
    )


def apply_candidate(part: pd.DataFrame, candidate: str, floor: float = 0.07) -> pd.Series:
    total = float(part["actual_gva_eok"].sum())
    shares = part.set_index("code")["baseline_predicted_gva_eok"] / total
    if candidate == "h50_floor_if_present" and "50" in shares.index and float(shares["50"]) < floor:
        old_resid = float(shares.drop("50").sum())
        shares.loc["50"] = floor
        if old_resid > 0:
            for code in list(shares.index):
                if code != "50":
                    shares.loc[code] = float(shares.loc[code]) / old_resid * (1 - floor)
    elif candidate == "h50_floor_all_regions":
        # Deliberately included as a negative-control: it creates H50 in
        # regions that did not have an H50 row.
        if "50" not in shares.index:
            old_resid = float(shares.sum())
            shares.loc["50"] = floor
            if old_resid > 0:
                for code in [c for c in list(shares.index) if c != "50"]:
                    shares.loc[code] = float(shares.loc[code]) / old_resid * (1 - floor)
        elif float(shares["50"]) < floor:
            old_resid = float(shares.drop("50").sum())
            shares.loc["50"] = floor
            if old_resid > 0:
                for code in list(shares.index):
                    if code != "50":
                        shares.loc[code] = float(shares.loc[code]) / old_resid * (1 - floor)
    return shares * total


def evaluate(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows: list[dict[str, object]] = []
    city_rows: list[dict[str, object]] = []
    candidates = {
        "baseline": "기준선",
        "h50_floor_if_present": "H50 존재지역 7% 하한",
        "h50_floor_all_regions": "음성대조: 모든 지역 7% 하한",
    }
    for (sample_group, region, sigungu), part in panel.groupby(["sample_group", "region", "sigungu"]):
        part = part.copy()
        total = float(part["actual_gva_eok"].sum())
        actual_by_code = part.set_index("code")["actual_gva_eok"]
        h50_row_present = "50" in set(part["code"])
        for cid, cname in candidates.items():
            if cid == "baseline":
                pred = part.set_index("code")["baseline_predicted_gva_eok"]
            else:
                pred = apply_candidate(part, cid)
            # Include candidate-created H50 row for negative-control.
            codes = sorted(set(actual_by_code.index).union(set(pred.index)))
            err_sum = 0.0
            for code in codes:
                actual = float(actual_by_code.get(code, 0.0))
                predicted = float(pred.get(code, 0.0))
                err = abs(predicted - actual)
                err_sum += err
                detail_rows.append(
                    {
                        "sample_group": sample_group,
                        "region": region,
                        "sigungu": sigungu,
                        "candidate_id": cid,
                        "candidate": cname,
                        "h50_row_present": h50_row_present,
                        "code": code,
                        "label": part.set_index("code")["label"].to_dict().get(code, "수상 운송업" if code == "50" else ""),
                        "actual_gva_eok": actual,
                        "predicted_gva_eok": predicted,
                        "actual_share_pct": actual / total * 100 if total else 0.0,
                        "predicted_share_pct": predicted / total * 100 if total else 0.0,
                        "error_eok": err,
                        "error_rate_pct": err / actual * 100 if actual else np.nan,
                    }
                )
            city_rows.append(
                {
                    "sample_group": sample_group,
                    "region": region,
                    "sigungu": sigungu,
                    "candidate_id": cid,
                    "candidate": cname,
                    "h50_row_present": h50_row_present,
                    "actual_sum_eok": total,
                    "error_sum_eok": err_sum,
                    "wape_pct": err_sum / total * 100 if total else np.nan,
                }
            )
    return pd.DataFrame(city_rows), pd.DataFrame(detail_rows)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    panel = pd.concat([load_external(), load_pohang()], ignore_index=True)
    city, detail = evaluate(panel)
    overall = (
        city.groupby("candidate", as_index=False)
        .agg(actual_sum_eok=("actual_sum_eok", "sum"), error_sum_eok=("error_sum_eok", "sum"), mean_city_wape_pct=("wape_pct", "mean"), max_city_wape_pct=("wape_pct", "max"))
    )
    overall["pooled_wape_pct"] = overall["error_sum_eok"] / overall["actual_sum_eok"] * 100
    baseline_error = float(overall.loc[overall["candidate"].eq("기준선"), "error_sum_eok"].iloc[0])
    overall["improvement_vs_baseline_eok"] = baseline_error - overall["error_sum_eok"]
    overall["adoption_status"] = np.where(
        overall["candidate"].eq("H50 존재지역 7% 하한"),
        "제한적 운영 후보: 항만도시 추가검증 필요",
        np.where(overall["candidate"].eq("음성대조: 모든 지역 7% 하한"), "채택금지: 비항만 지역 악화", "기준선"),
    )
    city_pivot = city.pivot_table(index=["sample_group", "region", "sigungu", "h50_row_present"], columns="candidate", values="wape_pct").reset_index()
    if "H50 존재지역 7% 하한" in city_pivot.columns and "기준선" in city_pivot.columns:
        city_pivot["h50_floor_delta_pp"] = city_pivot["H50 존재지역 7% 하한"] - city_pivot["기준선"]
    h50_detail = detail[(detail["code"].eq("50")) & (detail["candidate"].isin(["기준선", "H50 존재지역 7% 하한"]))].copy()

    panel.to_csv(OUTDIR / "phase171_h00_external_pohang_panel.csv", index=False, encoding="utf-8-sig")
    city.to_csv(OUTDIR / "phase171_city_candidate_wape.csv", index=False, encoding="utf-8-sig")
    detail.to_csv(OUTDIR / "phase171_middle_candidate_detail.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUTDIR / "phase171_overall_candidate_summary.csv", index=False, encoding="utf-8-sig")
    city_pivot.to_csv(OUTDIR / "phase171_city_wape_pivot.csv", index=False, encoding="utf-8-sig")
    h50_detail.to_csv(OUTDIR / "phase171_h50_detail.csv", index=False, encoding="utf-8-sig")
    (OUTDIR / "execution_manifest.json").write_text(
        json.dumps(
            {
                "external_input": str(EXTERNAL.relative_to(ROOT)),
                "pohang_input": str(POHANG.relative_to(ROOT)),
                "rule": "Apply 7% H50 floor only if H50 row is already present; never create H50 in non-H50 regions.",
                "boundary": "The 7% floor is supported only by limited external10 + Pohang diagnostic evidence; broader port-city validation remains required.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    h50_presence = city[city["candidate"].eq("기준선")].sort_values(["h50_row_present", "region", "sigungu"], ascending=[False, True, True])
    report = f"""# Phase171 H50 수상운송 7% 하한 규칙 외부 검증

## 목적

Phase170에서 포항시 H50 수상운송업에 7% 최소비중을 두면 H00 중분류 WAPE가 8.81%에서 1.28%로 크게 낮아졌다. 그러나 이 값이 포항 actual에 맞춘 우연인지 확인해야 한다. 이번 단계에서는 Phase108 외부 10개 시군구와 포항시를 함께 사용해, 다음 보수 규칙을 검증했다.

> H00 중분류 추정 우주에 H50 수상운송업 행이 이미 있는 지역에만 H50 예측비중을 최소 7%로 올리고, 나머지 H49/H52는 기존 비율대로 축소한다. H50 행이 없는 지역에는 H50을 새로 만들지 않는다.

## 후보별 전체 성능

{md_table(overall.sort_values("error_sum_eok"), [("candidate", "후보"), ("actual_sum_eok", "검증 actual 억원"), ("error_sum_eok", "합산오차 억원"), ("pooled_wape_pct", "통합 WAPE %"), ("mean_city_wape_pct", "지역평균 WAPE %"), ("max_city_wape_pct", "최대 WAPE %"), ("improvement_vs_baseline_eok", "기준 대비 개선 억원"), ("adoption_status", "판정")])}

## 지역별 WAPE 변화

{md_table(city_pivot.sort_values("h50_floor_delta_pp"), [("sample_group", "표본"), ("region", "광역"), ("sigungu", "시군구"), ("h50_row_present", "H50 행 존재"), ("기준선", "기준 WAPE %"), ("H50 존재지역 7% 하한", "제한규칙 WAPE %"), ("음성대조: 모든 지역 7% 하한", "무차별규칙 WAPE %"), ("h50_floor_delta_pp", "제한규칙 변화 pp")])}

## H50 행 존재 지역

{md_table(h50_presence[h50_presence["h50_row_present"]], [("sample_group", "표본"), ("region", "광역"), ("sigungu", "시군구"), ("actual_sum_eok", "H00 actual 억원"), ("wape_pct", "기준 WAPE %")])}

H50 중분류 자체의 변화:

{md_table(h50_detail.sort_values(["region", "sigungu", "candidate"]), [("sample_group", "표본"), ("region", "광역"), ("sigungu", "시군구"), ("candidate", "후보"), ("actual_gva_eok", "H50 실제 억원"), ("predicted_gva_eok", "H50 추정 억원"), ("actual_share_pct", "실제비중 %"), ("predicted_share_pct", "추정비중 %"), ("error_eok", "오차 억원"), ("error_rate_pct", "오차 %")])}

## 판정

1. 모든 지역에 7% H50을 강제하는 규칙은 채택하면 안 된다. 비항만/비H50 지역에 존재하지 않는 수상운송 GVA를 만들어 일부 지역을 악화시킨다.
2. H50 행이 이미 존재하는 지역에만 적용하는 제한규칙은 통합 WAPE를 낮춘다. 포항은 크게 개선되고, 영암군도 개선되며, 서귀포시는 기존 H50 비중이 이미 7%를 넘어서 변화가 없다.
3. 그러나 외부 10개 중 H50 행이 존재하는 검증 지역은 영암군·서귀포시 2개뿐이다. 따라서 이 규칙은 **제한적 운영 후보**이지 최종 확정식은 아니다.
4. 최종 채택에는 부산·울산·인천·광양·당진 등 대형 항만도시를 추가로 포함해 H50 actual 비중과 항만 물동량/GVA 관계를 검증해야 한다.

## 산출물

- `data/processed/phase171_h50_floor_external_gate/phase171_overall_candidate_summary.csv`
- `data/processed/phase171_h50_floor_external_gate/phase171_city_wape_pivot.csv`
- `data/processed/phase171_h50_floor_external_gate/phase171_h50_detail.csv`
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR)


if __name__ == "__main__":
    main()
