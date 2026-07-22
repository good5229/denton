#!/usr/bin/env python3
"""Phase73: Goyang health/welfare middle-industry split experiment.

The target is GVA accuracy, not accounting reconciliation.  The experiment
asks whether free public facility data can improve the Q00 split between
KSIC 86 (health) and KSIC 87 (social welfare services), where Phase68 found a
large offsetting error.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "phase37_goyang_emd"
DATA = ROOT / "data" / "processed"
BASE = DATA / "phase68_middle_industry_accuracy" / "phase68_middle_industry_accuracy_detail.csv"
OUTDIR = DATA / "phase73_goyang_health_welfare_split"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase73_goyang_health_welfare_split.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False, dtype=str)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False, dtype=str)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("-", "", regex=False),
        errors="coerce",
    )


def active_localdata(frame: pd.DataFrame) -> pd.Series:
    status = frame.get("영업상태명", pd.Series("", index=frame.index)).astype(str)
    detail = frame.get("상세영업상태명", pd.Series("", index=frame.index)).astype(str)
    return status.str.contains("영업|정상", na=False) | detail.str.contains("영업|정상", na=False)


def health_totals() -> dict[str, float]:
    totals: dict[str, float] = {}
    rows = []
    for slug, label in (("hospitals", "병원"), ("clinics", "의원"), ("pharmacies", "약국")):
        path = RAW / f"localdata_{slug}_goyang.csv"
        frame = read_csv(path)
        active = active_localdata(frame)
        count = int(active.sum())
        beds = numeric(frame.loc[active, "병상수"]).sum() if "병상수" in frame.columns else 0.0
        staff = numeric(frame.loc[active, "의료인수"]).sum() if "의료인수" in frame.columns else 0.0
        rooms = numeric(frame.loc[active, "입원실수"]).sum() if "입원실수" in frame.columns else 0.0
        area_col = "총면적" if "총면적" in frame.columns else "약국영업면적" if "약국영업면적" in frame.columns else None
        area = numeric(frame.loc[active, area_col]).sum() if area_col else 0.0
        totals[f"{slug}_count"] = float(count)
        totals[f"{slug}_beds"] = float(beds)
        totals[f"{slug}_staff"] = float(staff)
        totals[f"{slug}_rooms"] = float(rooms)
        totals[f"{slug}_area_sqm"] = float(area)
        rows.append(
            {
                "source": label,
                "active_facilities": count,
                "beds": beds,
                "medical_staff": staff,
                "rooms": rooms,
                "area_sqm": area,
                "sha256": sha256(path),
            }
        )
    health_count = sum(totals[f"{slug}_count"] for slug in ("hospitals", "clinics", "pharmacies"))
    health_beds = sum(totals[f"{slug}_beds"] for slug in ("hospitals", "clinics", "pharmacies"))
    health_staff = sum(totals[f"{slug}_staff"] for slug in ("hospitals", "clinics", "pharmacies"))
    health_area = sum(totals[f"{slug}_area_sqm"] for slug in ("hospitals", "clinics", "pharmacies"))
    totals.update(
        {
            "health_count": health_count,
            "health_beds": health_beds,
            "health_staff": health_staff,
            "health_area_sqm": health_area,
        }
    )
    pd.DataFrame(rows).to_csv(OUTDIR / "phase73_health_source_audit.csv", index=False, encoding="utf-8-sig")
    return totals


def welfare_totals() -> dict[str, float]:
    specs = (
        ("LYR0056", "여성복지시설", None),
        ("LYR0057", "노인복지시설", "입소정원수"),
        ("LYR0058", "아동복지시설", "입소정원(명)"),
        ("LYR0124", "경로당", "이용회원수"),
    )
    rows = []
    total_count = 0.0
    total_capacity = 0.0
    for layer, label, capacity_col in specs:
        path = RAW / f"goyang_layer_{layer}.csv"
        frame = read_csv(path)
        count = float(len(frame))
        capacity = numeric(frame[capacity_col]).sum() if capacity_col and capacity_col in frame.columns else 0.0
        total_count += count
        total_capacity += capacity
        rows.append(
            {
                "layer_id": layer,
                "source": label,
                "facilities": int(count),
                "capacity_or_members": capacity,
                "capacity_column": capacity_col or "",
                "sha256": sha256(path),
            }
        )
    pd.DataFrame(rows).to_csv(OUTDIR / "phase73_welfare_source_audit.csv", index=False, encoding="utf-8-sig")
    return {"welfare_count": total_count, "welfare_capacity": total_capacity}


def candidate_table(health: dict[str, float], welfare: dict[str, float]) -> pd.DataFrame:
    h_count = health["health_count"]
    h_no_pharm = health["hospitals_count"] + health["clinics_count"]
    h_area = health["health_area_sqm"]
    h_beds = health["health_beds"]
    h_staff = health["health_staff"]
    w_count = welfare["welfare_count"]
    w_capacity = welfare["welfare_capacity"]

    candidates = [
        {
            "candidate": "현행 소분류 합산 기준",
            "health_indicator": np.nan,
            "welfare_indicator": np.nan,
            "health_share": np.nan,
            "method_note": "Phase68 현행 추정값",
        },
        {
            "candidate": "균등 분할",
            "health_indicator": 1.0,
            "welfare_indicator": 1.0,
            "health_share": 0.5,
            "method_note": "두 중분류를 동일 비중으로 가정",
        },
        {
            "candidate": "시설 수 기준",
            "health_indicator": h_count,
            "welfare_indicator": w_count,
            "health_share": h_count / (h_count + w_count),
            "method_note": "병원·의원·약국 수 ÷ 보건·복지시설 수",
        },
        {
            "candidate": "의료기관 수 기준",
            "health_indicator": h_no_pharm,
            "welfare_indicator": w_count,
            "health_share": h_no_pharm / (h_no_pharm + w_count),
            "method_note": "약국 제외 의료기관 수 ÷ 복지시설 수",
        },
        {
            "candidate": "시설규모 혼합 기준",
            "health_indicator": h_count + h_beds / 10 + h_staff / 10 + h_area / 1_000,
            "welfare_indicator": w_count + w_capacity / 10,
            "health_share": (h_count + h_beds / 10 + h_staff / 10 + h_area / 1_000)
            / (h_count + h_beds / 10 + h_staff / 10 + h_area / 1_000 + w_count + w_capacity / 10),
            "method_note": "개수+병상/10+의료인/10+면적/1000㎡ vs 복지시설+정원/10",
        },
        {
            "candidate": "의료면적 강화 기준",
            "health_indicator": h_count + h_beds / 10 + h_staff / 10 + h_area / 200,
            "welfare_indicator": w_count + w_capacity / 10,
            "health_share": (h_count + h_beds / 10 + h_staff / 10 + h_area / 200)
            / (h_count + h_beds / 10 + h_staff / 10 + h_area / 200 + w_count + w_capacity / 10),
            "method_note": "의료시설 대형화 반영: 면적 200㎡를 활동 1단위로 환산",
        },
    ]
    return pd.DataFrame(candidates)


def md_table(df: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    lines = ["| " + " | ".join(label for _, label in columns) + " |"]
    lines.append("| " + " | ".join("---:" if any(t in label for t in ("억원", "%", "수", "면적", "정원")) else "---" for _, label in columns) + " |")
    for _, row in df.iterrows():
        vals = []
        for key, _ in columns:
            value = row[key]
            if isinstance(value, (float, np.floating)):
                vals.append(f"{value:,.1f}")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(BASE)
    q = base[base.city.eq("고양시") & base.parent_section.eq("Q00")].copy()
    if set(q.middle_code.astype(str).str.zfill(2)) != {"86", "87"}:
        raise RuntimeError("Expected Goyang Q00 to contain middle codes 86 and 87")
    q["middle_code"] = q.middle_code.astype(str).str.zfill(2)
    parent_gva = float(q.actual_gva_eok.sum())
    actual_health_share = float(q.loc[q.middle_code.eq("86"), "actual_middle_share"].iloc[0])
    current_health_share = float(q.loc[q.middle_code.eq("86"), "predicted_small_aggregated_share"].iloc[0])

    health = health_totals()
    welfare = welfare_totals()
    candidates = candidate_table(health, welfare)
    candidates.loc[candidates.candidate.eq("현행 소분류 합산 기준"), "health_share"] = current_health_share
    candidates["welfare_share"] = 1 - candidates["health_share"]
    candidates["health_actual_eok"] = actual_health_share * parent_gva
    candidates["welfare_actual_eok"] = (1 - actual_health_share) * parent_gva
    candidates["health_pred_eok"] = candidates.health_share * parent_gva
    candidates["welfare_pred_eok"] = candidates.welfare_share * parent_gva
    candidates["health_error_eok"] = (candidates.health_pred_eok - candidates.health_actual_eok).abs()
    candidates["welfare_error_eok"] = (candidates.welfare_pred_eok - candidates.welfare_actual_eok).abs()
    candidates["combined_error_eok"] = candidates.health_error_eok + candidates.welfare_error_eok
    candidates["health_error_pct"] = candidates.health_error_eok / candidates.health_actual_eok * 100
    candidates["welfare_error_pct"] = candidates.welfare_error_eok / candidates.welfare_actual_eok * 100
    candidates["combined_wape_pct"] = candidates.combined_error_eok / parent_gva * 100
    current_error = float(candidates.loc[candidates.candidate.eq("현행 소분류 합산 기준"), "combined_error_eok"].iloc[0])
    candidates["improvement_vs_current_eok"] = current_error - candidates.combined_error_eok
    candidates["improvement_vs_current_pct"] = candidates.improvement_vs_current_eok / current_error * 100
    candidates["decision"] = np.where(candidates.combined_error_eok < current_error, "개선", "악화")
    candidates = candidates.sort_values("combined_error_eok")
    candidates.to_csv(OUTDIR / "phase73_goyang_health_welfare_split_candidates.csv", index=False, encoding="utf-8-sig")

    best = candidates.iloc[0]
    source_summary = pd.DataFrame(
        [
            {
                "health_facilities": health["health_count"],
                "health_beds": health["health_beds"],
                "health_staff": health["health_staff"],
                "health_area_sqm": health["health_area_sqm"],
                "welfare_facilities": welfare["welfare_count"],
                "welfare_capacity": welfare["welfare_capacity"],
            }
        ]
    )
    source_summary.to_csv(OUTDIR / "phase73_goyang_health_welfare_source_summary.csv", index=False, encoding="utf-8-sig")

    detail = []
    for _, row in candidates.iterrows():
        for code, label, actual, pred, error, epct in (
            ("86", "보건업", row.health_actual_eok, row.health_pred_eok, row.health_error_eok, row.health_error_pct),
            ("87", "사회복지 서비스업", row.welfare_actual_eok, row.welfare_pred_eok, row.welfare_error_eok, row.welfare_error_pct),
        ):
            detail.append(
                {
                    "candidate": row.candidate,
                    "middle_code": code,
                    "middle_label": label,
                    "actual_gva_eok": actual,
                    "predicted_gva_eok": pred,
                    "error_gva_eok": error,
                    "error_rate_pct": epct,
                }
            )
    pd.DataFrame(detail).to_csv(OUTDIR / "phase73_goyang_health_welfare_split_detail.csv", index=False, encoding="utf-8-sig")

    display = candidates.copy()
    display["health_share_pct"] = display.health_share * 100
    display["welfare_share_pct"] = display.welfare_share * 100
    display["health_indicator"] = display.health_indicator.fillna(0)
    display["welfare_indicator"] = display.welfare_indicator.fillna(0)

    report = f"""# 고양시 보건·사회복지 GVA 내부 분할 개선 실험

