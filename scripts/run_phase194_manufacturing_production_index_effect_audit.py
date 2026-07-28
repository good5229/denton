from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
OUT = DATA / "phase194_manufacturing_production_index_effect_audit"
REPORT = ROOT / "reports" / "partial_statistics_estimation_phase194_manufacturing_production_index_effect_audit.md"
RUN_ID = "partial_statistics_estimation_phase194_manufacturing_production_index_effect_audit"
CREATED_AT = datetime.now().astimezone().isoformat(timespec="seconds")


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, **kwargs)


def audit_stamp(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    payload = out.to_json(orient="records", force_ascii=False, double_precision=12)
    out["input_hash"] = hashlib.sha256(payload.encode()).hexdigest()
    out["code_commit_hash"] = git_hash()
    out["run_id"] = RUN_ID
    out["created_at"] = CREATED_AT
    return out


def write_csv(name: str, df: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    audit_stamp(df).to_csv(OUT / name, index=False, encoding="utf-8-sig")


def md_table(df: pd.DataFrame, digits: int = 4) -> str:
    if df.empty:
        return "_해당 없음_"
    view = df.copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:,.{digits}f}")
        else:
            view[col] = view[col].map(lambda x: "" if pd.isna(x) else str(x))
    lines = [
        "| " + " | ".join(view.columns) + " |",
        "| " + " | ".join(["---"] * len(view.columns)) + " |",
    ]
    for row in view.itertuples(index=False):
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in row) + " |")
    return "\n".join(lines)


def quarter_share_fit(indicator: np.ndarray, quarterly_benchmarks: np.ndarray) -> np.ndarray:
    out: list[float] = []
    for q_idx, benchmark in enumerate(quarterly_benchmarks):
        sl = indicator[q_idx * 3 : q_idx * 3 + 3].astype(float)
        if not np.isfinite(sl).all() or sl.sum() <= 0:
            weights = np.ones(3) / 3
        else:
            weights = sl / sl.sum()
        out.extend((weights * benchmark).tolist())
    return np.asarray(out)


def proportional_denton(indicator: np.ndarray, benchmarks: np.ndarray, frequency: int = 3) -> np.ndarray:
    i, b = np.asarray(indicator, float), np.asarray(benchmarks, float)
    n = len(i)
    m = np.diag(1 / i)
    d = np.zeros((n - 1, n))
    for r in range(n - 1):
        d[r, r], d[r, r + 1] = -1, 1
    h = 2 * m.T @ d.T @ d @ m
    j = np.zeros((len(b), n))
    for k in range(len(b)):
        j[k, k * frequency : (k + 1) * frequency] = 1
    lhs = np.block([[h, j.T], [j, np.zeros((len(b), len(b)))]] )
    answer = np.linalg.lstsq(lhs, np.r_[np.zeros(n), b], rcond=None)[0][:n]
    if np.any(answer <= 0):
        answer = quarter_share_fit(i, b)
    return answer


def source_frequency_audit() -> pd.DataFrame:
    files = [
        ("rolling_mining_manufacturing_production_index.csv", "시도×제조업 확장 생산지수"),
        ("mining_manufacturing_production_index.csv", "시도×제조업 2019~2023 생산지수"),
        ("partial_stats_phase39_manufacturing_middle_production_index.csv", "전국 일부 세부 제조업 생산지수"),
    ]
    rows = []
    for filename, role in files:
        path = DATA / filename
        if not path.exists():
            rows.append({"source_file": filename, "role": role, "exists": False})
            continue
        df = read_csv(path)
        period_values = sorted(df["prd_de"].astype(str).dropna().unique()) if "prd_de" in df else []
        rows.append(
            {
                "source_file": filename,
                "role": role,
                "exists": True,
                "rows": len(df),
                "prd_se_values": ", ".join(sorted(df["prd_se"].astype(str).dropna().unique())) if "prd_se" in df else "",
                "period_min": period_values[0] if period_values else "",
                "period_max": period_values[-1] if period_values else "",
                "period_count": len(period_values),
                "table_id": ", ".join(sorted(df["tbl_id"].astype(str).dropna().unique())) if "tbl_id" in df else "",
                "table_name": ", ".join(sorted(df["tbl_nm"].astype(str).dropna().unique())) if "tbl_nm" in df else "",
                "unit": ", ".join(sorted(df["unit_nm"].astype(str).dropna().unique())) if "unit_nm" in df else "",
            }
        )
    return pd.DataFrame(rows)


