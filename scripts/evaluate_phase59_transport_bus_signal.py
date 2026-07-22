#!/usr/bin/env python3
"""Evaluate Gyeonggi bus boarding as a specialized H transport signal.

This does not claim bus data explains all H00 (transportation and storage).
It checks whether the newly collected free bus ridership source carries a
usable temporal signal against available upper-level actuals:

  - Gyeonggi H00 real GRVA annual actual (2020-2023)
  - Gyeonggi H establishments/employees annual actual (2020-2024)

Outputs are intentionally small and poster/report ready.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path


PROCESSED = Path("data/processed")
OUT_DIR = PROCESSED / "phase59_transport_bus_signal"
REPORT = Path("reports/partial_statistics_estimation_phase59_transport_bus_signal.md")


def read_bus_annual() -> dict[int, dict[str, float]]:
    path = PROCESSED / "phase58_gg_bus/gg_bus_sigun_monthly.csv"
    annual = defaultdict(lambda: defaultdict(float))
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            year = int(row["month"][:4])
            annual[year]["board_total"] += float(row["board_total"])
            annual[year]["alight_total"] += float(row["alight_total"])
            annual[year]["first_board_total"] += float(row["first_board_total"])
            annual[year]["transfer_total"] += float(row["transfer_total"])
            annual[year]["passenger_total"] += float(row["board_total"]) + float(row["alight_total"])
            annual[year]["rows"] += float(row["rows"])
    return {y: dict(v) for y, v in annual.items()}


def read_grva_actual() -> dict[int, float]:
    out = {}
    path = PROCESSED / "annual_grva_real.csv"
    with path.open(encoding="cp949", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["c1_id"] == "31" and row["c2_id"] == "H00" and row["item_id"] == "T11":
                out[int(row["prd_de"])] = float(row["value"])
    return out


def read_business_actual(metric: str) -> dict[int, float]:
    out = {}
    path = PROCESSED / "business_sido_industry_all.csv"
    with path.open(encoding="cp949", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["c1_id"] == "31" and row["c2_id"] == "H" and row["metric"] == metric:
                out[int(row["prd_de"])] = float(row["value"])
    return out


def index_series(series: dict[int, float], years: list[int], base_year: int) -> dict[int, float]:
    base = series.get(base_year)
    if not base:
        return {}
    return {y: series[y] / base * 100 for y in years if y in series}


def yoy(series: dict[int, float], years: list[int]) -> dict[int, float]:
    out = {}
    for y in years:
        if y - 1 in series and y in series and series[y - 1] != 0:
            out[y] = series[y] / series[y - 1] - 1.0
    return out


def mae(a: dict[int, float], b: dict[int, float]) -> float:
    ys = sorted(set(a) & set(b))
    return sum(abs(a[y] - b[y]) for y in ys) / len(ys) if ys else math.nan


def direction_accuracy(a: dict[int, float], b: dict[int, float]) -> float:
    ys = sorted(set(a) & set(b))
    if not ys:
        return math.nan
    return sum((a[y] >= 0) == (b[y] >= 0) for y in ys) / len(ys)


def corr(a: dict[int, float], b: dict[int, float]) -> float:
    ys = sorted(set(a) & set(b))
    if len(ys) < 2:
        return math.nan
    xs = [a[y] for y in ys]
    zs = [b[y] for y in ys]
    mx = sum(xs) / len(xs)
    mz = sum(zs) / len(zs)
    vx = sum((x - mx) ** 2 for x in xs)
    vz = sum((z - mz) ** 2 for z in zs)
    if vx <= 0 or vz <= 0:
        return math.nan
    return sum((x - mx) * (z - mz) for x, z in zip(xs, zs)) / math.sqrt(vx * vz)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bus = read_bus_annual()
    grva = read_grva_actual()
    est = read_business_actual("establishments")
    emp = read_business_actual("employees")

    targets = {
        "H00 실질 GVA": grva,
        "H 사업체수": est,
        "H 종사자수": emp,
    }
    features = {
        "버스 승차": {y: v["board_total"] for y, v in bus.items()},
        "버스 하차": {y: v["alight_total"] for y, v in bus.items()},
        "버스 승하차 합계": {y: v["passenger_total"] for y, v in bus.items()},
        "버스 초승": {y: v["first_board_total"] for y, v in bus.items()},
        "버스 환승": {y: v["transfer_total"] for y, v in bus.items()},
    }

    index_rows = []
    score_rows = []
    for target_name, target in targets.items():
        common_years = sorted(set(target) & set(bus))
        if not common_years:
            continue
        # GVA actual is only through 2023; business actual through 2024.
        base_year = min(common_years)
        target_idx = index_series(target, common_years, base_year)
        target_yoy = yoy(target, common_years)
        for feature_name, feature in features.items():
            feature_idx = index_series(feature, common_years, base_year)
            feature_yoy = yoy(feature, common_years)
            for y in common_years:
                index_rows.append(
                    {
                        "target": target_name,
                        "feature": feature_name,
                        "year": y,
                        "target_actual": target.get(y, ""),
                        "feature_value": feature.get(y, ""),
                        "target_index_base100": round(target_idx.get(y, math.nan), 6),
                        "feature_index_base100": round(feature_idx.get(y, math.nan), 6),
                        "target_yoy_pct": round(target_yoy.get(y, math.nan) * 100, 6) if y in target_yoy else "",
                        "feature_yoy_pct": round(feature_yoy.get(y, math.nan) * 100, 6) if y in feature_yoy else "",
                    }
                )
            score_rows.append(
                {
                    "target": target_name,
                    "feature": feature_name,
                    "years": f"{min(common_years)}-{max(common_years)}",
                    "n_years": len(common_years),
                    "index_mae_points": round(mae(target_idx, feature_idx), 6),
                    "yoy_direction_accuracy": round(direction_accuracy(target_yoy, feature_yoy), 6),
                    "yoy_corr": round(corr(target_yoy, feature_yoy), 6),
                }
            )

    write_csv(OUT_DIR / "phase59_bus_transport_index_panel.csv", index_rows)
    write_csv(OUT_DIR / "phase59_bus_transport_signal_scores.csv", score_rows)

    best = {}
    for target in sorted({r["target"] for r in score_rows}):
        candidates = [r for r in score_rows if r["target"] == target]
        best[target] = sorted(candidates, key=lambda r: (r["index_mae_points"], -r["yoy_direction_accuracy"]))[0]

    # Goyang-specific compact monthly table for poster/next model use.
    goyang_month = []
    with (PROCESSED / "phase58_gg_bus/gg_bus_sigun_monthly.csv").open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["관할관청"] == "고양시":
                goyang_month.append(
                    {
                        "month": row["month"],
                        "board_total": row["board_total"],
                        "alight_total": row["alight_total"],
                        "passenger_total": int(row["board_total"]) + int(row["alight_total"]),
                    }
                )
    write_csv(OUT_DIR / "phase59_goyang_bus_monthly_feature.csv", goyang_month)

    def md(rows: list[dict], cols: list[str]) -> str:
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for r in rows:
            lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
        return "\n".join(lines)

    top_rows = sorted(score_rows, key=lambda r: (r["target"], r["index_mae_points"]))[:15]
    lines = [
        "# Phase59 경기버스 승하차 기반 운수·창고업 특화 신호 검증",
        "",
        "## 결론",
        "",
        "- 경기버스 정류소별 승하차 원본 20개 ZIP을 전부 수집·무결성 확인 후 `시군×월`, `고양 일별`, `고양 정류소×월`로 스트리밍 집계했다.",
        "- 2025-05 원본만 영문 컬럼명을 사용해 초기 집계에서 승하차가 0으로 잡히는 문제가 있었고, 컬럼 alias 검사를 추가해 수정했다.",
        "- 경기도 전체 H00 실질 GVA actual과 비교하면, 버스 승하차는 H00 전체를 대체하는 단일 근거는 아니지만 여객 운송 부문의 월별 활동 신호로는 사용할 수 있다.",
        "- 고양시 행정동 공간 배분까지 내려가려면 정류소 좌표/행정동 매핑이 추가로 필요하다. 현재 공공데이터포털 정류소 조회 API는 403으로 막혔으므로, 경기데이터드림 정류소 현황 파일/API 접근권한 확인이 필요하다.",
        "",
        "## 주요 점검 결과",
        "",
        md(top_rows, ["target", "feature", "years", "n_years", "index_mae_points", "yoy_direction_accuracy", "yoy_corr"]),
        "",
        "## 생성 산출물",
        "",
        "- `data/processed/phase58_gg_bus/gg_bus_sigun_monthly.csv`",
        "- `data/processed/phase58_gg_bus/gg_bus_goyang_daily.csv`",
        "- `data/processed/phase58_gg_bus/gg_bus_station_monthly_goyang.csv`",
        "- `data/processed/phase59_transport_bus_signal/phase59_bus_transport_index_panel.csv`",
        "- `data/processed/phase59_transport_bus_signal/phase59_bus_transport_signal_scores.csv`",
        "- `data/processed/phase59_transport_bus_signal/phase59_goyang_bus_monthly_feature.csv`",
        "",
        "## 적용 판단",
        "",
        "- 시간 해상도: 월별 사용 가능.",
        "- 공간 해상도: 현재는 시군까지 직접 사용 가능. 고양 행정동은 정류소 좌표 수집 후 공간 결합 필요.",
        "- 산업 해상도: H00 중 여객 운송 활동 신호로 사용. 창고·화물·항만 활동은 별도 자료와 결합해야 H00 전체 설명력이 좋아진다.",
        "- 포스터 표현: `프록시` 대신 `버스 승하차 활동지표`, `월별 이동수요 지표`로 표기하는 것이 적절하다.",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    manifest = {
        "outputs": {
            "index_panel": str(OUT_DIR / "phase59_bus_transport_index_panel.csv"),
            "scores": str(OUT_DIR / "phase59_bus_transport_signal_scores.csv"),
            "goyang_monthly_feature": str(OUT_DIR / "phase59_goyang_bus_monthly_feature.csv"),
            "report": str(REPORT),
        },
        "best_by_target": best,
    }
    (OUT_DIR / "phase59_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