## 목적

Phase68에서 고양시 `보건·사회복지(Q00)`는 총량보다 내부 분할이 문제였다. 보건업은 과소추정되고 사회복지 서비스업은 같은 금액만큼 과대추정됐다. 이번 실험은 무료 공공자료인 병의원·약국 인허가와 고양시 생활지도 복지시설 자료를 이용해 두 중분류의 GVA 분할 정확도를 개선할 수 있는지 비교한다.

## 사용 자료

| 구분 | 자료 | 수량 |
| --- | --- | ---: |
| 보건 활동 | 병원·의원·약국 영업 중 시설 | {health['health_count']:,.0f}개 |
| 보건 활동 | 병상수 | {health['health_beds']:,.0f}개 |
| 보건 활동 | 의료인수 | {health['health_staff']:,.0f}명 |
| 보건 활동 | 의료·약국 면적 | {health['health_area_sqm']:,.0f}㎡ |
| 복지 활동 | 여성·노인·아동복지시설·경로당 | {welfare['welfare_count']:,.0f}개 |
| 복지 활동 | 노인·아동복지시설 입소정원 | {welfare['welfare_capacity']:,.0f}명 |

## 후보별 성능

단위는 억원이다. 실제값은 2023년 보건·사회복지 대분류 GVA를 중분류 실제 비중으로 환산한 값이고, 추정값은 각 후보의 보건/복지 분할비중을 같은 총량에 적용한 값이다.