def effect_audit() -> pd.DataFrame:
    specs = [
        {
            "city": "고양시",
            "path": DATA / "partial_stats_phase39_manufacturing_city_monthly.csv",
            "algorithm": "proportional_denton",
            "fit_col": "estimated_city_manufacturing_monthly_gva",
            "benchmark_source": DATA / "partial_stats_phase22_gva_sigungu_quarterly_allocation_cube.parquet",
        },
        {
            "city": "포항시",
            "path": DATA / "phase188_manufacturing_production_index_extension" / "phase188_pohang_c00_index_power_monthly_panel.csv",
            "algorithm": "quarter_share_fit",
            "benchmark_col": "uniform_monthly_gva",
            "fit_col": "industrial_index_power_monthly_gva",
        },
    ]
    rows = []
    for spec in specs:
        path = spec["path"]
        if not path.exists():
            rows.append({"city": spec["city"], "status": "missing", "path": str(path.relative_to(ROOT))})
            continue
        df = read_csv(path).sort_values(["year", "month"]).copy()
        required = {"year", "quarter", "month", "production_index_norm", "industrial_kwh_norm", spec["fit_col"]}
        if spec["city"] != "고양시":
            required.add(spec["benchmark_col"])
        missing = sorted(required - set(df.columns))
        if missing:
            rows.append({"city": spec["city"], "status": "missing_columns", "missing": ", ".join(missing)})
            continue
        if spec["city"] == "고양시":
            controls = pd.read_parquet(spec["benchmark_source"])
            control_q = controls[
                controls["source_region"].eq("경기도")
                & controls["sigungu_name"].eq("고양시")
                & controls["sector_code"].eq("C00")
            ][["year", "quarter", "estimated_quarterly_gva"]].copy()
        else:
            control_q = pd.DataFrame()

        if spec["city"] == "고양시":
            q_all = (
                control_q[control_q["year"].isin(sorted(df["year"].unique()))]
                .sort_values(["year", "quarter"])["estimated_quarterly_gva"]
                .to_numpy()
            )
        else:
            q_all = (
                df.groupby(["year", "quarter"], as_index=False)[spec["benchmark_col"]]
                .sum()
                .sort_values(["year", "quarter"])[spec["benchmark_col"]]
                .to_numpy()
            )
        combined_indicator_all = np.sqrt(df["production_index_norm"].to_numpy() * df["industrial_kwh_norm"].to_numpy())
        sqrt_electricity_indicator_all = np.sqrt(df["industrial_kwh_norm"].to_numpy())
        raw_electricity_indicator_all = df["industrial_kwh_norm"].to_numpy()
        production_only_indicator_all = df["production_index_norm"].to_numpy()

        fit_fn = proportional_denton if spec["algorithm"] == "proportional_denton" else quarter_share_fit
        combined_fit_all = fit_fn(combined_indicator_all, q_all)
        sqrt_electricity_fit_all = fit_fn(sqrt_electricity_indicator_all, q_all)
        raw_electricity_fit_all = fit_fn(raw_electricity_indicator_all, q_all)
        production_only_fit_all = fit_fn(production_only_indicator_all, q_all)
        denton_combined_fit_all = proportional_denton(combined_indicator_all, q_all)
        denton_sqrt_electricity_fit_all = proportional_denton(sqrt_electricity_indicator_all, q_all)
        stored_fit_all = df[spec["fit_col"]].to_numpy()

        for year, g in df.groupby("year", sort=True):
            pos = np.flatnonzero(df["year"].to_numpy() == year)
            combined_fit = combined_fit_all[pos]
            sqrt_electricity_fit = sqrt_electricity_fit_all[pos]
            raw_electricity_fit = raw_electricity_fit_all[pos]
            production_only_fit = production_only_fit_all[pos]
            denton_combined_fit = denton_combined_fit_all[pos]
            denton_sqrt_electricity_fit = denton_sqrt_electricity_fit_all[pos]
            stored_fit = stored_fit_all[pos]

            rows.append(
                {
                    "city": spec["city"],
                    "year": int(year),
                    "status": "ok",
                    "implemented_algorithm": spec["algorithm"],
                    "max_abs_diff_stored_vs_recomputed": float(np.max(np.abs(stored_fit - combined_fit))),
                    "max_abs_diff_combined_vs_sqrt_electricity": float(np.max(np.abs(combined_fit - sqrt_electricity_fit))),
                    "max_abs_diff_combined_vs_raw_electricity": float(np.max(np.abs(combined_fit - raw_electricity_fit))),
                    "max_abs_diff_combined_vs_production_only": float(np.max(np.abs(combined_fit - production_only_fit))),
                    "counterfactual_denton_combined_vs_sqrt_electricity": float(
                        np.max(np.abs(denton_combined_fit - denton_sqrt_electricity_fit))
                    ),
                    "quarterly_production_index_unique_counts": ",".join(
                        map(str, g.groupby("quarter")["production_index"].nunique().astype(int).tolist())
                    )
                    if "production_index" in g
                    else "",
                    "interpretation": (
                        "분기 생산지수라 월중 정보는 없지만 Denton 평활화의 분기간 ratio 경로에는 일부 영향"
                        if spec["algorithm"] == "proportional_denton"
                        else "현재 구현은 분기내 비례배분이라 분기 생산지수가 상쇄됨"
                    ),
                }
            )
    return pd.DataFrame(rows)