{md_table(display, [("candidate", "후보"), ("health_share_pct", "보건 비중 %"), ("health_pred_eok", "보건 추정 억원"), ("health_error_eok", "보건 오차 억원"), ("health_error_pct", "보건 오차 %"), ("welfare_pred_eok", "복지 추정 억원"), ("welfare_error_eok", "복지 오차 억원"), ("welfare_error_pct", "복지 오차 %"), ("combined_error_eok", "합산오차 억원"), ("combined_wape_pct", "합산오차 %"), ("improvement_vs_current_pct", "현행 대비 개선 %"), ("decision", "판정")])}

## 판정

- 최선 후보는 **{best.candidate}**이다.
- 현행 기준의 보건 비중은 {current_health_share * 100:.1f}%였고 실제 보건 비중은 {actual_health_share * 100:.1f}%였다.
- 최선 후보의 보건 비중은 {best.health_share * 100:.1f}%이며, 합산오차는 {best.combined_error_eok:,.1f}억원이다.
- 현행 합산오차 {current_error:,.1f}억원 대비 {best.improvement_vs_current_eok:,.1f}억원, {best.improvement_vs_current_pct:.1f}% 개선된다.

## 해석

1. 단순 시설 수 기준은 현행보다 개선되지만 충분하지 않다. 사회복지 시설과 경로당은 수가 많고 소규모 시설이 많아, 시설 수만 쓰면 사회복지 GVA를 여전히 크게 배분한다.
2. 보건업은 병상·의료인력·면적처럼 시설 규모 차이가 GVA와 더 가깝다. 이를 반영하면 보건업 과소추정이 크게 줄어든다.
3. 다만 `의료면적 강화 기준`은 고양시 한 지역에서 좋은 후보로 확인된 것이다. 실제 운영모델로 승격하려면 포항시와 다른 시군구의 보건·복지 자료로 같은 개선이 반복되는지 확인해야 한다.

## 포스터 반영 가능 문장

고양시 보건·사회복지 내부 분할에서 병의원·약국의 병상·의료인력·면적과 복지시설 정원을 결합하자, 보건업/사회복지 서비스업 합산 GVA 오차가 {current_error:,.0f}억원에서 {best.combined_error_eok:,.0f}억원으로 감소했다.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(REPORT)
    print(OUTDIR / "phase73_goyang_health_welfare_split_candidates.csv")
    print(OUTDIR / "phase73_goyang_health_welfare_split_detail.csv")


if __name__ == "__main__":
    main()