def script_audit() -> pd.DataFrame:
    targets = [
        ("collect_phase39_manufacturing_kosis.py", ROOT / "scripts" / "collect_phase39_manufacturing_kosis.py"),
        ("run_partial_statistics_phase39_gva.py", ROOT / "scripts" / "run_partial_statistics_phase39_gva.py"),
        ("run_phase188_manufacturing_production_index_extension.py", ROOT / "scripts" / "run_phase188_manufacturing_production_index_extension.py"),
    ]
    rows = []
    for name, path in targets:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        rows.append(
            {
                "script": name,
                "exists": path.exists(),
                "has_period_q_request": 'period="Q"' in text or "period='Q'" in text,
                "has_period_m_request": 'period="M"' in text or "period='M'" in text,
                "uses_quarter_repetition": ".loc[prod.index.repeat(3)]" in text or "month_in_quarter" in text,
                "uses_production_index": "production_index" in text,
                "uses_industrial_kwh": "industrial_kwh" in text,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    freq = source_frequency_audit()
    effect = effect_audit()
    scripts = script_audit()

    write_csv("phase194_source_frequency_audit.csv", freq)
    write_csv("phase194_effect_equivalence_audit.csv", effect)
    write_csv("phase194_script_path_audit.csv", scripts)

    effect_show = effect.copy()
    for col in [
        "max_abs_diff_stored_vs_recomputed",
        "max_abs_diff_combined_vs_sqrt_electricity",
        "max_abs_diff_combined_vs_raw_electricity",
        "max_abs_diff_combined_vs_production_only",
        "counterfactual_denton_combined_vs_sqrt_electricity",
    ]:
        if col in effect_show:
            effect_show[col] = effect_show[col] / 100.0
    effect_show = effect_show.rename(
        columns={
            "city": "지역",
            "year": "연도",
            "status": "상태",
            "implemented_algorithm": "구현 알고리즘",
            "max_abs_diff_stored_vs_recomputed": "저장값 재현 최대차이(억원)",
            "max_abs_diff_combined_vs_sqrt_electricity": "결합지표 vs sqrt전력 최대차이(억원)",
            "max_abs_diff_combined_vs_raw_electricity": "결합지표 vs 원전력 최대차이(억원)",
            "max_abs_diff_combined_vs_production_only": "결합지표 vs 생산지수단독 최대차이(억원)",
            "counterfactual_denton_combined_vs_sqrt_electricity": "Denton 적용시 결합지표 효과(억원)",
            "quarterly_production_index_unique_counts": "분기별 생산지수 유니크수",
            "interpretation": "해석",
        }
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        f"""# Phase194 제조업 산업생산지수 실제 반영효과 감사

## 결론

사용자 지적이 맞다. 제조업 총부가가치 추정에서 산업생산지수는 가장 중요한 시간변화 지표 중 하나인데, 현재 구현은 이를 **일관되게 제대로 활용했다고 보기 어렵다**.

이유는 단순하다. 현재 로컬 제조업 산업생산지수는 모두 `분기(Q)`로 수집되어 있고, 기존 코드가 이 분기값을 같은 분기 3개월에 반복했다. 고양시 Phase39는 비례 Denton 평활화라 분기 사이 지표 수준 변화가 일부 반영되지만, 월간 생산지수를 직접 쓴 것은 아니다. 포항시 Phase188은 분기 안 비례배분으로 구현되어 분기 생산지수가 실제로 상쇄된다.

따라서 기존 보고서의 표현은 다음처럼 정정해야 한다.

- 기존 표현: `제조업 산업생산지수 + 산업용 전력량으로 월별 제조업 GVA 경로를 생성`
- 정정 표현: `고양시는 분기 생산지수가 Denton 평활화에 일부 반영되지만 월간 생산지수는 미사용, 포항시는 현재 구현상 월별 변동이 사실상 산업용 전력량이 결정`

## 원천 주기 감사

{md_table(freq.rename(columns={
    "source_file": "파일",
    "role": "역할",
    "exists": "존재",
    "rows": "행수",
    "prd_se_values": "수록주기",
    "period_min": "시작시점",
    "period_max": "종료시점",
    "period_count": "시점수",
    "table_id": "KOSIS표",
    "table_name": "표명",
    "unit": "단위",
}), 0)}

## 실제 반영효과 감사

단위: 억원. `결합지표`는 기존 구현의 `sqrt(분기 생산지수 × 산업용 전력)`이다. `Denton 적용시 결합지표 효과`는 포항도 고양과 같은 비례 Denton으로 바꿨을 때 생산지수가 얼마나 월 경로를 바꿀 수 있는지를 보여주는 반사실 비교다.

{md_table(effect_show, 6)}

## 코드 경로 감사

{md_table(scripts.rename(columns={
    "script": "스크립트",
    "exists": "존재",
    "has_period_q_request": "분기요청",
    "has_period_m_request": "월요청",
    "uses_quarter_repetition": "분기값 3개월 반복",
    "uses_production_index": "생산지수 컬럼 사용",
    "uses_industrial_kwh": "산업용전력 사용",
}), 0)}

## 판정

1. **고양시 Phase39**: 저장된 월별 제조업 GVA는 재현된다. 분기 생산지수라 월중 직접 정보는 없지만, 비례 Denton의 분기간 ratio 평활화에는 일부 반영된다. 다만 “월간 산업생산지수 반영”은 아니다.
2. **포항시 Phase188/191**: 경북 제조업 생산지수를 붙였다는 점은 맞지만, 현재 구현은 분기 안 비례배분이라 생산지수가 상쇄된다. 포항은 고양과 같은 비례 Denton 또는 월간 생산지수 기반 방식으로 고쳐야 한다.
3. **중분류 배분**: 시도×제조업 총지수는 중분류 횡단면을 구분하지 못한다. 중분류별 성능 개선에는 중분류별 생산지수 또는 생산품·공장·전력·물동량 같은 직접 활동자료가 필요하다.
4. **속보성**: 월간 산업생산지수를 새로 수집하더라도, 1개월 이내 속보성 실험에는 각 월/분기의 공표 가능시점 장부가 필요하다.

## 수정 방향

1. KOSIS `DT_1F02001`, `DT_1F02011`을 `period=M`으로 재수집한다.
2. 월간 생산지수를 월별 지표로 직접 결합한다. 분기값 반복 방식은 폐기한다.
3. 산업생산지수는 제조업 전체 월 경로의 1차 지표로 사용하고, 산업용 전력은 지역 강도 보정으로 사용한다.
4. 중분류별 금액격차는 월간 총지수만으로 해결되지 않으므로, 중분류별 세부 생산지수 또는 KICOX 공장 생산품/면적/종업원, 포항 항만 품목 물동량 등을 별도 경로로 결합한다.
5. 포스터/보고서에서는 현재 결과를 `산업용 전력 중심 월배분`으로 정정하고, 월간 생산지수 재수집 후에만 `산업생산지수 반영`이라고 표현한다.
""",
        encoding="utf-8",
    )
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
